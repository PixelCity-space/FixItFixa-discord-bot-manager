import asyncio
import inspect
import os

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.checks import AccessLevel, get_user_level
from bot.ui.views.info_view import ModernInfoView
from bot.ui.views.status_view import ModernStatusView
from core.logger import log
from core.utils import format_desc, get_feedback


class MonitoringCog(commands.Cog):
    """Handles the live status dashboard, periodic status refreshes, and info commands."""

    def __init__(self, bot):
        self.bot = bot
        self.status_message_id = self.bot.state_repo.get("status_message_id")
        self.status_channel_id = self.bot.state_repo.get("status_channel_id")
        self._recreate_lock = asyncio.Lock()

        bot_settings = self.bot.app_cfg.bot_settings
        self.refresh_interval = bot_settings.status_refresh_seconds
        self.recreate_interval = bot_settings.status_recreate_minutes

        self.git_behind_status = {}
        self.current_page = 0
        self._background_tasks = set()
        self._initialized_panel = False

        for cmd in self.get_app_commands():
            if not hasattr(cmd, "_raw_desc"):
                cmd._raw_desc = cmd.description
            cmd.description = format_desc(self.bot, cmd._raw_desc)

    def get_total_pages(self) -> int:
        """Calculates total pages based on currently configured bot clusters."""
        bots = getattr(self.bot, "bots", {})
        path_groups = set(b.path for b in bots.values()) if bots else set()
        num_groups = len(path_groups)
        total_pages = 1 if num_groups <= 2 else 1 + (num_groups - 2 + 3 - 1) // 3
        return max(1, total_pages)

    async def change_page(self, delta: int) -> int:
        """Changes the current page with bounds validation and triggers a panel refresh."""
        total_pages = self.get_total_pages()
        new_page = max(0, min(self.current_page + delta, total_pages - 1))
        if new_page != self.current_page:
            self.current_page = new_page
            await self._refresh_status()
        return self.current_page

    async def _refresh_status(self):
        """Refreshes the status panel safely across Loop objects, async functions, and mocks."""
        if hasattr(self.update_status_task, "coro"):
            await self.update_status_task.coro(self)
        elif callable(self.update_status_task):
            res = self.update_status_task()
            if asyncio.iscoroutine(res) or hasattr(res, "__await__"):
                await res

    def create_tracked_task(self, coro, name: str = None) -> asyncio.Task:
        """Creates a tracked background task with exception logging and cleanup."""
        try:
            task = asyncio.create_task(coro, name=name)
        except RuntimeError:
            loop = getattr(self.bot, "loop", None)
            if loop and loop.is_running():
                task = loop.create_task(coro, name=name)
            else:
                return None

        self._background_tasks.add(task)

        def _cleanup(t):
            self._background_tasks.discard(t)
            if not t.cancelled() and t.exception() is not None:
                log.error(f"[MonitoringCog] Background task '{t.get_name()}' crashed: {t.exception()}", exc_info=True)

        task.add_done_callback(_cleanup)
        return task

    async def cog_load(self):
        log.info("[Status] MonitoringCog loaded. Starting background tasks...")
        self.update_status_task.change_interval(seconds=self.refresh_interval)
        self.recreate_status_task.change_interval(minutes=self.recreate_interval)

    @commands.Cog.listener()
    async def on_ready(self):
        log.info(f"[Status] Cog on_ready starting for user: {self.bot.user}")
        await asyncio.sleep(3)

        try:
            if not self._initialized_panel:
                log.info("[Status] Initializing persistent status panel for the first time...")
                await self.cleanup_and_recreate_panel()
                self._initialized_panel = True
            else:
                log.info("[Status] Gateway reconnected: updating existing status panel...")
                await self._refresh_status()

            log.info("[Status] Starting task loops...")
            if not self.update_status_task.is_running():
                self.update_status_task.start()
            if not self.recreate_status_task.is_running():
                self.recreate_status_task.start()
            if not self.git_fetch_task.is_running():
                self.git_fetch_task.start()
            log.info("[Status] Cog on_ready finished successfully.")
        except Exception as e:
            log.error(f"[Status] Error during cog on_ready: {e}", exc_info=True)

    def cog_unload(self):
        self.update_status_task.cancel()
        self.recreate_status_task.cancel()
        self.git_fetch_task.cancel()
        for t in list(self._background_tasks):
            t.cancel()
        self._background_tasks.clear()

    @tasks.loop(minutes=10)
    async def git_fetch_task(self):
        """Periodically checks concurrently if any bots or the manager have upstream updates."""
        log.info("[Git] Checking for updates in background threads...")
        manager_path = getattr(
            self.bot, "base_dir", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        bot_settings = self.bot.app_cfg.bot_settings
        default_branch = bot_settings.git_branch

        git_client = getattr(self.bot, "git_client", None)
        if not git_client:
            return

        async def _check_target(target_id: str, path: str, branch: str) -> tuple[str, bool]:
            try:
                is_behind = await asyncio.to_thread(git_client.check_is_behind, path, branch)
                return target_id, is_behind
            except Exception as e:
                log.warning(f"[Git] Error checking update for {target_id}: {e}")
                return target_id, False

        # Gather all check tasks to execute concurrently
        check_tasks = [_check_target("manager", manager_path, default_branch)]
        for bot_id, bot_config in self.bot.bots.items():
            target_branch = getattr(bot_config, "git_branch", None) or default_branch
            check_tasks.append(_check_target(bot_id, bot_config.path, target_branch))

        results = await asyncio.gather(*check_tasks)
        for target_id, is_behind in results:
            self.git_behind_status[target_id] = is_behind

        behind_count = sum(1 for _, is_behind in results if is_behind)
        log.info(f"[Git] Update check complete: {behind_count} update(s) available.")

    async def cleanup_and_recreate_panel(self, triggered_by_id=None):
        """Deletes any old status panel and posts a fresh modern panel in the admin workshop."""
        async with self._recreate_lock:
            if triggered_by_id and self.status_message_id != triggered_by_id:
                log.info("[Status] Cleanup skipped: message already recreated by another task.")
                return

            log.info("[Status] Cleaning up old status panel and creating a new one...")

            # 1. Delete old message
            if self.status_channel_id and self.status_message_id:
                try:
                    channel = self.bot.get_channel(int(self.status_channel_id))
                    if not channel:
                        channel = await self.bot.fetch_channel(int(self.status_channel_id))
                    if channel:
                        try:
                            old_msg = await channel.fetch_message(int(self.status_message_id))
                            await old_msg.delete()
                            log.info(f"[Status] Deleted old status message: {self.status_message_id}")
                        except discord.NotFound:
                            pass
                except Exception as e:
                    log.warning(f"[Status] Failed to cleanup old status message: {e}")

            # 2. Create new panel
            admin_channel_id = self.bot.admin_channel_id
            if not admin_channel_id:
                log.error("[Status] No admin_channel_id configured. Cannot create status panel.")
                return

            try:
                channel = self.bot.get_channel(int(admin_channel_id))
                if not channel:
                    channel = await self.bot.fetch_channel(int(admin_channel_id))

                if channel:
                    manager_stats, bots_stats = await self.get_status_data_async()
                    layout = ModernStatusView(
                        self.bot, self.bot.i18n, manager_stats, bots_stats, current_page=self.current_page
                    )
                    new_msg = await channel.send(view=layout)

                    self.status_message_id = str(new_msg.id)
                    self.status_channel_id = str(channel.id)

                    self.bot.state_repo.set("status_message_id", self.status_message_id)
                    self.bot.state_repo.set("status_channel_id", self.status_channel_id)

                    log.info(f"[Status] New status panel created: {self.status_message_id} in {self.status_channel_id}")
            except Exception as e:
                log.error(f"[Status] Failed to create new status panel: {e}", exc_info=True)

    async def get_status_data_async(self):
        """Asynchronously gathers system and managed bot statistics via TelemetryService without blocking the event loop."""
        telemetry = getattr(self.bot, "telemetry_service", None)
        if not telemetry:
            return {}, {}
        get_snapshot_async = getattr(telemetry, "get_status_snapshot_async", None)
        if callable(get_snapshot_async) and (
            inspect.iscoroutinefunction(get_snapshot_async) or getattr(get_snapshot_async, "_is_coroutine", False)
        ):
            res = get_snapshot_async(self.git_behind_status)
            if inspect.isawaitable(res):
                return await res
        get_snapshot = getattr(telemetry, "get_status_snapshot", None)
        if callable(get_snapshot):
            return await asyncio.to_thread(get_snapshot, self.git_behind_status)
        return {}, {}

    def get_status_data(self):
        """Gathers system and managed bot statistics via TelemetryService (synchronous fallback)."""
        telemetry = getattr(self.bot, "telemetry_service", None)
        if not telemetry:
            return {}, {}
        return telemetry.get_status_snapshot(self.git_behind_status)

    @tasks.loop(seconds=60)
    async def update_status_task(self):
        """Periodically refreshes the status panel message."""
        if not self.status_channel_id or not self.status_message_id:
            return

        try:
            channel = self.bot.get_channel(int(self.status_channel_id))
            if not channel:
                channel = await self.bot.fetch_channel(int(self.status_channel_id))

            if channel:
                manager_stats, bots_stats = await self.get_status_data_async()
                layout = ModernStatusView(
                    self.bot, self.bot.i18n, manager_stats, bots_stats, current_page=self.current_page
                )
                if hasattr(channel, "get_partial_message"):
                    partial_msg = channel.get_partial_message(int(self.status_message_id))
                    await partial_msg.edit(view=layout)
                else:
                    msg = await channel.fetch_message(int(self.status_message_id))
                    if msg:
                        await msg.edit(view=layout)
        except discord.NotFound:
            log.warning("[Status] Status message lost. Recreating...")
            await self.cleanup_and_recreate_panel(triggered_by_id=self.status_message_id)
        except Exception as e:
            log.error(f"[Status] Error updating status panel: {e}")

    @tasks.loop(minutes=58)
    async def recreate_status_task(self):
        """Periodically recreates the status panel to avoid Discord stale message limits and checks child log sizes."""
        log.info("[Status] Periodic recreation of status panel triggered.")
        log_rotator = getattr(self.bot, "log_rotator", None)
        if log_rotator:
            await asyncio.to_thread(log_rotator.rotate_all_bots, self.bot.bots, force=False)

        await self.cleanup_and_recreate_panel()

    def refresh_descriptions(self, guild):
        """Updates slash command descriptions with guild-specific terms."""
        for cmd in self.get_app_commands():
            if hasattr(cmd, "_raw_desc"):
                cmd.description = format_desc(self.bot, cmd._raw_desc, guild)

    @app_commands.command(
        name="info", description="General information about FixItFixa. (Public option for Admins only)"
    )
    @app_commands.describe(public="Set to True to show the info card to everyone (Admin only).")
    async def info(self, interaction: discord.Interaction, public: bool = False):
        if public:
            level = get_user_level(interaction.user, self.bot)
            if level < AccessLevel.MECHANIC:
                public = False

        view = ModernInfoView(self.bot, self.bot.i18n, interaction.guild)
        await interaction.response.send_message(view=view, ephemeral=not public)

    @app_commands.command(
        name="status",
        description="Bot status snapshot. Anyone can request a private report; admins refresh the Workshop.",
    )
    async def status(self, interaction: discord.Interaction):
        log.info(f"User {interaction.user} requested /status snapshot.")
        level = get_user_level(interaction.user, self.bot)
        is_admin_channel = str(interaction.channel_id) == str(self.bot.admin_channel_id)
        is_mechanic = level >= AccessLevel.MECHANIC
        do_refresh = is_admin_channel and is_mechanic

        await interaction.response.defer(ephemeral=True)
        await self.git_fetch_task()

        if do_refresh:
            await self.cleanup_and_recreate_panel()
            await interaction.followup.send(get_feedback(self.bot.i18n, "status_refreshed"), ephemeral=True)
        else:
            manager_stats, bots_stats = await self.get_status_data_async()
            layout = ModernStatusView(
                self.bot, self.bot.i18n, manager_stats, bots_stats, current_page=self.current_page
            )
            await interaction.followup.send(view=layout, ephemeral=True)


async def setup(bot):
    await bot.add_cog(MonitoringCog(bot))
