import discord
from discord.ext import tasks, commands
import logging
from utils import prc_api


@tasks.loop(seconds=10)
async def process_scheduled_pms(bot):
    try:
        logging.info("Processing scheduled PMs.")
        while not bot.scheduled_pm_queue.empty():
            pm_data = await bot.scheduled_pm_queue.get()
            guild_id, usernames, message = pm_data
            logging.info("Not empty, grabbed last queue of scheduled PMs.")
            try:
                await bot.prc_api.run_command(guild_id, f":pm {usernames} {message}")
            except prc_api.ResponseFailure as e:
                if e.status_code == 429:
                    logging.info(
                        "429 for last item in scheduled PM, putting back into queue."
                    )
                    await bot.scheduled_pm_queue.put(pm_data)
    except Exception as e:
        logging.error(f"Error in process_scheduled_pms: {e}")
