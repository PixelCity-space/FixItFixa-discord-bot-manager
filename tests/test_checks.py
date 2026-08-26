import discord
from unittest.mock import MagicMock
from core.common.enums import AccessLevel
from bot.checks import get_user_level, is_admin_context, is_monitor_context
import asyncio

def test_access_level_hierarchy():
    assert AccessLevel.BOSS > AccessLevel.MECHANIC
    assert AccessLevel.MECHANIC > AccessLevel.INSPECTOR
    assert AccessLevel.INSPECTOR > AccessLevel.USER

def test_get_user_level_guild_owner():
    user = MagicMock(spec=discord.Member)
    user.guild = MagicMock()
    user.guild.owner_id = 12345
    user.id = 12345
    bot = MagicMock()

    level = get_user_level(user, bot)
    assert level == AccessLevel.BOSS

def test_get_user_level_administrator_permission():
    user = MagicMock(spec=discord.Member)
    user.guild = MagicMock()
    user.guild.owner_id = 99999
    user.id = 12345
    user.guild_permissions = MagicMock()
    user.guild_permissions.administrator = True
    bot = MagicMock()

    level = get_user_level(user, bot)
    assert level == AccessLevel.BOSS

def test_get_user_level_admin_role():
    user = MagicMock(spec=discord.Member)
    user.guild = MagicMock()
    user.guild.owner_id = 99999
    user.id = 11111
    user.guild_permissions = MagicMock()
    user.guild_permissions.administrator = False

    role_admin = MagicMock()
    role_admin.id = 555
    user.roles = [role_admin]

    bot = MagicMock()
    bot.access_control = {"roles": {"admin": 555, "tester": 777}}

    level = get_user_level(user, bot)
    assert level == AccessLevel.MECHANIC

def test_get_user_level_tester_role():
    user = MagicMock(spec=discord.Member)
    user.guild = MagicMock()
    user.guild.owner_id = 99999
    user.id = 11111
    user.guild_permissions = MagicMock()
    user.guild_permissions.administrator = False

    role_tester = MagicMock()
    role_tester.id = 777
    user.roles = [role_tester]

    bot = MagicMock()
    bot.access_control = {"roles": {"admin": 555, "tester": 777}}

    level = get_user_level(user, bot)
    assert level == AccessLevel.INSPECTOR

def test_get_user_level_user():
    user = MagicMock(spec=discord.Member)
    user.guild = MagicMock()
    user.guild.owner_id = 99999
    user.id = 11111
    user.guild_permissions = MagicMock()
    user.guild_permissions.administrator = False
    user.roles = []

    bot = MagicMock()
    bot.access_control = {"roles": {"admin": 555, "tester": 777}}

    level = get_user_level(user, bot)
    assert level == AccessLevel.USER

def test_is_admin_context_check():
    async def run():
        check_decorator = is_admin_context()
        predicate = check_decorator.predicate

        # BOSS user
        interaction = MagicMock()
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.guild = MagicMock()
        interaction.user.guild.owner_id = 12345
        interaction.user.id = 12345
        interaction.client = MagicMock()

        allowed = await predicate(interaction)
        assert allowed is True

    asyncio.run(run())

def test_is_monitor_context_check():
    async def run():
        check_decorator = is_monitor_context()
        predicate = check_decorator.predicate

        # INSPECTOR in admin channel
        role_tester = MagicMock()
        role_tester.id = 777
        interaction = MagicMock()
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.guild = MagicMock()
        interaction.user.guild.owner_id = 99999
        interaction.user.id = 11111
        interaction.user.guild_permissions = MagicMock()
        interaction.user.guild_permissions.administrator = False
        interaction.user.roles = [role_tester]

        interaction.channel_id = 12345
        interaction.client.admin_channel_id = 12345
        interaction.client.access_control = {"roles": {"admin": 555, "tester": 777}}

        allowed = await predicate(interaction)
        assert allowed is True

    asyncio.run(run())
