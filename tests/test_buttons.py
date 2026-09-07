import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from bot.ui.components.buttons import BotControlButton, PageButton, handle_status_interaction
from core.services.i18n_service import LocalizationService


def test_bot_control_button_custom_id():
    btn = BotControlButton(bot_id="iris", action="restart", bot_name="Iris")
    assert btn.custom_id == "status:iris:restart"
    assert btn.bot_id == "iris"
    assert btn.action == "restart"


def test_page_button_state():
    cog = MagicMock()
    # First page (prev button must be disabled)
    prev_btn = PageButton(direction=-1, cog=cog, current_page=0, total_pages=3, i18n=None)
    assert prev_btn.disabled is True

    # Mid page (prev button must be enabled)
    prev_btn_mid = PageButton(direction=-1, cog=cog, current_page=1, total_pages=3, i18n=None)
    assert prev_btn_mid.disabled is False

    # Last page (next button must be disabled)
    next_btn_last = PageButton(direction=1, cog=cog, current_page=2, total_pages=3, i18n=None)
    assert next_btn_last.disabled is True


def test_handle_status_interaction_permission_denied():
    async def run():
        interaction = MagicMock()
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.guild = MagicMock()
        interaction.user.guild.owner_id = 99999
        interaction.user.id = 11111
        interaction.user.guild_permissions = MagicMock()
        interaction.user.guild_permissions.administrator = False
        interaction.user.roles = []

        interaction.client.access_control = {"roles": {"admin": 555, "tester": 777}}
        interaction.client.i18n = LocalizationService("hu")
        interaction.response.send_message = AsyncMock()

        # Normal user tries to stop a bot (requires MECHANIC)
        await handle_status_interaction(interaction, "bot1", "stop")
        interaction.response.send_message.assert_awaited_once()
        sent_msg = interaction.response.send_message.call_args[0][0]
        assert "jogosult" in sent_msg or "admin" in sent_msg.lower() or "parancs" in sent_msg

    asyncio.run(run())


def test_handle_status_interaction_channel_restricted():
    async def run():
        interaction = MagicMock()
        # MECHANIC role
        role_admin = MagicMock()
        role_admin.id = 555
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.guild = MagicMock()
        interaction.user.guild.owner_id = 99999
        interaction.user.id = 11111
        interaction.user.guild_permissions = MagicMock()
        interaction.user.guild_permissions.administrator = False
        interaction.user.roles = [role_admin]

        interaction.channel_id = 999999  # Wrong channel
        interaction.client.admin_channel_id = 111111  # Official workshop channel
        interaction.client.access_control = {"roles": {"admin": 555, "tester": 777}}
        interaction.client.i18n = LocalizationService("hu")
        interaction.response.send_message = AsyncMock()

        await handle_status_interaction(interaction, "bot1", "stop")
        interaction.response.send_message.assert_awaited_once()

    asyncio.run(run())


def test_handle_status_interaction_stop_success():
    async def run():
        interaction = MagicMock()
        role_admin = MagicMock()
        role_admin.id = 555
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.guild = MagicMock()
        interaction.user.guild.owner_id = 99999
        interaction.user.id = 20001
        interaction.user.guild_permissions = MagicMock()
        interaction.user.guild_permissions.administrator = False
        interaction.user.roles = [role_admin]

        interaction.channel_id = 111111
        interaction.client.admin_channel_id = 111111
        interaction.client.access_control = {"roles": {"admin": 555, "tester": 777}}
        interaction.client.i18n = LocalizationService("hu")
        interaction.client.lifecycle_service = MagicMock()
        interaction.client.lifecycle_service.stop_bot = AsyncMock(return_value=(True, None))
        interaction.client.bots = {}

        interaction.response.send_message = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        await handle_status_interaction(interaction, "bot1", "stop", bot_name="Iris")
        interaction.client.lifecycle_service.stop_bot.assert_awaited_once_with("bot1")
        sent_msg = interaction.followup.send.call_args[0][0]
        assert "sikeresen leállítva" in sent_msg

    asyncio.run(run())


def test_handle_status_interaction_stop_sudo_failure():
    async def run():
        interaction = MagicMock()
        role_admin = MagicMock()
        role_admin.id = 555
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.guild = MagicMock()
        interaction.user.guild.owner_id = 99999
        interaction.user.id = 20002
        interaction.user.guild_permissions = MagicMock()
        interaction.user.guild_permissions.administrator = False
        interaction.user.roles = [role_admin]

        interaction.channel_id = 111111
        interaction.client.admin_channel_id = 111111
        interaction.client.access_control = {"roles": {"admin": 555, "tester": 777}}
        interaction.client.i18n = LocalizationService("hu")
        interaction.client.lifecycle_service = MagicMock()
        sudo_err = "Passwordless sudo required. Please configure sudoers: 'username ALL=(ALL) NOPASSWD: /bin/systemctl'"
        interaction.client.lifecycle_service.stop_bot = AsyncMock(return_value=(False, sudo_err))
        interaction.client.bots = {}

        interaction.response.send_message = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        await handle_status_interaction(interaction, "bot1", "stop", bot_name="Iris")
        interaction.client.lifecycle_service.stop_bot.assert_awaited_once_with("bot1")
        sent_msg = interaction.followup.send.call_args[0][0]
        assert "leállítása sikertelen" in sent_msg
        assert "Passwordless sudo required" in sent_msg

    asyncio.run(run())


def test_handle_status_interaction_restart_sudo_failure():
    async def run():
        from core.config.models import BotConfig

        interaction = MagicMock()
        role_admin = MagicMock()
        role_admin.id = 555
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.guild = MagicMock()
        interaction.user.guild.owner_id = 99999
        interaction.user.id = 20003
        interaction.user.guild_permissions = MagicMock()
        interaction.user.guild_permissions.administrator = False
        interaction.user.roles = [role_admin]

        interaction.channel_id = 111111
        interaction.client.admin_channel_id = 111111
        interaction.client.access_control = {"roles": {"admin": 555, "tester": 777}}
        interaction.client.i18n = LocalizationService("hu")
        interaction.client.lifecycle_service = MagicMock()
        b_cfg = BotConfig(id="bot1", name="Iris", path="C:\\test", cmd="python iris.py")
        sudo_err = "Cannot start systemd service 'iris': Passwordless sudo required"
        interaction.client.lifecycle_service.restart_bot_cluster = AsyncMock(return_value=[(b_cfg, None, sudo_err)])
        interaction.client.notify_admin = AsyncMock()
        interaction.client.bots = {}

        interaction.response.send_message = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        await handle_status_interaction(interaction, "bot1", "restart", bot_name="Iris")
        sent_msg = interaction.followup.send.call_args[0][0]
        assert "hiba:" in sent_msg
        assert "Passwordless sudo required" in sent_msg
        interaction.client.notify_admin.assert_not_called()

    asyncio.run(run())


def test_handle_status_interaction_page_navigation():
    async def run():
        interaction = MagicMock()
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.guild = MagicMock()
        interaction.user.guild.owner_id = 99999
        interaction.user.id = 999
        interaction.user.guild_permissions = MagicMock()
        interaction.user.guild_permissions.administrator = False
        role_tester = MagicMock()
        role_tester.id = 777
        interaction.user.roles = [role_tester]
        interaction.client.access_control = {"roles": {"admin": 555, "tester": 777}}

        interaction.response.is_done.return_value = False
        interaction.response.defer = AsyncMock()

        mock_monitor = MagicMock()
        mock_monitor.change_page = AsyncMock()
        interaction.client.get_cog.return_value = mock_monitor

        # Test next page
        await handle_status_interaction(interaction, "page", "next")
        interaction.response.defer.assert_awaited_once()
        mock_monitor.change_page.assert_awaited_once_with(1)

        # Test prev page with different user
        interaction.user.id = 1000
        mock_monitor.change_page.reset_mock()
        await handle_status_interaction(interaction, "page", "prev")
        mock_monitor.change_page.assert_awaited_once_with(-1)

    asyncio.run(run())


def test_handle_status_interaction_page_navigation_unauthorized():
    async def run():
        interaction = MagicMock()
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.guild = MagicMock()
        interaction.user.guild.owner_id = 99999
        interaction.user.id = 55555
        interaction.user.guild_permissions = MagicMock()
        interaction.user.guild_permissions.administrator = False
        interaction.user.roles = []
        interaction.channel_id = 444
        interaction.client.admin_channel_id = 999
        interaction.client.access_control = {"roles": {"admin": 555, "tester": 777}}
        interaction.client.i18n = LocalizationService("hu")

        interaction.response.is_done.return_value = False
        interaction.response.send_message = AsyncMock()
        interaction.response.defer = AsyncMock()

        mock_monitor = MagicMock()
        mock_monitor.change_page = AsyncMock()
        interaction.client.get_cog.return_value = mock_monitor

        await handle_status_interaction(interaction, "page", "next")
        interaction.response.send_message.assert_awaited_once()
        mock_monitor.change_page.assert_not_called()

    asyncio.run(run())


def test_handle_status_interaction_manager_restart_and_update():
    async def run():
        interaction = MagicMock()
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.guild = MagicMock()
        interaction.user.guild.owner_id = 99999
        interaction.user.id = 99999
        interaction.user.guild_permissions = MagicMock()
        interaction.user.guild_permissions.administrator = True
        interaction.user.roles = []
        interaction.client.access_control = {"roles": {}}
        interaction.client.i18n = LocalizationService("hu")
        interaction.client.update_service = MagicMock()
        interaction.client.spawner = MagicMock()
        interaction.client.cleanup_status_panel = AsyncMock()
        interaction.client.manager_name = "Fixa"
        interaction.client.ui_settings = {}
        interaction.response.send_message = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            # Manager restart
            await handle_status_interaction(interaction, "manager", "restart")
            interaction.client.update_service.prepare_manager_restart.assert_called_once()
            interaction.followup.send.assert_awaited()
            interaction.client.spawner.execute_manager_restart.assert_called_once()

            # Manager update
            interaction.client.update_service.update_manager = AsyncMock(
                return_value=(True, "Success", True, {"hash": "abc", "author": "dev", "message": "fix"})
            )
            await handle_status_interaction(interaction, "manager", "update")
            interaction.client.update_service.update_manager.assert_awaited_once()

    asyncio.run(run())


def test_handle_status_interaction_start_and_update_bot():
    async def run():
        from core.config.models import BotConfig

        interaction = MagicMock()
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.guild = MagicMock()
        interaction.user.guild.owner_id = 99999
        interaction.user.id = 99999
        interaction.user.guild_permissions = MagicMock()
        interaction.user.guild_permissions.administrator = True
        interaction.user.roles = []
        interaction.client.access_control = {"roles": {}}
        interaction.client.i18n = LocalizationService("hu")
        interaction.client.lifecycle_service = MagicMock()
        interaction.client.update_service = MagicMock()
        interaction.client.notify_admin = AsyncMock()
        bot_cfg = BotConfig(id="bot1", name="Bot 1", path=".", cmd="python app.py")
        interaction.client.bots = {"bot1": bot_cfg}
        interaction.client.ui_settings = {}
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        # Restart bot cluster
        interaction.client.lifecycle_service.restart_bot_cluster = AsyncMock(return_value=[(bot_cfg, 7890, None)])
        await handle_status_interaction(interaction, "bot1", "restart", bot_name="Bot 1")
        interaction.client.lifecycle_service.restart_bot_cluster.assert_awaited_once_with("bot1")
        interaction.client.notify_admin.assert_awaited_once()

        # Update bot
        interaction.client.update_service.update_bot = AsyncMock(
            return_value=(True, "Updated", True, {"hash": "def", "author": "dev", "message": "msg"}, [])
        )
        await handle_status_interaction(interaction, "bot1", "update", bot_name="Bot 1")
        interaction.client.update_service.update_bot.assert_awaited_once_with("bot1")

    asyncio.run(run())
