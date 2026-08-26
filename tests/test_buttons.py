import asyncio
import discord
from unittest.mock import AsyncMock, MagicMock
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
