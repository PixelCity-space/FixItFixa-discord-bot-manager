from unittest.mock import AsyncMock, MagicMock

from bot.cogs.management_cog import ManagementCog
from bot.cogs.monitoring_cog import MonitoringCog
from bot.cogs.system_cog import SystemCog
from core.config.models import BotConfig


async def test_management_cog_update_command_with_embed(mock_bot, mock_interaction):
    cog = ManagementCog(mock_bot)
    await cog.update.callback(cog, mock_interaction, bot_id="b1")

    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=False)
    mock_bot.update_service.update_bot.assert_awaited_once_with("b1")
    mock_interaction.followup.send.assert_awaited_once()


async def test_management_cog_update_command_without_embed(mock_bot, mock_interaction):
    mock_bot.update_service.update_bot = AsyncMock(return_value=(True, "Raw text update", False, None, []))
    cog = ManagementCog(mock_bot)
    await cog.update.callback(cog, mock_interaction, bot_id="b1")

    mock_interaction.followup.send.assert_awaited_once_with("Raw text update", ephemeral=False)


async def test_management_cog_restart_command(mock_bot, mock_interaction):
    cog = ManagementCog(mock_bot)
    await cog.restart.callback(cog, mock_interaction, bot_id="b1")

    mock_bot.lifecycle_service.restart_bot_cluster.assert_awaited_once_with("b1")
    mock_interaction.followup.send.assert_awaited_once()


async def test_management_cog_stop_command(mock_bot, mock_interaction):
    mock_bot.bots["b1"] = BotConfig(id="b1", name="Bot 1", path="C:\\test", cmd="python b1.py")
    mock_bot.lifecycle_service.stop_bot = AsyncMock(return_value=(True, None))
    cog = ManagementCog(mock_bot)
    await cog.stop.callback(cog, mock_interaction, bot_id="b1")

    mock_bot.lifecycle_service.stop_bot.assert_awaited_once_with("b1")
    mock_interaction.followup.send.assert_awaited_once()
    assert "sikeresen leállítva" in mock_interaction.followup.send.call_args[0][0]


async def test_management_cog_start_command(mock_bot, mock_interaction):
    mock_bot.bots["b1"] = BotConfig(id="b1", name="Bot 1", path="C:\\test", cmd="python b1.py")
    mock_bot.lifecycle_service.start_bot = AsyncMock(return_value=9999)
    mock_bot.notify_admin = AsyncMock()
    cog = ManagementCog(mock_bot)
    await cog.start.callback(cog, mock_interaction, bot_id="b1")

    mock_bot.lifecycle_service.start_bot.assert_awaited_once_with("b1")
    mock_interaction.followup.send.assert_awaited_once()
    assert "9999" in mock_interaction.followup.send.call_args[0][0]


async def test_management_cog_rollback_command(mock_bot, mock_interaction):
    cog = ManagementCog(mock_bot)
    await cog.rollback.callback(cog, mock_interaction, bot_id="b1")

    mock_bot.update_service.rollback_bot.assert_awaited_once_with("b1")
    mock_interaction.followup.send.assert_awaited_once()


async def test_management_cog_logs_command_streams_file(tmp_path, mock_bot, mock_interaction):
    log_file = tmp_path / "b1.log"
    log_file.write_text("Line 1\nLine 2\nLine 3\n", encoding="utf-8")

    mock_bot.bots["b1"] = BotConfig(
        id="b1", name="Bot 1", path=str(tmp_path), cmd="python b1.py", log=str(log_file.name)
    )

    cog = ManagementCog(mock_bot)
    await cog.logs.callback(cog, mock_interaction, bot_id="b1", lines=2)

    mock_interaction.followup.send.assert_awaited_once()
    call_kwargs = mock_interaction.followup.send.call_args[1]
    assert "file" in call_kwargs


async def test_management_cog_logs_command_unknown_bot(mock_bot, mock_interaction):
    cog = ManagementCog(mock_bot)
    await cog.logs.callback(cog, mock_interaction, bot_id="unknown_bot", lines=10)

    mock_interaction.followup.send.assert_awaited_once()
    assert mock_interaction.followup.send.call_args[1]["ephemeral"] is True


async def test_management_cog_manager_logs(tmp_path, mock_bot, mock_interaction):
    mgr_log = tmp_path / "manager.log"
    mgr_log.write_text("Manager line 1\nManager line 2\n", encoding="utf-8")
    mock_bot.app_cfg.bot_settings.manager_log_file = str(mgr_log)

    cog = ManagementCog(mock_bot)
    await cog.manager_logs.callback(cog, mock_interaction, lines=2)

    mock_interaction.followup.send.assert_awaited_once()
    assert "file" in mock_interaction.followup.send.call_args[1]


async def test_management_cog_manager_update(mock_bot, mock_interaction):
    cog = ManagementCog(mock_bot)
    await cog.manager_update.callback(cog, mock_interaction)

    mock_bot.update_service.update_manager.assert_awaited_once()
    mock_bot.update_service.prepare_manager_restart.assert_called_once()
    mock_bot.spawner.execute_manager_restart.assert_called_once()


async def test_system_cog_ping_command(mock_bot):
    mock_bot.latency = 0.042
    cog = SystemCog(mock_bot)
    mock_ctx = MagicMock()
    mock_ctx.send = AsyncMock()

    await cog.ping_prefix.callback(cog, mock_ctx)
    mock_ctx.send.assert_awaited_once()
    msg = mock_ctx.send.call_args[0][0]
    assert "42" in msg


async def test_system_cog_purge_command_success(mock_bot, mock_interaction):
    cog = SystemCog(mock_bot)
    await cog.purge.callback(cog, mock_interaction)

    mock_interaction.response.send_message.assert_awaited_once()
    sent_view = mock_interaction.response.send_message.call_args[1].get("view")
    assert sent_view is not None

    btn_interaction = MagicMock()
    btn_interaction.user.id = mock_interaction.user.id
    btn_interaction.response.defer = AsyncMock()
    btn_interaction.followup.send = AsyncMock()

    await sent_view.confirm_button.callback(btn_interaction)
    mock_interaction.channel.purge.assert_awaited_once()
    btn_interaction.followup.send.assert_awaited_once()


async def test_system_cog_sync_command(mock_bot):
    mock_bot.tree = MagicMock()
    mock_bot.tree.sync = AsyncMock(return_value=[MagicMock(), MagicMock()])
    cog = SystemCog(mock_bot)
    mock_ctx = MagicMock()
    mock_ctx.bot = mock_bot
    mock_ctx.guild = MagicMock()
    mock_ctx.send = AsyncMock()

    # Guild sync
    await cog.sync_prefix.callback(cog, mock_ctx, spec="guild")
    mock_ctx.send.assert_awaited()


async def test_system_cog_clear_commands(mock_bot):
    mock_bot.tree = MagicMock()
    mock_bot.tree.clear_commands = MagicMock()
    mock_bot.tree.sync = AsyncMock(return_value=[])
    cog = SystemCog(mock_bot)
    mock_ctx = MagicMock()
    mock_ctx.bot = mock_bot
    mock_ctx.guild = MagicMock()
    mock_ctx.send = AsyncMock()

    await cog.clear_commands_prefix.callback(cog, mock_ctx)
    mock_bot.tree.clear_commands.assert_called()
    mock_ctx.send.assert_awaited()


async def test_monitoring_cog_data_and_panel_recreate(mock_bot, mock_channel):
    mock_bot.get_channel = MagicMock(return_value=mock_channel)
    new_msg = MagicMock()
    new_msg.id = 999123
    mock_channel.send = AsyncMock(return_value=new_msg)

    cog = MonitoringCog(mock_bot)

    # Verify status data getter
    mgr_stats, bot_stats = cog.get_status_data()
    assert "cpu" in mgr_stats

    # Test panel recreation
    await cog.cleanup_and_recreate_panel()
    mock_bot.state_repo.set.assert_any_call("status_message_id", "999123")
    mock_bot.state_repo.set.assert_any_call("status_channel_id", str(mock_channel.id))
