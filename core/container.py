import datetime
import os
from collections.abc import Callable
from typing import Any, TypeVar

from core.config.config_repository import ConfigRepository
from core.config.models import AppConfig
from core.config.state_repository import StateRepository
from core.icons import Icons
from core.logger import log, reconfigure_log
from core.services.bot_lifecycle_service import BotLifecycleService
from core.services.health_service import HealthService
from core.services.i18n_service import LocalizationService
from core.services.metrics_exporter import MetricsServer
from core.services.telemetry_service import TelemetryService
from core.services.update_service import UpdateService
from core.system.git_client import GitClient
from core.system.log_rotator import LogRotator
from core.system.metrics_collector import MetricsCollector
from core.system.process_spawner import ProcessSpawner
from core.system.process_tracker import ProcessTracker

T = TypeVar("T")


class ServiceContainer:
    """Dependency Injection and Service Registry Container for managing subsystem lifecycles and wiring."""

    def __init__(self):
        self._services: dict[str, Any] = {}
        self._types: dict[type, Any] = {}

    def register(self, key: str, service: Any, service_type: type | None = None) -> None:
        """Registers a service instance by string key and optionally by type."""
        self._services[key] = service
        if service_type is not None:
            self._types[service_type] = service
        elif isinstance(service, type):
            self._types[service] = service
        else:
            self._types[type(service)] = service

    def get(self, key_or_type: Any, default: Any = None) -> Any:
        """Resolves a service by string key or type."""
        if isinstance(key_or_type, str):
            return self._services.get(key_or_type, default)
        return self._types.get(key_or_type, default)

    def has(self, key_or_type: Any) -> bool:
        """Checks if a service is registered."""
        if isinstance(key_or_type, str):
            return key_or_type in self._services
        return key_or_type in self._types

    @classmethod
    def create_default(
        cls, base_dir: str, notify_callback: Callable | None = None, alert_callback: Callable | None = None
    ) -> "ServiceContainer":
        """Builds and wires the complete production dependency graph."""
        container = cls()
        base_dir = os.path.abspath(base_dir)

        config_path = os.path.join(base_dir, "config.json")
        state_path = os.path.join(base_dir, "state.json")

        # 1. Repositories
        config_repo = ConfigRepository(config_path)
        state_repo = StateRepository(state_path)
        app_cfg = config_repo.app_config
        bot_settings = app_cfg.bot_settings

        container.register("config_repo", config_repo, ConfigRepository)
        container.register("state_repo", state_repo, StateRepository)
        container.register("app_cfg", app_cfg, AppConfig)

        # 2. Logger Reconfiguration
        reconfigure_log(bot_settings.manager_log_file, bot_settings.log_max_bytes, bot_settings.log_backup_count)

        # 3. Icons & Localization
        Icons.setup(app_cfg.raw_config.get("bot_settings", {}))
        i18n = LocalizationService(bot_settings.language)
        container.register("i18n", i18n, LocalizationService)

        # 4. System & Infrastructure
        log_rotator = LogRotator(bot_settings.bot_log_max_bytes, bot_settings.bot_log_backup_count)
        spawner = ProcessSpawner(bot_settings.stop_timeout, bot_settings.restart_wait, log_rotator=log_rotator)
        tracker = ProcessTracker()
        metrics_collector = MetricsCollector()
        git_client = GitClient(bot_settings.requirements_file, bot_settings.rollback_ref)

        container.register("log_rotator", log_rotator, LogRotator)
        container.register("spawner", spawner, ProcessSpawner)
        container.register("tracker", tracker, ProcessTracker)
        container.register("metrics_collector", metrics_collector, MetricsCollector)
        container.register("git_client", git_client, GitClient)

        # 5. Core Business Services
        lifecycle_service = BotLifecycleService(
            config=app_cfg, spawner=spawner, tracker=tracker, notify_callback=notify_callback
        )
        update_service = UpdateService(
            config=app_cfg, git_client=git_client, lifecycle_service=lifecycle_service, manager_root=base_dir
        )
        health_service = HealthService(config=app_cfg, tracker=tracker, spawner=spawner, alert_callback=alert_callback)
        telemetry_service = TelemetryService(
            config=app_cfg,
            tracker=tracker,
            metrics_collector=metrics_collector,
            i18n=i18n,
            start_time=datetime.datetime.now(),
        )
        metrics_server = MetricsServer(
            telemetry_service=telemetry_service,
            host=bot_settings.metrics_host,
            port=bot_settings.metrics_port,
            enabled=bot_settings.metrics_enabled,
        )

        container.register("lifecycle_service", lifecycle_service, BotLifecycleService)
        container.register("update_service", update_service, UpdateService)
        container.register("health_service", health_service, HealthService)
        container.register("telemetry_service", telemetry_service, TelemetryService)
        container.register("metrics_server", metrics_server, MetricsServer)

        log.info("[ServiceContainer] Production service graph assembled successfully.")
        return container

    # --- Strongly-Typed Convenience Properties ---

    @property
    def config_repo(self) -> ConfigRepository:
        return self.get("config_repo")

    @property
    def state_repo(self) -> StateRepository:
        return self.get("state_repo")

    @property
    def app_config(self) -> AppConfig:
        return self.get("app_cfg")

    @property
    def i18n(self) -> LocalizationService:
        return self.get("i18n")

    @property
    def spawner(self) -> ProcessSpawner:
        return self.get("spawner")

    @property
    def tracker(self) -> ProcessTracker:
        return self.get("tracker")

    @property
    def metrics_collector(self) -> MetricsCollector:
        return self.get("metrics_collector")

    @property
    def git_client(self) -> GitClient:
        return self.get("git_client")

    @property
    def log_rotator(self) -> LogRotator:
        return self.get("log_rotator")

    @property
    def lifecycle_service(self) -> BotLifecycleService:
        return self.get("lifecycle_service")

    @property
    def update_service(self) -> UpdateService:
        return self.get("update_service")

    @property
    def health_service(self) -> HealthService:
        return self.get("health_service")

    @property
    def telemetry_service(self) -> TelemetryService:
        return self.get("telemetry_service")

    @property
    def metrics_server(self) -> MetricsServer:
        return self.get("metrics_server")


__all__ = ["ServiceContainer"]
