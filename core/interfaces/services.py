from typing import Protocol, runtime_checkable, Optional, List, Dict, Tuple, Any
import datetime
from core.config.models import BotConfig

@runtime_checkable
class ILocalizationService(Protocol):
    """Protocol for translation, icon substitution, and slash command localization."""
    default_lang: str
    current_lang: str
    translations: Dict[str, Any]

    def load_translations(self, lang: str) -> None: ...
    def get_plural_category(self, lang: str, count: int | float) -> str: ...
    def get(self, key: str, default: Optional[str] = None, **kwargs) -> str: ...
    def get_plural(self, key: str, count: int | float, default: Optional[str] = None, **kwargs) -> str: ...
    def localize_commands(self, tree: Any, guild: Any = None) -> None: ...

@runtime_checkable
class IBotLifecycleService(Protocol):
    """Protocol for bot subprocess lifecycle orchestration."""
    def get_related_bots(self, bot_id: str) -> List[BotConfig]: ...
    async def start_bot(self, bot_id: str) -> Optional[int]: ...
    async def stop_bot(self, bot_id: str, clean_rogue: bool = True) -> bool: ...
    async def restart_bot_cluster(self, bot_id: str) -> List[Tuple[BotConfig, Optional[int], Optional[str]]]: ...

@runtime_checkable
class IUpdateService(Protocol):
    """Protocol for Git updates, dependency installation, rollbacks, and self-updates."""
    manager_root: str

    def prepare_manager_restart(self) -> str: ...
    async def update_manager(self) -> Tuple[bool, str, bool, Optional[Dict[str, Any]]]: ...
    async def update_bot(
        self,
        bot_id: str
    ) -> Tuple[bool, str, bool, Optional[Dict[str, Any]], List[Tuple[BotConfig, Optional[int], Optional[str]]]]: ...
    async def rollback_bot(
        self,
        bot_id: str
    ) -> Tuple[bool, str, bool, Optional[Dict[str, Any]], List[Tuple[BotConfig, Optional[int], Optional[str]]]]: ...

@runtime_checkable
class IHealthService(Protocol):
    """Protocol for heartbeat health checking and crash alerting."""
    alerted_bots: set

    async def check_health(self) -> List[Tuple[str, BotConfig]]: ...

@runtime_checkable
class ITelemetryService(Protocol):
    """Protocol for aggregating system, process, log, and database metrics."""
    start_time: datetime.datetime

    def format_uptime(self, uptime_sec: float) -> str: ...
    def get_log_size(self, bot_path: str, log_filename: str) -> str: ...
    def get_db_sizes(self, bot_path: str, db_filenames: List[str]) -> Dict[str, str]: ...
    def collect_manager_metrics(self, git_behind_status: Optional[Dict[str, bool]] = None) -> Dict[str, Any]: ...
    def collect_bots_metrics(self, git_behind_status: Optional[Dict[str, bool]] = None) -> Dict[str, Any]: ...
    def get_status_snapshot(
        self,
        git_behind_status: Optional[Dict[str, bool]] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]: ...

__all__ = [
    "ILocalizationService",
    "IBotLifecycleService",
    "IUpdateService",
    "IHealthService",
    "ITelemetryService"
]
