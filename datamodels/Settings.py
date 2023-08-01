from discord.ext import commands
import discord
from utils.mongo import Document


class PunishmentType:
    def __init__(self, generic: bool, custom: bool, name: str):
        self.generic = generic
        self.custom = custom
        self.name = name

    generic: bool
    custom: bool
    name: str


class Settings(Document):
    async def get_settings(self, guild_id: int) -> dict:
        """
        Gets the settings for a guild.
        """
        return await self.db.find_one({"_id": guild_id})

    pass
