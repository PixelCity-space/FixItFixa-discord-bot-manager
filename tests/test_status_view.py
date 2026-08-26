from unittest.mock import MagicMock
from bot.ui.views.status_view import ModernStatusView
from bot.ui.views.info_view import ModernInfoView
from core.services.i18n_service import LocalizationService

def test_modern_status_view_single_page():
    bot = MagicMock()
    bot.manager_name = "FixItFixa"
    bot.ui_settings = {"accent_color": 0x123456}

    i18n = LocalizationService("hu")
    mgr_stats = {
        "cpu": 1.5,
        "ram": 60,
        "uptime": "2 órája",
        "branch": "origin/main",
        "os": "Windows 10",
        "sys_cpu_free": 80,
        "sys_ram_free": 4000,
        "sys_disk_free": 100,
        "swap": 10,
        "host_uptime": "5 napja",
        "net": "10 KB/s",
        "has_update": False
    }
    bots_stats = {
        "b1": {
            "name": "Bot 1",
            "path": "C:\\b1",
            "status": "🔴 Nem fut",
            "is_running": False,
            "log_size": "10 KB",
            "db_sizes": {}
        }
    }

    view = ModernStatusView(bot, i18n, mgr_stats, bots_stats, current_page=0)
    assert view is not None
    assert len(view.children) >= 1

def test_modern_status_view_multi_page_pagination():
    bot = MagicMock()
    bot.manager_name = "FixItFixa"
    bot.ui_settings = {}
    bot.get_cog.return_value = MagicMock()

    i18n = LocalizationService("hu")
    mgr_stats = {
        "cpu": 0, "ram": 50, "uptime": "1h", "branch": "main", "os": "Linux",
        "sys_cpu_free": 50, "sys_ram_free": 1000, "sys_disk_free": 50, "swap": 0,
        "host_uptime": "1d", "net": "1 KB/s", "has_update": False
    }
    # 6 distinct paths -> requires multiple pages
    bots_stats = {
        f"b{i}": {
            "name": f"Bot {i}",
            "path": f"C:\\bots\\b{i}",
            "status": "🔴 Nem fut",
            "is_running": False,
            "log_size": "N/A",
            "db_sizes": {}
        }
        for i in range(6)
    }

    view = ModernStatusView(bot, i18n, mgr_stats, bots_stats, current_page=0)
    assert view is not None

def test_modern_info_view_structure():
    bot = MagicMock()
    bot.manager_name = "FixItFixa"
    bot.admin_channel_id = 111
    bot.public_channel_id = 222
    bot.admin_role_id = 333
    bot.tester_role_id = 444
    bot.user = None
    bot.ui_settings = {"accent_color": 0x2b2d31}

    i18n = LocalizationService("hu")
    view = ModernInfoView(bot, i18n)
    assert view is not None
    assert len(view.children) >= 1
