import datetime
import re
import time
import discord
import pytz
from discord.ext import commands, tasks
import logging
import asyncio

from utils.constants import BLANK_COLOR
from utils.prc_api import Player
from utils import prc_api
from utils.utils import run_command, get_discord_by_roblox


@tasks.loop(minutes=2, reconnect=True)
async def discord_checks(bot):
    total_server_count = await bot.settings.db.aggregate([
        {
            '$match': {
                'ERLC': {'$exists': True},
                '$or': [
                    {'ERLC.discord_checks.channel': {'$type': 'long', '$ne': 0}}
                ]
            }
        },
        {
            '$lookup': {
                'from': 'server_keys',
                'localField': '_id',
                'foreignField': '_id',
                'as': 'server_key'
            }
        },
        {
            '$match': {
                'server_key': {'$ne': []}
            }
        },
        {
            '$count': 'total'
        }
    ]).to_list(1)
    total_server_count = total_server_count[0]['total'] if total_server_count else 0

    logging.warning(f"[ITERATE] Starting Discord Check Iteration for {total_server_count} servers")
    proccessed_servers = 0
    start_time = time.time()

    pipeline = [
        {
            '$match': {
                'ERLC': {'$exists': True},
                '$or': [
                    {'ERLC.discord_checks.channel': {'$type': 'long', '$ne': 0}}
                ]
            }
        },
        {
            '$lookup': {
                'from': 'server_keys',
                'localField': '_id',
                'foreignField': '_id',
                'as': 'server_key'
            }
        },
        {
            '$match': {
                'server_key': {'$ne': []}
            }
        }
    ]

    semaphore = asyncio.Semaphore(20)
    tasks = []

    async def check_servers(server):
        async with semaphore:
            try:
                guild = bot.get_guild(server['_id']) or await bot.fetch_guild(server['_id'])
                sett  = await bot.settings.db.find_by_id(guild.id)
                
                discord_check_channel = sett.get('ERLC', {}).get('discord_checks', {}).get('channel', 0)

                if discord_check_channel == 0:
                    return
                
                try:
                    players: list[Player] = await bot.prc_api.get_server_players(guild.id)

                    if not players:
                        return
                    
                    embed = discord.Embed(
                        title="Automatic Discord Checks",
                        color=BLANK_COLOR,
                    ).set_footer(
                        text=f"PM has been sent to the users"
                    )

                    guild_members_dict = {}
                    for member in guild.members:
                        if member.bot:
                            continue
                        keys = {
                            member.name.lower(): member,
                            member.display_name.lower(): member,
                        }
                        if hasattr(member, 'global_name') and member.global_name:
                            keys[member.global_name.lower()] = member
                        for key in keys:
                            if key not in guild_members_dict:
                                guild_members_dict[key] = []
                            guild_members_dict[key].append(member)

                    all_users = []
                    for player in players:
                        player_username_lower = player.username.lower()

                        if player_username_lower in guild_members_dict and guild_members_dict[player_username_lower]:
                            continue

                        try:
                            discord_id = await get_discord_by_roblox(bot, player.username)
                            if discord_id:
                                member = guild.get_member(discord_id)
                                if member:
                                    continue
                        except discord.HTTPException:
                            pass

                        embed.description += f"> [{player.username}](https://roblox.com/users/{player.id}/profile)\n"
                        all_users.append(player.username)   

                    if all_users:
                        all_users_str = ", ".join(all_users)
                        discord_check_message = sett.get('ERLC', {}).get('discord_checks', {}).get('message', "You are not in the communication server. Please join the server to avoid being kicked.")
                        await run_command(bot, guild.id, all_users_str, discord_check_message)

                    if not all_users:
                        return

                    channel = guild.get_channel(discord_check_channel)
                    if not channel:
                        logging.error(f"Channel not found for guild {guild.id}")
                        return
                    
                    await channel.send(embed=embed)

                except prc_api.ResponseFailure:
                    logging.error(f"PRC ResponseFailure for guild {guild.id}")

            except discord.HTTPException:
                logging.error(f"Error fetching guild {server['_id']}")

    async for server in bot.settings.db.aggregate(pipeline):
        tasks.append(check_servers(server))
        proccessed_servers += 1
        if proccessed_servers % 10 == 0:
            logging.warning(f"[ITERATE] Discord Check Iteration proccessed {proccessed_servers} / {total_server_count} servers")

    await asyncio.gather(*tasks)
    end_time = time.time()
    logging.warning(f"[ITERATE] Discord Check Iteration finished in {end_time - start_time} seconds")
    logging.warning(f"[ITERATE] Next Discord Check Iteration in 2 minutes")
                        
