import discord
from discord.ext import commands

from utils.constants import BLANK_COLOR, GREEN_COLOR


class OnLOAAccept(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_loa_accept(self, s_loa: dict, role_ids: list[int]):
        guild = self.bot.get_guild(s_loa["guild_id"])
        try:
            user = await guild.fetch_member(int(s_loa["user_id"]))
        except:
            return
        try:
            await user.send(
                embed=discord.Embed(
                    title="<:success:1163149118366040106> Activity Notice Accepted",
                    description=f"Your {s_loa['type']} request in **{guild.name}** was accepted!",
                    color=GREEN_COLOR
                )
            )
        except:
            pass

    
        loa_roles = list(filter(lambda x: x is not None, [discord.utils.get(identifier) for identifier in role_ids]))
        for rl in loa_roles:
            if rl not in user.roles:
                try:
                    await user.add_roles(rl)
                except discord.HTTPException:
                    pass


async def setup(bot):
    await bot.add_cog(OnLOAAccept(bot))
