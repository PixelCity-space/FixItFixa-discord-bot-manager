import os
import psutil
import datetime
from typing import Dict, List, Tuple, Optional, Any
from core.logger import log
from core.config.models import BotConfig

class ProcessTracker:
    """Tracks active processes, collects bot metrics, and detects crashes/unexpected stops."""
    def __init__(self):
        self.managed_processes: Dict[str, psutil.Process] = {}
        self.manual_stop: set = set()

    def is_running(self, bot_id: str) -> bool:
        """Checks if a bot's process is currently alive."""
        process = self.managed_processes.get(bot_id)
        return bool(process and process.is_running())

    def register(self, bot_id: str, pid: int) -> None:
        """Registers a newly started PID under tracking."""
        try:
            self.managed_processes[bot_id] = psutil.Process(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def unregister(self, bot_id: str) -> None:
        """Removes a bot from active tracking."""
        self.managed_processes.pop(bot_id, None)

    def mark_manual_stop(self, bot_id: str) -> None:
        """Flags that this bot was intentionally stopped to suppress crash alerts."""
        self.manual_stop.add(bot_id)

    def clear_manual_stop(self, bot_id: str) -> None:
        """Clears the manual stop flag once a bot is verified gone or restarted."""
        self.manual_stop.discard(bot_id)

    def discover_processes(self, bots: Dict[str, BotConfig]) -> int:
        """Scans running system processes to find and attach to any already-running bots."""
        found_count = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd']):
            try:
                cmdline = proc.info.get('cmdline')
                cwd = proc.info.get('cwd')
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
                    target_path = os.path.normpath(bot_cfg.path).lower()

                    path_match = (target_path == norm_cwd) or (norm_cwd.endswith(target_path.split(":")[-1].replace("\\", "/").strip("/").lower()))
                    cmd_match = target_args in cmd_str

                    if cmd_match and path_match:
                        self.managed_processes[bot_id] = psutil.Process(proc.info['pid'])
                        log.info(f"[ProcessTracker] Connected to existing bot: {bot_cfg.name} (PID: {proc.info['pid']})")
                        found_count += 1
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return found_count

    def get_stats(self, bot_id: str, bot_cfg: Optional[BotConfig] = None, all_bots: Optional[Dict[str, BotConfig]] = None) -> Optional[Dict[str, Any]]:
        """Returns CPU %, RAM MB, Uptime seconds, PID, and disk I/O for a tracked bot."""
        process = self.managed_processes.get(bot_id)

        # Proactive discovery if process is missing or dead
        if not process or not process.is_running():
            if all_bots:
                self.discover_processes(all_bots)
                process = self.managed_processes.get(bot_id)

        if not process or not process.is_running():
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
                except (psutil.AccessDenied, AttributeError):
                    disk_mb = None

            return {
                "cpu": cpu,
                "ram_mb": ram_mb,
                "uptime_sec": uptime_sec,
                "pid": process.pid,
                "disk_mb": disk_mb
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def fetch_unexpected_stops(self, bots: Dict[str, BotConfig], spawner=None) -> List[Tuple[str, BotConfig]]:
        """Identifies bots that have unexpectedly terminated or crashed."""
        stopped_bots = []

        for bot_id, bot_cfg in bots.items():
            process = self.managed_processes.get(bot_id)
            systemd_service = bot_cfg.systemd_service

            # Systemd check (Linux)
            if systemd_service and os.name == 'posix' and spawner:
                state = spawner.get_systemd_state(systemd_service)
                if state == "active":
                    if not process or not process.is_running():
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
                if not process.is_running():
                    if bot_id not in self.manual_stop:
                        stopped_bots.append((bot_id, bot_cfg))
                    self.unregister(bot_id)

            if bot_id in self.manual_stop:
                if not process or not process.is_running():
                    self.manual_stop.remove(bot_id)

        return stopped_bots
