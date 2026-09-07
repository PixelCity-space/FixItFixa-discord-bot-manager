import datetime
from typing import Any


class MetricsExporter:
    """Exports application and bot telemetry in Prometheus format and structured JSON snapshots."""

    @staticmethod
    def to_prometheus(manager_metrics: dict[str, Any], bots_metrics: dict[str, Any]) -> str:
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
        add_metric(
            "fixitfixa_system_cpu_free_percent", "gauge", "Host system free CPU percentage", [({}, sys_cpu_free)]
        )
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
    def to_json_snapshot(manager_metrics: dict[str, Any], bots_metrics: dict[str, Any]) -> dict[str, Any]:
        """Produces a structured JSON observability payload."""
        total_bots = len(bots_metrics)
        running_bots = sum(1 for b in bots_metrics.values() if b.get("is_running"))

        return {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "healthy" if running_bots == total_bots else "degraded",
            "summary": {
                "total_bots": total_bots,
                "running_bots": running_bots,
                "stopped_bots": total_bots - running_bots,
            },
            "manager": manager_metrics,
            "bots": bots_metrics,
        }


class MetricsServer:
    """Non-blocking HTTP server providing /metrics Prometheus scraping, /health checks, and /api/status endpoints."""

    def __init__(
        self,
        telemetry_service: Any = None,
        host: str = "0.0.0.0",
        port: int = 9090,
        enabled: bool = True,
    ):
        self.telemetry_service = telemetry_service
        self.host = host
        self.port = port
        self.enabled = enabled
        self._app: Any = None
        self._runner: Any = None
        self._site: Any = None
        self._is_running: bool = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    async def handle_metrics(self, request: Any) -> Any:
        """Prometheus scrape endpoint."""
        from aiohttp import web

        try:
            if self.telemetry_service:
                mgr, bots = await self.telemetry_service.get_status_snapshot_async()
            else:
                mgr, bots = {}, {}
            prom_text = MetricsExporter.to_prometheus(mgr, bots)
            return web.Response(text=prom_text, content_type="text/plain; version=0.0.4", charset="utf-8")
        except Exception as e:
            from core.logger import log

            log.error(f"[MetricsServer] Error rendering /metrics: {e}")
            return web.Response(text=f"# Error rendering metrics: {e}\n", status=500, content_type="text/plain")

    async def handle_health(self, request: Any) -> Any:
        """Health check endpoint."""
        from aiohttp import web

        return web.Response(text="OK\n", content_type="text/plain", charset="utf-8")

    async def handle_status(self, request: Any) -> Any:
        """Structured JSON status endpoint."""
        from aiohttp import web

        try:
            if self.telemetry_service:
                mgr, bots = await self.telemetry_service.get_status_snapshot_async()
            else:
                mgr, bots = {}, {}
            snapshot = MetricsExporter.to_json_snapshot(mgr, bots)
            return web.json_response(snapshot)
        except Exception as e:
            from core.logger import log

            log.error(f"[MetricsServer] Error rendering /api/status: {e}")
            return web.json_response({"status": "error", "error": str(e)}, status=500)

    async def handle_root(self, request: Any) -> Any:
        """Root landing page linking to available endpoints."""
        from aiohttp import web

        html = (
            "<html><head><title>FixItFixa Observability</title></head><body>"
            "<h1>FixItFixa Observability Engine</h1>"
            "<ul>"
            '<li><a href="/metrics">/metrics</a> - Prometheus scrape endpoint</li>'
            '<li><a href="/health">/health</a> - Liveness & Health check</li>'
            '<li><a href="/api/status">/api/status</a> - JSON Status Snapshot</li>'
            "</ul></body></html>\n"
        )
        return web.Response(text=html, content_type="text/html", charset="utf-8")

    async def start(self) -> bool:
        """Starts the aiohttp web server asynchronously."""
        from core.logger import log

        if not self.enabled:
            log.info("[MetricsServer] Prometheus HTTP server is disabled in settings.")
            return False

        if self._is_running:
            return True

        try:
            from aiohttp import web

            self._app = web.Application()
            self._app.router.add_get("/", self.handle_root)
            self._app.router.add_get("/metrics", self.handle_metrics)
            self._app.router.add_get("/health", self.handle_health)
            self._app.router.add_get("/api/status", self.handle_status)

            self._runner = web.AppRunner(self._app)
            await self._runner.setup()
            self._site = web.TCPSite(self._runner, self.host, self.port)
            await self._site.start()
            self._is_running = True
            log.info(f"[MetricsServer] Prometheus HTTP server listening on http://{self.host}:{self.port}/metrics")
            return True
        except OSError as e:
            import contextlib

            log.warning(f"[MetricsServer] Could not bind Prometheus HTTP server on {self.host}:{self.port}: {e}")
            if self._runner:
                with contextlib.suppress(Exception):
                    await self._runner.cleanup()
                self._runner = None
            return False
        except Exception as e:
            log.error(f"[MetricsServer] Unexpected error starting Prometheus HTTP server: {e}")
            return False

    async def stop(self) -> None:
        """Stops the aiohttp web server gracefully."""
        from core.logger import log

        if self._runner:
            try:
                await self._runner.cleanup()
                log.info("[MetricsServer] Prometheus HTTP server stopped.")
            except Exception as e:
                log.debug(f"[MetricsServer] Error during runner cleanup: {e}")
            finally:
                self._runner = None
                self._site = None
                self._app = None
                self._is_running = False


__all__ = ["MetricsExporter", "MetricsServer"]
