import logging

from discord.ext import commands


class OnReady(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_ready")
    async def on_ready(self):
        logging.info("{} has connected to gateway!".format(self.bot.user.name))


async def setup(bot):
    await bot.add_cog(OnReady(bot))
