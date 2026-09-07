import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.system_cog import SystemCog
from core.services.i18n_service import LocalizationService


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


def test_e2e_clear_commands_prefix_guild_flow():
    async def run():
        bot_mock = MagicMock()
        bot_mock.guild_id = 99999
        bot_mock.i18n = LocalizationService("hu")
        bot_mock.tree.clear_commands = MagicMock()
        bot_mock.tree.sync = AsyncMock(return_value=[])

        cog = SystemCog(bot_mock)

        ctx = MagicMock()
        ctx.author = MagicMock()
        ctx.guild = MagicMock()
        ctx.guild.id = 99999
        ctx.send = AsyncMock()

        await invoke_command(cog.clear_commands_prefix, cog, ctx)

        bot_mock.tree.clear_commands.assert_called_once_with(guild=ctx.guild)
        bot_mock.tree.sync.assert_awaited_once_with(guild=ctx.guild)
        assert ctx.send.await_count >= 2

    asyncio.run(run())


def test_e2e_clear_commands_prefix_global_flow():
    async def run():
        bot_mock = MagicMock()
        bot_mock.owner_id = 12345
        bot_mock.i18n = LocalizationService("hu")
        bot_mock.tree.clear_commands = MagicMock()
        bot_mock.tree.sync = AsyncMock(return_value=[])

        cog = SystemCog(bot_mock)

        # 1. Non-owner attempt -> Rejected
        ctx_unauthorized = MagicMock()
        ctx_unauthorized.author = MagicMock()
        ctx_unauthorized.author.id = 99999
        ctx_unauthorized.send = AsyncMock()
        await invoke_command(cog.clear_commands_prefix, cog, ctx_unauthorized, spec="global")
        bot_mock.tree.clear_commands.assert_not_called()
        sent_err = ctx_unauthorized.send.call_args[0][0]
        assert "Fejlesztőjének" in sent_err or "Owner" in sent_err

        # 2. Owner attempt -> Allowed
        ctx_owner = MagicMock()
        ctx_owner.author = MagicMock()
        ctx_owner.author.id = 12345
        ctx_owner.send = AsyncMock()
        await invoke_command(cog.clear_commands_prefix, cog, ctx_owner, spec="global")
        bot_mock.tree.clear_commands.assert_called_once_with(guild=None)
        bot_mock.tree.sync.assert_awaited_once_with(guild=None)

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
        interaction.response.send_message = AsyncMock()

        # Step 1: /purge summons confirmation dialog
        await invoke_command(cog.purge, cog, interaction)

        interaction.response.send_message.assert_awaited_once()
        sent_args = interaction.response.send_message.call_args
        view = sent_args[1].get("view")
        assert view is not None
        assert "Biztosan" in sent_args[0][0] or "Are you sure" in sent_args[0][0]

        # Step 2: Confirm button clicked by author
        btn_interaction = MagicMock()
        btn_interaction.user.id = 99999
        btn_interaction.response.defer = AsyncMock()
        btn_interaction.followup.send = AsyncMock()

        await view.confirm_button.callback(btn_interaction)

        interaction.channel.purge.assert_awaited_once()
        btn_interaction.followup.send.assert_awaited_once()
        sent_text = btn_interaction.followup.send.call_args[0][0]
        assert "15" in sent_text

    asyncio.run(run())


def test_e2e_purge_cancel_and_unauthorized_click():
    async def run():
        bot_mock = MagicMock()
        bot_mock.i18n = LocalizationService("hu")
        bot_mock.access_control = {"roles": {"admin": 555}}

        cog = SystemCog(bot_mock)

        interaction = MagicMock()
        interaction.user = MagicMock()
        interaction.user.guild = MagicMock()
        interaction.user.guild.owner_id = 99999
        interaction.user.id = 99999
        interaction.channel = MagicMock()
        interaction.response.send_message = AsyncMock()

        await invoke_command(cog.purge, cog, interaction)
        view = interaction.response.send_message.call_args[1].get("view")

        # 1. Unauthorized user tries to confirm
        intruder_interaction = MagicMock()
        intruder_interaction.user.id = 11111
        intruder_interaction.response.send_message = AsyncMock()
        await view.confirm_button.callback(intruder_interaction)
        intruder_interaction.response.send_message.assert_awaited_once()
        interaction.channel.purge.assert_not_called()

        # 2. Author clicks cancel
        author_interaction = MagicMock()
        author_interaction.user.id = 99999
        author_interaction.response.send_message = AsyncMock()
        await view.cancel_button.callback(author_interaction)
        assert view.confirmed is False
        author_interaction.response.send_message.assert_awaited_once()

    asyncio.run(run())
