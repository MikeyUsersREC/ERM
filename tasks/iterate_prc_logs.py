import re
from typing import List
import discord
from discord.ext import commands, tasks
import time
import logging
import asyncio
import aiohttp
import pytz
import roblox
import datetime

from sentry_sdk import push_scope, capture_exception

from utils.utils import fetch_get_channel, error_gen
from utils import prc_api
from utils.constants import BLANK_COLOR, GREEN_COLOR, RED_COLOR
from menus import AvatarCheckView


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
                    guild = bot.get_guild(items["_id"]) or await bot.fetch_guild(items['_id'])
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
                        last_timestamp = bot.log_tracker.get_last_timestamp(guild.id, 'welcome_message')
                        latest_timestamp = await send_welcome_message(bot, settings, guild.id, player_logs,
                                                                      last_timestamp)
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
                        embeds, latest_timestamp = await process_player_logs(bot, settings, guild.id, player_logs, last_timestamp)
                        if embeds:
                            subtasks.append(send_log_batch(channels['player_logs'], embeds))
                            bot.log_tracker.update_timestamp(guild.id, 'player_logs', latest_timestamp)

                    if erlc_settings.get("kick_timer", {}).get("enabled", False):
                        await handle_kick_timer(bot, settings, guild.id, player_logs)

                    if subtasks:
                        await asyncio.gather(*subtasks, return_exceptions=True)

                except Exception as e:
                    error_id = error_gen()
                    with push_scope() as scope:
                        scope.set_tag("error_id", error_id)
                        scope.level = "error"

                        capture_exception(e)
                logging.error(f"Error processing guild {items['_id']}: {error_id}")

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


async def process_player_logs(bot, settings, guild_id, player_logs, last_timestamp):
    """Process player logs and return embeds"""
    embeds = []
    latest_timestamp = last_timestamp
    new_join_ids = []

    for log in sorted(player_logs):
        if log.timestamp <= last_timestamp:
            continue
        if log.type == 'join':
            new_join_ids.append(log.user_id)

        latest_timestamp = max(latest_timestamp, log.timestamp)
        embed = discord.Embed(
            title=f"Player {'Join' if log.type == 'join' else 'Leave'} Log",
            description=f"[{log.username}](https://roblox.com/users/{log.user_id}/profile) {'joined the server' if log.type == 'join' else 'left the server'} • <t:{int(log.timestamp)}:T>",
            color=GREEN_COLOR if log.type == 'join' else RED_COLOR
        )
        embeds.append(embed)

    if new_join_ids and settings.get('ERLC', {}).get('avatar_check', {}).get('channel'):
        enabled = settings.get('ERLC', {}).get('avatar_check', {}).get("enabled", True)
        if not enabled:
            return

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    'https://avatar-checking.jxselinxe.workers.dev/internal/check_avatars',
                    json={'robloxIds': new_join_ids},
                    timeout=10
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('success'):
                            for user_id, result in data['data']['results'].items():
                                is_unrealistic = result.get('unrealistic', False)
                                has_blacklisted_items = False
                                blacklisted_reasons = []
                                
                                # Check for blacklisted items
                                blacklisted_items = settings.get('ERLC', {}).get('avatar_check', {}).get('blacklisted_items', [])
                                if blacklisted_items:
                                    for item in result.get('current_items', []):
                                        if item['id'] in blacklisted_items:
                                            has_blacklisted_items = True
                                            blacklisted_reasons.append(f"Using a blacklisted item: {item['name']}")
                                
                                if (is_unrealistic and not any(item in (settings.get('ERLC', {}).get('unrealistic_items_whitelist', []) or []) 
                                             for item in result.get('unrealistic_item_ids', []))) or has_blacklisted_items:
                                    
                                    reasons = result.get('reasons', []) + blacklisted_reasons
                                    
                                    channel_id = settings['ERLC']['avatar_check']['channel']
                                    guild = bot.get_guild(guild_id) or await bot.fetch_guild(guild_id)
                                    channel = await fetch_get_channel(guild, channel_id)
                                    if channel:
                                        try:
                                            user = await bot.roblox.get_user(int(user_id))
                                            avatar = await bot.roblox.thumbnails.get_user_avatar_thumbnails([user], type=roblox.thumbnails.AvatarThumbnailType.headshot)
                                            avatar_url = avatar[0].image_url
                                        except:
                                            return
                                        
                                        view = AvatarCheckView(bot, user_id, settings['ERLC']['avatar_check'].get('message', ''))
                                        await channel.send(
                                            content=', '.join([f'<@&{role}>' for role in settings['ERLC']['avatar_check'].get('mentioned_roles', [])]),
                                            embed=discord.Embed(
                                                title="Unrealistic Avatar Detected",
                                                description="We have detected that a player in your server has an unrealistic avatar.",
                                                color=0x2C2F33
                                            ).add_field(
                                                name="Player Information",
                                                value=f"> **Username:** [{user.name}](https://roblox.com/users/{user_id}/profile)\n> **User ID:** {user_id}\n> **Reason:** {', '.join(reasons)}"
                                            ).set_thumbnail(url=avatar_url),
                                            view=view,
                                            allowed_mentions=discord.AllowedMentions.all()
                                        )
                                        
                                        if settings['ERLC']['avatar_check'].get('message'):
                                            await bot.scheduled_pm_queue.put((guild_id, user.name, settings['ERLC']['avatar_check']['message']))
            except Exception as e:
                    error_id = error_gen()
                    with push_scope() as scope:
                        scope.set_tag("error_id", error_id)
                        scope.level = "error"

                        capture_exception(e)

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
    for log in sorted(player_logs, key=lambda x: x.timestamp, reverse=True):
        if log.timestamp <= last_timestamp:
            break
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
    
    enabled = team_restrictions.get("enabled", True)
    if not enabled:
        return

    guild = bot.get_guild(guild_id) or await bot.fetch_guild(guild_id)
    all_roles = await guild.fetch_roles()
    for team_name, plrs in teams.items():
        if team_restrictions.get(team_name) is not None:
            restriction = team_restrictions.get(team_name)
            roles = restriction["required_roles"]
            if roles == []:
                continue
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
                        if not isinstance(send_to.get(restriction["notification_channel"]), list):
                            send_to[restriction["notification_channel"]] = [[plr.username, plr.team]]
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
        filtered_load = [username for username in load_against if username.strip() and len(username.strip()) >= 3]
        if filtered_load:
            cmd = f":load {','.join(filtered_load)}"
            try:
                await bot.prc_api.run_command(guild_id, cmd)
            except:
                logging.warning("PRC API Rate limit reached when loading.")
        else:
            logging.warning("Skipped sending load command - usernames too short or empty")

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
    for channel, players_team_unions in send_to.items():
        for player_team_union in players_team_unions:
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
        per_user_action_list = ""
        for index, item in enumerate(players):
            per_user_action_list += f"- **{index + 1}.** {item}\n  - **Actions:** "
            preappended_items = 0
            if item.lower() in [i.lower() for i in kick_against]:
                per_user_action_list += "Kicked"
                preappended_items += 1
            users_to_pm = pm_against.values()
            total_users = []
            for userlist in users_to_pm:
                for user in userlist:
                    if user.lower() not in total_users:
                        total_users.append(user.lower())
            if item.lower() in total_users:  # This whole thing is entirely overengineered, and I should've just used
                # ','.join(list) but I didn't realise this before writing this whole
                # algorithm :skull:
                if preappended_items > 0:
                    per_user_action_list += ", Private Messaged"
                else:
                    per_user_action_list += "Private Messaged"
                preappended_items += 1
            if item.lower() in [i.lower() for i in load_against]:
                if preappended_items > 0:
                    per_user_action_list += ", Loaded"
                else:
                    per_user_action_list += "Loaded"
                preappended_items += 1
            per_user_action_list += "\n"
        embed = discord.Embed(
            title="Team Restrictions",
            description=f"Your team restriction for the `{team}` team has affected **{len(players)}** players.",
            color=BLANK_COLOR
        ).add_field(
            name=f"Players Affected [{len(players)}]",
            inline=False,
            value=per_user_action_list
        )

        await channel.send(
            ', '.join([f"<@&{role}>" for role in mentioned_roles]),
            embed=embed,
            allowed_mentions=discord.AllowedMentions.all()
        )


async def handle_kick_timer(bot, settings, guild_id, player_logs):
    """Handle kick timer logic using command logs"""
    kick_timer_settings = settings["ERLC"]["kick_timer"]
    punishment = kick_timer_settings.get("punishment", "ban")
    time_limit = kick_timer_settings.get("time", 1800)  # default to 30 minutes if not set

    if not hasattr(bot, 'kicked_users'):
        bot.kicked_users = {}

    if guild_id not in bot.kicked_users:
        bot.kicked_users[guild_id] = {}

    command_logs = await bot.prc_api.fetch_server_logs(guild_id)

    for log in command_logs:
        if ':kick' in log.command:
            # extract the username from the command
            parts = log.command.split()
            if len(parts) > 1:
                kicked_username = parts[1]
                bot.kicked_users[guild_id][kicked_username] = log.timestamp

    rejoined_users = []  # list of user IDs who rejoined within the time limit
    for log in player_logs:
        if log.type == 'join':
            user_id = log.user_id
            if user_id in bot.kicked_users[guild_id]:
                kick_timestamp = bot.kicked_users[guild_id][user_id]
                if (log.timestamp - kick_timestamp) <= time_limit:
                    rejoined_users.append(user_id)
                # remove the user from the kicked list after
                del bot.kicked_users[guild_id][user_id]

    if rejoined_users:
        if punishment == "ban":
            await bot.prc_api.run_command(guild_id, f":ban {','.join(map(str, rejoined_users))}")
        else:
            await bot.prc_api.run_command(guild_id, f":kick {','.join(map(str, rejoined_users))}")

        # log moderation actions
        for user_id in rejoined_users:
            user = await bot.roblox.get_user(int(user_id))
            user_name = user.name
            await bot.punishments.insert_warning(
                staff_id=978662093408591912,
                staff_name="ERM Systems",
                user_id=user_id,
                user_name=user_name,
                guild_id=guild_id,
                reason="Rejoined within kick timer",
                moderation_type=punishment,
                time_epoch=int(datetime.datetime.now(tz=pytz.UTC).timestamp())
            )
