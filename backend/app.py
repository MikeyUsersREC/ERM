from json import loads

import aiohttp
import hikari
from decouple import config
from sanic import Sanic
from sanic.exceptions import InvalidUsage, Unauthorized
from sanic.response import json
from sanic_cors import CORS

from utils import return_token_or_raise, filter_guilds

app = Sanic("HelloWorld")
CORS(app)
app.config.FALLBACK_ERROR_FORMAT = "json"


try:
    from uvloop import install

    install()
except:
    pass

rest_client = hikari.RESTApp()

if config("ENVIRONMENT") == "DEVELOPMENT":
    app.config["DISCORD_CLIENT_ID"] = config("DEVELOPMENT_CLIENT_ID")
    app.config["DISCORD_CLIENT_SECRET"] = config("DEVELOPMENT_CLIENT_SECRET")
    app.config["DISCORD_REDIRECT_URI"] = config("DEVELOPMENT_REDIRECT_URI")
    app.config["DISCORD_BOT_TOKEN"] = config("DEVELOPMENT_BOT_TOKEN")
elif config("ENVIRONMENT") == "PRODUCTION":
    app.config["DISCORD_CLIENT_ID"] = config("PRODUCTION_CLIENT_ID")
    app.config["DISCORD_CLIENT_SECRET"] = config("PRODUCTION_CLIENT_SECRET")
    app.config["DISCORD_REDIRECT_URI"] = config("PRODUCTION_REDIRECT_URI")
    app.config["DISCORD_BOT_TOKEN"] = config("PRODUCTION_BOT_TOKEN")
else:
    raise Exception("Environment variable 'environment' not set")


@app.route("/oauth2/callback", methods=["POST"])
async def callback(request):
    args = request.json

    if not args.get("code"):
        raise InvalidUsage("Invalid request")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": app.config["DISCORD_CLIENT_ID"],
                "client_secret": app.config["DISCORD_CLIENT_SECRET"],
                "grant_type": "authorization_code",
                "code": args.get("code"),
                "redirect_uri": app.config["DISCORD_REDIRECT_URI"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as resp:
            data = await resp.json()
            print(data)
            return json({"access_token": data.get("access_token")})
        # return redirect(f'/users/me?token={data.get("access_token")}')


@app.route("/users/me")
async def get_own_user(request):
    token = await return_token_or_raise(request)
    try:
        async with rest_client.acquire(token) as rest:
            user = await rest.fetch_my_user()
    except hikari.errors.UnauthorizedError:
        raise Unauthorized("Invalid access token")

    return json(
        {
            "id": user.id,
            "username": user.username,
            "discriminator": user.discriminator,
            "avatar_url": f"https://cdn.discordapp.com/avatars/{user.id}/{user.avatar_hash}.png",
            "bot": user.is_bot,
            "system": user.is_system,
            "mfa_enabled": user.is_mfa_enabled,
            "locale": user.locale,
            "verified": user.is_verified,
            "email": user.email,
            "flags": user.flags,
            "premium_type": user.premium_type,
        }
    )


@app.route("/guilds")
async def mutual_guilds(request):
    token = await return_token_or_raise(request)

    try:
        async with rest_client.acquire(token) as rest:
            user_guilds = await rest.fetch_my_guilds()
    except hikari.errors.UnauthorizedError:
        raise Unauthorized("Invalid access token")

    valid_guilds = await filter_guilds(user_guilds)
    guild_ids = map(lambda x: str(x.id), valid_guilds)

    async with aiohttp.ClientSession() as session:
        response = await session.post(
            "http://localhost:6969/guilds", json={"guilds": list(guild_ids)}
        )
        return json(loads(await response.text()))


if __name__ == "__main__":
    app.run(port=5000, debug=True)
