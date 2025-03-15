import datetime
import discord
import pytz
from discord.ext import commands
from discord import app_commands

from erm import is_staff, management_predicate, is_management
from utils.constants import BLANK_COLOR
from utils.paginators import SelectPagination, CustomPage
from utils.utils import require_settings, get_roblox_by_username
from utils.autocompletes import user_autocomplete, infraction_type_autocomplete


class Infractions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def check_manager_role(self, ctx):
        """Helper method to check if user has manager role from settings"""
        settings = await self.bot.settings.find_by_id(ctx.guild.id)
        if not settings or "infractions" not in settings:
            return False

        manager_roles = settings["infractions"].get("manager_roles", [])
        return any(role.id in manager_roles for role in ctx.author.roles)

    @commands.hybrid_group(name="infractions")
    @is_staff()
    async def infractions(self, ctx):
        """Base command for infractions"""
        if ctx.invoked_subcommand is None:
            return await ctx.send(
                embed=discord.Embed(
                    title="Invalid Subcommand",
                    description="Please specify a valid subcommand.",
                    color=BLANK_COLOR,
                )
            )

    @commands.guild_only()
    @commands.hybrid_command(
        name="myinfractions",
        description="View your infractions",
        extras={"category": "Infractions"},
    )
    @is_staff()
    @require_settings()
    async def myinfractions(self, ctx):
        """View your infractions"""
        settings = await self.bot.settings.find_by_id(ctx.guild.id)
        if not settings:
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Setup",
                    description="Your server is not setup.",
                    color=BLANK_COLOR,
                )
            )

        if not settings.get("infractions"):
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Enabled",
                    description="Infractions are not enabled on this server.",
                    color=BLANK_COLOR,
                )
            )

        infractions = []
        async for infraction in self.bot.db.infractions.find(
            {"guild_id": ctx.guild.id, "user_id": ctx.author.id}
        ).sort("timestamp", -1):
            infractions.append(infraction)

        if len(infractions) == 0:
            return await ctx.send(
                embed=discord.Embed(
                    title="No Infractions",
                    description="You have no infractions.",
                    color=BLANK_COLOR,
                ),
                ephemeral=True,
            )

        def setup_embed() -> discord.Embed:
            embed = discord.Embed(title="Your Infractions", color=BLANK_COLOR)
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
            return embed

        embeds = []
        for infraction in infractions:
            if len(embeds) == 0 or len(embeds[-1].fields) >= 4:
                embeds.append(setup_embed())

            embed = embeds[-1]
            issuer = "System"
            if infraction.get("issuer_id"):
                issuer = f"<@{infraction['issuer_id']}>"

            embed.add_field(
                name=f"Infraction #{infraction.get('_id', 'Unknown')}",
                value=(
                    f"> **Type:** {infraction['type']}\n"
                    f"> **Reason:** {infraction['reason']}\n"
                    f"> **Issuer:** {issuer}\n"
                    f"> **Date:** <t:{int(infraction['timestamp'])}:F>\n"
                    f"> **Status:** {'Revoked' if infraction.get('revoked', False) else 'Active'}"
                ),
                inline=False,
            )

        pages = [
            CustomPage(embeds=[embed], identifier=str(index + 1))
            for index, embed in enumerate(embeds)
        ]

        if len(pages) > 1:
            paginator = SelectPagination(self.bot, ctx.author.id, pages=pages)
            await ctx.send(embed=embeds[0], view=paginator)
        else:
            await ctx.send(embed=embeds[0])

    @commands.guild_only()
    @infractions.command(
        name="view",
        description="View a user's infractions",
        extras={"category": "Infractions"},
    )
    @is_staff()
    @require_settings()
    @app_commands.describe(user="The user to check infractions for")
    async def infractions_view(self, ctx, user: discord.Member):
        """View a user's infractions"""
        if user.id != ctx.author.id:
            has_manager_role = await self.check_manager_role(ctx)
            if not has_manager_role and not await management_predicate(ctx):
                return await ctx.send(
                    embed=discord.Embed(
                        title="Permission Denied",
                        description="You need management permissions to view other users' infractions.",
                        color=BLANK_COLOR,
                    )
                )

        settings = await self.bot.settings.find_by_id(ctx.guild.id)
        if not settings:
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Setup",
                    description="Your server is not setup.",
                    color=BLANK_COLOR,
                )
            )

        if not settings.get("infractions"):
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Enabled",
                    description="Infractions are not enabled on this server.",
                    color=BLANK_COLOR,
                )
            )

        target_id = user.id

        infractions = []
        async for infraction in self.bot.db.infractions.find(
            {"guild_id": ctx.guild.id, "user_id": target_id}
        ).sort("timestamp", -1):
            infractions.append(infraction)

        if len(infractions) == 0:
            return await ctx.send(
                embed=discord.Embed(
                    title="No Infractions",
                    description=f"{'You have' if target_id == ctx.author.id else 'This user has'} no infractions.",
                    color=BLANK_COLOR,
                ),
                ephemeral=True,
            )

        def setup_embed() -> discord.Embed:
            name = None
            try:
                if target_id:
                    member = ctx.guild.get_member(target_id)
                    if member:
                        name = member.name
                    else:
                        user = self.bot.get_user(target_id)
                        if user:
                            name = user.name
            except:
                pass

            if not name:
                name = str(target_id)

            embed = discord.Embed(title=f"Infractions for {name}", color=BLANK_COLOR)
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
            return embed

        embeds = []
        for infraction in infractions:
            if len(embeds) == 0 or len(embeds[-1].fields) >= 4:
                embeds.append(setup_embed())

            embed = embeds[-1]
            issuer = "System"
            if infraction.get("issuer_id"):
                issuer = f"<@{infraction['issuer_id']}>"

            embed.add_field(
                name=f"Infraction #{infraction.get('_id', 'Unknown')}",
                value=(
                    f"> **Type:** {infraction['type']}\n"
                    f"> **Reason:** {infraction['reason']}\n"
                    f"> **Issuer:** {issuer}\n"
                    f"> **Date:** <t:{int(infraction['timestamp'])}:F>\n"
                    f"> **Status:** {'Revoked' if infraction.get('revoked', False) else 'Active'}"
                ),
                inline=False,
            )

        pages = [
            CustomPage(embeds=[embed], identifier=str(index + 1))
            for index, embed in enumerate(embeds)
        ]

        if len(pages) > 1:
            paginator = SelectPagination(self.bot, ctx.author.id, pages=pages)
            await ctx.send(embed=embeds[0], view=paginator)
        else:
            await ctx.send(embed=embeds[0])

    @commands.guild_only()
    @infractions.command(name="issue", description="Issue an infraction to a user")
    @is_staff()
    @require_settings()
    @app_commands.autocomplete(type=infraction_type_autocomplete)
    @app_commands.describe(
        type="The type of infraction to give",
        user="The user to issue an infraction to",
        reason="What is your reason for giving this infraction?",
    )
    async def infractions_issue(
        self, ctx, user: discord.Member, type: str, *, reason: str
    ):
        """Issue an infraction to a user"""
        has_manager_role = await self.check_manager_role(ctx)
        if not has_manager_role and not await management_predicate(ctx):
            return await ctx.send(
                embed=discord.Embed(
                    title="Permission Denied",
                    description="You need management permissions or your infractions manager permission to issue infractions.",
                    color=BLANK_COLOR,
                )
            )

        settings = await self.bot.settings.find_by_id(ctx.guild.id)
        if not settings:
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Setup",
                    description="Your server is not setup.",
                    color=BLANK_COLOR,
                )
            )

        if not settings.get("infractions"):
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Enabled",
                    description="Infractions are not enabled on this server.",
                    color=BLANK_COLOR,
                )
            )

        target_id = user.id
        target_name = user.name

        infraction_config = next(
            (
                inf
                for inf in settings["infractions"]["infractions"]
                if inf["name"] == type
            ),
            None,
        )

        if not infraction_config:
            return await ctx.send(
                embed=discord.Embed(
                    title="Invalid Type",
                    description="This infraction type does not exist.",
                    color=BLANK_COLOR,
                ),
                ephemeral=True,
            )

        will_escalate = False
        existing_count = 0
        original_type = type
        current_type = type

        if infraction_config.get("escalation"):
            while True:
                threshold = infraction_config["escalation"].get("threshold", 0)
                next_infraction = infraction_config["escalation"].get("next_infraction")

                if not threshold or not next_infraction:
                    break

                existing_count = await self.bot.db.infractions.count_documents(
                    {
                        "user_id": target_id,
                        "guild_id": ctx.guild.id,
                        "type": current_type,
                        "revoked": {"$ne": True},
                    }
                )

                if (existing_count + 1) >= threshold:
                    next_config = next(
                        (
                            inf
                            for inf in settings["infractions"]["infractions"]
                            if inf["name"] == next_infraction
                        ),
                        None,
                    )
                    if not next_config:
                        break

                    current_type = next_infraction
                    will_escalate = True
                    infraction_config = next_config
                else:
                    break

        if will_escalate:
            type = current_type
            reason = (
                f"{reason}\n\nEscalated from {original_type} after reaching threshold"
            )

        # Create infraction document
        infraction_doc = {
            "user_id": target_id,
            "username": target_name,
            "guild_id": ctx.guild.id,
            "type": type,
            "original_type": original_type if will_escalate else None,
            "reason": reason,
            "timestamp": datetime.datetime.now(tz=pytz.UTC).timestamp(),
            "issuer_id": ctx.author.id,
            "issuer_username": ctx.author.name,
            "escalated": will_escalate,
            "escalation_count": existing_count + 1 if will_escalate else None,
        }

        result = await self.bot.db.infractions.insert_one(infraction_doc)
        infraction_doc["_id"] = result.inserted_id

        self.bot.dispatch("infraction_create", infraction_doc)

        target_name = str(target_id)
        try:
            member = ctx.guild.get_member(target_id)
            if member:
                target_name = member.name
            else:
                user = self.bot.get_user(target_id)
                if user:
                    target_name = user.name
                else:
                    roblox_user = await get_roblox_by_username(
                        str(target_id), self.bot, ctx
                    )
                    if roblox_user and not roblox_user.get("errors"):
                        target_name = roblox_user["name"]
        except:
            pass

        await ctx.send(
            embed=discord.Embed(
                title=f"{self.bot.emoji_controller.get_emoji('success')} Infraction Issued",
                description="Successfully issued an infraction!",
                color=discord.Color.green(),
            ).add_field(
                name="Details",
                value=(
                    f"> **User:** {target_name}\n"
                    f"> **Type:** {type}\n"
                    f"> **Reason:** {reason}\n"
                    f"> **Issued By:** {ctx.author.mention}\n"
                    f"> **Date:** <t:{int(infraction_doc['timestamp'])}:F>\n"
                    f"> **ID:** `{result.inserted_id}`\n"
                    + (
                        f"> **Escalated:** Yes (from {original_type})"
                        if will_escalate
                        else ""
                    )
                ),
                inline=False,
            ),
            ephemeral=True,
        )

    @infractions.command(name="revoke", description="Revoke an infraction using its ID")
    @is_staff()
    @require_settings()
    @app_commands.describe(infraction_id="The ID of the infraction to revoke")
    async def infractions_revoke(self, ctx, infraction_id: str):
        """Revoke an infraction"""
        has_manager_role = await self.check_manager_role(ctx)
        if not has_manager_role and not await management_predicate(ctx):
            return await ctx.send(
                embed=discord.Embed(
                    title="Permission Denied",
                    description="You need management permissions to revoke infractions.",
                    color=BLANK_COLOR,
                )
            )

        try:
            from bson import ObjectId

            infraction = await self.bot.db.infractions.find_one(
                {"_id": ObjectId(infraction_id)}
            )
            if not infraction:
                return await ctx.send(
                    embed=discord.Embed(
                        title="Not Found",
                        description="No infraction was found with that ID.",
                        color=BLANK_COLOR,
                    )
                )

            if infraction["guild_id"] != ctx.guild.id:
                return await ctx.send(
                    embed=discord.Embed(
                        title="Not Found",
                        description="No infraction was found with that ID in this server.",
                        color=BLANK_COLOR,
                    )
                )

            if infraction.get("revoked", False):
                return await ctx.send(
                    embed=discord.Embed(
                        title="Already Revoked",
                        description="This infraction has already been revoked.",
                        color=BLANK_COLOR,
                    )
                )

            await self.bot.db.infractions.update_one(
                {"_id": ObjectId(infraction_id)},
                {
                    "$set": {
                        "revoked": True,
                        "revoked_at": datetime.datetime.now(tz=pytz.UTC).timestamp(),
                        "revoked_by": ctx.author.id,
                    }
                },
            )

            infraction["revoked"] = True
            infraction["revoked_at"] = datetime.datetime.now(tz=pytz.UTC).timestamp()
            infraction["revoked_by"] = ctx.author.id
            self.bot.dispatch("infraction_revoke", infraction)

            await ctx.send(
                embed=discord.Embed(
                    title=f"{self.bot.emoji_controller.get_emoji('success')} Infraction Revoked",
                    description="Successfully revoked the infraction!",
                    color=discord.Color.green(),
                )
            )

        except Exception as e:
            await ctx.send(
                embed=discord.Embed(
                    title="Error",
                    description=f"An error occurred while revoking the infraction: {str(e)}",
                    color=BLANK_COLOR,
                )
            )


async def setup(bot):
    await bot.add_cog(Infractions(bot))
