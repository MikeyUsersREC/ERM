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
from erm import Bot, management_predicate, is_staff, staff_predicate, staff_check, management_check, admin_check
from typing import Annotated
from decouple import config
from utils.constants import BLANK_COLOR, GREEN_COLOR
from utils.utils import secure_logging
from pydantic import BaseModel

from utils.timestamp import td_format
# from helpers import MockContext
from utils.utils import tokenGenerator
import logging

logger = logging.getLogger(__name__)

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
           # # # print(i)
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
                   # # # print(e)
                    icon = "https://cdn.discordapp.com/embed/avatars/0.png?size=512"

                guilds.append(
                    {"id": str(guild.id), "name": str(guild.name), "icon_url": icon}
                )

        return {"guilds": guilds}

    async def GET_shard_pings(self, authorization: Annotated[str | None, Header()]):
        if not authorization:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        if not await validate_authorization(self.bot, authorization):
            raise HTTPException(status_code=401, detail="Invalid or expired authorization.")

        shard_pings = {}
        for shard_id, shard in self.bot.shards.items():
            shard_pings[shard_id] = round(shard.latency * 1000, 2)

        return {"shard_pings": shard_pings}

    async def GET_guild_shard(self, authorization: Annotated[str | None, Header()], guild_id: int):
        if not authorization:
            raise HTTPException(status_code=401, detail="Invalid authorization")

        if not await validate_authorization(self.bot, authorization):
            raise HTTPException(status_code=401, detail="Invalid or expired authorization.")

        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                raise HTTPException(status_code=404, detail="Guild not found")

            shard_id = guild.shard_id
            return {"guild_id": guild_id, "shard_id": shard_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

    async def POST_approve_application(
        self,
        authorization: Annotated[str | None, Header()],
        request: Request
    ):
        if not authorization:
            raise HTTPException(status_code=401, detail="Invalid authorization")
    
        if not await validate_authorization(self.bot, authorization):
            raise HTTPException(status_code=401, detail="Invalid or expired authorization.")
    
        try:
            json_data = await request.json()
            user_id = int(json_data["user"])
            add_role_ids = json_data.get("roles", [])
            remove_role_ids = json_data.get("remove_roles", [])
            guild_id = int(json_data["guild"])
            submitted_on = json_data.get("submitted", 1)
            note = json_data.get("note", "Not provided.")
            application_name = json_data.get("application_name")

            guild = self.bot.get_guild(guild_id)
            if not guild:
                raise HTTPException(status_code=400, detail="Invalid Guild ID")

            try:
                user = await guild.fetch_member(user_id)
            except discord.NotFound:
                raise HTTPException(status_code=400, detail="User not found in guild")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error fetching user: {str(e)}")

            embed = discord.Embed(
                title="<:success:1163149118366040106> Application Accepted",
                description=f"Your application in **{guild.name}** has been accepted. Congratulations!\n\n**Application Information**\n> **Application Name:** {application_name}\n> **Submitted On:** <t:{submitted_on}>\n> **Note:** {note}",
                color=GREEN_COLOR
            )
            
            try:
                await user.send(embed=embed)
            except discord.Forbidden:
                print(f"Could not send DM to user {user_id}")
            
            # Fetch and validate roles
            fetched_roles = await guild.fetch_roles()
            roles_to_add = []
            roles_to_remove = []
            
            # Process roles to add
            for role_id in add_role_ids:
                role = discord.utils.get(fetched_roles, id=int(role_id))
                if role:
                    roles_to_add.append(role)
            
            # Process roles to remove
            for role_id in remove_role_ids:
                role = discord.utils.get(fetched_roles, id=int(role_id))
                if role:
                    roles_to_remove.append(role)

            # Add roles
            if roles_to_add:
                try:
                    await user.add_roles(*roles_to_add, reason="Application approved - roles added")
                except discord.Forbidden:
                    raise HTTPException(status_code=403, detail="Bot lacks permission to manage roles")
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Error adding roles: {str(e)}")

            # Remove roles
            if roles_to_remove:
                try:
                    await user.remove_roles(*roles_to_remove, reason="Application approved - roles removed")
                except discord.Forbidden:
                    raise HTTPException(status_code=403, detail="Bot lacks permission to manage roles")
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Error removing roles: {str(e)}")

            return 200
                
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid data format: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


    async def POST_deny_application(
        self,
        authorization: Annotated[str | None, Header()],
        request: Request
    ):
        if not authorization:
            raise HTTPException(status_code=401, detail="Invalid authorization")
    
        if not await validate_authorization(self.bot, authorization):
            raise HTTPException(status_code=401, detail="Invalid or expired authorization.")
    
        try:
            json_data = await request.json()
            user_id = int(json_data["user"])
            add_role_ids = json_data.get("roles", [])
            remove_role_ids = json_data.get("remove_roles", [])
            guild_id = int(json_data["guild"])
            submitted_on = json_data.get("submitted", 1)
            note = json_data.get("note", "Not provided.")
            application_name = json_data.get("application_name")

            guild = self.bot.get_guild(guild_id)
            if not guild:
                raise HTTPException(status_code=400, detail="Invalid Guild ID")

            try:
                user = await guild.fetch_member(user_id)
            except discord.NotFound:
                raise HTTPException(status_code=400, detail="User not found in guild")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error fetching user: {str(e)}")

            embed = discord.Embed(
                title="Application Denied",
                description=f"Your application in **{guild.name}** has been denied.\n\n**Application Information**\n> **Application Name:** {application_name}\n> **Submitted On:** <t:{submitted_on}>\n> **Note:** {note}",
                color=BLANK_COLOR
            )
            
            try:
                await user.send(embed=embed)
            except discord.Forbidden:
                print(f"Could not send DM to user {user_id}")
            
            # Fetch and validate roles
            fetched_roles = await guild.fetch_roles()
            roles_to_add = []
            roles_to_remove = []
            
            # Process roles to add
            for role_id in add_role_ids:
                role = discord.utils.get(fetched_roles, id=int(role_id))
                if role:
                    roles_to_add.append(role)
            
            # Process roles to remove
            for role_id in remove_role_ids:
                role = discord.utils.get(fetched_roles, id=int(role_id))
                if role:
                    roles_to_remove.append(role)

            # Add roles
            if roles_to_add:
                try:
                    await user.add_roles(*roles_to_add, reason="Application denied - roles added")
                except discord.Forbidden:
                    raise HTTPException(status_code=403, detail="Bot lacks permission to manage roles")
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Error adding roles: {str(e)}")

            # Remove roles
            if roles_to_remove:
                try:
                    await user.remove_roles(*roles_to_remove, reason="Application denied - roles removed")
                except discord.Forbidden:
                    raise HTTPException(status_code=403, detail="Bot lacks permission to manage roles")
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Error removing roles: {str(e)}")

            return 200
                
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid data format: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    async def POST_accept_loa(
        self,
        authorization: Annotated[str | None, Header()],
        request: Request
    ):
        if not authorization:
            raise HTTPException(status_code=401, detail="Invalid authorization")
    
        if not await validate_authorization(self.bot, authorization):
            raise HTTPException(status_code=401, detail="Invalid or expired authorization.")
    
        json_data = await request.json()
        s_loa = json_data.get("loa") # dict { loa spec }
        roles = json_data.get("roles") # list[int]

        self.bot.dispatch("loa_accept", s_loa=s_loa, role_ids=roles)

        return 200
    
    async def POST_deny_loa(
        self,
        authorization: Annotated[str | None, Header()],
        request: Request
    ):
        if not authorization:
            raise HTTPException(status_code=401, detail="Invalid authorization")
    
        if not await validate_authorization(self.bot, authorization):
            raise HTTPException(status_code=401, detail="Invalid or expired authorization.")
    
        json_data = await request.json()
        s_loa = json_data.get("loa") # dict { loa spec }
        self.bot.dispatch("loa_deny", s_loa=s_loa)

        return 200


    async def POST_send_application_wave(
        self,
        authorization: Annotated[str | None, Header()],
        request: Request
    ):
        if not authorization:
            raise HTTPException(status_code=401, detail="Invalid authorization")
    
        if not await validate_authorization(self.bot, authorization):
            raise HTTPException(status_code=401, detail="Invalid or expired authorization.")
    
        json_data = await request.json()
        if not json_data.get("Channel"):
            return HTTPException(status_code=400, detail="Bad Format")
            
        channel = await self.bot.fetch_channel(json_data["Channel"])
        embed = discord.Embed(
            title="Application Results",
            description=f"The applications for **{json_data['ApplicationName']}** have been released!\n\n",
            color=BLANK_COLOR
        )
        embed_temp = discord.Embed(
            description="",
            color=BLANK_COLOR
        )
        embeds = [embed]
        
        for item in json_data["Applicants"]:
            new_content = f"<@{item['DiscordID']}>\n> Status: **{item['Status']}**\n> Reason: **{item['Reason']}**\n> Submission Time: <t:{int(item['SubmissionTime'])}>\n\n"
            
            current_desc = embeds[-1].description or ""
            if len(current_desc) + len(new_content) > 4000:
                new_embed = discord.Embed(description="", color=BLANK_COLOR)
                embeds.append(new_embed)
            
            embeds[-1].description = (embeds[-1].description or "") + new_content
            
        await channel.send(embeds=embeds)

    async def POST_all_members(
        self,
        authorization: Annotated[str | None, Header()],
        guild_id: int
    ):
        if not authorization:
            raise HTTPException(status_code=401, detail="Invalid authorization")
    
        if not await validate_authorization(self.bot, authorization):
            raise HTTPException(status_code=401, detail="Invalid or expired authorization.")
    
        guild = self.bot.get_guild(guild_id)
        if not guild:
            raise HTTPException(status_code=404, detail="Guild not found")
    
        if not guild.chunked:
            try:
                await guild.chunk(cache=True)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to fetch all members: {str(e)}")
    
        member_data = []
        for member in guild.members:
            voice_state = member.voice
            member_info = {
                "id": member.id,
                "name": member.name,
                "nick": member.nick,
                "roles": [role.id for role in member.roles[1:]],
                "voice_state": None
            }
            
            if voice_state:
                member_info["voice_state"] = {
                    "channel_id": voice_state.channel.id if voice_state.channel else None,
                    "channel_name": voice_state.channel.name if voice_state.channel else None,
                }
            
            member_data.append(member_info)
    
        response = {
            "members": member_data,
            "total_members": len(member_data)
        }
    
        return response
    
    async def POST_send_logging(
        self,
        authorization: Annotated[str | None, Header()],
        request: Request
    ):
        if not authorization:
            raise HTTPException(status_code=401, detail="Invalid authorization")
    
        if not await validate_authorization(self.bot, authorization):
            raise HTTPException(status_code=401, detail="Invalid or expired authorization.")
    
        json_data = await request.json()
        await secure_logging(self.bot, json_data["guild_id"], json_data["author_id"], json_data["interpret_type"], json_data["command_string"], json_data["attempted"])
        return {
            "message": "Successfully logged!"
        }

    async def POST_get_staff_guilds(self, request: Request):
        json_data = await request.json()
        guild_ids = json_data.get("guilds")
        user_id = json_data.get("user")
        if not guild_ids:
            raise HTTPException(status_code=400, detail="No guilds specified")
    
        semaphore = asyncio.Semaphore(5)

        async def get_or_fetch(guild: discord.Guild, member_id: int):
            m = guild.get_member(member_id)
            if m:
                return m
            try:
                m = await guild.fetch_member(member_id)
            except:
                m = None
            return m
    
        async def process_guild(guild_id):
            async with semaphore:
                guild: discord.Guild = self.bot.get_guild(int(guild_id))
                if not guild:
                    return None
                try:
                    icon = guild.icon.with_size(512)
                    icon = icon.with_format("png")
                    icon = str(icon)
                except AttributeError:

                    icon = "https://cdn.discordapp.com/embed/avatars/0.png?size=512"

                try:
                    user = await asyncio.wait_for(get_or_fetch(guild, user_id), timeout=5.0)
                except (discord.NotFound, asyncio.TimeoutError):
                    return None

                if user is None:
                    return None
    
                permission_level = 0
                if await management_check(self.bot, guild, user):
                    permission_level = 2
                elif await admin_check(self.bot, guild, user):
                    permission_level = 3
                elif await staff_check(self.bot, guild, user):
                    permission_level = 1
                if permission_level > 0:
                    return {
                        "id": str(guild.id),
                        "name": str(guild.name),
                        "member_count": str(guild.member_count),
                        "icon_url": icon,
                        "permission_level": permission_level,
                    }
                return None
    
        guild_results = await asyncio.gather(*[process_guild(guild_id) for guild_id in guild_ids])
    
        guilds = list(filter(lambda x: x is not None, guild_results))
    
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
        elif await admin_check(self.bot, guild, user):
            permission_level = 3
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
       # # # print(request)
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
        ## # print(token_obj)
        # # print(request.client.host)
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

        self.bot.dispatch('shift_start', ObjectId(data))
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

        self.bot.dispatch('shift_end', ObjectId(data))
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

        self.bot.dispatch('break_start', ObjectId(data))
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



        self.bot.dispatch('break_end', ObjectId(data))
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

        dataobject = await self.bot.shift_management.fetch_shift(ObjectId(data))
        guild = await self.bot.fetch_guild(dataobject["Guild"])
        staff_member = await guild.fetch_member(dataobject['UserID'])

        self.bot.dispatch('shift_void', staff_member, ObjectId(data))
        return 200

    async def POST_punishment_logged(self, authorization: Annotated[str | None, Header()], request: Request):
        if not authorization:
            return HTTPException(status_code=401, detail="Invalid authorization")

        base_auth = await validate_authorization(self.bot, authorization, disable_static_tokens=False)
        # print(base_auth)
        if not base_auth:
            return HTTPException(status_code=401, detail="Invalid authorization")
        data = request.query_params.get("ObjectId")
        if not data:
            return HTTPException(status_code=400, detail="Didn't provide 'ObjectId' parameter.")

        self.bot.dispatch('punishment', ObjectId(data))
        return 200
    async def POST_duty_on(
        self,
        authorization: Annotated[str | None, Header()],
        identification: Identification,
        request: Request,
    ):
        # # print(request)
        # # print(await request.json())
        # # print("REQUEST ^^")
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

        # # print(body)
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
        self.server = None
        self.server_task = None

    async def start_server(self):
        try:
            api.include_router(APIRoutes(self.bot).router)
            self.config = uvicorn.Config("utils.api:api", port=5000, log_level="info", host="0.0.0.0")
            self.server = uvicorn.Server(self.config)
            await self.server.serve()
        except Exception as e:
            logger.error(f"Server error: {e}")
            await asyncio.sleep(5)
            self.server_task = asyncio.create_task(self.start_server())

    async def stop_server(self):
        try:
            if self.server:
                await self.server.shutdown()
            else:
                logger.info("Server was not running")
        except Exception as e:
            logger.error(f"Error stopping server: {e}")

    async def cog_load(self) -> None:
        self.server_task = asyncio.create_task(self.start_server())
        self.server_task.add_done_callback(self.server_error_handler)

    def server_error_handler(self, future: asyncio.Future):
        try:
            future.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Unhandled server error: {e}")
            self.server_task = asyncio.create_task(self.start_server())

    async def cog_unload(self) -> None:
        try:
            if self.server_task:
                self.server_task.cancel()
            await self.stop_server()
        except Exception as e:
            logger.error(f"Error during cog unload: {e}")

async def setup(bot):
    try:
        await bot.add_cog(ServerAPI(bot))
    except Exception as e:
        logger.error(f"Error setting up ServerAPI cog: {e}")
