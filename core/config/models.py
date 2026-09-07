import os
from dataclasses import dataclass, field
from typing import Any, TypedDict

# --- TypedDict Schemas for Static Type Checking ---


class UiSettingsDict(TypedDict, total=False):
    status_panel_title: str | None
    show_host_metrics: bool
    show_bot_ram: bool
    show_bot_cpu: bool
    items_per_page: int
    theme_color: int | None


class BotConfigDict(TypedDict, total=False):
    name: str
    path: str
    path_win: str
    cmd: str
    cmd_win: str
    log: str
    systemd_service: str | None
    description: str | None
    git_branch: str | None
    db_files: list[str]


class AccessControlDict(TypedDict, total=False):
    roles: dict[str, str | int]
    channels: dict[str, str | int]
    admin_role_id: str | int | None
    tester_role_id: str | int | None
    admin_channel_id: str | int | None
    public_channel_id: str | int | None


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
    protected_env_vars: list[str]
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
    emojis: dict[str, str]
    metrics_enabled: bool
    metrics_host: str
    metrics_port: int


class AppConfigDict(TypedDict, total=False):
    guild_id: str | int | None
    settings: dict[str, Any]
    access_control: AccessControlDict
    bot_settings: BotSettingsDict
    ui_settings: UiSettingsDict
    bots: dict[str, BotConfigDict]


# --- Domain Dataclasses ---


@dataclass
class UiConfig:
    """Strongly-typed configuration for the Discord status dashboard."""

    status_panel_title: str | None = None
    show_host_metrics: bool = True
    show_bot_ram: bool = True
    show_bot_cpu: bool = True
    items_per_page: int = 6
    theme_color: int | None = None
    view_timeout: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None = None) -> "UiConfig":
        if not data:
            return cls()
        return cls(
            status_panel_title=data.get("status_panel_title"),
            show_host_metrics=data.get("show_host_metrics", True),
            show_bot_ram=data.get("show_bot_ram", True),
            show_bot_cpu=data.get("show_bot_cpu", True),
            items_per_page=data.get("items_per_page", 6),
            theme_color=data.get("theme_color"),
            view_timeout=data.get("view_timeout"),
            raw=data,
        )

    def to_dict(self) -> dict[str, Any]:
        res = dict(self.raw) if self.raw else {}
        if self.status_panel_title is not None:
            res["status_panel_title"] = self.status_panel_title
        res["show_host_metrics"] = self.show_host_metrics
        res["show_bot_ram"] = self.show_bot_ram
        res["show_bot_cpu"] = self.show_bot_cpu
        res["items_per_page"] = self.items_per_page
        if self.theme_color is not None:
            res["theme_color"] = self.theme_color
        if self.view_timeout is not None:
            res["view_timeout"] = self.view_timeout
        return res


@dataclass
class BotConfig:
    id: str
    name: str
    path: str
    cmd: str
    log: str = "bot.log"
    systemd_service: str | None = None
    description: str | None = None
    git_branch: str | None = None
    db_files: list[str] = field(default_factory=list)

    @property
    def is_runnable(self) -> bool:
        """Returns True if the bot has both a valid non-empty path and executable command."""
        return bool(
            self.path and str(self.path).strip() and self.cmd and str(self.cmd).strip() and str(self.cmd).strip() != "."
        )

    @classmethod
    def from_dict(cls, bot_id: str, data: dict, default_log: str = "bot.log") -> "BotConfig":
        """Creates a BotConfig object, adapting platform-specific paths for Windows / Linux."""
        is_windows = os.name == "nt"

        raw_path_win = data.get("path_win")
        raw_path = data.get("path", ".")
        if is_windows and raw_path_win is not None and str(raw_path_win).strip():
            path = str(raw_path_win).strip()
        else:
            path = str(raw_path).strip() if raw_path else "."

        raw_cmd_win = data.get("cmd_win")
        raw_cmd = data.get("cmd", "")
        if is_windows and raw_cmd_win is not None and str(raw_cmd_win).strip() and str(raw_cmd_win).strip() != ".":
            cmd = str(raw_cmd_win).strip()
        else:
            cmd = str(raw_cmd).strip() if raw_cmd else ""

        systemd_service = None if is_windows else data.get("systemd_service")

        raw_log = data.get("log")
        log_file = str(raw_log).strip() if raw_log and str(raw_log).strip() else default_log

        return cls(
            id=bot_id,
            name=data.get("name", "Unknown"),
            path=path,
            cmd=cmd,
            log=log_file,
            systemd_service=systemd_service,
            description=data.get("description"),
            git_branch=data.get("git_branch"),
            db_files=data.get("db_files", []),
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "path": self.path,
            "cmd": self.cmd,
            "log": self.log,
        }
        if self.systemd_service is not None:
            data["systemd_service"] = self.systemd_service
        if self.description is not None:
            data["description"] = self.description
        if self.git_branch is not None:
            data["git_branch"] = self.git_branch
        if self.db_files:
            data["db_files"] = list(self.db_files)
        return data


@dataclass
class AccessControlConfig:
    roles: dict[str, str] = field(default_factory=dict)
    channels: dict[str, str] = field(default_factory=dict)

    @property
    def admin_role_id(self) -> str | None:
        val = self.roles.get("admin")
        return str(val) if val else None

    @property
    def tester_role_id(self) -> str | None:
        val = self.roles.get("tester")
        return str(val) if val else None

    @property
    def admin_channel_id(self) -> str | None:
        val = self.channels.get("admin")
        return str(val) if val else None

    @property
    def public_channel_id(self) -> str | None:
        val = self.channels.get("public")
        return str(val) if val else None

    @classmethod
    def from_dict(cls, data: dict) -> "AccessControlConfig":
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

    def to_dict(self) -> dict[str, Any]:
        return {"roles": dict(self.roles), "channels": dict(self.channels)}


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
    protected_env_vars: list[str] = field(default_factory=lambda: ["DISCORD_TOKEN", "GUILD_ID", "ADMIN_CHANNEL_ID"])
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
    emojis: dict[str, str] = field(default_factory=dict)
    metrics_enabled: bool = True
    metrics_host: str = "0.0.0.0"
    metrics_port: int = 9090

    @classmethod
    def from_dict(cls, data: dict) -> "BotSettingsConfig":
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
            emojis=data.get("emojis", {}),
            metrics_enabled=bool(data.get("metrics_enabled", True)),
            metrics_host=str(data.get("metrics_host", "0.0.0.0")),
            metrics_port=int(data.get("metrics_port", 9090)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "command_prefix": self.command_prefix,
            "command_suffix": self.command_suffix,
            "log_default_lines": self.log_default_lines,
            "purge_limit": self.purge_limit,
            "check_interval_seconds": self.check_interval_seconds,
            "status_refresh_seconds": self.status_refresh_seconds,
            "status_recreate_minutes": self.status_recreate_minutes,
            "git_branch": self.git_branch,
            "requirements_file": self.requirements_file,
            "rollback_ref": self.rollback_ref,
            "protected_env_vars": list(self.protected_env_vars),
            "temp_dir": self.temp_dir,
            "stop_timeout": self.stop_timeout,
            "restart_wait": self.restart_wait,
            "manager_log_file": self.manager_log_file,
            "bot_log_default": self.bot_log_default,
            "log_max_bytes": self.log_max_bytes,
            "log_backup_count": self.log_backup_count,
            "bot_log_max_bytes": self.bot_log_max_bytes,
            "bot_log_backup_count": self.bot_log_backup_count,
            "systemd_name": self.systemd_name,
            "emojis": dict(self.emojis),
            "metrics_enabled": self.metrics_enabled,
            "metrics_host": self.metrics_host,
            "metrics_port": self.metrics_port,
        }


@dataclass
class AppConfig:
    guild_id: str | None = None
    access_control: AccessControlConfig = field(default_factory=AccessControlConfig)
    bot_settings: BotSettingsConfig = field(default_factory=BotSettingsConfig)
    ui: UiConfig = field(default_factory=UiConfig)
    ui_settings: dict[str, Any] = field(default_factory=dict)
    bots: dict[str, BotConfig] = field(default_factory=dict)
    raw_config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        settings = data.get("settings", {})
        guild_id = settings.get("guild_id") or data.get("guild_id")
        ac_data = settings.get("access_control") or data.get("access_control", {})
        ac = AccessControlConfig.from_dict(ac_data)

        bot_settings = BotSettingsConfig.from_dict(data.get("bot_settings", {}))
        raw_ui = data.get("ui_settings", {})
        ui = UiConfig.from_dict(raw_ui)

        raw_bots = data.get("bots", {})
        bots = {bid: BotConfig.from_dict(bid, bdata, bot_settings.bot_log_default) for bid, bdata in raw_bots.items()}

        return cls(
            guild_id=str(guild_id) if guild_id else None,
            access_control=ac,
            bot_settings=bot_settings,
            ui=ui,
            ui_settings=raw_ui,
            bots=bots,
            raw_config=data,
        )

    def to_dict(self) -> dict[str, Any]:
        out = dict(self.raw_config) if self.raw_config else {}
        if self.guild_id is not None:
            if "settings" in out and isinstance(out["settings"], dict):
                out["settings"]["guild_id"] = self.guild_id
            else:
                out["guild_id"] = self.guild_id

        ac_dict = self.access_control.to_dict()
        if "settings" in out and isinstance(out["settings"], dict):
            out["settings"]["access_control"] = ac_dict
        else:
            out["access_control"] = ac_dict

        out["bot_settings"] = self.bot_settings.to_dict()
        out["ui_settings"] = self.ui.to_dict() if hasattr(self.ui, "to_dict") else (self.ui_settings or {})
        out["bots"] = {bid: bcfg.to_dict() for bid, bcfg in self.bots.items()}
        return out


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
    "AppConfigDict",
]
