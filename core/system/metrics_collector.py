import datetime
import os
import platform
import shutil
from typing import Any

import psutil

from core.logger import log


class MetricsCollector:
    """Collects system-wide hardware and OS metrics."""

    def __init__(self):
        self.last_net_io = psutil.net_io_counters()
        self.last_net_time = datetime.datetime.now()

    def get_os_info(self) -> str:
        """Determines the operating system pretty name."""
        if os.name == "posix":
            try:
                with open("/etc/os-release") as f:
                    lines = f.readlines()
                    os_info = {}
                    for line in lines:
                        if "=" in line:
                            k, v = line.rstrip().split("=", 1)
                            os_info[k] = v.strip('"')
                    return os_info.get("PRETTY_NAME", platform.system())
            except Exception:
                return f"{platform.system()} {platform.release()}"
        return f"{platform.system()} {platform.release()}"

    @staticmethod
    def format_speed(bytes_per_sec: float) -> str:
        """Formats bytes per second into KB/s, MB/s or GB/s."""
        if bytes_per_sec > 1024 * 1024 * 1024:
            return f"{bytes_per_sec / (1024 * 1024 * 1024):.1f} GB/s"
        elif bytes_per_sec > 1024 * 1024:
            return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
        return f"{bytes_per_sec / 1024:.1f} KB/s"

    def calculate_network_speed(self) -> tuple[float, float, str]:
        """Calculates download and upload bandwidth speeds."""
        now = datetime.datetime.now()
        net_now = psutil.net_io_counters()
        dt = (now - self.last_net_time).total_seconds()

        if dt > 0:
            down_speed = (net_now.bytes_recv - self.last_net_io.bytes_recv) / dt
            up_speed = (net_now.bytes_sent - self.last_net_io.bytes_sent) / dt
        else:
            down_speed, up_speed = 0.0, 0.0

        self.last_net_io = net_now
        self.last_net_time = now

        net_str = f"↓ {self.format_speed(down_speed)} | ↑ {self.format_speed(up_speed)}"
        return down_speed, up_speed, net_str

    def get_system_metrics(self) -> dict[str, Any]:
        """Gathers comprehensive host system metrics."""
        try:
            os_name = self.get_os_info()

            # CPU
            sys_cpu_usage = psutil.cpu_percent(interval=None)
            sys_cpu_free = max(0, 100 - sys_cpu_usage)

            # RAM
            vm = psutil.virtual_memory()
            sys_ram_free = vm.available / (1024 * 1024)

            # Swap
            swap = psutil.swap_memory()
            sys_swap_percent = swap.percent

            # Host Uptime
            boot_time = psutil.boot_time()
            host_uptime_sec = datetime.datetime.now().timestamp() - boot_time

            # Disk Usage (Workspace drive)
            du = shutil.disk_usage(os.path.abspath("."))
            sys_disk_free = du.free / (1024 * 1024 * 1024)

            # Network
            _, _, net_str = self.calculate_network_speed()

            return {
                "os": os_name,
                "sys_cpu_usage": sys_cpu_usage,
                "sys_cpu_free": sys_cpu_free,
                "sys_ram_free": sys_ram_free,
                "sys_disk_free": sys_disk_free,
                "swap": sys_swap_percent,
                "host_uptime_sec": host_uptime_sec,
                "net": net_str,
            }
        except Exception as e:
            log.warning(f"[MetricsCollector] Failed to collect system metrics: {e}")
            return {
                "os": "Unknown",
                "sys_cpu_usage": 0.0,
                "sys_cpu_free": 0.0,
                "sys_ram_free": 0.0,
                "sys_disk_free": 0.0,
                "swap": 0.0,
                "host_uptime_sec": 0.0,
                "net": "Error",
            }
