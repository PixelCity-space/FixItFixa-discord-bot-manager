import pytest
import json
from core.config.validator import ConfigValidator, ConfigValidationError
from core.config.config_repository import ConfigRepository

def test_valid_configuration_passes_validation():
    valid_data = {
        "settings": {
            "guild_id": "123456789012345678",
            "access_control": {
                "roles": {"admin": "111", "tester": "222"},
                "channels": {"admin": "333", "public": "444"}
            }
        },
        "bot_settings": {
            "language": "hu",
            "check_interval_seconds": 60,
            "status_refresh_seconds": 60,
            "status_recreate_minutes": 58,
            "purge_limit": 1000
        },
        "bots": {
            "bot1": {
                "name": "Bot Alpha",
                "path": "C:\\bots\\alpha",
                "cmd": "python app.py",
                "log": "app.log"
            }
        }
    }
    errors = ConfigValidator.validate(valid_data)
    assert len(errors) == 0

def test_invalid_root_type():
    errors = ConfigValidator.validate(["not", "a", "dict"])
    assert len(errors) == 1
    assert "root" in errors[0].field

def test_invalid_bot_missing_fields():
    broken_data = {
        "bots": {
            "broken_bot": {
                "name": "",
                # path missing
                # cmd missing
            }
        }
    }
    errors = ConfigValidator.validate(broken_data)
    assert len(errors) >= 3
    fields = [e.field for e in errors]
    assert "bots['broken_bot'].name" in fields
    assert "bots['broken_bot'].path" in fields
    assert "bots['broken_bot'].cmd" in fields

def test_invalid_language_code():
    data = {
        "bot_settings": {
            "language": "unsupported_lang"
        }
    }
    errors = ConfigValidator.validate(data)
    assert any("language" in e.field for e in errors)

def test_negative_or_zero_intervals():
    data = {
        "bot_settings": {
            "status_refresh_seconds": 0,
            "purge_limit": -10,
            "stop_timeout": -1.0
        }
    }
    errors = ConfigValidator.validate(data)
    assert len(errors) >= 3
    fields = [e.field for e in errors]
    assert "bot_settings.status_refresh_seconds" in fields
    assert "bot_settings.purge_limit" in fields
    assert "bot_settings.stop_timeout" in fields

def test_validate_or_raise_raises_custom_exception():
    data = {"bots": {"bad": {}}}
    with pytest.raises(ConfigValidationError) as exc_info:
        ConfigValidator.validate_or_raise(data)
    assert "Configuration validation failed" in str(exc_info.value)
    assert "bots['bad'].name" in str(exc_info.value)

def test_config_repository_save_rejects_invalid_data(tmp_path):
    cfg_file = tmp_path / "valid_cfg.json"
    cfg_file.write_text("{}", encoding="utf-8")
    
    repo = ConfigRepository(str(cfg_file))
    
    invalid_data = {
        "bots": {
            "invalid_bot": {"name": ""}
        }
    }
    saved = repo.save(invalid_data)
    assert saved is False
    assert cfg_file.read_text(encoding="utf-8") == "{}"

def test_config_repository_load_stores_validation_errors(tmp_path):
    cfg_file = tmp_path / "invalid_cfg.json"
    invalid_json = {
        "bot_settings": {
            "language": "invalid_code"
        }
    }
    cfg_file.write_text(json.dumps(invalid_json), encoding="utf-8")
    
    repo = ConfigRepository(str(cfg_file))
    assert len(repo.validation_errors) >= 1
    assert "language" in repo.validation_errors[0].field
