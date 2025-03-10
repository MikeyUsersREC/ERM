from discord.ext import commands
import discord
from utils.mongo import Document
from datamodels.ServerKeys import ServerKey


class MapleKeys(Document):
    async def get_server_key(self, guild_id: int):
        doc = await self.db.find_one({"guildId": guild_id})
        if not doc:
            return None
        return ServerKey(guild_id=doc["guildId"], key=doc["uniqueToken"])
