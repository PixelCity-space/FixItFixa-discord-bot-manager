import asyncio
from unittest.mock import AsyncMock, MagicMock
from core.services.i18n_service import LocalizationService
from bot.cogs.system_cog import SystemCog

async def invoke_command(command, *args, **kwargs):
    """Safely invokes a commands.Command or app_commands.Command callback for testing."""
    callback_fn = getattr(command, "callback", command)
    return await callback_fn(*args, **kwargs)

def test_e2e_ping_prefix_flow():
    async def run():
        bot_mock = MagicMock()
        bot_mock.latency = 0.042  # 42ms
        bot_mock.i18n = LocalizationService("hu")

        cog = SystemCog(bot_mock)

        ctx = MagicMock()
        ctx.send = AsyncMock()

        await invoke_command(cog.ping_prefix, cog, ctx)

        ctx.send.assert_awaited_once()
        sent_text = ctx.send.call_args[0][0]
        assert "42" in sent_text

    asyncio.run(run())

def test_e2e_sync_slash_command_flow():
    async def run():
        bot_mock = MagicMock()
        bot_mock.guild_id = 99999
        bot_mock.i18n = LocalizationService("hu")
        bot_mock.cogs = {}

        cmd_mocks = [MagicMock() for _ in range(12)]
        bot_mock.tree.sync = AsyncMock(return_value=cmd_mocks)

        cog = SystemCog(bot_mock)

        interaction = MagicMock()
        interaction.client = bot_mock
        interaction.guild = MagicMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        await invoke_command(cog.sync_slash, cog, interaction, mode="guild")

        bot_mock.tree.sync.assert_awaited_once()
        interaction.followup.send.assert_awaited_once()
        sent_text = interaction.followup.send.call_args[0][0]
        assert "12" in sent_text

    asyncio.run(run())

def test_e2e_clear_commands_prefix_flow():
    async def run():
        bot_mock = MagicMock()
        bot_mock.guild_id = 99999
        bot_mock.i18n = LocalizationService("hu")
        bot_mock.tree.clear_commands = MagicMock()
        bot_mock.tree.sync = AsyncMock(return_value=[])

        cog = SystemCog(bot_mock)

        ctx = MagicMock()
        ctx.author = "AdminUser"
        ctx.guild = MagicMock()
        ctx.send = AsyncMock()

        await invoke_command(cog.clear_commands_prefix, cog, ctx)

        bot_mock.tree.clear_commands.assert_called()
        bot_mock.tree.sync.assert_awaited()
        assert ctx.send.await_count >= 2

    asyncio.run(run())

def test_e2e_purge_slash_command_flow():
    async def run():
        bot_mock = MagicMock()
        bot_mock.i18n = LocalizationService("hu")
        bot_mock.access_control = {"roles": {"admin": 555}}

        cog = SystemCog(bot_mock)

        interaction = MagicMock()
        interaction.user = MagicMock()
        interaction.user.guild = MagicMock()
        interaction.user.guild.owner_id = 99999
        interaction.user.id = 99999  # BOSS
        interaction.channel = MagicMock()
        interaction.channel.name = "general"
        interaction.channel.purge = AsyncMock(return_value=[MagicMock() for _ in range(15)])
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        await invoke_command(cog.purge, cog, interaction)

        interaction.channel.purge.assert_awaited_once()
        interaction.followup.send.assert_awaited_once()
        sent_text = interaction.followup.send.call_args[0][0]
        assert "15" in sent_text

    asyncio.run(run())
