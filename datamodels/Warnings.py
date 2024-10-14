import typing
from copy import copy
import traceback

import aiohttp
import pymongo.operations
from bson import ObjectId
from decouple import config
from discord.ext import commands
import discord

from utils.utils import generator
from utils.mongo import Document


class WarningItem:
    id: str
    username: str
    user_id: int
    warning_type: str
    reason: str
    moderator_name: str
    moderator_id: int
    guild_id: int
    time_epoch: int
    until_epoch: typing.Optional[int]
    snowflake: int

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __getitem__(self, item):
        legacy_correspondents = {
            "_id": "id",
            "userid": "user_id",
            "type": "warning_type",
            "moderator": "moderator_name",
            "moderatorid": "moderator_id",
            "guild": "guild_id",
            "epoch": "time_epoch",
            "untilepoch": "until_epoch"
        }
        if legacy_correspondents.get(item.lower()) is not None:
            item = legacy_correspondents[item.lower()]
        return getattr(self, item.lower())


class Warnings(Document):
    """
    Also known as the punishment module, this is used for intermediary methods for the Warnings database <-> ERM.
    """

    def __init__(self, bot):
        self.bot = bot
        super().__init__(bot.db, "punishments")
        self.recovery = Document(bot.db, "recovery")

    async def get_warnings(self, user: int, guild: int) -> list[WarningItem]:
        """
        Gets the warnings for a user in a guild.
        """
        try:
            return [WarningItem(
                id=i['_id'],
                snowflake=i['Snowflake'],
                username=i['Username'],
                user_id=i['UserID'],
                warning_type=i['Type'],
                reason=i['Reason'],
                moderator_name=i['Moderator'],
                moderator_id=i['ModeratorID'],
                guild_id=i['Guild'],
                time_epoch=i['Epoch'],
                until_epoch=None if i.get('UntilEpoch') == 0 else i['UntilEpoch']
            ) async for i in self.db.find({"Guild": guild, "UserID": user})]
        except Exception as e:
            print(f"Error in get_warnings: {str(e)}")
            traceback.print_exc()
            return []

    async def fetch_warning(self, warning_id: str) -> WarningItem | None:
        """
        Fetches a warning by its ID.
        """
        try:
            i = await self.db.find_one({"_id": ObjectId(warning_id)})
            if i is None:
                return None
            return WarningItem(
                id=i['_id'],
                snowflake=i['Snowflake'],
                username=i['Username'],
                user_id=i['UserID'],
                warning_type=i['Type'],
                reason=i['Reason'],
                moderator_name=i['Moderator'],
                moderator_id=i['ModeratorID'],
                guild_id=i['Guild'],
                time_epoch=i['Epoch'],
                until_epoch=None if i.get('UntilEpoch') == 0 else i['UntilEpoch']
            )
        except Exception as e:
            print(f"Error in fetch_warning: {str(e)}")
            traceback.print_exc()
            return None

    async def get_warning(self, warning_id: str) -> dict:
        """
        Gets a warning by its ID.
        """
        try:
            return await self.db.find_one({"_id": ObjectId(warning_id)})
        except Exception as e:
            print(f"Error in get_warning: {str(e)}")
            traceback.print_exc()
            return {}

    async def remove_warning(self, warning_id: str):
        """
        Removes a warning by its ID.
        """
        try:
            await self.db.delete_one({"_id": ObjectId(warning_id)})
        except Exception as e:
            print(f"Error in remove_warning: {str(e)}")
            traceback.print_exc()

    async def get_warning_by_snowflake(self, snowflake: int) -> dict:
        """
        Gets a warning by its ID.
        """
        try:
            return await self.db.find_one({"Snowflake": snowflake})
        except Exception as e:
            print(f"Error in get_warning_by_snowflake: {str(e)}")
            traceback.print_exc()
            return {}

    async def get_global_warnings(self, user: int) -> list[dict]:
        """
        Gets the warnings for a user globally.
        """
        try:
            return [i async for i in self.db.find({"UserID": user})]
        except Exception as e:
            print(f"Error in get_global_warnings: {str(e)}")
            traceback.print_exc()
            return []

    async def get_guild_bolos(self, guild: int) -> list[dict]:
        """
        Gets the BOLOs for a guild.
        """
        try:
            return [
                i
                async for i in self.db.find(
                    {"Guild": guild, "Type": {"$in": ["BOLO", "Bolo"]}}
                )
            ]
        except Exception as e:
            print(f"Error in get_guild_bolos: {str(e)}")
            traceback.print_exc()
            return []

    async def insert_warning(
        self,
        staff_id: int,
        staff_name: str,
        user_id: int,
        user_name: str,
        guild_id: int,
        reason: str,
        moderation_type: str,
        time_epoch: int,
        until_epoch: int | None = None,
) -> ObjectId | ValueError:
    try:
        if moderation_type == "Temporary Ban" and until_epoch is None:
            return ValueError("Epoch must be provided for temporary bans.")

        if not all([staff_id, staff_name, user_id, user_name, guild_id, reason, moderation_type]):
            return ValueError("All arguments must be provided.")

        identifier = ObjectId()
        snowflake = await self.bot.loop.run_in_executor(None, next, generator)

        warning_data = {
            "_id": identifier,
            "Snowflake": snowflake,
            "Username": user_name,
            "UserID": user_id,
            "Type": moderation_type,
            "Reason": reason,
            "Moderator": staff_name,
            "ModeratorID": staff_id,
            "Guild": guild_id,
            "Epoch": int(time_epoch),
            "UntilEpoch": int(until_epoch if until_epoch is not None else 0),
        }

        await self.db.insert_one(warning_data)

        # Run API requests concurrently
        tasks = []
        url_var = config("BASE_API_URL")
        panel_url_var = config("PANEL_API_URL")

        if url_var:
            tasks.append(self.make_api_request(
                f"{url_var}/Internal/SyncCreatePunishment/{identifier}",
                headers={"Authorization": config('INTERNAL_API_AUTH')}
            ))

        if panel_url_var:
            final_url = f"{panel_url_var}/{guild_id}/SyncCreatePunishment?ID={identifier}"
            print(f"Final Panel URL: {final_url}")
            tasks.append(self.make_api_request(
                final_url,
                method="POST",
                headers={"X-Static-Token": config('PANEL_STATIC_AUTH')}
            ))

        await asyncio.gather(*tasks, return_exceptions=True)

        return identifier
    except Exception as e:
        print(f"Error in insert_warning: {str(e)}")
        traceback.print_exc()
        return ValueError("An error occurred while inserting the warning.")

    async def make_api_request(self, url, method="GET", **kwargs):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, **kwargs) as response:
                    return await response.text()
        except Exception as e:
            print(f"API request failed: {str(e)}")

    async def find_warning_by_spec(
            self,
            guild_id: int,
            identifier: str | ObjectId | None = None,
            snowflake: int | None = None,
            warning_type: str | None = None,
            moderator_id: int | None = None,
            user_id: int | None = None,
    ):
        """
        Removes a warning from the database by a particular specification. Useful for removing many warnings at one time.
        """
        try:
            if all(
                    [
                        identifier is None,
                        warning_type is None,
                        moderator_id is None,
                        user_id is None,
                    ]
            ):
                return ValueError("At least one argument must be provided.")

            if snowflake is not None and all(
                    [
                        warning_type is None,
                        moderator_id is None,
                        user_id is None,
                        identifier is None,
                    ]
            ):
                return await self.db.find_one({"Snowflake": snowflake})

            if identifier is not None and all(
                    [
                        warning_type is None,
                        moderator_id is None,
                        user_id is None,
                        snowflake is None,
                    ]
            ):
                return await self.db.find_one({"_id": ObjectId(identifier)})

            map = {
                "Snowflake": identifier,
                "Type": warning_type,
                "ModeratorID": moderator_id,
                "UserID": user_id,
                "Guild": guild_id,
            }

            for i, v in copy(map).items():
                if v is None:
                    del map[i]

            return await self.db.find_one(map)
        except Exception as e:
            print(f"Error in find_warning_by_spec: {str(e)}")
            traceback.print_exc()
            return None

    def find_warnings_by_spec(
            self,
            guild_id: int,
            identifier: int | None = None,
            snowflake: int | None = None,
            warning_type: str | None = None,
            moderator_id: int | None = None,
            user_id: int | None = None,
            bolo: bool = False,
    ):
        """
        Finds a warnings by a specification.
        """
        try:
            if all(
                    [
                        identifier is None,
                        warning_type is None,
                        moderator_id is None,
                        user_id is None,
                        bolo is False,
                    ]
            ):
                return ValueError("At least one argument must be provided.")

            if snowflake is not None and all(
                    [
                        warning_type is None,
                        moderator_id is None,
                        user_id is None,
                        identifier is None,
                    ]
            ):
                return self.db.find({"Snowflake": snowflake})

            if identifier is not None and all(
                    [
                        warning_type is None,
                        moderator_id is None,
                        user_id is None,
                        snowflake is None,
                    ]
            ):
                return self.db.find({"_id": identifier})

            if bolo and not warning_type:
                warning_type = {"$regex": "bolo", "$options": "i"}

            map = {
                "Snowflake": identifier,
                "Type": warning_type,
                "ModeratorID": moderator_id,
                "UserID": user_id,
                "Guild": guild_id,
            }

            for i, v in copy(map).items():
                if v is None:
                    del map[i]

            return self.db.find(map)
        except Exception as e:
            print(f"Error in find_warnings_by_spec: {str(e)}")
            traceback.print_exc()
            return None

    async def remove_warnings_by_spec(
            self,
            guild_id: int,
            identifier: int | None = None,
            warning_type: str | None = None,
            moderator_id: int | None = None,
            user_id: int | None = None,
    ):
        """
        Removes a warning from the database by a particular specification. Useful for removing many warnings at one time.
        """
        try:
            if all(
                    [
                        identifier is None,
                        warning_type is None,
                        moderator_id is None,
                        user_id is None,
                        guild_id is None,
                    ]
            ):
                return ValueError("At least one argument must be provided.")

            if identifier is not None and all(
                    [
                        warning_type is None,
                        moderator_id is None,
                        user_id is None,
                        guild_id is None,
                    ]
            ):
                return await self.db.delete_many({"Snowflake": identifier})

            map = {
                "Snowflake": identifier,
                "Type": warning_type,
                "ModeratorID": moderator_id,
                "UserID": user_id,
                "Guild": guild_id,
            }

            for i, v in copy(map).items():
                if v is None:
                    del map[i]

            storage = []
            async for i in self.db.aggregate([
                {"$match": map},
                {"$project": {"_id": {"$ifNull": ["$_id", None]}}}
            ]):
                storage.append(i)
                await self.db.delete_one({"_id": i["_id"]})

            await self.recovery.db.bulk_write([
                pymongo.operations.UpdateOne({"_id": i["_id"]}, {"$set": i}, upsert=True) for i in storage
            ])
        except Exception as e:
            print(f"Error in remove_warnings_by_spec: {str(e)}")
            traceback.print_exc()

    async def remove_warning_by_snowflake(
            self, identifier: int, guild_id: int | None = None
    ):
        """
        Removes a warning from the database by its snowflake.
        """
        try:
            selected_item = await self.db.find_one({"Snowflake": identifier})
            if selected_item and selected_item["Guild"] == (guild_id or selected_item["Guild"]):
                try:
                    url_var = config("BASE_API_URL")
                    panel_url_var = config("PANEL_API_URL")
                    if url_var not in ["", None]:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(
                                    f"{url_var}/Internal/SyncDeletePunishment/{selected_item['_id']}", headers={
                                        "Authorization": config('INTERNAL_API_AUTH')
                                    }):
                                pass
                    if panel_url_var not in ["", None]:
                        final_guild_id = guild_id or selected_item["Guild"]
                        final_url = f"{panel_url_var}/{final_guild_id}/SyncDeletePunishment?ID={selected_item['_id']}"
                        print(f"Final Panel URL: {final_url}")
        
                        async with aiohttp.ClientSession() as session:
                            async with session.delete(
                                    final_url, headers={
                                        "X-Static-Token": config('PANEL_STATIC_AUTH')
                                    }):
                                pass
                except Exception as e:
                    print(f"Error during API requests: {e}")
                    traceback.print_exc()
                return await self.db.delete_one({"Snowflake": identifier})
            else:
                return ValueError("Warning does not exist.")
        except Exception as e:
            print(f"Error in remove_warning_by_snowflake: {str(e)}")
            traceback.print_exc()
            return ValueError("An error occurred while removing the warning.")

    async def count_warnings(
            self,
            identifier: int | None = None,
            warning_type: str | None = None,
            moderator_id: int | None = None,
            user_id: int | None = None,
            guild_id: int | None = None,
    ):
        """
        Counts the warnings in the database.
        """
        try:
            map = {
                "Snowflake": identifier,
                "Type": warning_type,
                "ModeratorID": moderator_id,
                "UserID": user_id,
                "Guild": guild_id,
            }
            for i, v in copy(map).items():
                if v is None:
                    del map[i]
            return await self.db.count_documents(map)
        except Exception as e:
            print(f"Error in count_warnings: {str(e)}")
            traceback.print_exc()
            return 0
