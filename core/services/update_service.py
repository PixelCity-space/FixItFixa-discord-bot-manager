import os
import json
import asyncio
from typing import Dict, Any, Optional, Tuple, List
from core.logger import log
from core.config.models import AppConfig, BotConfig
from core.interfaces.system import IGitClient
from core.interfaces.services import IBotLifecycleService

class UpdateService:
    """Orchestrates git updates, dependency installation, rollbacks, and self-updates."""
    def __init__(
        self,
        config: AppConfig,
        git_client: IGitClient,
        lifecycle_service: IBotLifecycleService,
        manager_root: str = "."
    ):
        self.config = config
        self.git_client = git_client
        self.lifecycle_service = lifecycle_service
        self.manager_root = os.path.abspath(manager_root)

    def prepare_manager_restart(self) -> str:
        """Writes a marker file to indicate a planned restart upon reboot."""
        temp_dir = os.path.join(self.manager_root, self.config.bot_settings.temp_dir)
        os.makedirs(temp_dir, exist_ok=True)
        flag_path = os.path.join(temp_dir, "manager_restart.json")
        try:
            with open(flag_path, "w", encoding="utf-8") as f:
                json.dump({"restarted_at": str(asyncio.get_event_loop().time())}, f)
            log.info(f"[UpdateService] Created manager restart marker: {flag_path}")
        except Exception as e:
            log.error(f"[UpdateService] Failed to create manager restart marker: {e}")
        return flag_path

    async def update_manager(self) -> Tuple[bool, str, bool, Optional[Dict[str, Any]]]:
        """Performs Git pull and Pip dependency installation for the Manager itself."""
        branch = self.config.bot_settings.git_branch
        log.info(f"[UpdateService] Updating Manager at {self.manager_root} on branch {branch}")

        update_fn = getattr(self.git_client, "update_repo_async", None)
        if callable(update_fn) and asyncio.iscoroutinefunction(update_fn):
            success, output, changed, details = await update_fn(self.manager_root, branch)
        else:
            success, output, changed, details = await asyncio.to_thread(
                self.git_client.update_repo, self.manager_root, branch
            )

        if not success:
            return False, output, False, None

        if not changed:
            return True, "No changes detected.", False, None

        # Install dependencies
        pip_fn = getattr(self.git_client, "install_dependencies_async", None)
        if callable(pip_fn) and asyncio.iscoroutinefunction(pip_fn):
            pip_ok, pip_out = await pip_fn(self.manager_root)
        else:
            pip_ok, pip_out = await asyncio.to_thread(
                self.git_client.install_dependencies, self.manager_root
            )

        if details:
            details["pip_status"] = "OK" if pip_ok else f"Error: {pip_out[:100]}"

        return True, f"{output}\n{pip_out}", True, details

    async def update_bot(self, bot_id: str) -> Tuple[bool, str, bool, Optional[Dict[str, Any]], List[Tuple[BotConfig, Optional[int], Optional[str]]]]:
        """Updates a bot or bot cluster via Git and restarts them if code changed."""
        bot_cfg = self.config.bots.get(bot_id)
        if not bot_cfg:
            return False, "Bot not found", False, None, []

        branch = bot_cfg.git_branch or self.config.bot_settings.git_branch
        log.info(f"[UpdateService] Updating bot '{bot_cfg.name}' at {bot_cfg.path} (branch: {branch})")

        update_fn = getattr(self.git_client, "update_repo_async", None)
        if callable(update_fn) and asyncio.iscoroutinefunction(update_fn):
            success, output, changed, details = await update_fn(bot_cfg.path, branch)
        else:
            success, output, changed, details = await asyncio.to_thread(
                self.git_client.update_repo, bot_cfg.path, branch
            )

        if not success:
            return False, output, False, None, []

        if not changed:
            return True, output, False, None, []

        # Install dependencies
        pip_fn = getattr(self.git_client, "install_dependencies_async", None)
        if callable(pip_fn) and asyncio.iscoroutinefunction(pip_fn):
            pip_ok, pip_out = await pip_fn(bot_cfg.path, bot_cfg.cmd)
        else:
            pip_ok, pip_out = await asyncio.to_thread(
                self.git_client.install_dependencies, bot_cfg.path, bot_cfg.cmd
            )

        if details:
            details["pip_status"] = "OK" if pip_ok else f"Error: {pip_out[:100]}"

        # Restart cluster
        restart_results = await self.lifecycle_service.restart_bot_cluster(bot_id)
        combined_output = f"{output}\n{pip_out}"

        return True, combined_output, True, details, restart_results

    async def rollback_bot(self, bot_id: str) -> Tuple[bool, str, bool, Optional[Dict[str, Any]], List[Tuple[BotConfig, Optional[int], Optional[str]]]]:
        """Rolls back the repository to previous ref and restarts all related bots."""
        bot_cfg = self.config.bots.get(bot_id)
        if not bot_cfg:
            return False, "Bot not found", False, None, []

        log.info(f"[UpdateService] Rolling back bot '{bot_cfg.name}' at {bot_cfg.path}")
        rollback_fn = getattr(self.git_client, "rollback_repo_async", None)
        if callable(rollback_fn) and asyncio.iscoroutinefunction(rollback_fn):
            success, output, changed, details = await rollback_fn(bot_cfg.path)
        else:
            success, output, changed, details = await asyncio.to_thread(
                self.git_client.rollback_repo, bot_cfg.path
            )

        if not success:
            return False, output, False, None, []

        # Re-install dependencies (if requirements changed)
        pip_fn = getattr(self.git_client, "install_dependencies_async", None)
        if callable(pip_fn) and asyncio.iscoroutinefunction(pip_fn):
            pip_ok, pip_out = await pip_fn(bot_cfg.path, bot_cfg.cmd)
        else:
            pip_ok, pip_out = await asyncio.to_thread(
                self.git_client.install_dependencies, bot_cfg.path, bot_cfg.cmd
            )

        if details:
            details["pip_status"] = "OK" if pip_ok else f"Error: {pip_out[:100]}"

        # Restart cluster
        restart_results = await self.lifecycle_service.restart_bot_cluster(bot_id)
        combined_output = f"{output}\n{pip_out}"

        return True, combined_output, True, details, restart_results

__all__ = ["UpdateService"]
