import pytest
from core.container import ServiceContainer
from core.config.config_repository import ConfigRepository
from core.config.state_repository import StateRepository
from core.services.bot_lifecycle_service import BotLifecycleService
from core.services.update_service import UpdateService
from core.services.health_service import HealthService
from core.services.telemetry_service import TelemetryService
from core.services.i18n_service import LocalizationService
from core.system.process_spawner import ProcessSpawner
from core.system.process_tracker import ProcessTracker
from core.system.git_client import GitClient
from core.system.log_rotator import LogRotator
from core.system.metrics_collector import MetricsCollector
from bot.client import BotManager

def test_service_container_manual_registration_and_get():
    container = ServiceContainer()
    assert not container.has("my_service")

    dummy_service = {"name": "TestService"}
    container.register("my_service", dummy_service)

    assert container.has("my_service")
    assert container.get("my_service") == dummy_service
    assert container.get("non_existing") is None
    assert container.get("non_existing", "default_val") == "default_val"

def test_service_container_create_default(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text('{"settings": {"guild_id": "1234567890"}, "bots": {}}', encoding="utf-8")
    
    state_file = tmp_path / "state.json"
    state_file.write_text('{}', encoding="utf-8")

    container = ServiceContainer.create_default(str(tmp_path))

    assert isinstance(container.config_repo, ConfigRepository)
    assert isinstance(container.state_repo, StateRepository)
    assert isinstance(container.i18n, LocalizationService)
    assert isinstance(container.spawner, ProcessSpawner)
    assert isinstance(container.tracker, ProcessTracker)
    assert isinstance(container.metrics_collector, MetricsCollector)
    assert isinstance(container.git_client, GitClient)
    assert isinstance(container.log_rotator, LogRotator)
    assert isinstance(container.lifecycle_service, BotLifecycleService)
    assert isinstance(container.update_service, UpdateService)
    assert isinstance(container.health_service, HealthService)
    assert isinstance(container.telemetry_service, TelemetryService)

def test_bot_manager_initializes_with_service_container(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text('{"settings": {"guild_id": "999888777"}, "bots": {}}', encoding="utf-8")
    state_file = tmp_path / "state.json"
    state_file.write_text('{}', encoding="utf-8")

    bot = BotManager(base_dir=str(tmp_path))
    assert isinstance(bot.container, ServiceContainer)
    assert bot.guild_id == "999888777"
    assert bot.lifecycle_service is bot.container.lifecycle_service
    assert bot.update_service is bot.container.update_service
    assert bot.health_service is bot.container.health_service
    assert bot.telemetry_service is bot.container.telemetry_service
