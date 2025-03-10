import discord
import logging

from decouple import config
from discord.ext import commands, tasks
import time
import datetime
import pytz


@tasks.loop(minutes=10, reconnect=True)
async def tempban_checks(bot):
    # This will check for expired time bans
    # and for servers which have this feature enabled
    # to automatically remove the ban in-game
    # using POST /server/command

    # This will also use a GET request before
    # sending that POST request, particularly
    # GET /server/bans

    # We also check if the punishment item is
    # before the update date, because else we'd
    # have too high influx of invalid
    # temporary bans

    # For diagnostic purposes, we also choose to
    # capture the amount of time it takes for this
    # event to run, as it may cause issues in
    # time registration.

    cached_servers = {}
    filter_map = (
        {"Guild": int(config("CUSTOM_GUILD_ID", default=0))}
        if config("ENVIRONMENT") == "CUSTOM"
        else {
            "Guild": {
                "$nin": [
                    int(item["GuildID"]) async for item in bot.whitelabel.db.find({})
                ]
            }
        }
    )
    initial_time = time.time()
    async for punishment_item in bot.punishments.db.find(
        {
            "Epoch": {"$gt": 1709164800},
            "CheckExecuted": {"$exists": False},
            "UntilEpoch": {"$lt": int(datetime.datetime.now(tz=pytz.UTC).timestamp())},
            "Type": "Temporary Ban",
            **filter_map,
        }
    ):
        try:
            guild = bot.get_guild(punishment_item["Guild"])
            if guild is None:
                guild = await bot.fetch_guild(punishment_item["Guild"])
        except discord.HTTPException:
            continue

        if not cached_servers.get(punishment_item["Guild"]):
            try:
                cached_servers[punishment_item["Guild"]] = await bot.prc_api.fetch_bans(
                    punishment_item["Guild"]
                )
            except:
                continue

        punishment_item["CheckExecuted"] = True
        await bot.punishments.update_by_id(punishment_item)

        if punishment_item["UserID"] not in [
            i.user_id for i in cached_servers[punishment_item["Guild"]]
        ]:
            continue

        sorted_punishments = sorted(
            [
                i
                async for i in bot.punishments.db.find(
                    {
                        "UserID": punishment_item["UserID"],
                        "Guild": punishment_item["Guild"],
                    }
                )
            ],
            key=lambda x: x["Epoch"],
            reverse=True,
        )
        new_sorted_punishments = []
        for item in sorted_punishments:
            if item == punishment_item:
                break
            new_sorted_punishments.append(item)

        if any([i["Type"] in ["Ban", "Temporary Ban"] for i in new_sorted_punishments]):
            continue

        await bot.prc_api.unban_user(
            punishment_item["Guild"], punishment_item["user_id"]
        )
    del cached_servers
    end_time = time.time()
    logging.warning(
        "Event tempban_checks took {} seconds".format(str(end_time - initial_time))
    )
