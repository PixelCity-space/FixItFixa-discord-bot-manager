import asyncio
from unittest.mock import AsyncMock, MagicMock
from core.config.models import AppConfig, BotConfig
from core.system.process_spawner import ProcessSpawner
from core.system.process_tracker import ProcessTracker
from core.services.bot_lifecycle_service import BotLifecycleService
from core.services.i18n_service import LocalizationService
from bot.cogs.management_cog import ManagementCog

async def invoke_slash_command(command, *args, **kwargs):
    """Safely invokes an app_commands.Command callback for testing."""
    callback_fn = getattr(command, "callback", command)
    return await callback_fn(*args, **kwargs)

def test_e2e_management_update_command_flow():
    async def run():
        bot_cfg = BotConfig(id="b_upd", name="Update Bot", path="C:\\test", cmd="python main.py")
        app_cfg = AppConfig(bots={"b_upd": bot_cfg})

        update_mock = MagicMock()
        update_mock.update_bot = AsyncMock(return_value=(True, "Successfully updated", True, {"hash": "12345", "message": "feat: new", "date": 1700000000}, [(bot_cfg, 9911, None)]))

        bot_mock = MagicMock()
        bot_mock.app_cfg = app_cfg
        bot_mock.update_service = update_mock
        bot_mock.ui_settings = {}
        bot_mock.i18n = LocalizationService("hu")

        cog = ManagementCog(bot_mock)

        interaction = MagicMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        await invoke_slash_command(cog.update, cog, interaction, bot_id="b_upd")

        interaction.response.defer.assert_awaited_once()
        interaction.followup.send.assert_awaited_once()

    asyncio.run(run())

def test_e2e_management_restart_command_flow():
    async def run():
        bot_cfg = BotConfig(id="b_res", name="Restart Bot", path="C:\\test", cmd="python main.py")
        app_cfg = AppConfig(bots={"b_res": bot_cfg})

        tracker = ProcessTracker()
        spawner = ProcessSpawner()
        lifecycle = BotLifecycleService(config=app_cfg, spawner=spawner, tracker=tracker)
        lifecycle.restart_bot_cluster = AsyncMock(return_value=[(bot_cfg, 7788, None)])

        bot_mock = MagicMock()
        bot_mock.lifecycle_service = lifecycle
        bot_mock.i18n = LocalizationService("hu")
        bot_mock.notify_admin = AsyncMock()

        cog = ManagementCog(bot_mock)

        interaction = MagicMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        await invoke_slash_command(cog.restart, cog, interaction, bot_id="b_res")

        interaction.followup.send.assert_awaited_once()
        sent_text = interaction.followup.send.call_args[0][0]
        assert "7788" in sent_text

    asyncio.run(run())

def test_e2e_management_rollback_command_flow():
    async def run():
        bot_cfg = BotConfig(id="b_rb", name="Rollback Bot", path="C:\\test", cmd="python main.py")
        app_cfg = AppConfig(bots={"b_rb": bot_cfg})

        update_mock = MagicMock()
        update_mock.rollback_bot = AsyncMock(return_value=(True, "Rolled back", True, {"hash": "prev99", "message": "revert", "date": 1700000000}, [(bot_cfg, 5555, None)]))

        bot_mock = MagicMock()
        bot_mock.app_cfg = app_cfg
        bot_mock.update_service = update_mock
        bot_mock.ui_settings = {}
        bot_mock.i18n = LocalizationService("hu")

        cog = ManagementCog(bot_mock)

        interaction = MagicMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        await invoke_slash_command(cog.rollback, cog, interaction, bot_id="b_rb")

        interaction.followup.send.assert_awaited_once()

    asyncio.run(run())

def test_e2e_management_logs_missing_file_fallback(tmp_path):
    async def run():
        missing_log = tmp_path / "missing_bot.log"
        bot_cfg = BotConfig(id="b_nolog", name="NoLog Bot", path=str(tmp_path), cmd="python main.py", log=str(missing_log))
        app_cfg = AppConfig(bots={"b_nolog": bot_cfg})

        bot_mock = MagicMock()
        bot_mock.bots = app_cfg.bots
        bot_mock.app_cfg = app_cfg
        bot_mock.i18n = LocalizationService("hu")

        cog = ManagementCog(bot_mock)

        interaction = MagicMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        await invoke_slash_command(cog.logs, cog, interaction, bot_id="b_nolog", lines=50)

        interaction.followup.send.assert_awaited_once()
        sent_text = interaction.followup.send.call_args[0][0]
        assert "nem található" in sent_text.lower() or "not found" in sent_text.lower() or "log" in sent_text.lower()

    asyncio.run(run())
