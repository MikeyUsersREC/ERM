from discord.ext import commands
import discord
from utils.mongo import Document


class PunishmentTypes(Document):
    async def get_punishment_types(self, guild_id: int):
        """
        Gets the punishment types for a guild.
        """
        return await self.db.find_one({"_id": guild_id})
