import asyncio
import datetime
from unittest.mock import MagicMock

from bot.cogs.monitoring_cog import MonitoringCog
from bot.ui.views.status_view import ModernStatusView
from core.config.models import AppConfig, BotConfig
from core.services.i18n_service import LocalizationService
from core.services.telemetry_service import TelemetryService
from core.system.metrics_collector import MetricsCollector
from core.system.process_tracker import ProcessTracker


def test_e2e_telemetry_to_status_view_rendering(tmp_path):
    # Setup test bot with temporary log file
    log_file = tmp_path / "bot1.log"
    log_file.write_text("2026-08-26 Bot started\n2026-08-26 Ready.", encoding="utf-8")

    bot1 = BotConfig(id="bot_live", name="Live Bot", path=str(tmp_path), cmd="python app.py", log=str(log_file))
    app_cfg = AppConfig(bots={"bot_live": bot1})

    tracker = ProcessTracker()
    metrics_collector = MetricsCollector()
    i18n = LocalizationService("hu")

    telemetry_service = TelemetryService(
        config=app_cfg,
        tracker=tracker,
        metrics_collector=metrics_collector,
        i18n=i18n,
        start_time=datetime.datetime.now(),
    )

    # 1. Telemetry snapshot generation
    mgr_stats, bots_stats = telemetry_service.get_status_snapshot()

    assert mgr_stats["cpu"] is not None
    assert mgr_stats["ram"] is not None
    assert "bot_live" in bots_stats
    assert bots_stats["bot_live"]["log_size"] != "0B"

    # 2. ModernStatusView construction
    bot_manager_mock = MagicMock()
    bot_manager_mock.manager_name = "FixItFixa"
    bot_manager_mock.ui_settings = {}

    view = ModernStatusView(bot_manager_mock, i18n, mgr_stats, bots_stats, current_page=0)
    assert view is not None
    assert len(view.children) >= 1


def test_e2e_telemetry_cluster_view_rendering(tmp_path):
    cluster_dir = tmp_path / "cluster"
    cluster_dir.mkdir()

    b1 = BotConfig(id="w1", name="Worker 1", path=str(cluster_dir), cmd="python w1.py")
    b2 = BotConfig(id="w2", name="Worker 2", path=str(cluster_dir), cmd="python w2.py")
    app_cfg = AppConfig(bots={"w1": b1, "w2": b2})

    telemetry_service = TelemetryService(
        config=app_cfg,
        tracker=ProcessTracker(),
        metrics_collector=MetricsCollector(),
        i18n=LocalizationService("hu"),
        start_time=datetime.datetime.now(),
    )

    mgr_stats, bots_stats = telemetry_service.get_status_snapshot()
    assert "w1" in bots_stats
    assert "w2" in bots_stats

    bot_mgr = MagicMock()
    bot_mgr.manager_name = "FixItFixa"
    bot_mgr.ui_settings = {}

    view = ModernStatusView(bot_mgr, LocalizationService("hu"), mgr_stats, bots_stats, current_page=0)
    assert view is not None


def test_e2e_telemetry_sqlite_db_sizes_reporting(tmp_path):
    db_file1 = tmp_path / "data.db"
    db_file1.write_bytes(b"SQLite format 3\x00" + b"\x00" * 4096)

    bot = BotConfig(id="db_bot", name="Database Bot", path=str(tmp_path), cmd="python db.py", db_files=["data.db"])
    app_cfg = AppConfig(bots={"db_bot": bot})

    telemetry_service = TelemetryService(
        config=app_cfg,
        tracker=ProcessTracker(),
        metrics_collector=MetricsCollector(),
        i18n=LocalizationService("hu"),
        start_time=datetime.datetime.now(),
    )

    mgr_stats, bots_stats = telemetry_service.get_status_snapshot()
    assert "db_bot" in bots_stats
    assert "data.db" in bots_stats["db_bot"]["db_sizes"]
    assert "KB" in bots_stats["db_bot"]["db_sizes"]["data.db"] or "B" in bots_stats["db_bot"]["db_sizes"]["data.db"]


def test_e2e_monitoring_cog_snapshot_integration(tmp_path):
    async def run():
        bot1 = BotConfig(id="b_mon", name="Monitored Bot", path=str(tmp_path), cmd="python app.py")
        app_cfg = AppConfig(bots={"b_mon": bot1})

        tracker = ProcessTracker()
        metrics = MetricsCollector()
        i18n = LocalizationService("hu")
        telemetry = TelemetryService(
            config=app_cfg, tracker=tracker, metrics_collector=metrics, i18n=i18n, start_time=datetime.datetime.now()
        )

        bot_mock = MagicMock()
        bot_mock.telemetry_service = telemetry

        cog = MonitoringCog(bot_mock)

        mgr_data, bots_data = cog.get_status_data()
        assert mgr_data is not None
        assert "b_mon" in bots_data

    asyncio.run(run())
