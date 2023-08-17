import aiohttp_cors
import discord
from aiohttp import web
from discord.ext import commands

from erm import management_predicate
from helpers import MockContext


async def is_staff(ctx: commands.Context):
    guild_settings = await ctx.bot.settings.find_by_id(ctx.guild.id)
    if guild_settings:
        if "role" in guild_settings["staff_management"].keys():
            if guild_settings["staff_management"]["role"] != "":
                if isinstance(guild_settings["staff_management"]["role"], list):
                    for role in guild_settings["staff_management"]["role"]:
                        if role in [role.id for role in ctx.author.roles]:
                            return True
                elif isinstance(guild_settings["staff_management"]["role"], int):
                    if guild_settings["staff_management"]["role"] in [
                        role.id for role in ctx.author.roles
                    ]:
                        return True
    if ctx.author.guild_permissions.manage_messages:
        return True
    return False


class Server(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.site = None

    async def get_status(self, request):
        return web.json_response(
            {"guilds": len(self.bot.guilds), "ping": round(self.bot.latency * 1000)}
        )

    async def cog_unload(self) -> None:
        await self.api.stop()

    async def get_mutual_guilds(self, request):
        json_data = await request.json()
        guild_ids = json_data.get("guilds")
        if not guild_ids:
            return web.json_response({"error": "Invalid guilds"}, status=400)

        guilds = []
        for i in guild_ids:
            guild: discord.Guild = self.bot.get_guild(int(i))
            if not guild:
                continue
            if guild.get_member(self.bot.user.id):
                try:
                    icon = guild.icon.with_size(512)
                    icon = icon.with_format("png")
                    icon = str(icon)
                except Exception as e:
                   # # print(e)
                    icon = "https://cdn.discordapp.com/embed/avatars/0.png?size=512"

                guilds.append(
                    {"id": str(guild.id), "name": str(guild.name), "icon_url": icon}
                )

        return web.json_response({"guilds": guilds})

    async def get_staff_guilds(self, request):
        json_data = await request.json()
        guild_ids = json_data.get("guilds")
        user_id = json_data.get("user")
        if not guild_ids:
            return web.json_response({"error": "Invalid guilds"}, status=400)

        guilds = []
        for i in guild_ids:
            guild: discord.Guild = self.bot.get_guild(int(i))
            if not guild:
                continue
            if guild.get_member(self.bot.user.id):
                try:
                    icon = guild.icon.with_size(512)
                    icon = icon.with_format("png")
                    icon = str(icon)
                except Exception as e:
                   # # print(e)
                    icon = "https://cdn.discordapp.com/embed/avatars/0.png?size=512"

                try:
                    user = await guild.fetch_member(user_id)
                except:
                    continue
                mock_context = MockContext(bot=self.bot, author=user, guild=guild)

                permission_level = 0
                if await management_predicate(mock_context):
                    permission_level = 2
                elif await is_staff(mock_context):
                    permission_level = 1

                if permission_level > 0:
                    guilds.append(
                        {
                            "id": str(guild.id),
                            "name": str(guild.name),
                            "icon_url": icon,
                            "member_count": str(guild.member_count),
                            "permission_level": permission_level,
                        }
                    )

        return web.json_response(guilds)

    async def check_staff_level(self, request):
        json_data = await request.json()
        guild_id = json_data.get("guild")
        user_id = json_data.get("user")
        if not guild_id or not user_id:
            return web.json_response({"error": "Invalid guild"}, status=400)

        try:
            guild = await self.bot.fetch_guild(guild_id)
        except (discord.Forbidden, discord.HTTPException):
            return web.json_response({"error": "Could not find guild"})

        try:
            user = await guild.fetch_member(user_id)
        except (discord.Forbidden, discord.HTTPException):
            return web.json_response({"permission_level": 0})

        mock_context = MockContext(bot=self.bot, author=user, guild=guild)

        permission_level = 0
        if await management_predicate(mock_context):
            permission_level = 2
        elif await is_staff(mock_context):
            permission_level = 1

        return web.json_response({"permission_level": permission_level})

    async def get_guild_settings(self, request):
        json_data = await request.json()
        guild_id = json_data.get("guild")
        if not guild_id:
            return web.json_response({"error": "Invalid guild"}, status=400)
        guild: discord.Guild = self.bot.get_guild(int(guild_id))
        settings = await self.bot.settings.find_by_id(guild.id)
        if not settings:
            return web.json_response({"error": "Guild not found"}, status=404)

        return web.json_response(settings)

    async def update_guild_settings(self, request):
        json_data = await request.json()
        guild_id = json_data.get("guild")

        for key, value in json_data.items():
            if key == "guild":
                continue
            if isinstance(value, dict):
                settings = await self.bot.settings.find_by_id(guild_id)
                if not settings:
                    return web.json_response({"error": "Guild not found"}, status=404)
                for k, v in value.items():
                    settings[key][k] = v
        await self.bot.settings.update_by_id(settings)

        if not guild_id:
            return web.json_response({"error": "Invalid guild"}, status=400)
        guild: discord.Guild = self.bot.get_guild(int(guild_id))
        settings = await self.bot.settings.find_by_id(guild.id)
        if not settings:
            return web.json_response({"error": "Guild not found"}, status=404)

        return web.json_response(settings)

    async def get_last_warnings(self, request):
        json_data = await request.json()
        guild_id = json_data.get("guild")

        warning_objects = {}
        async for document in self.bot.warnings.db.find(
            {"warnings": {"$elemMatch": {"Guild": guild_id}}}
        ).sort([("$natural", -1)]).limit(10):
            warning_objects[document["_id"]] = list(
                filter(lambda x: x["Guild"] == guild_id, document["warnings"])
            )

        return web.json_response(warning_objects)

    async def start_server(self):
        app = web.Application()
        cors = aiohttp_cors.setup(app)

        cors.add(
            cors.add(app.router.add_resource("/status")).add_route(
                "GET", self.get_status
            ),
            {
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True, expose_headers="*", allow_headers="*"
                )
            },
        )

        cors.add(
            cors.add(app.router.add_resource("/guilds")).add_route(
                "POST", self.get_mutual_guilds
            ),
            {
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True, expose_headers="*", allow_headers="*"
                )
            },
        )

        cors.add(
            cors.add(app.router.add_resource("/staff-guilds")).add_route(
                "POST", self.get_staff_guilds
            ),
            {
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True, expose_headers="*", allow_headers="*"
                )
            },
        )

        cors.add(
            cors.add(app.router.add_resource("/check-staff-level")).add_route(
                "POST", self.check_staff_level
            ),
            {
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True, expose_headers="*", allow_headers="*"
                )
            },
        )

        cors.add(
            cors.add(app.router.add_resource("/guild-settings")).add_route(
                "GET", self.get_guild_settings
            ),
            {
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True, expose_headers="*", allow_headers="*"
                )
            },
        )

        cors.add(
            cors.add(app.router.add_resource("/update-settings")).add_route(
                "GET", self.update_guild_settings
            ),
            {
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True, expose_headers="*", allow_headers="*"
                )
            },
        )

        cors.add(
            cors.add(app.router.add_resource("/get-warnings")).add_route(
                "GET", self.get_last_warnings
            ),
            {
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True, expose_headers="*", allow_headers="*"
                )
            },
        )

        runner = web.AppRunner(app)
        await runner.setup()

        self.api = web.TCPSite(runner, "0.0.0.0", 6969)

        await self.bot.wait_until_ready()
        await self.api.start()
       # # print("Server has been started.")


async def setup(bot):
    init = Server(bot)
    await bot.add_cog(init)
    await init.start_server()
