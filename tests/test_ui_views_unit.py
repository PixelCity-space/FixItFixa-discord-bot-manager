import pytest
import discord
from unittest.mock import AsyncMock, MagicMock
from bot.ui.views.info_view import ModernInfoView
from bot.ui.views.status_view import ModernStatusView, StatusContainer
from bot.ui.embeds.update_result import UpdateResultEmbed
from bot.ui.components.buttons import BotControlButton, PageButton, handle_status_interaction

def test_modern_info_view_structure(mock_bot, mock_i18n):
    view = ModernInfoView(mock_bot, mock_i18n)
    assert len(view.children) > 0

def test_update_result_embed_success_and_fields(mock_i18n):
    details = {
        "message": "Updated to latest HEAD",
        "hash": "abcdef1",
        "date": "1700000000",
        "pip_status": "OK",
        "repo_url": "https://github.com/repo/test"
    }
    embed = UpdateResultEmbed(mock_i18n, title="Bot Updated", details=details, is_rollback=False)
    assert embed.title == "Bot Updated"
    assert len(embed.fields) >= 3

def test_update_result_embed_rollback(mock_i18n):
    details = {
        "message": "Rolled back",
        "hash": "1234567"
    }
    embed = UpdateResultEmbed(mock_i18n, title="Bot Rollback", details=details, is_rollback=True)
    assert embed.title == "Bot Rollback"

def test_modern_status_view_single_and_multi_page(mock_bot, mock_i18n):
    manager_stats = {
        "cpu": 1.5, "ram": 45, "uptime": "2h", "branch": "main",
        "os": "Windows", "sys_cpu_free": 80, "sys_ram_free": 4000,
        "sys_disk_free": 100, "swap": 0, "host_uptime": "5d", "net": "↓0B ↑0B"
    }
    bots_stats = {
        "b1": {"name": "Bot 1", "path": "C:\\path1", "is_running": True, "status": "Running", "cpu": 0.5, "ram": 20, "uptime": "1h", "log_size": "1MB"},
        "b2": {"name": "Bot 2", "path": "C:\\path2", "is_running": False, "status": "Stopped", "log_size": "500KB"},
    }

    # 2 bots -> 1 page
    view_single = ModernStatusView(mock_bot, mock_i18n, manager_stats, bots_stats, current_page=0)
    assert len(view_single.children) == 1

    # 6 bots -> multiple pages
    more_bots = {
        f"b{i}": {"name": f"Bot {i}", "path": f"C:\\path_{i}", "is_running": True, "status": "Running", "cpu": 0.1, "ram": 10, "log_size": "10KB"}
        for i in range(1, 7)
    }
    view_multi = ModernStatusView(mock_bot, mock_i18n, manager_stats, more_bots, current_page=0)
    assert len(view_multi.children) == 1

async def test_bot_control_button_callback(mock_interaction):
    btn = BotControlButton(
        style=discord.ButtonStyle.secondary,
        emoji="🔄",
        bot_id="b1",
        bot_name="Bot 1",
        action="restart"
    )
    with pytest.MonkeyPatch.context() as mp:
        mock_handler = AsyncMock()
        mp.setattr("bot.ui.components.buttons.handle_status_interaction", mock_handler)
        await btn.callback(mock_interaction)
        mock_handler.assert_awaited_once_with(mock_interaction, "b1", "restart", "Bot 1")

async def test_page_button_callback(mock_interaction, mock_i18n):
    mock_cog = MagicMock()
    mock_cog.current_page = 0
    mock_cog.update_status_task = AsyncMock()
    
    btn = PageButton(direction=1, cog=mock_cog, current_page=0, total_pages=3, i18n=mock_i18n)
    await btn.callback(mock_interaction)
    
    assert mock_cog.current_page == 1
    mock_cog.update_status_task.assert_awaited_once()
    mock_interaction.response.defer.assert_awaited_once()
