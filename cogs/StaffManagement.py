import datetime

import discord
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
            return await invis_embed(
                ctx,
                "The server has not been set up yet. Please run `/setup` to set up the server.",
            )

        active_loas = [
            document
            async for document in bot.loas.db.find(
                {
                    "guild_id": ctx.guild.id,
                    "type": "RA",
                    "expired": False,
                    "accepted": True,
                    "expiry": {
                        "$gt": int(
                            datetime.datetime.timestamp(datetime.datetime.utcnow())
                        )
                    },
                }
            )
        ]

        if not active_loas:
            return await invis_embed(
                ctx,
                "No Reduced Activity notices are currently active within this server. If you did not expect this message, please contact ERM Support or server administration.",
            )
        print(active_loas)
        for item in active_loas.copy():
            if item.get("voided") is True:
                active_loas.remove(item)

        INVISIBLE_CHAR = "‎"

        embed = discord.Embed(
            title="<:Clock:1035308064305332224> Active RAs",
            description="*The active RAs for **{}** will be displayed here.*\n\n**<:Pause:1035308061679689859> Active LOAs:**".format(
                ctx.guild.name
            ),
            color=0x2A2D31,
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)

        unsorted_loas = [{"object": l, "expiry": l["expiry"]} for l in active_loas]
        sorted_loas = sorted(unsorted_loas, key=lambda k: k["expiry"])

        if not sorted_loas:
            return await invis_embed(
                ctx,
                "No Reduced Activity notices are currently active within this server. If you did not expect this message, please contact ERM Support or server administration.",
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
                    ].description += f"\n<:ArrowRightW:1035023450592514048> **{index + 1}.** {member.mention} - Active\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Reason:** {loa_object['reason']}\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Started At:** <t:{loa_object['_id'].split('_')[2]}>\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Ends At:** <t:{loa_object['expiry']}>"
                else:
                    new_embed = discord.Embed(
                        title="<:Clock:1035308064305332224> Active RAs",
                        description="*The active RAs for **{}** will be displayed here.*\n\n**<:Pause:1035308061679689859> Active LOAs:**".format(
                            ctx.guild.name
                        ),
                        color=0x2A2D31,
                    )
                    new_embed.set_author(
                        name=ctx.author.name, icon_url=ctx.author.display_avatar.url
                    )
                    embeds.append(new_embed)
                    embeds[
                        -1
                    ].description += f"\n<:ArrowRightW:1035023450592514048> **{index}.** {member.mention} - Active\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Reason:** {loa_object['reason']}\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Started At:** <t:{loa_object['_id'].split('_')[2]}>\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Ends At:** <t:{loa_object['expiry']}>"

        if ctx.interaction:
            new_ctx = ctx.interaction
        else:
            new_ctx = ctx

        menu = ViewMenu(new_ctx, menu_type=ViewMenu.TypeEmbed, timeout=None)
        menu.add_pages(embeds)
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
            return await invis_embed(
                ctx,
                "The server has not been set up yet. Please run `/setup` to set up the server.",
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
                    "expiry": {"$gt": datetime.datetime.utcnow().timestamp()},
                    "denied": False,
                    "expired": False,
                }
            )
        ]
        if len(documents) > 0:
            return await invis_embed(
                ctx,
                f"You already have an active Reduced Activity request. Please wait until it expires before filing another one. If you would like to extend your RA request, please ask a Management member to run `/ra admin`.",
            )

        if not time.lower().endswith(("h", "m", "s", "d", "w")):
            reason.insert(0, time)
            if not timeObj.lower().endswith(("h", "m", "s", "d", "w")):
                return await invis_embed(
                    ctx,
                    "A time must be provided at the start or at the end of the command. Example: `/ra 12h Going to walk my shark` / `/ra Mopping the ceiling 12h`",
                )
            else:
                time = timeObj
                reason.pop()

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
            return await invis_embed(
                ctx,
                "A time must be provided at the start or at the end of the command. Example: `/ra 12h Going to walk my shark` / `/ra Mopping the ceiling 12h`",
            )

        startTimestamp = datetime.datetime.timestamp(ctx.message.created_at)
        endTimestamp = int(startTimestamp + time)

        embed = discord.Embed(title="Reduced Activity", color=0x2A2D31)

        try:
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.set_footer(text="Staff Logging Module")

        except:
            pass
        embed.add_field(
            name="<:staff:1035308057007230976> Staff Member",
            value=f"<:ArrowRight:1035003246445596774>{ctx.author.mention}",
            inline=False,
        )

        embed.add_field(
            name="<:Resume:1035269012445216858> Start",
            value=f"<:ArrowRight:1035003246445596774><t:{int(startTimestamp)}>",
            inline=False,
        )

        embed.add_field(
            name="<:Pause:1035308061679689859> End",
            value=f"<:ArrowRight:1035003246445596774><t:{int(endTimestamp)}>",
            inline=False,
        )

        reason = "".join(reason)

        embed.add_field(
            name="<:QMark:1035308059532202104> Reason",
            value=f"<:ArrowRight:1035003246445596774>{reason}",
            inline=False,
        )

        settings = await bot.settings.find_by_id(ctx.guild.id)
        try:
            management_role = settings["staff_management"]["management_role"]
        except:
            return await invis_embed(
                ctx,
                "The management role has not been set up yet. Please run `/setup` to set up the server.",
            )
        try:
            ra_role = settings["staff_management"]["ra_role"]
        except:
            return await invis_embed(
                ctx,
                "The RA role has not been set up yet. Please run `/config change` to add the RA role.",
            )

        code = system_code_gen()
        view = LOAMenu(bot, management_role, ra_role, ctx.author.id, code)

        channel = discord.utils.get(
            ctx.guild.channels, id=configItem["staff_management"]["channel"]
        )

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

        successEmbed = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Sent RA Request",
            description="<:ArrowRight:1035003246445596774> I've sent your RA request to a Management member of this server.",
            color=0x71C15F,
        )

        if ctx.interaction:
            await ctx.interaction.followup.send(embed=successEmbed)
        else:
            await ctx.send(embed=successEmbed)

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
            return await invis_embed(
                ctx,
                "The server has not been set up yet. Please run `/setup` to set up the server.",
            )

        try:
            ra_role = configItem["staff_management"]["ra_role"]
        except:
            return await invis_embed(
                ctx,
                "The RA role has not been set up yet. Please run `/config change` to add the LOA role.",
            )

        view = ActivityNoticeModification(ctx.author.id)

        embeds = []
        embed = discord.Embed(
            title=f"<:EditIcon:1042550862834323597> {member.name}#{member.discriminator}'s RA Panel",
            description=f"*This panel is for editing {member.name}'s RA history, or current RA.*",
            color=0x2A2D31,
        )
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
                            datetime.datetime.timestamp(datetime.datetime.utcnow())
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
                            datetime.datetime.timestamp(datetime.datetime.utcnow())
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
                string += f"<:ArrowRight:1035003246445596774> Started on <t:{int(l['_id'].split('_')[2])}>. Expires on <t:{int(l['expiry'])}>.\n"

            embeds[-1].add_field(
                name="<:Clock:1035308064305332224> Current RA(s)",
                value=string,
                inline=False,
            )
        else:
            embeds[-1].add_field(
                name="<:Clock:1035308064305332224> Current RA(s)",
                value="<:ArrowRight:1035003246445596774> None",
                inline=False,
            )

        if len(previous_ras) > 0:
            string = ""
            for l in previous_ras:
                string += f"<:ArrowRight:1035003246445596774> Started on <t:{int(l['_id'].split('_')[2])}>. Expired on <t:{int(l['expiry'])}>\n"

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
                    name="<:Clock:1035308064305332224> Previous RA(s)",
                    value=string,
                    inline=False,
                )

                if new_str not in [None, " ", ""]:
                    new_embed = discord.Embed(
                        title=f"<:EditIcon:1042550862834323597> {member.name}#{member.discriminator}'s RA Panel",
                        description=f"*This panel is for editing {member.name}'s RA history, or current RAs.*",
                        color=0x2A2D31,
                    )
                    new_embed.add_field(
                        name="<:Clock:1035308064305332224> Previous RA(s)",
                        value=new_str,
                        inline=False,
                    )
                    embeds.append(new_embed)

            else:
                embeds[-1].add_field(
                    name="<:Clock:1035308064305332224> Previous RA(s)",
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
                    emoji="<:SConductTitle:1053359821308567592>",
                    value="create",
                ),
                discord.SelectOption(
                    label="Edit RA",
                    description="Edit an existing RA for this user.",
                    emoji="<:EditIcon:1042550862834323597>",
                    value="edit",
                ),
                discord.SelectOption(
                    label="Void RA",
                    description="Void an existing RA for this user.",
                    emoji="<:TrashIcon:1042550860435181628>",
                    value="void",
                ),
            ],
        )

        await ctx.send(embeds=embeds, view=view)
        timeout = await view.wait()
        if timeout:
            return

        async def create_ra(ctx, member):
            embed = discord.Embed(
                title=f"<:SConductTitle:1053359821308567592> Activity Notice Creation",
                description=f"<:ArrowRight:1035003246445596774> Please click the button below to create a Reduced Activity for {member.mention}.",
                color=0x2A2D31,
            )
            embed.set_footer(text="Staff Management Module")
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
            await ctx.send(embed=embed, view=view)
            timeout = await view.wait()
            if timeout:
                return

            reason = view.modal.reason.value
            duration = view.modal.duration.value
            if duration[-1].lower() not in ["s", "m", "h", "d", "w"]:
                error_embed = discord.Embed(
                    title=f"<:ErrorIcon:1042550862834323597> Error",
                    description=f"<:ArrowRight:1035003246445596774> Invalid duration. Please try again.",
                    color=0x2A2D31,
                )
                return await ctx.send(embed=error_embed)

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

            embed = discord.Embed(title="Reduced Activity", color=0x2A2D31)

            try:
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text="Staff Logging Module")

            except:
                pass
            embed.add_field(
                name="<:staff:1035308057007230976> Staff Member",
                value=f"<:ArrowRight:1035003246445596774>{member.mention}",
                inline=False,
            )

            embed.add_field(
                name="<:Resume:1035269012445216858> Start",
                value=f"<:ArrowRight:1035003246445596774><t:{int(startTimestamp)}>",
                inline=False,
            )

            embed.add_field(
                name="<:Pause:1035308061679689859> End",
                value=f"<:ArrowRight:1035003246445596774><t:{int(endTimestamp)}>",
                inline=False,
            )

            reason = "".join(reason)

            embed.add_field(
                name="<:QMark:1035308059532202104> Reason",
                value=f"<:ArrowRight:1035003246445596774>{reason}",
                inline=False,
            )

            settings = await bot.settings.find_by_id(ctx.guild.id)
            try:
                management_role = settings["staff_management"]["management_role"]
            except:
                return await invis_embed(
                    ctx,
                    "The management role has not been set up yet. Please run `/setup` to set up the server.",
                )
            try:
                ra_role = settings["staff_management"]["ra_role"]
            except:
                return await invis_embed(
                    ctx,
                    "The RA role has not been set up yet. Please run `/config change` to add the LOA role.",
                )

            code = system_code_gen()
            view = LOAMenu(bot, management_role, ra_role, ctx.author.id, code)

            channel = discord.utils.get(
                ctx.guild.channels, id=configItem["staff_management"]["channel"]
            )
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

            successEmbed = discord.Embed(
                title="<:CheckIcon:1035018951043842088> Sent RA Request",
                description=f"<:ArrowRight:1035003246445596774> I've sent your RA request to {channel.mention}.",
                color=0x71C15F,
            )

            if ctx.interaction:
                await ctx.interaction.followup.send(embed=successEmbed, ephemeral=True)
            else:
                await ctx.send(embed=successEmbed)

        async def void_ra(ctx, member):
            if len(active_ras) == 0:
                return await invis_embed(
                    ctx, "There are no active Reduced Activity for this user."
                )

            embed = discord.Embed(
                title=f"<:WarningIcon:1035258528149033090> Activity Notice Deletion",
                description=f"<:ArrowRight:1035003246445596774> Are you sure you would like to delete {member.mention}'s Reduced Activity request?",
                color=0x2A2D31,
            )
            embed.set_footer(text="Staff Management Module")

            view = YesNoColourMenu(ctx.author.id)
            await ctx.send(embed=embed, view=view)
            timeout = await view.wait()
            if timeout:
                return

            if view.value is False:
                return await invis_embed(ctx, "Cancelled voiding the Reduced Activity.")

            if "privacy_mode" in configItem["staff_management"].keys():
                if configItem["staff_management"]["privacy_mode"] is True:
                    mentionable = "Management"
                else:
                    mentionable = ctx.author.mention
            else:
                mentionable = ctx.author.mention

            void_success = discord.Embed(
                title="<:CheckIcon:1035018951043842088> Success!",
                description=f"<:ArrowRight:1035003246445596774> I've voided the Reduced Activity for {member.mention}.",
                color=0x71C15F,
            )

            void_success.set_footer(text="Staff Management Module")
            await ctx.send(embed=void_success)

            ra_obj = active_ras[0]
            ra_obj["voided"] = True

            await bot.loas.update_by_id(ra_obj)

            success = discord.Embed(
                title=f"<:ErrorIcon:1035000018165321808> {ra_obj['type']} Voided",
                description=f"<:ArrowRightW:1035023450592514048>{mentionable} has voided your {ra_obj['type']}.",
                color=0xFF3C3C,
            )
            success.set_footer(text="Staff Management Module")

            try:
                await ctx.guild.get_member(ra_obj["user_id"]).send(embed=success)
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
                await invis_embed(ctx, "Could not remove the RA role from the user.")

        async def edit_ra(ctx, member):
            if len(active_ras) == 0:
                return await invis_embed(
                    ctx, "There are no active Reduced Activity notices for this user."
                )

            ra_object = active_ras[0]

            embed = discord.Embed(
                title=f"<:WarningIcon:1035258528149033090> Edit Reduced Activity",
                description=f"<:ArrowRight:1035003246445596774> What would you like to edit about the following Reduced Activity?",
                color=0x2A2D31,
            )

            embed.add_field(
                name=f"<:staff:1035308057007230976> {member.name}#{member.discriminator}",
                value=f"<:ArrowRightW:1035023450592514048> **Type:** {'Reduced Activity' if ra_object['type'].lower() == 'ra' else 'Leave of Absence'}\n<:ArrowRightW:1035023450592514048> **Reason:** {ra_object['reason']}\n<:ArrowRightW:1035023450592514048> **Start:** <t:{int(ra_object['_id'].split('_')[2])}>\n<:ArrowRightW:1035023450592514048> **Expires at:** <t:{int(ra_object['expiry'])}>\n<:ArrowRightW:1035023450592514048> **Status:** { {ra_object['accepted']: 'Accepted', ra_object['denied']: 'Denied', (ra_object['accepted'] is False and ra_object['denied'] is False): 'Pending'}[True]}",
                inline=False,
            )

            embed.set_footer(text="Staff Management Module")
            view = CustomSelectMenu(
                ctx.author.id,
                [
                    discord.SelectOption(
                        label="Type",
                        description="Change the type of Activity Notice.",
                        emoji="<:staff:1035308057007230976>",
                        value="type",
                    ),
                    discord.SelectOption(
                        label="Reason",
                        description="Change the reason for the Activity Notice.",
                        emoji="<:EditIcon:1042550862834323597>",
                        value="reason",
                    ),
                    discord.SelectOption(
                        label="Start",
                        description="Change the start date of the Activity Notice.",
                        emoji="<:Pause:1035308061679689859>",
                        value="start",
                    ),
                    discord.SelectOption(
                        label="End",
                        description="Change the end date of the Activity Notice.",
                        emoji="<:Resume:1035269012445216858>",
                        value="end",
                    ),
                ],
            )
            await ctx.send(embed=embed, view=view)
            timeout = await view.wait()
            if timeout:
                return

            if view.value == "type":
                embed = discord.Embed(
                    title=f"<:WarningIcon:1035258528149033090> Edit Leave of Absence",
                    description=f"<:ArrowRight:1035003246445596774> What would you like to change the type of the Leave of Absence to?",
                    color=0x2A2D31,
                )
                view = CustomSelectMenu(
                    ctx.author.id,
                    [
                        discord.SelectOption(
                            label="Leave of Absence",
                            description="A Leave of Absence constitutes full inactivity towards the server.",
                            emoji="<:staff:1035308057007230976>",
                            value="LoA",
                        ),
                        discord.SelectOption(
                            label="Reduced Activity",
                            description="A Reduced Activity Notice constitutes partial activity towards the server.",
                            emoji="<:EditIcon:1042550862834323597>",
                            value="RA",
                        ),
                    ],
                )

                await ctx.send(embed=embed, view=view)
                timeout = await view.wait()
                if timeout:
                    return
                if view.value:
                    if view.value in ["LoA", "RA"]:
                        ra_object["type"] = view.value
                        await bot.loas.update_by_id(ra_object)
                        success = discord.Embed(
                            title="<:CheckIcon:1035018951043842088> Success!",
                            description=f"<:ArrowRight:1035003246445596774> I've changed the type of the Activity Notice to {view.value}.",
                            color=0x71C15F,
                        )
                        success.set_footer(text="Staff Management Module")
                        await ctx.send(embed=success)
                    else:
                        return await invis_embed(ctx, "Invalid type.")

            elif view.value == "reason":
                embed = discord.Embed(
                    title=f"<:WarningIcon:1035258528149033090> Edit Leave of Absence",
                    description=f"<:ArrowRight:1035003246445596774> What would you like to change the reason of the Leave of Absence to?",
                    color=0x2A2D31,
                )
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

                await ctx.send(embed=embed, view=view)
                timeout = await view.wait()
                if timeout:
                    return
                if view.modal.reason.value:
                    ra_object["reason"] = view.modal.reason.value
                    await bot.loas.update_by_id(ra_object)
                    success = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success!",
                        description=f"<:ArrowRight:1035003246445596774> I've changed the reason of the Activity Notice to {view.modal.reason.value}.",
                        color=0x71C15F,
                    )
                    success.set_footer(text="Staff Management Module")
                    await ctx.send(embed=success)

            elif view.value == "start":
                embed = discord.Embed(
                    title=f"<:WarningIcon:1035258528149033090> Edit Reduced Activity",
                    description=f"<:ArrowRight:1035003246445596774> What would you like to change the start date of the Reduced Activity to?",
                    color=0x2A2D31,
                )

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
                                    int(ra_object["_id"].split("_")[2])
                                ).strftime("%m/%d/%Y"),
                            ),
                        )
                    ],
                )

                await ctx.send(embed=embed, view=view)
                timeout = await view.wait()
                if timeout:
                    return

                if view.modal.start.value:
                    try:
                        startTimestamp = parser.parse(view.modal.start.value)
                    except ValueError:
                        return await invis_embed(ctx, "Invalid date format.")

                    ra_object[
                        "_id"
                    ] = f"{ra_object['_id'].split('_')[0]}_{ra_object['_id'].split('_')[1]}_{startTimestamp.timestamp()}_{'_'.join(ra_object['_id'].split('_')[3:])}"
                    await bot.loas.update_by_id(ra_object)
                    success = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success!",
                        description=f"<:ArrowRight:1035003246445596774> I've changed the start date of the Activity Notice to {view.modal.start.value}.",
                        color=0x71C15F,
                    )

                    success.set_footer(text="Staff Management Module")
                    await ctx.send(embed=success)

            elif view.value == "end":
                embed = discord.Embed(
                    title=f"<:WarningIcon:1035258528149033090> Edit Reduced Activity",
                    description=f"<:ArrowRight:1035003246445596774> What would you like to change the end date of the Reduced Activity to?",
                    color=0x2A2D31,
                )

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
                                    ra_object["expiry"]
                                ).strftime("%m/%d/%Y"),
                            ),
                        )
                    ],
                )
                await ctx.send(embed=embed, view=view)
                timeout = await view.wait()
                if timeout:
                    return

                if view.modal.end.value:
                    try:
                        endTimestamp = parser.parse(view.modal.end.value)
                    except ValueError:
                        return await invis_embed(ctx, "Invalid date format.")

                    ra_object["expiry"] = endTimestamp.timestamp()
                    await bot.loas.update_by_id(ra_object)
                    success = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success!",
                        description=f"<:ArrowRight:1035003246445596774> I've changed the end date of the Activity Notice to {view.modal.end.value}.",
                        color=0x71C15F,
                    )

                    success.set_footer(text="Staff Management Module")
                    await ctx.send(embed=success)

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
            return await invis_embed(
                ctx,
                "The server has not been set up yet. Please run `/setup` to set up the server.",
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
                    "type": "LoA",
                    "accepted": True,
                    "expiry": {"$gt": datetime.datetime.utcnow().timestamp()},
                    "denied": False,
                    "expired": False,
                }
            )
        ]
        if len(documents) > 0:
            return await invis_embed(
                ctx,
                f"You already have an active Leave of Absence request. Please wait until it expires before filing another one. If you would like to extend your LoA request, please ask a Management member to run `/loa admin`.",
            )
        if not time.lower().endswith(("h", "m", "s", "d", "w")):
            reason.insert(0, time)
            if not "".join(reason).lower().endswith(("h", "m", "s", "d", "w")):
                return await invis_embed(
                    ctx,
                    "A time must be provided at the start or at the end of the command. Example: `/loa 12h Going to walk my shark` / `/loa Mopping the ceiling 12h`",
                )
            else:
                time = timeObj
                reason.pop()

        if time.lower().endswith("s"):
            time = int(removesuffix(time.lower(), "s"))
        elif time.lower().endswith("m"):
            time = int(removesuffix(time.lower(), "m")) * 60
        elif time.lower().endswith("h"):
            time = int(removesuffix(time.lower(), "h")) * 60 * 60
        elif time.lower().endswith("d"):
            time = int(removesuffix(time.lower(), "d")) * 60 * 60 * 24
        elif time.lower().endswith("w"):
            time = int(removesuffix(time.lower(), "w")) * 60 * 60 * 24 * 7

        startTimestamp = datetime.datetime.timestamp(ctx.message.created_at)
        endTimestamp = int(startTimestamp + time)

        embed = discord.Embed(title="Leave of Absence", color=0x2A2D31)

        try:
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.set_footer(text="Staff Logging Module")

        except:
            pass
        embed.add_field(
            name="<:staff:1035308057007230976> Staff Member",
            value=f"<:ArrowRight:1035003246445596774>{ctx.author.mention}",
            inline=False,
        )

        embed.add_field(
            name="<:Resume:1035269012445216858> Start",
            value=f"<:ArrowRight:1035003246445596774><t:{int(startTimestamp)}>",
            inline=False,
        )

        embed.add_field(
            name="<:Pause:1035308061679689859> End",
            value=f"<:ArrowRight:1035003246445596774><t:{int(endTimestamp)}>",
            inline=False,
        )

        reason = "".join(reason)

        embed.add_field(
            name="<:QMark:1035308059532202104> Reason",
            value=f"<:ArrowRight:1035003246445596774>{reason}",
            inline=False,
        )

        settings = await bot.settings.find_by_id(ctx.guild.id)
        try:
            management_role = settings["staff_management"]["management_role"]
        except:
            return await invis_embed(
                ctx,
                "The management role has not been set up yet. Please run `/setup` to set up the server.",
            )
        try:
            loa_role = settings["staff_management"]["loa_role"]
        except:
            return await invis_embed(
                ctx,
                "The LOA role has not been set up yet. Please run `/config change` to add the LOA role.",
            )

        code = system_code_gen()
        view = LOAMenu(bot, management_role, loa_role, ctx.author.id, code)

        channel = discord.utils.get(
            ctx.guild.channels, id=configItem["staff_management"]["channel"]
        )
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
            "type": "LoA",
            "expiry": int(endTimestamp),
            "expired": False,
            "accepted": False,
            "denied": False,
            "reason": "".join(reason),
        }

        await bot.loas.insert(example_schema)

        successEmbed = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Sent LoA Request",
            description="<:ArrowRight:1035003246445596774> I've sent your LoA request to a Management member of this server.",
            color=0x71C15F,
        )

        if ctx.interaction:
            await ctx.interaction.followup.send(embed=successEmbed)
        else:
            await ctx.send(embed=successEmbed)

    @loa.command(
        name="admin",
        description="Administrate a Leave of Absence request",
        extras={"category": "Staff Management"},
        with_app_command=True,
    )
    @is_management()
    @app_commands.describe(
        member="Who's LoA would you like to administrate? Specify a Discord user."
    )
    async def loa_admin(self, ctx, member: discord.Member):
        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await invis_embed(
                ctx,
                "The server has not been set up yet. Please run `/setup` to set up the server.",
            )

        try:
            loa_role = configItem["staff_management"]["loa_role"]
        except:
            return await invis_embed(
                ctx,
                "The LOA role has not been set up yet. Please run `/config change` to add the LOA role.",
            )

        view = ActivityNoticeModification(ctx.author.id)

        embeds = []
        embed = discord.Embed(
            title=f"<:EditIcon:1042550862834323597> {member.name}#{member.discriminator}'s LOA Panel",
            description=f"*This panel is for editing {member.name}'s LOA history, or current LOA.*",
            color=0x2A2D31,
        )
        embeds.append(embed)
        active_loas = [
            document
            async for document in bot.loas.db.find(
                {
                    "user_id": member.id,
                    "guild_id": ctx.guild.id,
                    "type": "LoA",
                    "expired": False,
                    "accepted": True,
                    "expiry": {
                        "$gt": int(
                            datetime.datetime.timestamp(datetime.datetime.utcnow())
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
                    "type": "LoA",
                    "expired": True,
                    "accepted": True,
                    "expiry": {
                        "$lt": int(
                            datetime.datetime.timestamp(datetime.datetime.utcnow())
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
                string += f"<:ArrowRight:1035003246445596774> Started on <t:{int(l['_id'].split('_')[2])}>. Expires on <t:{int(l['expiry'])}>.\n"

            embeds[-1].add_field(
                name="<:Clock:1035308064305332224> Current LOA(s)",
                value=string,
                inline=False,
            )
        else:
            embeds[-1].add_field(
                name="<:Clock:1035308064305332224> Current LOA(s)",
                value="<:ArrowRight:1035003246445596774> None",
                inline=False,
            )

        if len(previous_loas) > 0:
            string = ""
            for l in previous_loas:
                string += f"<:ArrowRight:1035003246445596774> Started on <t:{int(l['_id'].split('_')[2])}>. Expired on <t:{int(l['expiry'])}>\n"

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
                    name="<:Clock:1035308064305332224> Previous LOA(s)",
                    value=string,
                    inline=False,
                )

                if new_str not in [None, " ", ""]:
                    new_embed = discord.Embed(
                        title=f"<:EditIcon:1042550862834323597> {member.name}#{member.discriminator}'s LOA Panel",
                        description=f"*This panel is for editing {member.name}'s LOA history, or current LOA.*",
                        color=0x2A2D31,
                    )
                    new_embed.add_field(
                        name="<:Clock:1035308064305332224> Previous LOA(s)",
                        value=new_str,
                        inline=False,
                    )
                    embeds.append(new_embed)

            else:
                embeds[-1].add_field(
                    name="<:Clock:1035308064305332224> Previous LOA(s)",
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
                    label="Create LoA",
                    description="Create a new LoA for this user.",
                    emoji="<:SConductTitle:1053359821308567592>",
                    value="create",
                ),
                discord.SelectOption(
                    label="Edit LoA",
                    description="Edit an existing LoA for this user.",
                    emoji="<:EditIcon:1042550862834323597>",
                    value="edit",
                ),
                discord.SelectOption(
                    label="Void LoA",
                    description="Void an existing LoA for this user.",
                    emoji="<:TrashIcon:1042550860435181628>",
                    value="void",
                ),
            ],
        )

        await ctx.send(embeds=embeds, view=view)
        timeout = await view.wait()
        if timeout:
            return

        async def create_loa(ctx, member):
            embed = discord.Embed(
                title=f"<:SConductTitle:1053359821308567592> Activity Notice Creation",
                description=f"<:ArrowRight:1035003246445596774> Please click the button below to create a Leave of Absence for {member.mention}.",
                color=0x2A2D31,
            )
            embed.set_footer(text="Staff Management Module")
            view = CustomModalView(
                ctx.author.id,
                "Create a Leave of Absence",
                "LoA Creation",
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
            await ctx.send(embed=embed, view=view)
            timeout = await view.wait()
            if timeout:
                return

            reason = view.modal.reason.value
            duration = view.modal.duration.value
            if duration[-1].lower() not in ["s", "m", "h", "d", "w"]:
                error_embed = discord.Embed(
                    title=f"<:ErrorIcon:1042550862834323597> Error",
                    description=f"<:ArrowRight:1035003246445596774> Invalid duration. Please try again.",
                    color=0x2A2D31,
                )
                return await ctx.send(embed=error_embed)

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

            embed = discord.Embed(title="Leave of Absence", color=0x2A2D31)

            try:
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text="Staff Logging Module")

            except:
                pass
            embed.add_field(
                name="<:staff:1035308057007230976> Staff Member",
                value=f"<:ArrowRight:1035003246445596774>{member.mention}",
                inline=False,
            )

            embed.add_field(
                name="<:Resume:1035269012445216858> Start",
                value=f"<:ArrowRight:1035003246445596774><t:{int(startTimestamp)}>",
                inline=False,
            )

            embed.add_field(
                name="<:Pause:1035308061679689859> End",
                value=f"<:ArrowRight:1035003246445596774><t:{int(endTimestamp)}>",
                inline=False,
            )

            reason = "".join(reason)

            embed.add_field(
                name="<:QMark:1035308059532202104> Reason",
                value=f"<:ArrowRight:1035003246445596774>{reason}",
                inline=False,
            )

            settings = await bot.settings.find_by_id(ctx.guild.id)
            try:
                management_role = settings["staff_management"]["management_role"]
            except:
                return await invis_embed(
                    ctx,
                    "The management role has not been set up yet. Please run `/setup` to set up the server.",
                )
            try:
                loa_role = settings["staff_management"]["loa_role"]
            except:
                return await invis_embed(
                    ctx,
                    "The LOA role has not been set up yet. Please run `/config change` to add the LOA role.",
                )

            code = system_code_gen()
            view = LOAMenu(bot, management_role, loa_role, ctx.author.id, code)

            channel = discord.utils.get(
                ctx.guild.channels, id=configItem["staff_management"]["channel"]
            )
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
                "_id": f"{member.id}_{ctx.guild.id}_{int(startTimestamp)}_{int(endTimestamp)}",
                "user_id": member.id,
                "guild_id": ctx.guild.id,
                "message_id": msg.id,
                "type": "LoA",
                "expiry": int(endTimestamp),
                "voided": False,
                "expired": False,
                "accepted": False,
                "denied": False,
                "reason": "".join(reason),
            }

            await bot.loas.insert(example_schema)

            successEmbed = discord.Embed(
                title="<:CheckIcon:1035018951043842088> Sent LoA Request",
                description="<:ArrowRight:1035003246445596774> I've sent your LoA request to a Management member of this server.",
                color=0x71C15F,
            )

            if ctx.interaction:
                try:
                    await ctx.interaction.followup.send(
                        embed=successEmbed, ephemeral=True
                    )
                except discord.HTTPException:
                    await ctx.send(embed=successEmbed)
            else:
                await ctx.send(embed=successEmbed)

        async def void_loa(ctx, member):
            if len(active_loas) == 0:
                return await invis_embed(
                    ctx, "There are no active Leave of Absences for this user."
                )

            embed = discord.Embed(
                title=f"<:WarningIcon:1035258528149033090> Activity Notice Deletion",
                description=f"<:ArrowRight:1035003246445596774> Are you sure you would like to delete {member.mention}'s Leave of Absence request?",
                color=0x2A2D31,
            )
            embed.set_footer(text="Staff Management Module")

            view = YesNoColourMenu(ctx.author.id)
            await ctx.send(embed=embed, view=view)
            timeout = await view.wait()
            if timeout:
                return

            if view.value is False:
                return await invis_embed(ctx, "Cancelled voiding the Leave of Absence.")

            if "privacy_mode" in configItem["staff_management"].keys():
                if configItem["staff_management"]["privacy_mode"] is True:
                    mentionable = "Management"
                else:
                    mentionable = ctx.author.mention
            else:
                mentionable = ctx.author.mention

            void_success = discord.Embed(
                title="<:CheckIcon:1035018951043842088> Success!",
                description=f"<:ArrowRight:1035003246445596774> I've voided the Leave of Absence for {member.mention}.",
                color=0x71C15F,
            )

            void_success.set_footer(text="Staff Management Module")
            await ctx.send(embed=void_success)

            loa_obj = active_loas[0]
            loa_obj["voided"] = True

            await bot.loas.update_by_id(loa_obj)

            success = discord.Embed(
                title=f"<:ErrorIcon:1035000018165321808> {loa_obj['type']} Voided",
                description=f"<:ArrowRightW:1035023450592514048>{mentionable} has voided your {loa_obj['type']}.",
                color=0xFF3C3C,
            )
            success.set_footer(text="Staff Management Module")

            try:
                await ctx.guild.get_member(loa_obj["user_id"]).send(embed=success)
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
                await invis_embed(ctx, "Could not remove the LOA role from the user.")

        async def edit_loa(ctx, member):
            if len(active_loas) == 0:
                return await invis_embed(
                    ctx, "There are no active Leave of Absences for this user."
                )

            loa_object = active_loas[0]

            embed = discord.Embed(
                title=f"<:WarningIcon:1035258528149033090> Edit Leave of Absence",
                description=f"<:ArrowRight:1035003246445596774> What would you like to edit about the following Leave of Absence?",
                color=0x2A2D31,
            )

            embed.add_field(
                name=f"<:staff:1035308057007230976> {member.name}#{member.discriminator}",
                value=f"<:ArrowRightW:1035023450592514048> **Type:** {'Reduced Activity' if loa_object['type'].lower() == 'ra' else 'Leave of Absence'}\n<:ArrowRightW:1035023450592514048> **Reason:** {loa_object['reason']}\n<:ArrowRightW:1035023450592514048> **Start:** <t:{int(loa_object['_id'].split('_')[2])}>\n<:ArrowRightW:1035023450592514048> **Expires at:** <t:{int(loa_object['expiry'])}>\n<:ArrowRightW:1035023450592514048> **Status:** { {loa_object['accepted']: 'Accepted', loa_object['denied']: 'Denied', (loa_object['accepted'] is False and loa_object['denied'] is False): 'Pending'}[True]}",
                inline=False,
            )

            embed.set_footer(text="Staff Management Module")
            view = CustomSelectMenu(
                ctx.author.id,
                [
                    discord.SelectOption(
                        label="Type",
                        description="Change the type of Activity Notice.",
                        emoji="<:staff:1035308057007230976>",
                        value="type",
                    ),
                    discord.SelectOption(
                        label="Reason",
                        description="Change the reason for the Activity Notice.",
                        emoji="<:EditIcon:1042550862834323597>",
                        value="reason",
                    ),
                    discord.SelectOption(
                        label="Start",
                        description="Change the start date of the Activity Notice.",
                        emoji="<:Pause:1035308061679689859>",
                        value="start",
                    ),
                    discord.SelectOption(
                        label="End",
                        description="Change the end date of the Activity Notice.",
                        emoji="<:Resume:1035269012445216858>",
                        value="end",
                    ),
                ],
            )
            await ctx.send(embed=embed, view=view)
            timeout = await view.wait()
            if timeout:
                return

            if view.value == "type":
                embed = discord.Embed(
                    title=f"<:WarningIcon:1035258528149033090> Edit Leave of Absence",
                    description=f"<:ArrowRight:1035003246445596774> What would you like to change the type of the Leave of Absence to?",
                    color=0x2A2D31,
                )
                view = CustomSelectMenu(
                    ctx.author.id,
                    [
                        discord.SelectOption(
                            label="Leave of Absence",
                            description="A Leave of Absence constitutes full inactivity towards the server.",
                            emoji="<:staff:1035308057007230976>",
                            value="LoA",
                        ),
                        discord.SelectOption(
                            label="Reduced Activity",
                            description="A Reduced Activity Notice constitutes partial activity towards the server.",
                            emoji="<:EditIcon:1042550862834323597>",
                            value="RA",
                        ),
                    ],
                )

                await ctx.send(embed=embed, view=view)
                timeout = await view.wait()
                if timeout:
                    return
                if view.value:
                    if view.value in ["LoA", "RA"]:
                        loa_object["type"] = view.value
                        await bot.loas.update_by_id(loa_object)
                        success = discord.Embed(
                            title="<:CheckIcon:1035018951043842088> Success!",
                            description=f"<:ArrowRight:1035003246445596774> I've changed the type of the Activity Notice to {view.value}.",
                            color=0x71C15F,
                        )
                        success.set_footer(text="Staff Management Module")
                        await ctx.send(embed=success)
                    else:
                        return await invis_embed(ctx, "Invalid type.")

            elif view.value == "reason":
                embed = discord.Embed(
                    title=f"<:WarningIcon:1035258528149033090> Edit Leave of Absence",
                    description=f"<:ArrowRight:1035003246445596774> What would you like to change the reason of the Leave of Absence to?",
                    color=0x2A2D31,
                )
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

                await ctx.send(embed=embed, view=view)
                timeout = await view.wait()
                if timeout:
                    return
                if view.modal.reason.value:
                    loa_object["reason"] = view.modal.reason.value
                    await bot.loas.update_by_id(loa_object)
                    success = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success!",
                        description=f"<:ArrowRight:1035003246445596774> I've changed the reason of the Activity Notice to {view.modal.reason.value}.",
                        color=0x71C15F,
                    )
                    success.set_footer(text="Staff Management Module")
                    await ctx.send(embed=success)

            elif view.value == "start":
                embed = discord.Embed(
                    title=f"<:WarningIcon:1035258528149033090> Edit Leave of Absence",
                    description=f"<:ArrowRight:1035003246445596774> What would you like to change the start date of the Leave of Absence to?",
                    color=0x2A2D31,
                )

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
                                    int(loa_object["_id"].split("_")[2])
                                ).strftime("%m/%d/%Y"),
                            ),
                        )
                    ],
                )

                await ctx.send(embed=embed, view=view)
                timeout = await view.wait()
                if timeout:
                    return

                if view.modal.start.value:
                    try:
                        startTimestamp = parser.parse(view.modal.start.value)
                    except ValueError:
                        return await invis_embed(ctx, "Invalid date format.")

                    loa_object[
                        "_id"
                    ] = f"{loa_object['_id'].split('_')[0]}_{loa_object['_id'].split('_')[1]}_{startTimestamp.timestamp()}_{'_'.join(loa_object['_id'].split('_')[3:])}"
                    await bot.loas.update_by_id(loa_object)
                    success = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success!",
                        description=f"<:ArrowRight:1035003246445596774> I've changed the start date of the Activity Notice to {view.modal.start.value}.",
                        color=0x71C15F,
                    )

                    success.set_footer(text="Staff Management Module")
                    await ctx.send(embed=success)

            elif view.value == "end":
                embed = discord.Embed(
                    title=f"<:WarningIcon:1035258528149033090> Edit Leave of Absence",
                    description=f"<:ArrowRight:1035003246445596774> What would you like to change the end date of the Leave of Absence to?",
                    color=0x2A2D31,
                )

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
                                    loa_object["expiry"]
                                ).strftime("%m/%d/%Y"),
                            ),
                        )
                    ],
                )
                await ctx.send(embed=embed, view=view)
                timeout = await view.wait()
                if timeout:
                    return

                if view.modal.end.value:
                    try:
                        endTimestamp = parser.parse(view.modal.end.value)
                    except ValueError:
                        return await invis_embed(ctx, "Invalid date format.")

                    loa_object["expiry"] = endTimestamp.timestamp()
                    await bot.loas.update_by_id(loa_object)
                    success = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success!",
                        description=f"<:ArrowRight:1035003246445596774> I've changed the end date of the Activity Notice to {view.modal.end.value}.",
                        color=0x71C15F,
                    )

                    success.set_footer(text="Staff Management Module")
                    await ctx.send(embed=success)

        if view.value == "create":
            await create_loa(ctx, member)
        elif view.value == "edit":
            await edit_loa(ctx, member)
        elif view.value == "void":
            await void_loa(ctx, member)

    @loa.command(
        name="active",
        description="View all active LoAs",
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
            return await invis_embed(
                ctx,
                "The server has not been set up yet. Please run `/setup` to set up the server.",
            )

        active_loas = [
            document
            async for document in bot.loas.db.find(
                {
                    "guild_id": ctx.guild.id,
                    "type": "LoA",
                    "accepted": True,
                    "expired": False,
                    "expiry": {
                        "$gt": int(
                            datetime.datetime.timestamp(datetime.datetime.utcnow())
                        )
                    },
                }
            )
        ]

        if not active_loas:
            return await invis_embed(
                ctx,
                "No Leave of Absences are currently active within this server. If you did not expect this message, please contact ERM Support or server administration.",
            )
        print(active_loas)
        INVISIBLE_CHAR = "‎"

        for item in active_loas.copy():
            if item.get("voided") is True:
                active_loas.remove(item)

        embed = discord.Embed(
            title="<:Clock:1035308064305332224> Active LOAs",
            description="*The active LOAs for **{}** will be displayed here.*\n\n**<:Pause:1035308061679689859> Active LOAs:**".format(
                ctx.guild.name
            ),
            color=0x2A2D31,
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)

        unsorted_loas = [{"object": l, "expiry": l["expiry"]} for l in active_loas]
        sorted_loas = sorted(unsorted_loas, key=lambda k: k["expiry"])

        if not sorted_loas:
            return await invis_embed(
                ctx,
                "No Leave of Absences are currently active within this server. If you did not expect this message, please contact ERM Support or server administration.",
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
                    ].description += f"\n<:ArrowRightW:1035023450592514048> **{index + 1}.** {member.mention} - Active\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Reason:** {loa_object['reason']}\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Started At:** <t:{loa_object['_id'].split('_')[2]}>\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Ends At:** <t:{loa_object['expiry']}>"
                else:
                    new_embed = discord.Embed(
                        title="<:Clock:1035308064305332224> Active LOAs",
                        description="*The active LOAs for **{}** will be displayed here.*\n\n**<:Pause:1035308061679689859> Active LOAs:**".format(
                            ctx.guild.name
                        ),
                        color=0x2A2D31,
                    )
                    new_embed.set_author(
                        name=ctx.author.name, icon_url=ctx.author.display_avatar.url
                    )
                    embeds.append(new_embed)
                    embeds[
                        -1
                    ].description += f"\n<:ArrowRightW:1035023450592514048> **{index}.** {member.mention} - Active\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Reason:** {loa_object['reason']}\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Started At:** <t:{loa_object['_id'].split('_')[2]}>\n{INVISIBLE_CHAR}<:Fill:1074858542718263366> **Ends At:** <t:{loa_object['expiry']}>"

        if ctx.interaction:
            new_ctx = ctx.interaction
        else:
            new_ctx = ctx

        menu = ViewMenu(new_ctx, menu_type=ViewMenu.TypeEmbed, timeout=None)
        menu.add_pages(embeds)
        menu.add_buttons([ViewButton.back(), ViewButton.next()])
        await menu.start()


async def setup(bot):
    await bot.add_cog(StaffManagement(bot))
