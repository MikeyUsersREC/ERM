import re

import discord
from discord.ext import commands, tasks
import time
import logging
import asyncio
import datetime
from utils.utils import fetch_get_channel
from utils import prc_api
from utils.constants import BLANK_COLOR, GREEN_COLOR, RED_COLOR


@tasks.loop(seconds=90, reconnect=True)
async def iterate_prc_logs(bot):
    try:
        server_count = await bot.settings.db.aggregate([
            {
                '$match': {
                    'ERLC': {'$exists': True},
                    '$or': [
                        {'ERLC.rdm_channel': {'$type': 'long', '$ne': 0}},
                        {'ERLC.kill_logs': {'$type': 'long', '$ne': 0}},
                        {'ERLC.player_logs': {'$type': 'long', '$ne': 0}},
                        {"ERLC.welcome_message": {"$exists": True}},
                        {"ERLC.team_restrictions": {"$exists": True}}
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
        server_count = server_count[0]['total'] if server_count else 0

        logging.warning(f"[ITERATE] Starting iteration for {server_count} servers")
        processed = 0
        start_time = time.time()

        pipeline = [
            {
                '$match': {
                    'ERLC': {'$exists': True},
                    '$or': [
                        {'ERLC.rdm_channel': {'$type': 'long', '$ne': 0}},
                        {'ERLC.kill_logs': {'$type': 'long', '$ne': 0}},
                        {'ERLC.player_logs': {'$type': 'long', '$ne': 0}},
                        {"ERLC.welcome_message": {"$exists": True}},
                        {"ERLC.team_restrictions": {"$exists": True}}
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

        semaphore = asyncio.Semaphore(20)  # Limit concurrent API requests to 20
        tasks = []

        async def process_guild(items):
            async with semaphore:
                try:
                    guild = bot.get_guild(items["id"]) or await bot.fetch_guild(items['_id'])
                    settings = await bot.settings.find_by_id(guild.id)
                    erlc_settings = settings.get('ERLC', {})

                    channels = {
                        'kill_logs': erlc_settings.get('kill_logs'),
                        'player_logs': erlc_settings.get('player_logs')
                    }

                    channels = {k: await fetch_get_channel(guild, v) for k, v in channels.items() if v}
                    has_welcome_message = bool(erlc_settings.get("welcome_message", False))
                    has_team_restrictions = bool(erlc_settings.get("team_restrictions"))

                    if not channels and not has_welcome_message and not has_team_restrictions:
                        return

                    kill_logs, player_logs = await fetch_logs_with_retry(guild.id, bot)
                    subtasks = []

                    if has_welcome_message:
                        last_timestamp = bot.log_tracker.get_last_timestamp(guild.id, 'player_logs')
                        latest_timestamp = await send_welcome_message(bot, settings, guild.id, player_logs, last_timestamp)
                        bot.log_tracker.update_timestamp(guild.id, "welcome_message", latest_timestamp)

                    if has_team_restrictions:
                        await check_team_restrictions(bot, settings, guild.id,
                                                      await bot.prc_api.get_server_players(guild.id))

                    if 'kill_logs' in channels and kill_logs:
                        last_timestamp = bot.log_tracker.get_last_timestamp(guild.id, 'kill_logs')
                        embeds, latest_timestamp = process_kill_logs(kill_logs, last_timestamp)
                        if embeds:
                            subtasks.append(send_log_batch(channels['kill_logs'], embeds))
                            bot.log_tracker.update_timestamp(guild.id, 'kill_logs', latest_timestamp)

                    if 'player_logs' in channels and player_logs:
                        last_timestamp = bot.log_tracker.get_last_timestamp(guild.id, 'player_logs')
                        embeds, latest_timestamp = process_player_logs(player_logs, last_timestamp)
                        if embeds:
                            subtasks.append(send_log_batch(channels['player_logs'], embeds))
                            bot.log_tracker.update_timestamp(guild.id, 'player_logs', latest_timestamp)

                    if subtasks:
                        await asyncio.gather(*subtasks, return_exceptions=True)

                except Exception as e:
                    logging.error(f"Error processing guild {items['_id']}: {e}")

        async for items in bot.settings.db.aggregate(pipeline):
            tasks.append(process_guild(items))
            processed += 1
            if processed % 10 == 0:
                logging.warning(f"[ITERATE] Queued {processed}/{server_count} servers")

        await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        logging.warning(
            f"[ITERATE] Completed task! Processed {processed} servers in {end_time - start_time:.2f} seconds")

    except Exception as e:
        logging.error(f"[ITERATE] Error in iteration: {str(e)}", exc_info=True)


async def fetch_logs_with_retry(guild_id, bot, retries=3):
    """Helper function to fetch logs with retry logic"""
    for attempt in range(retries):
        try:
            kill_logs = await bot.prc_api.fetch_kill_logs(guild_id)
            player_logs = await bot.prc_api.fetch_player_logs(guild_id)
            return kill_logs, player_logs
        except prc_api.ResponseFailure as e:
            if e.status_code == 429 and attempt < retries - 1:
                retry_after = float(e.response.get('retry_after', 5))
                await asyncio.sleep(retry_after)
                continue
            raise
    return None, None


async def send_log_batch(channel, embeds):
    """Helper function to send log embeds in batches"""
    if not embeds:
        return
    # Split embeds into chunks of 10 (Discord's limit)
    for i in range(0, len(embeds), 10):
        chunk = embeds[i:i + 10]
        try:
            await channel.send(embeds=chunk)
        except discord.HTTPException as e:
            logging.error(f"Failed to send log batch: {e}")


def process_kill_logs(kill_logs, last_timestamp):
    """Process kill logs and return embeds"""
    embeds = []
    latest_timestamp = last_timestamp

    for log in sorted(kill_logs):
        if log.timestamp <= last_timestamp:
            continue

        latest_timestamp = max(latest_timestamp, log.timestamp)
        embed = discord.Embed(
            title="Kill Log",
            color=BLANK_COLOR,
            description=f"[{log.killer_username}](https://roblox.com/users/{log.killer_user_id}/profile) killed [{log.killed_username}](https://roblox.com/users/{log.killed_user_id}/profile) • <t:{int(log.timestamp)}:T>"
        )
        embeds.append(embed)

    return embeds, latest_timestamp


def process_player_logs(player_logs, last_timestamp):
    """Process player logs and return embeds"""
    embeds = []
    latest_timestamp = last_timestamp

    for log in sorted(player_logs):
        if log.timestamp <= last_timestamp:
            continue

        latest_timestamp = max(latest_timestamp, log.timestamp)
        embed = discord.Embed(
            title=f"Player {'Join' if log.type == 'join' else 'Leave'} Log",
            description=f"[{log.username}](https://roblox.com/users/{log.user_id}/profile) {'joined the server' if log.type == 'join' else 'left the server'} • <t:{int(log.timestamp)}:T>",
            color=GREEN_COLOR if log.type == 'join' else RED_COLOR
        )
        embeds.append(embed)

    return embeds, latest_timestamp


async def is_username_found(username: str, members: list[discord.Member]) -> bool:
    pattern = re.compile(re.escape(username), re.IGNORECASE)
    member_found = False
    for member in members:
        if pattern.search(member.name) or pattern.search(member.display_name) or (
                hasattr(member, 'global_name') and member.global_name and pattern.search(
            member.global_name)):
            member_found = True
            break
    return member_found


async def send_welcome_message(bot, settings, guild_id, player_logs, last_timestamp) -> int:
    """Send welcome messages to new players"""
    welcome_message = settings["ERLC"].get("welcome_message", "")

    player_names = {}
    for log in sorted(player_logs, key=lambda x: x.timestamp):
        if log.timestamp <= last_timestamp:
            continue
        if log.timestamp <= bot.start_time:
            continue
        if log.type == "join":
            player_names[log.username] = log.timestamp
        else:
            if player_names.get(log.username, None) is not None:
                if player_names[log.username] < log.timestamp:
                    del player_names[log.username]
    players = player_names.keys()
    if len(players) == 0:
        return sorted(player_logs, key=lambda x: x.timestamp, reverse=True)[0].timestamp
    try:
        await bot.prc_api.run_command(guild_id, f":pm {','.join(players)} {welcome_message}")
    except prc_api.ResponseFailure:
        pass
    return sorted(player_logs, key=lambda x: x.timestamp, reverse=True)[0].timestamp


async def check_team_restrictions(bot, settings, guild_id, players):
    """Check and enforce team restrictions"""
    logging.info(f"Checking team restrictions for server {guild_id}")
    team_restrictions = settings["ERLC"].get("team_restrictions", {})
    if team_restrictions in [None, {}]:
        return
    teams = {}
    for item in players:
        if teams.get(item.team):
            teams[item.team].append(item)
        else:
            teams[item.team] = [item]

    load_against = []  # [Username]
    pm_against = {}  # Message: [Username]
    send_to = {}  # Channel_ID: [Username, Team]
    kick_against = []  # [Username]

    min_count_for_compute = team_restrictions.get("min_players", 0)
    if min_count_for_compute >= len(players):
        return

    guild = bot.get_guild(guild_id) or await bot.fetch_guild(guild_id)
    all_roles = await guild.fetch_roles()
    for team_name, plrs in teams.items():
        if team_restrictions.get(team_name) is not None:
            restriction = team_restrictions.get(team_name)
            roles = restriction["required_roles"]
            actual_roles = [discord.utils.get(all_roles, id=r) for r in roles]
            members = []
            for item in actual_roles:
                for member in item.members:
                    if member not in members:
                        members.append(member)
            for plr in plrs:
                is_found = await is_username_found(plr.username, members)
                if not is_found:
                    do_load = restriction["load_player"]
                    if do_load:
                        load_against.append(plr.username)
                    if restriction["warn_player"]:
                        if pm_against.get(restriction["warning_message"]) is not None:
                            pm_against[restriction["warning_message"]].append(plr.username)
                        else:
                            pm_against[restriction["warning_message"]] = [plr.username]
                    if restriction["notification_channel"] != 0:
                        if send_to.get(restriction["notification_channel"]) is None:
                            send_to[restriction["notification_channel"]] = [plr.username, plr.team]
                        else:
                            send_to[restriction["notification_channel"]].append([plr.username, plr.team])
                    if restriction["kick_after_infractions"] != 0:
                        if bot.team_restrictions_infractions.get(guild_id) is not None:
                            if not bot.team_restrictions_infractions[guild_id].get(plr.username):
                                bot.team_restrictions_infractions[guild_id][plr.username] = 1
                            else:
                                bot.team_restrictions_infractions[guild_id][plr.username] += 1
                        else:
                            bot.team_restrictions_infractions[guild_id] = {
                                plr.username: 1
                            }
                        if bot.team_restrictions_infractions[guild_id][plr.username] >= restriction[
                            "kick_after_infractions"]:
                            kick_against.append(plr.username)
                            bot.team_restrictions_infractions[guild_id][plr.username] = 0
    if len(load_against) > 0:
        try:
            await bot.prc_api.run_command(guild_id, f":load {','.join(load_against)}")
        except:
            logging.warning("PRC API Rate limit reached when loading.")
    for message, plrs_to_send in pm_against.items():
        try:
            await bot.scheduled_pm_queue.put((guild_id, ','.join(plrs_to_send), message))
            logging.warning("Added to scheduled PM queue.")
        except Exception as e:
            logging.warning("PRC API Rate limit reached when PMing.")
    if len(kick_against) > 0:
        try:
            await bot.prc_api.run_command(guild_id, f":kick {','.join(kick_against)}")
        except:
            logging.warning("PRC API Rate limit reached when kicking.")
    send_by_teams = {}
    team_to_channel = {}
    for channel, player_team_union in send_to.items():
        if send_by_teams.get(player_team_union[1]) is None:
            send_by_teams[player_team_union[1]] = [player_team_union[0]]
            team_to_channel[player_team_union[1]] = channel
        else:
            send_by_teams[player_team_union[1]].append(player_team_union[0])
    for team, channel in team_to_channel.items():
        players = send_by_teams[team]
        mentioned_roles = team_restrictions[team]["mentioned_roles"]
        missing_roles = team_restrictions[team]["required_roles"]
        try:
            channel = await fetch_get_channel(guild, channel)
        except discord.HTTPException:
            continue
        listed_users = ""
        for item in players:
            listed_users += f"- {item}\n"
        await channel.send(
            ', '.join([f"<@&{role}>" for role in mentioned_roles]),
            embed=discord.Embed(
                title="Team Restrictions",
                description=f"The following individuals are on the **{team}** team without holding any of the roles {', '.join([f'<@&{role}>' for role in missing_roles])}.\n{listed_users}",
                color=BLANK_COLOR
            )
        )