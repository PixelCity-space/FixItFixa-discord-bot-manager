import discord
from discord import app_commands
from discord.ext import commands
from core.logger import log
from core.utils import get_feedback
from bot.checks import is_admin_context, is_admin_prefix_context, is_monitor_context, get_user_level, AccessLevel

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
    async def clear_commands_prefix(self, ctx: commands.Context):
        """[Admin] Emergency clear of all slash commands."""
        log.info(f"[Clear] User {ctx.author} requested slash command purge.")
        await ctx.send(get_feedback(self.bot.i18n, "clear_commands_in_progress"))

        self.bot.tree.clear_commands(guild=None)
        await self.bot.tree.sync(guild=None)
        self.bot.tree.clear_commands(guild=ctx.guild)
        await self.bot.tree.sync(guild=ctx.guild)

        log.info("[Clear] Slash commands cleared successfully.")
        await ctx.send(get_feedback(self.bot.i18n, "clear_commands_success"))

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
        await interaction.response.defer(ephemeral=True)

        level = get_user_level(interaction.user, self.bot)
        if level < AccessLevel.MECHANIC:
            await interaction.followup.send(get_feedback(self.bot.i18n, "error_inspector_only"), ephemeral=True)
            return

        try:
            bot_settings = self.bot.app_cfg.bot_settings
            purge_limit = bot_settings.purge_limit
            deleted = await interaction.channel.purge(limit=purge_limit)

            count = len(deleted)
            msg = get_feedback(self.bot.i18n, "purge_success", count=count)
            await interaction.followup.send(msg, ephemeral=True)
            log.info(f"User {interaction.user} purged {count} messages in channel {interaction.channel.name}")
        except discord.Forbidden:
            msg = get_feedback(self.bot.i18n, "purge_error", error="Forbidden")
            await interaction.followup.send(msg, ephemeral=True)
        except Exception as e:
            log.error(f"Error during purge: {e}")
            msg = get_feedback(self.bot.i18n, "purge_error", error=str(e))
            await interaction.followup.send(msg, ephemeral=True)

async def setup(bot):
    cog = SystemCog(bot)
    suffix = getattr(bot, 'command_suffix', '')
    if suffix:
        cog.sync_prefix.aliases = [f"sync{suffix}"]
        cog.clear_commands_prefix.aliases = [f"clear_commands{suffix}"]
        cog.ping_prefix.aliases = [f"ping{suffix}"]
        log.info(f"[SystemCog] Dynamic aliases prepared for suffix: {suffix}")

    await bot.add_cog(cog)
