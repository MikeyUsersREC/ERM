import discord
from discord.ext import commands

from erm import management_predicate, staff_predicate
from helpers import MockContext
import aiohttp
from decouple import config

class OnMemberUpdate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_member_update")
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            # Role have been changed
            before_context = MockContext(bot=self.bot, author=after, guild=after.guild)

            after_permission = 0
            if await management_predicate(before_context):
                after_permission = 2
            elif await staff_predicate(before_context):
                after_permission = 1

            after_context = MockContext(bot=self.bot, author=before, guild=before.guild)

            old_permission = 0
            if await management_predicate(after_context):
                old_permission = 2
            elif await staff_predicate(after_context):
                old_permission = 1

            if after_permission != old_permission:
                url_var = config("BASE_API_URL")
                if url_var in ["", None]:
                    return
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{url_var}/UpdatePermissionCache/{before.id}/{before.guild.id}/{after_permission}"):
                        pass

async def setup(bot):
    await bot.add_cog(OnMemberUpdate(bot))