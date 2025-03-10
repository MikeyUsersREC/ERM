import datetime
import logging
import discord
from discord.ext import commands
from utils.constants import BLANK_COLOR

logger = logging.getLogger(__name__)


class OnInfractionRevoke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_infraction_revoke(self, infraction):
        try:
            guild = self.bot.get_guild(infraction["guild_id"])
            if not guild:
                return

            settings = await self.bot.settings.find_by_id(guild.id)
            if not settings or "infractions" not in settings:
                return

            member = guild.get_member(infraction["user_id"])
            if member:
                if "roles_removed" in infraction:
                    roles_to_add = []
                    for role_id in infraction["roles_removed"]:
                        role = guild.get_role(int(role_id))
                        if role and role not in member.roles:
                            roles_to_add.append(role)
                    if roles_to_add:
                        try:
                            await member.add_roles(
                                *roles_to_add,
                                reason="Infraction revoked - restoring removed roles",
                            )
                            roles_modified = True
                        except discord.HTTPException as e:
                            logger.error(
                                f"Failed to restore roles for {member.id}: {e}"
                            )

                if "roles_added" in infraction:
                    roles_to_remove = []
                    for role_id in infraction["roles_added"]:
                        role = guild.get_role(int(role_id))
                        if role and role in member.roles:
                            roles_to_remove.append(role)
                    if roles_to_remove:
                        try:
                            await member.remove_roles(
                                *roles_to_remove,
                                reason="Infraction revoked - removing added roles",
                            )
                            roles_modified = True
                        except discord.HTTPException as e:
                            logger.error(
                                f"Failed to remove added roles for {member.id}: {e}"
                            )

                infraction_config = next(
                    (
                        inf
                        for inf in settings["infractions"]["infractions"]
                        if inf["name"] == infraction["type"]
                    ),
                    None,
                )

                if infraction_config and infraction_config.get(
                    "remove_ingame_perms", False
                ):
                    try:
                        roblox_info = await self.bot.bloxlink.find_roblox(
                            infraction["user_id"]
                        )
                        if roblox_info and "robloxID" in roblox_info:
                            roblox_id = roblox_info["robloxID"]
                            if member:
                                await self.bot.prc_api.run_command(
                                    guild.id, f":mod {roblox_id}"
                                )
                    except Exception as e:
                        logger.error(f"Failed to restore in-game permissions: {e}")

                if settings.get("infractions", {}).get("dm_on_revoke", True):
                    try:
                        embed = discord.Embed(
                            title="Infraction Revoked",
                            description=f"One of your infractions in **{guild.name}** has been revoked.",
                            color=BLANK_COLOR,
                        )
                        embed.add_field(
                            name="Details",
                            value=(
                                f"> **Type:** {infraction['type']}\n"
                                f"> **Original Reason:** {infraction['reason']}\n"
                                f"> **Issued:** <t:{int(infraction['timestamp'])}:F>\n"
                                f"> **Revoked:** <t:{int(infraction['revoked_at'])}:F>"
                            ),
                            inline=False,
                        )
                        await member.send(embed=embed)
                    except discord.HTTPException:
                        pass

            if log_channel_id := settings.get("infractions", {}).get("log_channel"):
                if log_channel := guild.get_channel(int(log_channel_id)):
                    embed = discord.Embed(
                        title="Infraction Revoked",
                        color=BLANK_COLOR,
                        timestamp=datetime.datetime.now(),
                    )
                    embed.add_field(
                        name="Details",
                        value=(
                            f"> **User:** <@{infraction['user_id']}>\n"
                            f"> **Type:** {infraction['type']}\n"
                            f"> **Original Reason:** {infraction['reason']}\n"
                            f"> **Original Issuer:** <@{infraction.get('issuer_id', '0')}>\n"
                            f"> **Revoked By:** <@{infraction['revoked_by']}>\n"
                            f"> **Infraction ID:** `{infraction['_id']}`"
                        ),
                        inline=False,
                    )
                    await log_channel.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in infraction revoke handler: {e}")


async def setup(bot):
    await bot.add_cog(OnInfractionRevoke(bot))
