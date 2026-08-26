import os
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from core.config.models import AppConfig, BotConfig
from core.system.process_tracker import ProcessTracker
from core.system.process_spawner import ProcessSpawner
from core.services.bot_lifecycle_service import BotLifecycleService

@pytest.fixture
def sample_config():
    bot1 = BotConfig(id="b1", name="Bot 1", path="C:\\shared_path", cmd="python b1.py")
    bot2 = BotConfig(id="b2", name="Bot 2", path="C:\\shared_path", cmd="python b2.py")
    bot3 = BotConfig(id="b3", name="Solo Bot", path="C:\\solo_path", cmd="python solo.py")
    return AppConfig(bots={"b1": bot1, "b2": bot2, "b3": bot3})

def test_lifecycle_get_related_bots(sample_config):
    tracker = ProcessTracker()
    spawner = ProcessSpawner()
    service = BotLifecycleService(config=sample_config, spawner=spawner, tracker=tracker)

    related_to_b1 = service.get_related_bots("b1")
    assert len(related_to_b1) == 2
    related_ids = [b.id for b in related_to_b1]
    assert "b1" in related_ids
    assert "b2" in related_ids

    related_to_b3 = service.get_related_bots("b3")
    assert len(related_to_b3) == 1
    assert related_to_b3[0].id == "b3"

def test_lifecycle_start_bot_spawn(sample_config):
    async def run():
        tracker = ProcessTracker()
        spawner = ProcessSpawner()
        current_pid = os.getpid()
        spawner.spawn = MagicMock(return_value=current_pid)

        service = BotLifecycleService(config=sample_config, spawner=spawner, tracker=tracker)
        pid = await service.start_bot("b3")

        assert pid == current_pid
        assert tracker.is_running("b3") is True

    asyncio.run(run())

def test_lifecycle_stop_bot(sample_config):
    async def run():
        tracker = ProcessTracker()
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        tracker.managed_processes["b3"] = mock_proc

        spawner = ProcessSpawner()
        spawner.terminate_process = AsyncMock()
        spawner.kill_rogue_processes = AsyncMock()

        service = BotLifecycleService(config=sample_config, spawner=spawner, tracker=tracker)
        stopped = await service.stop_bot("b3")

        assert stopped is True
        assert "b3" not in tracker.managed_processes
        spawner.terminate_process.assert_awaited_once_with(mock_proc)

    asyncio.run(run())

def test_lifecycle_restart_cluster_sequence(sample_config):
    async def run():
        tracker = ProcessTracker()
        spawner = ProcessSpawner()
        spawner.terminate_process = AsyncMock()
        spawner.kill_rogue_processes = AsyncMock()
        spawner.spawn = MagicMock(side_effect=[1001, 1002])

        service = BotLifecycleService(config=sample_config, spawner=spawner, tracker=tracker)
        results = await service.restart_bot_cluster("b1")

        assert len(results) == 2
        assert results[0][0].id == "b1" and results[0][1] == 1001
        assert results[1][0].id == "b2" and results[1][1] == 1002
        spawner.kill_rogue_processes.assert_awaited()

    asyncio.run(run())
