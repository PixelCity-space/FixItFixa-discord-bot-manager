from typing import Any, Protocol, runtime_checkable

from core.config.models import AppConfig, BotConfig


@runtime_checkable
class IConfigRepository(Protocol):
    """Protocol for loading, saving, and accessing application configuration."""

    config_path: str
    app_config: AppConfig

    def load(self) -> AppConfig: ...
    def save(self, raw_data: dict[str, Any] | None = None) -> bool: ...
    async def save_async(self, raw_data: dict[str, Any] | None = None) -> bool: ...
    def get_bot(self, bot_id: str) -> BotConfig | None: ...

    @property
    def raw(self) -> dict[str, Any]: ...


@runtime_checkable
class IStateRepository(Protocol):
    """Protocol for managing persistent runtime state."""

    state_path: str

    def load(self) -> dict[str, Any]: ...
    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any, auto_save: bool = True) -> None: ...
    def save(self) -> bool: ...
    async def save_async(self) -> bool: ...

    @property
    def raw(self) -> dict[str, Any]: ...


__all__ = ["IConfigRepository", "IStateRepository"]
