import datetime
from core.config.config_repository import ConfigRepository
from core.config.state_repository import StateRepository
from core.config.models import AppConfig
from core.system.metrics_collector import MetricsCollector
from core.system.process_tracker import ProcessTracker
from core.services.i18n_service import LocalizationService
from core.services.telemetry_service import TelemetryService
from core.utils import get_feedback

def test_config_repository_corrupt_json_fallback(tmp_path):
    corrupt_file = tmp_path / "broken_config.json"
    corrupt_file.write_text("{ this is not valid json! }", encoding="utf-8")

    repo = ConfigRepository(str(corrupt_file))
    # Should safely fallback to empty AppConfig without crashing
    assert repo.app_config is not None
    assert repo.app_config.guild_id is None
    assert repo.app_config.bots == {}

def test_state_repository_corrupt_json_fallback(tmp_path):
    corrupt_file = tmp_path / "broken_state.json"
    corrupt_file.write_text("<<< invalid >>>", encoding="utf-8")

    repo = StateRepository(str(corrupt_file))
    assert repo.get("status_message_id") is None

    # Saving over corrupt file works cleanly
    repo.set("status_message_id", "recovered_123")
    assert repo.get("status_message_id") == "recovered_123"

def test_metrics_collector_zero_dt_bandwidth():
    collector = MetricsCollector()
    collector.last_net_time = collector.last_net_time  # same timestamp
    down, up, net_str = collector.calculate_network_speed()
    assert down >= 0.0
    assert up >= 0.0
    assert "↓" in net_str and "↑" in net_str

def test_get_feedback_missing_interpolation_key():
    service = LocalizationService("hu")
    # Calling with unexpected key should not crash
    res = get_feedback(service, "uptime_days")
    assert "napja" in res

def test_get_feedback_unicode_special_chars():
    service = LocalizationService("hu")
    res = get_feedback(service, "restart_success", name="Bot with 🤖 & äöü!?", pid=123)
    assert "Bot with 🤖 & äöü!?" in res
    assert "123" in res

def test_telemetry_service_empty_bots():
    app_cfg = AppConfig(bots={})
    service = TelemetryService(
        config=app_cfg,
        tracker=ProcessTracker(),
        metrics_collector=MetricsCollector(),
        i18n=LocalizationService("hu"),
        start_time=datetime.datetime.now()
    )
    bots_stats = service.collect_bots_metrics()
    assert bots_stats == {}
