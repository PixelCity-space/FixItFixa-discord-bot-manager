import discord
from discord import app_commands
from discord.ext import commands

from core.common.enums import AccessLevel


async def is_bot_owner(user: discord.Member | discord.User, bot: commands.Bot) -> bool:
    """Asynchronously checks if a user is the Discord application bot owner."""
    owner_id = getattr(bot, "owner_id", None)
    owner_ids = getattr(bot, "owner_ids", None)
    if (owner_id and user.id == owner_id) or (owner_ids and user.id in owner_ids):
        return True
    if hasattr(bot, "is_owner") and callable(bot.is_owner):
        try:
            return await bot.is_owner(user)
        except Exception:
            return False
    return False


def get_user_level(user: discord.Member | discord.User, bot: commands.Bot) -> AccessLevel:
    """Determines the AccessLevel for a Discord user."""
    # 1. Discord Bot Application Owner is always BOSS (in guilds and in DMs)
    owner_id = getattr(bot, "owner_id", None)
    owner_ids = getattr(bot, "owner_ids", None)
    if (owner_id and user.id == owner_id) or (owner_ids and user.id in owner_ids):
        return AccessLevel.BOSS

    # 2. Server Owner or Administrator is BOSS
    if isinstance(user, discord.Member) and user.guild and user.id == user.guild.owner_id:
        return AccessLevel.BOSS
    if getattr(user, "guild_permissions", None) and user.guild_permissions.administrator:
        return AccessLevel.BOSS

    # 3. Check roles from access_control configuration
    if isinstance(user, discord.Member):
        access_cfg = getattr(bot, "access_control", {})
        roles_cfg = access_cfg.get("roles", {}) if isinstance(access_cfg, dict) else getattr(access_cfg, "roles", {})

        admin_role_id = roles_cfg.get("admin")
        tester_role_id = roles_cfg.get("tester")

        user_role_ids = [str(r.id) for r in user.roles]

        if admin_role_id and str(admin_role_id) in user_role_ids:
            return AccessLevel.MECHANIC

        if tester_role_id and str(tester_role_id) in user_role_ids:
            return AccessLevel.INSPECTOR

    return AccessLevel.USER


def is_admin_context():
    """Slash check: User must be in admin channel or have MECHANIC/BOSS permissions."""

    async def predicate(interaction: discord.Interaction) -> bool:
        bot = interaction.client
        level = get_user_level(interaction.user, bot)
        if level >= AccessLevel.BOSS:
            return True

        admin_channel_id = getattr(bot, "admin_channel_id", None)
        is_admin_channel = admin_channel_id and str(interaction.channel_id) == str(admin_channel_id)

        return bool(is_admin_channel and level >= AccessLevel.MECHANIC)

    check = app_commands.check(predicate)
    check.predicate = predicate
    return check


def is_monitor_context():
    """Slash check: User must be in admin channel or have at least INSPECTOR permissions."""

    async def predicate(interaction: discord.Interaction) -> bool:
        bot = interaction.client
        level = get_user_level(interaction.user, bot)
        if level >= AccessLevel.BOSS:
            return True

        admin_channel_id = getattr(bot, "admin_channel_id", None)
        is_admin_channel = admin_channel_id and str(interaction.channel_id) == str(admin_channel_id)

        return bool(is_admin_channel and level >= AccessLevel.INSPECTOR)

    check = app_commands.check(predicate)
    check.predicate = predicate
    return check


def is_admin_prefix_context():
    """Prefix command check: User must be in admin channel and have MECHANIC/BOSS permissions."""

    async def predicate(ctx: commands.Context) -> bool:
        bot = ctx.bot
        level = get_user_level(ctx.author, bot)
        if level >= AccessLevel.BOSS:
            return True

        admin_channel_id = getattr(bot, "admin_channel_id", None)
        is_admin_channel = admin_channel_id and str(ctx.channel.id) == str(admin_channel_id)

        return bool(is_admin_channel and level >= AccessLevel.MECHANIC)

    return commands.check(predicate)
