import contextlib
import json
import os
import threading
from typing import Any

from core.config.models import AppConfig, BotConfig
from core.config.validator import ConfigValidator, ValidationError
from core.logger import log


class ConfigRepository:
    """Handles thread-safe, atomic persistent loading, validation, and saving of the application configuration."""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = os.path.abspath(config_path)
        self._lock = threading.RLock()
        self.validation_errors: list[ValidationError] = []
        self.app_config: AppConfig = self.load()

    def load(self) -> AppConfig:
        """Loads configuration from JSON file under lock, validates schema, and builds an AppConfig instance."""
        with self._lock:
            self.validation_errors = []
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, encoding="utf-8") as f:
                        raw = json.load(f)

                    # Validate configuration
                    self.validation_errors = ConfigValidator.validate(raw)
                    if self.validation_errors:
                        log.warning(
                            f"[ConfigRepository] Configuration contains {len(self.validation_errors)} validation issue(s):"
                        )
                        for err in self.validation_errors:
                            log.warning(f"  - {err}")

                    self.app_config = AppConfig.from_dict(raw)
                    log.info(
                        f"[ConfigRepository] Loaded config from {self.config_path} with {len(self.app_config.bots)} bots."
                    )
                    return self.app_config
                except json.JSONDecodeError as e:
                    log.error(
                        f"[ConfigRepository] Corrupt JSON syntax in config file {self.config_path} (line {e.lineno}, col {e.colno}): {e.msg}"
                    )
                except (PermissionError, OSError) as e:
                    log.error(f"[ConfigRepository] I/O or permission error accessing config at {self.config_path}: {e}")
                except Exception as e:
                    log.error(f"[ConfigRepository] Unexpected error loading config from {self.config_path}: {e}")
            else:
                log.warning(f"[ConfigRepository] Config file not found at {self.config_path}")

            self.app_config = AppConfig()
            return self.app_config

    def save(self, raw_data: dict[str, Any] | None = None) -> bool:
        """Validates and saves current configuration to file atomically under lock."""
        with self._lock:
            if raw_data is not None:
                data_to_save = raw_data
            elif hasattr(self.app_config, "to_dict"):
                data_to_save = self.app_config.to_dict()
            else:
                data_to_save = self.app_config.raw_config

            # Pre-save validation
            val_errors = ConfigValidator.validate(data_to_save)
            if val_errors:
                log.error(
                    f"[ConfigRepository] Cannot save invalid configuration ({len(val_errors)} validation errors):"
                )
                for err in val_errors:
                    log.error(f"  - {err}")
                return False

            tmp_path = f"{self.config_path}.tmp"
            try:
                # 1. Write to temporary file with flush & fsync
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(data_to_save, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())

                # 2. Atomically replace target file
                os.replace(tmp_path, self.config_path)

                if raw_data is not None:
                    self.app_config = AppConfig.from_dict(raw_data)
                else:
                    self.app_config.raw_config = data_to_save
                log.info(f"[ConfigRepository] Config saved successfully to {self.config_path}")
                return True
            except (PermissionError, OSError) as e:
                log.error(f"[ConfigRepository] I/O or permission error writing config to {self.config_path}: {e}")
                if os.path.exists(tmp_path):
                    with contextlib.suppress(OSError):
                        os.remove(tmp_path)
                return False
            except Exception as e:
                log.error(f"[ConfigRepository] Unexpected error saving config to {self.config_path}: {e}")
                if os.path.exists(tmp_path):
                    with contextlib.suppress(OSError):
                        os.remove(tmp_path)
                return False

    async def save_async(self, raw_data: dict[str, Any] | None = None) -> bool:
        """Asynchronously validates and saves configuration in a worker thread without blocking the event loop."""
        import asyncio

        return await asyncio.to_thread(self.save, raw_data)

    def get_bot(self, bot_id: str) -> BotConfig | None:
        """Gets a bot configuration by ID."""
        with self._lock:
            return self.app_config.bots.get(bot_id)

    @property
    def raw(self) -> dict[str, Any]:
        """Returns the raw dictionary format for backward compatibility."""
        with self._lock:
            return self.app_config.raw_config


__all__ = ["ConfigRepository"]
