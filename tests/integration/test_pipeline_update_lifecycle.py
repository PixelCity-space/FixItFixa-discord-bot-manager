from unittest.mock import MagicMock, patch

from core.config.models import AppConfig, BotConfig
from core.services.bot_lifecycle_service import BotLifecycleService
from core.services.update_service import UpdateService
from core.system.git_client import GitClient
from core.system.process_spawner import ProcessSpawner
from core.system.process_tracker import ProcessTracker


async def test_e2e_git_update_to_cluster_restart_pipeline(tmp_path):
    # Setup cluster of 2 bots sharing same directory
    cluster_dir = tmp_path / "shared_bot_repo"
    cluster_dir.mkdir()

    bot1 = BotConfig(id="worker_a", name="Worker A", path=str(cluster_dir), cmd="python a.py")
    bot2 = BotConfig(id="worker_b", name="Worker B", path=str(cluster_dir), cmd="python b.py")
    app_cfg = AppConfig(bots={"worker_a": bot1, "worker_b": bot2})

    git_client = GitClient()
    tracker = ProcessTracker()
    spawner = ProcessSpawner()

    # Mock Git update and Pip install to succeed
    git_client.update_repo = MagicMock(
        return_value=(True, "Updated to commit 999", True, {"hash": "999", "message": "feat: new", "date": 12345})
    )
    git_client.install_dependencies = MagicMock(return_value=(True, "Successfully installed requirements."))

    # Mock Popen spawn to assign new PIDs
    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.pid = 7771
        mock_popen.return_value = mock_proc

        lifecycle_service = BotLifecycleService(config=app_cfg, spawner=spawner, tracker=tracker)
        update_service = UpdateService(config=app_cfg, git_client=git_client, lifecycle_service=lifecycle_service)

        # Perform end-to-end update for worker_a
        ok, output, changed, details, restarts = await update_service.update_bot("worker_a")

        assert ok is True
        assert changed is True
        assert details["hash"] == "999"
        assert details["pip_status"] == "OK"

        # Both bots in the cluster were restarted
        assert len(restarts) == 2
        restarted_ids = [r[0].id for r in restarts]
        assert "worker_a" in restarted_ids
        assert "worker_b" in restarted_ids


async def test_e2e_git_rollback_to_cluster_restart_pipeline(tmp_path):
    bot_dir = tmp_path / "rollback_repo"
    bot_dir.mkdir()

    bot = BotConfig(id="bot_rb", name="Rollback Target", path=str(bot_dir), cmd="python main.py")
    app_cfg = AppConfig(bots={"bot_rb": bot})

    git_client = GitClient()
    tracker = ProcessTracker()
    spawner = ProcessSpawner()

    git_client.rollback_repo = MagicMock(
        return_value=(True, "HEAD@{1} restored", True, {"hash": "prev888", "message": "revert"})
    )
    git_client.install_dependencies = MagicMock(return_value=(True, "Pip OK"))

    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.pid = 4444
        mock_popen.return_value = mock_proc

        lifecycle_service = BotLifecycleService(config=app_cfg, spawner=spawner, tracker=tracker)
        update_service = UpdateService(config=app_cfg, git_client=git_client, lifecycle_service=lifecycle_service)

        ok, output, changed, details, restarts = await update_service.rollback_bot("bot_rb")

        assert ok is True
        assert changed is True
        assert details["hash"] == "prev888"
        assert len(restarts) == 1
        assert restarts[0][1] == 4444


async def test_e2e_update_with_pip_failure_graceful_handling(tmp_path):
    bot_dir = tmp_path / "pip_fail_repo"
    bot_dir.mkdir()

    bot = BotConfig(id="b_pip_fail", name="Pip Fail Bot", path=str(bot_dir), cmd="python app.py")
    app_cfg = AppConfig(bots={"b_pip_fail": bot})

    git_client = GitClient()
    tracker = ProcessTracker()
    spawner = ProcessSpawner()

    git_client.update_repo = MagicMock(return_value=(True, "Pull success", True, {"hash": "333"}))
    git_client.install_dependencies = MagicMock(
        return_value=(False, "ERROR: Could not find a version that satisfies the requirement invalid-pkg")
    )

    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.pid = 3331
        mock_popen.return_value = mock_proc

        lifecycle_service = BotLifecycleService(config=app_cfg, spawner=spawner, tracker=tracker)
        update_service = UpdateService(config=app_cfg, git_client=git_client, lifecycle_service=lifecycle_service)

        ok, output, changed, details, restarts = await update_service.update_bot("b_pip_fail")

        assert ok is True
        assert changed is True
        assert "Error: ERROR: Could not find" in details["pip_status"]
        assert len(restarts) == 1


async def test_e2e_manager_self_update_pipeline(tmp_path):
    app_cfg = AppConfig()
    git_client = GitClient()
    git_client.update_repo = MagicMock(return_value=(True, "Manager updated", True, {"hash": "mgr123"}))
    git_client.install_dependencies = MagicMock(return_value=(True, "Manager pip OK"))

    lifecycle_service = MagicMock()
    update_service = UpdateService(
        config=app_cfg, git_client=git_client, lifecycle_service=lifecycle_service, manager_root=str(tmp_path)
    )

    ok, output, changed, details = await update_service.update_manager()

    assert ok is True
    assert changed is True
    assert details["hash"] == "mgr123"
    assert details["pip_status"] == "OK"
