import uvicorn
from fastapi import FastAPI
from discord.ext import commands
import discord

app = FastAPI()


@app.get('/')
async def root():
    return {'message': 'Hello World!'}


class ServerAPI(commands.Cog):


    def __init__(self, bot):
        self.bot = bot

    async def start_server(self):
        self.config = uvicorn.Config("api:app", port=5000, log_level="info")
        self.server = uvicorn.Server(self.config)
        await self.server.serve()

    async def stop_server(self):
        await self.server.shutdown()

    async def cog_load(self) -> None:
        await self.start_server()

    async def cog_unload(self) -> None:
        await self.stop_server()

async def setup(bot):
    await bot.add_cog(ServerAPI(bot))
