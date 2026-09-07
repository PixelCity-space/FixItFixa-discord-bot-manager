import asyncio

import discord

from bot.checks import AccessLevel, get_user_level
from bot.ui.embeds.update_result import UpdateResultEmbed
from core.common.constants import (
    DISCORD_TRUNCATE_OUTPUT_HEAD,
    DISCORD_TRUNCATE_OUTPUT_LIMIT,
    DISCORD_TRUNCATE_OUTPUT_TAIL,
    truncate_message,
)
from core.common.rate_limiter import InteractionRateLimiter
from core.icons import Icons
from core.logger import log
from core.utils import get_feedback

_status_button_rate_limiter = InteractionRateLimiter(default_cooldown=3.0)


class BotControlButton(discord.ui.Button):
    """Button for controlling child bots and manager self-actions."""

    def __init__(
        self, style=discord.ButtonStyle.secondary, emoji=None, bot_id=None, bot_name=None, action=None, view=None
    ):
        cid = f"status:{bot_id}:{action}"
        super().__init__(style=style, label=None, emoji=emoji, custom_id=cid)
        self.bot_id = bot_id
        self.bot_name = bot_name
        self.action = action
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
        await handle_status_interaction(interaction, self.bot_id, self.action, self.bot_name)


class PageButton(discord.ui.Button):
    """Button for navigating paginated status pages."""

    def __init__(self, direction: int, cog=None, current_page: int = 0, total_pages: int = 1, i18n=None):
        self.direction = direction  # -1 for prev, 1 for next
        self.cog = cog
        emoji = Icons.CARET_LEFT if direction == -1 else Icons.CARET_RIGHT
        disabled = (direction == -1 and current_page == 0) or (direction == 1 and current_page >= total_pages - 1)
        cid = f"status:page:{'next' if direction > 0 else 'prev'}"
        super().__init__(style=discord.ButtonStyle.secondary, label=None, emoji=emoji, custom_id=cid, disabled=disabled)

    async def callback(self, interaction: discord.Interaction):
        bot = interaction.client or (getattr(self.cog, "bot", None) if self.cog else None)
        i18n = getattr(bot, "i18n", None) if bot else getattr(self, "i18n", None)

        # 1. Rate Limiting Check (0.5s cooldown)
        if interaction.user:
            is_limited, _ = _status_button_rate_limiter.is_limited(interaction.user.id, "page_nav", cooldown=0.5)
            if is_limited:
                return

        # 2. Permission Check (At least INSPECTOR or in admin channel or BOSS)
        if bot and interaction.user:
            level = get_user_level(interaction.user, bot)
            admin_ch = getattr(bot, "admin_channel_id", None)
            is_admin_channel = admin_ch and str(interaction.channel_id) == str(admin_ch)
            if level < AccessLevel.INSPECTOR and not is_admin_channel:
                is_done = (
                    interaction.response.is_done()
                    if hasattr(interaction.response, "is_done") and callable(interaction.response.is_done)
                    else False
                )
                if is_done is not True:
                    await interaction.response.send_message(get_feedback(i18n, "error_inspector_only"), ephemeral=True)
                return

        # 3. Immediate acknowledgment to prevent Discord 3s timeout
        is_done = (
            interaction.response.is_done()
            if hasattr(interaction.response, "is_done") and callable(interaction.response.is_done)
            else False
        )
        if is_done is not True:
            await interaction.response.defer()

        # 4. Delegate cleanly to MonitoringCog method
        if self.cog:
            change_fn = getattr(self.cog, "change_page", None)
            if callable(change_fn):
                res = change_fn(self.direction)
                if asyncio.iscoroutine(res):
                    await res
                elif hasattr(self.cog, "current_page"):
                    self.cog.current_page += self.direction
                    update_fn = getattr(self.cog, "update_status_task", None)
                    if callable(update_fn):
                        res_u = update_fn()
                        if asyncio.iscoroutine(res_u):
                            await res_u
            else:
                self.cog.current_page += self.direction
                update_fn = getattr(self.cog, "update_status_task", None)
                if callable(update_fn):
                    res = update_fn()
                    if asyncio.iscoroutine(res):
                        await res
        elif interaction.client:
            monitor = interaction.client.get_cog("MonitoringCog")
            if monitor and hasattr(monitor, "change_page"):
                await monitor.change_page(self.direction)


async def handle_status_interaction(interaction: discord.Interaction, bot_id: str, action: str, bot_name: str = None):
    """Core router for status panel button interactions."""
    bot = interaction.client
    i18n = getattr(bot, "i18n", None)

    # === SPECIAL HANDLING FOR STATUS PAGINATION ===
    if bot_id == "page":
        # 1. Rate Limiting (0.5s cooldown)
        is_limited, _ = _status_button_rate_limiter.is_limited(interaction.user.id, "page_nav", cooldown=0.5)
        if is_limited:
            return

        # 2. Permission Check
        level = get_user_level(interaction.user, bot)
        admin_ch = getattr(bot, "admin_channel_id", None)
        is_admin_channel = admin_ch and str(interaction.channel_id) == str(admin_ch)
        if level < AccessLevel.INSPECTOR and not is_admin_channel:
            is_done = (
                interaction.response.is_done()
                if hasattr(interaction.response, "is_done") and callable(interaction.response.is_done)
                else False
            )
            if is_done is not True:
                await interaction.response.send_message(get_feedback(i18n, "error_inspector_only"), ephemeral=True)
            return

        is_done = (
            interaction.response.is_done()
            if hasattr(interaction.response, "is_done") and callable(interaction.response.is_done)
            else False
        )
        if is_done is not True:
            await interaction.response.defer()
        monitor = bot.get_cog("MonitoringCog")
        if monitor and hasattr(monitor, "change_page"):
            delta = 1 if action == "next" else -1
            await monitor.change_page(delta)
        return

    # 1. Determine User Level
    level = get_user_level(interaction.user, bot)

    # 2. Determine Required Level
    required_level = AccessLevel.MECHANIC
    if action == "restart" or action.endswith("-restart"):
        required_level = AccessLevel.INSPECTOR
    elif action == "stop" or action.endswith("-stop") or action == "update" or action.endswith("-update"):
        required_level = AccessLevel.MECHANIC

    # 3. Check Level Permissions
    if level < required_level:
        msg = (
            get_feedback(i18n, "error_admin_only")
            if level < AccessLevel.INSPECTOR
            else get_feedback(i18n, "error_inspector_only")
        )
        await interaction.response.send_message(msg, ephemeral=True)
        return

    # 3.5 Check Rate Limiting
    is_limited, remaining = _status_button_rate_limiter.is_limited(
        interaction.user.id, f"{bot_id}:{action}", cooldown=3.0
    )
    if is_limited:
        limit_msg = get_feedback(i18n, "rate_limit_alert", seconds=remaining)
        await interaction.response.send_message(limit_msg, ephemeral=True)
        return

    # 4. Context (Channel) check
    admin_ch = getattr(bot, "admin_channel_id", None)
    is_admin_channel = admin_ch and str(interaction.channel_id) == str(admin_ch)
    if level < AccessLevel.BOSS and not is_admin_channel:
        await interaction.response.send_message(get_feedback(i18n, "error_admin_channel_only"), ephemeral=True)
        return

    await interaction.response.defer(ephemeral=not is_admin_channel)

    # Resolve bot name
    if not bot_name:
        if bot_id == "manager":
            bot_name = getattr(bot, "manager_name", "Bot Manager")
        elif hasattr(bot, "bots") and bot_id in bot.bots:
            bot_name = bot.bots[bot_id].name
        else:
            bot_name = bot_id

    # Reference services
    update_service = getattr(bot, "update_service", None)
    lifecycle_service = getattr(bot, "lifecycle_service", None)

    # === SPECIAL HANDLING FOR MANAGER SELF-CONTROLS ===
    if bot_id == "manager":
        if action == "restart":
            log.info(f"User {interaction.user} clicked SELF-RESTART for Manager")
            update_service.prepare_manager_restart()

            await interaction.followup.send(get_feedback(i18n, "status_restarting"), ephemeral=False)
            await asyncio.sleep(2)
            await bot.cleanup_status_panel()
            bot.spawner.execute_manager_restart()
            return

        elif action == "stop":
            log.info(f"User {interaction.user} clicked SELF-STOP for Manager")
            await interaction.followup.send(get_feedback(i18n, "status_stopping"), ephemeral=False)
            await asyncio.sleep(1)
            bot.spawner.execute_manager_shutdown()
            return

        elif action == "update":
            log.info(f"User {interaction.user} clicked SELF-UPDATE for Manager")
            updating_msg = get_feedback(i18n, "manager_updating", name="Manager")
            await interaction.followup.send(updating_msg, ephemeral=False)

            success, output, changed, details = await update_service.update_manager()

            if not success:
                output = truncate_message(
                    output,
                    max_len=DISCORD_TRUNCATE_OUTPUT_LIMIT,
                    head_len=DISCORD_TRUNCATE_OUTPUT_HEAD,
                    tail_len=DISCORD_TRUNCATE_OUTPUT_TAIL,
                )
                msg = get_feedback(i18n, "error_update_failed_output", output=output)
                await interaction.followup.send(msg, ephemeral=False)
                return

            if not changed:
                await interaction.followup.send(get_feedback(i18n, "update_no_changes"), ephemeral=False)
                return

            update_service.prepare_manager_restart()

            if details:
                title = get_feedback(i18n, "update_result_title", name="Manager")
                embed = UpdateResultEmbed(i18n, title, details, ui_settings=getattr(bot, "ui_settings", None))
                await interaction.followup.send(embed=embed, ephemeral=False)
            else:
                msg = get_feedback(i18n, "manager_update_success", name="Manager", output=output)
                msg = truncate_message(msg)
                await interaction.followup.send(msg, ephemeral=False)

            await asyncio.sleep(2)
            await bot.cleanup_status_panel()
            bot.spawner.execute_manager_restart()
            return

    # === STANDARD BOT CONTROLS ===
    result = ""
    if action == "restart":
        log.info(f"User {interaction.user} clicked RESTART for {bot_name} ({bot_id})")
        restarts = await lifecycle_service.restart_bot_cluster(bot_id)
        msgs = []
        for b_cfg, pid, err in restarts:
            if err or not pid:
                msgs.append(get_feedback(i18n, "restart_error", name=b_cfg.name, error=err or "Unknown error"))
            else:
                msgs.append(get_feedback(i18n, "restart_success", name=b_cfg.name, pid=pid))
                await bot.notify_admin(get_feedback(i18n, "bot_online_log", name=b_cfg.name, id=b_cfg.id, pid=pid))
        result = "\n".join(msgs)

    elif action == "stop":
        log.info(f"User {interaction.user} clicked STOP for {bot_name} ({bot_id})")
        stop_res = await lifecycle_service.stop_bot(bot_id)
        if isinstance(stop_res, tuple):
            success, err = stop_res
        else:
            success, err = bool(stop_res), None

        if success:
            result = get_feedback(i18n, "stop_success", name=bot_name)
        else:
            result = get_feedback(i18n, "stop_error", name=bot_name, error=err or "Unknown error")

    elif action == "update":
        log.info(f"User {interaction.user} clicked UPDATE for {bot_name} ({bot_id})")
        success, result_msg, changed, details, restarts = await update_service.update_bot(bot_id)

        if details:
            monitor = bot.get_cog("MonitoringCog")
            if monitor:
                updated_path = bot.bots[bot_id].path if bot_id in bot.bots else None
                monitor.git_behind_status[bot_id] = False
                if updated_path:
                    for bid, bcfg in bot.bots.items():
                        if bcfg.path == updated_path:
                            monitor.git_behind_status[bid] = False

            title = get_feedback(i18n, "update_result_title", name=bot_name)
            embed = UpdateResultEmbed(i18n, title, details)
            await interaction.followup.send(embed=embed, ephemeral=False)
            return
        else:
            result = result_msg

    result = truncate_message(result)
    await interaction.followup.send(result, ephemeral=False)
