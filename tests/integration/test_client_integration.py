import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from bot.client import BotManager


def test_bot_manager_full_initialization(tmp_path):
    config_data = {
        "guild_id": 99999,
        "access_control": {"channels": {"admin": 111, "public": 222}, "roles": {"admin": 333, "tester": 444}},
        "bot_settings": {
            "manager_name": "TestFixa",
            "language": "hu",
            "manager_log_file": str(tmp_path / "test_mgr.log"),
        },
        "bots": {
            "test_bot": {"name": "Integration Test Bot", "path": str(tmp_path / "bot_dir"), "cmd": "python app.py"}
        },
    }
    (tmp_path / "config.json").write_text(json.dumps(config_data), encoding="utf-8")
    (tmp_path / "state.json").write_text(json.dumps({}), encoding="utf-8")

    bot = BotManager(base_dir=str(tmp_path))

    assert bot.app_cfg.bot_settings.language == "hu"
    assert bot.guild_id == "99999"
    assert bot.lifecycle_service is not None
    assert bot.update_service is not None
    assert bot.health_service is not None
    assert bot.telemetry_service is not None
    assert bot.spawner is not None
    assert bot.tracker is not None
    assert len(bot.bots) == 1
    assert bot.bots["test_bot"].name == "Integration Test Bot"


def test_bot_manager_setup_hook_loads_all_cogs(tmp_path):
    async def run():
        config_data = {
            "guild_id": 12345,
            "bot_settings": {"language": "hu", "manager_log_file": str(tmp_path / "test_mgr.log")},
            "bots": {},
        }
        (tmp_path / "config.json").write_text(json.dumps(config_data), encoding="utf-8")
        (tmp_path / "state.json").write_text(json.dumps({}), encoding="utf-8")

        bot = BotManager(base_dir=str(tmp_path))
        bot.fetch_application_emojis = AsyncMock(return_value=[])
        await bot.setup_hook()
        bot.check_processes.cancel()

        # All 3 modular cogs are loaded
        assert "ManagementCog" in bot.cogs
        assert "MonitoringCog" in bot.cogs
        assert "SystemCog" in bot.cogs

        assert bot.get_cog("ManagementCog").__class__.__name__ == "ManagementCog"
        assert bot.get_cog("MonitoringCog").__class__.__name__ == "MonitoringCog"
        assert bot.get_cog("SystemCog").__class__.__name__ == "SystemCog"

        # 14 slash commands registered (including /stop and /start)
        assert len(bot.tree.get_commands()) == 14

    asyncio.run(run())


def test_bot_manager_notify_admin_integration(tmp_path):
    async def run():
        config_data = {
            "guild_id": 12345,
            "access_control": {"channels": {"admin": 999111}},
            "bot_settings": {"manager_log_file": str(tmp_path / "mgr.log")},
        }
        (tmp_path / "config.json").write_text(json.dumps(config_data), encoding="utf-8")
        (tmp_path / "state.json").write_text(json.dumps({}), encoding="utf-8")

        bot = BotManager(base_dir=str(tmp_path))

        mock_channel = MagicMock()
        mock_channel.send = AsyncMock()
        bot.get_channel = MagicMock(return_value=mock_channel)

        await bot.notify_admin("Alert: Bot 1 is online!")
        mock_channel.send.assert_awaited_once_with("Alert: Bot 1 is online!")

    asyncio.run(run())


def test_bot_manager_system_cog_aliases_generation(tmp_path):
    async def run():
        config_data = {
            "guild_id": 12345,
            "bot_settings": {"command_suffix": "_fix", "manager_log_file": str(tmp_path / "mgr.log")},
        }
        (tmp_path / "config.json").write_text(json.dumps(config_data), encoding="utf-8")
        (tmp_path / "state.json").write_text(json.dumps({}), encoding="utf-8")

        bot = BotManager(base_dir=str(tmp_path))
        await bot.setup_hook()

        system_cog = bot.get_cog("SystemCog")
        assert system_cog is not None

        # Verify prefix command names include suffix aliases
        prefix_cmds = [cmd.name for cmd in system_cog.get_commands()]
        assert "ping" in prefix_cmds
        assert "sync" in prefix_cmds

    asyncio.run(run())


async def test_bot_manager_lifecycle_and_events(tmp_path):
    import discord
    from discord.ext import commands

    from core.config.models import BotConfig

    config_data = {
        "guild_id": 12345,
        "access_control": {"channels": {"admin": 999111}},
        "bot_settings": {"manager_log_file": str(tmp_path / "mgr.log")},
        "bots": {"b1": {"name": "Bot 1", "path": str(tmp_path), "cmd": "python app.py"}},
    }
    (tmp_path / "config.json").write_text(json.dumps(config_data), encoding="utf-8")
    (tmp_path / "state.json").write_text(json.dumps({}), encoding="utf-8")

    bot = BotManager(base_dir=str(tmp_path))

    # 1. Crash handler
    with patch.object(bot, "notify_admin", new_callable=AsyncMock) as mock_notify:
        await bot._handle_bot_crash("b1", BotConfig(id="b1", name="Bot 1", path="", cmd=""))
        mock_notify.assert_awaited_once()

    # 2. notify_admin fallback with fetch_channel
    bot.get_channel = MagicMock(return_value=None)
    mock_chan = MagicMock()
    mock_chan.send = AsyncMock()
    bot.fetch_channel = AsyncMock(return_value=mock_chan)
    await bot.notify_admin("Testing fetch_channel")
    bot.fetch_channel.assert_awaited_once_with(999111)
    mock_chan.send.assert_awaited_once_with("Testing fetch_channel")

    # 3. cleanup_status_panel
    mock_monitor = MagicMock()
    mock_monitor.status_message_id = "555"
    mock_monitor.status_channel_id = "666"
    bot.get_cog = MagicMock(return_value=mock_monitor)
    mock_panel_chan = MagicMock()
    mock_old_msg = MagicMock()
    mock_old_msg.delete = AsyncMock()
    mock_panel_chan.fetch_message = AsyncMock(return_value=mock_old_msg)
    bot.get_channel = MagicMock(return_value=mock_panel_chan)
    await bot.cleanup_status_panel()
    mock_old_msg.delete.assert_awaited_once()

    # 4. on_message ignores bot messages, processes user messages
    bot_msg = MagicMock()
    bot_msg.author.bot = True
    bot.process_commands = AsyncMock()
    await bot.on_message(bot_msg)
    bot.process_commands.assert_not_called()

    user_msg = MagicMock()
    user_msg.author.bot = False
    user_msg.channel = "admin-chan"
    user_msg.content = "!help"
    await bot.on_message(user_msg)
    bot.process_commands.assert_awaited_once_with(user_msg)

    # 5. on_command_error handling
    ctx = MagicMock()
    ctx.send = AsyncMock()
    await bot.on_command_error(ctx, commands.CommandNotFound())
    ctx.send.assert_not_called()

    await bot.on_command_error(ctx, commands.CheckFailure("No access"))
    ctx.send.assert_awaited_once()

    ctx.send.reset_mock()
    await bot.on_command_error(ctx, RuntimeError("Something broke"))
    ctx.send.assert_awaited_once()

    # 6. on_interaction for status buttons
    mock_interaction = MagicMock()
    mock_interaction.client = bot
    mock_interaction.type = discord.InteractionType.component
    mock_interaction.data = {"custom_id": "status:b1:restart"}
    mock_interaction.user = MagicMock()
    mock_interaction.user.guild_permissions = MagicMock()
    mock_interaction.user.guild_permissions.administrator = True
    mock_interaction.user.roles = []
    mock_interaction.channel_id = 999111
    mock_interaction.response.defer = AsyncMock()
    mock_interaction.followup.send = AsyncMock()
    with patch.object(bot.lifecycle_service, "restart_bot_cluster", new_callable=AsyncMock, return_value=[]):
        await bot.on_interaction(mock_interaction)
    mock_interaction.response.defer.assert_awaited_once()

    # 7. close stops metrics server
    bot.container.metrics_server.stop = AsyncMock()
    await bot.close()
    bot.container.metrics_server.stop.assert_awaited_once()
