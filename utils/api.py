import asyncio

import uvicorn
from fastapi import FastAPI, APIRouter
from discord.ext import commands
import discord
from erm import Bot

class APIRoutes:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.router =  APIRouter()
        self.router.add_api_route("/status", self.get_status)
    def get_status(self):
        return {"guilds": len(self.bot.guilds), "ping": round(self.bot.latency * 1000)}



api = FastAPI()


class ServerAPI(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def start_server(self):
        api.include_router(APIRoutes(self.bot).router)
        self.config = uvicorn.Config("utils.api:api", port=5000, log_level="info")
        self.server = uvicorn.Server(self.config)
        await self.server.serve()

    async def stop_server(self):
        await self.server.shutdown()

    async def cog_load(self) -> None:
        asyncio.run_coroutine_threadsafe(self.start_server(), self.bot.loop)

    async def cog_unload(self) -> None:
        await self.stop_server()

async def setup(bot):
    await bot.add_cog(ServerAPI(bot))
