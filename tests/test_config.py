import json
from core.config.models import AppConfig, BotConfig, BotSettingsConfig, AccessControlConfig
from core.config.config_repository import ConfigRepository
from core.config.state_repository import StateRepository

def test_bot_config_defaults():
    bot = BotConfig(id="123", name="TestBot", path="/path/to/bot", cmd="python bot.py")
    assert bot.id == "123"
    assert bot.name == "TestBot"
    assert bot.path == "/path/to/bot"
    assert bot.cmd == "python bot.py"
    assert bot.log == "bot.log"
    assert bot.db_files == []
    assert bot.git_branch is None

def test_bot_settings_config_defaults():
    settings = BotSettingsConfig()
    assert settings.language == "hu"
    assert settings.git_branch == "origin/main"
    assert settings.check_interval_seconds == 60
    assert settings.status_refresh_seconds == 60
    assert settings.bot_log_max_bytes == 10 * 1024 * 1024
    assert settings.bot_log_backup_count == 3

def test_app_config_from_dict():
    raw = {
        "guild_id": 999888,
        "access_control": {
            "admin_channel_id": 111,
            "public_channel_id": 222,
            "roles": {"admin": 333, "tester": 444}
        },
        "bot_settings": {
            "manager_name": "CustomFixa",
            "language": "en"
        },
        "ui_settings": {
            "accent_color": 0x123456,
            "bots_per_page": 5
        },
        "bots": {
            "bot1": {
                "name": "Bot One",
                "path": "C:\\bots\\one",
                "cmd": "python app.py"
            }
        }
    }
    cfg = AppConfig.from_dict(raw)
    assert cfg.guild_id == "999888"
    assert cfg.access_control.admin_channel_id == "111"
    assert cfg.access_control.admin_role_id == "333"
    assert cfg.access_control.tester_role_id == "444"
    assert cfg.bot_settings.language == "en"
    assert cfg.ui_settings.get("accent_color") == 0x123456
    assert cfg.ui_settings.get("bots_per_page") == 5
    assert len(cfg.bots) == 1
    assert cfg.bots["bot1"].name == "Bot One"

def test_config_repository_load_and_save(tmp_path):
    config_file = tmp_path / "config.json"
    data = {
        "guild_id": 12345,
        "bots": {
            "b1": {"name": "Test1", "path": "/test", "cmd": "python bot.py"}
        }
    }
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    repo = ConfigRepository(str(config_file))
    assert repo.app_config.guild_id == "12345"
    assert "b1" in repo.app_config.bots
    assert repo.get_bot("b1").name == "Test1"
    assert repo.get_bot("non_existent") is None

    # Test saving
    data["guild_id"] = 67890
    assert repo.save(data) is True
    repo.load()
    assert repo.app_config.guild_id == "67890"

def test_config_repository_missing_file(tmp_path):
    missing_file = tmp_path / "non_existent.json"
    repo = ConfigRepository(str(missing_file))
    assert isinstance(repo.app_config, AppConfig)
    assert repo.app_config.guild_id is None

def test_state_repository_operations(tmp_path):
    state_file = tmp_path / "state.json"
    repo = StateRepository(str(state_file))
    assert repo.get("status_message_id") is None

    repo.set("status_message_id", "123456789")
    repo.set("status_channel_id", "987654321")
    assert repo.get("status_message_id") == "123456789"
    assert repo.get("status_channel_id") == "987654321"

    # Reload from disk
    new_repo = StateRepository(str(state_file))
    assert new_repo.get("status_message_id") == "123456789"
    assert new_repo.get("status_channel_id") == "987654321"

def test_bot_config_from_dict_platform():
    data = {
        "name": "CrossBot",
        "path": "/linux/path",
        "path_win": "C:\\windows\\path",
        "cmd": "python3 bot.py",
        "cmd_win": "python bot.py"
    }
    bot = BotConfig.from_dict("c1", data)
    assert bot.id == "c1"
    assert bot.name == "CrossBot"
    assert bot.path is not None
    assert bot.cmd is not None

def test_access_control_config_empty_defaults():
    ac = AccessControlConfig()
    assert ac.admin_role_id is None
    assert ac.tester_role_id is None
    assert ac.admin_channel_id is None
    assert ac.public_channel_id is None
