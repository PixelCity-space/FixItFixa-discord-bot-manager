from core.config.models import AppConfig, AppConfigDict, BotConfigDict, UiConfig, UiSettingsDict
from core.icons import Icons


def test_ui_config_defaults_and_from_dict():
    # Defaults
    ui_default = UiConfig()
    assert ui_default.status_panel_title is None
    assert ui_default.show_host_metrics is True
    assert ui_default.items_per_page == 6

    # From dict
    raw = {
        "status_panel_title": "Production Bot Fleet",
        "show_host_metrics": False,
        "show_bot_ram": True,
        "show_bot_cpu": False,
        "items_per_page": 8,
        "theme_color": 0x3498DB,
    }
    ui_custom = UiConfig.from_dict(raw)
    assert ui_custom.status_panel_title == "Production Bot Fleet"
    assert ui_custom.show_host_metrics is False
    assert ui_custom.show_bot_cpu is False
    assert ui_custom.items_per_page == 8
    assert ui_custom.theme_color == 0x3498DB
    assert ui_custom.raw == raw


def test_app_config_typed_ui_integration():
    raw_cfg = {
        "settings": {"guild_id": "111222333444"},
        "ui_settings": {"status_panel_title": "Main Cluster", "items_per_page": 4},
        "bots": {},
    }

    app_cfg = AppConfig.from_dict(raw_cfg)
    assert isinstance(app_cfg.ui, UiConfig)
    assert app_cfg.ui.status_panel_title == "Main Cluster"
    assert app_cfg.ui.items_per_page == 4


def test_typed_dict_structures():
    ui_dict: UiSettingsDict = {"status_panel_title": "Test Title", "show_host_metrics": True, "items_per_page": 5}
    assert ui_dict["items_per_page"] == 5

    bot_dict: BotConfigDict = {"name": "IrisBot", "path": "/srv/bots/iris", "cmd": "python app.py"}
    assert bot_dict["name"] == "IrisBot"

    app_dict: AppConfigDict = {"guild_id": "123456", "ui_settings": ui_dict, "bots": {"iris": bot_dict}}
    assert app_dict["guild_id"] == "123456"


def test_icons_classvar_annotations():
    annotations = Icons.__annotations__
    assert "RESTART" in annotations
    assert "UPDATE" in annotations
    assert "STOP" in annotations
    assert "ClassVar" in str(annotations["RESTART"])
