from copy import copy

from bson import ObjectId
from discord.ext import commands
import discord

from utils.utils import generator
from utils.mongo import Document


class Warnings(Document):
    """
    Also known as the punishment module, this is used for intermediary methods for the Warnings database <-> ERM.
    """

    def __init__(self, bot):
        self.bot = bot
        super().__init__(bot.db, "punishments")
        self.recovery = Document(bot.db, "recovery")

    async def get_warnings(self, user: int, guild: int) -> list[dict]:
        """
        Gets the warnings for a user in a guild.
        """
        return [i async for i in self.db.find({"Guild": guild, "UserID": user})]

    async def get_warning(self, warning_id: int) -> dict:
        """
        Gets a warning by its ID.
        """
        return await self.db.find_one({"_id": warning_id})

    async def get_warning_by_snowflake(self, snowflake: int) -> dict:
        """
        Gets a warning by its ID.
        """
        return await self.db.find_one({"Snowflake": snowflake})

    async def get_global_warnings(self, user: int) -> list[dict]:
        """
        Gets the warnings for a user globally.
        """
        return [i async for i in self.db.find({"UserID": user})]

    async def get_guild_bolos(self, guild: int) -> list[dict]:
        """
        Gets the BOLOs for a guild.
        """
        return [
            i
            async for i in self.db.find(
                {"Guild": guild, "Type": {"$in": ["BOLO", "Bolo"]}}
            )
        ]

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
    ) -> dict | ValueError:
        """
        Inserts a warning into the database.
        {
          "_id": 123456789012345678,
          "Username": "1friendlydoge",
          "UserID": 123456789012345678,
          "Type": "Warning",
          "Reason": "Nerd",
          "Moderator": "Noah",
          "ModeratorID": 123456789012345678,
          "Guild": 12345678910111213,
          "Epoch": 706969420,
          "UntilEpoch": 706969420
        }
        """
        if all([until_epoch is None, moderation_type == "Temporary Ban"]):
            return ValueError("Epoch must be provided for temporary bans.")

        if any(
            not i
            for i in [
                staff_id,
                staff_name,
                user_id,
                user_name,
                guild_id,
                reason,
                moderation_type,
            ]
        ):
            return ValueError("All arguments must be provided.")

        identifier = ObjectId()

        await self.db.insert_one(
            {
                "_id": identifier,
                "Snowflake": next(generator),
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
        )

        return identifier

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

    def find_warnings_by_spec(
        self,
        guild_id: int,
        identifier: int | None = None,
        snowflake: int | None = None,
        warning_type: str | None = None,
        moderator_id: int | None = None,
        user_id: int | None = None,
    ):
        """
        Finds a warnings by a specification.
        """
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
        print('!!!!')
        if all(
            [
                identifier is None,
                warning_type is None,
                moderator_id is None,
                user_id is None,
                guild_id is None
            ]
        ):
            return ValueError("At least one argument must be provided.")

        if identifier is not None and all(
            [warning_type is None, moderator_id is None, user_id is None, guild_id is None  ]
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

        print(map)
        async for i in self.db.aggregate([{"$match": map}]):
            print('!')
            await self.recovery.insert(i)
            await self.db.delete_one({"_id": i["_id"]})

    async def remove_warning_by_snowflake(
        self, identifier: int, guild_id: int | None = None
    ):
        """
        Removes a warning from the database by its snowflake.
        """

        selected_item = await self.db.find_one({"Snowflake": identifier})
        if selected_item["Guild"] == guild_id:
            return await self.db.delete_one({"Snowflake": identifier})
        else:
            return ValueError("Warning does not exist.")

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
