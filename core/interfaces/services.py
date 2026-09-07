import datetime
from typing import Any, Protocol, runtime_checkable

from core.config.models import BotConfig


@runtime_checkable
class ILocalizationService(Protocol):
    """Protocol for translation, icon substitution, and slash command localization."""

    default_lang: str
    current_lang: str
    translations: dict[str, Any]

    def load_translations(self, lang: str) -> None: ...
    def get_plural_category(self, lang: str, count: int | float) -> str: ...
    def get(self, key: str, default: str | None = None, **kwargs) -> str: ...
    def get_plural(self, key: str, count: int | float, default: str | None = None, **kwargs) -> str: ...
    def localize_commands(self, tree: Any, guild: Any = None) -> None: ...


@runtime_checkable
class IBotLifecycleService(Protocol):
    """Protocol for bot subprocess lifecycle orchestration."""

    def get_related_bots(self, bot_id: str) -> list[BotConfig]: ...
    async def start_bot(self, bot_id: str) -> int | None: ...
    async def stop_bot(self, bot_id: str, clean_rogue: bool = True) -> tuple[bool, str | None]: ...
    async def restart_bot_cluster(self, bot_id: str) -> list[tuple[BotConfig, int | None, str | None]]: ...


@runtime_checkable
class IUpdateService(Protocol):
    """Protocol for Git updates, dependency installation, rollbacks, and self-updates."""

    manager_root: str

    def prepare_manager_restart(self) -> str: ...
    async def update_manager(self) -> tuple[bool, str, bool, dict[str, Any] | None]: ...
    async def update_bot(
        self, bot_id: str
    ) -> tuple[bool, str, bool, dict[str, Any] | None, list[tuple[BotConfig, int | None, str | None]]]: ...
    async def rollback_bot(
        self, bot_id: str
    ) -> tuple[bool, str, bool, dict[str, Any] | None, list[tuple[BotConfig, int | None, str | None]]]: ...


@runtime_checkable
class IHealthService(Protocol):
    """Protocol for heartbeat health checking and crash alerting."""

    alerted_bots: set

    async def check_health(self) -> list[tuple[str, BotConfig]]: ...
    def clear_alert(self, bot_id: str) -> None: ...
    def reset_alerts(self) -> None: ...


@runtime_checkable
class ITelemetryService(Protocol):
    """Protocol for aggregating system, process, log, and database metrics."""

    start_time: datetime.datetime

    def format_uptime(self, uptime_sec: float) -> str: ...
    def get_log_size(self, bot_path: str, log_filename: str) -> str: ...
    def get_db_sizes(self, bot_path: str, db_filenames: list[str]) -> dict[str, str]: ...
    def collect_manager_metrics(self, git_behind_status: dict[str, bool] | None = None) -> dict[str, Any]: ...
    def collect_bots_metrics(self, git_behind_status: dict[str, bool] | None = None) -> dict[str, Any]: ...
    def get_status_snapshot(
        self, git_behind_status: dict[str, bool] | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]]: ...
    async def get_status_snapshot_async(
        self, git_behind_status: dict[str, bool] | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]]: ...


__all__ = ["ILocalizationService", "IBotLifecycleService", "IUpdateService", "IHealthService", "ITelemetryService"]
