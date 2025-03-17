import asyncio
import logging
from discord.ext import tasks
import aiohttp
from decouple import config

from utils.prc_api import ResponseFailure


@tasks.loop(minutes=2, reconnect=True)
async def sync_weather(bot):
    chosen_filter = {
        "CUSTOM": {"_id": int(config("CUSTOM_GUILD_ID", default=0))},
        "_": {
            "_id": {
                "$nin": [
                    int(item["GuildID"] or 0)
                    async for item in bot.whitelabel.db.find({})
                ]
            }
        },
    }["CUSTOM" if config("ENVIRONMENT") == "CUSTOM" else "_"]
    try:
        logging.info("Starting weather sync task...")

        logging.info("Querying for servers with weather sync settings...")
        pipeline = [
            {
                "$match": {
                    "ERLC.weather": {"$exists": True},
                    "$or": [
                        {"ERLC.weather.sync_time": True},
                        {"ERLC.weather.sync_weather": True},
                    ],
                    "ERLC.weather.location": {"$exists": True, "$ne": ""},
                    **chosen_filter,
                }
            },
            {
                "$lookup": {
                    "from": "server_keys",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "server_key",
                }
            },
            {"$match": {"server_key": {"$ne": []}}},
        ]

        weather_service_url = config("WEATHER_SERVICE_URL")
        logging.info(f"Using weather service URL: {weather_service_url}")

        server_count = await bot.settings.db.count_documents(
            {
                "ERLC.weather": {"$exists": True},
                "$or": [
                    {"ERLC.weather.sync_time": True},
                    {"ERLC.weather.sync_weather": True},
                ],
                "ERLC.weather.location": {"$exists": True, "$ne": ""},
            }
        )
        logging.info(f"Found {server_count} servers with weather sync enabled")

        processed = 0
        async with aiohttp.ClientSession() as session:
            async for guild_data in bot.settings.db.aggregate(pipeline):
                processed += 1
                guild_id = guild_data["_id"]

                if config("ENVIRONMENT") == "CUSTOM":
                    if guild_id != config("CUSTOM_GUILD_ID", default=0):
                        continue

                weather_settings = guild_data["ERLC"]["weather"]
                location = weather_settings["location"]

                logging.info(
                    f"Processing guild {guild_id} ({processed}/{server_count})"
                )
                logging.info(f"Location: {location}")
                logging.info(
                    f"Settings: sync_weather={weather_settings.get('sync_weather')}, sync_time={weather_settings.get('sync_time')}"
                )

                try:
                    # Fetch weather data
                    logging.info(f"Fetching weather data for {location}...")
                    async with session.get(
                        f"{weather_service_url}/?location={location}"
                    ) as resp:
                        if resp.status != 200:
                            logging.error(
                                f"Failed to fetch weather data for {location}: Status {resp.status}"
                            )
                            continue
                        weather_data = await resp.json()
                        logging.info(f"Weather data received: {weather_data}")

                    # Execute weather/time commands based on settings
                    if weather_settings.get("sync_weather"):
                        try:
                            logging.info(
                                f"Setting weather to {weather_data['weatherType']} for guild {guild_id}"
                            )
                            await bot.prc_api.run_command(
                                guild_id, f":weather {weather_data['weatherType']}"
                            )
                            logging.info(
                                f"Successfully set weather for guild {guild_id}"
                            )
                        except ResponseFailure as e:
                            logging.error(
                                f"Failed to sync weather for guild {guild_id}: {str(e)}"
                            )

                    if weather_settings.get("sync_time"):
                        try:
                            logging.info(
                                f"Setting time to {weather_data['time']} for guild {guild_id}"
                            )
                            await bot.prc_api.run_command(
                                guild_id, f":time {weather_data['time']}"
                            )
                            logging.info(f"Successfully set time for guild {guild_id}")
                        except ResponseFailure as e:
                            logging.error(
                                f"Failed to sync time for guild {guild_id}: {str(e)}"
                            )

                except Exception as e:
                    logging.error(
                        f"Error syncing weather for guild {guild_id}: {str(e)}",
                        exc_info=True,
                    )

        logging.info(
            f"Weather sync task completed. Processed {processed}/{server_count} servers"
        )

    except Exception as e:
        logging.error(f"Critical error in weather sync task: {str(e)}", exc_info=True)
