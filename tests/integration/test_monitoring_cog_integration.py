import asyncio
from unittest.mock import AsyncMock, MagicMock

import discord

from bot.cogs.monitoring_cog import MonitoringCog
from core.config.models import AppConfig, BotSettingsConfig
from core.services.i18n_service import LocalizationService


def create_mock_bot():
    """Factory creating a properly-typed, deterministic mock BotManager."""
    app_cfg = AppConfig(guild_id="99999", bot_settings=BotSettingsConfig(language="hu"))
    bot = MagicMock()
    bot.manager_name = "FixItFixa"
    bot.app_cfg = app_cfg
    bot.config = {"bot_settings": {"language": "hu"}}
    bot.state = {"status_message_id": None, "status_channel_id": None}
    bot.state_repo = MagicMock()
    bot.state_repo.get.return_value = None
    bot.admin_channel_id = "11111"
    bot.public_channel_id = "22222"
    bot.admin_role_id = "33333"
    bot.tester_role_id = "44444"
    bot.access_control = {"roles": {"admin": "33333", "tester": "44444"}}
    bot.user = None
    bot.ui_settings = {}
    bot.i18n = LocalizationService("hu")
    bot.bots = {}
    return bot


def create_mock_member(user_id=11111, is_owner=False, is_admin=False):
    """Factory creating a properly-typed mock discord.Member."""
    user = MagicMock(spec=discord.Member)
    user.id = user_id
    user.guild = MagicMock()
    user.guild.owner_id = user_id if is_owner else 99999
    user.guild_permissions = MagicMock()
    user.guild_permissions.administrator = is_admin
    user.roles = []
    return user


async def invoke_slash_command(command, *args, **kwargs):
    """Safely invokes an app_commands.Command callback for testing."""
    callback_fn = getattr(command, "callback", command)
    return await callback_fn(*args, **kwargs)


async def invoke_task_loop(task_loop, *args, **kwargs):
    """Safely invokes a discord.ext.tasks.Loop coroutine for testing."""
    coro_fn = getattr(task_loop, "coro", task_loop)
    return await coro_fn(*args, **kwargs)


def test_e2e_info_command_private_flow():
    async def run():
        bot_mock = create_mock_bot()
        cog = MonitoringCog(bot_mock)

        interaction = MagicMock()
        interaction.user = create_mock_member(user_id=11111, is_owner=False, is_admin=False)
        interaction.guild = MagicMock()
        interaction.response.send_message = AsyncMock()

        await invoke_slash_command(cog.info, cog, interaction, public=False)

        interaction.response.send_message.assert_awaited_once()
        kwargs = interaction.response.send_message.call_args[1]
        assert kwargs.get("ephemeral") is True
        assert kwargs.get("view") is not None

    asyncio.run(run())


def test_e2e_info_command_public_admin_flow():
    async def run():
        bot_mock = create_mock_bot()
        cog = MonitoringCog(bot_mock)

        interaction = MagicMock()
        # Admin requests public card
        interaction.user = create_mock_member(user_id=99999, is_owner=True, is_admin=True)
        interaction.guild = MagicMock()
        interaction.response.send_message = AsyncMock()

        await invoke_slash_command(cog.info, cog, interaction, public=True)

        interaction.response.send_message.assert_awaited_once()
        kwargs = interaction.response.send_message.call_args[1]
        assert kwargs.get("ephemeral") is False
        assert kwargs.get("view") is not None

    asyncio.run(run())


def test_e2e_status_command_ephemeral_report_flow():
    async def run():
        bot_mock = create_mock_bot()
        telemetry_mock = MagicMock()
        telemetry_mock.get_status_snapshot.return_value = (
            {
                "cpu": 1.0,
                "ram": 50,
                "uptime": "1h",
                "branch": "main",
                "os": "Windows",
                "sys_cpu_free": 90,
                "sys_ram_free": 2000,
                "sys_disk_free": 100,
                "swap": 0,
                "host_uptime": "1d",
                "net": "1 KB/s",
                "has_update": False,
            },
            {},
        )
        bot_mock.telemetry_service = telemetry_mock
        bot_mock.get_cog.return_value = None

        cog = MonitoringCog(bot_mock)
        cog.git_fetch_task = AsyncMock()

        interaction = MagicMock()
        interaction.user = create_mock_member(user_id=11111, is_owner=False, is_admin=False)
        interaction.channel_id = "55555"  # Non-admin channel
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        await invoke_slash_command(cog.status, cog, interaction)

        interaction.response.defer.assert_awaited_once_with(ephemeral=True)
        interaction.followup.send.assert_awaited_once()
        kwargs = interaction.followup.send.call_args[1]
        assert kwargs.get("view") is not None
        assert kwargs.get("ephemeral") is True

    asyncio.run(run())


def test_e2e_status_command_admin_refresh_flow():
    async def run():
        bot_mock = create_mock_bot()
        telemetry_mock = MagicMock()
        telemetry_mock.get_status_snapshot.return_value = (
            {
                "cpu": 1.0,
                "ram": 50,
                "uptime": "1h",
                "branch": "main",
                "os": "Windows",
                "sys_cpu_free": 90,
                "sys_ram_free": 2000,
                "sys_disk_free": 100,
                "swap": 0,
                "host_uptime": "1d",
                "net": "1 KB/s",
                "has_update": False,
            },
            {},
        )
        bot_mock.telemetry_service = telemetry_mock
        bot_mock.get_cog.return_value = None

        cog = MonitoringCog(bot_mock)
        cog.git_fetch_task = AsyncMock()
        cog.cleanup_and_recreate_panel = AsyncMock()

        interaction = MagicMock()
        # Boss in admin workshop channel
        interaction.user = create_mock_member(user_id=99999, is_owner=True, is_admin=True)
        interaction.channel_id = "11111"  # Admin channel
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        await invoke_slash_command(cog.status, cog, interaction)

        interaction.response.defer.assert_awaited_once_with(ephemeral=True)
        cog.cleanup_and_recreate_panel.assert_awaited_once()
        interaction.followup.send.assert_awaited_once()
        sent_msg = interaction.followup.send.call_args[0][0]
        assert "újraépítve" in sent_msg.lower() or "friss" in sent_msg.lower() or "refresh" in sent_msg.lower()

    asyncio.run(run())


def test_e2e_monitoring_cog_status_update_loop_edition():
    async def run():
        bot_mock = create_mock_bot()
        telemetry_mock = MagicMock()
        telemetry_mock.get_status_snapshot.return_value = (
            {
                "cpu": 1.0,
                "ram": 50,
                "uptime": "1h",
                "branch": "main",
                "os": "Windows",
                "sys_cpu_free": 90,
                "sys_ram_free": 2000,
                "sys_disk_free": 100,
                "swap": 0,
                "host_uptime": "1d",
                "net": "1 KB/s",
                "has_update": False,
            },
            {},
        )
        bot_mock.telemetry_service = telemetry_mock
        bot_mock.get_cog.return_value = None

        mock_partial_msg = MagicMock()
        mock_partial_msg.edit = AsyncMock()
        mock_channel = MagicMock()
        mock_channel.get_partial_message = MagicMock(return_value=mock_partial_msg)
        bot_mock.get_channel = MagicMock(return_value=mock_channel)

        cog = MonitoringCog(bot_mock)
        cog.status_channel_id = "11111"
        cog.status_message_id = "999"

        await invoke_task_loop(cog.update_status_task, cog)

        mock_channel.get_partial_message.assert_called_once_with(999)
        mock_partial_msg.edit.assert_awaited_once()

    asyncio.run(run())


def test_e2e_monitoring_cog_on_ready_idempotency():
    async def run():
        bot_mock = create_mock_bot()
        cog = MonitoringCog(bot_mock)
        cog.cleanup_and_recreate_panel = AsyncMock()
        cog.update_status_task = MagicMock()
        cog.update_status_task.coro = AsyncMock()
        cog.update_status_task.is_running.return_value = True
        cog.recreate_status_task = MagicMock()
        cog.recreate_status_task.is_running.return_value = True
        cog.git_fetch_task = MagicMock()
        cog.git_fetch_task.is_running.return_value = True

        assert cog._initialized_panel is False

        # First on_ready -> recreates panel
        await cog.on_ready()
        cog.cleanup_and_recreate_panel.assert_awaited_once()
        assert cog._initialized_panel is True

        # Second on_ready (gateway reconnect) -> calls update_status_task, NOT cleanup_and_recreate_panel again!
        cog.cleanup_and_recreate_panel.reset_mock()
        await cog.on_ready()
        cog.cleanup_and_recreate_panel.assert_not_called()
        cog.update_status_task.coro.assert_awaited_once()

    asyncio.run(run())


def test_e2e_monitoring_cog_cleanup_and_recreate():
    async def run():
        bot_mock = create_mock_bot()
        telemetry_mock = MagicMock()
        telemetry_mock.get_status_snapshot.return_value = (
            {
                "cpu": 1.0,
                "ram": 50,
                "uptime": "1h",
                "branch": "main",
                "os": "Windows",
                "sys_cpu_free": 90,
                "sys_ram_free": 2000,
                "sys_disk_free": 100,
                "swap": 0,
                "host_uptime": "1d",
                "net": "1 KB/s",
                "has_update": False,
            },
            {},
        )
        bot_mock.telemetry_service = telemetry_mock
        bot_mock.get_cog.return_value = None

        mock_old_msg = MagicMock()
        mock_old_msg.delete = AsyncMock()

        mock_new_msg = MagicMock()
        mock_new_msg.id = 88888

        mock_channel = MagicMock()
        mock_channel.id = 11111
        mock_channel.fetch_message = AsyncMock(return_value=mock_old_msg)
        mock_channel.send = AsyncMock(return_value=mock_new_msg)
        bot_mock.get_channel = MagicMock(return_value=mock_channel)

        cog = MonitoringCog(bot_mock)
        cog.status_channel_id = "11111"
        cog.status_message_id = "999"

        await cog.cleanup_and_recreate_panel()

        mock_old_msg.delete.assert_awaited_once()
        mock_channel.send.assert_awaited_once()
        assert cog.status_message_id == "88888"

    asyncio.run(run())
