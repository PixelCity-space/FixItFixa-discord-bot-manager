import os
import sys
import subprocess
import asyncio
import psutil
from typing import Optional, List
from core.logger import log
from core.config.models import BotConfig
from core.system.log_rotator import LogRotator

class ProcessSpawner:
    """Handles low-level process creation, termination, and systemd service interactions."""
    def __init__(self, stop_timeout: float = 5.0, restart_wait: float = 1.0, log_rotator: Optional[LogRotator] = None):
        self.stop_timeout = stop_timeout
        self.restart_wait = restart_wait
        self.log_rotator = log_rotator

    def spawn(self, bot_config: BotConfig, env: dict) -> Optional[int]:
        """Spawns a child bot process in background, redirecting stdout/stderr to its log file."""
        try:
            log_file_path = os.path.join(bot_config.path, bot_config.log)
            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

            # Rotate child log before starting if size exceeded
            if self.log_rotator:
                self.log_rotator.rotate_file(log_file_path)

            with open(log_file_path, "a", encoding="utf-8") as log_file:
                # Use CREATE_NEW_PROCESS_GROUP (0x00000200) on Windows to isolate processes
                creation_flags = 0x00000200 if os.name == 'nt' else 0
                new_proc = subprocess.Popen(
                    bot_config.cmd.split(),
                    cwd=bot_config.path,
                    env=env,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    creationflags=creation_flags
                )

            log.info(f"[ProcessSpawner] Spawned bot '{bot_config.name}' ({bot_config.id}) with PID: {new_proc.pid}")
            return new_proc.pid
        except Exception as e:
            log.error(f"[ProcessSpawner] Failed to spawn bot {bot_config.id}: {e}")
            return None

    async def terminate_process(self, process: psutil.Process) -> bool:
        """Gracefully terminates a process, escalating to kill if necessary."""
        if not process or not process.is_running():
            return True

        try:
            log.info(f"[ProcessSpawner] Terminating process PID {process.pid}...")
            process.terminate()
            
            # Wait loop
            for _ in range(int(self.stop_timeout * 10)):
                if not process.is_running():
                    break
                await asyncio.sleep(0.1)

            if process.is_running():
                log.warning(f"[ProcessSpawner] Process PID {process.pid} did not exit in time. Killing it...")
                process.kill()

            return True
        except psutil.NoSuchProcess:
            return True
        except Exception as e:
            log.error(f"[ProcessSpawner] Error terminating process PID {process.pid}: {e}")
            return False

    def find_all_processes_in_path(self, bot_path: str) -> List[int]:
        """Finds any running Python processes rooted inside the bot's folder."""
        found_pids = []
        target_path = os.path.normpath(bot_path).lower()

        for proc in psutil.process_iter(['pid', 'name', 'cwd', 'cmdline']):
            try:
                cwd = proc.info.get('cwd')
                if not cwd:
                    continue
                norm_cwd = os.path.normpath(cwd).lower()
                if norm_cwd.startswith(target_path):
                    cmdline = proc.info.get('cmdline')
                    if cmdline and any('python' in arg.lower() for arg in cmdline):
                        found_pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return found_pids

    async def kill_rogue_processes(self, bot_path: str) -> None:
        """Kills any rogue/orphaned processes running from the specified bot path."""
        rogue_pids = await asyncio.to_thread(self.find_all_processes_in_path, bot_path)
        for pid in rogue_pids:
            try:
                p = psutil.Process(pid)
                if p.is_running():
                    log.info(f"[ProcessSpawner] Force-killing rogue process {pid} in {bot_path}")
                    p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    # --- Systemd Support (Linux) ---
    def start_service(self, service_name: str) -> bool:
        if os.name != 'posix':
            return False
        try:
            log.info(f"[ProcessSpawner] Starting systemd service: {service_name}")
            subprocess.run(['sudo', 'systemctl', 'start', service_name], check=True)
            return True
        except Exception as e:
            log.error(f"[ProcessSpawner] Failed to start systemd service {service_name}: {e}")
            return False

    def stop_service(self, service_name: str) -> bool:
        if os.name != 'posix':
            return False
        try:
            log.info(f"[ProcessSpawner] Stopping systemd service: {service_name}")
            subprocess.run(['sudo', 'systemctl', 'stop', service_name], check=True)
            return True
        except Exception as e:
            log.error(f"[ProcessSpawner] Failed to stop systemd service {service_name}: {e}")
            return False

    def restart_service(self, service_name: str) -> bool:
        if os.name != 'posix':
            return False
        try:
            log.info(f"[ProcessSpawner] Restarting systemd service: {service_name}")
            subprocess.run(['sudo', 'systemctl', 'restart', service_name], check=True)
            return True
        except Exception as e:
            log.error(f"[ProcessSpawner] Failed to restart systemd service {service_name}: {e}")
            return False

    def get_systemd_state(self, service_name: str) -> str:
        if os.name != 'posix':
            return "unknown"
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True, text=True, check=False
            )
            return result.stdout.strip()
        except Exception as e:
            log.error(f"[ProcessSpawner] Error checking systemd state for {service_name}: {e}")
            return "error"

    def get_systemd_pid(self, service_name: str) -> Optional[int]:
        if os.name != 'posix':
            return None
        try:
            result = subprocess.run(
                ['systemctl', 'show', '-p', 'MainPID', '--value', service_name],
                capture_output=True, text=True, check=False
            )
            pid_str = result.stdout.strip()
            if pid_str and pid_str != '0':
                return int(pid_str)
        except Exception as e:
            log.error(f"[ProcessSpawner] Error getting PID for systemd {service_name}: {e}")
        return None

    async def get_systemd_pid_async(self, service_name: str, retries: int = 3) -> Optional[int]:
        for i in range(retries):
            pid = self.get_systemd_pid(service_name)
            if pid:
                return pid
            await asyncio.sleep(self.restart_wait)
        return None

    def execute_manager_restart(self) -> None:
        """Executes a self-restart of the manager process using os.execv or subprocess fallback."""
        log.info("[ProcessSpawner] Executing Bot Manager self-restart...")
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            log.error(f"[ProcessSpawner] os.execv failed, falling back to subprocess.Popen: {e}")
            subprocess.Popen([sys.executable] + sys.argv)
            sys.exit(0)

    def execute_manager_shutdown(self) -> None:
        """Terminates the Bot Manager process cleanly."""
        log.info("[ProcessSpawner] Terminating Bot Manager process...")
        sys.exit(0)
