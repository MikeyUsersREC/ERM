import datetime
import re
import time
import discord
import pytz
from discord.ext import commands, tasks
import logging

from utils.constants import RED_COLOR
from utils.prc_api import Player
from utils import prc_api
from utils.utils import is_whitelisted, run_command, get_player_avatar_url

@tasks.loop(minutes=2, reconnect=True)
async def check_whitelisted_car(bot):
    initial_time = time.time()
    logging.warning("[ITERATE] Starting Whitelisted Vehicle Check Iteration")
    async for items in bot.settings.db.find({"ERLC.vehicle_restrictions.enabled": True}):
        guild_id = items['_id']

        try:
            guild = await bot.fetch_guild(guild_id)
        except discord.errors.NotFound:
            logging.error(f"Guild {guild_id} not found")
            continue

        try:
            settings = items.get('ERLC', {}).get('vehicle_restrictions', {})
            whitelisted_vehicle_roles = settings.get('roles', [])
            alert_channel_id = settings.get('channel', 0)
            whitelisted_vehicles = settings.get('cars', [])
            alert_message = settings.get('message', 
                "You do not have the required role to use this vehicle. Switch it or risk being moderated.")
        except KeyError:
            logging.error(f"Invalid settings structure for guild {guild_id}")
            continue

        if not whitelisted_vehicle_roles or not alert_channel_id or not whitelisted_vehicles:
            logging.warning(f"Missing required settings for guild {guild_id}")
            continue

        exotic_roles = []
        if isinstance(whitelisted_vehicle_roles, int):
            role = guild.get_role(whitelisted_vehicle_roles)
            if role:
                exotic_roles.append(role)
        elif isinstance(whitelisted_vehicle_roles, list):
            exotic_roles = [guild.get_role(role_id) for role_id in whitelisted_vehicle_roles if guild.get_role(role_id)]
        
        if not exotic_roles:
            logging.warning(f"No valid roles found for guild {guild_id}")
            continue

        try:
            alert_channel = bot.get_channel(alert_channel_id) or await bot.fetch_channel(alert_channel_id)
        except discord.HTTPException:
            logging.warning(f"Alert channel {alert_channel_id} not found for guild {guild_id}")
            continue

        try:
            players = await bot.prc_api.get_server_players(guild_id)
            vehicles = await bot.prc_api.get_server_vehicles(guild_id)
            logging.info(f"Found {len(vehicles)} vehicles and {len(players)} players in guild {guild_id}")
        except prc_api.ResponseFailure:
            logging.error(f"Failed to fetch data from PRC API for guild {guild_id}")
            continue

        player_lookup = {player.username.lower(): player for player in players}

        for vehicle in vehicles:
            username = vehicle.username.lower()
            if username not in player_lookup:
                continue
                
            player = player_lookup[username]

            vehicle_whitelisted = any(
                is_whitelisted(vehicle.vehicle, whitelisted_vehicle) 
                for whitelisted_vehicle in whitelisted_vehicles
            )
            
            if not vehicle_whitelisted:
                continue

            pattern = re.compile(re.escape(player.username), re.IGNORECASE)
            member = next(
                (m for m in guild.members if pattern.search(m.name) 
                 or pattern.search(m.display_name) 
                 or (m.global_name and pattern.search(m.global_name))),
                None
            )

            if member is None or not any(role in member.roles for role in exotic_roles):
                await handle_unauthorized_vehicle(bot, guild, alert_channel, player, alert_message)

    end_time = time.time()
    logging.warning(f"[ITERATE] Whitelisted Vehicle Check Iteration took {end_time - initial_time:.2f} seconds")

async def handle_unauthorized_vehicle(bot, guild, alert_channel, player, alert_message):
    """Handle unauthorized vehicle usage"""
    await run_command(bot, guild.id, player.username, alert_message)

    if player.username not in bot.pm_counter:
        bot.pm_counter[player.username] = 1
    else:
        bot.pm_counter[player.username] += 1
    
    logging.debug(f"PM Counter for {player.username}: {bot.pm_counter[player.username]}")

    if bot.pm_counter[player.username] >= 4:
        try:
            embed = discord.Embed(
                title="Whitelisted Vehicle Warning",
                description=f"> Player [{player.username}](https://roblox.com/users/{player.id}/profile) "
                           f"has been PMed 3 times to obtain the required role for their whitelisted vehicle.",
                color=RED_COLOR,
                timestamp=datetime.datetime.now(tz=pytz.UTC)
            )
            embed.set_footer(text=f"Guild: {guild.name} | Powered by ERM Systems")
            embed.set_thumbnail(url=await get_player_avatar_url(player.id))
            
            await alert_channel.send(embed=embed)
            bot.pm_counter.pop(player.username)
            logging.info(f"Sent warning embed and reset counter for {player.username}")
        except discord.HTTPException as e:
            logging.error(f"Failed to send embed for {player.username}: {e}")
