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
from utils.utils import is_whitelisted, run_command

@tasks.loop(minutes=2, reconnect=True)
async def check_whitelisted_car(bot):
    initial_time = time.time()
    async for items in bot.settings.db.find(
            {"ERLC.vehicle_restrictions.enabled": {"$exists": True, "$eq": True}}
    ):
        guild_id = items['_id']
        try:
            guild = await bot.fetch_guild(guild_id)
        except discord.errors.NotFound:
            continue
        try:
            whitelisted_vehicle_roles = items['ERLC'].get('vehicle_restrictions').get('roles')
            alert_channel_id = items['ERLC'].get('vehicle_restrictions').get('channel')
            whitelisted_vehicles = items['ERLC'].get('vehicle_restrictions').get('cars', [])
            alert_message = items["ERLC"].get("vehicle_restrictions").get('message',
                                                                          "You do not have the required role to use this vehicle. Switch it or risk being moderated.")
        except KeyError:
            logging.error(f"KeyError for guild {guild_id}")
            continue

        if not whitelisted_vehicle_roles or not alert_channel_id:
            logging.warning(f"Skipping guild {guild_id} due to missing whitelisted vehicle roles or alert channel.")
            continue

        if isinstance(whitelisted_vehicle_roles, int):
            exotic_roles = [guild.get_role(whitelisted_vehicle_roles)]
        elif isinstance(whitelisted_vehicle_roles, list):
            exotic_roles = [guild.get_role(role_id) for role_id in whitelisted_vehicle_roles if guild.get_role(role_id)]
        else:
            logging.warning(f"Invalid whitelisted_vehicle_roles data: {whitelisted_vehicle_roles}")
            continue

        alert_channel = bot.get_channel(alert_channel_id)
        if not alert_channel:
            try:
                alert_channel = await bot.fetch_channel(alert_channel_id)
            except discord.HTTPException:
                alert_channel = None
                logging.warning(f"Alert channel not found for guild {guild_id}")
                continue

        if not exotic_roles or not alert_channel:
            logging.warning(f"Exotic role or alert channel not found for guild {guild_id}.")
            continue
        try:
            players: list[Player] = await bot.prc_api.get_server_players(guild_id)
            vehicles: list[prc_api.ActiveVehicle] = await bot.prc_api.get_server_vehicles(guild_id)
        except prc_api.ResponseFailure:
            logging.error(f"PRC ResponseFailure for guild {guild_id}")
            continue

        logging.info(f"Found {len(vehicles)} vehicles in guild {guild_id}")
        logging.info(f"Found {len(players)} players in guild {guild_id}")

        matched = {}
        for item in vehicles:
            for x in players:
                if x.username == item.username:
                    matched[item] = x

        for vehicle, player in matched.items():
            whitelisted = False
            for whitelisted_vehicle in whitelisted_vehicles:
                if is_whitelisted(vehicle.vehicle, whitelisted_vehicle):
                    whitelisted = True
                    break
                pattern = re.compile(re.escape(player.username), re.IGNORECASE)
                member_found = False
                for member in guild.members:
                    if pattern.search(member.name) or pattern.search(member.display_name) or (
                            hasattr(member, 'global_name') and member.global_name and pattern.search(
                            member.global_name)):
                        member_found = True
                        has_exotic_role = False
                        for role in exotic_roles:
                            if role in member.roles:
                                has_exotic_role = True
                                break

                        if not has_exotic_role:
                            logging.debug(
                                f"Player {player.username} does not have the required role for their whitelisted vehicle.")
                            await run_command(bot, guild_id, player.username, alert_message)

                            if player.username not in bot.pm_counter:
                                bot.pm_counter[player.username] = 1
                                logging.debug(f"PM Counter for {player.username}: 1")
                            else:
                                bot.pm_counter[player.username] += 1
                                logging.debug(f"PM Counter for {player.username}: {bot.pm_counter[player.username]}")

                            if bot.pm_counter[player.username] >= 4:
                                logging.info(f"Sending warning embed for {player.username} in guild {guild.name}")
                                try:
                                    embed = discord.Embed(
                                        title="Whitelisted Vehicle Warning",
                                        description=f"""
                                        > Player [{player.username}](https://roblox.com/users/{player.id}/profile) has been PMed 3 times to obtain the required role for their whitelisted vehicle.
                                        """,
                                        color=RED_COLOR,
                                        timestamp=datetime.datetime.now(tz=pytz.UTC)
                                    ).set_footer(
                                        text=f"Guild: {guild.name} | Powered by ERM Systems",
                                    ).set_thumbnail(
                                        url=await get_player_avatar_url(player.id)
                                    )
                                    await alert_channel.send(embed=embed)
                                except discord.HTTPException as e:
                                    logging.error(
                                        f"Failed to send embed for {player.username} in guild {guild.name}: {e}")
                                logging.info(f"Removing {player.username} from PM counter")
                                bot.pm_counter.pop(player.username)
                        break
                    elif member_found == False:
                        logging.debug(f"Member with username {player.username} not found in guild {guild.name}.")
                        await run_command(bot, guild_id, player.username, alert_message)

                        if player.username not in bot.pm_counter:
                            bot.pm_counter[player.username] = 1
                            logging.debug(f"PM Counter for {player.username}: 1")
                        else:
                            bot.pm_counter[player.username] += 1
                            logging.debug(f"PM Counter for {player.username}: {bot.pm_counter[player.username]}")

                        if bot.pm_counter[player.username] >= 4:
                            logging.info(f"Sending warning embed for {player.username} in guild {guild.name}")
                            try:
                                embed = discord.Embed(
                                    title="Whitelisted Vehicle Warning",
                                    description=f"""
                                    > Player [{player.username}](https://roblox.com/users/{player.id}/profile) has been PMed 3 times to obtain the required role for their whitelisted vehicle.
                                    """,
                                    color=RED_COLOR,
                                    timestamp=datetime.datetime.now(tz=pytz.UTC)
                                ).set_footer(
                                    text=f"Guild: {guild.name} | Powered by ERM Systems",
                                ).set_thumbnail(
                                    url=await get_player_avatar_url(player.id)
                                )
                                await alert_channel.send(embed=embed)
                            except discord.HTTPException as e:
                                logging.error(f"Failed to send embed for {player.username} in guild {guild.name}: {e}")
                            logging.info(f"Removing {player.username} from PM counter")
                            bot.pm_counter.pop(player.username)
                        break
                    else:
                        continue
        del matched

    end_time = time.time()
    logging.warning(f"Event check_whitelisted_car took {end_time - initial_time} seconds")