import discord
from discord.ext import commands
from erm import management_predicate, staff_predicate, management_check, staff_check
import aiohttp
from decouple import config

class OnMemberRawRemove(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_member_raw_remove")
    async def on_member_raw_remove(self, payload: discord.RawMemberRemoveEvent):
        try:
            url_var = config("BASE_API_URL")
            if url_var in ["", None]:
                return

            panel_url_var = config("PANEL_API_URL")
            if url_var in ["", None]:
                return
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{url_var}/Auth/UpdatePermissionCache/{payload.user.id}/{payload.guild_id}/0", headers={
                    "Authorization": config('INTERNAL_API_AUTH')
                }):
                    pass

                url = f"{panel_url_var}/Internal/UpdatePermissionsCache/{payload.guild_id}/{payload.user.id}/0"
                print(f"Sending request to: {url}")
                
                async with session.post(url):
                    pass

        except Exception as e:
            print(f"l35, on_member_remove: {e}")

async def setup(bot):
    await bot.add_cog(OnMemberRawRemove(bot))
