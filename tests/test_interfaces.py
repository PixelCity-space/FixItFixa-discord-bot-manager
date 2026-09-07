import datetime

from core.config.config_repository import ConfigRepository
from core.config.models import AppConfig, BotConfig
from core.config.state_repository import StateRepository
from core.interfaces import (
    IBotLifecycleService,
    IConfigRepository,
    IGitClient,
    IHealthService,
    ILocalizationService,
    ILogRotator,
    IMetricsCollector,
    IProcessSpawner,
    IProcessTracker,
    IStateRepository,
    ITelemetryService,
    IUpdateService,
)
from core.services.bot_lifecycle_service import BotLifecycleService
from core.services.health_service import HealthService
from core.services.i18n_service import LocalizationService
from core.services.telemetry_service import TelemetryService
from core.services.update_service import UpdateService
from core.system.git_client import GitClient
from core.system.log_rotator import LogRotator
from core.system.metrics_collector import MetricsCollector
from core.system.process_spawner import ProcessSpawner
from core.system.process_tracker import ProcessTracker


def test_system_implementations_satisfy_protocols(tmp_path):
    """Verifies that all concrete system classes satisfy their respective Protocol interfaces."""
    log_rotator = LogRotator()
    assert isinstance(log_rotator, ILogRotator)

    spawner = ProcessSpawner(log_rotator=log_rotator)
    assert isinstance(spawner, IProcessSpawner)

    tracker = ProcessTracker()
    assert isinstance(tracker, IProcessTracker)

    git_client = GitClient()
    assert isinstance(git_client, IGitClient)

    metrics_collector = MetricsCollector()
    assert isinstance(metrics_collector, IMetricsCollector)


def test_config_implementations_satisfy_protocols(tmp_path):
    """Verifies that ConfigRepository and StateRepository satisfy repository protocols."""
    config_file = tmp_path / "config.json"
    config_file.write_text("{}", encoding="utf-8")
    config_repo = ConfigRepository(str(config_file))
    assert isinstance(config_repo, IConfigRepository)

    state_file = tmp_path / "state.json"
    state_repo = StateRepository(str(state_file))
    assert isinstance(state_repo, IStateRepository)


def test_services_implementations_satisfy_protocols():
    """Verifies that all domain service classes satisfy service protocols."""
    i18n = LocalizationService("hu")
    assert isinstance(i18n, ILocalizationService)

    app_cfg = AppConfig(bots={"b1": BotConfig(id="b1", name="Bot 1", path="C:\\test", cmd="python bot.py")})
    spawner = ProcessSpawner()
    tracker = ProcessTracker()
    git_client = GitClient()

    lifecycle_service = BotLifecycleService(config=app_cfg, spawner=spawner, tracker=tracker)
    assert isinstance(lifecycle_service, IBotLifecycleService)

    update_service = UpdateService(config=app_cfg, git_client=git_client, lifecycle_service=lifecycle_service)
    assert isinstance(update_service, IUpdateService)

    health_service = HealthService(config=app_cfg, tracker=tracker, spawner=spawner)
    assert isinstance(health_service, IHealthService)

    telemetry_service = TelemetryService(
        config=app_cfg,
        tracker=tracker,
        metrics_collector=MetricsCollector(),
        i18n=i18n,
        start_time=datetime.datetime.now(),
    )
    assert isinstance(telemetry_service, ITelemetryService)


def test_custom_mock_satisfies_protocol_and_can_be_injected():
    """Verifies that a custom mock implementing IProcessSpawner can be injected into BotLifecycleService."""

    class CustomMockSpawner:
        stop_timeout = 1.0
        restart_wait = 0.5
        log_rotator = None
        last_error = None

        def spawn(self, bot_config, env):
            return 4242

        async def terminate_process(self, process):
            return True

        def find_all_processes_in_path(self, bot_path):
            return []

        async def kill_rogue_processes(self, bot_path):
            pass

        def start_service(self, service_name):
            return True

        def stop_service(self, service_name):
            return True

        def restart_service(self, service_name):
            return True

        def get_systemd_state(self, service_name):
            return "active"

        def get_systemd_pid(self, service_name):
            return 4242

        async def get_systemd_pid_async(self, service_name, retries=3):
            return 4242

        def execute_manager_restart(self):
            pass

        def execute_manager_shutdown(self):
            pass

    mock_spawner = CustomMockSpawner()
    assert isinstance(mock_spawner, IProcessSpawner)

    app_cfg = AppConfig(bots={"b1": BotConfig(id="b1", name="Bot 1", path="C:\\test", cmd="python bot.py")})
    tracker = ProcessTracker()

    service = BotLifecycleService(config=app_cfg, spawner=mock_spawner, tracker=tracker)
    assert service.spawner is mock_spawner
