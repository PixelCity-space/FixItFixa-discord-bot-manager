import discord
from discord import app_commands
from discord.ext import commands

from bot.checks import (
    AccessLevel,
    get_user_level,
    is_admin_context,
    is_admin_prefix_context,
    is_bot_owner,
    is_monitor_context,
)
from core.icons import Icons
from core.logger import log
from core.utils import get_feedback


class ConfirmPurgeView(discord.ui.View):
    """Confirmation dialog view for destructive message purge operations."""

    def __init__(
        self,
        author_id: int,
        bot,
        channel: discord.TextChannel | discord.abc.Messageable,
        i18n=None,
        timeout: float = 30.0,
    ):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.bot = bot
        self.channel = channel
        self.i18n = i18n
        self.confirmed = False

        self.confirm_button.label = get_feedback(self.i18n, "btn_confirm")
        self.cancel_button.label = get_feedback(self.i18n, "btn_cancel")

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger, emoji=Icons.STOP)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(get_feedback(self.i18n, "error_inspector_only"), ephemeral=True)
            return
        self.confirmed = True
        self.stop()
        await interaction.response.defer(ephemeral=True)
        try:
            bot_settings = getattr(self.bot, "app_cfg", None)
            purge_limit = (
                bot_settings.bot_settings.purge_limit if bot_settings and hasattr(bot_settings, "bot_settings") else 100
            )
            deleted = await self.channel.purge(limit=purge_limit)
            count = len(deleted)
            msg = get_feedback(self.i18n, "purge_success", count=count)
            await interaction.followup.send(msg, ephemeral=True)
            ch_name = getattr(self.channel, "name", str(self.channel))
            log.info(f"User {interaction.user} purged {count} messages in channel {ch_name}")
        except discord.Forbidden:
            msg = get_feedback(self.i18n, "purge_error", error="Forbidden")
            await interaction.followup.send(msg, ephemeral=True)
        except Exception as e:
            log.error(f"Error during purge: {e}")
            msg = get_feedback(self.i18n, "purge_error", error=str(e))
            await interaction.followup.send(msg, ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(get_feedback(self.i18n, "error_inspector_only"), ephemeral=True)
            return
        self.confirmed = False
        self.stop()
        await interaction.response.send_message(get_feedback(self.i18n, "purge_cancelled"), ephemeral=True)


class SystemCog(commands.Cog):
    """System, maintenance, and administrative utility commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping_prefix(self, ctx: commands.Context):
        """[Bot Dev] Simple connectivity check."""
        await ctx.send(get_feedback(self.bot.i18n, "ping_pong", latency=round(self.bot.latency * 1000)))

    @commands.command(name="sync")
    @commands.guild_only()
    @is_admin_prefix_context()
    async def sync_prefix(self, ctx: commands.Context, spec: str | None = None):
        """[Admin] Sync slash commands manually (guild/global/copy)."""
        for cog in ctx.bot.cogs.values():
            if hasattr(cog, "refresh_descriptions"):
                cog.refresh_descriptions(ctx.guild)

        self.bot.i18n.localize_commands(self.bot.tree, guild=None)
        if ctx.guild:
            self.bot.i18n.localize_commands(self.bot.tree, guild=ctx.guild)

        if spec == "global":
            synced = await self.bot.tree.sync()
            msg = get_feedback(self.bot.i18n, "sync_success_global", count=len(synced))
            await ctx.send(msg)
        elif spec == "copy":
            self.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await self.bot.tree.sync(guild=ctx.guild)
            msg = get_feedback(self.bot.i18n, "sync_success_copy", count=len(synced))
            await ctx.send(msg)
        else:
            log.info(f"[Sync] Attempting guild sync for {ctx.guild.id}...")
            await ctx.send(get_feedback(self.bot.i18n, "sync_in_progress"))
            synced = await self.bot.tree.sync(guild=ctx.guild)
            msg = get_feedback(self.bot.i18n, "sync_success_guild", count=len(synced))
            await ctx.send(msg)

    @commands.command(name="clear_commands")
    @commands.guild_only()
    @is_admin_prefix_context()
    async def clear_commands_prefix(self, ctx: commands.Context, spec: str | None = None):
        """[Admin] Emergency clear of slash commands (guild by default, global requires Bot Owner)."""
        if spec == "global":
            owner = await is_bot_owner(ctx.author, self.bot)
            if not owner:
                await ctx.send(get_feedback(self.bot.i18n, "error_owner_only"))
                return

            log.warning(f"[Clear] Bot Owner {ctx.author} requested GLOBAL slash command purge.")
            await ctx.send(get_feedback(self.bot.i18n, "clear_commands_in_progress"))
            self.bot.tree.clear_commands(guild=None)
            await self.bot.tree.sync(guild=None)
            log.info("[Clear] Global slash commands cleared successfully.")
            await ctx.send(get_feedback(self.bot.i18n, "clear_commands_global_success"))
        else:
            log.info(f"[Clear] User {ctx.author} requested guild slash command purge for {ctx.guild.id}.")
            await ctx.send(get_feedback(self.bot.i18n, "clear_commands_in_progress"))
            self.bot.tree.clear_commands(guild=ctx.guild)
            await self.bot.tree.sync(guild=ctx.guild)
            log.info(f"[Clear] Guild slash commands cleared successfully for {ctx.guild.id}.")
            await ctx.send(get_feedback(self.bot.i18n, "clear_commands_guild_success"))

    @app_commands.command(name="sync", description="[Bot Dev] Sync slash commands manually.")
    @app_commands.describe(mode="guild (instant), global (slow), or copy")
    @is_admin_context()
    async def sync_slash(self, interaction: discord.Interaction, mode: str = "guild"):
        for cog in interaction.client.cogs.values():
            if hasattr(cog, "refresh_descriptions"):
                cog.refresh_descriptions(interaction.guild)

        log.info(f"User {interaction.user} requested /sync mode={mode}")
        await interaction.response.defer(ephemeral=True)

        self.bot.i18n.localize_commands(self.bot.tree, guild=interaction.guild if mode != "global" else None)

        if mode == "global":
            synced = await self.bot.tree.sync()
            msg = get_feedback(self.bot.i18n, "sync_success_global", count=len(synced))
            await interaction.followup.send(msg, ephemeral=True)
        elif mode == "copy":
            self.bot.tree.copy_global_to(guild=interaction.guild)
            synced = await self.bot.tree.sync(guild=interaction.guild)
            msg = get_feedback(self.bot.i18n, "sync_success_copy", count=len(synced))
            await interaction.followup.send(msg, ephemeral=True)
        else:
            synced = await self.bot.tree.sync(guild=interaction.guild)
            msg = get_feedback(self.bot.i18n, "sync_success_guild", count=len(synced))
            await interaction.followup.send(msg, ephemeral=True)

    @app_commands.command(name="purge", description="[Bot Dev] Deletes all messages in the current channel.")
    @is_monitor_context()
    async def purge(self, interaction: discord.Interaction):
        level = get_user_level(interaction.user, self.bot)
        if level < AccessLevel.MECHANIC:
            await interaction.response.send_message(get_feedback(self.bot.i18n, "error_inspector_only"), ephemeral=True)
            return

        view = ConfirmPurgeView(
            author_id=interaction.user.id,
            bot=self.bot,
            channel=interaction.channel,
            i18n=self.bot.i18n,
        )
        await interaction.response.send_message(
            get_feedback(self.bot.i18n, "purge_confirm"),
            view=view,
            ephemeral=True,
        )


async def setup(bot):
    cog = SystemCog(bot)
    suffix = getattr(bot, "command_suffix", "")
    if suffix:
        cog.sync_prefix.aliases = [f"sync{suffix}"]
        cog.clear_commands_prefix.aliases = [f"clear_commands{suffix}"]
        cog.ping_prefix.aliases = [f"ping{suffix}"]
        log.info(f"[SystemCog] Dynamic aliases prepared for suffix: {suffix}")

    await bot.add_cog(cog)
