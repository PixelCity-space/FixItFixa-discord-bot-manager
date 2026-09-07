import datetime
from unittest.mock import patch

import psutil
import pytest

from core.config.models import AppConfig, BotConfig
from core.services.i18n_service import LocalizationService
from core.services.telemetry_service import TelemetryService
from core.system.metrics_collector import MetricsCollector
from core.system.process_tracker import ProcessTracker


@pytest.fixture
def telemetry_service(tmp_path):
    app_cfg = AppConfig(
        bots={
            "b1": BotConfig(
                id="b1", name="Bot Alpha", path=str(tmp_path), cmd="python app.py", log="app.log", db_files=["data.db"]
            )
        }
    )
    tracker = ProcessTracker()
    metrics = MetricsCollector()
    i18n = LocalizationService("hu")
    return TelemetryService(
        config=app_cfg, tracker=tracker, metrics_collector=metrics, i18n=i18n, start_time=datetime.datetime.now()
    )


def test_telemetry_format_uptime(telemetry_service):
    # Minutes
    m_res = telemetry_service.format_uptime(120)
    assert "2" in m_res

    # Hours
    h_res = telemetry_service.format_uptime(7200)
    assert "2" in h_res

    # Days
    d_res = telemetry_service.format_uptime(100000)
    assert "1" in d_res

    # Negative uptime drift is sanitized to 0
    neg_res = telemetry_service.format_uptime(-15)
    assert "0" in neg_res


def test_telemetry_get_log_size(telemetry_service, tmp_path):
    log_file = tmp_path / "app.log"
    log_file.write_text("A" * 5000, encoding="utf-8")
    res_kb = telemetry_service.get_log_size(str(tmp_path), "app.log")
    assert "KB" in res_kb

    log_file.write_text("B" * (2 * 1024 * 1024), encoding="utf-8")
    res_mb = telemetry_service.get_log_size(str(tmp_path), "app.log")
    assert "MB" in res_mb

    missing_res = telemetry_service.get_log_size(str(tmp_path), "missing.log")
    assert missing_res == "N/A"

    # None and empty checks
    assert telemetry_service.get_log_size(None, "app.log") == "N/A"
    assert telemetry_service.get_log_size(str(tmp_path), None) == "N/A"
    assert telemetry_service.get_log_size("", "") == "N/A"


def test_telemetry_get_db_sizes(telemetry_service, tmp_path):
    db1 = tmp_path / "main.db"
    db1.write_bytes(b"\x00" * 4096)
    db2 = tmp_path / "large.db"
    db2.write_bytes(b"\x00" * (3 * 1024 * 1024))

    sizes = telemetry_service.get_db_sizes(str(tmp_path), ["main.db", "large.db", "not_found.db"])
    assert "main.db" in sizes
    assert "KB" in sizes["main.db"]
    assert "large.db" in sizes
    assert "MB" in sizes["large.db"]
    assert "not_found.db" not in sizes

    # None and empty checks
    assert telemetry_service.get_db_sizes(None, ["main.db"]) == {}
    assert telemetry_service.get_db_sizes(str(tmp_path), None) == {}
    assert telemetry_service.get_db_sizes(str(tmp_path), []) == {}


def test_telemetry_collect_manager_metrics(telemetry_service):
    mgr_stats = telemetry_service.collect_manager_metrics({"manager": True})
    assert "cpu" in mgr_stats
    assert "ram" in mgr_stats
    assert "uptime" in mgr_stats
    assert "os" in mgr_stats
    assert "sys_disk_free" in mgr_stats
    assert mgr_stats["has_update"] is True


def test_telemetry_collect_manager_metrics_psutil_exception_fallback(telemetry_service):
    telemetry_service._process = None
    with patch("psutil.Process") as mock_proc:
        mock_proc.side_effect = psutil.AccessDenied()
        mgr_stats = telemetry_service.collect_manager_metrics()
        assert mgr_stats["cpu"] == 0.0
        assert mgr_stats["ram"] == 0.0


def test_telemetry_get_status_snapshot(telemetry_service):
    mgr_stats, bots_stats = telemetry_service.get_status_snapshot()
    assert isinstance(mgr_stats, dict)
    assert isinstance(bots_stats, dict)
    assert "b1" in bots_stats
    assert bots_stats["b1"]["name"] == "Bot Alpha"
    assert bots_stats["b1"]["is_running"] is False


async def test_telemetry_get_status_snapshot_async(telemetry_service):
    mgr_stats, bots_stats = await telemetry_service.get_status_snapshot_async()
    assert isinstance(mgr_stats, dict)
    assert isinstance(bots_stats, dict)
    assert "b1" in bots_stats
    assert bots_stats["b1"]["name"] == "Bot Alpha"


def test_telemetry_running_bot_and_error_branches(telemetry_service, tmp_path):
    from unittest.mock import MagicMock

    # 1. Bot running with stats
    with patch.object(
        telemetry_service.tracker,
        "get_stats",
        return_value={"uptime_sec": 3600, "pid": 1234, "cpu": 2.5, "ram_mb": 45.0},
    ):
        _, bots_stats = telemetry_service.get_status_snapshot()
        assert bots_stats["b1"]["is_running"] is True
        assert bots_stats["b1"]["pid"] == 1234
        assert "cpu" in bots_stats["b1"]

    # 2. get_log_size and get_db_sizes with OSError
    with patch("os.path.exists", return_value=True), patch("os.path.getsize", side_effect=PermissionError("Locked")):
        assert telemetry_service.get_log_size(str(tmp_path), "locked.log") == "N/A"
        assert telemetry_service.get_db_sizes(str(tmp_path), ["locked.db"]) == {}

    # 3. psutil.Process() failure on TelemetryService init
    with patch("psutil.Process", side_effect=RuntimeError("psutil init failed")):
        svc = TelemetryService(
            config=telemetry_service.config,
            tracker=telemetry_service.tracker,
            metrics_collector=telemetry_service.metrics_collector,
            i18n=telemetry_service.i18n,
        )
        assert svc._process is None

    # 4. oneshot raises NoSuchProcess and re-init fallback
    mock_p = MagicMock()
    mock_p.oneshot.side_effect = psutil.NoSuchProcess(pid=999)
    telemetry_service._process = mock_p
    with patch("psutil.Process", side_effect=psutil.AccessDenied()):
        mgr_stats = telemetry_service.collect_manager_metrics()
        assert mgr_stats["cpu"] == 0.0
