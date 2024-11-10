import discord
from discord.ext import commands

from utils.constants import BLANK_COLOR


class OnLOADeny(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_loa_deny(self, s_loa: dict):
        guild = self.bot.get_guild(s_loa["guild_id"])
        try:
            user = await guild.fetch_member(int(s_loa["user_id"]))
        except:
            return
        reason = s_loa["denial_reason"]
        try:
            await user.send(
                embed=discord.Embed(
                    title="Activity Notice Denied",
                    description=f"Your {s_loa['type']} request in **{guild.name}** was denied.\n**Reason:** {reason}",
                    color=BLANK_COLOR
                )
            )
        except:
            pass


async def setup(bot):
    await bot.add_cog(OnLOADeny(bot))
