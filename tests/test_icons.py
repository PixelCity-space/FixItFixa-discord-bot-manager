from core.icons import Icons

def test_icons_default_emojis():
    Icons.setup({})
    assert Icons.RESTART is not None
    assert Icons.UPDATE is not None
    assert Icons.STOP is not None
    assert Icons.SUCCESS is not None
    assert Icons.ERROR is not None
    assert Icons.WARNING is not None
    assert Icons.ROCKET is not None

def test_icons_custom_emoji_override():
    custom_cfg = {
        "emojis": {
            "ROCKET": "🚀",
            "SUCCESS": "👍",
            "CUSTOM_ACTION": "<:my_emoji:123456789012345678>"
        }
    }
    Icons.setup(custom_cfg)
    assert str(Icons.SUCCESS) == "👍"
    assert str(Icons.ROCKET) == "🚀"

def test_icons_string_representation():
    Icons.setup({})
    success_str = str(Icons.SUCCESS)
    assert len(success_str) > 0
    assert success_str == "✅"

def test_icons_fallback_handling():
    custom_cfg = {"emojis": {"WARNING": "⚠️"}}
    Icons.setup(custom_cfg)
    assert Icons.WARNING is not None
    assert str(Icons.WARNING) == "⚠️"

def test_icons_all_keys_populated():
    Icons.setup({})
    assert str(Icons.WRENCH) == "🔧"
    assert str(Icons.GEAR) == "⚙️"
    assert str(Icons.ALERT) == "🚨"
    assert str(Icons.LOG) == "📄"
    assert str(Icons.SHIELD) == "🛡️"
