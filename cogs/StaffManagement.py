import datetime

import discord
import pytz
from dateutil import parser
from discord import app_commands
from discord.ext import commands
from reactionmenu import ViewButton, ViewMenu

from erm import is_management, system_code_gen
from menus import (
    ActivityNoticeModification,
    CustomModalView,
    CustomSelectMenu,
    LOAMenu,
    YesNoColourMenu,
)
from utils.utils import invis_embed, removesuffix


class StaffManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(
        name="ra",
        description="File a Reduced Activity request",
        extras={"category": "Staff Management"},
        with_app_command=True,
    )
    async def ra(self, ctx, time, *, reason):
        pass

    @ra.command(
        name="active",
        description="View all active RAs",
        extras={"category": "Staff Management"},
    )
    @is_management()
    async def ra_active(self, ctx):
        bot = self.bot
        try:
            configItem = await bot.settings.find_by_id(ctx.guild.id)
            if not configItem:
                raise Exception("Settings not found")
        except:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup! Run `/setup` to setup the bot."
            )

        active_loas = [
            document
            async for document in bot.loas.db.find(
                {
                    "guild_id": ctx.guild.id,
                    "type": "RA",
                    "expired": False,
                    "accepted": True,
                }
            )
        ]

        if not active_loas:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** there are no active RAs in this server."
            )
        print(active_loas)
        for item in active_loas.copy():
            if item.get("voided") is True:
                active_loas.remove(item)

        INVISIBLE_CHAR = "‎"

        embed = discord.Embed(
            title=f"<:ERMUser:1111098647485108315> Active RAs",
            color=0xED4348,
            description="",
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)

        unsorted_loas = [{"object": l, "expiry": l["expiry"]} for l in active_loas]
        sorted_loas = sorted(unsorted_loas, key=lambda k: k["expiry"])

        if not sorted_loas:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** there are no active RAs in this server."
            )

        embeds = [embed]

        for index, l in enumerate(sorted_loas):
            loa_object = l["object"]
            member = loa_object["user_id"]
            member = discord.utils.get(ctx.guild.members, id=member)
            print(loa_object["_id"].split("_")[2])
            if member is not None:
                if len(embeds[-1].description.splitlines()) < 18:
                    embeds[
                        -1
                    ].description += f"\n<:ERMUser:1111098647485108315>  {member.mention} <:ERMCheck:1111089850720976906>\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Reason:** {loa_object['reason']}\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Started At:** <t:{loa_object['_id'].split('_')[2]}>\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Ends At:** <t:{int(loa_object['expiry'])}>"
                else:
                    new_embed = discord.Embed(
                        title=f"<:ERMUser:1111098647485108315> Active RAs",
                        color=0xED4348,
                        description="",
                    )
                    new_embed.set_author(
                        name=ctx.author.name, icon_url=ctx.author.display_avatar.url
                    )
                    embeds.append(new_embed)
                    embeds[
                        -1
                    ].description += f"\n<:ERMUser:1111098647485108315>** {member.mention} <:ERMCheck:1111089850720976906>\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Reason:** {loa_object['reason']}\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Started At:** <t:{loa_object['_id'].split('_')[2]}>\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Ends At:** <t:{int(loa_object['expiry'])}>"

        if ctx.interaction:
            new_ctx = ctx.interaction
        else:
            new_ctx = ctx

        menu = ViewMenu(new_ctx, menu_type=ViewMenu.TypeEmbed, timeout=None)
        for e in embeds:
            menu.add_page(
                embed=e,
                content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** there are **{len(sorted_loas)}** active RAs.",
            )
        menu.add_buttons([ViewButton.back(), ViewButton.next()])
        await menu.start()

    @ra.command(
        name="request",
        description="File a Reduced Activity request",
        extras={"category": "Staff Management", "ephemeral": True},
        with_app_command=True,
    )
    @app_commands.describe(time="How long are you going to be on RA for? (s/m/h/d)")
    @app_commands.describe(reason="What is your reason for going on RA?")
    async def rarequest(self, ctx, time, *, reason):
        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup! Run `/setup` to setup the bot."
            )

        try:
            timeObj = reason.split(" ")[-1]
        except:
            timeObj = ""
        reason = list(reason)

        documents = [
            document
            async for document in bot.loas.db.find(
                {
                    "guild_id": ctx.guild.id,
                    "user_id": ctx.author.id,
                    "type": "RA",
                    "expiry": {"$gt": datetime.datetime.now(tz=pytz.UTC).timestamp()},
                    "denied": False,
                    "expired": False,
                }
            )
        ]
        if len(documents) > 0:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** you already have a pending RA, or an active RA."
            )

        if not time.lower().endswith(("h", "m", "s", "d", "w")):
            reason.insert(0, time)
            if not timeObj.lower().endswith(("h", "m", "s", "d", "w")):
                return await ctx.reply(
                    f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** a time must be provided."
                )
            else:
                time = timeObj
                reason.pop()

        try:
            if time.lower().endswith("s"):
                time = int(time.lower().replace("s", ""))
            elif time.lower().endswith("m"):
                time = int(time.lower().replace("m", "")) * 60
            elif time.lower().endswith("h"):
                time = int(time.lower().replace("h", "")) * 60 * 60
            elif time.lower().endswith("d"):
                time = int(time.lower().replace("d", "")) * 60 * 60 * 24
            elif time.lower().endswith("w"):
                time = int(time.lower().replace("w", "")) * 60 * 60 * 24 * 7
            else:
                return await ctx.reply(
                    f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** a correct time must be provided."
                )
        except:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** a correct time must be provided."
            )

        startTimestamp = datetime.datetime.timestamp(ctx.message.created_at)
        endTimestamp = int(startTimestamp + time)

        embed = discord.Embed(
            title="<:ERMAdmin:1111100635736187011> Pending RA Request", color=0xED4348
        )

        try:
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.set_author(
                icon_url=ctx.author.display_avatar.url, name=ctx.author.name
            )

        except:
            pass
        embed.add_field(
            name="<:ERMUser:1111098647485108315> Staff Member",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{ctx.author.mention}",
            inline=False,
        )

        embed.add_field(
            name="<:ERMSchedule:1111091306089939054> Start",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912><t:{int(startTimestamp)}>",
            inline=False,
        )

        embed.add_field(
            name="<:ERMMisc:1113215605424795648> End",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912><t:{int(endTimestamp)}>",
            inline=False,
        )

        reason = "".join(reason)

        embed.add_field(
            name="<:ERMLog:1113210855891423302> Reason",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{reason}",
            inline=False,
        )

        settings = await bot.settings.find_by_id(ctx.guild.id)
        try:
            management_role = settings["staff_management"]["management_role"]
        except:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** a management role has not been set."
            )
        try:
            ra_role = settings["staff_management"]["ra_role"]
        except:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** an RA role has not been set up."
            )

        code = system_code_gen()
        view = LOAMenu(bot, management_role, ra_role, ctx.author.id, code)

        channel = discord.utils.get(
            ctx.guild.channels, id=configItem["staff_management"]["channel"]
        )
        if channel is None:
            return
        msg = await channel.send(embed=embed, view=view)
        await bot.views.insert(
            {
                "_id": code,
                "args": ["SELF", management_role, ra_role, ctx.author.id, code],
                "view_type": "LOAMenu",
                "message_id": msg.id,
            }
        )

        example_schema = {
            "_id": f"{ctx.author.id}_{ctx.guild.id}_{int(startTimestamp)}_{int(endTimestamp)}",
            "user_id": ctx.author.id,
            "guild_id": ctx.guild.id,
            "message_id": msg.id,
            "type": "RA",
            "expiry": int(endTimestamp),
            "expired": False,
            "accepted": False,
            "denied": False,
            "reason": "".join(reason),
        }

        await bot.loas.insert(example_schema)

        if ctx.interaction:
            await ctx.interaction.followup.send(
                content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've sent in your RA request."
            )
        else:
            await ctx.reply(
                content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've sent in your RA request."
            )

    @ra.command(
        name="admin",
        description="Administrate a Reduced Activity request",
        extras={"category": "Staff Management"},
        with_app_command=True,
    )
    @is_management()
    @app_commands.describe(
        member="Who's RA would you like to administrate? Specify a Discord user."
    )
    async def ra_admin(self, ctx, member: discord.Member):
        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup! Run `/setup` to setup the bot."
            )

        try:
            ra_role = configItem["staff_management"]["ra_role"]
        except:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup! Run `/setup` to setup the bot."
            )

        view = ActivityNoticeModification(ctx.author.id)

        embeds = []
        embed = discord.Embed(
            title=f"<:ERMUser:1111098647485108315> {member.name}'s RA Panel",
            color=0xED4348,
        )
        embed.set_author(icon_url=ctx.author.display_avatar.url, name=ctx.author.name)
        embeds.append(embed)
        active_ras = [
            document
            async for document in bot.loas.db.find(
                {
                    "user_id": member.id,
                    "guild_id": ctx.guild.id,
                    "type": "RA",
                    "expired": False,
                    "accepted": True,
                    "expiry": {
                        "$gt": int(
                            datetime.datetime.timestamp(
                                datetime.datetime.now(tz=pytz.UTC)
                            )
                        )
                    },
                }
            )
        ]
        previous_ras = [
            document
            async for document in bot.loas.db.find(
                {
                    "user_id": member.id,
                    "guild_id": ctx.guild.id,
                    "type": "RA",
                    "expired": True,
                    "accepted": True,
                    "expiry": {
                        "$lt": int(
                            datetime.datetime.timestamp(
                                datetime.datetime.now(tz=pytz.UTC)
                            )
                        )
                    },
                }
            )
        ]
        print(active_ras)

        for al in active_ras.copy():
            if al.get("voided") is True:
                active_ras.remove(al)

        if len(active_ras) > 0:
            string = ""
            for l in active_ras:
                string += f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Started:** <t:{int(l['_id'].split('_')[2])}>. \n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Expires:** <t:{int(l['expiry'])}>.\n"

            embeds[-1].add_field(
                name="<:ERMSchedule:1111091306089939054> Current RA(s)",
                value=string,
                inline=False,
            )
        else:
            embeds[-1].add_field(
                name="<:ERMSchedule:1111091306089939054> Current RA(s)",
                value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>None",
                inline=False,
            )

        if len(previous_ras) > 0:
            string = ""
            for l in previous_ras:
                string += f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Started:** <t:{int(l['_id'].split('_')[2])}>. \n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Expired:** <t:{int(l['expiry'])}>.\n"

            if len(string) > 700:
                string = string.splitlines()
                string = string[:6]
                new_str = string[6:]
                stri = "\n".join(string)
                new_str = "\n".join(new_str)
                print("stri:" + stri)
                print("new_str: " + new_str)

                string = stri
                embeds[-1].add_field(
                    name="<:ERMMisc:1113215605424795648> Current RA(s)",
                    value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>None",
                    inline=False,
                )

                if new_str not in [None, " ", ""]:
                    new_embed = discord.Embed(
                        title=f"<:ERMUser:1111098647485108315> {member.name}'s RA Panel",
                        color=0xED4348,
                    )
                    embed.set_author(
                        icon_url=ctx.author.display_avatar.url, name=ctx.author.name
                    )
                    new_embed.add_field(
                        name="<:ERMMisc:1113215605424795648> Previous RA(s)",
                        value=new_str,
                        inline=False,
                    )
                    embeds.append(new_embed)

            else:
                embeds[-1].add_field(
                    name="<:ERMMisc:1113215605424795648> Previous RA(s)",
                    value=string,
                    inline=False,
                )

        for e in embeds:
            e.set_footer(text="Staff Management Module")
        # view = YesNoMenu(ctx.author.id)

        view = CustomSelectMenu(
            ctx.author.id,
            [
                discord.SelectOption(
                    label="Create RA",
                    description="Create a new RA for this user.",
                    value="create",
                ),
                discord.SelectOption(
                    label="Edit RA",
                    description="Edit an existing RA for this user.",
                    value="edit",
                ),
                discord.SelectOption(
                    label="Void RA",
                    description="Void an existing RA for this user.",
                    value="void",
                ),
            ],
        )

        ra_admin_msg = await ctx.reply(embeds=embeds, view=view)
        timeout = await view.wait()
        if timeout:
            return

        async def create_ra(ctx, member):
            view = CustomModalView(
                ctx.author.id,
                "Create a Reduced Activity",
                "RA Creation",
                [
                    (
                        "reason",
                        discord.ui.TextInput(
                            label="Reason",
                            placeholder="Reason for the Reduced Activity",
                            min_length=1,
                            max_length=200,
                            style=discord.TextStyle.short,
                        ),
                    ),
                    (
                        "duration",
                        discord.ui.TextInput(
                            label="Duration",
                            placeholder="Duration of the Reduced Activity (s/m/h/d)",
                            min_length=1,
                            max_length=5,
                            style=discord.TextStyle.short,
                        ),
                    ),
                ],
            )
            await ra_admin_msg.edit(embed=None, view=view)
            timeout = await view.wait()
            if timeout:
                return

            reason = view.modal.reason.value
            duration = view.modal.duration.value
            if duration[-1].lower() not in ["s", "m", "h", "d", "w"]:
                return await ra_admin_msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that is not a valid time format."
                )

            if duration[-1].lower() == "s":
                duration = int(duration[:-1])
            elif duration[-1].lower() == "m":
                duration = int(duration[:-1]) * 60
            elif duration[-1].lower() == "h":
                duration = int(duration[:-1]) * 60 * 60
            elif duration[-1].lower() == "d":
                duration = int(duration[:-1]) * 60 * 60 * 24
            elif duration[-1].lower() == "w":
                duration = int(duration[:-1]) * 60 * 60 * 24 * 7

            startTimestamp = datetime.datetime.timestamp(ctx.message.created_at)
            endTimestamp = int(startTimestamp + duration)

            embed = discord.Embed(
                title="<:ERMAdmin:1111100635736187011> Pending RA Request",
                color=0xED4348,
            )

            try:
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_author(icon_url=member.display_avatar.url, name=member.name)

            except:
                pass
            embed.add_field(
                name="<:ERMUser:1111098647485108315> Staff Member",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{member.mention}",
                inline=False,
            )

            embed.add_field(
                name="<:ERMSchedule:1111091306089939054> Start",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912><t:{int(startTimestamp)}>",
                inline=False,
            )

            embed.add_field(
                name="<:ERMMisc:1113215605424795648> End",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912><t:{int(endTimestamp)}>",
                inline=False,
            )

            reason = "".join(reason)

            embed.add_field(
                name="<:ERMLog:1113210855891423302> Reason",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{reason}",
                inline=False,
            )

            settings = await bot.settings.find_by_id(ctx.guild.id)
            try:
                management_role = settings["staff_management"]["management_role"]
            except:
                return await ctx.reply(
                    f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** a management role has not been set."
                )
            try:
                ra_role = settings["staff_management"]["ra_role"]
            except:
                return await ctx.reply(
                    f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** an RA role has not been set up."
                )

            code = system_code_gen()
            view = LOAMenu(bot, management_role, ra_role, ctx.author.id, code)

            channel = discord.utils.get(
                ctx.guild.channels, id=configItem["staff_management"]["channel"]
            )
            if channel is None:
                return

            msg = await channel.send(embed=embed, view=view)

            await bot.views.insert(
                {
                    "_id": code,
                    "args": ["SELF", management_role, ra_role, ctx.author.id, code],
                    "view_type": "LOAMenu",
                    "message_id": msg.id,
                    "channel_id": msg.channel.id,
                }
            )

            example_schema = {
                "_id": f"{member.id}_{ctx.guild.id}_{int(startTimestamp)}_{int(endTimestamp)}",
                "user_id": member.id,
                "guild_id": ctx.guild.id,
                "message_id": msg.id,
                "type": "RA",
                "expiry": int(endTimestamp),
                "voided": False,
                "expired": False,
                "accepted": False,
                "denied": False,
                "reason": "".join(reason),
            }

            await bot.loas.insert(example_schema)

            if ctx.interaction:
                await ctx.interaction.followup.send(
                    content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've sent in a RA request for **{member.name}**.",
                    ephemeral=True,
                )
            else:
                await ctx.reply(
                    content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've sent in a RA request for **{member.name}**."
                )

        async def void_ra(ctx, member):
            if len(active_ras) == 0:
                return await ra_admin_msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that user doesn't have any RAs.",
                    embed=None,
                    view=None,
                )

            view = YesNoColourMenu(ctx.author.id)
            await ra_admin_msg.edit(
                content=f"<:ERMPending:1111097561588183121> **{ctx.author.name}**, are you sure you would like to delete **{member.name}**'s RA?",
                view=view,
                embed=None,
            )
            timeout = await view.wait()
            if timeout:
                return

            if view.value is False:
                return await ra_admin_msg.edit(
                    content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've cancelled voiding **{member.name}**'s RA.",
                    view=None,
                )

            if "privacy_mode" in configItem["staff_management"].keys():
                if configItem["staff_management"]["privacy_mode"] is True:
                    mentionable = "Management"
                else:
                    mentionable = ctx.author.mention
            else:
                mentionable = ctx.author.mention

            await ra_admin_msg.edit(
                content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've voided **{member.name}**'s RA.",
                view=None,
            )

            ra_obj = active_ras[0]
            ra_obj["voided"] = True

            await bot.loas.update_by_id(ra_obj)

            try:
                await ctx.guild.get_member(ra_obj["user_id"]).send(
                    content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** your **{ra_obj['type']}** has been voided by **{mentionable}**."
                )
                if isinstance(ra_role, int):
                    if ra_role in [role.id for role in member.roles]:
                        await member.remove_roles(
                            discord.utils.get(ctx.guild.roles, id=ra_role)
                        )
                elif isinstance(ra_role, list):
                    for role in ra_role:
                        if role in [r.id for r in member.roles]:
                            await member.remove_roles(
                                discord.utils.get(ctx.guild.roles, id=role)
                            )

            except:
                return await ra_admin_msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I couldn't void **{member.name}**'s RA.",
                    view=None,
                )

        async def edit_ra(ctx, member):
            if len(active_ras) == 0:
                return await ra_admin_msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** the user **{member.name}** has no active RAs.",
                    embed=None,
                    view=None,
                )

            ra_object = active_ras[0]

            view = CustomSelectMenu(
                ctx.author.id,
                [
                    discord.SelectOption(
                        label="Type",
                        description="Change the type of Activity Notice.",
                        value="type",
                    ),
                    discord.SelectOption(
                        label="Reason",
                        description="Change the reason for the Activity Notice.",
                        value="reason",
                    ),
                    discord.SelectOption(
                        label="Start",
                        description="Change the start date of the Activity Notice.",
                        value="start",
                    ),
                    discord.SelectOption(
                        label="End",
                        description="Change the end date of the Activity Notice.",
                        value="end",
                    ),
                ],
            )
            await ra_admin_msg.edit(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what would you like to edit about **{member.name}**'s RA?",
                view=view,
                embed=None,
            )
            timeout = await view.wait()
            if timeout:
                return

            if view.value == "type":
                view = CustomSelectMenu(
                    ctx.author.id,
                    [
                        discord.SelectOption(
                            label="Leave of Absence",
                            description="A Leave of Absence constitutes full inactivity towards the server.",
                            value="LoA",
                        ),
                        discord.SelectOption(
                            label="Reduced Activity",
                            description="A Reduced Activity Notice constitutes partial activity towards the server.",
                            value="RA",
                        ),
                    ],
                )

                await ra_admin_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** okey-dokey, what type do you want to change this RA to?",
                    view=view,
                )
                timeout = await view.wait()
                if timeout:
                    return
                if view.value:
                    if view.value in ["LoA", "RA"]:
                        ra_object["type"] = view.value
                        await bot.loas.update_by_id(ra_object)
                        await ctx.reply(
                            content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've changed the type of that activity notice to **{view.value}**.",
                            view=None,
                        )
                    else:
                        return await ra_admin_msg.edit(
                            content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that's an invalid type.",
                            view=None,
                        )

            elif view.value == "reason":
                view = CustomModalView(
                    ctx.author.id,
                    "Edit Leave of Absence",
                    "Edit Leave of Absence",
                    [
                        (
                            "reason",
                            discord.ui.TextInput(
                                label="Reason", placeholder="Reason", required=True
                            ),
                        )
                    ],
                )

                await ra_admin_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what would you like the reason of **{member.name}**'s Activity Notice to be?",
                    view=view,
                )
                timeout = await view.wait()
                if timeout:
                    return
                if view.modal.reason.value:
                    ra_object["reason"] = view.modal.reason.value
                    await bot.loas.update_by_id(ra_object)
                    await ra_admin_msg.edit(
                        content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** got it. I've changed the reason of **{member.name}**'s Activity Notice to **{view.modal.reason.value}**.",
                        view=None,
                    )

            elif view.value == "start":
                view = CustomModalView(
                    ctx.author.id,
                    "Edit the Start Date",
                    "Editing Activity Notice",
                    [
                        (
                            "start",
                            discord.ui.TextInput(
                                label="Start",
                                placeholder="Start",
                                required=True,
                                default=datetime.datetime.fromtimestamp(
                                    int(ra_object["_id"].split("_")[2]), tz=pytz.UTC
                                ).strftime("%m/%d/%Y"),
                            ),
                        )
                    ],
                )

                await ra_admin_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what would you like the new start data for **{member.name}**'s RA to be?",
                    view=view,
                    embed=None,
                )
                timeout = await view.wait()
                if timeout:
                    return

                if view.modal.start.value:
                    try:
                        startTimestamp = parser.parse(view.modal.start.value)
                    except ValueError:
                        return await ra_admin_msg.edit(
                            content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that's an invalid date format."
                        )

                    ra_object[
                        "_id"
                    ] = f"{ra_object['_id'].split('_')[0]}_{ra_object['_id'].split('_')[1]}_{startTimestamp.timestamp()}_{'_'.join(ra_object['_id'].split('_')[3:])}"
                    await bot.loas.update_by_id(ra_object)
                    await ctx.reply(
                        content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've changed the Start Date of that Activity Notice to **{view.modal.start.value}**.",
                        view=None,
                    )

            elif view.value == "end":
                view = CustomModalView(
                    ctx.author.id,
                    "Edit Reduced Activity",
                    "Edit Reduced Activity",
                    [
                        (
                            "end",
                            discord.ui.TextInput(
                                label="End",
                                placeholder="End",
                                required=True,
                                default=datetime.datetime.fromtimestamp(
                                    ra_object["expiry"], tz=pytz.UTC
                                ).strftime("%m/%d/%Y"),
                            ),
                        )
                    ],
                )
                await ra_admin_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what would you like the new end data for **{member.name}**'s RA to be?",
                    view=view,
                    embed=None,
                )
                timeout = await view.wait()
                if timeout:
                    return

                if view.modal.end.value:
                    try:
                        endTimestamp = parser.parse(view.modal.end.value)
                    except ValueError:
                        return await ra_admin_msg.edit(
                            content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that's an invalid date format."
                        )

                    ra_object["expiry"] = endTimestamp.timestamp()
                    await bot.loas.update_by_id(ra_object)
                    await ra_admin_msg.edit(
                        content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've changed the End Date of that Activity Notice to **{view.modal.end.value}**.",
                        view=None,
                    )

        if view.value == "create":
            await create_ra(ctx, member)
        elif view.value == "edit":
            await edit_ra(ctx, member)
        elif view.value == "void":
            await void_ra(ctx, member)

    @commands.hybrid_group(
        name="loa",
        description="File a Leave of Absence request",
        extras={"category": "Staff Management"},
        with_app_command=True,
    )
    async def loa(self, ctx, time, *, reason):
        pass

    @loa.command(
        name="active",
        description="View all active LOAs",
        extras={"category": "Staff Management"},
    )
    @is_management()
    async def loa_active(self, ctx):
        bot = self.bot
        try:
            configItem = await bot.settings.find_by_id(ctx.guild.id)
            if not configItem:
                raise Exception("Settings not found")
        except:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup! Run `/setup` to setup the bot."
            )

        active_loas = [
            document
            async for document in bot.loas.db.find(
                {
                    "guild_id": ctx.guild.id,
                    "type": {"$in": ["LoA", "LOA"]},
                    "expired": False,
                    "accepted": True,
                }
            )
        ]

        if not active_loas:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** there are no active LOAs in this server."
            )
        print(active_loas)
        for item in active_loas.copy():
            if item.get("voided") is True:
                active_loas.remove(item)

        INVISIBLE_CHAR = "‎"

        embed = discord.Embed(
            title=f"<:ERMUser:1111098647485108315> Active LOAs",
            color=0xED4348,
            description="",
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)

        unsorted_loas = [{"object": l, "expiry": l["expiry"]} for l in active_loas]
        sorted_loas = sorted(unsorted_loas, key=lambda k: k["expiry"])

        if not sorted_loas:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** there are no active LOAs in this server."
            )

        embeds = [embed]

        for index, l in enumerate(sorted_loas):
            loa_object = l["object"]
            member = loa_object["user_id"]
            member = discord.utils.get(ctx.guild.members, id=member)
            print(loa_object["_id"].split("_")[2])
            if member is not None:
                if len(embeds[-1].description.splitlines()) < 18:
                    embeds[
                        -1
                    ].description += f"\n<:ERMUser:1111098647485108315>  {member.mention} <:ERMCheck:1111089850720976906>\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Reason:** {loa_object['reason']}\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Started At:** <t:{loa_object['_id'].split('_')[2]}>\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Ends At:** <t:{int(loa_object['expiry'])}>"
                else:
                    new_embed = discord.Embed(
                        title=f"<:ERMUser:1111098647485108315> Active LOAs",
                        color=0xED4348,
                        description="",
                    )
                    new_embed.set_author(
                        name=ctx.author.name, icon_url=ctx.author.display_avatar.url
                    )
                    embeds.append(new_embed)
                    embeds[
                        -1
                    ].description += f"\n<:ERMUser:1111098647485108315>** {member.mention} <:ERMCheck:1111089850720976906>\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Reason:** {loa_object['reason']}\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Started At:** <t:{loa_object['_id'].split('_')[2]}>\n{INVISIBLE_CHAR}<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Ends At:** <t:{int(loa_object['expiry'])}>"

        if ctx.interaction:
            new_ctx = ctx.interaction
        else:
            new_ctx = ctx

        menu = ViewMenu(new_ctx, menu_type=ViewMenu.TypeEmbed, timeout=None)
        for e in embeds:
            menu.add_page(
                embed=e,
                content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** there are **{len(sorted_loas)}** active LOAs.",
            )
        menu.add_buttons([ViewButton.back(), ViewButton.next()])
        await menu.start()

    @commands.hybrid_group(
        name="loa",
        description="File a Leave of Absence request",
        extras={"category": "Staff Management"},
        with_app_command=True,
    )
    @app_commands.describe(time="How long are you going to be on LoA for? (s/m/h/d)")
    @app_commands.describe(reason="What is your reason for going on LoA?")
    async def loa(self, ctx, time, *, reason):
        await ctx.invoke(self.bot.get_command("loa request"), time=time, reason=reason)

    @loa.command(
        name="request",
        description="File a Leave of Absence request",
        extras={"category": "Staff Management", "ephemeral": True},
        with_app_command=True,
    )
    @app_commands.describe(time="How long are you going to be on LoA for? (s/m/h/d)")
    @app_commands.describe(reason="What is your reason for going on LoA?")
    async def loarequest(self, ctx, time, *, reason):
        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup! Run `/setup` to setup the bot."
            )

        try:
            timeObj = reason.split(" ")[-1]
        except:
            timeObj = ""
        reason = list(reason)

        documents = [
            document
            async for document in bot.loas.db.find(
                {
                    "guild_id": ctx.guild.id,
                    "user_id": ctx.author.id,
                    "type": "LOA",
                    "expiry": {"$gt": datetime.datetime.now(tz=pytz.UTC).timestamp()},
                    "denied": False,
                    "expired": False,
                }
            )
        ]
        if len(documents) > 0:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** you already have a pending LOA, or an active LOA."
            )

        if not time.lower().endswith(("h", "m", "s", "d", "w")):
            reason.insert(0, time)
            if not timeObj.lower().endswith(("h", "m", "s", "d", "w")):
                return await ctx.reply(
                    f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** a time must be provided."
                )
            else:
                time = timeObj
                reason.pop()

        try:
            if time.lower().endswith("s"):
                time = int(time.lower().replace("s", ""))
            elif time.lower().endswith("m"):
                time = int(time.lower().replace("m", "")) * 60
            elif time.lower().endswith("h"):
                time = int(time.lower().replace("h", "")) * 60 * 60
            elif time.lower().endswith("d"):
                time = int(time.lower().replace("d", "")) * 60 * 60 * 24
            elif time.lower().endswith("w"):
                time = int(time.lower().replace("w", "")) * 60 * 60 * 24 * 7
            else:
                return await ctx.reply(
                    f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** a time must be provided."
                )
        except:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** a correct time must be provided."
            )

        startTimestamp = datetime.datetime.timestamp(ctx.message.created_at)
        endTimestamp = int(startTimestamp + time)

        embed = discord.Embed(
            title="<:ERMAdmin:1111100635736187011> Pending LOA Request", color=0xED4348
        )

        try:
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.set_author(
                icon_url=ctx.author.display_avatar.url, name=ctx.author.name
            )

        except:
            pass
        embed.add_field(
            name="<:ERMUser:1111098647485108315> Staff Member",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{ctx.author.mention}",
            inline=False,
        )

        embed.add_field(
            name="<:ERMSchedule:1111091306089939054> Start",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912><t:{int(startTimestamp)}>",
            inline=False,
        )

        embed.add_field(
            name="<:ERMMisc:1113215605424795648> End",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912><t:{int(endTimestamp)}>",
            inline=False,
        )

        reason = "".join(reason)

        embed.add_field(
            name="<:ERMLog:1113210855891423302> Reason",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{reason}",
            inline=False,
        )

        settings = await bot.settings.find_by_id(ctx.guild.id)
        try:
            management_role = settings["staff_management"]["management_role"]
        except:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** a management role has not been set."
            )
        try:
            loa_role = settings["staff_management"]["loa_role"]
        except:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** an LOA role has not been set up."
            )

        code = system_code_gen()
        view = LOAMenu(bot, management_role, loa_role, ctx.author.id, code)

        channel = discord.utils.get(
            ctx.guild.channels, id=configItem["staff_management"]["channel"]
        )

        if channel is None:
            return

        msg = await channel.send(embed=embed, view=view)
        await bot.views.insert(
            {
                "_id": code,
                "args": ["SELF", management_role, loa_role, ctx.author.id, code],
                "view_type": "LOAMenu",
                "message_id": msg.id,
            }
        )

        example_schema = {
            "_id": f"{ctx.author.id}_{ctx.guild.id}_{int(startTimestamp)}_{int(endTimestamp)}",
            "user_id": ctx.author.id,
            "guild_id": ctx.guild.id,
            "message_id": msg.id,
            "type": "LOA",
            "expiry": int(endTimestamp),
            "expired": False,
            "accepted": False,
            "denied": False,
            "reason": "".join(reason),
        }

        await bot.loas.insert(example_schema)

        if ctx.interaction:
            await ctx.interaction.followup.send(
                content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've sent in your LOA request."
            )
        else:
            await ctx.reply(
                content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've sent in your LOA request."
            )

    @loa.command(
        name="admin",
        description="Administrate a Leave of Absence request",
        extras={"category": "Staff Management"},
        with_app_command=True,
    )
    @is_management()
    @app_commands.describe(
        member="Who's LOA would you like to administrate? Specify a Discord user."
    )
    async def loa_admin(self, ctx, member: discord.Member):
        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup! Run `/setup` to setup the bot."
            )

        try:
            loa_role = configItem["staff_management"]["loa_role"]
        except:
            return await ctx.reply(
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this server is not setup! Run `/setup` to setup the bot."
            )

        view = ActivityNoticeModification(ctx.author.id)

        embeds = []
        embed = discord.Embed(
            title=f"<:ERMUser:1111098647485108315> {member.name}'s LOA Panel",
            color=0xED4348,
        )
        embed.set_author(icon_url=ctx.author.display_avatar.url, name=ctx.author.name)
        embeds.append(embed)
        active_loas = [
            document
            async for document in bot.loas.db.find(
                {
                    "user_id": member.id,
                    "guild_id": ctx.guild.id,
                    "type": "LOA",
                    "expired": False,
                    "accepted": True,
                    "expiry": {
                        "$gt": int(
                            datetime.datetime.timestamp(
                                datetime.datetime.now(tz=pytz.UTC)
                            )
                        )
                    },
                }
            )
        ]
        previous_loas = [
            document
            async for document in bot.loas.db.find(
                {
                    "user_id": member.id,
                    "guild_id": ctx.guild.id,
                    "type": "LOA",
                    "expired": True,
                    "accepted": True,
                    "expiry": {
                        "$lt": int(
                            datetime.datetime.timestamp(
                                datetime.datetime.now(tz=pytz.UTC)
                            )
                        )
                    },
                }
            )
        ]
        print(active_loas)

        for al in active_loas.copy():
            if al.get("voided") is True:
                active_loas.remove(al)

        if len(active_loas) > 0:
            string = ""
            for l in active_loas:
                string += f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Started:** <t:{int(l['_id'].split('_')[2])}>. \n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Expires:** <t:{int(l['expiry'])}>.\n"

            embeds[-1].add_field(
                name="<:ERMSchedule:1111091306089939054> Current LOA(s)",
                value=string,
                inline=False,
            )
        else:
            embeds[-1].add_field(
                name="<:ERMSchedule:1111091306089939054> Current LOA(s)",
                value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>None",
                inline=False,
            )

        if len(previous_loas) > 0:
            string = ""
            for l in previous_loas:
                string += f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Started:** <t:{int(l['_id'].split('_')[2])}>. \n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Expired:** <t:{int(l['expiry'])}>.\n"

            if len(string) > 700:
                string = string.splitlines()
                string = string[:6]
                new_str = string[6:]
                stri = "\n".join(string)
                new_str = "\n".join(new_str)
                print("stri:" + stri)
                print("new_str: " + new_str)

                string = stri
                embeds[-1].add_field(
                    name="<:ERMMisc:1113215605424795648> Current LOA(s)",
                    value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>None",
                    inline=False,
                )

                if new_str not in [None, " ", ""]:
                    new_embed = discord.Embed(
                        title=f"<:ERMUser:1111098647485108315> {member.name}'s LOA Panel",
                        color=0xED4348,
                    )
                    embed.set_author(
                        icon_url=ctx.author.display_avatar.url, name=ctx.author.name
                    )
                    new_embed.add_field(
                        name="<:ERMMisc:1113215605424795648> Previous LOA(s)",
                        value=new_str,
                        inline=False,
                    )
                    embeds.append(new_embed)

            else:
                embeds[-1].add_field(
                    name="<:ERMMisc:1113215605424795648> Previous LOA(s)",
                    value=string,
                    inline=False,
                )

        for e in embeds:
            e.set_footer(text="Staff Management Module")
        # view = YesNoMenu(ctx.author.id)

        view = CustomSelectMenu(
            ctx.author.id,
            [
                discord.SelectOption(
                    label="Create LOA",
                    description="Create a new LOA for this user.",
                    value="create",
                ),
                discord.SelectOption(
                    label="Edit LOA",
                    description="Edit an existing LOA for this user.",
                    value="edit",
                ),
                discord.SelectOption(
                    label="Void LOA",
                    description="Void an existing LOA for this user.",
                    value="void",
                ),
            ],
        )

        loa_admin_msg = await ctx.reply(embeds=embeds, view=view)
        timeout = await view.wait()
        if timeout:
            return

        async def create_loa(ctx, member):
            view = CustomModalView(
                ctx.author.id,
                "Create a Leave of Absence",
                "LOA Creation",
                [
                    (
                        "reason",
                        discord.ui.TextInput(
                            label="Reason",
                            placeholder="Reason for the Leave of Absence",
                            min_length=1,
                            max_length=200,
                            style=discord.TextStyle.short,
                        ),
                    ),
                    (
                        "duration",
                        discord.ui.TextInput(
                            label="Duration",
                            placeholder="Duration of the Leave of Absence (s/m/h/d)",
                            min_length=1,
                            max_length=5,
                            style=discord.TextStyle.short,
                        ),
                    ),
                ],
            )
            await loa_admin_msg.edit(embed=None, view=view)
            timeout = await view.wait()
            if timeout:
                return

            reason = view.modal.reason.value
            duration = view.modal.duration.value
            if duration[-1].lower() not in ["s", "m", "h", "d", "w"]:
                return await loa_admin_msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that is not a valid time format."
                )

            if duration[-1].lower() == "s":
                duration = int(duration[:-1])
            elif duration[-1].lower() == "m":
                duration = int(duration[:-1]) * 60
            elif duration[-1].lower() == "h":
                duration = int(duration[:-1]) * 60 * 60
            elif duration[-1].lower() == "d":
                duration = int(duration[:-1]) * 60 * 60 * 24
            elif duration[-1].lower() == "w":
                duration = int(duration[:-1]) * 60 * 60 * 24 * 7

            startTimestamp = datetime.datetime.timestamp(ctx.message.created_at)
            endTimestamp = int(startTimestamp + duration)

            embed = discord.Embed(
                title="<:ERMAdmin:1111100635736187011> Pending LOA Request",
                color=0xED4348,
            )

            try:
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_author(icon_url=member.display_avatar.url, name=member.name)

            except:
                pass
            embed.add_field(
                name="<:ERMUser:1111098647485108315> Staff Member",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{member.mention}",
                inline=False,
            )

            embed.add_field(
                name="<:ERMSchedule:1111091306089939054> Start",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912><t:{int(startTimestamp)}>",
                inline=False,
            )

            embed.add_field(
                name="<:ERMMisc:1113215605424795648> End",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912><t:{int(endTimestamp)}>",
                inline=False,
            )

            reason = "".join(reason)

            embed.add_field(
                name="<:ERMLog:1113210855891423302> Reason",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{reason}",
                inline=False,
            )

            settings = await bot.settings.find_by_id(ctx.guild.id)
            try:
                management_role = settings["staff_management"]["management_role"]
            except:
                return await ctx.reply(
                    f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** a management role has not been set."
                )
            try:
                loa_role = settings["staff_management"]["loa_role"]
            except:
                return await ctx.reply(
                    f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** an LOA role has not been set up."
                )

            code = system_code_gen()
            view = LOAMenu(bot, management_role, loa_role, ctx.author.id, code)

            channel = discord.utils.get(
                ctx.guild.channels, id=configItem["staff_management"]["channel"]
            )
            if channel is None:
                return

            msg = await channel.send(embed=embed, view=view)

            await bot.views.insert(
                {
                    "_id": code,
                    "args": ["SELF", management_role, loa_role, ctx.author.id, code],
                    "view_type": "LOAMenu",
                    "message_id": msg.id,
                    "channel_id": msg.channel.id,
                }
            )

            example_schema = {
                "_id": f"{member.id}_{ctx.guild.id}_{int(startTimestamp)}_{int(endTimestamp)}",
                "user_id": member.id,
                "guild_id": ctx.guild.id,
                "message_id": msg.id,
                "type": "LOA",
                "expiry": int(endTimestamp),
                "voided": False,
                "expired": False,
                "accepted": False,
                "denied": False,
                "reason": "".join(reason),
            }

            await bot.loas.insert(example_schema)

            if ctx.interaction:
                await ctx.interaction.followup.send(
                    content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've sent in a LOA request for **{member.name}**.",
                    ephemeral=True,
                )
            else:
                await ctx.reply(
                    content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've sent in a LOA request for **{member.name}**."
                )

        async def void_loa(ctx, member):
            if len(active_loas) == 0:
                return await loa_admin_msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that user doesn't have any LOAs.",
                    embed=None,
                    view=None,
                )

            view = YesNoColourMenu(ctx.author.id)
            await loa_admin_msg.edit(
                content=f"<:ERMPending:1111097561588183121> **{ctx.author.name}**, are you sure you would like to delete **{member.name}**'s LOA?",
                view=view,
                embed=None,
            )
            timeout = await view.wait()
            if timeout:
                return

            if view.value is False:
                return await loa_admin_msg.edit(
                    content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've cancelled voiding **{member.name}**'s LOA.",
                    view=None,
                )

            if "privacy_mode" in configItem["staff_management"].keys():
                if configItem["staff_management"]["privacy_mode"] is True:
                    mentionable = "Management"
                else:
                    mentionable = ctx.author.mention
            else:
                mentionable = ctx.author.mention

            await loa_admin_msg.edit(
                content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've voided **{member.name}**'s LOA.",
                view=None,
            )

            loa_obj = active_loas[0]
            loa_obj["voided"] = True

            await bot.loas.update_by_id(loa_obj)

            try:
                await ctx.guild.get_member(loa_obj["user_id"]).send(
                    content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** your **{loa_obj['type']}** has been voided by **{mentionable}**."
                )
                if isinstance(loa_role, int):
                    if loa_role in [role.id for role in member.roles]:
                        await member.remove_roles(
                            discord.utils.get(ctx.guild.roles, id=loa_role)
                        )
                elif isinstance(loa_role, list):
                    for role in loa_role:
                        if role in [r.id for r in member.roles]:
                            await member.remove_roles(
                                discord.utils.get(ctx.guild.roles, id=role)
                            )

            except:
                return await loa_admin_msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** I couldn't void **{member.name}**'s LOA.",
                    view=None,
                )

        async def edit_loa(ctx, member):
            if len(active_loas) == 0:
                return await loa_admin_msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** the user **{member.name}** has no active LOAs.",
                    embed=None,
                    view=None,
                )

            loa_object = active_loas[0]

            view = CustomSelectMenu(
                ctx.author.id,
                [
                    discord.SelectOption(
                        label="Type",
                        description="Change the type of Activity Notice.",
                        value="type",
                    ),
                    discord.SelectOption(
                        label="Reason",
                        description="Change the reason for the Activity Notice.",
                        value="reason",
                    ),
                    discord.SelectOption(
                        label="Start",
                        description="Change the start date of the Activity Notice.",
                        value="start",
                    ),
                    discord.SelectOption(
                        label="End",
                        description="Change the end date of the Activity Notice.",
                        value="end",
                    ),
                ],
            )
            await loa_admin_msg.edit(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what would you like to edit about **{member.name}**'s LOA?",
                view=view,
                embed=None,
            )
            timeout = await view.wait()
            if timeout:
                return

            if view.value == "type":
                view = CustomSelectMenu(
                    ctx.author.id,
                    [
                        discord.SelectOption(
                            label="Leave of Absence",
                            description="A Leave of Absence constitutes full inactivity towards the server.",
                            value="LoA",
                        ),
                        discord.SelectOption(
                            label="Leave of Absence",
                            description="A Leave of Absence Notice constitutes partial activity towards the server.",
                            value="LOA",
                        ),
                    ],
                )

                await loa_admin_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** okey-dokey, what type do you want to change this LOA to?",
                    view=view,
                )
                timeout = await view.wait()
                if timeout:
                    return
                if view.value:
                    if view.value in ["LoA", "LOA"]:
                        loa_object["type"] = view.value
                        await bot.loas.update_by_id(loa_object)
                        await ctx.reply(
                            content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've changed the type of that activity notice to **{view.value}**.",
                            view=None,
                        )
                    else:
                        return await loa_admin_msg.edit(
                            content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that's an invalid type.",
                            view=None,
                        )

            elif view.value == "reason":
                view = CustomModalView(
                    ctx.author.id,
                    "Edit Leave of Absence",
                    "Edit Leave of Absence",
                    [
                        (
                            "reason",
                            discord.ui.TextInput(
                                label="Reason", placeholder="Reason", required=True
                            ),
                        )
                    ],
                )

                await loa_admin_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what would you like the reason of **{member.name}**'s Activity Notice to be?",
                    view=view,
                )
                timeout = await view.wait()
                if timeout:
                    return
                if view.modal.reason.value:
                    loa_object["reason"] = view.modal.reason.value
                    await bot.loas.update_by_id(loa_object)
                    await loa_admin_msg.edit(
                        content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** got it. I've changed the reason of **{member.name}**'s Activity Notice to **{view.modal.reason.value}**.",
                        view=None,
                    )

            elif view.value == "start":
                view = CustomModalView(
                    ctx.author.id,
                    "Edit the Start Date",
                    "Editing Activity Notice",
                    [
                        (
                            "start",
                            discord.ui.TextInput(
                                label="Start",
                                placeholder="Start",
                                required=True,
                                default=datetime.datetime.fromtimestamp(
                                    int(loa_object["_id"].split("_")[2]), tz=pytz.UTC
                                ).strftime("%m/%d/%Y"),
                            ),
                        )
                    ],
                )

                await loa_admin_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what would you like the new start data for **{member.name}**'s LOA to be?",
                    view=view,
                    embed=None,
                )
                timeout = await view.wait()
                if timeout:
                    return

                if view.modal.start.value:
                    try:
                        startTimestamp = parser.parse(view.modal.start.value)
                    except ValueError:
                        return await loa_admin_msg.edit(
                            content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that's an invalid date format."
                        )

                    loa_object[
                        "_id"
                    ] = f"{loa_object['_id'].split('_')[0]}_{loa_object['_id'].split('_')[1]}_{startTimestamp.timestamp()}_{'_'.join(loa_object['_id'].split('_')[3:])}"
                    await bot.loas.update_by_id(loa_object)
                    await ctx.reply(
                        content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've changed the Start Date of that Activity Notice to **{view.modal.start.value}**.",
                        view=None,
                    )

            elif view.value == "end":
                view = CustomModalView(
                    ctx.author.id,
                    "Edit Leave of Absence",
                    "Edit Leave of Absence",
                    [
                        (
                            "end",
                            discord.ui.TextInput(
                                label="End",
                                placeholder="End",
                                required=True,
                                default=datetime.datetime.fromtimestamp(
                                    loa_object["expiry"], tz=pytz.UTC
                                ).strftime("%m/%d/%Y"),
                            ),
                        )
                    ],
                )
                await loa_admin_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what would you like the new end data for **{member.name}**'s LOA to be?",
                    view=view,
                    embed=None,
                )
                timeout = await view.wait()
                if timeout:
                    return

                if view.modal.end.value:
                    try:
                        endTimestamp = parser.parse(view.modal.end.value)
                    except ValueError:
                        return await loa_admin_msg.edit(
                            content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** that's an invalid date format."
                        )

                    loa_object["expiry"] = endTimestamp.timestamp()
                    await bot.loas.update_by_id(loa_object)
                    await loa_admin_msg.edit(
                        content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've changed the End Date of that Activity Notice to **{view.modal.end.value}**.",
                        view=None,
                    )

        if view.value == "create":
            await create_loa(ctx, member)
        elif view.value == "edit":
            await edit_loa(ctx, member)
        elif view.value == "void":
            await void_loa(ctx, member)


async def setup(bot):
    await bot.add_cog(StaffManagement(bot))
