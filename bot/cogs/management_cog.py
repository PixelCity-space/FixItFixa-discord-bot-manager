import os
import io
import asyncio
from collections import deque
import discord
from discord import app_commands
from discord.ext import commands
from core.logger import log
from core.utils import get_feedback
from core.common.constants import truncate_message
from bot.checks import is_admin_context, is_monitor_context
from bot.autocomplete import bot_id_autocomplete
from bot.ui.embeds.update_result import UpdateResultEmbed

class ManagementCog(commands.Cog):
    """Admin and Dev commands for managing child bots and the manager."""
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="update", description="[Bot Dev] Update and restart a bot by ID.")
    @app_commands.describe(bot_id="The ID of the bot to update")
    @is_admin_context()
    @app_commands.autocomplete(bot_id=bot_id_autocomplete)
    async def update(self, interaction: discord.Interaction, bot_id: str):
        log.info(f"User {interaction.user} requested /update for bot: {bot_id}")
        await interaction.response.defer(ephemeral=False)

        success, result_msg, changed, details, restarts = await self.bot.update_service.update_bot(bot_id)

        if details:
            title = get_feedback(self.bot.i18n, "bot_updated_title")
            embed = UpdateResultEmbed(self.bot.i18n, title, details, ui_settings=self.bot.ui_settings)
            await interaction.followup.send(embed=embed, ephemeral=False)
        else:
            result_msg = truncate_message(result_msg)
            await interaction.followup.send(result_msg, ephemeral=False)

    @app_commands.command(name="restart", description="[Bot Dev] Restart a bot without update.")
    @app_commands.describe(bot_id="The ID of the bot to restart")
    @is_admin_context()
    @app_commands.autocomplete(bot_id=bot_id_autocomplete)
    async def restart(self, interaction: discord.Interaction, bot_id: str):
        log.info(f"User {interaction.user} requested /restart for bot: {bot_id}")
        await interaction.response.defer(ephemeral=False)

        restarts = await self.bot.lifecycle_service.restart_bot_cluster(bot_id)
        msgs = []
        for b_cfg, pid, err in restarts:
            if err:
                msgs.append(get_feedback(self.bot.i18n, "restart_error", name=b_cfg.name, error=err))
            else:
                msgs.append(get_feedback(self.bot.i18n, "restart_success", name=b_cfg.name, pid=pid))
                await self.bot.notify_admin(get_feedback(self.bot.i18n, "bot_online_log", name=b_cfg.name, id=b_cfg.id, pid=pid))
        result = "\n".join(msgs)

        await interaction.followup.send(result, ephemeral=False)

    @app_commands.command(name="rollback", description="[Bot Dev] Rollback bot to previous Git state (HEAD@{1}).")
    @app_commands.describe(bot_id="The ID of the bot to rollback")
    @is_admin_context()
    @app_commands.autocomplete(bot_id=bot_id_autocomplete)
    async def rollback(self, interaction: discord.Interaction, bot_id: str):
        log.info(f"User {interaction.user} requested /rollback for bot: {bot_id}")
        await interaction.response.defer(ephemeral=False)

        success, result_msg, changed, details, restarts = await self.bot.update_service.rollback_bot(bot_id)

        if details:
            title = get_feedback(self.bot.i18n, "bot_rollback_title")
            embed = UpdateResultEmbed(self.bot.i18n, title, details, ui_settings=self.bot.ui_settings, is_rollback=True)
            await interaction.followup.send(embed=embed, ephemeral=False)
        else:
            await interaction.followup.send(result_msg, ephemeral=False)

    @app_commands.command(name="logs", description="[Bot Dev] Get last N lines of a bot log file.")
    @app_commands.describe(bot_id="The ID of the bot", lines="Number of lines")
    @is_monitor_context()
    @app_commands.autocomplete(bot_id=bot_id_autocomplete)
    async def logs(self, interaction: discord.Interaction, bot_id: str, lines: int | None = None):
        bot_settings = self.bot.app_cfg.bot_settings
        default_lines = bot_settings.log_default_lines
        lines = lines if lines is not None else default_lines

        log.info(f"User {interaction.user} requested /logs ({lines} lines) for bot: {bot_id}")
        await interaction.response.defer(ephemeral=False)

        if bot_id not in self.bot.bots:
            await interaction.followup.send(get_feedback(self.bot.i18n, "error_unknown_bot"), ephemeral=True)
            return

        bot = self.bot.bots[bot_id]
        log_name = bot.log if bot.log else bot_settings.bot_log_default
        log_path = os.path.join(bot.path, log_name)

        if os.path.exists(log_path):
            try:
                if lines > 0:
                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                        last_lines = deque(f, maxlen=lines)

                    content = "".join(last_lines)
                    if not content:
                        await interaction.followup.send(get_feedback(self.bot.i18n, "error_log_empty"), ephemeral=True)
                        return

                    buffer = io.BytesIO(content.encode("utf-8"))
                    file = discord.File(buffer, filename=f"{bot.name}_last_{lines}_lines.txt")
                    header = get_feedback(self.bot.i18n, "logs_header", name=bot.name, lines=lines)
                    await interaction.followup.send(header, file=file, ephemeral=False)
                else:
                    file = discord.File(log_path, filename=f"{bot.name}_full_logs.txt")
                    header = get_feedback(self.bot.i18n, "logs_full_header", name=bot.name)
                    await interaction.followup.send(header, file=file, ephemeral=True)
            except Exception as e:
                await interaction.followup.send(get_feedback(self.bot.i18n, "error_log_fetch", error=str(e)), ephemeral=True)
        else:
            await interaction.followup.send(get_feedback(self.bot.i18n, "error_log_not_found", path=log_path), ephemeral=True)

    @app_commands.command(name="manager-logs", description="[Bot Dev] Get last N lines of the Bot Manager log.")
    @app_commands.describe(lines="Number of lines")
    @is_admin_context()
    async def manager_logs(self, interaction: discord.Interaction, lines: int | None = None):
        bot_settings = self.bot.app_cfg.bot_settings
        default_lines = bot_settings.log_default_lines
        lines = lines if lines is not None else default_lines

        log.info(f"User {interaction.user} requested /manager-logs ({lines} lines)")
        await interaction.response.defer(ephemeral=False)

        log_path = bot_settings.manager_log_file

        if os.path.exists(log_path):
            try:
                if lines > 0:
                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                        last_lines = deque(f, maxlen=lines)

                    content = "".join(last_lines)
                    if not content:
                        await interaction.followup.send(get_feedback(self.bot.i18n, "error_manager_log_empty"), ephemeral=True)
                        return

                    buffer = io.BytesIO(content.encode("utf-8"))
                    file = discord.File(buffer, filename=f"manager_last_{lines}_lines.txt")
                    header = get_feedback(self.bot.i18n, "manager_logs_header", lines=lines)
                    await interaction.followup.send(header, file=file, ephemeral=False)
                else:
                    file = discord.File(log_path, filename="manager_full_logs.txt")
                    header = get_feedback(self.bot.i18n, "manager_logs_full_header")
                    await interaction.followup.send(header, file=file, ephemeral=False)
            except Exception as e:
                await interaction.followup.send(get_feedback(self.bot.i18n, "error_log_fetch", error=str(e)), ephemeral=True)
        else:
            await interaction.followup.send(get_feedback(self.bot.i18n, "error_manager_log_not_found"), ephemeral=True)

    @app_commands.command(name="logs-rotate", description="[Bot Dev] Rotate/archive a bot log file.")
    @app_commands.describe(bot_id="The ID of the bot", force="Rotate even if size is below limit")
    @is_admin_context()
    @app_commands.autocomplete(bot_id=bot_id_autocomplete)
    async def logs_rotate(self, interaction: discord.Interaction, bot_id: str, force: bool = False):
        log.info(f"User {interaction.user} requested /logs-rotate for bot: {bot_id} (force={force})")
        await interaction.response.defer(ephemeral=False)

        if bot_id not in self.bot.bots:
            await interaction.followup.send(get_feedback(self.bot.i18n, "error_unknown_bot"), ephemeral=True)
            return

        bot = self.bot.bots[bot_id]
        log_rotator = getattr(self.bot, 'log_rotator', None)
        if not log_rotator:
            from core.system.log_rotator import LogRotator
            log_rotator = LogRotator()

        rotated, msg = log_rotator.rotate_bot_log(bot, force=force)
        if rotated:
            response = get_feedback(self.bot.i18n, "logs_rotate_success", name=bot.name, size=msg)
        else:
            log_path = os.path.join(bot.path, bot.log)
            cur_size = f"{os.path.getsize(log_path) / (1024 * 1024):.2f} MB" if os.path.exists(log_path) else "0 MB"
            max_size = f"{log_rotator.max_bytes / (1024 * 1024):.2f} MB"
            response = get_feedback(self.bot.i18n, "logs_rotate_no_need", name=bot.name, size=cur_size, max_size=max_size)

        await interaction.followup.send(response, ephemeral=False)

    @app_commands.command(name="manager-restart", description="[Bot Dev] Immediate restart of Bot Manager.")
    @is_admin_context()
    async def manager_restart(self, interaction: discord.Interaction):
        log.info(f"User {interaction.user} requested /manager-restart. Restarting {self.bot.manager_name}...")
        msg = get_feedback(self.bot.i18n, "manager_restart_msg", name=self.bot.manager_name, pid=os.getpid())
        await interaction.response.send_message(msg, ephemeral=False)

        self.bot.update_service.prepare_manager_restart()

        await asyncio.sleep(2)
        await self.bot.cleanup_status_panel()
        self.bot.spawner.execute_manager_restart()

    @app_commands.command(name="manager-update", description="[Bot Dev] Git pull, pip install and restart Bot Manager.")
    @is_admin_context()
    async def manager_update(self, interaction: discord.Interaction):
        log.info(f"User {interaction.user} requested /manager-update for {self.bot.manager_name}.")
        await interaction.response.defer(ephemeral=False)

        updating_msg = get_feedback(self.bot.i18n, "manager_updating", name=self.bot.manager_name)
        await interaction.followup.send(updating_msg, ephemeral=False)

        try:
            success, output, changed, details = await self.bot.update_service.update_manager()

            if not success:
                msg = get_feedback(self.bot.i18n, "error_update_failed_output", output=output)
                await interaction.followup.send(msg, ephemeral=True)
                return

            if not changed:
                await interaction.followup.send(get_feedback(self.bot.i18n, "update_no_changes"), ephemeral=False)
                return

            if details:
                title = get_feedback(self.bot.i18n, "manager_updated_title")
                embed = UpdateResultEmbed(self.bot.i18n, title, details, ui_settings=self.bot.ui_settings)
                await interaction.followup.send(embed=embed, ephemeral=False)
            else:
                msg = get_feedback(self.bot.i18n, "manager_update_success", name=self.bot.manager_name, output=output)
                msg = truncate_message(msg)
                await interaction.followup.send(msg, ephemeral=False)

            log.info("Manager updated, restarting process...")
            self.bot.update_service.prepare_manager_restart()

            await asyncio.sleep(2)
            await self.bot.cleanup_status_panel()
            self.bot.spawner.execute_manager_restart()

        except Exception as e:
            log.error(f"Manager update failed: {e}")
            await interaction.followup.send(get_feedback(self.bot.i18n, "error_update_general", error=str(e)), ephemeral=True)

async def setup(bot):
    await bot.add_cog(ManagementCog(bot))
