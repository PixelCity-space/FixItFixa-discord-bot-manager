import os
import asyncio
import psutil
from typing import List, Optional, Callable, Tuple
from core.logger import log
from core.config.models import BotConfig, AppConfig
from core.interfaces.system import IProcessSpawner, IProcessTracker

class BotLifecycleService:
    """Orchestrates starting, stopping, and restarting child bot processes and clusters."""
    def __init__(
        self,
        config: AppConfig,
        spawner: IProcessSpawner,
        tracker: IProcessTracker,
        notify_callback: Optional[Callable] = None
    ):
        self.config = config
        self.spawner = spawner
        self.tracker = tracker
        self.notify_callback = notify_callback

    def _build_bot_env(self, bot_cfg: BotConfig) -> dict:
        """Constructs an isolated execution environment for a child bot."""
        env = os.environ.copy()
        for key in self.config.bot_settings.protected_env_vars:
            env.pop(key, None)
        env["MANAGED_LOGGING"] = "1"
        env["INSTANCE_NAME"] = bot_cfg.cmd.split()[-1] if bot_cfg.cmd else bot_cfg.name
        return env

    def get_related_bots(self, bot_id: str) -> List[BotConfig]:
        """Returns all bots sharing the same directory path (cluster)."""
        bot = self.config.bots.get(bot_id)
        if not bot:
            return []
        return [b for b in self.config.bots.values() if b.path == bot.path]

    async def start_bot(self, bot_id: str) -> Optional[int]:
        """Starts a single bot if not already running."""
        bot_cfg = self.config.bots.get(bot_id)
        if not bot_cfg:
            return None

        if self.tracker.is_running(bot_id):
            proc = self.tracker.managed_processes.get(bot_id)
            if proc:
                try:
                    return proc.pid
                except (psutil.NoSuchProcess, psutil.ZombieProcess):
                    self.tracker.unregister(bot_id)

        # Systemd check (Linux)
        if bot_cfg.systemd_service and os.name == 'posix':
            success = self.spawner.start_service(bot_cfg.systemd_service)
            if success:
                await asyncio.sleep(self.spawner.restart_wait)
                pid = await self.spawner.get_systemd_pid_async(bot_cfg.systemd_service)
                if pid:
                    self.tracker.register(bot_id, pid)
                    return pid
            return None

        env = self._build_bot_env(bot_cfg)
        pid = self.spawner.spawn(bot_cfg, env)
        if pid:
            self.tracker.register(bot_id, pid)
        return pid

    async def stop_bot(self, bot_id: str, clean_rogue: bool = True) -> bool:
        """Stops a single bot process and optionally cleans up rogue processes in its folder."""
        self.tracker.mark_manual_stop(bot_id)
        bot_cfg = self.config.bots.get(bot_id)

        # Linux systemd
        if bot_cfg and bot_cfg.systemd_service and os.name == 'posix':
            await asyncio.to_thread(self.spawner.stop_service, bot_cfg.systemd_service)

        # Terminate tracked process
        proc = self.tracker.managed_processes.get(bot_id)
        if proc:
            try:
                await self.spawner.terminate_process(proc)
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                pass
            except Exception as e:
                log.debug(f"[BotLifecycleService] Non-critical error terminating process for {bot_id}: {e}")

        self.tracker.unregister(bot_id)

        # Clean rogue processes in folder (if requested)
        if clean_rogue and bot_cfg and bot_cfg.path:
            await self.spawner.kill_rogue_processes(bot_cfg.path)

        await asyncio.sleep(self.spawner.restart_wait)
        return True

    async def restart_bot_cluster(self, bot_id: str) -> List[Tuple[BotConfig, Optional[int], Optional[str]]]:
        """Restarts the target bot and all related bots in the same folder.
        
        Properly sequences cluster restarts:
        1. First, stops all bots sharing the directory and cleans rogue processes.
        2. Then, sequentially launches all bots in the cluster.
        """
        bot_cfg = self.config.bots.get(bot_id)
        if not bot_cfg:
            return []

        related = self.get_related_bots(bot_id)
        results = []

        # 1. Stop all bots in the cluster first
        for b in related:
            try:
                await self.stop_bot(b.id, clean_rogue=False)
            except Exception as e:
                log.error(f"[BotLifecycleService] Error stopping bot {b.name}: {e}")

        # Clean rogue processes in the shared folder once all tracked bots are stopped
        if bot_cfg.path:
            await self.spawner.kill_rogue_processes(bot_cfg.path)

        # 2. Start all bots in the cluster
        for b in related:
            try:
                new_pid = await self.start_bot(b.id)
                results.append((b, new_pid, None))
            except Exception as e:
                log.error(f"[BotLifecycleService] Error starting bot {b.name}: {e}")
                results.append((b, None, str(e)))

        return results
