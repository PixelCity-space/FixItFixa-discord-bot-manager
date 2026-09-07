import asyncio
from unittest.mock import AsyncMock, MagicMock

from core.config.models import AppConfig, BotConfig
from core.services.health_service import HealthService
from core.system.process_spawner import ProcessSpawner
from core.system.process_tracker import ProcessTracker


def test_health_service_triggers_alert_on_crash():
    async def run():
        bot = BotConfig(id="b1", name="CrashingBot", path="C:\\bots\\crash", cmd="python main.py")
        app_cfg = AppConfig(bots={"b1": bot})

        tracker = ProcessTracker()
        dead_proc = MagicMock()
        dead_proc.is_running.return_value = False
        tracker.managed_processes["b1"] = dead_proc

        spawner = ProcessSpawner()
        alert_callback = AsyncMock()

        service = HealthService(config=app_cfg, tracker=tracker, spawner=spawner, alert_callback=alert_callback)

        stopped = await service.check_health()
        assert len(stopped) == 1
        assert "b1" in service.alerted_bots
        alert_callback.assert_awaited_once_with("b1", bot)

    asyncio.run(run())


def test_health_service_avoids_duplicate_alerts():
    async def run():
        bot = BotConfig(id="b1", name="CrashingBot", path="C:\\bots\\crash", cmd="python main.py")
        app_cfg = AppConfig(bots={"b1": bot})

        tracker = ProcessTracker()
        dead_proc = MagicMock()
        dead_proc.is_running.return_value = False
        tracker.managed_processes["b1"] = dead_proc

        spawner = ProcessSpawner()
        alert_callback = AsyncMock()

        service = HealthService(config=app_cfg, tracker=tracker, spawner=spawner, alert_callback=alert_callback)

        # First check triggers alert
        await service.check_health()
        assert alert_callback.await_count == 1

        # Second check while still dead should NOT re-alert
        await service.check_health()
        assert alert_callback.await_count == 1

    asyncio.run(run())


def test_health_service_clears_alert_when_back_online():
    async def run():
        bot = BotConfig(id="b1", name="CrashingBot", path="C:\\bots\\crash", cmd="python main.py")
        app_cfg = AppConfig(bots={"b1": bot})

        tracker = ProcessTracker()
        spawner = ProcessSpawner()
        service = HealthService(config=app_cfg, tracker=tracker, spawner=spawner)

        # Simulate bot was alerted
        service.alerted_bots.add("b1")

        # Bot comes back online
        live_proc = MagicMock()
        live_proc.is_running.return_value = True
        tracker.managed_processes["b1"] = live_proc

        await service.check_health()
        assert "b1" not in service.alerted_bots

    asyncio.run(run())


def test_health_service_clears_alert_on_manual_stop_and_removal():
    async def run():
        bot = BotConfig(id="b1", name="CrashingBot", path="C:\\bots\\crash", cmd="python main.py")
        app_cfg = AppConfig(bots={"b1": bot})

        tracker = ProcessTracker()
        spawner = ProcessSpawner()
        service = HealthService(config=app_cfg, tracker=tracker, spawner=spawner)

        # Bot crashed and alerted
        service.alerted_bots.add("b1")

        # Admin manually stops the bot
        tracker.mark_manual_stop("b1")
        await service.check_health()
        assert "b1" not in service.alerted_bots

        # Test explicit clear_alert and reset_alerts
        service.alerted_bots.add("b2")
        service.alerted_bots.add("b3")
        service.clear_alert("b2")
        assert "b2" not in service.alerted_bots
        assert "b3" in service.alerted_bots

        service.reset_alerts()
        assert len(service.alerted_bots) == 0

    asyncio.run(run())
