from unittest.mock import MagicMock
from core.utils import format_desc, get_feedback
from core.services.i18n_service import LocalizationService

def test_format_desc_replaces_placeholders():
    bot = MagicMock()
    bot.admin_channel_id = 111
    bot.public_channel_id = 222
    bot.admin_role_id = 333
    bot.tester_role_id = 444
    bot.manager_name = "FixItFixa"

    raw_desc = "Admin: {admin_channel} | Role: {admin_role} | Name: {bot_name}"
    res = format_desc(bot, raw_desc)
    assert "<#111>" in res
    assert "<@&333>" in res
    assert "FixItFixa" in res

def test_format_desc_missing_ids_fallback():
    bot = MagicMock()
    bot.admin_channel_id = None
    bot.public_channel_id = None
    bot.admin_role_id = None
    bot.tester_role_id = None
    bot.manager_name = None

    raw_desc = "Channel: {admin_channel}"
    res = format_desc(bot, raw_desc)
    assert "N/A" in res

def test_format_desc_empty_text():
    bot = MagicMock()
    assert format_desc(bot, "") == ""
    assert format_desc(bot, None) is None

def test_get_feedback_injects_icon_placeholders():
    service = LocalizationService("hu")
    msg = get_feedback(service, "uptime_days", d=5)
    assert "5" in msg
    assert "napja" in msg
