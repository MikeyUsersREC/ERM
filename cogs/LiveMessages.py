import discord
from discord.ext import commands

from menus import LiveMenu
from utils.flags import DutyManageOptions


class LiveMessages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # @commands.hybrid_group("livemessage")
    # async def livemessage(self, ctx):
    #     pass
    #
    # @livemessage.command(
    #     name="panel",
    #     description="Sends a panel to a channel so that staff members can use ERM features easily",
    #     extras={"category": "Live Message"},
    # )
    # async def livemessage_panel(
    #     self, ctx: commands.Context, channel: discord.TextChannel
    # ):
    #     await ctx.send(view=LiveMenu(self.bot, ctx))


async def setup(bot):
    await bot.add_cog(LiveMessages(bot))
