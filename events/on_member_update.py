import discord
from discord.ext import commands
from erm import management_predicate, staff_predicate, management_check, staff_check
import aiohttp
from decouple import config


class OnMemberUpdate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_member_update")
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            # Roles have been changed
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

                    panel_url_var = config("PANEL_API_URL")
                    if panel_url_var in ["", None]:
                        return

                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"{url_var}/Auth/UpdatePermissionCache/{before.id}/{before.guild.id}/{after_permission}",
                            headers={"Authorization": config("INTERNAL_API_AUTH")},
                        ):
                            pass

                        url = f"{panel_url_var}/Internal/UpdatePermissionsCache/{before.guild.id}/{before.id}/{after_permission}"
                        print(f"Sending request to: {url}")

                        async with session.post(url):
                            pass

                except:
                    pass


async def setup(bot):
    await bot.add_cog(OnMemberUpdate(bot))
