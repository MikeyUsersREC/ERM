import logging

from discord.ext import commands
on_ready = False

class OnReady(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_ready")
    async def on_ready(self):
        global on_ready
        if on_ready:
            logging.info("{} has connected to gateway!".format(self.bot.user.name))
            on_ready = False

    @commands.Cog.listener('on_shard_connect')
    async def on_shard_connect(self, sid: int):
        async def callback():
            try:
                channel = await self.bot.fetch_channel(1057960689639116860)
                await channel.send(f'Shard `{sid}` has connected.')
            except Exception as e:
                print(e)
        # print('Shard connection')
        await callback()

    @commands.Cog.listener('on_shard_disconnect')
    async def on_shard_disconnect(self, sid: int):
        async def callback():
            try:
                channel = await self.bot.fetch_channel(1057960689639116860)
                await channel.send(f'Shard `{sid}` has disconnected.')
            except Exception as e:
                print(e)
        # print('Shard disconnection')
        await callback()

async def setup(bot):
    await bot.add_cog(OnReady(bot))
