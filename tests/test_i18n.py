import json
import os
from core.services.i18n_service import LocalizationService
from core.utils import get_feedback
from core.icons import Icons

def test_i18n_loads_hungarian_and_english():
    hu_service = LocalizationService("hu")
    assert hu_service.current_lang == "hu"
    assert len(hu_service.translations) > 0

    en_service = LocalizationService("en")
    assert en_service.current_lang == "en"
    assert len(en_service.translations) > 0

def test_i18n_key_synchronization():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hu_path = os.path.join(base_dir, "locales", "hu.json")
    en_path = os.path.join(base_dir, "locales", "en.json")

    with open(hu_path, "r", encoding="utf-8") as f:
        hu_keys = set(json.load(f).keys())
    with open(en_path, "r", encoding="utf-8") as f:
        en_keys = set(json.load(f).keys())

    missing_in_en = hu_keys - en_keys
    missing_in_hu = en_keys - hu_keys

    assert missing_in_en == set(), f"Keys in hu.json but missing in en.json: {missing_in_en}"
    assert missing_in_hu == set(), f"Keys in en.json but missing in hu.json: {missing_in_hu}"
    assert len(hu_keys) == len(en_keys)

def test_i18n_variable_formatting():
    service = LocalizationService("hu")
    formatted = service.get("restart_success", name="Alpha", pid=4567)
    assert "Alpha" in formatted
    assert "4567" in formatted

def test_i18n_icon_placeholder_replacement():
    service = LocalizationService("hu")
    service.translations["test_icon_key"] = "{SUCCESS} Operation finished {ROCKET}"
    res = service.get("test_icon_key")
    assert "{SUCCESS}" not in res
    assert "{ROCKET}" not in res
    assert str(Icons.SUCCESS) in res

def test_get_feedback_fallback_and_emojis():
    service = LocalizationService("hu")
    msg = get_feedback(service, "restart_success", name="TestBot", pid=9999)
    assert "TestBot" in msg
    assert "9999" in msg

def test_i18n_missing_key_fallback():
    service = LocalizationService("hu")
    res = service.get("non_existent_key_12345")
    assert res == "non_existent_key_12345"

def test_i18n_pluralization_english_days():
    service = LocalizationService("en")
    assert service.get("uptime_days", d=1) == "1 day ago"
    assert service.get("uptime_days", d=5) == "5 days ago"

def test_i18n_pluralization_english_hours_and_minutes():
    service = LocalizationService("en")
    assert service.get("uptime_hours", h=1) == "1 hour ago"
    assert service.get("uptime_hours", h=3) == "3 hours ago"
    assert service.get("uptime_minutes", m=1) == "1 minute ago"
    assert service.get("uptime_minutes", m=12) == "12 minutes ago"

def test_i18n_pluralization_english_activity_and_logs():
    service = LocalizationService("en")
    assert service.get("activity_text", count=1) == "Monitoring 1 bot..."
    assert service.get("activity_text", count=4) == "Monitoring 4 bots..."
    assert service.get("logs_header", name="Alpha", lines=1) == "**Alpha** last 1 line:"
    assert service.get("logs_header", name="Alpha", lines=20) == "**Alpha** last 20 lines:"

def test_i18n_pluralization_hungarian_behavior():
    hu = LocalizationService("hu")
    assert hu.get("uptime_days", d=1) == "1 napja"
    assert hu.get("uptime_days", d=5) == "5 napja"

def test_i18n_explicit_get_plural_method():
    service = LocalizationService("en")
    res_one = service.get_plural("uptime_hours", count=1, h=1)
    res_other = service.get_plural("uptime_hours", count=5, h=5)
    assert res_one == "1 hour ago"
    assert res_other == "5 hours ago"

def test_i18n_plural_category_evaluator():
    service = LocalizationService("hu")
    assert service.get_plural_category("hu", 1) == "other"
    assert service.get_plural_category("hu", 5) == "other"
    assert service.get_plural_category("en", 1) == "one"
    assert service.get_plural_category("en", 0) == "other"
    assert service.get_plural_category("en", 2) == "other"
