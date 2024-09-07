import discord
from discord.ext import commands

from erm import management_predicate, staff_predicate, management_check, staff_check
# from helpers import MockContext
import aiohttp
from decouple import config

class OnMemberUpdate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_member_update")
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            # Role have been changed
            old_permission = 0
            if await management_check(self.bot, before.guild, before):
                old_permission = 2
            elif await staff_check(self.bot, before.guild, before):
                old_permission = 1

            after_permission = 0
            if await management_check(self.bot, after.guild, after):
                after_permission = 2
            elif await staff_check(self.bot, after.guild, after):
                after_permission = 1


            if after_permission != old_permission:
                    try:
                        url_var = config("BASE_API_URL")
                        if url_var in ["", None]:
                            return
                        async with aiohttp.ClientSession() as session:
                            async with session.get(f"{url_var}/Auth/UpdatePermissionCache/{before.id}/{before.guild.id}/{after_permission}", headers={
                                "Authorization": config('INTERNAL_API_AUTH')
                            }):
                                pass
                    except:
                        pass



async def setup(bot):
    await bot.add_cog(OnMemberUpdate(bot))
