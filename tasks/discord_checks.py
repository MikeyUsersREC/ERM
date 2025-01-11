import datetime
import re
import time
import discord
import pytz
from discord.ext import commands, tasks
import logging
import asyncio
from typing import List, Dict, Optional, Set

from utils.constants import BLANK_COLOR
from utils.prc_api import Player
from utils import prc_api
from utils.utils import run_command, get_discord_by_roblox

class PunishmentTracker:
    def __init__(self, bot):
        self.bot = bot
        self.infractions: Dict[int, Dict[str, int]] = {}

    async def add_puishment(self, guild_id: int, username: str) -> int:
        if guild_id not in self.infractions:
            self.infractions[guild_id] = {}
        
        if username not in self.infractions[guild_id]:
            self.infractions[guild_id][username] = 0
            
        self.infractions[guild_id][username] += 1
        return self.infractions[guild_id][username]

    def get_puishment(self, guild_id: int, username: str) -> int:
        return self.infractions.get(guild_id, {}).get(username, 0)

    def reset_puishment(self, guild_id: int, username: str) -> None:
        if guild_id in self.infractions and username in self.infractions[guild_id]:
            del self.infractions[guild_id][username]
            
    def cleanup_guild(self, guild_id: int, active_players: Set[str]) -> List[str]:
        """
        Remove players from the tracker who are no longer in the server
        Returns list of cleaned up usernames
        """
        if guild_id not in self.infractions:
            return []
        
        removed_players = []
        for username in list(self.infractions[guild_id].keys()):
            if username not in active_players:
                self.reset_puishment(guild_id, username)
                removed_players.append(username)
                
        return removed_players

@tasks.loop(minutes=2, reconnect=True)
async def discord_checks(bot):
    if not hasattr(bot, 'punishment_tracker'):
        bot.punishment_tracker = PunishmentTracker(bot)

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
    processed_servers = 0
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

    async def handle_user_action(bot, guild_id: int, username: str, settings: dict, should_load: bool) -> bool:
        """Handle user action based on settings and return whether user should be kicked"""
        current_infractions = bot.infraction_tracker.get_puishment(guild_id, username)
        kick_after = settings.get('kick_after_infractions', 0)

        if kick_after and current_infractions + 1 >= kick_after:
            await bot.infraction_tracker.add_puishment(guild_id, username)
            bot.infraction_tracker.reset_puishment(guild_id, username)
            return True
            
        if should_load:
            await run_command(bot, guild_id, username, "/load")
        
        await bot.infraction_tracker.add_puishment(guild_id, username)
        return False

    async def check_servers(server):
        async with semaphore:
            try:
                guild = bot.get_guild(server['_id']) or await bot.fetch_guild(server['_id'])
                settings = await bot.settings.db.find_by_id(guild.id)
                
                discord_checks = settings.get('ERLC', {}).get('discord_checks', {})
                discord_check_channel = discord_checks.get('channel', 0)
                should_load = discord_checks.get('should_load', False)
                should_warn = discord_checks.get('should_warn', True)
                mentioned_roles = discord_checks.get('mentioned_roles', [])
                
                if discord_check_channel == 0:
                    return
                
                try:
                    players: list[Player] = await bot.prc_api.get_server_players(guild.id)

                    if not players:
                        return

                    active_players = {player.username for player in players}

                    removed_players = bot.infraction_tracker.cleanup_guild(guild.id, active_players)
                    if removed_players:
                        logging.info(f"Cleaned up {len(removed_players)} players from tracker in guild {guild.id}: {', '.join(removed_players)}")
                    
                    embed = discord.Embed(
                        title="Automatic Discord Checks",
                        color=BLANK_COLOR,
                        description=""
                    ).set_footer(
                        text="Action taken based on server settings"
                    )

                    guild_members_dict = {}
                    for member in guild.members:
                        if member.bot:
                            continue
                        keys = {
                            member.name.lower(): member,
                            member.display_name.lower(): member
                        }
                        if hasattr(member, 'global_name') and member.global_name:
                            keys[member.global_name.lower()] = member
                        for key in keys:
                            if key not in guild_members_dict:
                                guild_members_dict[key] = []
                            guild_members_dict[key].append(member)

                    users_to_action = []
                    users_to_kick = []

                    for player in players:
                        player_username_lower = player.username.lower()

                        if player_username_lower in guild_members_dict and guild_members_dict[player_username_lower]:
                            # Reset infractions for players who join the Discord
                            bot.infraction_tracker.reset_puishment(guild.id, player.username)
                            continue

                        try:
                            discord_id = await get_discord_by_roblox(bot, player.username)
                            if discord_id:
                                member = guild.get_member(discord_id)
                                if member:
                                    # Reset infractions for players who link their Discord
                                    bot.infraction_tracker.reset_puishment(guild.id, player.username)
                                    continue
                        except discord.HTTPException:
                            pass

                        current_infractions = bot.infraction_tracker.get_puishment(guild.id, player.username)
                        embed.description += f"> [{player.username}](https://roblox.com/users/{player.id}/profile) - Infractions: {current_infractions}\n"
                        users_to_action.append(player.username)

                        should_kick = await handle_user_action(bot, guild.id, player.username, discord_checks, should_load)
                        if should_kick:
                            users_to_kick.append(player.username)

                    if users_to_action and should_warn:
                        users_str = ", ".join(users_to_action)
                        warning_message = discord_checks.get('message', "You are not in the communication server. Please join the server to avoid being kicked.")
                        await run_command(bot, guild.id, users_str, warning_message)

                    if users_to_kick:
                        kick_str = ", ".join(users_to_kick)
                        await run_command(bot, guild.id, kick_str, "/kick")
                        embed.add_field(name="Kicked Users", value=kick_str, inline=False)

                    if not users_to_action:
                        return

                    channel = guild.get_channel(discord_check_channel)
                    if not channel:
                        logging.error(f"Channel not found for guild {guild.id}")
                        return

                    mention_text = " ".join(f"<@&{role_id}>" for role_id in mentioned_roles) if mentioned_roles else ""
                    
                    await channel.send(content=mention_text if mention_text else None, embed=embed)

                except prc_api.ResponseFailure:
                    logging.error(f"PRC ResponseFailure for guild {guild.id}")

            except discord.HTTPException:
                logging.error(f"Error fetching guild {server['_id']}")

    async for server in bot.settings.db.aggregate(pipeline):
        tasks.append(check_servers(server))
        processed_servers += 1
        if processed_servers % 10 == 0:
            logging.warning(f"[ITERATE] Discord Check Iteration processed {processed_servers} / {total_server_count} servers")

    await asyncio.gather(*tasks)
    end_time = time.time()
    logging.warning(f"[ITERATE] Discord Check Iteration finished in {end_time - start_time} seconds")
    logging.warning(f"[ITERATE] Next Discord Check Iteration in 2 minutes")