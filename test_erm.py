import unittest
from typing import Union
from unittest.mock import MagicMock

from discord import DMChannel
from discord.ext.commands import CheckFailure, Context, NoPrivateMessage, has_any_role

from helpers import MockContext, MockRole


async def has_any_role_check(ctx: Context, *roles: Union[str, int]) -> bool:
    """
    Returns True if the context's author has any of the specified roles.
    `roles` are the names or IDs of the roles for which to check.
    False is always returns if the context is outside a guild.
    """
    try:
        return await has_any_role(*roles).predicate(ctx)
    except CheckFailure:
        return False


async def has_no_roles_check(ctx: Context, *roles: Union[str, int]) -> bool:
    """
    Returns True if the context's author doesn't have any of the specified roles.
    `roles` are the names or IDs of the roles for which to check.
    False is always returns if the context is outside a guild.
    """
    try:
        return not await has_any_role(*roles).predicate(ctx)
    except NoPrivateMessage:
        return False
    except CheckFailure:
        return True


class ChecksTests(unittest.IsolatedAsyncioTestCase):
    """Tests the check functions defined in `bot.checks`."""

    def setUp(self):
        self.ctx = MockContext()

    async def test_has_any_role_check_without_guild(self):
        """`has_any_role_check` returns `False` for non-guild channels."""
        self.ctx.channel = MagicMock(DMChannel)
        self.assertFalse(await has_any_role_check(self.ctx))

    async def test_has_any_role_check_without_required_roles(self):
        """`has_any_role_check` returns `False` if `Context.author` lacks the required role."""
        self.ctx.author.roles = []
        self.assertFalse(await has_any_role_check(self.ctx))

    async def test_has_any_role_check_with_guild_and_required_role(self):
        """`has_any_role_check` returns `True` if `Context.author` has the required role."""
        self.ctx.author.roles.append(MockRole(id=10))
        self.assertTrue(await has_any_role_check(self.ctx, 10))

    async def test_has_no_roles_check_without_guild(self):
        """`has_no_roles_check` should return `False` when `Context.guild` is None."""
        self.ctx.channel = MagicMock(DMChannel)
        self.ctx.guild = None
        self.assertFalse(await has_no_roles_check(self.ctx))
