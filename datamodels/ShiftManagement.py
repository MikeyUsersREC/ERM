import datetime
import aiohttp
from bson import ObjectId
import discord
from utils.mongo import Document
from decouple import config
from utils.basedataclass import BaseDataClass
import logging
from typing import Optional

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

    async def fetch_shift(self, object_id: ObjectId) -> Optional[ShiftItem]:
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

            await self._sync_shift_start(data['_id'], guild)

            return data["_id"]
        except Exception as e:
            logger.error(f"Error in add_shift_by_user: {e}")
            raise

    async def _sync_shift_start(self, shift_id: ObjectId, guild_id: int):
        url_var = config("BASE_API_URL", default="")
        panel_url_var = config("PANEL_API_URL", default="")
        
        if url_var:
            await self._make_api_call(
                f"{url_var}/Internal/SyncStartShift/{shift_id}",
                headers={"Authorization": config('INTERNAL_API_AUTH', default="")}
            )
        
        if panel_url_var:
            await self._make_api_call(
                f"{panel_url_var}/{guild_id}/SyncStartShift?ID={shift_id}",
                method="POST",
                headers={"X-Static-Token": config('PANEL_STATIC_AUTH', default="")}
            )

    async def _make_api_call(self, url: str, method: str = "GET", headers: dict = None, timeout: int = 30):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=headers, timeout=timeout) as response:
                    if response.status != 200:
                        logger.warning(f"Unexpected status {response.status} from API call to {url}")
                    return await response.text()
        except aiohttp.ClientError as e:
            logger.error(f"API call failed: {e}")
        except asyncio.TimeoutError:
            logger.error(f"API call timed out: {url}")

    async def add_time_to_shift(self, identifier: str, seconds: int):
        try:
            document = await self.shifts.db.find_one_and_update(
                {"_id": ObjectId(identifier)},
                {"$inc": {"AddedTime": int(seconds)}},
                return_document=True
            )
            if not document:
                raise ValueError(f"Shift with id {identifier} not found")
            return document
        except Exception as e:
            logger.error(f"Error in add_time_to_shift: {e}")
            raise

    async def remove_time_from_shift(self, identifier: str, seconds: int):
        try:
            document = await self.shifts.db.find_one_and_update(
                {"_id": ObjectId(identifier)},
                {"$inc": {"RemovedTime": int(seconds)}},
                return_document=True
            )
            if not document:
                raise ValueError(f"Shift with id {identifier} not found")
            return document
        except Exception as e:
            logger.error(f"Error in remove_time_from_shift: {e}")
            raise

    async def end_shift(self, identifier: str, guild_id: int | None = None, timestamp: int | None = None):
        try:
            end_time = datetime.datetime.now().timestamp() if timestamp in [None, 0] else timestamp
            
            document = await self.shifts.db.find_one_and_update(
                {"_id": ObjectId(identifier), "Guild": guild_id or {"$exists": True}, "EndEpoch": 0},
                {
                    "$set": {
                        "EndEpoch": end_time,
                        "Breaks.$[elem].EndEpoch": end_time
                    }
                },
                array_filters=[{"elem.EndEpoch": 0}],
                return_document=True
            )

            if not document:
                raise ValueError("Shift not found or already ended.")

            await self._sync_shift_end(document['UserID'], document['Guild'], document['_id'])

            return document
        except Exception as e:
            logger.error(f"Error in end_shift: {e}")
            raise

    async def _sync_shift_end(self, user_id: int, guild_id: int, shift_id: ObjectId):
        url_var = config("BASE_API_URL", default="")
        panel_url_var = config("PANEL_API_URL", default="")
        
        if url_var:
            await self._make_api_call(
                f"{url_var}/Internal/SyncEndShift/{user_id}/{guild_id}",
                headers={"Authorization": config('INTERNAL_API_AUTH', default="")}
            )
        
        if panel_url_var:
            await self._make_api_call(
                f"{panel_url_var}/{guild_id}/SyncEndShift?ID={shift_id}",
                method="DELETE",
                headers={"X-Static-Token": config('PANEL_STATIC_AUTH', default="")}
            )

    async def get_current_shift(self, member: discord.Member, guild_id: int):
        try:
            return await self.shifts.db.find_one(
                {"UserID": member.id, "EndEpoch": 0, "Guild": guild_id}
            )
        except Exception as e:
            logger.error(f"Error in get_current_shift: {e}")
            return None
