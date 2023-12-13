import discord
from discord.ext import commands


class OnMessageDelete(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author is not self.bot.user:
            return

        if message.guild is None:
            return
        pass

async def setup(bot: commands.Bot):
    await bot.add_cog(OnMessageDelete(bot))
