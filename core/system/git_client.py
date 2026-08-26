import os
import sys
import subprocess
from typing import Optional, Dict, Any, Tuple
from core.logger import log

class GitClient:
    """Provides pure Git and Pip execution operations without Discord UI dependencies."""
    def __init__(self, requirements_file: str = "requirements.txt", rollback_ref: str = "HEAD@{1}"):
        self.requirements_file = requirements_file
        self.rollback_ref = rollback_ref

    def is_git_repo(self, repo_path: str) -> bool:
        """Checks if a given path is a valid existing directory with a .git repository."""
        if not repo_path or not os.path.exists(repo_path) or not os.path.isdir(repo_path):
            return False
        return os.path.exists(os.path.join(repo_path, ".git"))

    def clean_locks(self, repo_path: str) -> None:
        """Removes leftover .git/index.lock files that prevent git operations."""
        if not self.is_git_repo(repo_path):
            return
        lock_file = os.path.join(repo_path, ".git", "index.lock")
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
                log.info(f"[GitClient] Removed stuck Git lock file: {lock_file}")
            except Exception as e:
                log.error(f"[GitClient] Failed to remove Git lock file {lock_file}: {e}")

    def get_commit_details(self, repo_path: str, rev: str = "HEAD") -> Optional[Dict[str, str]]:
        """Retrieves hash, author, subject, and timestamp of a commit revision."""
        if not self.is_git_repo(repo_path):
            return None
        try:
            commit_hash = subprocess.check_output(["git", "rev-parse", "--short", rev], cwd=repo_path).decode('utf-8').strip()
            author = subprocess.check_output(["git", "show", "-s", "--format=%an", rev], cwd=repo_path).decode('utf-8').strip()
            message = subprocess.check_output(["git", "show", "-s", "--format=%s", rev], cwd=repo_path).decode('utf-8').strip()
            date = subprocess.check_output(["git", "show", "-s", "--format=%ct", rev], cwd=repo_path).decode('utf-8').strip()

            return {
                "hash": commit_hash,
                "author": author,
                "message": message,
                "date": date
            }
        except Exception as e:
            log.error(f"[GitClient] Failed to get commit details for {rev} at {repo_path}: {e}")
            return None

    def get_remote_url(self, repo_path: str) -> Optional[str]:
        """Gets the HTTPS web URL of origin remote."""
        if not self.is_git_repo(repo_path):
            return None
        try:
            url = subprocess.check_output(["git", "config", "--get", "remote.origin.url"], cwd=repo_path).decode('utf-8').strip()
            if url.startswith("git@"):
                url = url.replace(":", "/").replace("git@", "https://")

            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(url)
            if "github" in parsed.netloc and parsed.netloc != "github.com":
                parsed = parsed._replace(netloc="github.com")
                url = urlunparse(parsed)

            if url.endswith(".git"):
                url = url[:-4]
            return url
        except Exception:
            return None

    def check_is_behind(self, repo_path: str, branch: str = "origin/main") -> bool:
        """Fetches from remote and counts commits behind the target branch."""
        if not self.is_git_repo(repo_path):
            return False
        try:
            fetch_res = subprocess.run(["git", "fetch", "--all"], cwd=repo_path, check=False, capture_output=True, text=True)
            if fetch_res.returncode != 0:
                log.debug(f"[GitClient] Fetch failed for {repo_path}: {fetch_res.stderr.strip()}")
                return False

            result = subprocess.run(
                ["git", "rev-list", "--count", f"HEAD..{branch}"],
                cwd=repo_path, capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                count = int(result.stdout.strip())
                return count > 0
        except Exception as e:
            log.error(f"[GitClient] Error checking updates for {repo_path}: {e}")
        return False

    def update_repo(self, repo_path: str, branch: str = "origin/main") -> Tuple[bool, str, bool, Optional[Dict[str, Any]]]:
        """Pulls latest changes by resetting hard to target branch."""
        if not self.is_git_repo(repo_path):
            return False, f"Not a valid git repository directory: '{repo_path}'", False, None

        self.clean_locks(repo_path)
        results = []
        try:
            old_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_path, stderr=subprocess.STDOUT).decode('utf-8').strip()
            fetch_out = subprocess.check_output(["git", "fetch", "--all"], cwd=repo_path, stderr=subprocess.STDOUT).decode('utf-8')
            results.append(fetch_out)

            reset_out = subprocess.check_output(["git", "reset", "--hard", branch], cwd=repo_path, stderr=subprocess.STDOUT).decode('utf-8')
            results.append(reset_out)

            new_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_path, stderr=subprocess.STDOUT).decode('utf-8').strip()

            changed = (old_hash != new_hash)
            details = None
            if changed:
                details = self.get_commit_details(repo_path)
                if details:
                    details["repo_url"] = self.get_remote_url(repo_path)

            return True, "\n".join(results), changed, details
        except subprocess.CalledProcessError as e:
            error_msg = e.output.decode('utf-8') if e.output else str(e)
            log.error(f"[GitClient] Git update failed at {repo_path}: {error_msg}")
            return False, error_msg, False, None
        except Exception as e:
            log.error(f"[GitClient] Unexpected error during git update at {repo_path}: {e}")
            return False, str(e), False, None

    def rollback_repo(self, repo_path: str) -> Tuple[bool, str, bool, Optional[Dict[str, Any]]]:
        """Rolls back the repository to previous ref (e.g. HEAD@{1})."""
        if not self.is_git_repo(repo_path):
            return False, f"Not a valid git repository directory: '{repo_path}'", False, None

        try:
            output = subprocess.check_output(
                ["git", "reset", "--hard", self.rollback_ref],
                cwd=repo_path,
                stderr=subprocess.STDOUT
            ).decode('utf-8')

            details = self.get_commit_details(repo_path)
            if details:
                details["repo_url"] = self.get_remote_url(repo_path)

            return True, output, True, details
        except subprocess.CalledProcessError as e:
            error_msg = e.output.decode('utf-8') if e.output else str(e)
            log.error(f"[GitClient] Rollback failed at {repo_path}: {error_msg}")
            return False, error_msg, False, None
        except Exception as e:
            return False, str(e), False, None

    def install_dependencies(self, repo_path: str, bot_cmd: Optional[str] = None) -> Tuple[bool, str]:
        """Installs dependencies via pip in the context of the bot's python environment."""
        req_path = os.path.join(repo_path, self.requirements_file)
        if not os.path.exists(req_path):
            return True, f"No {self.requirements_file} found."

        try:
            pip_cmd = [sys.executable, "-m", "pip"]
            if bot_cmd:
                parts = bot_cmd.split()
                if len(parts) > 0:
                    potential_python = parts[0]
                    if "/" in potential_python or "\\" in potential_python or os.path.isabs(potential_python):
                        pip_cmd = [potential_python, "-m", "pip"]

            output = subprocess.check_output(
                pip_cmd + ["install", "-r", self.requirements_file],
                cwd=repo_path,
                stderr=subprocess.STDOUT
            ).decode('utf-8')
            return True, output
        except subprocess.CalledProcessError as e:
            error_msg = e.output.decode('utf-8') if e.output else str(e)
            log.error(f"[GitClient] Pip install failed at {repo_path}: {error_msg}")
            return False, error_msg
        except Exception as e:
            return False, str(e)
