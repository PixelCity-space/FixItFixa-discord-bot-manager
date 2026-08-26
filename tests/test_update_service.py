import pytest
from unittest.mock import AsyncMock, MagicMock
from core.config.models import AppConfig, BotConfig, BotSettingsConfig
from core.services.update_service import UpdateService

def test_update_service_prepare_manager_restart(tmp_path):
    app_cfg = AppConfig(bot_settings=BotSettingsConfig(temp_dir="tmp_test"))
    git_client = MagicMock()
    lifecycle_service = MagicMock()

    service = UpdateService(
        config=app_cfg,
        git_client=git_client,
        lifecycle_service=lifecycle_service,
        manager_root=str(tmp_path)
    )

    flag_file = service.prepare_manager_restart()
    assert (tmp_path / "tmp_test" / "manager_restart.json").exists()
    assert str(flag_file).endswith("manager_restart.json")

async def test_update_service_update_bot_success(tmp_path):
    bot = BotConfig(id="b1", name="Bot One", path=str(tmp_path), cmd="python app.py")
    app_cfg = AppConfig(bots={"b1": bot})
    
    git_client = MagicMock()
    git_client.update_repo.return_value = (True, "Pull output", True, {"commit": "abc1234"})
    git_client.install_dependencies.return_value = (True, "Pip success")

    lifecycle_service = MagicMock()
    lifecycle_service.restart_bot_cluster = AsyncMock(return_value=[(bot, 12345, None)])

    service = UpdateService(
        config=app_cfg,
        git_client=git_client,
        lifecycle_service=lifecycle_service,
        manager_root=str(tmp_path)
    )

    ok, output, changed, details, restarts = await service.update_bot("b1")

    assert ok is True
    assert changed is True
    assert details["commit"] == "abc1234"
    assert details["pip_status"] == "OK"
    assert len(restarts) == 1
    assert restarts[0][1] == 12345

async def test_update_service_update_bot_no_changes(tmp_path):
    bot = BotConfig(id="b1", name="Bot One", path=str(tmp_path), cmd="python app.py")
    app_cfg = AppConfig(bots={"b1": bot})
    
    git_client = MagicMock()
    git_client.update_repo.return_value = (True, "Already up to date.", False, None)

    lifecycle_service = MagicMock()
    lifecycle_service.restart_bot_cluster = AsyncMock()

    service = UpdateService(
        config=app_cfg,
        git_client=git_client,
        lifecycle_service=lifecycle_service,
        manager_root=str(tmp_path)
    )

    ok, output, changed, details, restarts = await service.update_bot("b1")

    assert ok is True
    assert changed is False
    assert restarts == []
    lifecycle_service.restart_bot_cluster.assert_not_called()

async def test_update_service_rollback_bot(tmp_path):
    bot = BotConfig(id="b1", name="Bot One", path=str(tmp_path), cmd="python app.py")
    app_cfg = AppConfig(bots={"b1": bot})
    
    git_client = MagicMock()
    git_client.rollback_repo.return_value = (True, "HEAD@{1} restored", True, {"commit": "prev999"})
    git_client.install_dependencies.return_value = (True, "Pip OK")

    lifecycle_service = MagicMock()
    lifecycle_service.restart_bot_cluster = AsyncMock(return_value=[(bot, 5555, None)])

    service = UpdateService(
        config=app_cfg,
        git_client=git_client,
        lifecycle_service=lifecycle_service,
        manager_root=str(tmp_path)
    )

    ok, output, changed, details, restarts = await service.rollback_bot("b1")

    assert ok is True
    assert changed is True
    assert details["commit"] == "prev999"
    assert restarts[0][1] == 5555

async def test_update_service_update_non_existent_bot():
    app_cfg = AppConfig(bots={})
    service = UpdateService(
        config=app_cfg,
        git_client=MagicMock(),
        lifecycle_service=MagicMock()
    )

    ok, msg, changed, details, restarts = await service.update_bot("ghost")
    assert ok is False
    assert "Bot not found" in msg
