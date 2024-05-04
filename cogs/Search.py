import datetime
import logging

import aiohttp
import discord
import pytz
from discord import app_commands
from discord.ext import commands
from reactionmenu import ViewButton, ViewMenu, Page
from reactionmenu.abc import _PageController
from roblox import client as roblox
import roblox as rbx_api

from datamodels.StaffConnections import StaffConnection
from datamodels.Warnings import WarningItem
from erm import check_privacy, is_staff, staff_field, staff_predicate
from utils.autocompletes import user_autocomplete
from utils.constants import BLANK_COLOR
from utils.utils import invis_embed, failure_embed, get_roblox_by_username, require_settings
from utils.paginators import SelectPagination, CustomPage

client = roblox.Client()


class Search(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.hybrid_command(
        name="mywarnings",
        aliases=["mymoderations", "mypunishments"],
        description="Lookup your punishments with ERM.",
        extras={"category": "Search"},
        with_app_command=True,
    )
    @require_settings()
    async def mywarnings(self, ctx: commands.Context, user: discord.User = None):
        if user is None:
           user = ctx.author 
        guild_id = ctx.guild.id
        if guild_id == 823606319529066548:
            guild_id = 1015622817452138606
        if self.bot.punishments_disabled is True:
            return await failure_embed(
                ctx,
                "This command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance. It will be returned shortly.",
            )

        bot = self.bot
        roblox_user = await bot.bloxlink.find_roblox(user.id)
        if not roblox_user or not (roblox_user or {}).get('robloxID'):
            return await ctx.send(
                embed=discord.Embed(
                    title="Could not find user",
                    description="I could not find this user's ROBLOX account. Ensure that they are linked with Bloxlink and try again.",
                    color=BLANK_COLOR
                )
            )
        roblox_user = roblox_user['robloxID']

        client = roblox.Client()
        roblox_player = await client.get_user(roblox_user)

        warnings: list[WarningItem] = await bot.punishments.get_warnings(roblox_player.id, guild_id) or []

        player_information_embed = discord.Embed(
            title=f"{roblox_player.name}",
            color=BLANK_COLOR,
        )
        punishments_embed = discord.Embed(
            title=player_information_embed.title,
            color=BLANK_COLOR,
        )
        embed_list = [player_information_embed, punishments_embed]

        magic_flags = {
            "ERM Team": 1001972346661384302,
            "ERM Developer": 1046204873496068176,
            "ERM Management": 1038597868023447552,
            "ERM Senior Support": 1028848687927013396,
            "ERM Support": 1053417531278364713,
            "ERM Staff": 988055417907200010
        }

        magic_flags_reverse = {v: k for k, v in magic_flags.items()}  # this is reverse mapping for quick lookup

        g_id = 987798554972143728
        guild: discord.Guild = bot.get_guild(g_id)
        applied_flags = set()  # use set to automatically remove duplicates
        member: None | StaffConnection = await bot.staff_connections.fetch_by_spec(roblox_id=roblox_player.id)

        if member:
            try:
                discord_member = await guild.fetch_member(member.discord_id)
            except discord.NotFound:
                discord_member = None

            if discord_member:
                applied_flags.update(
                    magic_flags_reverse.get(role.id) for role in discord_member.roles if role.id in magic_flags_reverse)

        applied_flags = list(applied_flags)
        if (await bot.custom_flags.db.count_documents({
            "roblox_id": roblox_player.id
        })) > 0:
            custom_flags = await bot.custom_flags.get_flags_by_roblox(roblox_player.id)
            for item in custom_flags:
                applied_flags.insert(0, f"{item.name} {item.emoji or ''}")

        if applied_flags:
            embed_list[0].add_field(
                name="Player Flags",
                inline=False,
                value=''.join([f"{item}\n" for item in applied_flags])
            )


        embed_list[0].add_field(
            name="Player Information",
            value=(
                f"> **Username:** {roblox_player.name}\n"
                f"> **Display Name:** {roblox_player.display_name}\n"
                f"> **User ID:** `{roblox_player.id}`\n"
                f"> **Friend Count:** {await roblox_player.get_friend_count()}\n"
                f"> **Created At:** <t:{int(roblox_player.created.timestamp())}>"
            ),
            inline=False
        )

        if ctx.author == user:
            embed_list[0].add_field(
                name="Punishments",
                value=(
                    f"> **Total Punishments:** {len(warnings)}\n"
                    f"> **Warnings:** {len(list(filter(lambda x: x.warning_type == 'Warning', warnings)))}\n"
                    f"> **Kicks:** {len(list(filter(lambda x: x.warning_type == 'Kick', warnings)))}\n"
                    f"> **Bans:** {len(list(filter(lambda x: x.warning_type == 'Ban', warnings)))}\n"
                    f"> **BOLOs:** {len(list(filter(lambda x: x.warning_type.upper() == 'BOLO', warnings)))}\n"
                    f"> **Other:** {len(list(filter(lambda x: x.warning_type.upper() not in ['WARNING', 'KICK', 'BAN', 'BOLO'], warnings)))}"
                ),
                inline=False,
            )

        if await staff_predicate(ctx):
            moderations = [await bot.punishments.fetch_warning(i['_id']) async for i in bot.punishments.db.find({
                "ModeratorID": ctx.author.id,
                "Guild": guild_id
            })]
            embed_list[0].add_field(
                name="Staff Information",
                value=(
                    f"> **Total Moderations:** {len(moderations)}\n"
                    f"> **Warnings:** {len(list(filter(lambda x: x.warning_type == 'Warning', moderations)))}\n"
                    f"> **Kicks:** {len(list(filter(lambda x: x.warning_type == 'Kick', moderations)))}\n"
                    f"> **Bans:** {len(list(filter(lambda x: x.warning_type == 'Ban', moderations)))}\n"
                    f"> **BOLOs:** {len(list(filter(lambda x: x.warning_type.upper() == 'BOLO', moderations)))}\n"
                    f"> **Other:** {len(list(filter(lambda x: x.warning_type.upper() not in ['WARNING', 'KICK', 'BAN', 'BOLO'], moderations)))}"
                ),
                inline=False
            )
        else:
            if user != ctx.author:
                return await ctx.send(
                    embed=discord.Embed(
                        title="No Staff Moderations",
                        description="This user has no moderations that they've handed out, so they cannot be viewed for privacy reasons.",
                        color=BLANK_COLOR
                    )
                )

        def add_warning_field(warning):
            new_line = '\n'
            embed_list[-1].add_field(
                name=f"{warning['Type']}",
                inline=False,
                value=(
                    f"> **Reason:** {warning.reason}\n"
                    f"> **At:** <t:{int(warning.time_epoch)}>\n"
                    f'{"> **Until:** <t:{}>{}".format(int(warning.until_epoch), new_line) if warning.until_epoch is not None else ""}'
                    f"> **ID:** `{warning.snowflake}`"
                )
            )

        for warning in warnings:
            if ctx.author != user:
                break
            if len(embed_list[-1].fields) <= 2:
                add_warning_field(warning)
            else:
                new_embed = discord.Embed(
                    title=embed_list[0].title, color=BLANK_COLOR
                )
                embed_list.append(new_embed)
                add_warning_field(warning)

        thumbnails = await client.thumbnails.get_user_avatar_thumbnails([roblox_player],
                                                                        type=rbx_api.thumbnails.AvatarThumbnailType.headshot)
        thumbnail_url = thumbnails[0].image_url
        for embed in embed_list:
            if len(embed.fields or []) == 0:
                embed_list.remove(embed)
            embed.set_thumbnail(url=thumbnail_url)
            embed.set_author(
                name=ctx.author.name,
                icon_url=ctx.author.display_avatar.url
            )

        pages = [CustomPage(embeds=[embed], identifier=str(index + 1) if index != 0 else 'Player Information') if len(embed.fields) > 0 else None for
                 index, embed in enumerate(embed_list)]
        paginator = SelectPagination(ctx.author.id, list(filter(lambda x: x is not None, pages)))

        # # print(embed_list)
        # [# print(obj) for obj in [embed.to_dict() for embed in embed_list]]
        if len(embed_list) == 1:
            return await ctx.send(
                embeds=pages[0].embeds
            )

        paginator.message = await ctx.send(
            embeds=pages[0].embeds,
            view=paginator
        )


    @commands.guild_only()
    @commands.hybrid_command(
        name="search",
        aliases=["s"],
        description="Searches for a user in the warning database.",
        extras={"category": "Search"},
        usage="<user>",
        with_app_command=True,
    )
    @is_staff()
    @app_commands.autocomplete(query=user_autocomplete)
    @app_commands.describe(
        query="What is the user you want to search for? This can be a Discord mention or a ROBLOX username."
    )
    @require_settings()
    async def search(self, ctx, *, query):

        if self.bot.punishments_disabled is True:
            return await failure_embed(
                ctx,
                "This command is currently disabled as ERM is currently undergoing maintenance updates. This command will be turned off briefly to ensure that no data is lost during the maintenance. It will be returned shortly.",
            )

        bot = self.bot
        alerts = {
            "NoAlerts": "No alerts found for this account!",
            "AccountAge": "The account age of the user is less than 100 days.",
            "NotManyFriends": "This user has less than 30 friends.",
            # "NotManyGroups": "This user has less than 5 groups.", - Flag has been removed for rate-limiting purposes
            "HasBOLO": "This user has a BOLO active.",
            "IsBanned": "This user is banned from Roblox."
        }

        user = query
        roblox_user = await get_roblox_by_username(user, bot, ctx)
        if roblox_user.get('errors'):
            return await ctx.send(embed=discord.Embed(
                title="Could not find player",
                description="I could not find a ROBLOX player with that corresponding username.",
                color=BLANK_COLOR
            ))

        client = roblox.Client()
        roblox_player = await client.get_user_by_username(roblox_user['name'])

        warnings: list[WarningItem] = await bot.punishments.get_warnings(roblox_player.id, ctx.guild.id) or []

        player_information_embed = discord.Embed(
            title=f"{roblox_player.name}",
            color=BLANK_COLOR,
        )
        punishments_embed = discord.Embed(
            title=player_information_embed.title,
            color=BLANK_COLOR,
        )
        embed_list = [player_information_embed, punishments_embed]

        alert_maps = {
            "IsBanned": roblox_player.is_banned,
            "AccountAge": (datetime.datetime.now(tz=pytz.UTC) - roblox_player.created).days < 100,
            "NotManyFriends": (await roblox_player.get_friend_count()) < 30,
            # "NotManyGroups": len(await roblox_player.get_group_roles()) < 5, - This flag has been removed for ratelimiting purposes
            "HasBOLO": "BOLO" in [warning.warning_type.upper() for warning in warnings]
        }
        triggered_alerts = [item[0] for item in list(filter(lambda x: x[1] is True, alert_maps.items()))] or [
            "NoAlerts"]

        magic_flags = {
            "ERM Team": 1001972346661384302,
            "ERM Developer": 1046204873496068176,
            "ERM Management": 1038597868023447552,
            "ERM Senior Support": 1028848687927013396,
            "ERM Support": 1053417531278364713,
            "ERM Staff": 988055417907200010
        }

        magic_flags_reverse = {v: k for k, v in magic_flags.items()}  # this is reverse mapping for quick lookup

        guild_id = 987798554972143728
        guild: discord.Guild = bot.get_guild(guild_id)
        applied_flags = set()  # use set to automatically remove duplicates
        member: None | StaffConnection = await bot.staff_connections.fetch_by_spec(roblox_id=roblox_player.id)

        if member:
            try:
                discord_member = await guild.fetch_member(member.discord_id)
            except discord.NotFound:
                discord_member = None

            if discord_member:
                applied_flags.update(
                    magic_flags_reverse.get(role.id) for role in discord_member.roles if role.id in magic_flags_reverse)

        applied_flags = list(applied_flags)
        if (await bot.custom_flags.db.count_documents({
            "roblox_id": roblox_player.id
        })) > 0:
            custom_flags = await bot.custom_flags.get_flags_by_roblox(roblox_player.id)
            for item in custom_flags:
                applied_flags.insert(0, f"{item.name} {item.emoji or ''}")

        if applied_flags:
            embed_list[0].add_field(
                name="Player Flags",
                inline=False,
                value=''.join([f"{item}\n" for item in applied_flags])
            )

        # TODO: Flag Interpretation

        embed_list[0].add_field(
            name="Player Information",
            value=(
                f"> **Username:** {roblox_player.name}\n"
                f"> **Display Name:** {roblox_player.display_name}\n"
                f"> **User ID:** `{roblox_player.id}`\n"
                f"> **Friend Count:** {await roblox_player.get_friend_count()}\n"
                f"> **Created At:** <t:{int(roblox_player.created.timestamp())}>"
            ),
            inline=False
        )

        embed_list[0].add_field(
            name="Punishments",
            value=(
                f"> **Total Punishments:** {len(warnings)}\n"
                f"> **Warnings:** {len(list(filter(lambda x: x.warning_type == 'Warning', warnings)))}\n"
                f"> **Kicks:** {len(list(filter(lambda x: x.warning_type == 'Kick', warnings)))}\n"
                f"> **Bans:** {len(list(filter(lambda x: x.warning_type == 'Ban', warnings)))}\n"
                f"> **BOLOs:** {len(list(filter(lambda x: x.warning_type.upper() == 'BOLO', warnings)))}\n"
                f"> **Other:** {len(list(filter(lambda x: x.warning_type.upper() not in ['WARNING', 'KICK', 'BAN', 'BOLO'], warnings)))}"
            ),
            inline=False,
        )

        string = "\n".join([f"{alerts[i]}" for i in triggered_alerts])

        embed_list[0].add_field(
            name="Player Alerts",
            value=f"{string}",
            inline=False,
        )

        # # # print(result)
        def add_warning_field(warning):
            new_line = '\n'
            embed_list[-1].add_field(
                name=f"{warning['Type']}",
                inline=False,
                value=(
                    f"> **Moderator:** <@{warning.moderator_id}>\n"
                    f"> **Reason:** {warning.reason}\n"
                    f"> **At:** <t:{int(warning.time_epoch)}>\n"
                    f'{"> **Until:** <t:{}>{}".format(int(warning.until_epoch), new_line) if warning.until_epoch is not None else ""}'
                    f"> **ID:** `{warning.snowflake}`"
                )
            )

        for warning in warnings:
            if len(embed_list[-1].fields) <= 2:
                add_warning_field(warning)
            else:
                new_embed = discord.Embed(
                    title=embed_list[0].title, color=BLANK_COLOR
                )
                embed_list.append(new_embed)
                add_warning_field(warning)

        thumbnails = await client.thumbnails.get_user_avatar_thumbnails([roblox_player],
                                                                        type=rbx_api.thumbnails.AvatarThumbnailType.headshot)
        thumbnail_url = thumbnails[0].image_url
        for embed in embed_list:
            if len(embed.fields or []) == 0:
                embed_list.remove(embed)
            embed.set_thumbnail(url=thumbnail_url)
            embed.set_author(
                name=ctx.author.name,
                icon_url=ctx.author.display_avatar.url
            )

        pages = [CustomPage(embeds=[embed], identifier=str(index + 1)) if len(embed.fields) > 0 else None for
                 index, embed in enumerate(embed_list)]
        paginator = SelectPagination(ctx.author.id, list(filter(lambda x: x is not None, pages)))

        # # print(embed_list)
        # [# print(obj) for obj in [embed.to_dict() for embed in embed_list]]
        if len(embed_list) == 1:
            return await ctx.send(
                embeds=pages[0].embeds
            )

        paginator.message = await ctx.send(
            embeds=pages[0].embeds,
            view=paginator
        )

    @commands.hybrid_command(
        name="userid",
        aliases=["u"],
        description="Returns the User Id of a searched user.",
        extras={"category": "Search"},
        usage="<user>",
        with_app_command=True,
    )
    @app_commands.autocomplete(query=user_autocomplete)
    @app_commands.describe(
        query="What is the user you want to search for? This can be a Discord mention or a ROBLOX username."
    )
    async def userid(self, ctx, *, query):
        bot = self.bot
        user = query

        user = query
        roblox_user = await get_roblox_by_username(user, bot, ctx)
        if roblox_user.get('errors'):
            return await ctx.send(embed=discord.Embed(
                title="Could not find player",
                description="I could not find a ROBLOX player with that corresponding username.",
                color=BLANK_COLOR
            ))

        client = roblox.Client()
        roblox_player = await client.get_user_by_username(roblox_user['name'])
        thumbnails = await client.thumbnails.get_user_avatar_thumbnails([roblox_player], type=rbx_api.thumbnails.AvatarThumbnailType.headshot)
        thumbnail = thumbnails[0].image_url
        embed = discord.Embed(title=roblox_player.name, color=BLANK_COLOR)

        embed.set_author(
            name=ctx.author.name,
            icon_url=ctx.author.display_avatar.url
        )

        embed.add_field(
            name="Player Information",
            value=(
                f"> **Username:** {roblox_player.name}\n"
                f"> **Display Name:** {roblox_player.display_name}\n"
                f"> **User ID:** `{roblox_player.id}`\n"
                f"> **Presence:** { {0: 'Offline', 1: 'Online', 2: 'In Game', 3: 'In Studio'}[presence.user_presence_type.value] if (presence := await roblox_player.get_presence()) is not None else 'Offline'}\n"
                f"> **Created At:** <t:{int(roblox_player.created.timestamp())}>"
            ),
            inline=False
        )

        embed.add_field(
            name="Player Counts",
            value=(
                f"> **Friends:** {await roblox_player.get_friend_count()}\n"
                f"> **Followers:** {await roblox_player.get_follower_count()}\n"
                f"> **Following:** {await roblox_player.get_following_count()}\n"
                f"> **Groups:** {len(await roblox_player.get_group_roles())}\n"
            )
        )
        
        embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text="Search Module")
        await ctx.send(
            embed=embed
        )



async def setup(bot):
    await bot.add_cog(Search(bot))
