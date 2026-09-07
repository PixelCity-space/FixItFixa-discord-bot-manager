from bot.ui.embeds.update_result import UpdateResultEmbed
from core.services.i18n_service import LocalizationService


def test_update_result_embed_success():
    i18n = LocalizationService("hu")
    details = {
        "message": "Feat: Add new slash command",
        "hash": "a1b2c3d",
        "date": 1700000000,
        "pip_status": "OK",
        "repo_url": "https://github.com/test/repo",
    }

    embed = UpdateResultEmbed(i18n, "Update Result", details, is_rollback=False)
    assert embed.title == "Update Result"
    assert "Feat: Add new slash command" in embed.description
    assert embed.color.value == 0x2ECC71  # Green
    assert any("a1b2c3d" in f.value for f in embed.fields)
    assert any("OK" in f.value for f in embed.fields)
    assert any("github.com" in f.value for f in embed.fields)


def test_update_result_embed_rollback():
    i18n = LocalizationService("hu")
    details = {"message": "Revert to previous commit", "hash": "f9e8d7c", "date": 1700000000}

    embed = UpdateResultEmbed(i18n, "Rollback Result", details, is_rollback=True)
    assert embed.title == "Rollback Result"
    assert embed.color.value == 0xE67E22  # Orange


def test_update_result_embed_custom_ui_settings():
    i18n = LocalizationService("hu")
    details = {"message": "Custom style", "hash": "123", "date": 1700000000}
    ui_settings = {"update_success_color": 0x3498DB, "update_rollback_color": 0x9B59B6}

    embed_success = UpdateResultEmbed(i18n, "Custom Success", details, ui_settings=ui_settings, is_rollback=False)
    assert embed_success.color.value == 0x3498DB

    embed_rollback = UpdateResultEmbed(i18n, "Custom Rollback", details, ui_settings=ui_settings, is_rollback=True)
    assert embed_rollback.color.value == 0x9B59B6


def test_update_result_embed_minimal_details():
    i18n = LocalizationService("hu")
    embed = UpdateResultEmbed(i18n, "Minimal", None)
    assert embed.title == "Minimal"
    assert embed.description is not None
