from sanic.exceptions import Unauthorized
import typing
import hikari


async def return_token_or_raise(request):
    token = request.headers.get("access_token")
    if not token:
        raise Unauthorized("Invalid access token")
    return token


async def filter_guilds(guilds: typing.List[hikari.OwnGuild]):
    return filter(lambda x: x.my_permissions & hikari.Permissions.MANAGE_GUILD, guilds)
