import os
import asyncio
import datetime
import psutil
import discord
from discord import app_commands
from discord.ext import commands, tasks

from core.logger import log, reconfigure_log
from core.icons import Icons
from core.utils import get_feedback
from core.config.config_repository import ConfigRepository
from core.config.state_repository import StateRepository
from core.services.i18n_service import LocalizationService
from core.system.process_spawner import ProcessSpawner
from core.system.process_tracker import ProcessTracker
from core.system.metrics_collector import MetricsCollector
from core.system.git_client import GitClient
from core.system.log_rotator import LogRotator
from core.services.bot_lifecycle_service import BotLifecycleService
from core.services.update_service import UpdateService
from core.services.health_service import HealthService
from core.services.telemetry_service import TelemetryService

class BotManager(commands.Bot):
    """Clean BotManager class responsible for Discord lifecycle, presence, and extension loading."""
    def __init__(self, base_dir: str = None):
        self.base_dir = os.path.abspath(base_dir) if base_dir else os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        config_path = os.path.join(self.base_dir, "config.json")
        state_path = os.path.join(self.base_dir, "state.json")

        # 1. Load Configuration & State Repositories
        self.config_repo = ConfigRepository(config_path)
        self.state_repo = StateRepository(state_path)
        self.app_cfg = self.config_repo.app_config

        self.config = self.config_repo.raw
        self.state = self.state_repo.raw
        self.bots = self.app_cfg.bots

        bot_settings = self.app_cfg.bot_settings

        # 2. Reconfigure logger
        log_file = bot_settings.manager_log_file
        max_bytes = bot_settings.log_max_bytes
        backup_count = bot_settings.log_backup_count
        reconfigure_log(log_file, max_bytes, backup_count)

        log.info(f"[BotManager] Initialized with config from: {config_path}")

        # 3. Setup Icons & Localization
        Icons.setup(self.config.get("bot_settings", {}))
        self.language = bot_settings.language
        self.i18n = LocalizationService(self.language)

        self.ui_settings = self.app_cfg.ui_settings
        self.start_time = datetime.datetime.now()
        self.activity_index = 0
        self.last_net_io = psutil.net_io_counters()
        self.last_net_time = datetime.datetime.now()

        # 4. Initialize Core Infrastructure & Services
        self.log_rotator = LogRotator(bot_settings.bot_log_max_bytes, bot_settings.bot_log_backup_count)
        self.spawner = ProcessSpawner(bot_settings.stop_timeout, bot_settings.restart_wait, log_rotator=self.log_rotator)
        self.tracker = ProcessTracker()
        self.metrics_collector = MetricsCollector()
        self.git_client = GitClient(bot_settings.requirements_file, bot_settings.rollback_ref)

        self.lifecycle_service = BotLifecycleService(
            config=self.app_cfg,
            spawner=self.spawner,
            tracker=self.tracker,
            notify_callback=self.notify_admin
        )
        self.update_service = UpdateService(
            config=self.app_cfg,
            git_client=self.git_client,
            lifecycle_service=self.lifecycle_service,
            manager_root=self.base_dir
        )
        self.health_service = HealthService(
            config=self.app_cfg,
            tracker=self.tracker,
            spawner=self.spawner,
            alert_callback=self._handle_bot_crash
        )
        self.telemetry_service = TelemetryService(
            config=self.app_cfg,
            tracker=self.tracker,
            metrics_collector=self.metrics_collector,
            i18n=self.i18n,
            start_time=self.start_time
        )

        # 5. Access Control
        self.guild_id = self.app_cfg.guild_id
        self.access_control = self.app_cfg.access_control
        self.admin_channel_id = self.app_cfg.access_control.admin_channel_id
        self.public_channel_id = self.app_cfg.access_control.public_channel_id
        self.admin_role_id = self.app_cfg.access_control.admin_role_id
        self.tester_role_id = self.app_cfg.access_control.tester_role_id

        self.check_interval = bot_settings.check_interval_seconds
        self.git_branch = bot_settings.git_branch
        self.command_prefix = bot_settings.command_prefix
        self.command_suffix = bot_settings.command_suffix

        # 6. Discord Intents & Base Init
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(command_prefix=self.command_prefix, intents=intents)

    def save_state(self, key, value):
        """Saves a key-value pair to runtime state."""
        self.state_repo.set(key, value)

    def save_config(self, config):
        """Saves configuration changes."""
        self.config_repo.save(config)
        self.config = self.config_repo.raw
        self.app_cfg = self.config_repo.app_config
        self.bots = self.app_cfg.bots

    @property
    def manager_name(self):
        """Returns the dynamic display name of the bot manager."""
        if self.guild_id and self.guilds:
            guild = self.get_guild(int(self.guild_id))
            if guild and guild.me:
                return guild.me.display_name
        return self.user.name if self.user else get_feedback(self.i18n, "default_manager_name")

    async def _handle_bot_crash(self, bot_id: str, bot_cfg):
        """Callback triggered when a bot terminates unexpectedly."""
        alert_msg = get_feedback(self.i18n, "bot_stopped_alert", name=bot_cfg.name, id=bot_id)
        await self.notify_admin(alert_msg)

    async def notify_admin(self, msg):
        """Sends a message to the designated administrative Discord channel."""
        if self.admin_channel_id:
            channel = self.get_channel(int(self.admin_channel_id))
            if not channel:
                try:
                    channel = await self.fetch_channel(int(self.admin_channel_id))
                except Exception:
                    pass
            if channel:
                await channel.send(msg)

    @tasks.loop(seconds=30)
    async def update_activity_task(self):
        """Cycles dynamic mechanic-themed activity presences."""
        try:
            activities = [
                "activity_maintenance",
                "activity_resource",
                "activity_network",
                "activity_status"
            ]
            key = activities[self.activity_index % len(activities)]
            self.activity_index += 1

            kwargs = {}
            if key == "activity_maintenance":
                kwargs["count"] = len(self.bots)
            elif key == "activity_resource":
                kwargs["cpu"] = int(psutil.cpu_percent())
                kwargs["ram"] = int(psutil.virtual_memory().used / (1024 * 1024))
            elif key == "activity_network":
                now = datetime.datetime.now()
                io = psutil.net_io_counters()
                dt = (now - self.last_net_time).total_seconds()
                if dt > 0:
                    down = (io.bytes_recv - self.last_net_io.bytes_recv) / dt
                    up = (io.bytes_sent - self.last_net_io.bytes_sent) / dt
                    def format_bytes(b):
                        for unit in ['B/s', 'KB/s', 'MB/s']:
                            if b < 1024:
                                return f"{b:.1f} {unit}"
                            b /= 1024
                        return f"{b:.1f} GB/s"
                    kwargs["down"] = format_bytes(down)
                    kwargs["up"] = format_bytes(up)
                else:
                    kwargs["down"] = "0 B/s"
                    kwargs["up"] = "0 B/s"
                self.last_net_io = io
                self.last_net_time = now

            activity_text = get_feedback(self.i18n, key, **kwargs)
            if len(activity_text) > 120:
                activity_text = activity_text[:117] + "..."

            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=activity_text
                )
            )
        except Exception as e:
            log.error(f"[Activity] Error updating presence: {e}")

    @update_activity_task.before_loop
    async def before_update_activity_task(self):
        await self.wait_until_ready()

    async def setup_hook(self):
        """Runs immediately after connecting to Discord."""
        # 1. Load extension Cogs (support bot.cogs and cogs/)
        loaded_extensions = set()
        for ext in ["bot.cogs.management_cog", "bot.cogs.monitoring_cog", "bot.cogs.system_cog"]:
            try:
                await self.load_extension(ext)
                loaded_extensions.add(ext)
                log.info(f"[BotManager] Loaded modular extension: {ext}")
            except Exception as e:
                log.error(f"[BotManager] Failed to load {ext}: {e}")

        # Fallback to cogs/ if not using bot.cogs
        if not loaded_extensions:
            cogs_dir = os.path.join(self.base_dir, "cogs")
            if os.path.exists(cogs_dir):
                for filename in os.listdir(cogs_dir):
                    if filename.endswith(".py") and not filename.startswith("__"):
                        try:
                            await self.load_extension(f"cogs.{filename[:-3]}")
                            log.info(f"[BotManager] Loaded legacy extension: {filename}")
                        except Exception as e:
                            log.error(f"[BotManager] Failed to load extension {filename}: {e}")

        log.info(f"[BotManager] Total commands in tree: {len(self.tree.get_commands())}")

        # 2. Setup Async Icons
        await Icons.setup_async(self)

        # 3. Discover running processes
        self.tracker.discover_processes(self.bots)

        # 4. Start Heartbeat check loop
        self.check_processes.change_interval(seconds=self.check_interval)
        self.check_processes.start()

        # Global slash command error handler
        @self.tree.error
        async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            if isinstance(error, app_commands.CheckFailure):
                msg = get_feedback(self.i18n, "error_admin_context")
                if not interaction.response.is_done():
                    await interaction.response.send_message(msg, ephemeral=True)
                else:
                    await interaction.followup.send(msg, ephemeral=True)
                return

            log.error(f"[BotManager] Slash command error: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message(get_feedback(self.i18n, "error_command_failed", error=str(error)), ephemeral=True)

    async def cleanup_status_panel(self) -> None:
        """Deletes previous status panel message before manager restart."""
        try:
            monitor = self.get_cog('MonitoringCog')
            if monitor and getattr(monitor, 'status_message_id', None) and getattr(monitor, 'status_channel_id', None):
                channel = self.get_channel(int(monitor.status_channel_id))
                if not channel:
                    channel = await self.fetch_channel(int(monitor.status_channel_id))
                if channel:
                    try:
                        old_msg = await channel.fetch_message(int(monitor.status_message_id))
                        await old_msg.delete()
                    except discord.NotFound:
                        pass
        except Exception as e:
            log.warning(f"[BotManager] Failed to delete panel before restart: {e}")

    async def on_interaction(self, interaction: discord.Interaction):
        """Persistent button interaction handler."""
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            if custom_id.startswith("status:"):
                parts = custom_id.split(":")
                if len(parts) >= 3:
                    bot_id = parts[1]
                    action = parts[2]
                    from bot.ui.components.buttons import handle_status_interaction
                    await handle_status_interaction(interaction, bot_id, action)
                    return

        await super().on_interaction(interaction)

    async def on_ready(self):
        """Runs once when the Discord client is fully ready."""
        log.info(f"[BotManager] on_ready received. Logged in as: {self.user} (ID: {self.user.id if self.user else 'None'})")
        await Icons.setup_async(self)
        await asyncio.sleep(2)

        if not self.update_activity_task.is_running():
            self.update_activity_task.start()

        temp_dir = self.config.get("bot_settings", {}).get("temp_dir", "tmp")
        restart_info_path = os.path.join(self.base_dir, temp_dir, "manager_restart.json")
        is_restart = os.path.exists(restart_info_path)

        try:
            msg = get_feedback(self.i18n, "manager_online_log", name=self.manager_name, pid=os.getpid())
            await self.notify_admin(msg)
            if is_restart and os.path.exists(restart_info_path):
                os.remove(restart_info_path)
                log.info("[BotManager] Restart marker cleaned up.")
        except Exception as e:
            log.error(f"[BotManager] Failed to send startup notification: {e}")

    async def on_message(self, message):
        if message.author.bot:
            return
        log.info(f"[Message] From {message.author} in #{message.channel}: {message.content}")
        await self.process_commands(message)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            log.warning(f"[Prefix] Unrecognized command: {ctx.message.content} from {ctx.author}")
            return
        if isinstance(error, commands.CheckFailure):
            log.warning(f"[Prefix] Check failed for user {ctx.author}: {error}")
            msg = get_feedback(self.i18n, "error_admin_context")
            await ctx.send(msg)
            return

        log.error(f"[Prefix] Error in command {ctx.command}: {error}")
        try:
            msg = get_feedback(self.i18n, "error_command_failed", error=str(error))
            await ctx.send(msg)
        except Exception:
            pass

    @tasks.loop(seconds=60)
    async def check_processes(self):
        """Heartbeat check loop for unexpected bot termination."""
        log.info("[BotManager] Heartbeat: Checking processes...")
        await self.health_service.check_health()
