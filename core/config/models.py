import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, TypedDict, Union

# --- TypedDict Schemas for Static Type Checking ---

class UiSettingsDict(TypedDict, total=False):
    status_panel_title: Optional[str]
    show_host_metrics: bool
    show_bot_ram: bool
    show_bot_cpu: bool
    items_per_page: int
    theme_color: Optional[int]

class BotConfigDict(TypedDict, total=False):
    name: str
    path: str
    path_win: str
    cmd: str
    cmd_win: str
    log: str
    systemd_service: Optional[str]
    description: Optional[str]
    git_branch: Optional[str]
    db_files: List[str]

class AccessControlDict(TypedDict, total=False):
    roles: Dict[str, Union[str, int]]
    channels: Dict[str, Union[str, int]]
    admin_role_id: Optional[Union[str, int]]
    tester_role_id: Optional[Union[str, int]]
    admin_channel_id: Optional[Union[str, int]]
    public_channel_id: Optional[Union[str, int]]

class BotSettingsDict(TypedDict, total=False):
    language: str
    command_prefix: str
    command_suffix: str
    log_default_lines: int
    purge_limit: int
    check_interval_seconds: int
    status_refresh_seconds: int
    status_recreate_minutes: int
    git_branch: str
    requirements_file: str
    rollback_ref: str
    protected_env_vars: List[str]
    temp_dir: str
    stop_timeout: float
    restart_wait: float
    manager_log_file: str
    bot_log_default: str
    log_max_bytes: int
    log_backup_count: int
    bot_log_max_bytes: int
    bot_log_backup_count: int
    systemd_name: str
    emojis: Dict[str, str]

class AppConfigDict(TypedDict, total=False):
    guild_id: Optional[Union[str, int]]
    settings: Dict[str, Any]
    access_control: AccessControlDict
    bot_settings: BotSettingsDict
    ui_settings: UiSettingsDict
    bots: Dict[str, BotConfigDict]

# --- Domain Dataclasses ---

@dataclass
class UiConfig:
    """Strongly-typed configuration for the Discord status dashboard."""
    status_panel_title: Optional[str] = None
    show_host_metrics: bool = True
    show_bot_ram: bool = True
    show_bot_cpu: bool = True
    items_per_page: int = 6
    theme_color: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]] = None) -> 'UiConfig':
        if not data:
            return cls()
        return cls(
            status_panel_title=data.get("status_panel_title"),
            show_host_metrics=data.get("show_host_metrics", True),
            show_bot_ram=data.get("show_bot_ram", True),
            show_bot_cpu=data.get("show_bot_cpu", True),
            items_per_page=data.get("items_per_page", 6),
            theme_color=data.get("theme_color"),
            raw=data
        )

@dataclass
class BotConfig:
    id: str
    name: str
    path: str
    cmd: str
    log: str = "bot.log"
    systemd_service: Optional[str] = None
    description: Optional[str] = None
    git_branch: Optional[str] = None
    db_files: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, bot_id: str, data: dict, default_log: str = "bot.log") -> 'BotConfig':
        """Creates a BotConfig object, adapting platform-specific paths for Windows / Linux."""
        is_windows = os.name == 'nt'
        
        path = data.get("path_win", data.get("path", ".")) if is_windows else data.get("path", ".")
        cmd = data.get("cmd_win", data.get("cmd", "")) if is_windows else data.get("cmd", "")
        systemd_service = None if is_windows else data.get("systemd_service")
        
        return cls(
            id=bot_id,
            name=data.get("name", "Unknown"),
            path=path,
            cmd=cmd,
            log=data.get("log", default_log),
            systemd_service=systemd_service,
            description=data.get("description"),
            git_branch=data.get("git_branch"),
            db_files=data.get("db_files", [])
        )

@dataclass
class AccessControlConfig:
    roles: Dict[str, str] = field(default_factory=dict)
    channels: Dict[str, str] = field(default_factory=dict)

    @property
    def admin_role_id(self) -> Optional[str]:
        val = self.roles.get("admin")
        return str(val) if val else None

    @property
    def tester_role_id(self) -> Optional[str]:
        val = self.roles.get("tester")
        return str(val) if val else None

    @property
    def admin_channel_id(self) -> Optional[str]:
        val = self.channels.get("admin")
        return str(val) if val else None

    @property
    def public_channel_id(self) -> Optional[str]:
        val = self.channels.get("public")
        return str(val) if val else None

    @classmethod
    def from_dict(cls, data: dict) -> 'AccessControlConfig':
        roles = dict(data.get("roles", {}))
        if "admin_role_id" in data and "admin" not in roles:
            roles["admin"] = data["admin_role_id"]
        if "tester_role_id" in data and "tester" not in roles:
            roles["tester"] = data["tester_role_id"]

        channels = dict(data.get("channels", {}))
        if "admin_channel_id" in data and "admin" not in channels:
            channels["admin"] = data["admin_channel_id"]
        if "public_channel_id" in data and "public" not in channels:
            channels["public"] = data["public_channel_id"]

        return cls(roles=roles, channels=channels)

@dataclass
class BotSettingsConfig:
    language: str = "hu"
    command_prefix: str = "!"
    command_suffix: str = "_fix"
    log_default_lines: int = 50
    purge_limit: int = 1000
    check_interval_seconds: int = 60
    status_refresh_seconds: int = 60
    status_recreate_minutes: int = 58
    git_branch: str = "origin/main"
    requirements_file: str = "requirements.txt"
    rollback_ref: str = "HEAD@{1}"
    protected_env_vars: List[str] = field(default_factory=lambda: ["DISCORD_TOKEN", "GUILD_ID", "ADMIN_CHANNEL_ID"])
    temp_dir: str = "tmp"
    stop_timeout: float = 5.0
    restart_wait: float = 1.0
    manager_log_file: str = "manager.log"
    bot_log_default: str = "bot.log"
    log_max_bytes: int = 5 * 1024 * 1024
    log_backup_count: int = 3
    bot_log_max_bytes: int = 10 * 1024 * 1024
    bot_log_backup_count: int = 3
    systemd_name: str = "discord-manager.service"
    emojis: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> 'BotSettingsConfig':
        return cls(
            language=data.get("language", "hu"),
            command_prefix=data.get("command_prefix", "!"),
            command_suffix=data.get("command_suffix", "_fix"),
            log_default_lines=data.get("log_default_lines", 50),
            purge_limit=data.get("purge_limit", 1000),
            check_interval_seconds=data.get("check_interval_seconds", 60),
            status_refresh_seconds=data.get("status_refresh_seconds", 60),
            status_recreate_minutes=data.get("status_recreate_minutes", 58),
            git_branch=data.get("git_branch", "origin/main"),
            requirements_file=data.get("requirements_file", "requirements.txt"),
            rollback_ref=data.get("rollback_ref", "HEAD@{1}"),
            protected_env_vars=data.get("protected_env_vars", ["DISCORD_TOKEN", "GUILD_ID", "ADMIN_CHANNEL_ID"]),
            temp_dir=data.get("temp_dir", "tmp"),
            stop_timeout=float(data.get("stop_timeout", 5.0)),
            restart_wait=float(data.get("restart_wait", 1.0)),
            manager_log_file=data.get("manager_log_file", "manager.log"),
            bot_log_default=data.get("bot_log_default", "bot.log"),
            log_max_bytes=data.get("log_max_bytes", 5 * 1024 * 1024),
            log_backup_count=data.get("log_backup_count", 3),
            bot_log_max_bytes=data.get("bot_log_max_bytes", 10 * 1024 * 1024),
            bot_log_backup_count=data.get("bot_log_backup_count", 3),
            systemd_name=data.get("systemd_name", "discord-manager.service"),
            emojis=data.get("emojis", {})
        )

@dataclass
class AppConfig:
    guild_id: Optional[str] = None
    access_control: AccessControlConfig = field(default_factory=AccessControlConfig)
    bot_settings: BotSettingsConfig = field(default_factory=BotSettingsConfig)
    ui: UiConfig = field(default_factory=UiConfig)
    ui_settings: Dict[str, Any] = field(default_factory=dict)
    bots: Dict[str, BotConfig] = field(default_factory=dict)
    raw_config: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> 'AppConfig':
        settings = data.get("settings", {})
        guild_id = settings.get("guild_id") or data.get("guild_id")
        ac_data = settings.get("access_control") or data.get("access_control", {})
        ac = AccessControlConfig.from_dict(ac_data)
        
        bot_settings = BotSettingsConfig.from_dict(data.get("bot_settings", {}))
        raw_ui = data.get("ui_settings", {})
        ui = UiConfig.from_dict(raw_ui)
        
        raw_bots = data.get("bots", {})
        bots = {
            bid: BotConfig.from_dict(bid, bdata, bot_settings.bot_log_default)
            for bid, bdata in raw_bots.items()
        }
        
        return cls(
            guild_id=str(guild_id) if guild_id else None,
            access_control=ac,
            bot_settings=bot_settings,
            ui=ui,
            ui_settings=raw_ui,
            bots=bots,
            raw_config=data
        )

__all__ = [
    "BotConfig",
    "AccessControlConfig",
    "BotSettingsConfig",
    "UiConfig",
    "AppConfig",
    "UiSettingsDict",
    "BotConfigDict",
    "AccessControlDict",
    "BotSettingsDict",
    "AppConfigDict"
]
