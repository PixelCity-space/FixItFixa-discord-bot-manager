"""Shared Pytest fixtures and mock objects for FixItFixa test suite."""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from core.config.models import AppConfig, BotConfig, BotSettingsConfig, AccessControlConfig
from core.system.process_tracker import ProcessTracker
from core.services.i18n_service import LocalizationService

@pytest.fixture
def sample_config():
    """Provides a multi-bot test configuration with clustered and solo bots."""
    bot1 = BotConfig(id="b1", name="Bot 1", path="C:\\shared_cluster", cmd="python b1.py", log="b1.log")
    bot2 = BotConfig(id="b2", name="Bot 2", path="C:\\shared_cluster", cmd="python b2.py", log="b2.log")
    bot3 = BotConfig(id="b3", name="Solo Bot", path="C:\\solo_folder", cmd="python solo.py", log="solo.log")
    
    settings = BotSettingsConfig(
        language="hu",
        git_branch="origin/main",
        status_refresh_seconds=60,
        status_recreate_minutes=58,
        log_default_lines=50,
        purge_limit=1000
    )
    
    access = AccessControlConfig(
        roles={"admin": "111222", "tester": "333444"},
        channels={"admin": "555666", "public": "777888"}
    )
    
    return AppConfig(
        guild_id="999888",
        access_control=access,
        bot_settings=settings,
        ui_settings={"accent_color": 0x2b2d31, "view_timeout": 300},
        bots={"b1": bot1, "b2": bot2, "b3": bot3}
    )

@pytest.fixture
def mock_i18n():
    """Provides a live LocalizationService instance initialized with Hungarian locale."""
    return LocalizationService("hu")

@pytest.fixture
def mock_spawner():
    """Provides a mocked IProcessSpawner."""
    spawner = MagicMock()
    spawner.stop_timeout = 5.0
    spawner.restart_wait = 0.1
    spawner.spawn = MagicMock(return_value=12345)
    spawner.terminate_process = AsyncMock(return_value=True)
    spawner.kill_rogue_processes = AsyncMock(return_value=None)
    spawner.start_service = MagicMock(return_value=True)
    spawner.stop_service = MagicMock(return_value=True)
    spawner.restart_service = MagicMock(return_value=True)
    spawner.get_systemd_state = MagicMock(return_value="active")
    spawner.get_systemd_pid = MagicMock(return_value=12345)
    spawner.get_systemd_pid_async = AsyncMock(return_value=12345)
    spawner.execute_manager_restart = MagicMock()
    spawner.execute_manager_shutdown = MagicMock()
    return spawner

@pytest.fixture
def mock_tracker():
    """Provides an isolated ProcessTracker instance."""
    return ProcessTracker()

@pytest.fixture
def mock_git_client():
    """Provides a mocked IGitClient."""
    git_client = MagicMock()
    git_client.is_git_repo = MagicMock(return_value=True)
    git_client.clean_locks = MagicMock()
    git_client.get_commit_details = MagicMock(return_value={"hash": "abcdef1", "author": "Dev", "message": "feat", "date": "1700000000"})
    git_client.get_remote_url = MagicMock(return_value="https://github.com/repo/test")
    git_client.check_is_behind = MagicMock(return_value=False)
    git_client.update_repo = MagicMock(return_value=(True, "Updated successfully", True, {"hash": "abcdef1", "message": "feat"}))
    git_client.rollback_repo = MagicMock(return_value=(True, "Rolled back successfully", True, {"hash": "1234567", "message": "revert"}))
    git_client.install_dependencies = MagicMock(return_value=(True, "Dependencies installed."))
    return git_client

@pytest.fixture
def mock_user():
    """Provides a mock Discord Member with admin role."""
    user = MagicMock()
    user.id = 999111
    user.name = "TestAdmin"
    user.guild_permissions.administrator = True
    
    admin_role = MagicMock()
    admin_role.id = 111222
    user.roles = [admin_role]
    return user

@pytest.fixture
def mock_channel():
    """Provides a mock Discord TextChannel."""
    channel = MagicMock()
    channel.id = 555666
    channel.name = "admin-workshop"
    channel.send = AsyncMock()
    channel.purge = AsyncMock(return_value=[MagicMock(), MagicMock()])
    channel.fetch_message = AsyncMock()
    return channel

@pytest.fixture
def mock_interaction(mock_user, mock_channel, mock_bot):
    """Provides a fully mocked Discord Interaction."""
    interaction = MagicMock()
    interaction.user = mock_user
    interaction.channel = mock_channel
    interaction.channel_id = mock_channel.id
    interaction.guild_id = 999888
    interaction.client = mock_bot
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    return interaction

@pytest.fixture
def mock_bot(sample_config, mock_i18n, mock_spawner, mock_tracker, mock_git_client):
    """Provides a mocked BotManager client with all services attached."""
    bot = MagicMock()
    bot.user = MagicMock()
    bot.user.id = 1000000
    bot.user.name = "FixItFixa"
    bot.manager_name = "FixItFixa"
    bot.i18n = mock_i18n
    bot.app_cfg = sample_config
    bot.bots = sample_config.bots
    bot.admin_channel_id = sample_config.access_control.admin_channel_id
    bot.public_channel_id = sample_config.access_control.public_channel_id
    bot.admin_role_id = sample_config.access_control.admin_role_id
    bot.tester_role_id = sample_config.access_control.tester_role_id
    bot.ui_settings = sample_config.ui_settings
    bot.spawner = mock_spawner
    bot.tracker = mock_tracker
    bot.git_client = mock_git_client
    
    # State repo mock
    state_repo = MagicMock()
    state_repo.get = MagicMock(side_effect=lambda k, d=None: "999000" if "id" in k else d)
    state_repo.set = MagicMock()
    bot.state_repo = state_repo
    
    # Config repo mock
    config_repo = MagicMock()
    config_repo.app_config = sample_config
    bot.config_repo = config_repo

    # Services
    bot.lifecycle_service = MagicMock()
    bot.lifecycle_service.restart_bot_cluster = AsyncMock(return_value=[(sample_config.bots["b1"], 12345, None)])
    bot.lifecycle_service.start_bot = AsyncMock(return_value=12345)
    bot.lifecycle_service.stop_bot = AsyncMock(return_value=(True, None))

    bot.update_service = MagicMock()
    bot.update_service.update_manager = AsyncMock(return_value=(True, "Manager updated", True, {"hash": "abcdef1", "message": "update"}))
    bot.update_service.update_bot = AsyncMock(return_value=(True, "Bot updated", True, {"hash": "abcdef1", "message": "update"}, [(sample_config.bots["b1"], 12345, None)]))
    bot.update_service.rollback_bot = AsyncMock(return_value=(True, "Bot rolled back", True, {"hash": "1234567", "message": "rollback"}, [(sample_config.bots["b1"], 12345, None)]))
    bot.update_service.prepare_manager_restart = MagicMock(return_value="tmp/restart.json")

    bot.health_service = MagicMock()
    bot.health_service.check_health = AsyncMock(return_value=[])

    manager_stats = {
        "cpu": 1.0,
        "ram": 50,
        "uptime": "1d",
        "branch": "main",
        "os": "Windows",
        "sys_cpu_free": 80,
        "sys_ram_free": 4000,
        "sys_disk_free": 100,
        "swap": 0,
        "host_uptime": "5d",
        "net": "↓0B ↑0B"
    }
    bot.telemetry_service.get_status_snapshot = MagicMock(return_value=(manager_stats, {}))

    bot.notify_admin = AsyncMock()
    bot.cleanup_status_panel = AsyncMock()

    return bot
