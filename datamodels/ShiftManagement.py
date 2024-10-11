import datetime
import aiohttp
from bson import ObjectId
from discord.ext import commands
import discord
from utils.mongo import Document
from decouple import config
from utils.basedataclass import BaseDataClass
import logging

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

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
        try:
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
        except Exception as e:
            logger.error(f"Error in fetch_shift: {e}")
            return None

    async def add_shift_by_user(
        self, member: discord.Member, shift_type: str, breaks: list, guild: int, timestamp: int = 0
    ):
        try:
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

            url_var = config("BASE_API_URL", default="")
            panel_url_var = config("PANEL_API_URL", default="")
            
            if url_var:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                            f"{url_var}/Internal/SyncStartShift/{data['_id']}", 
                            headers={"Authorization": config('INTERNAL_API_AUTH', default="")},
                            timeout=10
                    ) as response:
                        if response.status != 200:
                            logger.warning(f"Unexpected status {response.status} from BASE_API_URL")
            
            if panel_url_var:
                url = f"{panel_url_var}/{guild}/SyncStartShift?ID={data['_id']}"
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                            url, 
                            headers={"X-Static-Token": config('PANEL_STATIC_AUTH', default="")},
                            timeout=10
                    ) as response:
                        if response.status != 200:
                            logger.warning(f"Unexpected status {response.status} from PANEL_API_URL")

            return data["_id"]
        except Exception as e:
            logger.error(f"Error in add_shift_by_user: {e}")
            raise

    async def add_time_to_shift(self, identifier: str, seconds: int):
        try:
            document = await self.shifts.db.find_one({"_id": ObjectId(identifier)})
            if not document:
                raise ValueError(f"Shift with id {identifier} not found")
            document["AddedTime"] += int(seconds)
            await self.shifts.update_by_id(document)
            return document
        except Exception as e:
            logger.error(f"Error in add_time_to_shift: {e}")
            raise

    async def remove_time_from_shift(self, identifier: str, seconds: int):
        try:
            document = await self.shifts.db.find_one({"_id": ObjectId(identifier)})
            if not document:
                raise ValueError(f"Shift with id {identifier} not found")
            document["RemovedTime"] += int(seconds)
            await self.shifts.update_by_id(document)
            return document
        except Exception as e:
            logger.error(f"Error in remove_time_from_shift: {e}")
            raise

    async def end_shift(self, identifier: str, guild_id: int | None = None, timestamp: int | None = None):
        try:
            document = await self.shifts.db.find_one({"_id": ObjectId(identifier)})
            if not document:
                raise ValueError("Shift not found.")

            guild_id = guild_id if guild_id else document["Guild"]

            if document["Guild"] != guild_id:
                raise ValueError("Shift not found.")

            document["EndEpoch"] = datetime.datetime.now().timestamp() if timestamp in [None, 0] else timestamp

            for breaks in document["Breaks"]:
                if breaks["EndEpoch"] == 0:
                    breaks["EndEpoch"] = int(datetime.datetime.now().timestamp()) if timestamp in [None, 0] else timestamp

            url_var = config("BASE_API_URL", default="")
            panel_url_var = config("PANEL_API_URL", default="")
            
            if url_var:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                            f"{url_var}/Internal/SyncEndShift/{document['UserID']}/{guild_id}",
                            headers={"Authorization": config('INTERNAL_API_AUTH', default="")},
                            timeout=10
                    ) as response:
                        if response.status != 200:
                            logger.warning(f"Unexpected status {response.status} from BASE_API_URL")
            
            if panel_url_var:
                url = f"{panel_url_var}/{guild_id}/SyncEndShift?ID={document['_id']}"
                async with aiohttp.ClientSession() as session:
                    async with session.delete(
                            url,
                            headers={"X-Static-Token": config('PANEL_STATIC_AUTH', default="")},
                            timeout=10
                    ) as response:
                        if response.status != 200:
                            logger.warning(f"Unexpected status {response.status} from PANEL_API_URL")

            await self.shifts.update_by_id(document)
            return document
        except Exception as e:
            logger.error(f"Error in end_shift: {e}")
            raise

    async def get_current_shift(self, member: discord.Member, guild_id: int):
        try:
            return await self.shifts.db.find_one(
                {"UserID": member.id, "EndEpoch": 0, "Guild": guild_id}
            )
        except Exception as e:
            logger.error(f"Error in get_current_shift: {e}")
            return None
