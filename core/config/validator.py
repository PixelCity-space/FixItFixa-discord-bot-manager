import os
from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationError:
    """Represents a single validation error in the configuration."""

    field: str
    message: str
    value: Any = None

    def __str__(self) -> str:
        val_str = f" (received: {repr(self.value)})" if self.value is not None else ""
        return f"[{self.field}] {self.message}{val_str}"


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    def __init__(self, errors: list[ValidationError]):
        self.errors = errors
        error_lines = "\n  - ".join(str(e) for e in errors)
        super().__init__(f"Configuration validation failed with {len(errors)} error(s):\n  - {error_lines}")


class ConfigValidator:
    """Validates raw configuration dictionaries against the application schema and semantic rules."""

    SUPPORTED_LANGUAGES = {"hu", "en"}

    @classmethod
    def validate(cls, data: dict[str, Any]) -> list[ValidationError]:
        """Validates configuration dictionary and returns a list of all validation errors."""
        errors: list[ValidationError] = []

        if not isinstance(data, dict):
            errors.append(ValidationError("root", "Configuration root must be a JSON object / dictionary", data))
            return errors

        # 1. Validate Bot Settings
        bot_settings = data.get("bot_settings", {})
        if not isinstance(bot_settings, dict):
            errors.append(ValidationError("bot_settings", "Must be a dictionary", bot_settings))
        else:
            lang = bot_settings.get("language")
            if lang is not None and lang not in cls.SUPPORTED_LANGUAGES:
                errors.append(
                    ValidationError(
                        "bot_settings.language",
                        f"Unsupported language code '{lang}'. Supported: {', '.join(sorted(cls.SUPPORTED_LANGUAGES))}",
                        lang,
                    )
                )

            # Numeric positive limits validation
            positive_int_fields = [
                ("purge_limit", 1),
                ("check_interval_seconds", 1),
                ("status_refresh_seconds", 1),
                ("status_recreate_minutes", 1),
                ("log_max_bytes", 1024),
                ("log_backup_count", 1),
                ("bot_log_max_bytes", 1024),
                ("bot_log_backup_count", 1),
            ]
            for field_name, min_val in positive_int_fields:
                if field_name in bot_settings:
                    val = bot_settings[field_name]
                    if not isinstance(val, int) or val < min_val:
                        errors.append(
                            ValidationError(f"bot_settings.{field_name}", f"Must be an integer >= {min_val}", val)
                        )

            positive_float_fields = [("stop_timeout", 0.1), ("restart_wait", 0.0)]
            for field_name, min_float_val in positive_float_fields:
                if field_name in bot_settings:
                    val = bot_settings[field_name]
                    if not isinstance(val, (int, float)) or val < min_float_val:
                        errors.append(
                            ValidationError(f"bot_settings.{field_name}", f"Must be a number >= {min_float_val}", val)
                        )

            if "metrics_port" in bot_settings:
                port_val = bot_settings["metrics_port"]
                if not isinstance(port_val, int) or port_val < 1 or port_val > 65535:
                    errors.append(
                        ValidationError("bot_settings.metrics_port", "Must be a valid TCP port (1-65535)", port_val)
                    )

        # 2. Validate Access Control
        settings_sec = data.get("settings", {})
        ac_data = settings_sec.get("access_control") if isinstance(settings_sec, dict) else None
        if ac_data is None:
            ac_data = data.get("access_control", {})

        if ac_data and isinstance(ac_data, dict):
            roles = ac_data.get("roles")
            if roles is not None and not isinstance(roles, dict):
                errors.append(
                    ValidationError("access_control.roles", "Must be a dictionary mapping role names to IDs", roles)
                )
            channels = ac_data.get("channels")
            if channels is not None and not isinstance(channels, dict):
                errors.append(
                    ValidationError(
                        "access_control.channels", "Must be a dictionary mapping channel names to IDs", channels
                    )
                )

        # 3. Validate Bots
        raw_bots = data.get("bots", {})
        if not isinstance(raw_bots, dict):
            errors.append(
                ValidationError("bots", "Must be a dictionary mapping bot IDs to bot configurations", raw_bots)
            )
        else:
            is_windows = os.name == "nt"
            for bot_id, bot_cfg in raw_bots.items():
                prefix = f"bots['{bot_id}']"
                if not isinstance(bot_cfg, dict):
                    errors.append(ValidationError(prefix, "Bot entry must be a dictionary", bot_cfg))
                    continue

                # Name validation
                name = bot_cfg.get("name")
                if not name or not isinstance(name, str) or not name.strip():
                    errors.append(
                        ValidationError(f"{prefix}.name", "Bot name is required and must be a non-empty string", name)
                    )

                # Path validation (cross-platform)
                path = bot_cfg.get("path_win") if is_windows and "path_win" in bot_cfg else bot_cfg.get("path")
                # Fallback to standard path if path_win empty on windows
                if is_windows and (path is None or not str(path).strip()):
                    path = bot_cfg.get("path")

                if path is None or not isinstance(path, str) or not path.strip():
                    errors.append(
                        ValidationError(
                            f"{prefix}.path",
                            "Bot working directory path is required and cannot be empty (path or path_win)",
                            path,
                        )
                    )

                # Command validation (cross-platform)
                cmd = bot_cfg.get("cmd_win") if is_windows and "cmd_win" in bot_cfg else bot_cfg.get("cmd")
                if is_windows and (cmd is None or not str(cmd).strip() or str(cmd).strip() == "."):
                    cmd = bot_cfg.get("cmd")

                if cmd is None or not isinstance(cmd, str) or not cmd.strip() or cmd.strip() == ".":
                    errors.append(
                        ValidationError(
                            f"{prefix}.cmd",
                            "Bot startup command is required and cannot be empty or '.' (cmd or cmd_win)",
                            cmd,
                        )
                    )

                # db_files validation
                db_files = bot_cfg.get("db_files")
                if db_files is not None and not isinstance(db_files, list):
                    errors.append(
                        ValidationError(f"{prefix}.db_files", "Must be a list of database filenames", db_files)
                    )

        return errors

    @classmethod
    def validate_or_raise(cls, data: dict[str, Any]) -> None:
        """Validates configuration and raises ConfigValidationError if any errors are found."""
        errors = cls.validate(data)
        if errors:
            raise ConfigValidationError(errors)


__all__ = ["ValidationError", "ConfigValidationError", "ConfigValidator"]
