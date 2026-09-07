import os
from unittest.mock import AsyncMock, MagicMock

from core.services.bot_lifecycle_service import BotLifecycleService
from core.system.process_spawner import ProcessSpawner
from core.system.process_tracker import ProcessTracker


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


async def test_lifecycle_start_bot_spawn(sample_config):
    tracker = ProcessTracker()
    spawner = ProcessSpawner()
    current_pid = os.getpid()
    spawner.spawn = MagicMock(return_value=current_pid)

    service = BotLifecycleService(config=sample_config, spawner=spawner, tracker=tracker)
    pid = await service.start_bot("b3")

    assert pid == current_pid
    assert tracker.is_running("b3") is True


async def test_lifecycle_stop_bot(sample_config):
    tracker = ProcessTracker()
    mock_proc = MagicMock()
    mock_proc.pid = 9999
    tracker.managed_processes["b3"] = mock_proc

    spawner = ProcessSpawner()
    spawner.terminate_process = AsyncMock(return_value=True)
    spawner.kill_rogue_processes = AsyncMock(return_value=None)

    service = BotLifecycleService(config=sample_config, spawner=spawner, tracker=tracker)
    stopped, err = await service.stop_bot("b3")

    assert stopped is True
    assert err is None
    assert "b3" not in tracker.managed_processes
    spawner.terminate_process.assert_awaited_once_with(mock_proc)


async def test_lifecycle_stop_bot_systemd_sudo_failure(sample_config, monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    tracker = ProcessTracker()
    spawner = ProcessSpawner()
    spawner.stop_service = MagicMock(return_value=False)
    spawner.last_error = (
        "Passwordless sudo required. Please configure sudoers: 'username ALL=(ALL) NOPASSWD: /bin/systemctl'"
    )

    # Configure b3 to use systemd_service
    sample_config.bots["b3"].systemd_service = "b3-service"

    service = BotLifecycleService(config=sample_config, spawner=spawner, tracker=tracker)
    stopped, err = await service.stop_bot("b3")

    assert stopped is False
    assert "Passwordless sudo required" in err


async def test_lifecycle_stop_bot_access_denied(sample_config):
    tracker = ProcessTracker()
    mock_proc = MagicMock()
    mock_proc.pid = 9999
    tracker.managed_processes["b3"] = mock_proc

    spawner = ProcessSpawner()
    spawner.terminate_process = AsyncMock(return_value=False)
    spawner.last_error = "Access denied terminating PID 9999 (insufficient permissions)"

    service = BotLifecycleService(config=sample_config, spawner=spawner, tracker=tracker)
    stopped, err = await service.stop_bot("b3")

    assert stopped is False
    assert "Access denied" in err
    assert "b3" in tracker.managed_processes  # Should NOT unregister when stop failed


async def test_lifecycle_restart_cluster_sequence(sample_config):
    tracker = ProcessTracker()
    spawner = ProcessSpawner()
    spawner.terminate_process = AsyncMock(return_value=True)
    spawner.kill_rogue_processes = AsyncMock(return_value=None)
    spawner.spawn = MagicMock(side_effect=[1001, 1002])

    service = BotLifecycleService(config=sample_config, spawner=spawner, tracker=tracker)
    results = await service.restart_bot_cluster("b1")

    assert len(results) == 2
    assert results[0][0].id == "b1" and results[0][1] == 1001
    assert results[1][0].id == "b2" and results[1][1] == 1002
    spawner.kill_rogue_processes.assert_awaited()


async def test_lifecycle_restart_cluster_with_sudo_start_failure(sample_config, monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    tracker = ProcessTracker()
    spawner = ProcessSpawner()
    spawner.terminate_process = AsyncMock(return_value=True)
    spawner.kill_rogue_processes = AsyncMock(return_value=None)
    spawner.stop_service = MagicMock(return_value=True)
    spawner.start_service = MagicMock(return_value=False)
    spawner.last_error = "Cannot start systemd service 'b1': Passwordless sudo required"
    sample_config.bots["b1"].systemd_service = "b1"

    service = BotLifecycleService(config=sample_config, spawner=spawner, tracker=tracker)
    results = await service.restart_bot_cluster("b1")

    assert len(results) >= 1
    assert results[0][1] is None  # PID is None
    assert "Passwordless sudo required" in str(results[0][2])  # Error is populated!


def test_lifecycle_build_bot_env_local_dotenv(sample_config, tmp_path):
    tracker = ProcessTracker()
    spawner = ProcessSpawner()
    service = BotLifecycleService(config=sample_config, spawner=spawner, tracker=tracker)

    bot_dir = tmp_path / "custom_bot"
    bot_dir.mkdir()
    env_file = bot_dir / ".env"
    env_file.write_text("CUSTOM_BOT_TOKEN=secret123\nBOT_PREFIX=!\nDISCORD_TOKEN=attempt_override", encoding="utf-8")

    from core.config.models import BotConfig

    bot_cfg = BotConfig(id="custom", name="CustomBot", path=str(bot_dir), cmd="python main.py")

    built_env = service._build_bot_env(bot_cfg)

    assert built_env.get("CUSTOM_BOT_TOKEN") == "secret123"
    assert built_env.get("BOT_PREFIX") == "!"
    assert built_env.get("MANAGED_LOGGING") == "1"
    # Protected variables (like DISCORD_TOKEN) must not be exposed/overridden
    assert "DISCORD_TOKEN" not in built_env
