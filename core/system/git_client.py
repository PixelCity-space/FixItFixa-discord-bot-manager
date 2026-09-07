import os
import re
import subprocess
import sys
from typing import Any

from core.common.retry import retry_sync
from core.logger import log


class GitClient:
    """Provides pure Git and Pip execution operations without Discord UI dependencies."""

    def __init__(
        self,
        requirements_file: str = "requirements.txt",
        rollback_ref: str = "HEAD@{1}",
        default_timeout: float = 30.0,
        pip_timeout: float = 180.0,
    ):
        self.requirements_file = requirements_file
        self.rollback_ref = rollback_ref
        self.default_timeout = default_timeout
        self.pip_timeout = pip_timeout

    def _get_git_env(self) -> dict[str, str]:
        """Returns environment variables disabling interactive prompts for Git."""
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_ASKPASS"] = "echo"
        return env

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
            except (PermissionError, OSError) as e:
                log.error(f"[GitClient] Permission or I/O error removing Git lock file {lock_file}: {e}")
            except Exception as e:
                log.error(f"[GitClient] Failed to remove Git lock file {lock_file}: {e}")

    @staticmethod
    def is_safe_ref(ref: str) -> bool:
        """Validates that a git reference or branch name contains no dangerous shell or git flags."""
        if not ref or not isinstance(ref, str):
            return False
        ref = ref.strip()
        if not ref or ref.startswith("-") or ".." in ref:
            return False
        return bool(re.match(r"^[a-zA-Z0-9_\-\./@{}~^]+$", ref))

    def get_commit_details(self, repo_path: str, rev: str = "HEAD") -> dict[str, Any] | None:
        """Retrieves hash, author, subject, and timestamp of a commit revision."""
        if not self.is_git_repo(repo_path) or not self.is_safe_ref(rev):
            if not self.is_safe_ref(rev):
                log.error(f"[GitClient] Dangerous or invalid git ref rejected: '{rev}'")
            return None
        try:
            env = self._get_git_env()
            commit_hash = (
                subprocess.check_output(
                    ["git", "rev-parse", "--short", rev],
                    cwd=repo_path,
                    timeout=self.default_timeout,
                    env=env,
                )
                .decode("utf-8")
                .strip()
            )
            author = (
                subprocess.check_output(
                    ["git", "show", "-s", "--format=%an", rev],
                    cwd=repo_path,
                    timeout=self.default_timeout,
                    env=env,
                )
                .decode("utf-8")
                .strip()
            )
            message = (
                subprocess.check_output(
                    ["git", "show", "-s", "--format=%s", rev],
                    cwd=repo_path,
                    timeout=self.default_timeout,
                    env=env,
                )
                .decode("utf-8")
                .strip()
            )
            date = (
                subprocess.check_output(
                    ["git", "show", "-s", "--format=%ct", rev],
                    cwd=repo_path,
                    timeout=self.default_timeout,
                    env=env,
                )
                .decode("utf-8")
                .strip()
            )

            return {"hash": commit_hash, "author": author, "message": message, "date": date}
        except subprocess.TimeoutExpired:
            log.warning(f"[GitClient] Git command timed out retrieving commit details for {rev} at {repo_path}")
            return None
        except subprocess.CalledProcessError as e:
            log.debug(
                f"[GitClient] Git command failed retrieving commit details for {rev} at {repo_path}: exit code {e.returncode}"
            )
            return None
        except FileNotFoundError:
            log.error("[GitClient] git executable not found on system path.")
            return None
        except Exception as e:
            log.error(f"[GitClient] Failed to get commit details for {rev} at {repo_path}: {e}")
            return None

    def get_remote_url(self, repo_path: str) -> str | None:
        """Gets the HTTPS web URL of origin remote."""
        if not self.is_git_repo(repo_path):
            return None
        try:
            url = (
                subprocess.check_output(
                    ["git", "config", "--get", "remote.origin.url"],
                    cwd=repo_path,
                    timeout=10,
                    env=self._get_git_env(),
                )
                .decode("utf-8")
                .strip()
            )
            if url.startswith("git@"):
                url = re.sub(r"^git@([^:]+):", r"https://\1/", url)

            if url.endswith(".git"):
                url = url[:-4]
            return url
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            log.debug(f"[GitClient] Failed or timed out getting remote.origin.url in {repo_path}: {e}")
            return None
        except FileNotFoundError:
            log.debug("[GitClient] git executable not found when fetching remote url.")
            return None
        except Exception as e:
            log.debug(f"[GitClient] Error getting remote url for {repo_path}: {e}")
            return None

    def check_is_behind(self, repo_path: str, branch: str = "origin/main") -> bool:
        """Fetches from remote and counts commits behind the target branch with retry support."""
        if not self.is_git_repo(repo_path):
            return False
        if not self.is_safe_ref(branch):
            log.error(f"[GitClient] Dangerous or invalid git branch rejected: '{branch}'")
            return False

        def _do_fetch_and_check():
            env = self._get_git_env()
            fetch_res = subprocess.run(
                ["git", "fetch", "--all"],
                cwd=repo_path,
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
                env=env,
            )
            if fetch_res.returncode != 0:
                log.debug(f"[GitClient] Fetch returned non-zero for {repo_path}: {fetch_res.stderr.strip()}")
                return False

            result = subprocess.run(
                ["git", "rev-list", "--count", f"HEAD..{branch}"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
                env=env,
            )
            if result.returncode == 0:
                count = int(result.stdout.strip())
                return count > 0
            return False

        try:
            return retry_sync(
                _do_fetch_and_check,
                max_retries=2,
                initial_delay=0.5,
                backoff_factor=1.5,
                exceptions=(subprocess.TimeoutExpired, OSError),
            )
        except subprocess.TimeoutExpired:
            log.warning(f"[GitClient] Git check timed out for {repo_path}")
            return False
        except FileNotFoundError:
            log.error("[GitClient] git executable not found.")
            return False
        except Exception as e:
            log.error(f"[GitClient] Error checking updates for {repo_path}: {e}")
            return False

    def update_repo(self, repo_path: str, branch: str = "origin/main") -> tuple[bool, str, bool, dict[str, Any] | None]:
        """Pulls latest changes by resetting hard to target branch."""
        if not self.is_git_repo(repo_path):
            return False, f"Not a valid git repository directory: '{repo_path}'", False, None
        if not self.is_safe_ref(branch):
            msg = f"Dangerous or invalid git branch name rejected: '{branch}'"
            log.error(f"[GitClient] {msg}")
            return False, msg, False, None

        self.clean_locks(repo_path)
        results = []
        env = self._get_git_env()
        try:
            old_hash = (
                subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo_path,
                    stderr=subprocess.STDOUT,
                    timeout=10,
                    env=env,
                )
                .decode("utf-8")
                .strip()
            )
            fetch_out = subprocess.check_output(
                ["git", "fetch", "--all"],
                cwd=repo_path,
                stderr=subprocess.STDOUT,
                timeout=self.default_timeout,
                env=env,
            ).decode("utf-8")
            results.append(fetch_out)

            reset_out = subprocess.check_output(
                ["git", "reset", "--hard", branch],
                cwd=repo_path,
                stderr=subprocess.STDOUT,
                timeout=self.default_timeout,
                env=env,
            ).decode("utf-8")
            results.append(reset_out)

            new_hash = (
                subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo_path,
                    stderr=subprocess.STDOUT,
                    timeout=10,
                    env=env,
                )
                .decode("utf-8")
                .strip()
            )

            changed = old_hash != new_hash
            details = None
            if changed:
                details = self.get_commit_details(repo_path)
                if details:
                    remote_url = self.get_remote_url(repo_path)
                    if remote_url:
                        details["repo_url"] = remote_url

            return True, "\n".join(results), changed, details
        except subprocess.TimeoutExpired as e:
            msg = f"Git update command timed out after {e.timeout}s at {repo_path}"
            log.error(f"[GitClient] {msg}")
            return False, msg, False, None
        except subprocess.CalledProcessError as e:
            error_msg = e.output.decode("utf-8") if e.output else str(e)
            log.error(f"[GitClient] Git update command failed at {repo_path}: {error_msg}")
            return False, error_msg, False, None
        except FileNotFoundError:
            msg = "git executable not found on system."
            log.error(f"[GitClient] {msg}")
            return False, msg, False, None
        except (PermissionError, OSError) as e:
            log.error(f"[GitClient] I/O or permission error updating {repo_path}: {e}")
            return False, str(e), False, None
        except Exception as e:
            log.error(f"[GitClient] Unexpected error during git update at {repo_path}: {e}")
            return False, str(e), False, None

    def rollback_repo(self, repo_path: str) -> tuple[bool, str, bool, dict[str, Any] | None]:
        """Rolls back the repository to previous ref (e.g. HEAD@{1})."""
        if not self.is_git_repo(repo_path):
            return False, f"Not a valid git repository directory: '{repo_path}'", False, None

        env = self._get_git_env()
        try:
            output = subprocess.check_output(
                ["git", "reset", "--hard", self.rollback_ref],
                cwd=repo_path,
                stderr=subprocess.STDOUT,
                timeout=self.default_timeout,
                env=env,
            ).decode("utf-8")

            details = self.get_commit_details(repo_path)
            if details:
                remote_url = self.get_remote_url(repo_path)
                if remote_url:
                    details["repo_url"] = remote_url

            return True, output, True, details
        except subprocess.TimeoutExpired as e:
            msg = f"Rollback command timed out after {e.timeout}s at {repo_path}"
            log.error(f"[GitClient] {msg}")
            return False, msg, False, None
        except subprocess.CalledProcessError as e:
            error_msg = e.output.decode("utf-8") if e.output else str(e)
            log.error(f"[GitClient] Rollback command failed at {repo_path}: {error_msg}")
            return False, error_msg, False, None
        except FileNotFoundError:
            msg = "git executable not found on system."
            log.error(f"[GitClient] {msg}")
            return False, msg, False, None
        except (PermissionError, OSError) as e:
            log.error(f"[GitClient] I/O or permission error rolling back {repo_path}: {e}")
            return False, str(e), False, None
        except Exception as e:
            log.error(f"[GitClient] Unexpected error during rollback at {repo_path}: {e}")
            return False, str(e), False, None

    def install_dependencies(self, repo_path: str, bot_cmd: str | None = None) -> tuple[bool, str]:
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
                pip_cmd + ["install", "--no-input", "-r", self.requirements_file],
                cwd=repo_path,
                stderr=subprocess.STDOUT,
                timeout=self.pip_timeout,
            ).decode("utf-8")
            return True, output
        except subprocess.TimeoutExpired as e:
            msg = f"Pip install timed out after {e.timeout}s at {repo_path}"
            log.error(f"[GitClient] {msg}")
            return False, msg
        except subprocess.CalledProcessError as e:
            error_msg = e.output.decode("utf-8") if e.output else str(e)
            log.error(f"[GitClient] Pip install failed at {repo_path}: {error_msg}")
            return False, error_msg
        except FileNotFoundError as e:
            msg = f"Python or pip executable not found for {repo_path}: {e}"
            log.error(f"[GitClient] {msg}")
            return False, msg
        except (PermissionError, OSError) as e:
            log.error(f"[GitClient] I/O error during pip install in {repo_path}: {e}")
            return False, str(e)
        except Exception as e:
            log.error(f"[GitClient] Unexpected error during pip install at {repo_path}: {e}")
            return False, str(e)

    async def check_is_behind_async(self, repo_path: str, branch: str = "origin/main") -> bool:
        """Asynchronously checks if local branch is behind remote."""
        import asyncio

        return await asyncio.to_thread(self.check_is_behind, repo_path, branch)

    async def update_repo_async(
        self, repo_path: str, branch: str = "origin/main"
    ) -> tuple[bool, str, bool, dict[str, Any] | None]:
        """Asynchronously executes git fetch and reset operations in a worker thread."""
        import asyncio

        return await asyncio.to_thread(self.update_repo, repo_path, branch)

    async def rollback_repo_async(self, repo_path: str) -> tuple[bool, str, bool, dict[str, Any] | None]:
        """Asynchronously rolls back repository in a worker thread."""
        import asyncio

        return await asyncio.to_thread(self.rollback_repo, repo_path)

    async def install_dependencies_async(self, repo_path: str, bot_cmd: str | None = None) -> tuple[bool, str]:
        """Asynchronously executes pip install in a worker thread."""
        import asyncio

        return await asyncio.to_thread(self.install_dependencies, repo_path, bot_cmd)


__all__ = ["GitClient"]
