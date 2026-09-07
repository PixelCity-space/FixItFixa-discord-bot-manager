import asyncio
from unittest.mock import MagicMock, patch

from core.config.models import BotConfig
from core.system.process_spawner import ProcessSpawner


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


def test_process_spawner_excludes_manager_pid_and_root(tmp_path):
    async def run():
        import os

        spawner = ProcessSpawner()
        current_pid = os.getpid()

        # Mock psutil.process_iter to return current process and a child process
        mock_curr_proc = MagicMock()
        mock_curr_proc.pid = current_pid
        mock_curr_proc.info = {"name": "python.exe"}
        mock_curr_proc.cwd.return_value = str(tmp_path)

        mock_rogue_proc = MagicMock()
        mock_rogue_proc.pid = 999999
        mock_rogue_proc.info = {"name": "python.exe"}
        mock_rogue_proc.cwd.return_value = str(tmp_path)
        mock_rogue_proc.is_running.return_value = True

        with patch("psutil.process_iter", return_value=[mock_curr_proc, mock_rogue_proc]):
            pids = spawner.find_all_processes_in_path(str(tmp_path))
            # Current process must NOT be included in rogue pids
            assert current_pid not in pids
            assert 999999 in pids

        # Test kill_rogue_processes on "." skips safely
        with patch("psutil.process_iter") as mock_iter:
            await spawner.kill_rogue_processes(".")
            await spawner.kill_rogue_processes("")
            mock_iter.assert_not_called()

        # Test kill_rogue_processes never kills current PID
        mock_p = MagicMock()
        mock_p.is_running.return_value = True
        with (
            patch.object(spawner, "find_all_processes_in_path", return_value=[current_pid, 999999]),
            patch("psutil.Process", return_value=mock_p) as mock_proc_cls,
        ):
            await spawner.kill_rogue_processes(str(tmp_path))
            # Only 999999 should be killed, never current_pid
            mock_proc_cls.assert_called_once_with(999999)
            mock_p.kill.assert_called_once()

    asyncio.run(run())


def test_process_spawner_systemd_with_privileges(monkeypatch):
    import os
    import subprocess

    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(ProcessSpawner, "check_systemd_privileges", staticmethod(lambda: (True, None)))

    mock_res = MagicMock()
    mock_res.returncode = 0
    with patch("subprocess.run", return_value=mock_res):
        spawner = ProcessSpawner()
        assert spawner.start_service("bot.service") is True
        assert spawner.stop_service("bot.service") is True
        assert spawner.restart_service("bot.service") is True

    # Subprocess failure handling
    fail_exc = subprocess.CalledProcessError(1, ["sudo", "systemctl", "start", "bot.service"])
    with patch("subprocess.run", side_effect=fail_exc):
        spawner = ProcessSpawner()
        assert spawner.start_service("bot.service") is False
        assert "exit code 1" in spawner.last_error

    # TimeoutExpired handling
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("systemctl", 10)):
        spawner = ProcessSpawner()
        assert spawner.start_service("bot.service") is False
        assert "timed out" in spawner.last_error or "systemctl" in spawner.last_error


async def test_process_spawner_systemd_queries(monkeypatch):
    import os

    monkeypatch.setattr(os, "name", "posix")
    spawner = ProcessSpawner()

    # get_systemd_state
    mock_res = MagicMock()
    mock_res.stdout = "active\n"
    with patch("subprocess.run", return_value=mock_res):
        assert spawner.get_systemd_state("bot.service") == "active"

    # get_systemd_pid
    mock_pid_res = MagicMock()
    mock_pid_res.stdout = "4321\n"
    with patch("subprocess.run", return_value=mock_pid_res):
        assert spawner.get_systemd_pid("bot.service") == 4321

    # get_systemd_pid_async
    with patch.object(spawner, "get_systemd_pid", return_value=4321):
        pid = await spawner.get_systemd_pid_async("bot.service", retries=1)
        assert pid == 4321


def test_process_spawner_execute_manager_restart():
    spawner = ProcessSpawner()
    with patch("os.execv") as mock_execv:
        spawner.execute_manager_restart()
        mock_execv.assert_called_once()

    with (
        patch("os.execv", side_effect=OSError("Exec failed")),
        patch("subprocess.Popen") as mock_popen,
        patch("sys.exit") as mock_exit,
    ):
        spawner.execute_manager_restart()
        mock_popen.assert_called_once()
        mock_exit.assert_called_once_with(0)


def test_process_spawner_execute_manager_shutdown():
    spawner = ProcessSpawner()
    with patch("sys.exit") as mock_exit:
        spawner.execute_manager_shutdown()
        mock_exit.assert_called_once_with(0)


def test_process_spawner_non_posix_systemd_guards(monkeypatch):
    import os

    monkeypatch.setattr(os, "name", "nt")
    spawner = ProcessSpawner()
    assert spawner.start_service("bot.service") is False
    assert spawner.stop_service("bot.service") is False
    assert spawner.restart_service("bot.service") is False
    assert spawner.get_systemd_state("bot.service") == "unknown"
    assert spawner.get_systemd_pid("bot.service") is None


def test_process_spawner_systemd_filenotfound(monkeypatch):
    import os
    from unittest.mock import patch

    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(ProcessSpawner, "check_systemd_privileges", staticmethod(lambda: (True, None)))
    spawner = ProcessSpawner()
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        assert spawner.start_service("bot.service") is False
        assert "not found" in spawner.last_error
        assert spawner.stop_service("bot.service") is False
        assert "not found" in spawner.last_error
        assert spawner.restart_service("bot.service") is False
        assert "not found" in spawner.last_error
