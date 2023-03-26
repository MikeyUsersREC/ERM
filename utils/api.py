import asyncio
import datetime

import uvicorn
from fastapi import FastAPI, APIRouter, Header, HTTPException, Request
from discord.ext import commands
import discord
from erm import Bot
from typing import Annotated
from decouple import config
from zuid import ZUID

tokenGenerator = ZUID(
    prefix="",
    length=64,
    timestamped=True,
    charset="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_",
)

class APIRoutes:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.router = APIRouter()
        for i in dir(self):
            print(i)
            if any([i.startswith(a) for a in ('GET_', 'POST_', 'PATCH_', 'DELETE_')]) and not i.startswith("_"):
                x = i.split("_")[0]
                self.router.add_api_route(f"/{i.removeprefix(x+'_')}", getattr(self, i), methods=[i.split('_')[0].upper()])

    def GET_status(self):
        return {"guilds": len(self.bot.guilds), "ping": round(self.bot.latency * 1000)}

    async def GET_get_token(self, authorization: Annotated[str | None, Header()], request: Request):
        '''

        Generates a token for the API. Requires an unspecified private key.

        :param authorization:
        :param request:
        :return:
        '''

        if authorization != config("API_PRIVATE_KEY"):
            raise HTTPException(status_code=401, detail="Invalid authorization")
        has_token = await self.bot.api_tokens.find_by_id(request.client.host)
        if has_token:
            if not int(datetime.datetime.now().timestamp()) > has_token["expires_at"]:
                return has_token

        generated = tokenGenerator()
        object = {
            "_id": request.client.host,
            "token": generated,
            "created_at": int(datetime.datetime.now().timestamp()),
            "expires_at": int(datetime.datetime.now().timestamp()) + 2.592e+6,
        }

        await self.bot.api_tokens.upsert(object)

        return object


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
