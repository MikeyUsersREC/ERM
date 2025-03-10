import discord
from discord.ext import commands
import aiohttp


class Bloxlink:
    def __init__(self, bot: commands.Bot, key: str):
        self.api_key = key
        self.session = aiohttp.ClientSession()
        bot.external_http_sessions.append(self.session)
        self.bot = bot

    async def _send_request(self, method, url, params=None, body=None):
        async with self.session.request(
            method, url, params=params, headers={"Authorization": self.api_key}
        ) as resp:
            return (resp, await resp.json())

    async def find_roblox(self, user_id: int):
        doc = await self.bot.oauth2_users.db.find_one({"discord_id": user_id})
        if doc:
            return {"robloxID": doc["roblox_id"]}

        response, resp_json = await self._send_request(
            "GET", f"https://api.blox.link/v4/public/discord-to-roblox/{user_id}"
        )

        if resp_json.get("error"):
            return {}
        else:
            return resp_json

    async def get_roblox_info(self, user_id: int):
        if not user_id:
            return {}

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://users.roblox.com/v1/users/{}".format(user_id)
            ) as resp:
                return await resp.json()
