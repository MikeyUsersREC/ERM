import datetime
import pytz
from discord.ext import commands
import discord
from utils.mongo import Document


class OldShiftManagement:
    def __init__(self, connection, current_shifts, past_shifts):
        self.shifts = Document(connection, current_shifts)
        self.shift_storage = Document(connection, past_shifts)

    async def add_shift_by_user(self, member: discord.Member, extras: dict):
        """
        Adds a shift for the specified user to the database, with the provided
        extras data.

        The shift is recorded as a document in the 'shifts' collection, and the
        user's ID is used as the document ID. If a document with that ID already
        exists in the collection, the new shift data is added to the existing
        'data' array.

        Args:
            member (discord.Member): The Discord member to add the shift for.
            extras (dict): Additional data to include in the shift document.
                Expected keys:
                    - message: (Optional) A discord.Message object to extract the
                        timestamp from. If not provided, the current time is used.
                    - changed_nick: (Optional) A boolean indicating whether the user
                        changed their nickname during the shift. If True, the
                        'current_name' and 'new_name' keys must also be present in
                        the extras dict.
                    - current_name: (Optional) The user's nickname before the change.
                    - new_name: (Optional) The user's nickname after the change.
                    - shift_type: (Optional) A dict describing the type of shift. The
                        dict should have an 'id' key, which is a string ID for the shift
                        type.
                    - guild: (Required) A discord.Guild object representing the guild
                        where the shift took place.

        Raises:
            Exception: If there was an error inserting/updating the shift data in the
                database.
        """
        message = extras.get("message")
        changed_nick = extras.get("changed_nick")
        current_name = extras.get("current_name")
        new_name = extras.get("new_name")
        shift_type = extras.get("shift_type")
        guild = extras.get("guild")
        if message:
            timestamp = message.created_at.replace(tzinfo=pytz.UTC).timestamp()
        else:
            timestamp = int(
                datetime.datetime.now().replace(tzinfo=pytz.UTC).timestamp()
            )

        try:
            if shift_type:
                if changed_nick:
                    await self.shifts.insert(
                        {
                            "_id": member.id,
                            "name": member.name,
                            "data": [
                                {
                                    "guild": guild.id,
                                    "startTimestamp": timestamp,
                                    "type": shift_type["id"],
                                    "nickname": {
                                        "old": current_name,
                                        "new": new_name,
                                    },
                                }
                            ],
                        }
                    )
                else:
                    await self.shifts.insert(
                        {
                            "_id": member.id,
                            "name": member.name,
                            "data": [
                                {
                                    "guild": guild.id,
                                    "startTimestamp": timestamp,
                                    "type": shift_type["id"],
                                }
                            ],
                        }
                    )
            else:
                if changed_nick:
                    await self.shifts.insert(
                        {
                            "_id": member.id,
                            "name": member.name,
                            "data": [
                                {
                                    "guild": guild.id,
                                    "startTimestamp": timestamp,
                                    "nickname": {
                                        "old": current_name,
                                        "new": new_name,
                                    },
                                }
                            ],
                        }
                    )
                else:
                    await self.shifts.insert(
                        {
                            "_id": member.id,
                            "name": member.name,
                            "data": [
                                {
                                    "guild": guild.id,
                                    "startTimestamp": timestamp,
                                }
                            ],
                        }
                    )
        except:
            if await self.shifts.find_by_id(member.id):
                shift = await self.shifts.find_by_id(member.id)
                if "data" in shift.keys():
                    if shift_type:
                        newData = shift["data"]
                        if changed_nick:
                            newData.append(
                                {
                                    "guild": guild.id,
                                    "startTimestamp": timestamp,
                                    "type": shift_type["id"],
                                    "nickname": {
                                        "new": new_name,
                                        "old": current_name,
                                    },
                                }
                            )
                        else:
                            newData.append(
                                {
                                    "guild": guild.id,
                                    "startTimestamp": timestamp,
                                    "type": shift_type["id"],
                                }
                            )
                        await self.shifts.update_by_id(
                            {
                                "_id": member.id,
                                "name": member.name,
                                "data": newData,
                            }
                        )
                    else:
                        newData = shift["data"]
                        if changed_nick:
                            newData.append(
                                {
                                    "guild": guild.id,
                                    "startTimestamp": timestamp,
                                    "nickname": {
                                        "old": current_name,
                                        "new": new_name,
                                    },
                                }
                            )
                        else:
                            newData.append(
                                {
                                    "guild": guild.id,
                                    "startTimestamp": timestamp,
                                }
                            )
                        await self.shifts.update_by_id(
                            {
                                "_id": member.id,
                                "name": member.name,
                                "data": newData,
                            }
                        )
                elif "data" not in shift.keys():
                    if shift_type:
                        if changed_nick:
                            await self.shifts.update_by_id(
                                {
                                    "_id": member.id,
                                    "name": member.name,
                                    "data": [
                                        {
                                            "guild": guild.id,
                                            "startTimestamp": timestamp,
                                            "type": shift_type["id"],
                                            "nickname": {
                                                "old": current_name,
                                                "new": new_name,
                                            },
                                        },
                                        {
                                            "guild": shift["guild"],
                                            "startTimestamp": shift["startTimestamp"],
                                        },
                                    ],
                                }
                            )
                        else:
                            await self.shifts.update_by_id(
                                {
                                    "_id": member.id,
                                    "name": member.name,
                                    "data": [
                                        {
                                            "guild": guild.id,
                                            "startTimestamp": timestamp,
                                            "type": shift_type["id"],
                                        },
                                        {
                                            "guild": shift["guild"],
                                            "startTimestamp": shift["startTimestamp"],
                                        },
                                    ],
                                }
                            )
                    else:
                        if changed_nick:
                            await self.shifts.update_by_id(
                                {
                                    "_id": member.id,
                                    "name": member.name,
                                    "data": [
                                        {
                                            "guild": guild.id,
                                            "startTimestamp": timestamp,
                                            "nickname": {
                                                "old": current_name,
                                                "new": new_name,
                                            },
                                        },
                                        {
                                            "guild": shift["guild"],
                                            "startTimestamp": shift["startTimestamp"],
                                        },
                                    ],
                                }
                            )
                        else:
                            await self.shifts.update_by_id(
                                {
                                    "_id": member.id,
                                    "name": member.name,
                                    "data": [
                                        {
                                            "guild": guild.id,
                                            "startTimestamp": timestamp,
                                        },
                                        {
                                            "guild": shift["guild"],
                                            "startTimestamp": shift["startTimestamp"],
                                        },
                                    ],
                                }
                            )

    async def remove_shift_by_user(self, member: discord.Member, extras: dict):
        """Remove a shift for the given member.

        Args:
            member (discord.Member): The member whose shift is to be removed.
            extras (dict): A dictionary containing the following keys:
                - guild (discord.Guild): The guild where the shift took place.
                - message (discord.Message): The message that initiated the shift.
                - time_delta (datetime.timedelta): (Optional) The duration of the shift.
                - shift (dict): A dictionary containing the following keys:
                    - startTimestamp (float): The timestamp when the shift started.
                    - moderations (list): A list of moderations made during the shift.
                    - type (str): The type of the shift.

        Raises:
            Exception: If any of the required keys are missing from the `extras` dictionary.

        Returns:
            None
        """

        guild = extras.get("guild")
        message = extras.get("message")
        time_delta = extras.get("time_delta")
        shift = extras.get("shift")

        if any([not guild, not shift]):
            raise Exception("Missing required extras")

        if message:
            timestamp = message.created_at.replace(tzinfo=pytz.UTC).timestamp()
        else:
            timestamp = datetime.datetime.now().replace(tzinfo=pytz.UTC).timestamp()

        if not time_delta and shift:
            time_delta = datetime.datetime.now().replace(
                tzinfo=pytz.UTC
            ) - datetime.datetime.fromtimestamp(shift["startTimestamp"]).replace(
                tzinfo=pytz.UTC
            )

            break_seconds = 0
            if "breaks" in shift.keys():
                for item in shift["breaks"]:
                    if item["ended"] == None:
                        item["ended"] = timestamp
                    startTimestamp = item["started"]
                    endTimestamp = item["ended"]
                    break_seconds += int(endTimestamp - startTimestamp)

            time_delta = time_delta - datetime.timedelta(seconds=break_seconds)

            added_seconds = 0
            removed_seconds = 0
            if "added_time" in shift.keys():
                for added in shift["added_time"]:
                    added_seconds += added

            if "removed_time" in shift.keys():
                for removed in shift["removed_time"]:
                    removed_seconds += removed

            try:
                time_delta = time_delta + datetime.timedelta(seconds=added_seconds)
                time_delta = time_delta - datetime.timedelta(seconds=removed_seconds)
            except OverflowError:
                pass

        if not await self.shift_storage.find_by_id(member.id):
            await self.shift_storage.insert(
                {
                    "_id": member.id,
                    "shifts": [
                        {
                            "name": member.name,
                            "startTimestamp": shift["startTimestamp"],
                            "endTimestamp": timestamp,
                            "totalSeconds": time_delta.total_seconds(),
                            "guild": guild.id,
                            "moderations": shift["moderations"]
                            if "moderations" in shift.keys()
                            else [],
                            "type": shift["type"] if "type" in shift.keys() else None,
                        }
                    ],
                    "totalSeconds": time_delta.total_seconds(),
                }
            )
        else:
            data = await self.shift_storage.find_by_id(member.id)

            if "shifts" in data.keys():
                if data["shifts"] is None:
                    data["shifts"] = []

                if data["shifts"] == []:
                    shifts = [
                        {
                            "name": member.name,
                            "startTimestamp": shift["startTimestamp"],
                            "endTimestamp": timestamp,
                            "totalSeconds": time_delta.total_seconds(),
                            "guild": guild.id,
                            "moderations": shift["moderations"]
                            if "moderations" in shift.keys()
                            else [],
                            "type": shift["type"] if "type" in shift.keys() else None,
                        }
                    ]
                else:
                    object = {
                        "name": member.name,
                        "startTimestamp": shift["startTimestamp"],
                        "endTimestamp": timestamp,
                        "totalSeconds": time_delta.total_seconds(),
                        "guild": guild.id,
                        "moderations": shift["moderations"]
                        if "moderations" in shift.keys()
                        else [],
                        "type": shift["type"] if "type" in shift.keys() else None,
                    }
                    shiftdata = data["shifts"]
                    shifts = shiftdata + [object]

                await self.shift_storage.update_by_id(
                    {
                        "_id": member.id,
                        "shifts": shifts,
                        "totalSeconds": sum(
                            [
                                shifts[i]["totalSeconds"]
                                for i in range(len(shifts))
                                if shifts[i] is not None
                            ]
                        ),
                    }
                )
            else:
                await self.shift_storage.update_by_id(
                    {
                        "_id": member.id,
                        "shifts": [
                            {
                                "name": member.name,
                                "startTimestamp": shift["startTimestamp"],
                                "endTimestamp": timestamp,
                                "totalSeconds": time_delta.total_seconds(),
                                "guild": guild.id,
                                "moderations": shift["moderations"]
                                if "moderations" in shift.keys()
                                else [],
                                "type": shift["type"]
                                if "type" in shift.keys()
                                else None,
                            }
                        ],
                        "totalSeconds": time_delta.total_seconds(),
                    }
                )

        if await self.shifts.find_by_id(member.id):
            dataShift = await self.shifts.find_by_id(member.id)
            if "data" in dataShift.keys():
                if isinstance(dataShift["data"], list):
                    for item in dataShift["data"]:
                        if item["guild"] == guild.id:
                            dataShift["data"].remove(item)
                            break
            await self.shifts.update_by_id(dataShift)
