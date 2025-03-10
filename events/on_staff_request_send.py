import aiohttp
import discord
from discord.ext import commands
import bson
from erm import Bot
from bson import ObjectId
from decouple import config

from menus import AcknowledgeStaffRequest
from utils import prc_api
from utils.constants import BLANK_COLOR


class OnStaffRequestSend(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_staff_request_send(self, o_id: ObjectId):
        doc = await self.bot.staff_requests.db.find_one({"_id": o_id})
        user_id = doc["user_id"]
        guild_id = doc["guild_id"]
        reason = doc["reason"]

        settings = await self.bot.settings.db.find_one({"_id": guild_id})
        staff_requests = settings.get("game_logging", {}).get("staff_requests", {})
        if staff_requests == {}:
            return

        is_erlc = bool(await self.bot.server_keys.db.count_documents({"_id": guild_id}))
        players_ingame = -1
        staff_ingame = -1
        if is_erlc:
            try:
                players = await self.bot.prc_api.get_server_players(guild_id)
            except prc_api.ResponseFailure:
                players = []

            if len(players) > 0:
                players_ingame = len(players)
                staff_ingame = len(
                    list(filter(lambda x: x.permission != "Normal", players))
                )

        staff_clocked_in = await self.bot.shift_management.shifts.db.count_documents(
            {"EndEpoch": 0, "Guild": guild_id}
        )

        guild = self.bot.get_guild(guild_id) or await self.bot.fetch_guild(guild_id)
        user = guild.get_member(user_id) or await self.bot.fetch_user(user_id)
        newline = "\n"

        embed = (
            discord.Embed(
                title="Staff Request Received",
                description="A new staff request has been received from <@{0}> ({0})".format(
                    user_id
                ),
                color=BLANK_COLOR,
            )
            .set_thumbnail(url=user.display_avatar.url)
            .add_field(
                name="Request Information",
                value=(f"> **Reason:** {reason}\n" f"> **Requested By:** <@{user_id}>"),
                inline=False,
            )
            .add_field(
                name="Staff Information",
                value=(
                    f"{'> **Players In-Game:** {0}{1}'.format(str(players_ingame), newline) if players_ingame > 0 else ''}"
                    f"> **Staff Clocked In:** {staff_clocked_in}\n"
                    f"{'> **Staff In-Game:** {0}{1}'.format(str(staff_ingame), newline) if staff_ingame > 0 else ''}"
                ),
            )
        )

        mentioned_roles = staff_requests.get("mentioned_roles", [])
        channel_id = staff_requests["channel"]
        channel = guild.get_channel(channel_id) or await guild.fetch_channel(channel_id)

        await channel.send(
            ", ".join(["<@&{0}>".format(role) for role in mentioned_roles]),
            embed=embed,
            allowed_mentions=discord.AllowedMentions.all(),
            view=AcknowledgeStaffRequest(self.bot, o_id),
        )


async def setup(bot):
    await bot.add_cog(OnStaffRequestSend(bot))
