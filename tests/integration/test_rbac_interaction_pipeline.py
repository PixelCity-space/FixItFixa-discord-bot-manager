import asyncio
import discord
from unittest.mock import AsyncMock, MagicMock
from core.services.i18n_service import LocalizationService
from bot.ui.components.buttons import handle_status_interaction

def test_e2e_rbac_unprivileged_user_blocked():
    async def run():
        interaction = MagicMock()
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.guild = MagicMock()
        interaction.user.guild.owner_id = 99999
        interaction.user.id = 10001
        interaction.user.guild_permissions = MagicMock()
        interaction.user.guild_permissions.administrator = False
        interaction.user.roles = []

        interaction.client.access_control = {"roles": {"admin": 555, "tester": 777}}
        interaction.client.i18n = LocalizationService("hu")
        interaction.response.send_message = AsyncMock()

        # Unprivileged user attempts restart
        await handle_status_interaction(interaction, "bot1", "restart")
        interaction.response.send_message.assert_awaited_once()
        sent_msg = interaction.response.send_message.call_args[0][0]
        assert "jogosult" in sent_msg or "admin" in sent_msg.lower() or "parancs" in sent_msg

    asyncio.run(run())

def test_e2e_rbac_inspector_can_restart_but_not_stop():
    async def run():
        role_tester = MagicMock()
        role_tester.id = 777

        interaction = MagicMock()
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.guild = MagicMock()
        interaction.user.guild.owner_id = 99999
        interaction.user.id = 10002
        interaction.user.guild_permissions = MagicMock()
        interaction.user.guild_permissions.administrator = False
        interaction.user.roles = [role_tester]

        interaction.channel_id = 12345
        interaction.client.admin_channel_id = 12345
        interaction.client.access_control = {"roles": {"admin": 555, "tester": 777}}
        interaction.client.i18n = LocalizationService("hu")
        interaction.client.lifecycle_service.restart_bot_cluster = AsyncMock(return_value=[])
        interaction.client.notify_admin = AsyncMock()
        interaction.client.bots = {}

        interaction.response.send_message = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        # 1. Inspector CAN restart
        await handle_status_interaction(interaction, "bot1", "restart")
        interaction.response.defer.assert_awaited_once()

        # 2. Inspector CANNOT stop (requires MECHANIC)
        interaction.response.send_message.reset_mock()
        interaction.response.defer.reset_mock()
        await handle_status_interaction(interaction, "bot1", "stop")
        interaction.response.send_message.assert_awaited_once()

    asyncio.run(run())

def test_e2e_rbac_mechanic_can_restart_and_stop():
    async def run():
        role_admin = MagicMock()
        role_admin.id = 555

        interaction = MagicMock()
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.guild = MagicMock()
        interaction.user.guild.owner_id = 99999
        interaction.user.id = 10003
        interaction.user.guild_permissions = MagicMock()
        interaction.user.guild_permissions.administrator = False
        interaction.user.roles = [role_admin]

        interaction.channel_id = 12345
        interaction.client.admin_channel_id = 12345
        interaction.client.access_control = {"roles": {"admin": 555, "tester": 777}}
        interaction.client.i18n = LocalizationService("hu")
        interaction.client.lifecycle_service.stop_bot = AsyncMock()
        interaction.client.lifecycle_service.restart_bot_cluster = AsyncMock(return_value=[])
        interaction.client.notify_admin = AsyncMock()
        interaction.client.bots = {}

        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        # Mechanic can stop
        await handle_status_interaction(interaction, "bot1", "stop")
        interaction.response.defer.assert_awaited_once()
        interaction.client.lifecycle_service.stop_bot.assert_awaited_once_with("bot1")

    asyncio.run(run())

def test_e2e_rbac_guild_owner_boss_bypass_channel_restriction():
    async def run():
        interaction = MagicMock()
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.guild = MagicMock()
        interaction.user.guild.owner_id = 99999
        interaction.user.id = 99999  # Guild Owner = BOSS
        interaction.user.guild_permissions = MagicMock()
        interaction.user.roles = []

        interaction.channel_id = 88888  # Any random channel
        interaction.client.admin_channel_id = 12345
        interaction.client.access_control = {"roles": {"admin": 555, "tester": 777}}
        interaction.client.i18n = LocalizationService("hu")
        interaction.client.lifecycle_service.stop_bot = AsyncMock()
        interaction.client.bots = {}

        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        # BOSS can execute action from any channel
        await handle_status_interaction(interaction, "bot1", "stop")
        interaction.response.defer.assert_awaited_once()
        interaction.client.lifecycle_service.stop_bot.assert_awaited_once_with("bot1")

    asyncio.run(run())
