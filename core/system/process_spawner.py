import os
import sys
import shlex
import subprocess
import asyncio
import psutil
from typing import Optional, List, Tuple
from core.logger import log
from core.config.models import BotConfig
from core.interfaces.system import ILogRotator
from core.common.retry import retry_async
from core.system.path_utils import is_subpath_or_equal

class ProcessSpawner:
    """Handles low-level process creation, termination, and systemd service interactions."""
    def __init__(self, stop_timeout: float = 5.0, restart_wait: float = 1.0, log_rotator: Optional[ILogRotator] = None):
        self.stop_timeout = stop_timeout
        self.restart_wait = restart_wait
        self.log_rotator = log_rotator
        self.last_error: Optional[str] = None

    @staticmethod
    def validate_command(cmd: str) -> Tuple[bool, Optional[str]]:
        """Validates command string against dangerous shell injection patterns and metacharacters."""
        if not cmd or not cmd.strip():
            return False, "Command cannot be empty"

        dangerous_chars = [";", "&&", "||", "|", "`", "$", "\n", "\r", ">", "<"]
        for ch in dangerous_chars:
            if ch in cmd:
                return False, f"Command contains forbidden shell metacharacter '{ch}'"

        return True, None

    def spawn(self, bot_config: BotConfig, env: dict) -> Optional[int]:
        """Spawns a child bot process in background, redirecting stdout/stderr to its log file."""
        is_valid, error_msg = self.validate_command(bot_config.cmd)
        if not is_valid:
            self.last_error = f"Security rejection for bot '{bot_config.id}': {error_msg}"
            log.error(f"[ProcessSpawner] {self.last_error}")
            return None

        try:
            log_file_path = os.path.join(bot_config.path, bot_config.log)
            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

            # Rotate child log before starting if size exceeded
            if self.log_rotator:
                self.log_rotator.rotate_file(log_file_path)

            argv = shlex.split(bot_config.cmd, posix=(os.name != 'nt'))
            with open(log_file_path, "a", encoding="utf-8") as log_file:
                # Use CREATE_NEW_PROCESS_GROUP (0x00000200) on Windows to isolate processes
                creation_flags = 0x00000200 if os.name == 'nt' else 0
                new_proc = subprocess.Popen(
                    argv,
                    cwd=bot_config.path,
                    env=env,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    creationflags=creation_flags
                )

            self.last_error = None
            log.info(f"[ProcessSpawner] Spawned bot '{bot_config.name}' ({bot_config.id}) with PID: {new_proc.pid}")
            return new_proc.pid
        except FileNotFoundError as e:
            self.last_error = f"Executable or directory not found for bot {bot_config.id} ('{bot_config.cmd}'): {e}"
            log.error(f"[ProcessSpawner] {self.last_error}")
            return None
        except PermissionError as e:
            self.last_error = f"Permission denied spawning bot {bot_config.id}: {e}"
            log.error(f"[ProcessSpawner] {self.last_error}")
            return None
        except subprocess.SubprocessError as e:
            self.last_error = f"Subprocess failure spawning bot {bot_config.id}: {e}"
            log.error(f"[ProcessSpawner] {self.last_error}")
            return None
        except OSError as e:
            self.last_error = f"OS error spawning bot {bot_config.id}: {e}"
            log.error(f"[ProcessSpawner] {self.last_error}")
            return None
        except Exception as e:
            self.last_error = f"Unexpected error spawning bot {bot_config.id}: {e}"
            log.error(f"[ProcessSpawner] {self.last_error}")
            return None

    async def terminate_process(self, process: psutil.Process) -> bool:
        """Gracefully terminates a process, escalating to kill if necessary."""
        if not process:
            self.last_error = None
            return True

        try:
            if not process.is_running():
                self.last_error = None
                return True
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            self.last_error = None
            return True
        except psutil.AccessDenied:
            log.warning(f"[ProcessSpawner] Access denied checking process PID {process.pid}")

        try:
            log.info(f"[ProcessSpawner] Terminating process PID {process.pid}...")
            process.terminate()
            
            # Wait loop
            for _ in range(int(self.stop_timeout * 10)):
                try:
                    if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
                        break
                except (psutil.NoSuchProcess, psutil.ZombieProcess):
                    break
                await asyncio.sleep(0.1)

            try:
                if process.is_running() and process.status() != psutil.STATUS_ZOMBIE:
                    log.warning(f"[ProcessSpawner] Process PID {process.pid} did not exit in time. Killing it...")
                    process.kill()
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                pass

            self.last_error = None
            return True
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            self.last_error = None
            return True
        except psutil.AccessDenied as e:
            self.last_error = f"Access denied terminating PID {process.pid} (insufficient permissions): {e}"
            log.error(f"[ProcessSpawner] {self.last_error}")
            return False
        except Exception as e:
            self.last_error = f"Unexpected error terminating process PID {process.pid}: {e}"
            log.error(f"[ProcessSpawner] {self.last_error}")
            return False

    def find_all_processes_in_path(self, bot_path: str) -> List[int]:
        """Finds any running bot processes rooted inside the bot's folder.
        
        Optimized with fast executable name filtering before performing expensive cwd inspections.
        """
        found_pids = []
        target_path = os.path.normpath(bot_path).lower()
        runtime_executables = ("python", "java", "node", "pypy", "uv", "uvicorn")

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = (proc.info.get('name') or '').lower()
                if not any(name.startswith(exe) for exe in runtime_executables):
                    continue

                cwd = proc.cwd()
                if not cwd:
                    continue
                if is_subpath_or_equal(cwd, bot_path):
                    found_pids.append(proc.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as e:
                log.debug(f"[ProcessSpawner] Error inspecting process: {e}")
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
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                pass
            except psutil.AccessDenied:
                log.debug(f"[ProcessSpawner] Access denied force-killing rogue process {pid}")
            except Exception as e:
                log.debug(f"[ProcessSpawner] Unexpected error force-killing rogue process {pid}: {e}")

    # --- Systemd Support (Linux) ---
    @staticmethod
    def check_systemd_privileges() -> Tuple[bool, str]:
        """Checks if current user has necessary sudo privileges to execute systemctl."""
        if os.name != 'posix':
            return False, "Systemd is only supported on Linux/POSIX."
        try:
            res = subprocess.run(['sudo', '-n', 'systemctl', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                return True, "Sudo access confirmed"
            return False, "Passwordless sudo required. Please configure sudoers: 'username ALL=(ALL) NOPASSWD: /bin/systemctl'"
        except (FileNotFoundError, PermissionError, OSError) as e:
            return False, f"Cannot verify sudo privileges: {e}"

    def start_service(self, service_name: str) -> bool:
        if os.name != 'posix':
            self.last_error = "Systemd is only supported on Linux/POSIX."
            return False
        has_privs, priv_msg = self.check_systemd_privileges()
        if not has_privs:
            self.last_error = f"Cannot start systemd service '{service_name}': {priv_msg}"
            log.error(f"[ProcessSpawner] {self.last_error}")
            return False
        try:
            log.info(f"[ProcessSpawner] Starting systemd service: {service_name}")
            subprocess.run(['sudo', 'systemctl', 'start', service_name], check=True)
            self.last_error = None
            return True
        except subprocess.CalledProcessError as e:
            self.last_error = f"Systemctl start failed for {service_name}: exit code {e.returncode}"
            log.error(f"[ProcessSpawner] {self.last_error}")
            return False
        except FileNotFoundError:
            self.last_error = "systemctl executable not found on system."
            log.error(f"[ProcessSpawner] {self.last_error}")
            return False
        except Exception as e:
            self.last_error = f"Unexpected error starting systemd service {service_name}: {e}"
            log.error(f"[ProcessSpawner] {self.last_error}")
            return False

    def stop_service(self, service_name: str) -> bool:
        if os.name != 'posix':
            self.last_error = "Systemd is only supported on Linux/POSIX."
            return False
        has_privs, priv_msg = self.check_systemd_privileges()
        if not has_privs:
            self.last_error = f"Cannot stop systemd service '{service_name}': {priv_msg}"
            log.error(f"[ProcessSpawner] {self.last_error}")
            return False
        try:
            log.info(f"[ProcessSpawner] Stopping systemd service: {service_name}")
            subprocess.run(['sudo', 'systemctl', 'stop', service_name], check=True)
            self.last_error = None
            return True
        except subprocess.CalledProcessError as e:
            self.last_error = f"Systemctl stop failed for {service_name}: exit code {e.returncode}"
            log.error(f"[ProcessSpawner] {self.last_error}")
            return False
        except FileNotFoundError:
            self.last_error = "systemctl executable not found on system."
            log.error(f"[ProcessSpawner] {self.last_error}")
            return False
        except Exception as e:
            self.last_error = f"Unexpected error stopping systemd service {service_name}: {e}"
            log.error(f"[ProcessSpawner] {self.last_error}")
            return False

    def restart_service(self, service_name: str) -> bool:
        if os.name != 'posix':
            self.last_error = "Systemd is only supported on Linux/POSIX."
            return False
        has_privs, priv_msg = self.check_systemd_privileges()
        if not has_privs:
            self.last_error = f"Cannot restart systemd service '{service_name}': {priv_msg}"
            log.error(f"[ProcessSpawner] {self.last_error}")
            return False
        try:
            log.info(f"[ProcessSpawner] Restarting systemd service: {service_name}")
            subprocess.run(['sudo', 'systemctl', 'restart', service_name], check=True)
            self.last_error = None
            return True
        except subprocess.CalledProcessError as e:
            self.last_error = f"Systemctl restart failed for {service_name}: exit code {e.returncode}"
            log.error(f"[ProcessSpawner] {self.last_error}")
            return False
        except FileNotFoundError:
            self.last_error = "systemctl executable not found on system."
            log.error(f"[ProcessSpawner] {self.last_error}")
            return False
        except Exception as e:
            self.last_error = f"Unexpected error restarting systemd service {service_name}: {e}"
            log.error(f"[ProcessSpawner] {self.last_error}")
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
        except FileNotFoundError:
            log.debug("[ProcessSpawner] systemctl executable not found.")
            return "unknown"
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
        async def _fetch():
            pid = self.get_systemd_pid(service_name)
            if not pid:
                raise ValueError("PID not available yet")
            return pid

        try:
            return await retry_async(
                _fetch,
                max_retries=retries,
                initial_delay=self.restart_wait,
                backoff_factor=1.0,
                jitter=False,
                exceptions=(ValueError,)
            )
        except Exception:
            return None

    def execute_manager_restart(self) -> None:
        """Executes a self-restart of the manager process using os.execv or subprocess fallback."""
        log.info("[ProcessSpawner] Executing Bot Manager self-restart...")
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except OSError as e:
            log.error(f"[ProcessSpawner] os.execv failed ({e}), falling back to subprocess.Popen")
            subprocess.Popen([sys.executable] + sys.argv)
            sys.exit(0)
        except Exception as e:
            log.error(f"[ProcessSpawner] Unexpected error in execv ({e}), falling back to Popen")
            subprocess.Popen([sys.executable] + sys.argv)
            sys.exit(0)

    def execute_manager_shutdown(self) -> None:
        """Terminates the Bot Manager process cleanly."""
        log.info("[ProcessSpawner] Terminating Bot Manager process...")
        sys.exit(0)
