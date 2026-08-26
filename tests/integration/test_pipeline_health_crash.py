import asyncio
from unittest.mock import AsyncMock, MagicMock
from core.config.models import AppConfig, BotConfig
from core.system.process_spawner import ProcessSpawner
from core.system.process_tracker import ProcessTracker
from core.services.bot_lifecycle_service import BotLifecycleService
from core.services.health_service import HealthService

def test_e2e_health_check_crash_and_alert_pipeline():
    async def run():
        bot = BotConfig(id="b_crash", name="Crash Bot", path="C:\\bots\\b_crash", cmd="python app.py")
        app_cfg = AppConfig(bots={"b_crash": bot})

        tracker = ProcessTracker()
        spawner = ProcessSpawner()
        alert_cb = AsyncMock()

        health_service = HealthService(config=app_cfg, tracker=tracker, spawner=spawner, alert_callback=alert_cb)

        # Bot is running
        mock_proc = MagicMock()
        mock_proc.is_running.return_value = True
        tracker.managed_processes["b_crash"] = mock_proc

        # First health check (all healthy)
        stopped = await health_service.check_health()
        assert len(stopped) == 0
        alert_cb.assert_not_called()

        # Bot process dies
        mock_proc.is_running.return_value = False

        # Next health check detects death and triggers alert
        stopped = await health_service.check_health()
        assert len(stopped) == 1
        assert stopped[0][0] == "b_crash"
        alert_cb.assert_awaited_once_with("b_crash", bot)

    asyncio.run(run())

def test_e2e_health_check_manual_stop_suppresses_alert():
    async def run():
        bot = BotConfig(id="b_manual", name="Manual Bot", path="C:\\bots\\b_manual", cmd="python app.py")
        app_cfg = AppConfig(bots={"b_manual": bot})

        tracker = ProcessTracker()
        spawner = ProcessSpawner()
        spawner.terminate_process = AsyncMock()
        spawner.kill_rogue_processes = AsyncMock()

        alert_cb = AsyncMock()
        health_service = HealthService(config=app_cfg, tracker=tracker, spawner=spawner, alert_callback=alert_cb)
        lifecycle_service = BotLifecycleService(config=app_cfg, spawner=spawner, tracker=tracker)

        mock_proc = MagicMock()
        mock_proc.is_running.return_value = True
        tracker.managed_processes["b_manual"] = mock_proc

        # Intentionally stop via lifecycle service
        await lifecycle_service.stop_bot("b_manual")

        # Health check must NOT alert for manual stops
        stopped = await health_service.check_health()
        assert len(stopped) == 0
        alert_cb.assert_not_called()

    asyncio.run(run())

def test_e2e_health_check_auto_recovery_clears_alert():
    async def run():
        bot = BotConfig(id="b_recover", name="Recover Bot", path="C:\\bots\\b_recover", cmd="python app.py")
        app_cfg = AppConfig(bots={"b_recover": bot})

        tracker = ProcessTracker()
        spawner = ProcessSpawner()
        alert_cb = AsyncMock()
        health_service = HealthService(config=app_cfg, tracker=tracker, spawner=spawner, alert_callback=alert_cb)

        # Bot crashed initially
        dead_proc = MagicMock()
        dead_proc.is_running.return_value = False
        tracker.managed_processes["b_recover"] = dead_proc

        await health_service.check_health()
        assert "b_recover" in health_service.alerted_bots

        # Bot restarts and comes back online
        live_proc = MagicMock()
        live_proc.is_running.return_value = True
        tracker.managed_processes["b_recover"] = live_proc

        await health_service.check_health()
        assert "b_recover" not in health_service.alerted_bots

    asyncio.run(run())

def test_e2e_health_check_multi_bot_cluster_isolation():
    async def run():
        b1 = BotConfig(id="worker_1", name="Worker 1", path="C:\\cluster", cmd="python w1.py")
        b2 = BotConfig(id="worker_2", name="Worker 2", path="C:\\cluster", cmd="python w2.py")
        app_cfg = AppConfig(bots={"worker_1": b1, "worker_2": b2})

        tracker = ProcessTracker()
        spawner = ProcessSpawner()
        alert_cb = AsyncMock()
        health_service = HealthService(config=app_cfg, tracker=tracker, spawner=spawner, alert_callback=alert_cb)

        # worker_1 is alive, worker_2 has died
        proc_live = MagicMock()
        proc_live.is_running.return_value = True
        proc_dead = MagicMock()
        proc_dead.is_running.return_value = False

        tracker.managed_processes["worker_1"] = proc_live
        tracker.managed_processes["worker_2"] = proc_dead

        stopped = await health_service.check_health()
        assert len(stopped) == 1
        assert stopped[0][0] == "worker_2"
        alert_cb.assert_awaited_once_with("worker_2", b2)

    asyncio.run(run())
