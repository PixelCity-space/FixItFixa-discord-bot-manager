import os

from core.system.git_client import GitClient


def test_git_client_is_git_repo(tmp_path):
    client = GitClient()

    # Non-existent path
    assert client.is_git_repo(str(tmp_path / "does_not_exist")) is False

    # Directory without .git
    plain_dir = tmp_path / "plain_dir"
    plain_dir.mkdir()
    assert client.is_git_repo(str(plain_dir)) is False

    # Valid directory with .git folder
    git_dir = tmp_path / "git_dir"
    git_dir.mkdir()
    (git_dir / ".git").mkdir()
    assert client.is_git_repo(str(git_dir)) is True


def test_git_client_clean_locks(tmp_path):
    client = GitClient()
    git_dir = tmp_path / "repo_with_lock"
    git_dir.mkdir()
    dot_git = git_dir / ".git"
    dot_git.mkdir()
    lock_file = dot_git / "index.lock"
    lock_file.write_text("lock", encoding="utf-8")

    assert os.path.exists(lock_file)
    client.clean_locks(str(git_dir))
    assert not os.path.exists(lock_file)


def test_git_client_update_repo_invalid_dir(tmp_path):
    client = GitClient()
    invalid_path = str(tmp_path / "not_a_repo")
    success, msg, changed, details = client.update_repo(invalid_path)
    assert success is False
    assert "Not a valid git repository" in msg
    assert changed is False
    assert details is None


def test_git_client_rollback_invalid_dir(tmp_path):
    client = GitClient()
    invalid_path = str(tmp_path / "not_a_repo")
    success, msg, changed, details = client.rollback_repo(invalid_path)
    assert success is False
    assert "Not a valid git repository" in msg
    assert changed is False


def test_git_client_custom_init():
    client = GitClient(requirements_file="custom_req.txt", rollback_ref="HEAD~2")
    assert client.requirements_file == "custom_req.txt"
    assert client.rollback_ref == "HEAD~2"


def test_git_client_default_properties():
    client = GitClient()
    assert client.requirements_file == "requirements.txt"
    assert client.rollback_ref == "HEAD@{1}"
    assert client.default_timeout == 30.0
    assert client.pip_timeout == 180.0
    env = client._get_git_env()
    assert env.get("GIT_TERMINAL_PROMPT") == "0"
    assert env.get("GIT_ASKPASS") == "echo"


def test_git_client_timeout_handling(tmp_path, monkeypatch):
    import subprocess

    client = GitClient(default_timeout=5.0)
    git_dir = tmp_path / "repo_timeout"
    git_dir.mkdir()
    (git_dir / ".git").mkdir()

    def mock_check_output(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=5.0)

    monkeypatch.setattr(subprocess, "check_output", mock_check_output)

    success, msg, changed, details = client.update_repo(str(git_dir))
    assert success is False
    assert "timed out" in msg.lower()

    success_rb, msg_rb, changed_rb, details_rb = client.rollback_repo(str(git_dir))
    assert success_rb is False
    assert "timed out" in msg_rb.lower()

    (git_dir / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    success_pip, msg_pip = client.install_dependencies(str(git_dir))
    assert success_pip is False
    assert "timed out" in msg_pip.lower()


async def test_git_client_async_wrappers(tmp_path):
    client = GitClient()
    invalid_path = str(tmp_path / "invalid")

    behind = await client.check_is_behind_async(invalid_path)
    assert behind is False

    up_ok, msg, _, _ = await client.update_repo_async(invalid_path)
    assert up_ok is False

    rb_ok, msg_rb, _, _ = await client.rollback_repo_async(invalid_path)
    assert rb_ok is False

    pip_ok, _ = await client.install_dependencies_async(invalid_path)
    assert pip_ok is True


def test_git_client_get_remote_url_enterprise(tmp_path, monkeypatch):
    import subprocess

    client = GitClient()
    git_dir = tmp_path / "enterprise_repo"
    git_dir.mkdir()
    (git_dir / ".git").mkdir()

    # 1. GitHub Enterprise SSH URL
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda *args, **kwargs: b"git@github.internal.mycompany.com:devops/fixitfixa.git\n",
    )
    url = client.get_remote_url(str(git_dir))
    assert url == "https://github.internal.mycompany.com/devops/fixitfixa"

    # 2. GitLab SSH URL
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda *args, **kwargs: b"git@gitlab.corp.net:infra/bot.git\n",
    )
    url = client.get_remote_url(str(git_dir))
    assert url == "https://gitlab.corp.net/infra/bot"

    # 3. Standard GitHub HTTPS URL
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda *args, **kwargs: b"https://github.com/stargate91/discord-bot-manager.git\n",
    )
    url = client.get_remote_url(str(git_dir))
    assert url == "https://github.com/stargate91/discord-bot-manager"


def test_git_client_get_commit_details(tmp_path, monkeypatch):
    import subprocess

    client = GitClient()
    git_dir = tmp_path / "details_repo"
    git_dir.mkdir()
    (git_dir / ".git").mkdir()

    # Unsafe ref rejection
    assert client.get_commit_details(str(git_dir), "--bad-flag") is None

    # Normal success
    outputs = [b"a1b2c3d\n", b"John Doe\n", b"Fix bug #123\n", b"1700000000\n"]

    def mock_check(*args, **kwargs):
        return outputs.pop(0)

    monkeypatch.setattr(subprocess, "check_output", mock_check)
    details = client.get_commit_details(str(git_dir), "HEAD")
    assert details == {
        "hash": "a1b2c3d",
        "author": "John Doe",
        "message": "Fix bug #123",
        "date": "1700000000",
    }

    # CalledProcessError handling
    def mock_error(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr(subprocess, "check_output", mock_error)
    assert client.get_commit_details(str(git_dir), "HEAD") is None

    # FileNotFoundError handling
    def mock_fnf(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(subprocess, "check_output", mock_fnf)
    assert client.get_commit_details(str(git_dir), "HEAD") is None


def test_git_client_check_is_behind_scenarios(tmp_path, monkeypatch):
    import subprocess
    from unittest.mock import MagicMock

    client = GitClient()
    git_dir = tmp_path / "behind_repo"
    git_dir.mkdir()
    (git_dir / ".git").mkdir()

    # Dangerous ref
    assert client.check_is_behind(str(git_dir), "; rm -rf /") is False

    # Fetch error
    fail_res = MagicMock(returncode=1, stderr="Failed to connect")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: fail_res)
    assert client.check_is_behind(str(git_dir), "origin/main") is False

    # Fetch ok, rev-list returns 3 commits behind
    def mock_run(*args, **kwargs):
        cmd = args[0]
        if "fetch" in cmd:
            return MagicMock(returncode=0, stderr="")
        if "rev-list" in cmd:
            return MagicMock(returncode=0, stdout="3\n")
        return MagicMock(returncode=0)

    monkeypatch.setattr(subprocess, "run", mock_run)
    assert client.check_is_behind(str(git_dir), "origin/main") is True

    # Fetch ok, rev-list returns 0 commits behind
    def mock_run_uptodate(*args, **kwargs):
        cmd = args[0]
        if "fetch" in cmd:
            return MagicMock(returncode=0, stderr="")
        if "rev-list" in cmd:
            return MagicMock(returncode=0, stdout="0\n")
        return MagicMock(returncode=0)

    monkeypatch.setattr(subprocess, "run", mock_run_uptodate)
    assert client.check_is_behind(str(git_dir), "origin/main") is False


def test_git_client_update_repo_success(tmp_path, monkeypatch):
    import subprocess

    client = GitClient()
    git_dir = tmp_path / "update_repo"
    git_dir.mkdir()
    (git_dir / ".git").mkdir()

    # Dangerous branch
    ok, msg, _, _ = client.update_repo(str(git_dir), "-f")
    assert ok is False

    # Update succeeds with changes
    # Sequence: old_hash, fetch, reset, new_hash
    cmd_outputs = [b"hash_old\n", b"Fetched 2 commits\n", b"HEAD is at hash_new\n", b"hash_new\n"]

    def mock_check_output(*args, **kwargs):
        if cmd_outputs:
            return cmd_outputs.pop(0)
        return b"https://github.com/org/repo.git\n"

    monkeypatch.setattr(subprocess, "check_output", mock_check_output)
    monkeypatch.setattr(
        client, "get_commit_details", lambda *a, **k: {"hash": "hash_new", "author": "Alice", "message": "Updated"}
    )
    monkeypatch.setattr(client, "get_remote_url", lambda *a, **k: "https://github.com/org/repo")

    ok, out, changed, details = client.update_repo(str(git_dir), "origin/main")
    assert ok is True
    assert changed is True
    assert details["hash"] == "hash_new"
    assert details["repo_url"] == "https://github.com/org/repo"


def test_git_client_rollback_repo_success(tmp_path, monkeypatch):
    import subprocess

    client = GitClient()
    git_dir = tmp_path / "rb_repo"
    git_dir.mkdir()
    (git_dir / ".git").mkdir()

    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: b"HEAD is now at 1234567\n")
    monkeypatch.setattr(
        client, "get_commit_details", lambda *a, **k: {"hash": "1234567", "author": "Bob", "message": "Revert"}
    )
    monkeypatch.setattr(client, "get_remote_url", lambda *a, **k: "https://github.com/org/repo")

    ok, out, changed, details = client.rollback_repo(str(git_dir))
    assert ok is True
    assert changed is True
    assert details["hash"] == "1234567"
    assert details["repo_url"] == "https://github.com/org/repo"


def test_git_client_install_dependencies_with_bot_cmd(tmp_path, monkeypatch):
    import subprocess

    client = GitClient()
    git_dir = tmp_path / "pip_repo"
    git_dir.mkdir()
    (git_dir / "requirements.txt").write_text("requests\n", encoding="utf-8")

    captured_cmds = []

    def mock_pip_check(cmd, *args, **kwargs):
        captured_cmds.append(cmd)
        return b"Successfully installed requests\n"

    monkeypatch.setattr(subprocess, "check_output", mock_pip_check)

    # Custom bot command with python path
    ok, out = client.install_dependencies(str(git_dir), bot_cmd="/custom/venv/bin/python main.py")
    assert ok is True
    assert "Successfully installed" in out
    assert captured_cmds[0][0] == "/custom/venv/bin/python"

    # CalledProcessError failure
    def mock_pip_fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0], output=b"No matching distribution")

    monkeypatch.setattr(subprocess, "check_output", mock_pip_fail)
    ok_fail, out_fail = client.install_dependencies(str(git_dir))
    assert ok_fail is False
    assert "No matching distribution" in out_fail
