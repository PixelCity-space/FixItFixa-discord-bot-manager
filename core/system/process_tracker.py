import os
import psutil
import datetime
from typing import Dict, List, Tuple, Optional, Any, TYPE_CHECKING
from core.logger import log
from core.config.models import BotConfig
from core.system.path_utils import is_subpath_or_equal

if TYPE_CHECKING:
    from core.interfaces.system import IProcessSpawner

class ProcessTracker:
    """Tracks active processes, collects bot metrics, and detects crashes/unexpected stops."""
    def __init__(self):
        self.managed_processes: Dict[str, psutil.Process] = {}
        self.manual_stop: set = set()

    def is_running(self, bot_id: str) -> bool:
        """Checks if a bot's process is currently alive and not in a zombie state."""
        process = self.managed_processes.get(bot_id)
        if not process:
            return False
        try:
            alive = bool(process.is_running() and process.status() != psutil.STATUS_ZOMBIE)
            if not alive:
                self.unregister(bot_id)
            return alive
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            self.unregister(bot_id)
            return False
        except Exception as e:
            log.debug(f"[ProcessTracker] Error checking is_running for {bot_id}: {e}")
            return False

    def register(self, bot_id: str, pid: int) -> None:
        """Registers a newly started PID under tracking."""
        try:
            self.managed_processes[bot_id] = psutil.Process(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            log.debug(f"[ProcessTracker] Could not attach to PID {pid} for bot {bot_id}: {e}")

    def unregister(self, bot_id: str) -> None:
        """Removes a bot from active tracking."""
        self.managed_processes.pop(bot_id, None)

    def mark_manual_stop(self, bot_id: str) -> None:
        """Flags that this bot was intentionally stopped to suppress crash alerts."""
        self.manual_stop.add(bot_id)

    def clear_manual_stop(self, bot_id: str) -> None:
        """Clears the manual stop flag once a bot is verified gone or restarted."""
        self.manual_stop.discard(bot_id)

    # Known runtime executables for bots to filter out unrelated OS/system processes fast
    RUNTIME_EXECUTABLES = ("python", "java", "node", "pypy", "uv", "uvicorn")

    def discover_processes(self, bots: Dict[str, BotConfig]) -> int:
        """Scans running system processes to find and attach to any already-running bots.
        
        Optimized with fast executable name filtering to prevent expensive OS syscalls on unrelated processes.
        """
        found_count = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = (proc.info.get('name') or '').lower()
                if not any(name.startswith(exe) for exe in self.RUNTIME_EXECUTABLES):
                    continue

                cmdline = proc.cmdline()
                cwd = proc.cwd()
                if not cmdline or not cwd or len(cmdline) < 2:
                    continue

                cmd_str = " ".join(cmdline).lower()
                norm_cwd = os.path.normpath(cwd).lower()

                for bot_id, bot_cfg in bots.items():
                    if bot_id in self.managed_processes:
                        continue

                    if not bot_cfg.cmd or not bot_cfg.path:
                        continue

                    target_parts = bot_cfg.cmd.lower().split()
                    if not target_parts:
                        continue

                    target_args = " ".join(target_parts[1:]) if len(target_parts) > 1 else target_parts[0]
                    path_match = is_subpath_or_equal(cwd, bot_cfg.path)
                    cmd_match = target_args in cmd_str

                    if cmd_match and path_match:
                        self.managed_processes[bot_id] = proc
                        log.info(f"[ProcessTracker] Connected to existing bot: {bot_cfg.name} (PID: {proc.pid})")
                        found_count += 1
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as e:
                log.debug(f"[ProcessTracker] Error during process discovery: {e}")
                continue
        return found_count

    def get_stats(self, bot_id: str, bot_cfg: Optional[BotConfig] = None, all_bots: Optional[Dict[str, BotConfig]] = None) -> Optional[Dict[str, Any]]:
        """Returns CPU %, RAM MB, Uptime seconds, PID, and disk I/O for a tracked bot."""
        process = self.managed_processes.get(bot_id)

        # Proactive discovery if process is missing or dead
        if not process or not self.is_running(bot_id):
            if all_bots:
                self.discover_processes(all_bots)
                process = self.managed_processes.get(bot_id)

        if not process or not self.is_running(bot_id):
            return None

        try:
            with process.oneshot():
                cpu = process.cpu_percent()
                ram_mb = process.memory_info().rss / (1024 * 1024)
                create_time = process.create_time()
                uptime_sec = datetime.datetime.now().timestamp() - create_time

                try:
                    io = process.io_counters()
                    disk_mb = (io.read_bytes + io.write_bytes) / (1024 * 1024)
                except (psutil.AccessDenied, AttributeError, psutil.NoSuchProcess):
                    disk_mb = None

            return {
                "cpu": cpu,
                "ram_mb": ram_mb,
                "uptime_sec": uptime_sec,
                "pid": process.pid,
                "disk_mb": disk_mb
            }
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            self.unregister(bot_id)
            return None
        except psutil.AccessDenied:
            return None
        except Exception as e:
            log.debug(f"[ProcessTracker] Unexpected error reading stats for {bot_id}: {e}")
            return None

    def fetch_unexpected_stops(self, bots: Dict[str, BotConfig], spawner: Optional['IProcessSpawner'] = None) -> List[Tuple[str, BotConfig]]:
        """Identifies bots that have unexpectedly terminated or crashed."""
        stopped_bots = []

        for bot_id, bot_cfg in bots.items():
            process = self.managed_processes.get(bot_id)
            systemd_service = bot_cfg.systemd_service

            # Systemd check (Linux)
            if systemd_service and os.name == 'posix' and spawner:
                state = spawner.get_systemd_state(systemd_service)
                if state == "active":
                    if not process or not self.is_running(bot_id):
                        pid = spawner.get_systemd_pid(systemd_service)
                        if pid:
                            self.register(bot_id, pid)
                elif state in ["inactive", "failed"]:
                    if bot_id not in self.manual_stop:
                        stopped_bots.append((bot_id, bot_cfg))
                    self.unregister(bot_id)
                continue

            # Standard process check
            if process:
                is_alive = False
                try:
                    is_alive = process.is_running() and process.status() != psutil.STATUS_ZOMBIE
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    is_alive = False

                if not is_alive:
                    if bot_id not in self.manual_stop:
                        stopped_bots.append((bot_id, bot_cfg))
                    self.unregister(bot_id)

            if bot_id in self.manual_stop:
                if not process or not self.is_running(bot_id):
                    self.manual_stop.remove(bot_id)

        return stopped_bots
