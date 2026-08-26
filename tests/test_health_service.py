import asyncio
from unittest.mock import AsyncMock, MagicMock
from core.config.models import AppConfig, BotConfig
from core.system.process_tracker import ProcessTracker
from core.system.process_spawner import ProcessSpawner
from core.services.health_service import HealthService

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

        service = HealthService(
            config=app_cfg,
            tracker=tracker,
            spawner=spawner,
            alert_callback=alert_callback
        )

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

        service = HealthService(
            config=app_cfg,
            tracker=tracker,
            spawner=spawner,
            alert_callback=alert_callback
        )

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
