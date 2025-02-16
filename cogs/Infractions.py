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
                    color=BLANK_COLOR
                )
            )

        if not settings.get('infractions'):  
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Enabled",
                    description="Infractions are not enabled on this server.",
                    color=BLANK_COLOR
                )
            )

        infractions = []
        async for infraction in self.bot.db.infractions.find({
            "guild_id": ctx.guild.id,
            "user_id": ctx.author.id
        }).sort("timestamp", -1):
            infractions.append(infraction)

        if len(infractions) == 0:
            return await ctx.send(
                embed=discord.Embed(
                    title="No Infractions",
                    description="You have no infractions.",
                    color=BLANK_COLOR
                ),
                ephemeral=True
            )

        def setup_embed() -> discord.Embed:
            embed = discord.Embed(
                title="Your Infractions",
                color=BLANK_COLOR
            )
            embed.set_author(
                name=ctx.guild.name,
                icon_url=ctx.guild.icon
            )
            return embed

        embeds = []
        for infraction in infractions:
            if len(embeds) == 0 or len(embeds[-1].fields) >= 4:
                embeds.append(setup_embed())

            embed = embeds[-1]
            issuer = "System"
            if infraction.get('issuer_id'):
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
                inline=False
                ephemeral=True
            )

        pages = [
            CustomPage(
                embeds=[embed],
                identifier=str(index + 1)
            ) for index, embed in enumerate(embeds)
        ]

        if len(pages) > 1:
            paginator = SelectPagination(ctx.author.id, pages=pages)
            await ctx.send(
                embed=embeds[0],
                view=paginator
            )
        else:
            await ctx.send(embed=embeds[0])

    @commands.guild_only()
    @commands.hybrid_command(
        name="infractions",
        description="View a user's infractions", 
        extras={"category": "Infractions"}
    )
    @is_staff()
    @require_settings()
    @app_commands.describe(user="The user to check infractions for")
    async def infractions(self, ctx, user: discord.Member):
        """View a user's infractions"""
        settings = await self.bot.settings.find_by_id(ctx.guild.id)
        if not settings:
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Setup",
                    description="Your server is not setup.",
                    color=BLANK_COLOR
                )
            )

        if not settings.get('infractions'):
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Enabled",
                    description="Infractions are not enabled on this server.",
                    color=BLANK_COLOR
                )
            )

        if user.id != ctx.author.id:
            if not await management_predicate(ctx):
                return await ctx.send(
                    embed=discord.Embed(
                        title="Permission Denied",
                        description="You need management permissions to view other users' infractions.",
                        color=BLANK_COLOR
                    )
                )

        target_id = user.id

        infractions = []
        async for infraction in self.bot.db.infractions.find({
            "guild_id": ctx.guild.id,
            "user_id": target_id
        }).sort("timestamp", -1):
            infractions.append(infraction)

        if len(infractions) == 0:
            return await ctx.send(
                embed=discord.Embed(
                    title="No Infractions",
                    description=f"{'You have' if target_id == ctx.author.id else 'This user has'} no infractions.",
                    color=BLANK_COLOR
                ),
                ephemeral=True
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

            embed = discord.Embed(
                title=f"Infractions for {name}",
                color=BLANK_COLOR
            )
            embed.set_author(
                name=ctx.guild.name,
                icon_url=ctx.guild.icon
            )
            return embed

        embeds = []
        for infraction in infractions:
            if len(embeds) == 0 or len(embeds[-1].fields) >= 4:
                embeds.append(setup_embed())

            embed = embeds[-1]
            issuer = "System"
            if infraction.get('issuer_id'):
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
                inline=False
                ephemeral=True
            )

        pages = [
            CustomPage(
                embeds=[embed],
                identifier=str(index + 1)
            ) for index, embed in enumerate(embeds)
        ]

        if len(pages) > 1:
            paginator = SelectPagination(ctx.author.id, pages=pages) 
            await ctx.send(
                embed=embeds[0],
                view=paginator
            )
        else:
            await ctx.send(embed=embeds[0])

    @commands.guild_only()
    @commands.hybrid_command(name="infract")
    @is_staff()
    @is_management()
    @require_settings()
    @app_commands.autocomplete(type=infraction_type_autocomplete)
    @app_commands.describe(type="The type of infraction to give.")
    @app_commands.describe(
        user="The user to issue an infraction to"
    )
    @app_commands.describe(reason="What is your reason for giving this infraction?")
    async def infract(self, ctx, user: discord.Member, type: str, *, reason: str):
        """Issue an infraction to a user"""
        settings = await self.bot.settings.find_by_id(ctx.guild.id)
        if not settings:
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Setup",
                    description="Your server is not setup.",
                    color=BLANK_COLOR
                )
            )

        if not settings.get('infractions'):
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Enabled",
                    description="Infractions are not enabled on this server.",
                    color=BLANK_COLOR
                )
            )

        target_id = user.id
        target_name = user.name

        infraction_config = next(
            (inf for inf in settings["infractions"]["infractions"] 
            if inf["name"] == type),
            None
        )

        if not infraction_config:
            return await ctx.send(
                embed=discord.Embed(
                    title="Invalid Type",
                    description="This infraction type does not exist.",
                    color=BLANK_COLOR
                ),
                ephemeral=True
            )

        will_escalate = False
        existing_count = 0
        original_type = type
        
        if infraction_config.get("escalation"):
            threshold = infraction_config["escalation"].get("threshold", 0)
            next_infraction = infraction_config["escalation"].get("next_infraction")
            
            if threshold and next_infraction:
                existing_count = await self.bot.db.infractions.count_documents({
                    "user_id": target_id,
                    "guild_id": ctx.guild.id,
                    "type": type,
                    "revoked": {"$ne": True}
                })

                if (existing_count + 1) >= threshold:
                    type = next_infraction
                    will_escalate = True
                    reason = f"{reason}\n\nEscalated from {original_type} after reaching {existing_count + 1} infractions"

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
            "escalation_count": existing_count + 1 if will_escalate else None
        }

        result = await self.bot.db.infractions.insert_one(infraction_doc)
        infraction_doc["_id"] = result.inserted_id

        self.bot.dispatch('infraction_create', infraction_doc)

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
                    roblox_user = await get_roblox_by_username(str(target_id), self.bot, ctx)
                    if roblox_user and not roblox_user.get('errors'):
                        target_name = roblox_user['name']
        except:
            pass

        await ctx.send(
            embed=discord.Embed(
                title="<:success:1163149118366040106> Infraction Issued",
                description="Successfully issued an infraction!",
                color=discord.Color.green()
            ).add_field(
                name="Details",
                value=(
                    f"> **User:** {target_name}\n"
                    f"> **Type:** {type}\n"
                    f"> **Reason:** {reason}\n"
                    f"> **Issued By:** {ctx.author.mention}\n"
                    f"> **Date:** <t:{int(infraction_doc['timestamp'])}:F>\n"
                    f"> **ID:** `{result.inserted_id}`\n"
                    + (f"> **Escalated:** Yes (from {original_type})" if will_escalate else "")
                ),
                inline=False
                ephemeral=True
            )
        )

async def setup(bot):
    await bot.add_cog(Infractions(bot))
