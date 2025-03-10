import discord
from discord.ext import commands
from erm import management_predicate, staff_predicate, management_check, staff_check
import aiohttp
from decouple import config


class OnMemberRemove(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_member_remove")
    async def on_member_remove(self, member: discord.Member):
        try:
            url_var = config("BASE_API_URL")
            if url_var in ["", None]:
                return

            panel_url_var = config("PANEL_API_URL")
            if panel_url_var in ["", None]:
                return

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{url_var}/Auth/UpdatePermissionCache/{member.id}/{member.guild.id}/0",
                    headers={"Authorization": config("INTERNAL_API_AUTH")},
                ):
                    pass

                url = f"{panel_url_var}/Internal/UpdatePermissionsCache/{member.guild.id}/{member.id}/0"
                print(f"Sending request to: {url}")

                async with session.post(url):
                    pass

        except Exception as e:
            print(f"l35, on_member_remove: {e}")


async def setup(bot):
    await bot.add_cog(OnMemberRemove(bot))
