import os
import psutil
import datetime
from typing import Dict, Any, Tuple, Optional
from core.config.models import AppConfig
from core.system.process_tracker import ProcessTracker
from core.system.metrics_collector import MetricsCollector
from core.services.i18n_service import LocalizationService
from core.utils import get_feedback

class TelemetryService:
    """Aggregates system, process, log file, and database telemetry into structured status payloads."""
    def __init__(
        self,
        config: AppConfig,
        tracker: ProcessTracker,
        metrics_collector: MetricsCollector,
        i18n: LocalizationService,
        start_time: Optional[datetime.datetime] = None,
    ):
        self.config = config
        self.tracker = tracker
        self.metrics_collector = metrics_collector
        self.i18n = i18n
        self.start_time = start_time or datetime.datetime.now()

    def format_uptime(self, uptime_sec: float) -> str:
        """Formats uptime in seconds into localized human-readable string."""
        if uptime_sec > 86400:
            return get_feedback(self.i18n, "uptime_days", d=int(uptime_sec / 86400))
        elif uptime_sec > 3600:
            return get_feedback(self.i18n, "uptime_hours", h=int(uptime_sec / 3600))
        return get_feedback(self.i18n, "uptime_minutes", m=int(uptime_sec / 60))

    def get_log_size(self, bot_path: str, log_filename: str) -> str:
        """Calculates human-readable log size in MB or KB."""
        try:
            log_file_path = os.path.join(bot_path, log_filename)
            if os.path.exists(log_file_path):
                size_bytes = os.path.getsize(log_file_path)
                if size_bytes > 1024 * 1024:
                    return f"{size_bytes / (1024 * 1024):.1f} MB"
                return f"{size_bytes / 1024:.1f} KB"
        except Exception:
            pass
        return "N/A"

    def get_db_sizes(self, bot_path: str, db_filenames: list[str]) -> Dict[str, str]:
        """Calculates file sizes of all monitored SQLite database files."""
        db_sizes = {}
        if not db_filenames:
            return db_sizes

        for db_file in db_filenames:
            try:
                db_path = os.path.join(bot_path, db_file)
                if os.path.exists(db_path):
                    db_bytes = os.path.getsize(db_path)
                    if db_bytes > 1024 * 1024:
                        db_sizes[db_file] = f"{db_bytes / (1024 * 1024):.1f} MB"
                    else:
                        db_sizes[db_file] = f"{db_bytes / 1024:.1f} KB"
            except Exception:
                pass
        return db_sizes

    def collect_manager_metrics(self, git_behind_status: Optional[Dict[str, bool]] = None) -> Dict[str, Any]:
        """Gathers Manager process and host system statistics."""
        current_proc = psutil.Process()
        with current_proc.oneshot():
            self_cpu = current_proc.cpu_percent()
            self_ram_mb = current_proc.memory_info().rss / 1024 / 1024

        uptime_sec = (datetime.datetime.now() - self.start_time).total_seconds()
        uptime_str = self.format_uptime(uptime_sec)

        sys_metrics = self.metrics_collector.get_system_metrics()
        host_uptime_sec = sys_metrics.get("host_uptime_sec", 0)
        host_uptime_str = self.format_uptime(host_uptime_sec)

        default_branch = self.config.bot_settings.git_branch

        behind_map = git_behind_status or {}
        has_update = behind_map.get("manager", False)

        return {
            "cpu": self_cpu,
            "ram": self_ram_mb,
            "uptime": uptime_str,
            "branch": default_branch,
            "os": sys_metrics.get("os", "Unknown"),
            "sys_cpu_free": sys_metrics.get("sys_cpu_free", 0),
            "sys_ram_free": sys_metrics.get("sys_ram_free", 0),
            "sys_disk_free": sys_metrics.get("sys_disk_free", 0),
            "swap": sys_metrics.get("swap", 0),
            "host_uptime": host_uptime_str,
            "net": sys_metrics.get("net", "N/A"),
            "has_update": has_update,
        }

    def collect_bots_metrics(self, git_behind_status: Optional[Dict[str, bool]] = None) -> Dict[str, Any]:
        """Gathers telemetry for all configured child bots."""
        bots_stats = {}
        behind_map = git_behind_status or {}

        for bot_id, bot in self.config.bots.items():
            stats = self.tracker.get_stats(bot_id, bot, self.config.bots)
            log_size_str = self.get_log_size(bot.path, bot.log)
            db_sizes = self.get_db_sizes(bot.path, bot.db_files)

            bot_entry = {
                "name": bot.name,
                "path": bot.path,
                "is_running": False,
                "log_size": log_size_str,
                "db_sizes": db_sizes,
                "has_update": behind_map.get(bot_id, False),
            }

            if stats:
                bot_entry["is_running"] = True
                b_uptime_str = self.format_uptime(stats["uptime_sec"])
                status_text = get_feedback(self.i18n, "status_running")
                bot_entry.update({
                    "status": status_text,
                    "uptime": b_uptime_str,
                    "pid": stats["pid"],
                    "cpu": stats["cpu"],
                    "ram": stats["ram_mb"],
                })
            else:
                bot_entry["status"] = get_feedback(self.i18n, "status_stopped")

            bots_stats[bot_id] = bot_entry

        return bots_stats

    def get_status_snapshot(self, git_behind_status: Optional[Dict[str, bool]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Returns complete (manager_stats, bots_stats) tuple ready for UI presentation."""
        manager_stats = self.collect_manager_metrics(git_behind_status)
        bots_stats = self.collect_bots_metrics(git_behind_status)
        return manager_stats, bots_stats

__all__ = ["TelemetryService"]
