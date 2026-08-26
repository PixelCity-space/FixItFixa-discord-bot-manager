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
