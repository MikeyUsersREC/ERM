from discord.ext import commands
import discord
from utils.mongo import Document


class FlagItem:
    emoji: str
    name: str

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class CustomFlags(Document):
    async def get_flags_by_roblox(self, roblox_id: int):
        document = await self.db.find_one({"roblox_id": roblox_id})
        flags = []
        for item in document["flags"]:
            flags.append(FlagItem(name=item["name"], emoji=item["emoji"]))
        return flags
