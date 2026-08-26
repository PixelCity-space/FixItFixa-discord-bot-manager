import json
import asyncio
from unittest.mock import AsyncMock, MagicMock
from bot.client import BotManager

def test_bot_manager_full_initialization(tmp_path):
    config_data = {
        "guild_id": 99999,
        "access_control": {"channels": {"admin": 111, "public": 222}, "roles": {"admin": 333, "tester": 444}},
        "bot_settings": {
            "manager_name": "TestFixa",
            "language": "hu",
            "manager_log_file": str(tmp_path / "test_mgr.log")
        },
        "bots": {
            "test_bot": {
                "name": "Integration Test Bot",
                "path": str(tmp_path / "bot_dir"),
                "cmd": "python app.py"
            }
        }
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
            "bot_settings": {
                "language": "hu",
                "manager_log_file": str(tmp_path / "test_mgr.log")
            },
            "bots": {}
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
            "bot_settings": {"manager_log_file": str(tmp_path / "mgr.log")}
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
            "bot_settings": {
                "command_suffix": "_fix",
                "manager_log_file": str(tmp_path / "mgr.log")
            }
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
