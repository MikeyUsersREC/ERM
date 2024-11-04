import datetime

import aiohttp
from bson import ObjectId
from discord.ext import commands
import discord
from utils.mongo import Document
from decouple import config

from utils.basedataclass import BaseDataClass


class BreakItem(BaseDataClass):
    start_epoch: int
    end_epoch: int

class ShiftItem:
    id: str
    username: str
    nickname: str
    user_id: int
    type: str
    start_epoch: int
    breaks: list
    guild: int
    moderations: list
    end_epoch: int
    added_time: int
    removed_time: int

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class ShiftManagement:
    def __init__(self, connection, current_shifts):
        self.shifts = Document(connection, current_shifts)

    async def fetch_shift(self, object_id: ObjectId) -> ShiftItem | None:
        shift = await self.shifts.find_by_id(object_id)
        if not shift:
            return None
        return ShiftItem(
            id=shift["_id"],
            username=shift["Username"],
            nickname=shift["Nickname"],
            user_id=shift["UserID"],
            type=shift["Type"],
            start_epoch=shift["StartEpoch"],
            breaks=[BreakItem(start_epoch=item['StartEpoch'], end_epoch=item['EndEpoch']) for item in shift["Breaks"]],
            guild=shift["Guild"],
            moderations=shift["Moderations"],
            end_epoch=shift["EndEpoch"],
            added_time=shift["AddedTime"],
            removed_time=shift["RemovedTime"]
        )

    async def add_shift_by_user(
        self, member: discord.Member, shift_type: str, breaks: list, guild: int, timestamp: int = 0
    ):
        """
        Adds a shift for the specified user to the database, with the provided
        extras data.

        The shift is recorded as a document in the 'shifts' collection, and the
        user's ID is used as the document ID. If a document with that ID already
        exists in the collection, the new shift data is added to the existing
        'data' array.

        {
          "Username": "1FriendlyDoge",
          "Nickname": "NoobyNoob",
          "UserID": 123456789012345678,
          "Type": "Ingame Shift",
          "StartEpoch": 706969420,
          "Breaks": [
            {
              "StartEpoch": 706969430,
              "EndEpoch": 706969550
            }
          ],
          "Moderations": [
                ObjectId("123456789012345678901234")
          ],
          "EndEpoch": 706969420,
          "Guild": 12345678910111213
        }
        """
        data = {
            "_id": ObjectId(),
            "Username": member.name,
            "Nickname": member.display_name,
            "UserID": member.id,
            "Type": shift_type,
            "StartEpoch": datetime.datetime.now().timestamp() if timestamp in [0, None] else timestamp,
            "Breaks": breaks,
            "Guild": guild,
            "Moderations": [],
            "AddedTime": 0,
            "RemovedTime": 0,
            "EndEpoch": 0,
        }
        await self.shifts.db.insert_one(data)

        try:
            url_var = config("BASE_API_URL")
            if url_var not in ["", None]:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                            f"{url_var}/Internal/SyncStartShift/{data['_id']}", headers={
                                "Authorization": config('INTERNAL_API_AUTH')
                            }):
                        pass
        except:
            pass

        return data["_id"]

    async def add_time_to_shift(self, identifier: str, seconds: int):
        """
        Adds time to the specified user's shift.
        """
        document = await self.shifts.db.find_one({"_id": ObjectId(identifier)})
        document["AddedTime"] += int(seconds)
        await self.shifts.update_by_id(document)
        return document

    async def remove_time_from_shift(self, identifier: str, seconds: int):
        """
        Removes time from the specified user's shift.
        """
        document = await self.shifts.db.find_one({"_id": ObjectId(identifier)})
        document["RemovedTime"] += int(seconds)
        await self.shifts.update_by_id(document)
        return document

    async def end_shift(self, identifier: str, guild_id: int | None = None, timestamp: int | None = None):
        """
        Ends the specified user's shift.
        """

        document = await self.shifts.db.find_one({"_id": ObjectId(identifier)})
        if not document:
            raise ValueError("Shift not found.")

        if document["Guild"] != (guild_id if guild_id else document["Guild"]):
            raise ValueError("Shift not found.")

        document["EndEpoch"] = datetime.datetime.now().timestamp()

        for breaks in document["Breaks"]:
            if breaks["EndEpoch"] == 0:
                breaks["EndEpoch"] = int(datetime.datetime.now().timestamp()) if timestamp in [None, 0] else timestamp

        try:
            url_var = config("BASE_API_URL")
            if url_var not in ["", None]:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                            f"{url_var}/Internal/SyncEndShift/{document['UserID']}/{guild_id}", headers={
                                "Authorization": config('INTERNAL_API_AUTH')
                            }):
                        pass
        except:
            pass

        await self.shifts.update_by_id(document)
        return document

    async def get_current_shift(self, member: discord.Member, guild_id: int):
        """
        Gets the current shift for the specified user.
        """
        return await self.shifts.db.find_one(
            {"UserID": member.id, "EndEpoch": 0, "Guild": guild_id}
        )
