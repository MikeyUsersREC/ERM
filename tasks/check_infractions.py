import discord
import logging
from discord.ext import commands, tasks
import time
import datetime
from utils.constants import BLANK_COLOR
import pytz

@tasks.loop(hours=1)
async def check_infractions(bot):
    try:
        current_time = datetime.datetime.now(tz=pytz.UTC).timestamp()
        initial_time = time.time()

        async for infraction in bot.db.infractions.find({"temp_roles_expire_at": {"$exists": True}}):
            if infraction["temp_roles_expire_at"] <= current_time:
                try:
                    guild = bot.get_guild(infraction["guild_id"])
                    if not guild:
                        continue
                        
                    member = guild.get_member(infraction["user_id"])
                    if not member:
                        continue

                    if infraction.get("temp_roles_added"):
                        roles_to_remove = []
                        for role_id in infraction["temp_roles_added"]:
                            role = guild.get_role(int(role_id))
                            if role:
                                roles_to_remove.append(role)
                        if roles_to_remove:
                            await member.remove_roles(*roles_to_remove, reason="Temporary infraction role duration expired")

                    if infraction.get("temp_roles_removed"):
                        roles_to_add = []
                        for role_id in infraction["temp_roles_removed"]:
                            role = guild.get_role(int(role_id))
                            if role:
                                roles_to_add.append(role)
                        if roles_to_add:
                            await member.add_roles(*roles_to_add, reason="Temporary infraction role removal expired")

                    await bot.db.infractions.update_one(
                        {"_id": infraction["_id"]},
                        {"$unset": {
                            "temp_roles_expire_at": "",
                            "temp_roles_added": "",
                            "temp_roles_removed": ""
                        }}
                    )
                except Exception as e:
                    logging.error(f"Error processing temporary roles for infraction {infraction['_id']}: {str(e)}")

        cached_settings = {}
        async for infraction in bot.db.infractions.find({
            "revoked": {"$ne": True},
            "check_executed": {"$exists": False}
        }):
            try:
                guild_id = infraction["guild_id"]
                guild = bot.get_guild(guild_id)
                if not guild:
                    continue

                if not cached_settings.get(guild_id):
                    settings = await bot.settings.find_by_id(guild_id)
                    if not settings or not settings.get("infractions", {}).get("infractions"):
                        continue
                    cached_settings[guild_id] = settings

                settings = cached_settings[guild_id]
                infraction_type = next((t for t in settings["infractions"]["infractions"] 
                                      if t.get("name") == infraction["type"]), None)
                
                if not infraction_type or \
                   not infraction_type.get("expiry", {}).get("enabled") or \
                   not infraction_type.get("expiry", {}).get("duration"):
                    continue

                expiry_days = infraction_type["expiry"]["duration"]
                expiry_seconds = expiry_days * 24 * 60 * 60
                
                if infraction["timestamp"] <= current_time - expiry_seconds:
                    member = guild.get_member(infraction["user_id"])
                    if member:
                        try:
                            embed = discord.Embed(
                                title="Infraction Expired",
                                description=f"Your infraction in {guild.name} has expired.",
                                color=BLANK_COLOR
                            )
                            embed.add_field(
                                name="Details",
                                value=(
                                    f"> **Type:** {infraction['type']}\n"
                                    f"> **Reason:** {infraction['reason']}\n"
                                    f"> **Expired At:** <t:{int(current_time)}:F>"
                                ),
                                inline=False
                            )
                            await member.send(embed=embed)
                        except discord.Forbidden:
                            logging.warning(f"Could not send DM to {member.id} about expired infraction")
                        
                        role_changes = infraction_type.get("role_changes", {})
                        
                        if role_changes.get("add", {}).get("roles"):
                            roles_to_remove = []
                            for role_id in role_changes["add"]["roles"]:
                                role = guild.get_role(int(role_id["$numberLong"]) if isinstance(role_id, dict) else int(role_id))
                                if role:
                                    roles_to_remove.append(role)
                            if roles_to_remove:
                                await member.remove_roles(*roles_to_remove, reason="Infraction expired")

                        if role_changes.get("remove", {}).get("roles"):
                            roles_to_add = []
                            for role_id in role_changes["remove"]["roles"]:
                                role = guild.get_role(int(role_id["$numberLong"]) if isinstance(role_id, dict) else int(role_id))
                                if role:
                                    roles_to_add.append(role)
                            if roles_to_add:
                                await member.add_roles(*roles_to_add, reason="Infraction expired")

                        if infraction_type.get("remove_ingame_perms"):
                            try:
                                await bot.prc_api.run_command(guild_id, f":mod {infraction['user_id']}")
                            except Exception as e:
                                logging.error(f"Failed to restore in-game permissions: {str(e)}")

                    await bot.db.infractions.update_one(
                        {"_id": infraction["_id"]},
                        {
                            "$set": {
                                "revoked": True,
                                "revoked_at": current_time,
                                "reason": infraction["reason"] + " - Revoked by system since this infraction expired.",
                                "check_executed": True
                            }
                        }
                    )

            except Exception as e:
                logging.error(f"Error processing infraction expiry for {infraction['_id']}: {str(e)}")

        end_time = time.time()
        logging.warning('Event check_infractions took {} seconds'.format(str(end_time - initial_time)))

    except Exception as e:
        logging.error(f"Error in check_infractions task: {str(e)}")
