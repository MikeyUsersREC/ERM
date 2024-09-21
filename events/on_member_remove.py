import discord
from discord.ext import commands
from erm import management_predicate, staff_predicate, management_check, staff_check
import aiohttp
from decouple import config

class OnMemberRawRemove(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_member_raw_remove")
    async def on_member_raw_remove(self, payload):
        # Member left the server
        old_permission = 0
        new_perm = 0
        guild = await self.bot.fetch_guild(payload.guild_id)
        user = payload.user

        if not isinstance(payload.user, discord.User) and not payload.user:            
            if await management_check(self.bot, guild, user):
                old_permission = 2
            elif await staff_check(self.bot, guild, user):
                old_permission = 1
        else:
            old_permission = -1

        if new_perm != old_permission:
            try:
                url_var = config("BASE_API_URL")
                if url_var in ["", None]:
                    return

                panel_url_var = config("PANEL_API_URL")
                if url_var in ["", None]:
                    return
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{url_var}/Auth/UpdatePermissionCache/{user.id}/{guild.id}/{new_perm}", headers={
                        "Authorization": config('INTERNAL_API_AUTH')
                    }):
                        pass

                    url = f"{panel_url_var}/Internal/UpdatePermissionsCache/{user.id}/{guild.id}/{new_perm}"
                    print(f"Sending request to: {url}")
                    
                    async with session.post(url):
                        pass

            except:
                pass

async def setup(bot):
    await bot.add_cog(OnMemberRawRemove(bot))
