from discord.ext import commands
import aiohttp_cors
import discord
from aiohttp import web
from discord.ext import commands


class Server(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.site = None

    async def get_status(self, request):
        return web.json_response({"guilds": len(self.bot.guilds), "ping": round(self.bot.latency * 1000)})

    async def get_mutual_guilds(self, request):
        json_data = await request.json()
        guild_ids = json_data.get('guilds')
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
                    print(e)
                    icon = "https://cdn.discordapp.com/embed/avatars/0.png?size=512"

                guilds.append({
                    "id": str(guild.id),
                    "name": str(guild.name),
                    "icon_url": icon
                })

        return web.json_response({"guilds": guilds})

    async def get_guild_settings(self, request):
        json_data = await request.json()
        guild_id = json_data.get('guild')
        if not guild_id:
            return web.json_response({"error": "Invalid guild"}, status=400)
        guild: discord.Guild = self.bot.get_guild(int(guild_id))
        settings = await self.bot.settings.find_by_id(guild.id)
        if not settings:
            return web.json_response({"error": "Guild not found"}, status=404)

        return web.json_response(settings)

    async def update_guild_settings(self, request):
        json_data = await request.json()
        guild_id = json_data.get('guild')

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
        guild_id = json_data.get('guild')

        warning_objects = {}
        async for document in self.bot.warnings.db.find({"warnings": {"$elemMatch": {"Guild": guild_id}}}).sort(
                [("$natural", -1)]).limit(10):
            warning_objects[document["_id"]] = list(filter(lambda x: x["Guild"] == guild_id, document["warnings"]))

        return web.json_response(warning_objects)

    async def start_server(self):
        app = web.Application()
        cors = aiohttp_cors.setup(app)

        cors.add(
            cors.add(app.router.add_resource('/status')).add_route('GET', self.get_status), {
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*"
                )
            }
        )

        cors.add(
            cors.add(app.router.add_resource('/guilds')).add_route('POST', self.get_mutual_guilds), {
                "localhost": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*"
                )
            }
        )

        cors.add(
            cors.add(app.router.add_resource('/guild-settings')).add_route('GET', self.get_guild_settings), {
                "localhost": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*"
                )
            }
        )

        cors.add(
            cors.add(app.router.add_resource('/update-settings')).add_route('POST', self.update_guild_settings), {
                "localhost": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*"
                )
            }
        )

        cors.add(
            cors.add(app.router.add_resource('/get-warnings')).add_route('GET', self.get_last_warnings), {
                "localhost": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*"
                )
            }
        )

        runner = web.AppRunner(app)
        await runner.setup()

        self.api = web.TCPSite(runner, '0.0.0.0', 6969)

        await self.bot.wait_until_ready()
        await self.api.start()
        print('Server has been started.')


async def setup(bot):
    init = Server(bot)
    await bot.add_cog(init)
    await init.start_server()
