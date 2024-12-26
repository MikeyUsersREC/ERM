import datetime
import asyncio
import logging
from typing import Optional

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
        self.logger = logging.getLogger(__name__)

    async def fetch_shift(self, object_id: ObjectId) -> Optional[ShiftItem]:
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
    ) -> ObjectId:
        """
        Adds a shift for the specified user to the database and syncs with external APIs.
        
        Args:
            member: Discord member starting the shift
            shift_type: Type of shift being started
            breaks: List of break periods
            guild: Guild ID where the shift is being started
            timestamp: Optional custom start timestamp
        
        Returns:
            ObjectId of the created shift document
        
        Raises:
            aiohttp.ClientError: If API sync fails
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
        
        url_var = config("BASE_API_URL")
        panel_url_var = config("PANEL_API_URL")
        
        async def sync_with_apis():
            async with aiohttp.ClientSession() as session:
                tasks = []
                
                if url_var not in ["", None]:
                    tasks.append(
                        session.get(
                            f"{url_var}/Internal/SyncStartShift/{data['_id']}", 
                            headers={"Authorization": config('INTERNAL_API_AUTH')},
                            raise_for_status=True
                        )
                    )
                
                if panel_url_var not in ["", None]:
                    tasks.append(
                        session.post(
                            f"{panel_url_var}/{guild}/SyncStartShift?ID={data['_id']}", 
                            headers={"X-Static-Token": config('PANEL_STATIC_AUTH')},
                            raise_for_status=True
                        )
                    )
                
                if tasks:
                    responses = await asyncio.gather(*tasks, return_exceptions=True)
                    for response in responses:
                        if isinstance(response, Exception):
                            self.logger.error(f"API sync failed: {str(response)}")
        
        try:
            await sync_with_apis()
        except aiohttp.ClientError as e:
            self.logger.error(f"Failed to sync shift start with APIs: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error during API sync: {str(e)}")
        
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
        Ends the specified user's shift and syncs with external APIs.
        
        Args:
            identifier: Shift document ID
            guild_id: Optional guild ID override
            timestamp: Optional custom end timestamp
        
        Returns:
            Updated shift document
            
        Raises:
            ValueError: If shift not found or guild mismatch
        """
        document = await self.shifts.db.find_one({"_id": ObjectId(identifier)})
        if not document:
            raise ValueError("Shift not found.")
        
        guild_id = guild_id if guild_id else document["Guild"]
        
        if document["Guild"] != guild_id:
            raise ValueError("Shift not found.")
        
        current_time = datetime.datetime.now().timestamp() if timestamp in [None, 0] else timestamp
        document["EndEpoch"] = current_time
        
        # Close any open breaks
        for breaks in document["Breaks"]:
            if breaks["EndEpoch"] == 0:
                breaks["EndEpoch"] = int(current_time)
        
        url_var = config("BASE_API_URL")
        panel_url_var = config("PANEL_API_URL")
        
        async def sync_end_with_apis():
            async with aiohttp.ClientSession() as session:
                tasks = []
                
                if url_var not in ["", None]:
                    tasks.append(
                        session.get(
                            f"{url_var}/Internal/SyncEndShift/{document['UserID']}/{guild_id}",
                            headers={"Authorization": config('INTERNAL_API_AUTH')},
                            raise_for_status=True
                        )
                    )
                
                if panel_url_var not in ["", None]:
                    tasks.append(
                        session.delete(
                            f"{panel_url_var}/{guild_id}/SyncEndShift?ID={document['_id']}",
                            headers={"X-Static-Token": config('PANEL_STATIC_AUTH')},
                            raise_for_status=True
                        )
                    )
                
                if tasks:
                    responses = await asyncio.gather(*tasks, return_exceptions=True)
                    for response in responses:
                        if isinstance(response, Exception):
                            self.logger.error(f"End shift API sync failed: {str(response)}")
        
        try:
            await sync_end_with_apis()
        except aiohttp.ClientError as e:
            self.logger.error(f"Failed to sync shift end with APIs: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error during end shift API sync: {str(e)}")
        
        await self.shifts.update_by_id(document)
        return document

    async def get_current_shift(self, member: discord.Member, guild_id: int):
        """
        Gets the current shift for the specified user.
        
        Args:
            member: Discord member to check
            guild_id: Guild ID to check
            
        Returns:
            Current shift document or None if no active shift
        """
        return await self.shifts.db.find_one(
            {"UserID": member.id, "EndEpoch": 0, "Guild": guild_id}
        )
