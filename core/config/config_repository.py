import os
import json
from typing import Optional, Dict, Any
from core.logger import log
from core.config.models import AppConfig, BotConfig

class ConfigRepository:
    """Handles persistent loading and saving of the application configuration."""
    def __init__(self, config_path: str = "config.json"):
        self.config_path = os.path.abspath(config_path)
        self.app_config: AppConfig = self.load()

    def load(self) -> AppConfig:
        """Loads configuration from JSON file and builds an AppConfig instance."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    self.app_config = AppConfig.from_dict(raw)
                    log.info(f"[ConfigRepository] Loaded config from {self.config_path} with {len(self.app_config.bots)} bots.")
                    return self.app_config
            except Exception as e:
                log.error(f"[ConfigRepository] Error loading config from {self.config_path}: {e}")
        else:
            log.warning(f"[ConfigRepository] Config file not found at {self.config_path}")

        self.app_config = AppConfig()
        return self.app_config

    def save(self, raw_data: Optional[Dict[str, Any]] = None) -> bool:
        """Saves current configuration to file."""
        data_to_save = raw_data if raw_data is not None else self.app_config.raw_config
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=4)
            if raw_data is not None:
                self.app_config = AppConfig.from_dict(raw_data)
            log.info(f"[ConfigRepository] Config saved successfully to {self.config_path}")
            return True
        except Exception as e:
            log.error(f"[ConfigRepository] Error saving config to {self.config_path}: {e}")
            return False

    def get_bot(self, bot_id: str) -> Optional[BotConfig]:
        """Gets a bot configuration by ID."""
        return self.app_config.bots.get(bot_id)

    @property
    def raw(self) -> Dict[str, Any]:
        """Returns the raw dictionary format for backward compatibility."""
        return self.app_config.raw_config
