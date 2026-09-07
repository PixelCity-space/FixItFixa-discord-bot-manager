import asyncio
import threading

import pytest

from bot.cogs.monitoring_cog import MonitoringCog
from core.config.config_repository import ConfigRepository
from core.config.state_repository import StateRepository


def test_state_repository_thread_safety_concurrent_writes(tmp_path):
    state_file = tmp_path / "concurrent_state.json"
    repo = StateRepository(str(state_file))

    def worker(worker_id: int):
        for i in range(20):
            repo.set(f"worker_{worker_id}_key_{i}", f"val_{i}", auto_save=True)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Verify state integrity
    loaded_state = repo.load()
    assert len(loaded_state) == 100
    assert loaded_state["worker_0_key_0"] == "val_0"
    assert loaded_state["worker_4_key_19"] == "val_19"


def test_config_repository_thread_safety_concurrent_saves(tmp_path):
    cfg_file = tmp_path / "concurrent_config.json"
    cfg_file.write_text('{"settings": {}, "bots": {}}', encoding="utf-8")
    repo = ConfigRepository(str(cfg_file))

    def worker(worker_id: int):
        for _i in range(10):
            data = {
                "settings": {"guild_id": f"12345678901234567{worker_id}"},
                "bots": {
                    f"bot_{worker_id}": {"name": f"Bot {worker_id}", "path": str(tmp_path), "cmd": "python app.py"}
                },
            }
            repo.save(data)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Final read must be valid JSON and loaded without corruption
    final_cfg = repo.load()
    assert final_cfg is not None
    assert not (tmp_path / "concurrent_config.json.tmp").exists()


async def test_monitoring_cog_create_tracked_task_execution_and_cleanup(mock_bot):
    cog = MonitoringCog(mock_bot)

    async def sample_coro():
        await asyncio.sleep(0.01)
        return "ok"

    task = cog.create_tracked_task(sample_coro(), name="test_sample_task")
    assert task in cog._background_tasks

    await task
    # Should be removed from background tasks upon completion
    assert task not in cog._background_tasks


async def test_monitoring_cog_create_tracked_task_exception_handling(mock_bot):
    cog = MonitoringCog(mock_bot)

    async def failing_coro():
        await asyncio.sleep(0.01)
        raise ValueError("Simulated background error")

    task = cog.create_tracked_task(failing_coro(), name="failing_task")
    assert task in cog._background_tasks

    # Wait for completion (with exception handled)
    with pytest.raises(ValueError, match="Simulated background error"):
        await task

    # Task is cleanly discarded from tracker
    assert task not in cog._background_tasks
