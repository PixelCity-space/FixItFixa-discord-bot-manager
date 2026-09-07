from core.common.constants import (
    truncate_message,
)
from core.common.icon_mappings import resolve_icon_for_key
from core.icons import Icons
from core.services.i18n_service import LocalizationService
from core.utils import get_feedback


def test_truncate_message_short_text():
    short = "Hello, world!"
    assert truncate_message(short) == short


def test_truncate_message_empty():
    assert truncate_message("") == ""
    assert truncate_message(None) is None


def test_truncate_message_long_text():
    long_text = "A" * 3000
    res = truncate_message(long_text, max_len=1900, head_len=1000, tail_len=800)
    assert len(res) < 3000
    assert "... [TRUNCATED] ..." in res
    assert res.startswith("A" * 1000)
    assert res.endswith("A" * 800)


def test_truncate_message_custom_separator():
    long_text = "B" * 2000
    res = truncate_message(long_text, max_len=500, head_len=100, tail_len=100, separator=" [CUT] ")
    assert res == ("B" * 100) + " [CUT] " + ("B" * 100)


def test_icon_mappings_resolutions():
    # Direct mapping
    err_icon = resolve_icon_for_key("error_generic")
    assert err_icon == Icons.ERROR

    # Case insensitive
    warn_icon = resolve_icon_for_key("UPDATE_AVAILABLE")
    assert warn_icon == Icons.WARNING

    # Alert mapping
    alert_icon = resolve_icon_for_key("bot_stopped_alert")
    assert alert_icon == Icons.ALERT

    # Functional icon
    restart_icon = resolve_icon_for_key("RESTART")
    assert restart_icon == Icons.RESTART

    # Fallback keyword matching
    custom_err = resolve_icon_for_key("some_custom_error_key")
    assert custom_err == Icons.ERROR

    custom_succ = resolve_icon_for_key("some_custom_success_key")
    assert custom_succ == Icons.SUCCESS

    custom_warn = resolve_icon_for_key("some_custom_warning_key")
    assert custom_warn == Icons.WARNING

    # Unmapped empty
    unmapped = resolve_icon_for_key("non_existent_key_xyz")
    assert unmapped == ""


def test_get_feedback_with_refactored_mapping():
    i18n = LocalizationService("hu")
    msg = get_feedback(i18n, "restart_success", name="BotZilla", pid=9999)
    assert "BotZilla" in msg
    assert "9999" in msg

    # Fallback keyword
    err_msg = get_feedback(i18n, "custom_error_something", default="Hiba van")
    assert "Hiba van" in err_msg
