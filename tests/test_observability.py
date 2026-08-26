import json
import logging
import pytest
from core.logger import (
    JsonFormatter,
    CorrelationFilter,
    get_correlation_id,
    set_correlation_id,
    trace_context,
    setup_discord_logging
)
from core.services.metrics_exporter import MetricsExporter

def test_json_formatter_outputs_valid_json():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="TestLogger",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Bot cluster restarted successfully",
        args=(),
        exc_info=None
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
        exc_info=exc_info
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
    manager_metrics = {
        "cpu": 1.5,
        "ram": 85.0,
        "sys_cpu_free": 65.0,
        "sys_ram_free": 8192.0,
        "sys_disk_free": 250.0
    }
    bots_metrics = {
        "bot_1": {"name": "Iris", "is_running": True, "cpu": 0.8, "ram": 42.0},
        "bot_2": {"name": "Ava", "is_running": False}
    }

    prom_text = MetricsExporter.to_prometheus(manager_metrics, bots_metrics)

    assert "fixitfixa_manager_cpu_percent 1.5" in prom_text
    assert "fixitfixa_manager_ram_mb 85.0" in prom_text
    assert 'fixitfixa_bot_running{bot_id="bot_1",name="Iris"} 1' in prom_text
    assert 'fixitfixa_bot_running{bot_id="bot_2",name="Ava"} 0' in prom_text
    assert 'fixitfixa_bot_cpu_percent{bot_id="bot_1",name="Iris"} 0.8' in prom_text

def test_json_metrics_snapshot():
    manager_metrics = {"cpu": 2.0, "ram": 90.0}
    bots_metrics = {
        "bot_1": {"name": "Iris", "is_running": True},
        "bot_2": {"name": "Ava", "is_running": True}
    }

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
