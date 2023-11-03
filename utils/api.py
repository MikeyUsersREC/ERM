import asyncio
import copy
import datetime
import typing

import aiohttp
import pytz
import uvicorn
from bson import ObjectId
from fastapi import FastAPI, APIRouter, Header, HTTPException, Request
from discord.ext import commands
import discord
from erm import Bot, management_predicate, is_staff, staff_predicate, staff_check, management_check
from typing import Annotated
from decouple import config

from pydantic import BaseModel

from utils.timestamp import td_format
# from helpers import MockContext
from utils.utils import tokenGenerator


class Identification(BaseModel):
    license: typing.Optional[typing.Any]
    discord: typing.Optional[typing.Any]
    source: typing.Literal["fivem", "discord"]


async def validate_authorization(bot: Bot, token: str, disable_static_tokens=False):
    # Check static and dynamic tokens
    if not disable_static_tokens:
        static_token = config("API_STATIC_TOKEN")  # Dashboard
        if token == static_token:
            return True
    token_obj = await bot.api_tokens.db.find_one({"token": token})
    if token_obj:
        if int(datetime.datetime.now().timestamp()) < token_obj["expires_at"]:
            return True
        else:
            return False
    else:
        return False


class APIRoutes:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.router = APIRouter()
        for i in dir(self):
           # # print(i)
            if any(
                [i.startswith(a) for a in ("GET_", "POST_", "PATCH_", "DELETE_")]
            ) and not i.startswith("_"):
                x = i.split("_")[0]
                self.router.add_api_route(
                    f"/{i.removeprefix(x+'_')}",
                    getattr(self, i),
                    methods=[i.split("_")[0].upper()],
                )

    def GET_status(self):
        return {"guilds": len(self.bot.guilds), "ping": round(self.bot.latency * 1000)}

    async def POST_get_mutual_guilds(self, request: Request):
        json_data = await request.json()
        guild_ids = json_data.get("guilds")
        if not guild_ids:
            return HTTPException(status_code=400, detail="No guild ids given")

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

        return {"guilds": guilds}


    async def POST_get_staff_guilds(self, request: Request):
        json_data = await request.json()
        guild_ids = json_data.get("guilds")
        user_id = json_data.get("user")
        if not guild_ids:
            return HTTPException(status_code=400, detail="No guilds specified")

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

                permission_level = 0
                if await management_check(self.bot, guild, user):
                    permission_level = 2
                elif await staff_check(self.bot, guild, user):
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

        return guilds

    async def POST_check_staff_level(self, request: Request):
        json_data = await request.json()
        guild_id = json_data.get("guild")
        user_id = json_data.get("user")
        if not guild_id or not user_id:
            return HTTPException(status_code=400, detail="Invalid guild")

        try:
            guild = await self.bot.fetch_guild(guild_id)
        except (discord.Forbidden, discord.HTTPException):
            return HTTPException(status_code=400, detail="Invalid guild")

        try:
            user = await guild.fetch_member(user_id)
        except (discord.Forbidden, discord.HTTPException):
            return {"permission_level": 0}

        permission_level = 0
        if await management_check(self.bot, guild, user):
            permission_level = 2
        elif await staff_check(self.bot, guild, user):
            permission_level = 1


        return {"permission_level": permission_level}

    async def POST_get_guild_settings(self, request: Request):
        json_data = await request.json()
        guild_id = json_data.get("guild")
        if not guild_id:
            return HTTPException(status_code=400, detail="Invalid guild")
        guild: discord.Guild = self.bot.get_guild(int(guild_id))
        settings = await self.bot.settings.find_by_id(guild.id)
        if not settings:
            return HTTPException(status_code=400, detail="Invalid guild")

        return settings

    async def POST_update_guild_settings(self, request: Request):
        json_data = await request.json()
        guild_id = json_data.get("guild")

        for key, value in json_data.items():
            if key == "guild":
                continue
            if isinstance(value, dict):
                settings = await self.bot.settings.find_by_id(guild_id)
                if not settings:
                    return HTTPException(status_code=400, detail="Invalid guild")
                for k, v in value.items():
                    settings[key][k] = v
        await self.bot.settings.update_by_id(settings)

        if not guild_id:
            return HTTPException(status_code=400, detail="Invalid guild")
        guild: discord.Guild = self.bot.get_guild(int(guild_id))
        settings = await self.bot.settings.find_by_id(guild.id)
        if not settings:
            return HTTPException(status_code=404, detail="Guild does not have settings attribute")

        return settings


    async def POST_get_guild_roles(self, request: Request):
        json_data = await request.json()
        guild_id = json_data.get("guild")

        if not guild_id:
            return HTTPException(status_code=400, detail="Invalid guild")
        guild: discord.Guild = self.bot.get_guild(int(guild_id))



        return [{
            "name": role.name,
            "id": role.id,
            "color": str(role.color)
        } for role in guild.roles]

    async def POST_get_guild_channels(self, request: Request):
        json_data = await request.json()
        guild_id = json_data.get("guild")

        if not guild_id:
            return HTTPException(status_code=400, detail="Invalid guild")
        guild: discord.Guild = self.bot.get_guild(int(guild_id))

        return [{
            "name": channel.name,
            "id": channel.id,
            "type": channel.type
        } for channel in guild.channels]

    async def POST_get_last_warnings(self, request):
        json_data = await request.json()
        guild_id = json_data.get("guild")
        # NOTE: This API is deprecated.
        return HTTPException(status_code=500, detail="This API is deprecated")

        # warning_objects = {}
        # async for document in self.bot.warnings.db.find(
        #         {"Guild": guild_id}
        # ).sort([("$natural", -1)]).limit(10):
        #     warning_objects[document["_id"]] = list(
        #         filter(lambda x: x["Guild"] == guild_id, document["warnings"])
        #     )

        # return warning_objects

    async def GET_get_token(
        self, authorization: Annotated[str | None, Header()], request: Request
    ):
        """

        Generates a token for the API. Requires an unspecified private key.

        :param authorization:
        :param request:
        :return:
        """

        if authorization != config("API_PRIVATE_KEY"):
            raise HTTPException(status_code=401, detail="Invalid authorization")
        has_token = await self.bot.api_tokens.find_by_id(request.client.host)
        if has_token:
            if not int(datetime.datetime.now().timestamp()) > has_token["expires_at"]:
                return has_token
       # # print(request)
        generated = tokenGenerator()
        object = {
            "_id": request.client.host,
            "token": generated,
            "created_at": int(datetime.datetime.now().timestamp()),
            "expires_at": int(datetime.datetime.now().timestamp()) + 2.592e6,
        }

        await self.bot.api_tokens.upsert(object)

        return object

    async def POST_authorize_token(
        self,
        authorization: Annotated[str | None, Header()],
        x_link_string: Annotated[str | None, Header()],
    ):
        """

        Authorizes a token for the API, and links a Discord server to the token. Requires a token and a transfer string, which is placed in the X-Link-String header.

        :param authorization:
        :param x_link_string:
        :return:
        """
        if not authorization:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        if not await validate_authorization(
            self.bot, authorization, disable_static_tokens=True
        ):
            raise HTTPException(
                status_code=401, detail="Invalid or expired authorization."
            )
        token_obj = await self.bot.api_tokens.db.find_one({"token": authorization})

        if not x_link_string:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        link_string_obj = await self.bot.link_strings.db.find_one(
            {"_id": x_link_string}
        )

        if not link_string_obj:
            raise HTTPException(status_code=401, detail="Invalid link string")

        link_string_obj["token"] = authorization
        link_string_obj["ip"] = token_obj["_id"]
        link_string_obj["link_string"] = link_string_obj["_id"]
        await self.bot.link_strings.update_by_id(link_string_obj)

        token_obj["link_string"] = link_string_obj["_id"]
        await self.bot.api_tokens.update_by_id(token_obj)

        return link_string_obj

    async def GET_get_link_string(
        self, authorization: Annotated[str | None, Header()], request: Request
    ):
        """
        Given an authorization token as a header, returns a dictionary with information about the token.

        Parameters:
            authorization (str | None): The authorization token to be verified.
            request (fastapi.Request): The incoming HTTP request.

        Raises:
            HTTPException: If the authorization token is missing, invalid, or has expired.

        Returns:
            dict: A dictionary containing information about the authorization token, such as the token string,
                  its expiration timestamp, and any other associated data.
        """
        if not authorization:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        token_obj = await self.bot.api_tokens.db.find_one({"token": authorization})

        if not token_obj:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        if int(datetime.datetime.now().timestamp()) > token_obj["expires_at"]:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        return token_obj

    async def GET_get_current_token(self, request: Request):
        """
        Given the client host IP, returns a dictionary with information about the token.

        Parameters:
            request (fastapi.Request): The incoming HTTP request.

        Raises:
            HTTPException: If the authorization token is missing, invalid, or has expired.

        Returns:
            dict: A dictionary containing information about the authorization token, such as the token string,
                  its expiration timestamp, and any other associated data.
        """

        token_obj = await self.bot.api_tokens.db.find_one({"_id": request.client.host})
        ## print(token_obj)
        # print(request.client.host)
        if not token_obj:
            raise HTTPException(
                status_code=404, detail="Could not find token associated with IP"
            )

        return token_obj

    async def GET_get_online_staff(
        self, authorization: Annotated[str | None, Header()], request: Request
    ):
        # Use the self.bot.shifts to get all current shifts for the guild ID associated with the link string associated with the token
        if not authorization:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        token_obj = await self.bot.api_tokens.db.find_one({"token": authorization})

        if not token_obj:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        if int(datetime.datetime.now().timestamp()) > token_obj["expires_at"]:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        link_string_obj = await self.bot.link_strings.db.find_one(
            {"_id": token_obj["link_string"]}
        )

        if not link_string_obj:
            raise HTTPException(status_code=401, detail="Invalid link string")

        guild = self.bot.get_guild(link_string_obj["guild"])

        if not guild:
            raise HTTPException(status_code=404, detail="Guild not found")

        shifts = []
        async for doc in self.bot.shift_management.shifts.db.find(
            {"data": {"$elemMatch": {"guild": link_string_obj["guild"]}}}
        ):
            item = [
                *list(
                    filter(
                        lambda x: (x or {}).get("guild") == link_string_obj["guild"],
                        doc["data"],
                    )
                )
            ][0]
            item["discord"] = doc["_id"]
            fivem_link = await self.bot.fivem_links.db.find_one(
                {"_id": item["discord"]}
            )
            item["fivem"] = (fivem_link or {}).get("steam_id")
            shifts.append(item)

        return shifts

    async def POST_get_discord(
        self,
        authorization: Annotated[str | None, Header()],
        body: Identification,
        request: Request,
    ):
        if not authorization:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        token_obj = await self.bot.api_tokens.db.find_one({"token": authorization})

        if not token_obj:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        if int(datetime.datetime.now().timestamp()) > token_obj["expires_at"]:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        link_string_obj = await self.bot.link_strings.db.find_one(
            {"_id": token_obj["link_string"]}
        )

        if not link_string_obj:
            raise HTTPException(status_code=401, detail="Invalid link string")

        if not body or not body.license:
            raise HTTPException(status_code=400, detail="Missing license")

        fivem_link = await self.bot.fivem_links.db.find_one({"license": body.license})
        return (
            {"status": "success"}.update(fivem_link)
            if fivem_link
            else {"status": "failed"}
        )

    async def POST_get_fivem(
        self, authorization: Annotated[str | None, Header()], request: Request
    ):
        if not authorization:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        token_obj = await self.bot.api_tokens.db.find_one({"token": authorization})

        if not token_obj:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        if int(datetime.datetime.now().timestamp()) > token_obj["expires_at"]:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        link_string_obj = await self.bot.link_strings.db.find_one(
            {"_id": token_obj["link_string"]}
        )

        if not link_string_obj:
            raise HTTPException(status_code=401, detail="Invalid link string")

        body = await request.json()
        if not body or not body.get("discord_id"):
            raise HTTPException(status_code=400, detail="Missing discord_id")

        fivem_link = await self.bot.fivem_links.db.find_one({"_id": body["discord_id"]})
        return (
            {"status": "success"}.update(fivem_link)
            if fivem_link
            else {"status": "failed"}
        )

    async def POST_duty_on_actions(
            self, authorization: Annotated[str | None, Header()],
            request: Request
    ):
        if not authorization:
            return HTTPException(status_code=401, detail="Invalid authorization")

        base_auth = await validate_authorization(self.bot, authorization, disable_static_tokens=False)
        if not base_auth:
            return HTTPException(status_code=401, detail="Invalid authorization")
        data = request.query_params.get("ObjectId")
        if not data:
            return HTTPException(status_code=400, detail="Didn't provide 'ObjectId' parameter.")
        print(502)

        dataobject = await self.bot.shift_management.shifts.db.find_one({'_id': ObjectId(data)})
        guild = await self.bot.fetch_guild(dataobject["Guild"])
        staff_member = await guild.fetch_member(dataobject['UserID'])
        guild_settings = await self.bot.settings.find_by_id(guild.id)
        configItem = guild_settings
        shift_types = (guild_settings.get('shift_types') or {}).get('types')
        mapped = {}

        print(513)

        if not shift_types:
            shift_type = None
        else:
            for i in shift_types:
                mapped[i['name']] = i

        if len(mapped) != 0:
            if dataobject['Type'] in mapped.keys():
                shift_type = mapped[dataobject['Type']]

        print(524)

        embed = discord.Embed(
            title=f"<:ERMAdd:1113207792854106173> Shift Started", color=0xED4348
        )
        try:
            embed.set_thumbnail(url=staff_member.display_avatar.url)
            embed.set_footer(text="Staff Logging Module")
            embed.set_author(
                name=staff_member.name,
                icon_url=staff_member.display_avatar.url,
            )
        except:
            pass

        if shift_type:
            embed.add_field(
                name="<:ERMList:1111099396990435428> Type",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Clocking in. **({shift_type['name']})**",
                inline=False,
            )
        else:
            embed.add_field(
                name="<:ERMList:1111099396990435428> Type",
                value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Clocking in.",
                inline=False,
            )
        embed.add_field(
            name="<:ERMList:1111099396990435428> Current Time",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912><t:{int(datetime.datetime.now(tz=pytz.UTC).timestamp())}>",
            inline=False,
        )

        print(557)

        print(configItem['shift_management']['channel'])
        shift_channel = self.bot.get_channel(configItem["shift_management"]["channel"])
            
        print(563)
        print(shift_channel)
        if shift_channel is None:
            return HTTPException(status_code=400)
        print('!!!!')
        print(shift_channel)
        await shift_channel.send(embed=embed)

        nickname_prefix = None
        changed_nick = False
        if shift_type:
            if shift_type.get("nickname"):
                nickname_prefix = shift_type.get("nickname")
        else:
            if configItem["shift_management"].get("nickname_prefix"):
                nickname_prefix = configItem["shift_management"].get(
                    "nickname_prefix"
                )

        if nickname_prefix:
            current_name = (
                staff_member.nick if staff_member.nick else staff_member.name
            )
            new_name = "{}{}".format(nickname_prefix, current_name)

            try:
                await staff_member.edit(nick=new_name)
                changed_nick = True
            except Exception as e:
                pass
        role = None

        if shift_type:
            if shift_type.get("role"):
                if isinstance(shift_type.get("role"), list):
                    role = [
                        discord.utils.get(guild.roles, id=rl)
                        for rl in shift_type.get("role")
                    ]
                else:
                    role = [
                        discord.utils.get(
                            guild.roles, id=shift_type.get("role")
                        )
                    ]
        else:
            if configItem["shift_management"]["role"]:
                if not isinstance(configItem["shift_management"]["role"], list):
                    role = [
                        discord.utils.get(
                            guild.roles,
                            id=configItem["shift_management"]["role"],
                        )
                    ]
                else:
                    role = [
                        discord.utils.get(guild.roles, id=role)
                        for role in configItem["shift_management"]["role"]
                    ]
        if role:
            for rl in role:
                if rl not in staff_member.roles and rl is not None:
                    try:
                        await staff_member.add_roles(rl)
                    except:
                        pass

        return 200


    async def POST_duty_off_actions(self,
        authorization: Annotated[str | None, Header()],
        request: Request
    ):
        if not authorization:
            return HTTPException(status_code=401, detail="Invalid authorization")

        base_auth = await validate_authorization(self.bot, authorization, disable_static_tokens=False)
        if not base_auth:
            return HTTPException(status_code=401, detail="Invalid authorization")
        data = request.query_params.get("ObjectId")
        if not data:
            return HTTPException(status_code=400, detail="Didn't provide 'ObjectId' parameter.")


        dataobject = await self.bot.shift_management.shifts.db.find_one({'_id': ObjectId(data)})
        guild = await self.bot.fetch_guild(dataobject["Guild"])
        staff_member = await guild.fetch_member(dataobject['UserID'])
        guild_settings = await self.bot.settings.find_by_id(guild.id)
        configItem = guild_settings
        shift_types = (guild_settings.get('shift_types') or {}).get('types')
        mapped = {}


        if not shift_types:
            shift_type = None
        else:
            for i in shift_types:
                mapped[i['name']] = i

        if len(mapped) != 0:
            if dataobject['Type'] in mapped.keys():
                shift_type = mapped[dataobject['Type']]
        bot = self.bot
        shift = dataobject
        member = staff_member

        break_seconds = 0
        if shift:
            if shift["Guild"] != guild.id:
                shift = None

            if shift:
                for index, item in enumerate(shift["Breaks"].copy()):
                    if item["EndEpoch"] == 0:
                        item["EndEpoch"] = datetime.datetime.now(tz=pytz.UTC)
                        shift["Breaks"][index] = item

                    startTimestamp = item["StartEpoch"]
                    endTimestamp = item["EndEpoch"]
                    break_seconds += int(endTimestamp - startTimestamp)

        nickname = None
        if shift.get("Type") is not None:
            settings = await bot.settings.get_settings(guild.id)
            shift_types = None
            if settings.get("shift_types"):
                shift_types = settings["shift_types"].get("types", [])
            else:
                shift_types = []
            for s in shift_types:
                if s["name"] == shift.get("Type"):
                    shift_type = s
                    nickname = s["nickname"] if s.get("nickname") else None
        if nickname is None:
            nickname = settings["shift_management"].get(
                "nickname_prefix", ""
            )
        if nickname in str(member.nick):
            try:
                await member.edit(nick=member.nick.replace(nickname, ""))
            except Exception as e:
                pass

        embed = discord.Embed(
            title=f"<:ERMRemove:1113207777662345387> Shift Ended", color=0xED4348
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Staff Logging Module")
        embed.set_author(
            name=member.name,
            icon_url=member.display_avatar.url,
        )

        if shift.get("Type") != "Default":
            embed.add_field(
                name="<:ERMList:1111099396990435428> Type",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Clocking out. **({shift_type.get('name')})**",
                inline=False,
            )
        else:
            embed.add_field(
                name="<:ERMList:1111099396990435428> Type",
                value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Clocking out.",
                inline=False,
            )

        time_delta = datetime.datetime.now(tz=pytz.UTC) - datetime.datetime.fromtimestamp(
            shift["StartEpoch"], tz=pytz.UTC
        )

        added_seconds = 0
        removed_seconds = 0
        if "AddedTime" in shift.keys():
            added_seconds = shift["AddedTime"]
        if "RemovedTime" in shift.keys():
            removed_seconds = shift["RemovedTime"]

        if break_seconds > 0:
            embed.add_field(
                name="<:ERMList:1111099396990435428> Type",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(time_delta)} **({td_format(datetime.timedelta(seconds=break_seconds))})** on break",
                inline=False,
            )
        else:
            embed.add_field(
                name="<:ERMList:1111099396990435428> Elapsed Time",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(time_delta)}",
                inline=False,
            )

        shift_channel = self.bot.get_channel(configItem["shift_management"]["channel"])

        if shift_channel is None:
            return

        await shift_channel.send(embed=embed)

        if shift.get("Nickname"):
            if shift.get("Nickname") == member.nick:
                nickname = None
                if shift.get("Type") is not None:
                    settings = await bot.settings.get_settings(guild.id)
                    if settings.get("shift_types"):
                        shift_types = settings["shift_types"].get("types", [])
                    else:
                        shift_types = []
                    for s in shift_types:
                        if s["name"] == shift.get("Type"):
                            shift_type = s
                            nickname = s["nickname"] if s.get("nickname") else None
                if nickname is None:
                    nickname = settings["shift_management"].get(
                        "nickname_prefix", ""
                    )
                try:
                    await member.edit(nick=member.nick.replace(nickname, ""))
                except Exception as e:
                    pass
        role = None
        if shift_type:
            if shift_type.get("role"):
                role = [
                    discord.utils.get(guild.roles, id=role)
                    for role in shift_type.get("role")
                ]
        else:
            if configItem["shift_management"]["role"]:
                if not isinstance(configItem["shift_management"]["role"], list):
                    role = [
                        discord.utils.get(
                            guild.roles,
                            id=configItem["shift_management"]["role"],
                        )
                    ]
                else:
                    role = [
                        discord.utils.get(guild.roles, id=role)
                        for role in configItem["shift_management"]["role"]
                    ]

        if role:
            for rl in role:
                if rl in member.roles and rl is not None:
                    try:
                        await member.remove_roles(rl)
                    except:
                        pass
        return 200


    async def POST_duty_break_actions(self, authorization: Annotated[str | None, Header()], request: Request):
        if not authorization:
            return HTTPException(status_code=401, detail="Invalid authorization")

        base_auth = await validate_authorization(self.bot, authorization, disable_static_tokens=False)
        if not base_auth:
            return HTTPException(status_code=401, detail="Invalid authorization")
        data = request.query_params.get("ObjectId")
        if not data:
            return HTTPException(status_code=400, detail="Didn't provide 'ObjectId' parameter.")


        dataobject = await self.bot.shift_management.shifts.db.find_one({'_id': ObjectId(data)})
        guild = await self.bot.fetch_guild(dataobject["Guild"])
        staff_member = await guild.fetch_member(dataobject['UserID'])
        guild_settings = await self.bot.settings.find_by_id(guild.id)
        configItem = guild_settings
        shift_types = (guild_settings.get('shift_types') or {}).get('types')
        mapped = {}


        if not shift_types:
            shift_type = None
        else:
            for i in shift_types:
                mapped[i['name']] = i

        if len(mapped) != 0:
            if dataobject['Type'] in mapped.keys():
                shift_type = mapped[dataobject['Type']]
        bot = self.bot
        shift = dataobject
        member = staff_member

        nickname = None
        if shift.get("Type") is not None:
            settings = await bot.settings.get_settings(guild.id)
            shift_types = None
            if settings.get("shift_types"):
                shift_types = settings["shift_types"].get("types", [])
            else:
                shift_types = []
            for s in shift_types:
                if s["name"] == shift.get("Type"):
                    shift_type = s
                    nickname = s["nickname"] if s.get("nickname") else None
        if nickname is None:
            nickname = settings["shift_management"].get(
                "nickname_prefix", ""
            )
        if nickname in str(member.nick):
            try:
                await member.edit(nick=member.nick.replace(nickname, ""))
            except Exception as e:
                pass

        role = []
        if shift_type:
            if shift_type.get("role"):
                role = [
                    discord.utils.get(guild.roles, id=role)
                    for role in shift_type.get("role")
                ]
        else:
            if configItem["shift_management"]["role"]:
                if not isinstance(configItem["shift_management"]["role"], list):
                    role = [
                        discord.utils.get(
                            guild.roles,
                            id=configItem["shift_management"]["role"],
                        )
                    ]
                else:
                    role = [
                        discord.utils.get(guild.roles, id=role)
                        for role in configItem["shift_management"]["role"]
                    ]

        if role is not None:
            for rl in role:
                if rl in member.roles and rl is not None:
                    try:
                        await member.remove_roles(rl)
                    except:
                        pass

        return 200

    async def POST_duty_end_break_actions(self, authorization: Annotated[str | None, Header()], request: Request):
        if not authorization:
            return HTTPException(status_code=401, detail="Invalid authorization")

        base_auth = await validate_authorization(self.bot, authorization, disable_static_tokens=False)
        if not base_auth:
            return HTTPException(status_code=401, detail="Invalid authorization")
        data = request.query_params.get("ObjectId")
        if not data:
            return HTTPException(status_code=400, detail="Didn't provide 'ObjectId' parameter.")


        dataobject = await self.bot.shift_management.shifts.db.find_one({'_id': ObjectId(data)})
        guild = await self.bot.fetch_guild(dataobject["Guild"])
        staff_member = await guild.fetch_member(dataobject['UserID'])
        guild_settings = await self.bot.settings.find_by_id(guild.id)
        configItem = guild_settings
        shift_types = (guild_settings.get('shift_types') or {}).get('types')
        mapped = {}
        shift_type = None


        if not shift_types:
            shift_type = None
        else:
            for i in shift_types:
                mapped[i['name']] = i

        if len(mapped) != 0:
            if dataobject['Type'] in mapped.keys():
                shift_type = mapped[dataobject['Type']]
        bot = self.bot
        shift = dataobject
        member = staff_member

        nickname_prefix = None
        changed_nick = False
        role = None

        if shift_type:
            if shift_type.get("nickname"):
                nickname_prefix = shift_type.get("nickname")
        else:
            if configItem["shift_management"].get("nickname_prefix"):
                nickname_prefix = configItem["shift_management"].get("nickname_prefix")

        if nickname_prefix:
            current_name = member.nick if member.nick else member.name
            new_name = "{}{}".format(nickname_prefix, current_name)

            try:
                await member.edit(nick=new_name)
                changed_nick = True
            except Exception as e:
                # # print(e)
                pass

        if shift_type:
            if shift_type.get("role"):
                role = [
                    discord.utils.get(guild.roles, id=role)
                    for role in shift_type.get("role")
                ]
        else:
            if configItem["shift_management"]["role"]:
                if not isinstance(configItem["shift_management"]["role"], list):
                    role = [
                        discord.utils.get(
                            guild.roles,
                            id=configItem["shift_management"]["role"],
                        )
                    ]
                else:
                    role = [
                        discord.utils.get(guild.roles, id=role)
                        for role in configItem["shift_management"]["role"]
                    ]

        if role:
            for rl in role:
                if not rl in member.roles and rl is not None:
                    try:
                        await member.add_roles(rl)
                    except:
                        pass
        return 200

    async def POST_duty_voided_actions(self, authorization: Annotated[str | None, Header()], request: Request):
        if not authorization:
            return HTTPException(status_code=401, detail="Invalid authorization")

        base_auth = await validate_authorization(self.bot, authorization, disable_static_tokens=False)

        if not base_auth:
            return HTTPException(status_code=401, detail="Invalid authorization")
        data = request.query_params.get("ObjectId")
        if not data:
            return HTTPException(status_code=400, detail="Didn't provide 'ObjectId' parameter.")


        dataobject = await self.bot.shift_management.shifts.db.find_one({'_id': ObjectId(data)})
        guild = await self.bot.fetch_guild(dataobject["Guild"])
        staff_member = await guild.fetch_member(dataobject['UserID'])
        guild_settings = await self.bot.settings.find_by_id(guild.id)
        configItem = guild_settings
        shift_types = (guild_settings.get('shift_types') or {}).get('types')
        mapped = {}
        shift_type = None


        if not shift_types:
            shift_type = None
        else:
            for i in shift_types:
                mapped[i['name']] = i

        if len(mapped) != 0:
            if dataobject['Type'] in mapped.keys():
                shift_type = mapped[dataobject['Type']]
        bot = self.bot
        shift = dataobject
        member = staff_member

        nickname_prefix = None
        changed_nick = False
        role = None

        embed = discord.Embed(
            title=f"<:ERMTrash:1111100349244264508> Voided Time", color=0xED4348
        )

        if shift.get("Nickname"):
            if shift.get("Nickname") == member.nick:
                nickname = None
                if shift.get("Type") is not None:
                    settings = await bot.settings.get_settings(guild.id)
                    shift_types = None
                    if settings.get("shift_types"):
                        shift_types = settings["shift_types"].get("types", [])
                    else:
                        shift_types = []
                    for s in shift_types:
                        if s["name"] == shift.get("Type"):
                            shift_type = s
                            nickname = s["nickname"] if s.get("nickname") else None
                if nickname is None:
                    nickname = settings["shift_management"].get(
                        "nickname_prefix", ""
                    )
                try:
                    await member.edit(
                        nick=member.nick.replace(nickname, "")
                    )
                except Exception as e:
                    pass
        try:
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_author(
                name=member.name,
                icon_url=member.display_avatar.url,
            )
        except:
            pass
        embed.add_field(
            name="<:ERMList:1111099396990435428> Type",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Voided time.",
            inline=False,
        )

        embed.add_field(
            name="<:ERMList:1111099396990435428> Elapsed Time",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{td_format(datetime.datetime.now(tz=pytz.UTC) - datetime.datetime.fromtimestamp(shift['StartEpoch'], tz=pytz.UTC))}",
            inline=False,
        )

        embed.set_footer(text="Staff Logging Module")

        sh = await bot.shift_management.get_current_shift(member, guild.id)
        await bot.shift_management.shifts.delete_by_id(sh["_id"])


        shift_channel = self.bot.get_channel(configItem["shift_management"]["channel"])

        if shift_channel is None:
            return

        await shift_channel.send(embed=embed)

        role = None
        if shift_type:
            if shift_type.get("role"):
                role = [
                    discord.utils.get(guild.roles, id=role)
                    for role in shift_type.get("role")
                ]
        else:
            if configItem["shift_management"]["role"]:
                if not isinstance(configItem["shift_management"]["role"], list):
                    role = [
                        discord.utils.get(
                            guild.roles,
                            id=configItem["shift_management"]["role"],
                        )
                    ]
                else:
                    role = [
                        discord.utils.get(guild.roles, id=role)
                        for role in configItem["shift_management"]["role"]
                    ]

        if role:
            for rl in role:
                if rl in member.roles and rl is not None:
                    try:
                        await member.remove_roles(rl)
                    except:
                        pass
        return 200

    async def POST_punishment_logged(self, authorization: Annotated[str | None, Header()], request: Request):
        if not authorization:
            return HTTPException(status_code=401, detail="Invalid authorization")

        base_auth = await validate_authorization(self.bot, authorization, disable_static_tokens=False)
        print(base_auth)
        if not base_auth:
            return HTTPException(status_code=401, detail="Invalid authorization")
        data = request.query_params.get("ObjectId")
        if not data:
            return HTTPException(status_code=400, detail="Didn't provide 'ObjectId' parameter.")

        dataobject = await self.bot.punishments.db.find_one({'_id': ObjectId(data)})
        guild = await self.bot.fetch_guild(dataobject["Guild"])
        staff_member = await guild.fetch_member(dataobject['ModeratorID'])
        guild_settings = await self.bot.settings.find_by_id(guild.id)
        configItem = guild_settings
        settings = configItem
        warning_types = (await self.bot.punishment_types.get_punishment_types(guild.id))

        type = dataobject['Type']
        bot = self.bot
        designated_channel = None

        if settings:
            warning_type = None
            designated_channel = None
            for warning in warning_types:
                if isinstance(warning, str):
                    if warning.lower() == type.lower():
                        warning_type = warning
                elif isinstance(warning, dict):
                    if warning["name"].lower() == type.lower():
                        warning_type = warning

            if isinstance(warning_type, str):
                if settings["customisation"].get("kick_channel"):
                    if settings["customisation"]["kick_channel"] != "None":
                        if type.lower() == "kick":
                            designated_channel = bot.get_channel(
                                settings["customisation"]["kick_channel"]
                            )
                if settings["customisation"].get("ban_channel"):
                    if settings["customisation"]["ban_channel"] != "None":
                        if type.lower() == "ban":
                            designated_channel = bot.get_channel(
                                settings["customisation"]["ban_channel"]
                            )
                if settings["customisation"].get("bolo_channel"):
                    if settings["customisation"]["bolo_channel"] != "None":
                        if type.lower() == "bolo":
                            designated_channel = bot.get_channel(
                                settings["customisation"]["bolo_channel"]
                            )
            else:
                if isinstance(warning_type, dict):
                    if "channel" in warning_type.keys():
                        if warning_type["channel"] != "None":
                            designated_channel = bot.get_channel(
                                warning_type["channel"]
                            )


        shift = dataobject
        member = staff_member
        avatar = None

        async with aiohttp.ClientSession() as session:
            async with session.get(
                    f"https://thumbnails.roblox.com/v1/users/avatar?userIds={dataobject['UserID']}&size=420x420&format=Png"
            ) as f:
                if f.status == 200:
                    avatar = await f.json()
                    avatar = avatar["data"][0]["imageUrl"]
                else:
                    avatar = ""

        embed = discord.Embed(
            title="<:ERMAdd:1113207792854106173> Punishment Logged", color=0xED4348
        )
        embed.set_thumbnail(url=avatar)
        embed.set_author(
            name=member.name,
            icon_url=member.display_avatar.url,
        )
        try:
            embed.set_footer(text="Staff Logging Module")
        except:
            pass
        embed.add_field(
            name="<:ERMList:1111099396990435428> Staff Member",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> {member.mention}",
            inline=False,
        )
        embed.add_field(
            name="<:ERMList:1111099396990435428> Violator",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> {dataobject['Username']}",
            inline=False,
        )
        embed.add_field(
            name="<:ERMList:1111099396990435428> Type",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> {type.lower().title()}",
            inline=False,
        )
        embed.add_field(
            name="<:ERMList:1111099396990435428> Reason",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> {dataobject['Reason']}",
            inline=False,
        )

        if designated_channel is None:
            print(configItem['punishments']['channel'])
            designated_channel = bot.get_channel(configItem['punishments']['channel'])


        shift = await bot.shift_management.get_current_shift(
            member, guild.id
        )
        if shift:
            shift["Moderations"].append(data)
            await bot.shift_management.shifts.update_by_id(shift)

        success = (
            discord.Embed(
                title=f"{dataobject['Username']}",
                description=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Reason:** {dataobject['Reason']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Type:** {type.lower().title()}",
                color=0xED4348,
            )
            .set_author(
                name=member.name, icon_url=member.display_avatar.url
            )
            .set_thumbnail(url=avatar)
        )

        roblox_id = dataobject['UserID']

        discord_user = None
        async for document in bot.synced_users.db.find({"roblox": roblox_id}):
            discord_user = document["_id"]

        if discord_user:
            try:
                member = await guild.fetch_member(discord_user)
            except discord.NotFound:
                member = None

            if member:
                should_dm = True

                async for doc in bot.consent.db.find({"_id": member.id}):
                    if doc.get("punishments"):
                        if document.get("punishments") is False:
                            should_dm = False

                if should_dm:
                    try:
                        personal_embed = discord.Embed(
                            title="<:ERMPunish:1111095942075138158> You have been moderated!",
                            description=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>***{guild.name}** has moderated you in-game*",
                            color=0xED4348,
                        )
                        personal_embed.add_field(
                            name="<:ERMList:1111099396990435428> Moderation Details",
                            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Username:** {dataobject['Username']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Reason:** {dataobject['Reason']}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Type:** {type.lower().title()}",
                            inline=False,
                        )

                        try:
                            personal_embed.set_author(
                                name=guild.name, icon_url=guild.icon.url
                            )
                        except:
                            personal_embed.set_author(name=guild.name)

                        await member.send(
                            embed=personal_embed,
                            content=f"<:ERMAlert:1113237478892130324>  **{member.name}**, you have been moderated inside of **{guild.name}**.",
                        )

                    except:
                        pass

    
        await designated_channel.send(embed=embed)
    

        return 200


    async def POST_duty_on(
        self,
        authorization: Annotated[str | None, Header()],
        identification: Identification,
        request: Request,
    ):
        # print(request)
        # print(await request.json())
        # print("REQUEST ^^")
        if not authorization:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        token_obj = await self.bot.api_tokens.db.find_one({"token": authorization})

        if not token_obj:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        if int(datetime.datetime.now().timestamp()) > token_obj["expires_at"]:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        link_string_obj = await self.bot.link_strings.db.find_one(
            {"_id": token_obj["link_string"]}
        )

        if not link_string_obj:
            raise HTTPException(status_code=401, detail="Invalid link string")

        guild = self.bot.get_guild(link_string_obj["guild"])

        if not guild:
            raise HTTPException(status_code=404, detail="Guild not found")

        body = await request.json()

        if not body:
            raise HTTPException(status_code=400, detail="No body provided")

        if not body.get("steam_id"):
            raise HTTPException(status_code=400, detail="No steam ID provided")

        # print(body)
        fivem_link = await self.bot.fivem_links.db.find_one(
            {"steam_id": body["steam_id"]}
        )

        if not fivem_link:
            raise HTTPException(status_code=404, detail="Could not find FiveM link")

        if not fivem_link.get("_id"):
            raise HTTPException(status_code=404, detail="Could not find FiveM link")

        try:
            member = await guild.fetch_member(fivem_link["_id"])
        except discord.NotFound:
            raise HTTPException(status_code=404, detail="Could not find Discord member")

        settings = await self.bot.settings.find_by_id(guild.id)
        if not settings:
            raise HTTPException(status_code=404, detail="Could not find settings")

        if settings.get("shift_types"):
            available_shift_types = []
            for shift_type in settings["shift_types"]:
                available_shift_types.append(shift_type["id"])

        if not body.get("shift_type"):
            await self.bot.shift_management.add_shift_by_user(member, {"guild": guild})
        else:
            if body["shift_type"] not in available_shift_types:
                raise HTTPException(status_code=400, detail="Invalid shift type")
            await self.bot.shift_management.add_shift_by_user(
                member, {"guild": guild, "shift_type": body["shift_type"]}
            )

        return {
            "status": "success",
            "member": member.id,
            "shift_type": body.get("shift_type"),
        }

    async def POST_duty_off(
        self, authorization: Annotated[str | None, Header()], request: Request
    ):
        if not authorization:
            raise HTTPException(status_code=401, detail="Invalid authorization")
        
        if not await validate_authorization(
            self.bot, authorization, disable_static_tokens=False
        ):
            raise HTTPException(
                status_code=401, detail="Invalid or expired authorization."
            )

        token_obj = await self.bot.api_tokens.db.find_one({"token": authorization})

        if token_obj:
            link_string_obj = await self.bot.link_strings.db.find_one(
                {"_id": token_obj["link_string"]}
            )

            if not link_string_obj:
                raise HTTPException(status_code=401, detail="Invalid link string")

            guild = self.bot.get_guild(link_string_obj["guild"])
        else:
            data = await request.json()
            guild = data['guild']

        if not guild:
            raise HTTPException(status_code=404, detail="Guild not found")

        body = await request.json()

        if not body:
            raise HTTPException(status_code=400, detail="No body provided")

        if token_obj:
            if not body.get("steam_id"):
                raise HTTPException(status_code=400, detail="No steam ID provided")

            fivem_link = await self.bot.fivem_links.db.find_one(
                {"steam_id": body["steam_id"]}
            )

            if not fivem_link:
                raise HTTPException(status_code=404, detail="Could not find FiveM link")

            if not fivem_link.get("_id"):
                raise HTTPException(status_code=404, detail="Could not find FiveM link")

        try:
            member = await guild.fetch_member(fivem_link["_id"])
        except discord.NotFound:
            raise HTTPException(status_code=404, detail="Could not find Discord member")

        settings = await self.bot.settings.find_by_id(guild.id)
        if not settings:
            raise HTTPException(status_code=404, detail="Could not find settings")

        shifts = await self.bot.shift_management.shifts.find_by_id(member.id)
        if not shifts:
            raise HTTPException(status_code=404, detail="Could not find user shifts")

        associated_shift = list(
            filter(lambda x: (x or {}).get("guild") == guild.id, shifts["data"])
        )
        if not associated_shift or len(associated_shift) == 0:
            raise HTTPException(status_code=404, detail="Could not find user shifts")
        else:
            associated_shift = associated_shift[0]

        await self.bot.shift_management.remove_shift_by_user(
            member, {"guild": guild, "shift": associated_shift}
        )



api = FastAPI()


class ServerAPI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def start_server(self):
        api.include_router(APIRoutes(self.bot).router)
        self.config = uvicorn.Config("utils.api:api", port=5000, log_level="info", host="0.0.0.0")
        self.server = uvicorn.Server(self.config)
        await self.server.serve()

    async def stop_server(self):
        await self.server.shutdown()

    async def cog_load(self) -> None:
        # asyncio.run_coroutine_threadsafe(self.start_server(), self.bot.loop)
        try:
            await self.start_server()
        except:
            # print('REALLY BAD ERROR.')
            pass
    async def cog_unload(self) -> None:
        await self.stop_server()


async def setup(bot):
    await bot.add_cog(ServerAPI(bot))
