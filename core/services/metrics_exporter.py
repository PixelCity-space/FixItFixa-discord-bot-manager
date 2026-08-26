import datetime
from typing import Dict, Any, Optional

class MetricsExporter:
    """Exports application and bot telemetry in Prometheus format and structured JSON snapshots."""

    @staticmethod
    def to_prometheus(manager_metrics: Dict[str, Any], bots_metrics: Dict[str, Any]) -> str:
        """Generates Prometheus-formatted metrics text suitable for scraping by Prometheus or Grafana Agent."""
        lines = []

        def add_metric(metric_name: str, metric_type: str, help_text: str, samples: list):
            lines.append(f"# HELP {metric_name} {help_text}")
            lines.append(f"# TYPE {metric_name} {metric_type}")
            for labels, value in samples:
                if labels:
                    lbl_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
                    lines.append(f"{metric_name}{{{lbl_str}}} {value}")
                else:
                    lines.append(f"{metric_name} {value}")

        # Manager metrics
        cpu = manager_metrics.get("cpu", 0.0)
        ram = manager_metrics.get("ram", 0.0)
        sys_cpu_free = manager_metrics.get("sys_cpu_free", 0.0)
        sys_ram_free = manager_metrics.get("sys_ram_free", 0.0)
        sys_disk_free = manager_metrics.get("sys_disk_free", 0.0)

        add_metric("fixitfixa_manager_cpu_percent", "gauge", "Manager CPU usage percentage", [({}, cpu)])
        add_metric("fixitfixa_manager_ram_mb", "gauge", "Manager RAM usage in MB", [({}, ram)])
        add_metric("fixitfixa_system_cpu_free_percent", "gauge", "Host system free CPU percentage", [({}, sys_cpu_free)])
        add_metric("fixitfixa_system_ram_free_mb", "gauge", "Host system free RAM in MB", [({}, sys_ram_free)])
        add_metric("fixitfixa_system_disk_free_gb", "gauge", "Host system free Disk in GB", [({}, sys_disk_free)])

        # Bots metrics
        running_samples = []
        bot_cpu_samples = []
        bot_ram_samples = []

        for bot_id, bdata in bots_metrics.items():
            name = bdata.get("name", bot_id)
            is_running = 1 if bdata.get("is_running") else 0
            labels = {"bot_id": bot_id, "name": name}
            running_samples.append((labels, is_running))

            if is_running:
                bot_cpu = bdata.get("cpu", 0.0)
                bot_ram = bdata.get("ram", 0.0)
                bot_cpu_samples.append((labels, bot_cpu))
                bot_ram_samples.append((labels, bot_ram))

        add_metric("fixitfixa_bot_running", "gauge", "Bot running status (1 = running, 0 = stopped)", running_samples)
        if bot_cpu_samples:
            add_metric("fixitfixa_bot_cpu_percent", "gauge", "Bot CPU usage percentage", bot_cpu_samples)
        if bot_ram_samples:
            add_metric("fixitfixa_bot_ram_mb", "gauge", "Bot RAM usage in MB", bot_ram_samples)

        return "\n".join(lines) + "\n"

    @staticmethod
    def to_json_snapshot(manager_metrics: Dict[str, Any], bots_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Produces a structured JSON observability payload."""
        total_bots = len(bots_metrics)
        running_bots = sum(1 for b in bots_metrics.values() if b.get("is_running"))

        return {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "healthy" if running_bots == total_bots else "degraded",
            "summary": {
                "total_bots": total_bots,
                "running_bots": running_bots,
                "stopped_bots": total_bots - running_bots
            },
            "manager": manager_metrics,
            "bots": bots_metrics
        }

__all__ = ["MetricsExporter"]
