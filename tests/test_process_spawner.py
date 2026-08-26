import asyncio
from unittest.mock import MagicMock, patch
from core.system.process_spawner import ProcessSpawner
from core.config.models import BotConfig

def test_process_spawner_init():
    spawner = ProcessSpawner(stop_timeout=3.0, restart_wait=0.5)
    assert spawner.stop_timeout == 3.0
    assert spawner.restart_wait == 0.5

def test_process_spawner_spawn_success(tmp_path):
    bot_dir = tmp_path / "bot_test"
    bot_dir.mkdir()
    bot = BotConfig(id="b1", name="TestBot", path=str(bot_dir), cmd="python -V", log="bot.log")

    spawner = ProcessSpawner()
    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.pid = 54321
        mock_popen.return_value = mock_proc

        pid = spawner.spawn(bot, env={})
        assert pid == 54321
        mock_popen.assert_called_once()

def test_process_spawner_spawn_failure(tmp_path):
    bot = BotConfig(id="b_fail", name="FailBot", path=str(tmp_path), cmd="invalid_cmd", log="bot.log")
    spawner = ProcessSpawner()
    with patch("subprocess.Popen", side_effect=OSError("Command not found")):
        pid = spawner.spawn(bot, env={})
        assert pid is None

def test_process_spawner_terminate_process_graceful():
    async def run():
        spawner = ProcessSpawner(stop_timeout=1.0)
        mock_psutil_proc = MagicMock()
        mock_psutil_proc.pid = 8888
        mock_psutil_proc.is_running.side_effect = [True, True, False, False]

        success = await spawner.terminate_process(mock_psutil_proc)
        assert success is True
        mock_psutil_proc.terminate.assert_called_once()
        mock_psutil_proc.kill.assert_not_called()

    asyncio.run(run())

def test_process_spawner_terminate_process_escalates_to_kill():
    async def run():
        spawner = ProcessSpawner(stop_timeout=0.2)
        mock_psutil_proc = MagicMock()
        # Process stays running throughout timeout
        mock_psutil_proc.is_running.return_value = True

        success = await spawner.terminate_process(mock_psutil_proc)
        assert success is True
        mock_psutil_proc.terminate.assert_called_once()
        mock_psutil_proc.kill.assert_called_once()

    asyncio.run(run())

def test_process_spawner_terminate_process_access_denied():
    async def run():
        import psutil
        spawner = ProcessSpawner(stop_timeout=0.2)
        mock_psutil_proc = MagicMock()
        mock_psutil_proc.pid = 7777
        mock_psutil_proc.is_running.return_value = True
        mock_psutil_proc.terminate.side_effect = psutil.AccessDenied(pid=7777)

        success = await spawner.terminate_process(mock_psutil_proc)
        assert success is False
        assert spawner.last_error is not None
        assert "Access denied" in spawner.last_error

    asyncio.run(run())

def test_process_spawner_systemd_sudo_privilege_check(monkeypatch):
    import os
    import subprocess
    monkeypatch.setattr(os, "name", "posix")

    # Mock subprocess.run for sudo check returning code 1 (no passwordless sudo)
    mock_res = MagicMock()
    mock_res.returncode = 1
    with patch("subprocess.run", return_value=mock_res):
        has_privs, msg = ProcessSpawner.check_systemd_privileges()
        assert has_privs is False
        assert "Passwordless sudo required" in msg

        spawner = ProcessSpawner()
        stopped = spawner.stop_service("iris")
        assert stopped is False
        assert "Passwordless sudo required" in spawner.last_error

        started = spawner.start_service("iris")
        assert started is False
        assert "Passwordless sudo required" in spawner.last_error
