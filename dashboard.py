import asyncio
import os

from decouple import config
from discord.ext import ipc
from quart import Quart, redirect, render_template, request, url_for
from quart_discord import DiscordOAuth2Session

app = Quart(__name__)
app.secret_key = b"UQOAOWOQP_ALNBYIPPPML"
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true"

if config("ENVIRONMENT") == "DEVELOPMENT":
    app.config["DISCORD_CLIENT_ID"] = config("DEVELOPMENT_CLIENT_ID")
    app.config["DISCORD_CLIENT_SECRET"] = config("DEVELOPMENT_CLIENT_SECRET")
    app.config["DISCORD_REDIRECT_URI"] = config("DEVELOPMENT_REDIRECT_URI")
    app.config["DISCORD_BOT_TOKEN"] = config("DEVELOPMENT_BOT_TOKEN")
elif os.config("ENVIRONMENT") == "PRODUCTION":
    app.config["DISCORD_CLIENT_ID"] = config("PRODUCTION_CLIENT_ID")
    app.config["DISCORD_CLIENT_SECRET"] = config("PRODUCTION_CLIENT_SECRET")
    app.config["DISCORD_REDIRECT_URI"] = config("PRODUCTION_REDIRECT_URI")
    app.config["DISCORD_BOT_TOKEN"] = config("PRODUCTION_BOT_TOKEN")
else:
    raise Exception("Environment variable 'environment' not set")

discord_oauth = DiscordOAuth2Session(app)
ipcClient = ipc.Client(host="127.0.0.1", port=5600, secret_key=config("IPC_SECRET_KEY"))


@app.route("/login/")
async def login():
    return await discord_oauth.create_session()


@app.route("/callback/")
async def callback():
    try:
        await discord_oauth.callback()
       # print("callback success")
    except:
       # print("callback failed")
        return redirect(url_for("login"))
   # print("redirecting")
    return redirect(url_for("dashboard"))


@app.route("/")
async def index():
    return await render_template("index.html")


@app.route("/invite/")
async def invite(guild_id=None):
    if guild_id is None:
        return redirect(
            f'https://discord.com/oauth2/authorize?client_id={app.config["DISCORD_CLIENT_ID"]}&scope=bot&permissions=8'
        )
    return redirect(
        f'https://discord.com/oauth2/authorize?client_id={app.config["DISCORD_CLIENT_ID"]}&scope=bot&permissions=8&guild_id={guild_id}&response_type=code&redirect_uri={app.config["DISCORD_REDIRECT_URI"]}'
    )


@app.route("/dashboard/")
async def dashboard():
    user = await discord_oauth.fetch_user()
    guild_count = await ipcClient.request("get_guild_count")
    guild_count = guild_count["count"]
    guildIds = await ipcClient.request("get_guild_ids")
    guildIds = guildIds["guilds"]
    try:
        userGuilds = await discord_oauth.fetch_guilds()
    except:
        # return await redirect(url_for('login'))
        pass
    guilds = []

    for guild in userGuilds:
        if guild.permissions.manage_guild:
            guild.classColor = "greenBorder" if guild.id in guildIds else "redBorder"
            guilds.append(guild)

    guilds.sort(key=lambda x: x.classColor == "redBorder")

    return await render_template(
        "dashboard.html", user=user, guildCount=guild_count, guilds=guilds
    )


@app.route("/dashboard/<int:guild_id>/")
async def dashboardServer(guild_id):
    if not await discord_oauth.authorized:
        return redirect(url_for("login"))

    guild = await ipcClient.request("get_guild", guild_id=guild_id)
    if "name" not in guild:
        return redirect(
            f'https://discord.com/oauth2/authorize?client_id={app.config["DISCORD_CLIENT_ID"]}&scope=bot&permissions=8&guild_id={guild_id}&response_type=code&redirect_uri={app.config["DISCORD_REDIRECT_URI"]}'
        )

    return await render_template(
        "server.html",
        guild=guild,
        guildName=guild["name"],
        guildIcon=guild["icon"],
        guildRoles=guild["roles"],
        guildChannels=guild["channels"],
        guildID=guild_id,
    )


@app.route("/dashboard/<int:guild_id>/", methods=["POST"])
async def dashboardServerPOST(guild_id):
    if not await discord_oauth.authorized:
        return redirect(url_for("login"))

    settingsChange = await request.get_json()

    guild = await ipcClient.request("get_guild", guild_id=guild_id)

    if settingsChange == None:
       # print("Variable was null or undefined.")
    else:
       # print(settingsChange)

    for configItem in guild["settings"]:
        if configItem in settingsChange.keys():
            guild["settings"][configItem] = settingsChange[configItem]

   # print(guild["settings"][configItem])

    if "name" not in guild:
        return redirect(
            f'https://discord.com/oauth2/authorize?client_id={app.config["DISCORD_CLIENT_ID"]}&scope=bot&permissions=8&guild_id={guild_id}&response_type=code&redirect_uri={app.config["DISCORD_REDIRECT_URI"]}'
        )

    return settingsChange
    return await render_template(
        "server.html",
        guild=guild,
        guildName=guild["name"],
        guildRoles=guild["roles"],
        guildIcon=guild["icon"],
        guildChannesl=guild["channels"],
        settingsChange=settingsChange,
    )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        app.ipc = loop.run_until_complete(
            ipcClient.start(loop=loop)
        )  # `Client.start()` returns new Client instance or None if it fails to start
        app.run(loop=loop)
    except:
        asyncio.sleep(1)
        app.ipc = loop.run_until_complete(
            ipcClient.start(loop=loop)
        )  # `Client.start()` returns new Client instance or None if it fails to start
        app.run(loop=loop)
    finally:
        loop.run_until_complete(
            app.ipc.close()
        )  # Closes the session, doesn't close the loop
        loop.close()
