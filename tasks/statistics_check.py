import asyncio
import logging
import time
from typing import Dict, List, Optional
from dataclasses import dataclass

import discord
from discord.ext import commands, tasks
from discord.errors import NotFound, Forbidden

from utils import prc_api
from utils.prc_api import Player, ServerStatus
from utils.utils import fetch_get_channel

UPDATE_INTERVAL = 90
BATCH_SIZE = 50
TIMEOUT = 10

@dataclass
class StatisticsData:
    on_duty: int
    staff_ingame: int
    moderators: int
    admins: int
    current_players: int
    join_code: str
    max_players: int
    queue: int

async def get_statistics_data(
    bot,
    guild_id: int,
    shift_management,
    prc_api_client
) -> Optional[StatisticsData]:
    """Fetch all statistics data for a guild with timeout protection."""
    try:
        async with asyncio.timeout(TIMEOUT):
            players, status, queue = await asyncio.gather(
                prc_api_client.get_server_players(guild_id),
                prc_api_client.get_server_status(guild_id),
                prc_api_client.get_server_queue(guild_id, minimal=True)
            )

            on_duty = await shift_management.shifts.db.count_documents(
                {'Guild': guild_id, 'EndEpoch': 0}
            )

            return StatisticsData(
                on_duty=on_duty,
                staff_ingame=len([p for p in players if p.permission != 'Normal']),
                moderators=len([p for p in players if p.permission == 'Server Moderator']),
                admins=len([p for p in players if p.permission == 'Server Administrator']),
                current_players=status.current_players,
                join_code=status.join_key,
                max_players=status.max_players,
                queue=queue
            )
    except (asyncio.TimeoutError, prc_api.ResponseFailure) as e:
        logging.error(f"Failed to fetch statistics for guild {guild_id}: {e}")
        return None

async def update_channel_safe(
    guild: discord.Guild,
    channel_id: int,
    stat_config: Dict,
    placeholders: Dict
) -> bool:
    """Update a single channel with error handling and rate limit protection."""
    try:
        channel = await fetch_get_channel(guild, channel_id)
        if not channel:
            logging.error(f"Channel {channel_id} not found in guild {guild.id}")
            return False

        format_string = stat_config["format"]
        new_name = format_string
        for key, value in placeholders.items():
            new_name = new_name.replace(f"{{{key}}}", str(value))

        if channel.name != new_name:
            await channel.edit(name=new_name)
            logging.info(f"Updated channel {channel_id} in guild {guild.id}")
        return True

    except (NotFound, Forbidden) as e:
        logging.error(f"Permission error updating channel {channel_id} in guild {guild.id}: {e}")
        return False
    except Exception as e:
        logging.error(f"Failed to update channel in guild {guild.id}: {e}", exc_info=True)
        return False

async def process_guild(
    bot,
    guild_id: int,
    settings: Dict
) -> None:
    """Process a single guild's statistics updates."""
    try:
        guild = await bot.fetch_guild(guild_id)
        statistics = settings["ERLC"]["statistics"]

        stats_data = await get_statistics_data(
            bot, guild_id, bot.shift_management, bot.prc_api
        )
        if not stats_data:
            return

        placeholders = {
            "onduty": stats_data.on_duty,
            "staff": stats_data.staff_ingame,
            "mods": stats_data.moderators,
            "admins": stats_data.admins,
            "players": stats_data.current_players,
            "join_code": stats_data.join_code,
            "max_players": stats_data.max_players,
            "queue": stats_data.queue
        }

        update_tasks = [
            update_channel_safe(guild, int(channel_id), stat_config, placeholders)
            for channel_id, stat_config in statistics.items()
        ]

        await asyncio.gather(*update_tasks, return_exceptions=True)

    except Exception as e:
        logging.error(f"Failed to process guild {guild_id}: {e}", exc_info=True)

@tasks.loop(seconds=UPDATE_INTERVAL, reconnect=True)
async def statistics_check(bot):
    """Main statistics check loop with improved error handling and batching."""
    start_time = time.time()
    
    try:
        async with asyncio.timeout(UPDATE_INTERVAL - 5):
            cursor = bot.settings.db.find({"ERLC.statistics": {"$exists": True}})
            guilds_to_process = []
            
            async for guild_data in cursor:
                guild_id = guild_data['_id']
                settings = await bot.settings.find_by_id(guild_id)
                
                if not settings or "ERLC" not in settings or "statistics" not in settings["ERLC"]:
                    continue
                    
                guilds_to_process.append((guild_id, settings))

            for i in range(0, len(guilds_to_process), BATCH_SIZE):
                batch = guilds_to_process[i:i + BATCH_SIZE]
                await asyncio.gather(
                    *(process_guild(bot, guild_id, settings) for guild_id, settings in batch),
                    return_exceptions=True
                )

    except asyncio.TimeoutError:
        logging.error("Statistics check timed out")
    except Exception as e:
        logging.error(f"Statistics check failed: {e}", exc_info=True)
    finally:
        end_time = time.time()
        logging.info(f"Statistics check completed in {end_time - start_time:.2f} seconds")