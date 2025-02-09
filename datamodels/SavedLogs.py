from discord.ext import commands
import discord
from utils.mongo import Document
from utils.basedataclass import BaseDataClass


class SavedLog(BaseDataClass):
    guild_id: int
    timestamp: int
    logs: list[dict]


class SavedLogs(Document):
    pass
