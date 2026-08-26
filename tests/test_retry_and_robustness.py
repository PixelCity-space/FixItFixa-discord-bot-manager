import pytest
import asyncio
import psutil
from unittest.mock import MagicMock
from core.common.retry import retry_sync, retry_async
from core.system.process_tracker import ProcessTracker
from core.config.config_repository import ConfigRepository
from core.config.state_repository import StateRepository
from core.config.models import BotConfig

def test_retry_sync_succeeds_on_transient_failure():
    attempts = 0
    def flaky_func():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise OSError("Transient disk error")
        return "success"

    res = retry_sync(flaky_func, max_retries=3, initial_delay=0.01, backoff_factor=1.0, jitter=False, exceptions=(OSError,))
    assert res == "success"
    assert attempts == 3

def test_retry_sync_exhausts_and_raises():
    attempts = 0
    def always_fails():
        nonlocal attempts
        attempts += 1
        raise ValueError("Permanent error")

    with pytest.raises(ValueError, match="Permanent error"):
        retry_sync(always_fails, max_retries=3, initial_delay=0.01, backoff_factor=1.0, jitter=False, exceptions=(ValueError,))
    assert attempts == 3

async def test_retry_async_succeeds_on_transient_failure():
    attempts = 0
    async def flaky_coro():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionResetError("Connection dropped")
        return "async_success"

    res = await retry_async(flaky_coro, max_retries=3, initial_delay=0.01, backoff_factor=1.0, jitter=False, exceptions=(ConnectionResetError,))
    assert res == "async_success"
    assert attempts == 3

async def test_retry_async_exhausts_and_raises():
    attempts = 0
    async def always_fails():
        nonlocal attempts
        attempts += 1
        raise TimeoutError("Timed out")

    with pytest.raises(TimeoutError, match="Timed out"):
        await retry_async(always_fails, max_retries=2, initial_delay=0.01, backoff_factor=1.0, jitter=False, exceptions=(TimeoutError,))
    assert attempts == 2

def test_process_tracker_toctou_zombie_handling():
    tracker = ProcessTracker()
    mock_proc = MagicMock()
    mock_proc.is_running.return_value = True
    mock_proc.status.return_value = psutil.STATUS_ZOMBIE
    tracker.managed_processes["bot_zombie"] = mock_proc

    # Zombie process should be considered NOT running and unregistered
    assert tracker.is_running("bot_zombie") is False
    assert "bot_zombie" not in tracker.managed_processes

def test_process_tracker_toctou_no_such_process_handling():
    tracker = ProcessTracker()
    mock_proc = MagicMock()
    mock_proc.is_running.side_effect = psutil.NoSuchProcess(pid=12345)
    tracker.managed_processes["bot_dead"] = mock_proc

    assert tracker.is_running("bot_dead") is False
    assert "bot_dead" not in tracker.managed_processes

def test_process_tracker_get_stats_handles_sudden_process_death():
    tracker = ProcessTracker()
    mock_proc = MagicMock()
    mock_proc.is_running.return_value = True
    mock_proc.status.return_value = psutil.STATUS_RUNNING
    mock_proc.oneshot.side_effect = psutil.NoSuchProcess(pid=99999)
    tracker.managed_processes["bot_died_during_stats"] = mock_proc

    stats = tracker.get_stats("bot_died_during_stats")
    assert stats is None
    assert "bot_died_during_stats" not in tracker.managed_processes

def test_config_repository_specific_json_error_handling(tmp_path):
    bad_config = tmp_path / "broken_config.json"
    bad_config.write_text("{ unclosed json", encoding="utf-8")

    repo = ConfigRepository(str(bad_config))
    assert repo.app_config is not None
    assert repo.app_config.bots == {}

def test_state_repository_specific_json_error_handling(tmp_path):
    bad_state = tmp_path / "broken_state.json"
    bad_state.write_text("invalid json...", encoding="utf-8")

    repo = StateRepository(str(bad_state))
    assert repo.raw == {}
    assert repo.get("key") is None
