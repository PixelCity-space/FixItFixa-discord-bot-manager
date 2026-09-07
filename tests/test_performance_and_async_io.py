from unittest.mock import MagicMock, patch

from core.config.config_repository import ConfigRepository
from core.config.models import BotConfig
from core.config.state_repository import StateRepository
from core.icons import Icons
from core.system.git_client import GitClient
from core.system.log_rotator import LogRotator
from core.system.process_spawner import ProcessSpawner
from core.system.process_tracker import ProcessTracker
from core.utils import _CACHED_ICON_MAP, get_feedback, rebuild_icon_cache


def test_icon_cache_speed_and_rebuild():
    assert len(_CACHED_ICON_MAP) > 0
    assert "SUCCESS" in _CACHED_ICON_MAP
    assert "ERROR" in _CACHED_ICON_MAP

    # Test cache rebuild
    rebuild_icon_cache()
    assert len(_CACHED_ICON_MAP) > 0

    # Fast feedback resolution
    dummy_i18n = MagicMock()
    dummy_i18n.get.side_effect = lambda key, **kw: f"Formatted {kw.get('SUCCESS')}"
    msg = get_feedback(dummy_i18n, "test_key")
    assert str(Icons.SUCCESS) in msg


def test_process_discovery_fast_filter():
    tracker = ProcessTracker()

    # Simulate process list with 1 OS process (explorer.exe) and 1 Python bot
    mock_os_proc = MagicMock()
    mock_os_proc.info = {"pid": 100, "name": "explorer.exe"}

    mock_bot_proc = MagicMock()
    mock_bot_proc.pid = 200
    mock_bot_proc.info = {"pid": 200, "name": "python.exe"}
    mock_bot_proc.cmdline.return_value = ["python.exe", "bot.py"]
    mock_bot_proc.cwd.return_value = "C:\\bots\\iris"

    with patch("psutil.process_iter", return_value=[mock_os_proc, mock_bot_proc]):
        bots = {"iris": BotConfig(id="iris", name="Iris", path="C:\\bots\\iris", cmd="python bot.py")}
        found = tracker.discover_processes(bots)

        # explorer.exe should have been skipped immediately without calling cmdline()
        assert not hasattr(mock_os_proc, "cmdline") or mock_os_proc.cmdline.call_count == 0
        assert found == 1
        assert "iris" in tracker.managed_processes


def test_process_spawner_find_in_path_fast_filter():
    spawner = ProcessSpawner()

    mock_system_proc = MagicMock()
    mock_system_proc.info = {"pid": 50, "name": "svchost.exe"}

    mock_python_proc = MagicMock()
    mock_python_proc.pid = 300
    mock_python_proc.info = {"pid": 300, "name": "python.exe"}
    mock_python_proc.cwd.return_value = "C:\\bots\\watcher"

    with patch("psutil.process_iter", return_value=[mock_system_proc, mock_python_proc]):
        pids = spawner.find_all_processes_in_path("C:\\bots\\watcher")
        assert pids == [300]
        # svchost.exe should not have cwd called
        assert not hasattr(mock_system_proc, "cwd") or mock_system_proc.cwd.call_count == 0


async def test_config_repository_save_async(tmp_path):
    cfg_file = tmp_path / "async_config.json"
    cfg_file.write_text("{}", encoding="utf-8")

    repo = ConfigRepository(str(cfg_file))
    success = await repo.save_async({"settings": {}, "bots": {}})
    assert success is True
    assert cfg_file.exists()


async def test_state_repository_save_async(tmp_path):
    state_file = tmp_path / "async_state.json"
    repo = StateRepository(str(state_file))
    repo.set("theme", "dark", auto_save=False)

    success = await repo.save_async()
    assert success is True
    assert repo.get("theme") == "dark"


async def test_log_rotator_rotate_async(tmp_path):
    log_file = tmp_path / "bot_async.log"
    log_file.write_text("X" * 2000, encoding="utf-8")

    rotator = LogRotator(max_bytes=1000, backup_count=2)

    # 1. rotate_file_async
    success, size_str = await rotator.rotate_file_async(str(log_file))
    assert success is True
    assert (tmp_path / "bot_async.log.1").exists()

    # 2. rotate_bot_log_async
    bot_cfg = BotConfig(id="b1", name="AsyncBot", path=str(tmp_path), cmd="python b.py", log="bot_async.log")
    log_file.write_text("Y" * 2000, encoding="utf-8")
    bot_success, _ = await rotator.rotate_bot_log_async(bot_cfg)
    assert bot_success is True

    # 3. rotate_all_bots_async
    results = await rotator.rotate_all_bots_async({"b1": bot_cfg}, force=True)
    assert len(results) == 1
    assert results[0][1] is True


async def test_git_client_async_methods(tmp_path):
    client = GitClient()

    with patch.object(client, "check_is_behind", return_value=True):
        behind = await client.check_is_behind_async(str(tmp_path))
        assert behind is True

    with patch.object(client, "update_repo", return_value=(True, "Updated", True, {"commit": "abc"})):
        ok, out, changed, details = await client.update_repo_async(str(tmp_path))
        assert ok is True
        assert changed is True
        assert details["commit"] == "abc"

    with patch.object(client, "rollback_repo", return_value=(True, "Rolled back", True, None)):
        rb_ok, rb_out, rb_changed, _ = await client.rollback_repo_async(str(tmp_path))
        assert rb_ok is True
        assert rb_changed is True

    with patch.object(client, "install_dependencies", return_value=(True, "Successfully installed")):
        pip_ok, pip_out = await client.install_dependencies_async(str(tmp_path))
        assert pip_ok is True
        assert "Successfully installed" in pip_out
