import json
import logging

from core.logger import (
    CorrelationFilter,
    JsonFormatter,
    get_correlation_id,
    setup_discord_logging,
    trace_context,
)
from core.services.metrics_exporter import MetricsExporter, MetricsServer


def test_json_formatter_outputs_valid_json():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="TestLogger",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Bot cluster restarted successfully",
        args=(),
        exc_info=None,
    )

    with trace_context("req_abc123"):
        json_output = formatter.format(record)
        data = json.loads(json_output)

        assert data["level"] == "INFO"
        assert data["logger"] == "TestLogger"
        assert data["message"] == "Bot cluster restarted successfully"
        assert data["correlation_id"] == "req_abc123"
        assert "timestamp" in data
        assert data["line"] == 42


def test_json_formatter_handles_exception():
    formatter = JsonFormatter()
    try:
        raise ValueError("Database connection failed")
    except ValueError:
        import sys

        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="DBLogger",
        level=logging.ERROR,
        pathname="db.py",
        lineno=10,
        msg="Critical DB failure",
        args=(),
        exc_info=exc_info,
    )

    json_output = formatter.format(record)
    data = json.loads(json_output)
    assert data["level"] == "ERROR"
    assert "exception" in data
    assert "ValueError: Database connection failed" in data["exception"]


def test_correlation_id_and_trace_context():
    assert get_correlation_id() == ""

    with trace_context("trace_custom_99") as tid:
        assert tid == "trace_custom_99"
        assert get_correlation_id() == "trace_custom_99"

    # Context restored
    assert get_correlation_id() == ""

    # Auto-generated trace ID
    with trace_context() as auto_tid:
        assert auto_tid.startswith("tr_")
        assert get_correlation_id() == auto_tid

    assert get_correlation_id() == ""


def test_correlation_filter_injects_into_log_record():
    c_filter = CorrelationFilter()
    record = logging.LogRecord("App", logging.INFO, "app.py", 1, "test", (), None)

    with trace_context("req_filter_test"):
        c_filter.filter(record)
        assert record.correlation_id == "req_filter_test"
        assert record.corr_prefix == " [req_filter_test]"


def test_prometheus_metrics_export():
    manager_metrics = {"cpu": 1.5, "ram": 85.0, "sys_cpu_free": 65.0, "sys_ram_free": 8192.0, "sys_disk_free": 250.0}
    bots_metrics = {
        "bot_1": {"name": "Iris", "is_running": True, "cpu": 0.8, "ram": 42.0},
        "bot_2": {"name": "Ava", "is_running": False},
    }

    prom_text = MetricsExporter.to_prometheus(manager_metrics, bots_metrics)

    assert "fixitfixa_manager_cpu_percent 1.5" in prom_text
    assert "fixitfixa_manager_ram_mb 85.0" in prom_text
    assert 'fixitfixa_bot_running{bot_id="bot_1",name="Iris"} 1' in prom_text
    assert 'fixitfixa_bot_running{bot_id="bot_2",name="Ava"} 0' in prom_text
    assert 'fixitfixa_bot_cpu_percent{bot_id="bot_1",name="Iris"} 0.8' in prom_text


def test_json_metrics_snapshot():
    manager_metrics = {"cpu": 2.0, "ram": 90.0}
    bots_metrics = {"bot_1": {"name": "Iris", "is_running": True}, "bot_2": {"name": "Ava", "is_running": True}}

    snapshot = MetricsExporter.to_json_snapshot(manager_metrics, bots_metrics)

    assert snapshot["status"] == "healthy"
    assert snapshot["summary"]["total_bots"] == 2
    assert snapshot["summary"]["running_bots"] == 2
    assert snapshot["summary"]["stopped_bots"] == 0
    assert "timestamp" in snapshot


def test_discord_logging_level(tmp_path):
    discord_log = tmp_path / "discord_test.log"
    setup_discord_logging(str(discord_log), 1024 * 1024, 1, level=logging.INFO)
    d_logger = logging.getLogger("discord")
    assert d_logger.level == logging.INFO


async def test_metrics_server_disabled():
    server = MetricsServer(enabled=False)
    started = await server.start()
    assert started is False
    assert server.is_running is False
    await server.stop()


async def test_metrics_server_endpoints():
    class DummyTelemetry:
        async def get_status_snapshot_async(self):
            return {"cpu": 3.5, "ram": 100.0}, {"b1": {"name": "Bot1", "is_running": True, "cpu": 1.0, "ram": 50.0}}

    server = MetricsServer(telemetry_service=DummyTelemetry(), host="127.0.0.1", port=19090, enabled=True)

    # 1. Test handle_metrics
    resp_metrics = await server.handle_metrics(None)
    assert resp_metrics.status == 200
    assert "fixitfixa_manager_cpu_percent 3.5" in resp_metrics.text
    assert "fixitfixa_bot_running" in resp_metrics.text

    # 2. Test handle_health
    resp_health = await server.handle_health(None)
    assert resp_health.status == 200
    assert resp_health.text == "OK\n"

    # 3. Test handle_status
    resp_status = await server.handle_status(None)
    assert resp_status.status == 200
    status_data = json.loads(resp_status.text)
    assert status_data["status"] == "healthy"
    assert status_data["summary"]["running_bots"] == 1

    # 4. Test handle_root
    resp_root = await server.handle_root(None)
    assert resp_root.status == 200
    assert "FixItFixa Observability Engine" in resp_root.text


async def test_metrics_server_error_resilience():
    class BrokenTelemetry:
        async def get_status_snapshot_async(self):
            raise RuntimeError("Database read timeout")

    server = MetricsServer(telemetry_service=BrokenTelemetry(), host="127.0.0.1", port=19091, enabled=True)

    resp_metrics = await server.handle_metrics(None)
    assert resp_metrics.status == 500
    assert "Error rendering metrics" in resp_metrics.text

    resp_status = await server.handle_status(None)
    assert resp_status.status == 500
    err_data = json.loads(resp_status.text)
    assert err_data["status"] == "error"
    assert "Database read timeout" in err_data["error"]


async def test_metrics_server_lifecycle():
    server = MetricsServer(telemetry_service=None, host="127.0.0.1", port=19092, enabled=True)
    started = await server.start()
    assert started is True
    assert server.is_running is True

    # Idempotent start
    assert await server.start() is True

    await server.stop()
    assert server.is_running is False
    assert server._runner is None
