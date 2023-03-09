import sys
import logging
import sys

from decouple import config
from discord.ext import commands, ipc
from discord.ext.ipc.errors import IPCError
from discord.ext.ipc.server import route


class Routes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if not hasattr(bot, "ipc"):
            bot.ipc = ipc.Server(
                self.bot,
                host="127.0.0.1",
                port=5600,
                secret_key=config("IPC_SECRET_KEY"),
            )
            bot.ipc.start()

    @commands.Cog.listener()
    async def on_ipc_ready(self):
        logging.info("IPC is ready")

    @commands.Cog.listener()
    async def on_ipc_error(self, endpoint: str, error: IPCError):
        logging.error(endpoint, "raised", error, file=sys.stderr)

    @route("get_user_data")
    async def get_user_data(self, data):
        user = self.bot.get_user(data.user_id)
        return user._to_minimal_user_json()

    @route("get_guild_count")
    async def get_guild_count(self, data):
        return {"count": len(self.bot.guilds)}

    @route("get_guild_ids")
    async def get_guild_ids(self, data):
        final = []
        for guild in self.bot.guilds:
            final.append(guild.id)
        return {"guilds": final}

    @route("get_guild")
    async def get_guild(self, data):
        guild = self.bot.get_guild(data.guild_id)
        settingData = await self.bot.settings.find_by_id(data.guild_id)

        if guild == None or settingData == None:
            return None

        guild_data = {
            "name": guild.name,
            "id": guild.id,
            "icon": guild.icon.url,
            "settings": settingData,
            "roles": [{"name": role.name, "id": role.id} for role in guild.roles],
            "channels": [
                {"name": channel.name, "id": channel.id} for channel in guild.channels
            ],
        }

        return guild_data


async def setup(bot):
    await bot.add_cog(Routes(bot))
