from unittest.mock import MagicMock

from core.services.i18n_service import LocalizationService
from core.utils import format_desc, get_feedback


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


def test_read_file_tail_basic_and_edge_cases(tmp_path):
    from core.utils import read_file_tail

    # Non-existent file
    assert read_file_tail(str(tmp_path / "missing.txt"), 10) == []

    # 0 or negative lines
    assert read_file_tail(str(tmp_path / "any.txt"), 0) == []
    assert read_file_tail(str(tmp_path / "any.txt"), -5) == []

    # Empty file
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")
    assert read_file_tail(str(empty_file), 10) == []

    # Multi-line file
    test_file = tmp_path / "test.log"
    lines = [f"Line {i}\n" for i in range(1, 101)]
    test_file.write_text("".join(lines), encoding="utf-8")

    # Read last 5 lines
    tail5 = read_file_tail(str(test_file), 5, buffer_size=32)
    assert len(tail5) == 5
    assert tail5 == ["Line 96\n", "Line 97\n", "Line 98\n", "Line 99\n", "Line 100\n"]

    # Read more lines than exist
    tail200 = read_file_tail(str(test_file), 200, buffer_size=64)
    assert len(tail200) == 100
    assert tail200[0] == "Line 1\n"
    assert tail200[-1] == "Line 100\n"
