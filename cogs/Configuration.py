import discord
from discord.ext import commands

from erm import check_privacy, generator, is_management
from menus import (
    ChannelSelect,
    CustomModalView,
    CustomSelectMenu,
    EnableDisableMenu,
    MultiSelectMenu,
    RoleSelect,
    SettingsSelectMenu,
    YesNoColourMenu,
    YesNoMenu,
)
from utils.utils import request_response, failure_embed, pending_embed


class Configuration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="config")
    @is_management()
    async def config_group(self, ctx):
        await ctx.invoke(self.bot.get_command("config view"))

    @config_group.command(
        name="view",
        description="View the current configuration of the server.",
        extras={"category": "Configuration"},
    )
    @is_management()
    async def viewconfig(self, ctx):
        bot = self.bot
        if not await bot.settings.find_by_id(ctx.guild.id):
            return await failure_embed(
                ctx,
                "this server is not setup! Run `/setup` to setup the bot.",
            )

        settingContents = await bot.settings.find_by_id(ctx.guild.id)
        privacyConfig = await bot.privacy.find_by_id(ctx.guild.id)
        antiping_role = "None"
        bypass_role = "None"
        verification_role = "None"
        shift_role = "None"
        staff_management_channel = "None"
        staff_role = "None"
        management_role = "None"
        punishments_channel = "None"
        kick_channel = "None"
        ban_channel = "None"
        bolo_channel = "None"
        ra_role = "None"
        loa_role = "None"
        webhook_channel = "None"
        aa_channel = "None"
        aa_role = "None"
        minimum_shift_time = 0

        try:
            if isinstance(settingContents["verification"]["role"], int):
                verification_role = ctx.guild.get_role(
                    settingContents["verification"]["role"]
                ).mention
            elif isinstance(settingContents["verification"]["role"], list):
                verification_role = ""
                for role in settingContents["verification"]["role"]:
                    verification_role += ctx.guild.get_role(role).mention + ", "
                verification_role = verification_role[:-2]
        except:
            verification_role = "None"
        try:
            if isinstance(settingContents["shift_management"]["role"], int):
                shift_role = ctx.guild.get_role(
                    settingContents["shift_management"]["role"]
                ).mention
            elif isinstance(settingContents["shift_management"]["role"], list):
                shift_role = ""
                for role in settingContents["shift_management"]["role"]:
                    shift_role += ctx.guild.get_role(role).mention + ", "
                shift_role = shift_role[:-2]
        except:
            shift_role = "None"
        try:
            if isinstance(settingContents["antiping"]["role"], int):
                antiping_role = ctx.guild.get_role(
                    settingContents["antiping"]["role"]
                ).mention
            elif isinstance(settingContents["antiping"]["role"], list):
                antiping_role = ""
                for role in settingContents["antiping"]["role"]:
                    antiping_role += ctx.guild.get_role(role).mention + ", "
                antiping_role = antiping_role[:-2]
        except:
            antiping_role = "None"

        try:
            if isinstance(settingContents["antiping"]["bypass_role"], int):
                bypass_role = ctx.guild.get_role(
                    settingContents["antiping"]["bypass_role"]
                ).mention
            elif isinstance(settingContents["antiping"]["bypass_role"], list):
                bypass_role = ""
                for role in settingContents["antiping"]["bypass_role"]:
                    bypass_role += ctx.guild.get_role(role).mention + ", "
                bypass_role = bypass_role[:-2]
        except:
            bypass_role = "None"

        try:
            if isinstance(settingContents["game_security"]["role"], int):
                aa_role = ctx.guild.get_role(
                    settingContents["game_security"]["role"]
                ).mention
            elif isinstance(settingContents["game_security"]["role"], list):
                aa_role = ""
                for role in settingContents["game_security"]["role"]:
                    aa_role += ctx.guild.get_role(role).mention + ", "
                aa_role = aa_role[:-2]
        except:
            aa_role = "None"

        try:
            staff_management_channel = ctx.guild.get_channel(
                settingContents["staff_management"]["channel"]
            ).mention
        except:
            staff_management_channel = "None"

        try:
            webhook_channel = ctx.guild.get_channel(
                settingContents["game_security"]["webhook_channel"]
            ).mention
        except:
            webhook_channel = "None"

        try:
            aa_channel = ctx.guild.get_channel(
                settingContents["game_security"]["channel"]
            ).mention
        except:
            aa_channel = "None"

        try:
            if isinstance(settingContents["staff_management"]["role"], int):
                staff_role = ctx.guild.get_role(
                    settingContents["staff_management"]["role"]
                ).mention
            elif isinstance(settingContents["staff_management"]["role"], list):
                staff_role = ""
                for role in settingContents["staff_management"]["role"]:
                    staff_role += ctx.guild.get_role(role).mention + ", "
                staff_role = staff_role[:-2]
        except:
            staff_role = "None"

        try:
            if isinstance(settingContents["staff_management"]["management_role"], int):
                management_role = ctx.guild.get_role(
                    settingContents["staff_management"]["management_role"]
                ).mention
            elif isinstance(
                settingContents["staff_management"]["management_role"], list
            ):
                management_role = ""
                for role in settingContents["staff_management"]["management_role"]:
                    management_role += ctx.guild.get_role(role).mention + ", "
                management_role = management_role[:-2]
        except:
            management_role = "None"

        # punishments channel
        try:
            punishments_channel = ctx.guild.get_channel(
                settingContents["punishments"]["channel"]
            ).mention
        except:
            punishments_channel = "None"

        # shift management channel
        try:
            shift_management_channel = ctx.guild.get_channel(
                settingContents["shift_management"]["channel"]
            ).mention
        except:
            shift_management_channel = "None"

        try:
            ban_channel = ctx.guild.get_channel(
                settingContents["customisation"]["ban_channel"]
            ).mention
        except:
            ban_channel = "None"

        try:
            kick_channel = ctx.guild.get_channel(
                settingContents["customisation"]["kick_channel"]
            ).mention
        except:
            kick_channel = "None"

        try:
            bolo_channel = ctx.guild.get_channel(
                settingContents["customisation"]["bolo_channel"]
            ).mention
        except:
            bolo_channel = "None"

        try:
            compact_mode = settingContents["customisation"]["compact_mode"]
        except:
            compact_mode = False
        try:
            if isinstance(settingContents["staff_management"]["loa_role"], int):
                loa_role = ctx.guild.get_role(
                    settingContents["staff_management"]["loa_role"]
                ).mention
            elif isinstance(settingContents["staff_management"]["loa_role"], list):
                loa_role = ""
                for role in settingContents["staff_management"]["loa_role"]:
                    loa_role += ctx.guild.get_role(role).mention + ", "
                loa_role = loa_role[:-2]
        except:
            loa_role = "None"

        try:
            if isinstance(settingContents["staff_management"]["ra_role"], int):
                ra_role = ctx.guild.get_role(
                    settingContents["staff_management"]["ra_role"]
                ).mention
            elif isinstance(settingContents["staff_management"]["ra_role"], list):
                ra_role = ""
                for role in settingContents["staff_management"]["ra_role"]:
                    ra_role += ctx.guild.get_role(role).mention + ", "
                ra_role = ra_role[:-2]
        except:
            ra_role = "None"

        try:
            quota = f"{settingContents['shift_management']['quota']} seconds"
        except:
            quota = "0 seconds"

        for item in [
            antiping_role,
            bypass_role,
            verification_role,
            shift_role,
            staff_management_channel,
            staff_role,
            management_role,
            punishments_channel,
            kick_channel,
            ban_channel,
            bolo_channel,
            ra_role,
            loa_role,
            webhook_channel,
            aa_channel,
            aa_role,
            minimum_shift_time,
            quota,
        ]:
            if item in ["", " "] or item is None:
                item = "None"

        embed = discord.Embed(
            title="<:ERMConfig:1113208218521456835> Server Configuration",
            color=0xED4348,
        )
        embed.set_author(
            name=ctx.author.name,
            icon_url=ctx.author.display_avatar.url,
        )
        try:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        except:
            pass
        embed.add_field(
            name="<:ERMList:1111099396990435428> Verification",
            value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Enabled:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Role:** {}".format(
                settingContents["verification"]["enabled"], verification_role
            ),
            inline=False,
        )

        embed.add_field(
            name="<:ERMList:1111099396990435428> Anti-ping",
            value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Enabled:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Role:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Bypass Role:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Use Hierarchy:** {}".format(
                settingContents["antiping"]["enabled"],
                antiping_role,
                bypass_role,
                settingContents["antiping"].get("use_hierarchy")
                if settingContents["antiping"].get("use_hierarchy") is not None
                else "True",
            ),
            inline=False,
        )

        embed.add_field(
            name="<:ERMList:1111099396990435428> Staff Management",
            value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Enabled:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Channel:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Staff Role:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Management Role:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**LOA Role:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**RA Role:** {}".format(
                settingContents["staff_management"]["enabled"],
                staff_management_channel,
                staff_role,
                management_role,
                loa_role,
                ra_role,
            ),
            inline=False,
        )
        embed.add_field(
            name="<:ERMList:1111099396990435428> Punishments",
            value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Enabled:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Channel:** {}".format(
                settingContents["punishments"]["enabled"], punishments_channel
            ),
            inline=False,
        )

        moderation_sync_enabled = "False"
        sync_webhook_channel = "None"
        kick_ban_webhook_channel = "None"

        if settingContents.get("moderation_sync"):
            moderation_sync_enabled = str(settingContents["moderation_sync"]["enabled"])
            sync_webhook_channel = settingContents["moderation_sync"]["webhook_channel"]
            kick_ban_webhook_channel = settingContents["moderation_sync"].get(
                "kick_ban_webhook_channel"
            )

            try:
                sync_webhook_channel = ctx.guild.get_channel(int(sync_webhook_channel))
            except (TypeError, ValueError):
                sync_webhook_channel = None

            if sync_webhook_channel is None:
                sync_webhook_channel = "None"
            else:
                sync_webhook_channel = sync_webhook_channel.mention

            try:
                kick_ban_webhook_channel = ctx.guild.get_channel(
                    int(kick_ban_webhook_channel)
                )
            except (TypeError, ValueError):
                kick_ban_webhook_channel = None

            if kick_ban_webhook_channel is None:
                kick_ban_webhook_channel = "None"
            else:
                kick_ban_webhook_channel = kick_ban_webhook_channel.mention

        embed.add_field(
            name="<:ERMList:1111099396990435428> Game Sync",
            value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Enabled:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Webhook Channel:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Kick/Ban Webhook Channel:** {}".format(
                moderation_sync_enabled, sync_webhook_channel, kick_ban_webhook_channel
            ),
            inline=False,
        )

        embed.add_field(
            name="<:ERMList:1111099396990435428> Shift Management",
            value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Enabled:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Channel:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Role:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Nickname Prefix:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Quota:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Maximum Staff On Duty:** {}".format(
                settingContents["shift_management"]["enabled"],
                shift_management_channel,
                shift_role,
                settingContents["shift_management"].get("nickname_prefix")
                if settingContents["shift_management"].get("nickname_prefix")
                else "None",
                quota,
                settingContents["shift_management"].get("maximum_staff")
                if settingContents["shift_management"].get("maximum_staff")
                else "None",
            ),
            inline=False,
        )
        embed.add_field(
            name="<:ERMList:1111099396990435428> Customisation",
            value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Color:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Prefix:** `{}`\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Brand Name:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Thumbnail URL:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Footer Text:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Compact Mode:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Ban Channel:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Kick Channel:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**BOLO Channel:** {}".format(
                settingContents["customisation"]["color"],
                settingContents["customisation"]["prefix"],
                settingContents["customisation"]["brand_name"],
                settingContents["customisation"]["thumbnail_url"],
                settingContents["customisation"]["footer_text"],
                compact_mode,
                ban_channel,
                kick_channel,
                bolo_channel,
            ),
            inline=False,
        )
        game_security_enabled = False
        if "game_security" in settingContents.keys():
            if "enabled" in settingContents["game_security"].keys():
                game_security_enabled = settingContents["game_security"]["enabled"]
            else:
                game_security_enabled = "False"
        else:
            game_security_enabled = "False"

        embed.add_field(
            name="<:ERMList:1111099396990435428> Game Security",
            value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Enabled:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Channel:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Role:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Webhook Channel:** {}".format(
                game_security_enabled, aa_channel, aa_role, webhook_channel
            ),
            inline=False,
        )

        message_logging_enabled = "False"
        message_logging_channel = "None"
        sts_logging_enabled = "False"
        sts_logging_channel = "None"
        priority_logging_enabled = "False"
        priority_logging_channel = "None"

        if settingContents.get("game_logging"):
            message_logging_enabled = str(
                settingContents["game_logging"]["message"]["enabled"]
            )
            message_logging_channel = settingContents["game_logging"]["message"][
                "channel"
            ]

            if settingContents["game_logging"].get("priority"):
                priority_logging_enabled = str(
                    settingContents["game_logging"]["priority"]["enabled"]
                )
                priority_logging_channel = settingContents["game_logging"]["priority"][
                    "channel"
                ]

                try:
                    priority_logging_channel = ctx.guild.get_channel(
                        int(priority_logging_channel)
                    )
                except (TypeError, ValueError):
                    priority_logging_channel = None

                if priority_logging_channel is None:
                    priority_logging_channel = "None"
                else:
                    priority_logging_channel = priority_logging_channel.mention

            sts_logging_enabled = str(settingContents["game_logging"]["sts"]["enabled"])
            sts_logging_channel = str(settingContents["game_logging"]["sts"]["channel"])

            try:
                message_logging_channel = ctx.guild.get_channel(
                    int(message_logging_channel)
                )
            except (TypeError, ValueError):
                message_logging_channel = None

            if message_logging_channel is None:
                message_logging_channel = "None"
            else:
                message_logging_channel = message_logging_channel.mention

            try:
                sts_logging_channel = ctx.guild.get_channel(int(sts_logging_channel))
            except (TypeError, ValueError):
                sts_logging_channel = None

            if sts_logging_channel is None:
                sts_logging_channel = "None"
            else:
                sts_logging_channel = sts_logging_channel.mention

        for item in [
            message_logging_enabled,
            message_logging_channel,
            sts_logging_enabled,
            sts_logging_channel,
            priority_logging_enabled,
            priority_logging_channel,
        ]:
            if item in [" ", ""]:
                item = "None"

        embed.add_field(
            name="<:ERMList:1111099396990435428> Game Logging",
            value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Message Logging Enabled:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Message Logging Channel:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**STS Logging Enabled:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**STS Logging Channel:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Priority Logging Enabled:** {}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Priority Logging Channel:** {}".format(
                message_logging_enabled,
                message_logging_channel,
                sts_logging_enabled,
                sts_logging_channel,
                priority_logging_enabled,
                priority_logging_channel,
            ),
            inline=False,
        )

        embed.add_field(
            name="<:ERMList:1111099396990435428> Privacy",
            value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Global Warnings:** {}".format(
                await check_privacy(bot, ctx.guild.id, "global_warnings")
            ),
            inline=False,
        )

        embed.add_field(
            name="<:ERMList:1111099396990435428> Shift Types",
            value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **To view Shift Types, use the Select Menu below.**",
            inline=False,
        )

        view = CustomSelectMenu(
            ctx.author.id,
            [
                discord.SelectOption(
                    label="View Shift Types",
                    value="view",
                    description="View all shift types.",
                )
            ],
        )

        for field in embed.fields:
            field.inline = False

        await ctx.reply(embed=embed, view=view)
        timeout = await view.wait()
        if timeout:
            return

        if view.value == "view":
            shift_types = settingContents.get("shift_types")
            if shift_types is None:
                shift_types = {"enabled": False, "types": []}

            embed = discord.Embed(
                title="<:ERMLog:1113210855891423302> Shift Types",
                color=0xED4348,
            )

            embed.add_field(
                name="<:ERMList:1111099396990435428> Basic Configuration",
                value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Enabled:** {shift_types.get('enabled')}",
                inline=False,
            )

            for type in shift_types.get("types"):
                roles = type.get("role")
                if type.get("role") is None or len(type.get("role")) == 0:
                    roles = "None"
                else:
                    roles = ", ".join([f"<@&{role}>" for role in type.get("role")])

                if type.get("channel") is None:
                    channel = "None"
                else:
                    channel = f"<#{type.get('channel')}>"

                embed.add_field(
                    name=f"<:ERMList:1111099396990435428> {type.get('name')}",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Name:** {type.get('name')}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Default:** {type.get('default')}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Role:** {roles}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Channel:** {channel}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Nickname Prefix:** {type.get('nickname') if type.get('nickname') else 'None'}",
                    inline=False,
                )
                embed.set_author(
                    name=ctx.author.name,
                    icon_url=ctx.author.display_avatar.url,
                )
                embed.set_thumbnail(url=ctx.guild.icon.url)

            if len(embed.fields) == 1:
                embed.add_field(
                    name="<:ERMList:1111099396990435428> Shift Types",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> No shift types have been added.",
                    inline=False,
                )
            try:
                await ctx.reply(embed=embed, view=view)
            except HTTPException:
                await ctx.reply(f"<:ERMClose:1111101633389146223> **{ctx.author.name}**, I am unable to send this embed as it is too long.")

    @config_group.command(
        name="change",
        description="Change the configuration of the server.",
        extras={"category": "Configuration"},
    )
    @is_management()
    async def changeconfig(self, ctx):
        bot = self.bot
        if not await bot.settings.find_by_id(ctx.guild.id):
            return await failure_embed(
                ctx,
                "this server is not setup! Run `/setup` to setup the bot.",
            )

        settingContents = await bot.settings.find_by_id(ctx.guild.id)

        category = SettingsSelectMenu(ctx.author.id)

        config_msg = await ctx.reply(
            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, which module would you like to change the configuration for?",
            view=category,
        )

        await category.wait()
        category = category.value

        if category == "verification":
            question = "what do you want to do with verification?"
            customselect = CustomSelectMenu(
                ctx.author.id,
                [
                    discord.SelectOption(
                        label="Enable Verification",
                        description="Enable the verification module",
                        value="enable",
                    ),
                    discord.SelectOption(
                        label="Disable Verification",
                        description="Disable the verification module",
                        value="disable",
                    ),
                    discord.SelectOption(
                        label="Set Verification Roles",
                        description="Set the verification roles",
                        value="role",
                    ),
                ],
            )

            await config_msg.edit(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                view=customselect,
            )

            await customselect.wait()
            content = customselect.value
            if content == "enable":
                settingContents["verification"]["enabled"] = True
            elif content == "disable":
                settingContents["verification"]["enabled"] = False
            elif content == "role":
                view = RoleSelect(ctx.author.id)
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                settingContents["verification"]["role"] = (
                    [role.id for role in view.value]
                    if [role.id for role in view.value]
                    else []
                )
            else:
                return await failure_embed(
                    ctx,
                    "pick one of the options. `enable`, `disable`, `role`. Run this command again with correct parameters.",
                )
        elif category == "antiping":
            question = "what do you want to do with antiping?"
            customselect = CustomSelectMenu(
                ctx.author.id,
                [
                    discord.SelectOption(
                        label="Enable Antiping",
                        description="Enable the antiping module",
                        value="enable",
                    ),
                    discord.SelectOption(
                        label="Disable Antiping",
                        description="Disable the antiping module",
                        value="disable",
                    ),
                    discord.SelectOption(
                        label="Set Antiping Roles",
                        description="Set the antiping roles",
                        value="role",
                    ),
                    discord.SelectOption(
                        label="Set Bypass Roles",
                        description="Set the roles that can bypass antiping",
                        value="bypass_role",
                    ),
                    discord.SelectOption(
                        label="Enable Hierarchy",
                        description="Enable whether to apply antiping for roles higher than those selected",
                        value="enable_hierarchy",
                    ),
                    discord.SelectOption(
                        label="Disable Hierarchy",
                        description="Disable whether to apply antiping for roles higher than those selected",
                        value="disable_hierarchy",
                    ),
                ],
            )
            await config_msg.edit(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                view=customselect,
            )
            await customselect.wait()
            content = customselect.value
            if content == "enable":
                settingContents["antiping"]["enabled"] = True
            elif content == "disable":
                settingContents["antiping"]["enabled"] = False
            elif content == "role":
                view = RoleSelect(ctx.author.id)
                question = (
                    "what roles do you want to use for antiping? (e.g. `@Don't ping`)"
                )

                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                settingContents["antiping"]["role"] = (
                    [role.id for role in view.value]
                    if [role.id for role in view.value]
                    else []
                )
            elif (
                content == "bypass_role"
                or content == "bypass"
                or content == "bypass-role"
            ):
                view = RoleSelect(ctx.author.id)
                question = "what roles do you want to use as a bypass role? (e.g. `@Antiping Bypass`)"
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )

                await view.wait()
                settingContents["antiping"]["bypass_role"] = (
                    [role.id for role in view.value]
                    if [role.id for role in view.value]
                    else []
                )

            elif content == "enable_hierarchy" or content == "enable-hierarchy":
                settingContents["antiping"]["use_hierarchy"] = True
            elif content == "disable_hierarchy" or content == "disable-hierarchy":
                settingContents["antiping"]["use_hierarchy"] = False
            else:
                return await failure_embed(
                    ctx,
                    "you have not selected one of the options. Run this command again.",
                )
        elif category == "staff_management":
            question = "what do you want to do with staff management?"
            customselect = CustomSelectMenu(
                ctx.author.id,
                [
                    discord.SelectOption(
                        label="Enable Staff Management",
                        description="Enable the staff management module",
                        value="enable",
                    ),
                    discord.SelectOption(
                        label="Disable Staff Management",
                        description="Disable the staff management module",
                        value="disable",
                    ),
                    discord.SelectOption(
                        label="Set Staff Management Channel",
                        description="Set the channel for staff management",
                        value="channel",
                    ),
                    discord.SelectOption(
                        label="Set Staff Roles",
                        description="Set the staff roles. These will allow access to staff commands.",
                        value="staff_role",
                    ),
                    discord.SelectOption(
                        label="Set Management Roles",
                        description="Set the management roles. These will allow access to management commands.",
                        value="management_role",
                    ),
                    discord.SelectOption(
                        label="Set LOA Roles",
                        description="Set the LoA roles.",
                        value="loa_role",
                    ),
                    discord.SelectOption(
                        label="Set RA Roles",
                        description="Set the RA roles.",
                        value="ra_role",
                    ),
                    discord.SelectOption(
                        label="Set Privacy Mode",
                        description="Set whether or not to show identifiable information when using management commands",
                        value="privacy_mode",
                    ),
                ],
            )
            await config_msg.edit(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                view=customselect,
            )
            await customselect.wait()
            content = customselect.value
            if content == "enable":
                settingContents["staff_management"]["enabled"] = True
            elif content == "disable":
                settingContents["staff_management"]["enabled"] = False
            elif content == "channel":
                view = ChannelSelect(ctx.author.id, limit=1)
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, what channel would you like to use for Staff Management? (eg. LOA Requests)?",
                    view=view,
                )
                await view.wait()
                settingContents["staff_management"]["channel"] = (
                    view.value[0].id if view.value else None
                )
            elif content == "staff_role":
                view = RoleSelect(ctx.author.id)
                question = (
                    "what roles do you want to use as staff roles? (e.g. `@Staff`)"
                )
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                settingContents["staff_management"]["role"] = (
                    [role.id for role in view.value]
                    if [role.id for role in view.value]
                    else []
                )

            elif content == "management_role":
                view = RoleSelect(ctx.author.id)
                question = "what roles do you want to use as management roles? (e.g. `@Management`)"
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                settingContents["staff_management"]["management_role"] = (
                    [role.id for role in view.value]
                    if [role.id for role in view.value]
                    else []
                )
            elif content == "loa_role":
                view = RoleSelect(ctx.author.id)
                question = "what roles do you want to use as a LOA role? (e.g. `@LOA`)"
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                settingContents["staff_management"]["loa_role"] = (
                    [role.id for role in view.value]
                    if [role.id for role in view.value]
                    else []
                )
            elif content == "ra_role":
                view = RoleSelect(ctx.author.id)
                question = "what roles do you want to use as a RA role? (e.g. `@RA`)"
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                settingContents["staff_management"]["ra_role"] = (
                    [role.id for role in view.value]
                    if [role.id for role in view.value]
                    else []
                )
            elif content == "privacy_mode":
                view = EnableDisableMenu(ctx.author.id)
                question = "Do you want to enable Privacy Mode? This will anonymize the person who denies/accepts/voids a LoA/RA."
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                if view.value == True:
                    settingContents["staff_management"]["privacy_mode"] = True
                elif view.value == False:
                    settingContents["customisation"]["privacy_mode"] = False
            else:
                return await failure_embed(
                    ctx,
                    "you have not selected one of the options. Run this command again.",
                )
        elif category == "punishments":
            question = "what do you want to do with punishments?"
            customselect = CustomSelectMenu(
                ctx.author.id,
                [
                    discord.SelectOption(
                        label="Enable Punishments",
                        description="Enable the punishments module",
                        value="enable",
                    ),
                    discord.SelectOption(
                        label="Disable Punishments",
                        description="Disable the punishments module",
                        value="disable",
                    ),
                    discord.SelectOption(
                        label="Set Punishment Channel",
                        description="Set the channel for punishments",
                        value="channel",
                    ),
                    discord.SelectOption(
                        label="Set Kick Channel",
                        description="Set the channel for kicks",
                        value="kick_channel",
                    ),
                    discord.SelectOption(
                        label="Set Ban Channel",
                        description="Set the channel for bans",
                        value="ban_channel",
                    ),
                    discord.SelectOption(
                        label="Set BOLO Channel",
                        description="Set the channel for BOLOs",
                        value="bolo_channel",
                    ),
                ],
            )
            await config_msg.edit(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                view=customselect,
            )
            await customselect.wait()
            content = customselect.value
            if content == "enable":
                settingContents["punishments"]["enabled"] = True
            elif content == "disable":
                settingContents["punishments"]["enabled"] = False
            elif content == "channel":
                view = ChannelSelect(ctx.author.id, limit=1)
                question = "what channel do you want to use for punishments? (e.g. `#punishments`)"
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                settingContents["punishments"]["channel"] = (
                    view.value[0].id if view.value else None
                )
            elif content == "ban_channel":
                view = ChannelSelect(ctx.author.id, limit=1)
                question = "what channel do you want to use for bans? (e.g. `#bans`)"
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                settingContents["customisation"]["ban_channel"] = (
                    view.value[0].id if view.value else None
                )
            elif content == "kick_channel":
                view = ChannelSelect(ctx.author.id, limit=1)
                question = "what channel do you want to use for kicks? (e.g. `#kicks`)"
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                settingContents["customisation"]["kick_channel"] = (
                    view.value[0].id if view.value else None
                )
            elif content == "bolo_channel":
                view = ChannelSelect(ctx.author.id, limit=1)
                question = "what channel do you want to use for BOLOs? (e.g. `#bolos`)"
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                settingContents["customisation"]["bolo_channel"] = (
                    view.value[0].id if view.value else None
                )
            else:
                return await failure_embed(
                    ctx,
                    "you have not selected one of the options. Run this command again.",
                )
        elif category == "moderation_sync":
            question = "what do you want to do with Game Sync?"
            customselect = CustomSelectMenu(
                ctx.author.id,
                [
                    discord.SelectOption(
                        label="Enable Game Sync",
                        description="Enable the Game Sync module",
                        value="enable",
                    ),
                    discord.SelectOption(
                        label="Disable Game Sync",
                        description="Disable the Game Sync module",
                        value="disable",
                    ),
                    discord.SelectOption(
                        label="Set Webhook Channel",
                        description="Change the channel that ER:LC Webhooks are read in",
                        value="channel",
                    ),
                    discord.SelectOption(
                        label="Set Kick/Ban Webhook Channel",
                        description="Change the channel that the Kick/Ban Webhooks are read in",
                        value="kick_channel",
                    ),
                ],
            )
            await config_msg.edit(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                view=customselect,
            )
            await customselect.wait()
            content = customselect.value
            if content == "enable":
                if not settingContents.get("moderation_sync"):
                    settingContents["moderation_sync"] = {
                        "enabled": True,
                        "webhook_channel": None,
                        "kick_ban_webhook_channel": None,
                    }
                settingContents["moderation_sync"]["enabled"] = True
            elif content == "disable":
                if not settingContents.get("moderation_sync"):
                    settingContents["moderation_sync"] = {
                        "enabled": True,
                        "webhook_channel": None,
                        "kick_ban_webhook_channel": None,
                    }
                settingContents["moderation_sync"]["enabled"] = False
            elif content == "channel":
                view = ChannelSelect(ctx.author.id, limit=1)
                question = 'what channel do you want to use for Game Sync? (e.g. `#command-logs`)\n*This channel is where the "Command Usage" embeds are sent.*'
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                if not settingContents.get("moderation_sync"):
                    settingContents["moderation_sync"] = {
                        "enabled": True,
                        "webhook_channel": None,
                        "kick_ban_webhook_channel": None,
                    }
                settingContents["moderation_sync"]["webhook_channel"] = (
                    view.value[0].id if view.value else None
                )
            elif content == "kick_channel":
                view = ChannelSelect(ctx.author.id, limit=1)
                question = 'what channel do you want to use for Game Sync? (e.g. `#kick-ban-logs`)\n*This channel is where the "Player Kicked" embeds are sent.*'
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                if not settingContents.get("moderation_sync"):
                    settingContents["moderation_sync"] = {
                        "enabled": True,
                        "webhook_channel": None,
                        "kick_ban_webhook_channel": None,
                    }
                settingContents["moderation_sync"]["kick_ban_webhook_channel"] = (
                    view.value[0].id if view.value else None
                )
        elif category == "shift_management":
            question = "what do you want to do with shift management?"
            customselect = CustomSelectMenu(
                ctx.author.id,
                [
                    discord.SelectOption(
                        label="Enable Shift Management",
                        description="Enable the shift management module",
                        value="enable",
                    ),
                    discord.SelectOption(
                        label="Disable Shift Management",
                        description="Disable the shift management module",
                        value="disable",
                    ),
                    discord.SelectOption(
                        label="Set Shift Channel",
                        description="Set the channel for shift management",
                        value="channel",
                    ),
                    discord.SelectOption(
                        label="Set Nickname Prefix",
                        description="Set the nickname prefix. This will be put to people's nicknames on-duty.",
                        value="nickname_prefix",
                    ),
                    discord.SelectOption(
                        label="Set Maximum Staff Online",
                        description="Set the maximum amount of staff allowed online consecutively.",
                        value="maximum_staff",
                    ),
                    discord.SelectOption(
                        label="Set On Duty Role",
                        description="Set the role to be given when on duty.",
                        value="role",
                    ),
                    discord.SelectOption(
                        label="Quota System",
                        description="Set the weekly quota.",
                        value="quota",
                    ),
                ],
            )

            await config_msg.edit(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                view=customselect,
            )
            await customselect.wait()
            content = customselect.value
            if content == "enable":
                settingContents["shift_management"]["enabled"] = True
            elif content == "disable":
                settingContents["shift_management"]["enabled"] = False
            elif content == "quota":
                content = (
                    await request_response(
                        bot, ctx, "what would you like the quota to be? (s/m/h/d)"
                    )
                ).content
                content = content.strip()
                total_seconds = 0

                if content.endswith(("s", "m", "h", "d")):
                    if content.endswith("s"):
                        total_seconds = int(content.removesuffix("s"))
                    if content.endswith("m"):
                        total_seconds = int(content.removesuffix("m")) * 60
                    if content.endswith("h"):
                        total_seconds = int(content.removesuffix("h")) * 60 * 60
                    if content.endswith("d"):
                        total_seconds = int(content.removesuffix("d")) * 60 * 60 * 24
                else:
                    return await failure_embed(
                        ctx,
                        "we could not translate your time. Remember to end it with s/m/h/d.",
                    )

                settingContents["shift_management"]["quota"] = total_seconds
            elif content == "nickname_prefix":
                view = CustomModalView(
                    ctx.author.id,
                    "Nickname Prefix",
                    "Nickname Prefix",
                    [
                        (
                            "nickname",
                            discord.ui.TextInput(
                                placeholder="Nickname Prefix",
                                min_length=1,
                                max_length=20,
                                label="Nickname Prefix",
                            ),
                        )
                    ],
                )
                question = "what do you want to use a Nickname Prefix? (e.g. `𝗦𝘁𝗮𝗳𝗳 |`)"
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                if view.modal.nickname.value.lower() in ["none", "clear"]:
                    settingContents["shift_management"][
                        "nickname_prefix"
                    ] = None
                else:
                    settingContents["shift_management"][
                        "nickname_prefix"
                    ] = view.modal.nickname.value
            elif content == "maximum_staff":
                view = CustomSelectMenu(
                    ctx.author.id,
                    [
                        discord.SelectOption(
                            label="No Limit",
                            description="There is no limit to the amount of staff online.",
                            value="0",
                        ),
                        discord.SelectOption(
                            label="5 Staff Members",
                            description="Only 5 staff members can be consecutively online.",
                            value="5",
                        ),
                        discord.SelectOption(
                            label="10 Staff Members",
                            description="Only 10 staff members can be consecutively online.",
                            value="10",
                        ),
                        discord.SelectOption(
                            label="Custom",
                            description="Set a custom amount of staff members that can be consecutively online",
                            value="custom",
                        ),
                    ],
                )

                question = "Wwat do you want the Maximum Staff limit to be?"
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()

                if view.value == "custom":
                    view = CustomModalView(
                        ctx.author.id,
                        "Maximum Staff",
                        "Maximum Staff",
                        [
                            (
                                "max_staff",
                                discord.ui.TextInput(
                                    placeholder="Maximum amount of staff allowed online (e.g. 5)",
                                    min_length=1,
                                    max_length=20,
                                    label="Maximum Staff",
                                ),
                            )
                        ],
                    )
                    question = "what do you want the maximum amount of staff allowed online to be? (e.g. 5)"
                    await config_msg.edit(
                        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                        view=view,
                    )
                    await view.wait()
                    try:
                        int(view.modal.max_staff.value)
                    except (ValueError, TypeError):
                        return await failure_embed(
                            ctx,
                            "that is not a valid number to set as a Maximum Staff Limit. Try again by rerunning this command.",
                        )
                    settingContents["shift_management"]["maximum_staff"] = int(
                        view.modal.max_staff.value
                    )
                else:
                    settingContents["shift_management"]["maximum_staff"] = int(
                        view.value
                    )

            elif content == "channel":
                view = ChannelSelect(ctx.author.id, limit=1)
                question = "what channel do you want to use for shift management? (e.g. shift logons)"
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                settingContents["shift_management"]["channel"] = (
                    view.value[0].id if view.value else None
                )
            elif content == "role":
                view = RoleSelect(ctx.author.id)
                question = (
                    "what roles do you want to use as a On-Duty role? (e.g. `@On-Duty`)"
                )
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                settingContents["shift_management"]["role"] = (
                    [role.id for role in view.value]
                    if [role.id for role in view.value]
                    else []
                )
            else:
                return await failure_embed(
                    ctx,
                    "pick one of the options. `enable`, `disable`, `channel`. Run this command again with correct parameters.",
                )
        elif category == "shift_types":
            question = "what do you want to do with Shift Types?"

            customselect = CustomSelectMenu(
                ctx.author.id,
                [
                    discord.SelectOption(
                        label="View Shift Types",
                        description="View all shift types",
                        value="view",
                    ),
                    discord.SelectOption(
                        label="Manage Shift Types",
                        description="Add and remove shift types",
                        value="manage",
                    ),
                ],
            )

            await config_msg.edit(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                view=customselect,
                embed=None,
            )

            timeout = await customselect.wait()
            if timeout:
                return

            if not customselect.value:
                return

            if customselect.value == "view":
                shift_types = settingContents.get("shift_types")
                if shift_types is None:
                    shift_types = {"enabled": False, "types": []}

                embed = discord.Embed(
                    title="<:ERMLog:1113210855891423302> Shift Types",
                    color=0xED4348,
                )

                embed.add_field(
                    name="<:ERMList:1111099396990435428> Basic Configuration",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Enabled:** {shift_types.get('enabled')}",
                    inline=False,
                )

                embed.set_author(
                    name=ctx.author.name,
                    icon_url=ctx.author.display_avatar.url,
                )
                embed.set_thumbnail(url=ctx.guild.icon.url)

                for type in shift_types.get("types"):
                    roles = type.get("role")
                    if type.get("role") is None or len(type.get("role")) == 0:
                        roles = "None"
                    else:
                        roles = ", ".join([f"<@&{role}>" for role in type.get("role")])

                    if type.get("channel") is None:
                        channel = "None"
                    else:
                        channel = f"<#{type.get('channel')}>"

                    embed.add_field(
                        name=f"<:ERMList:1111099396990435428> {type.get('name')}",
                        value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Name:** {type.get('name')}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Default:** {type.get('default')}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Role:** {roles}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Channel:** {channel}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **Nickname Prefix:** {type.get('nickname') if type.get('nickname') else 'None'}",
                        inline=False,
                    )

                if len(embed.fields) == 1:
                    embed.add_field(
                        name="<:ERMList:1111099396990435428> Shift Types",
                        value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> No shift types have been added.",
                        inline=False,
                    )

                return await config_msg.edit(
                    embed=embed,
                    view=None,
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, you are **viewing** Shift Types.",
                )

            elif customselect.value == "manage":
                shift_types = settingContents.get("shift_types")
                if shift_types is None:
                    shift_types = {"enabled": False, "types": []}

                view = CustomSelectMenu(
                    ctx.author.id,
                    [
                        discord.SelectOption(
                            label="Enable Shift Types",
                            description="Enable Shift Types",
                            value="enable",
                        ),
                        discord.SelectOption(
                            label="Disable Shift Types",
                            description="Disable Shift Types",
                            value="disable",
                        ),
                        discord.SelectOption(
                            label="Add Shift Type",
                            description="Add a Shift Type",
                            value="add",
                        ),
                        discord.SelectOption(
                            label="Edit Shift Type",
                            description="Edit a Shift Type",
                            value="edit",
                        ),
                        discord.SelectOption(
                            label="Remove Shift Type",
                            description="Remove a Shift Type",
                            value="delete",
                        ),
                    ],
                )

                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** how would you like to manage Shift Types?",
                    view=view,
                    embed=None,
                )
                await view.wait()
                if view.value == "enable":
                    shift_types["enabled"] = True
                    settingContents["shift_types"] = shift_types
                    await bot.settings.update_by_id(settingContents)
                elif view.value == "disable":
                    shift_types["enabled"] = False
                    settingContents["shift_types"] = shift_types
                    await bot.settings.update_by_id(settingContents)
                elif view.value == "add":
                    if len(shift_types.get("types")) >= 25:
                        return await failure_embed(
                            ctx,
                            "you cannot have more than 25 shift types due to discord limitations. Please remove some shift types before adding more.",
                        )

                    view = CustomModalView(
                        ctx.author.id,
                        "Create a Shift Type",
                        "Create a Shift Type",
                        [
                            (
                                "name",
                                discord.ui.TextInput(
                                    placeholder="Name of the Shift Type",
                                    label="Name",
                                    required=True,
                                    min_length=1,
                                    max_length=32,
                                ),
                            )
                        ],
                    )

                    await config_msg.edit(
                        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}** click the buttom below to start the creation process of Shift Types.",
                        view=view,
                        embed=None,
                    )
                    timeout = await view.wait()
                    if timeout:
                        return

                    if view.modal.name.value:
                        name = view.modal.name.value
                    else:
                        return

                    view = YesNoColourMenu(ctx.author.id)

                    await config_msg.edit(
                        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}** would you like this Shift Type to be default?",
                        view=view,
                        embed=None,
                    )
                    timeout = await view.wait()
                    if timeout:
                        return

                    if view.value is True:
                        default = True
                    else:
                        default = False

                    view = YesNoColourMenu(ctx.author.id)

                    await config_msg.edit(
                        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}** would you like a role to be assigned when someone goes on duty with this shift type?",
                        view=view,
                    )
                    timeout = await view.wait()
                    if timeout:
                        return

                    if view.value is True:
                        view = RoleSelect(ctx.author.id)

                        await config_msg.edit(
                            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}** got it. What roles would you like to be assigned?",
                            view=view,
                        )
                        timeout = await view.wait()
                        if timeout:
                            return

                        roles = view.value
                    else:
                        roles = []

                    view = YesNoColourMenu(ctx.author.id)

                    await config_msg.edit(
                        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}** do you want a Nickname Prefix to be added to someone's name when they are on-duty for this shift type?",
                        view=view,
                    )
                    timeout = await view.wait()
                    if timeout:
                        return

                    if view.value is True:
                        view = CustomModalView(
                            ctx.author.id,
                            "Nickname Prefix",
                            "Nickname Prefix",
                            [
                                (
                                    "nickname",
                                    discord.ui.TextInput(
                                        placeholder="Nickname Prefix",
                                        label="Nickname Prefix",
                                        max_length=20,
                                    ),
                                )
                            ],
                        )

                        await config_msg.edit(
                            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}** got it. What would you like the nickname prefix to be?",
                            view=view,
                        )
                        timeout = await view.wait()
                        if timeout:
                            return

                        if view.modal.nickname.value.lower() in ["none", "clear"]:
                            nickname = None
                        else:
                            nickname = view.modal.nickname.value
                    else:
                        nickname = None

                    view = YesNoColourMenu(ctx.author.id)

                    await config_msg.edit(
                        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}** do you want this type to send in a different channel that's not the configured one?",
                        view=view,
                    )
                    timeout = await view.wait()
                    if timeout:
                        return

                    if view.value is True:
                        view = ChannelSelect(ctx.author.id, limit=1)

                        await config_msg.edit(
                            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}** got it. What channel would you like this shift type to log in?",
                            view=view,
                        )
                        timeout = await view.wait()
                        if timeout:
                            return

                        channel = view.value
                        if channel:
                            channel = channel[0]
                        else:
                            return await config_msg.edit(
                                f"<:ERMClose:1111101633389146223> **{ctx.author.id},** you did not select a channel."
                            )
                    else:
                        channel = None

                    shift_types["types"].append(
                        {
                            "id": next(generator),
                            "name": name,
                            "default": default,
                            "role": [role.id for role in roles],
                            "channel": channel.id if channel else None,
                            "nickname": nickname,
                        }
                    )

                    settingContents["shift_types"] = shift_types
                    settingContents["_id"] = settingContents.get("_id") or ctx.guild.id
                    await bot.settings.update_by_id(settingContents)
                elif view.value == "edit":
                    if len(shift_types.get("types")) == 0:
                        return await failure_embed(
                            ctx,
                            "there are no shift types to edit. Create a shift type before attempting to delete one.",
                        )

                    view = CustomSelectMenu(
                        ctx.author.id,
                        [
                            discord.SelectOption(
                                label=type.get("name"),
                                description=type.get("name"),
                                value=str(type.get("id")),
                            )
                            for type in shift_types.get("types")
                        ],
                    )

                    await config_msg.edit(
                        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, which Shift Type would you like to edit?",
                        view=view,
                        embed=None,
                    )
                    timeout = await view.wait()
                    if timeout:
                        return

                    shift_item = None

                    for item in shift_types.get("types"):
                       # # # print(item)
                        if item.get("id") == int(view.value):
                            shift_type = item
                            break

                    if shift_type is None:
                        return await failure_embed(
                            ctx, "that shift type does not exist."
                        )

                    view = CustomSelectMenu(
                        ctx.author.id,
                        [
                            discord.SelectOption(
                                label="Name",
                                description="Edit the name of the shift type",
                                value="name",
                            ),
                            discord.SelectOption(
                                label="Default",
                                description="Change whether this is the default shift type",
                                value="default",
                            ),
                            discord.SelectOption(
                                label="Roles",
                                description="Edit the roles that are assigned when someone is on shift for this type",
                                value="role",
                            ),
                            discord.SelectOption(
                                label="Channel",
                                description="Change the channel logs for this shift type are sent",
                                value="channel",
                            ),
                            discord.SelectOption(
                                label="Nickname",
                                description="Edit the nickname that is given to someone when they are on shift for this type",
                                value="nickname",
                            ),
                        ],
                    )

                    await config_msg.edit(
                        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, what do you want to edit about that Shift Type?",
                        view=view,
                        embed=None,
                    )
                    timeout = await view.wait()
                    if timeout:
                        return

                    if view.value == "name":
                        view = CustomModalView(
                            ctx.author.id,
                            "Edit Shift Type Name",
                            "Edit Shift Type Name",
                            [
                                (
                                    "name",
                                    discord.ui.TextInput(
                                        placeholder="Name of the Shift Type",
                                        label="Name",
                                        required=True,
                                        min_length=1,
                                        max_length=32,
                                    ),
                                )
                            ],
                        )

                        await config_msg.edit(
                            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, what would you like to change the name of this shift type to?",
                            view=view,
                            embed=None,
                        )
                        timeout = await view.wait()
                        if timeout:
                            return

                        if view.modal.name.value:
                            name = view.modal.name.value
                        else:
                            return

                        shift_type["name"] = name

                        settingContents["_id"] = (
                            settingContents.get("_id") or ctx.guild.id
                        )
                        await bot.settings.update_by_id(settingContents)
                    elif view.value == "default":
                        view = YesNoColourMenu(ctx.author.id)

                        await config_msg.edit(
                            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, would you like this Shift Type to be default?",
                            view=view,
                            embed=None,
                        )
                        timeout = await view.wait()
                        if timeout:
                            return

                        if view.value is True:
                            for item in shift_types.get("types"):
                                item["default"] = False

                            shift_type["default"] = True
                        else:
                            shift_type["default"] = False

                        settingContents["_id"] = (
                            settingContents.get("_id") or ctx.guild.id
                        )
                        await bot.settings.update_by_id(settingContents)
                    elif view.value == "role":
                        view = YesNoColourMenu(ctx.author.id)

                        await config_msg.edit(
                            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, would you like a role to be assigned when someone goes on duty with this shift type?",
                            view=view,
                        )
                        timeout = await view.wait()

                        if timeout:
                            return

                        if view.value is True:
                            view = RoleSelect(ctx.author.id)

                            await config_msg.edit(
                                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, got it. What roles would you like to be assigned?",
                                view=view,
                            )
                            timeout = await view.wait()

                            if timeout:
                                return

                            roles = (
                                [role.id for role in view.value]
                                if [role.id for role in view.value]
                                else []
                            )
                        else:
                            roles = []

                        shift_type["role"] = roles
                        settingContents["_id"] = (
                            settingContents.get("_id") or ctx.guild.id
                        )
                        await bot.settings.update_by_id(settingContents)
                    elif view.value == "channel":
                        view = YesNoColourMenu(ctx.author.id)

                        await config_msg.edit(
                            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, do you want this type to send in a different channel that's not the configured one?",
                            view=view,
                        )
                        timeout = await view.wait()

                        if timeout:
                            return

                        if view.value is True:
                            view = ChannelSelect(ctx.author.id, limit=1)

                            await config_msg.edit(
                                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, got it. What channel would you like this shift type to log in?",
                                view=view,
                            )
                            timeout = await view.wait()

                            if timeout:
                                return

                            channel = view.value
                            if channel:
                                channel = channel[0].id
                            else:
                                return await ctx.reply(
                                    f"<:ERMClose:1111101633389146223> **{ctx.author.id}**, you did not select a channel."
                                )

                        else:
                            channel = None

                        shift_type["channel"] = channel
                        settingContents["_id"] = (
                            settingContents.get("_id") or ctx.guild.id
                        )
                        await bot.settings.update_by_id(settingContents)
                    elif view.value == "nickname":
                        view = CustomModalView(
                            ctx.author.id,
                            "Edit Shift Type Nickname",
                            "Edit Shift Type Nickname",
                            [
                                (
                                    "nickname",
                                    discord.ui.TextInput(
                                        placeholder="Nickname Prefix",
                                        label="Nickname Prefix",
                                        required=True,
                                        min_length=1,
                                        max_length=20,
                                    ),
                                )
                            ],
                        )

                        await config_msg.edit(
                            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, got it. What would you like the nickname prefix to be?",
                            view=view,
                        )
                        timeout = await view.wait()
                        if timeout:
                            return

                        if view.modal.nickname.value:
                            nickname = view.modal.nickname.value
                        else:
                            return

                        shift_type["nickname"] = nickname

                        settingContents["_id"] = (
                            settingContents.get("_id") or ctx.guild.id
                        )
                        await bot.settings.update_by_id(settingContents)
                elif view.value == "delete":
                    if len(shift_types.get("types")) == 0:
                        return await failure_embed(
                            ctx, "there are no shift types to delete."
                        )

                    if len(shift_types.get("types")) == 0:
                        return await failure_embed(
                            ctx, "uh, there are no shift types to delete."
                        )
                    view = CustomSelectMenu(
                        ctx.author.id,
                        [
                            discord.SelectOption(
                                label=type.get("name"),
                                description=type.get("name"),
                                value=type.get("id"),
                            )
                            for type in shift_types.get("types")
                        ],
                    )

                    await config_msg.edit(
                        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, select the shift type you wish to delete",
                        view=view,
                        embed=None,
                    )
                    timeout = await view.wait()
                    if timeout:
                        return

                    shift_type = [
                        type
                        for type in shift_types.get("types")
                        if type.get("id") == int(view.value)
                    ]
                    if len(shift_type) == 0:
                        return await failure_embed(
                            ctx, "that shift type does not exist."
                        )

                    shift_type = shift_type[0]

                    shift_types.get("types").remove(shift_type)
                    settingContents["_id"] = settingContents.get("_id") or ctx.guild.id
                    await bot.settings.update_by_id(settingContents)

        elif category == "privacy":
            privacyConfig = await bot.privacy.find_by_id(ctx.guild.id)
            if privacyConfig is None:
                privacyConfig = {"_id": ctx.guild.id, "global_warnings": True}
            question = "what would you like to change?"
            customselect = CustomSelectMenu(
                ctx.author.id,
                [
                    discord.SelectOption(
                        label="Enable Global Warnings",
                        description="Enable global warnings for this server",
                        value="enable_global_warnings",
                    ),
                    discord.SelectOption(
                        label="Disable Global Warnings",
                        description="Disable global warnings for this server",
                        value="disable_global_warnings",
                    ),
                ],
            )
            await config_msg.edit(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                view=customselect,
            )
            await customselect.wait()
            content = customselect.value
            if content == "enable_global_warnings":
                privacyConfig["global_warnings"] = True
            if content == "disable_global_warnings":
                privacyConfig["global_warnings"] = False
            await bot.privacy.upsert(privacyConfig)
            return await config_msg.edit(
                content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, your configuration has been changed.",
                view=None,
                embed=None,
            )
        elif category == "game_logging":
            if not settingContents.get("game_logging"):
                settingContents["game_logging"] = {
                    "message": {"enabled": False, "channel": None},
                    "sts": {"enabled": False, "channel": None},
                    "priority": {"enabled": False, "channel": None},
                }

            question = "what would you like to manage?"
            customselect = CustomSelectMenu(
                ctx.author.id,
                [
                    discord.SelectOption(
                        label="Manage Message Logging",
                        description="Manage message / announcement logging",
                        value="message",
                    ),
                    discord.SelectOption(
                        label="Manage STS Logging",
                        description="Manage Shoulder-to-Shoulder Logging",
                        value="sts",
                    ),
                    discord.SelectOption(
                        label="Manage Priority Logging",
                        description="Manage logging priorities and Roleplay permissions",
                        value="priority",
                    ),
                ],
            )
            await config_msg.edit(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                view=customselect,
            )
            await customselect.wait()
            content = customselect.value

            if not content:
                return

            if content == "message":
                question = "what would you like to change?"

                customselect = CustomSelectMenu(
                    ctx.author.id,
                    [
                        discord.SelectOption(
                            label="Enable Message Logging",
                            description="Enable message logging for this server",
                            value="enable_message_logging",
                        ),
                        discord.SelectOption(
                            label="Disable Message Logging",
                            description="Disable message logging for this server",
                            value="disable_message_logging",
                        ),
                        discord.SelectOption(
                            label="Set Message Logging Channel",
                            description="Set the channel for message logging",
                            value="set_message_logging_channel",
                        ),
                    ],
                )
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=customselect,
                )
                timeout = await customselect.wait()
                if timeout:
                    return

                content = customselect.value
                if content == "enable_message_logging":
                    settingContents["game_logging"]["message"]["enabled"] = True
                elif content == "disable_message_logging":
                    settingContents["game_logging"]["message"]["enabled"] = False
                elif content == "set_message_logging_channel":
                    view = ChannelSelect(ctx.author.id, limit=1)

                    await config_msg.edit(
                        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                        view=view,
                    )

                    timeout = await view.wait()
                    if timeout:
                        return

                    if not view.value:
                        return

                    if view.value:
                        channel = view.value
                        settingContents["game_logging"]["message"]["channel"] = (
                            channel[0].id if channel else None
                        )
            elif content == "sts":
                question = "what would you like to change?"

                customselect = CustomSelectMenu(
                    ctx.author.id,
                    [
                        discord.SelectOption(
                            label="Enable STS Logging",
                            description="Enable STS logging for this server",
                            value="enable_sts_logging",
                        ),
                        discord.SelectOption(
                            label="Disable STS Logging",
                            description="Disable STS logging for this server",
                            value="disable_sts_logging",
                        ),
                        discord.SelectOption(
                            label="Set STS Logging Channel",
                            description="Set the channel for STS logging",
                            value="set_sts_logging_channel",
                        ),
                    ],
                )

                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=customselect,
                )
                timeout = await customselect.wait()
                if timeout:
                    return

                content = customselect.value
                if content == "enable_sts_logging":
                    settingContents["game_logging"]["sts"]["enabled"] = True
                elif content == "disable_sts_logging":
                    settingContents["game_logging"]["sts"]["enabled"] = False
                elif content == "set_sts_logging_channel":
                    view = ChannelSelect(ctx.author.id, limit=1)
                    question = "what channel would you like to set for STS logging?"
                    await config_msg.edit(
                        content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                        view=view,
                    )

                    timeout = await view.wait()
                    if timeout:
                        return

                    if not view.value:
                        return

                    if view.value:
                        channel = view.value
                        settingContents["game_logging"]["sts"]["channel"] = (
                            channel[0].id if channel else None
                        )
            elif content == "priority":
                question = "what would you like to change?"

                customselect = CustomSelectMenu(
                    ctx.author.id,
                    [
                        discord.SelectOption(
                            label="Enable Priority Logging",
                            description="Enable Priority logging for this server",
                            value="enable_priority_logging",
                        ),
                        discord.SelectOption(
                            label="Disable Priority Logging",
                            description="Disable Priority logging for this server",
                            value="disable_priority_logging",
                        ),
                        discord.SelectOption(
                            label="Set Priority Logging Channel",
                            description="Set the channel for Priority logging",
                            value="set_priority_logging_channel",
                        ),
                    ],
                )

                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=customselect,
                )
                timeout = await customselect.wait()
                if timeout:
                    return

                content = customselect.value
                if content == "enable_priority_logging":
                    if not settingContents["game_logging"].get("priority"):
                        settingContents["game_logging"]["priority"] = {
                            "enabled": False,
                            "channel": None,
                        }

                    settingContents["game_logging"]["priority"]["enabled"] = True
                elif content == "disable_priority_logging":
                    if not settingContents["game_logging"].get("priority"):
                        settingContents["game_logging"]["priority"] = {
                            "enabled": False,
                            "channel": None,
                        }

                    settingContents["game_logging"]["priority"]["enabled"] = False
                elif content == "set_priority_logging_channel":
                    embed = discord.Embed(
                        title="<:EditIcon:1042550862834323597> Change Configuration",
                        description=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> what channel do you want to set for Priority logging?",
                        color=0xED4348,
                    )

                    view = ChannelSelect(ctx.author.id, limit=1)

                    await ctx.reply(embed=embed, view=view)
                    timeout = await view.wait()
                    if timeout:
                        return

                    if not view.value:
                        return

                    if not settingContents["game_logging"].get("priority"):
                        settingContents["game_logging"]["priority"] = {
                            "enabled": False,
                            "channel": None,
                        }
                    channel = view.value
                    settingContents["game_logging"]["priority"]["channel"] = (
                        channel[0].id if channel else None
                    )
            await bot.settings.update_by_id(settingContents)
            return await config_msg.edit(
                content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, your configuration has been changed.",
                view=None,
                embed=None,
            )
        elif category == "security":
            question = "what do you want to do with Game Security?"
            customselect = CustomSelectMenu(
                ctx.author.id,
                [
                    discord.SelectOption(
                        label="Enable Game Security",
                        description="Enable Game Security for this server",
                        value="enable",
                    ),
                    discord.SelectOption(
                        label="Disable Game Security",
                        description="Disable Game Security for this server",
                        value="disable",
                    ),
                    discord.SelectOption(
                        label="Mention Roles on Abuse",
                        description="These roles will be pinged when abuse is detected",
                        value="role",
                    ),
                    discord.SelectOption(
                        label="Set Report Channel",
                        description="Set the channel where reports will be sent",
                        value="channel",
                    ),
                    discord.SelectOption(
                        label="Set Webhook Channel",
                        description="This channel is where ER:LC webhooks are sent",
                        value="webhook_channel",
                    ),
                ],
            )
            await config_msg.edit(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                view=customselect,
            )

            await customselect.wait()
            content = customselect.value

            if not "game_security" in settingContents.keys():
                settingContents["game_security"] = {}

            if content == "enable":
                settingContents["game_security"]["enabled"] = True
            elif content == "disable":
                settingContents["game_security"]["enabled"] = False
            elif content == "role":
                view = RoleSelect(ctx.author.id)
                question = "what roles do you want to be mentioned when abuse is detected? (e.g. `@Leadership`)"

                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                settingContents["game_security"]["role"] = (
                    [role.id for role in view.value]
                    if [role.id for role in view.value]
                    else []
                )
            elif content == "webhook_channel":
                view = ChannelSelect(ctx.author.id, limit=1)
                question = (
                    "what channel are ER:LC webhooks sent to? (e.g. `#kicks-and-bans`)"
                )
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                settingContents["game_security"]["webhook_channel"] = (
                    view.value[0].id if view.value else None
                )
            elif content == "channel":
                view = ChannelSelect(ctx.author.id, limit=1)
                question = "what channel do you want Anti-Abuse reports to go to? (e.g. `#admin-abuse`)"
                await config_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, {question}",
                    view=view,
                )
                await view.wait()
                settingContents["game_security"]["channel"] = (
                    view.value[0].id if view.value else None
                )
            else:
                return await failure_embed(
                    ctx,
                    "pick one of the options. `enable`, `disable`, `role`, `channel`, `webhook_channel`. Run this command again with correct parameters.",
                )
        else:
            return await failure_embed(
                ctx,
                "you did not pick any of the options. Run this command again with correct parameters.",
            )

        if category != "shift_types":
            await bot.settings.update_by_id(settingContents)

        await config_msg.edit(
            content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, your configuration has been changed.",
            view=None,
            embed=None,
        )

    @commands.hybrid_command(
        name="setup",
        description="Sets up the bot for use.",
        extras={"category": "Configuration"},
        aliases=["setupbot"],
        with_app_command=True,
    )
    @is_management()
    async def setup(self, ctx):
        bot = self.bot
        settingContents = {
            "_id": 0,
            "verification": {
                "enabled": False,
                "role": None,
            },
            "antiping": {"enabled": False, "role": None, "bypass_role": "None"},
            "staff_management": {"enabled": False, "channel": None},
            "punishments": {"enabled": False, "channel": None},
            "shift_management": {"enabled": False, "channel": None, "role": None},
            "customisation": {
                "color": "",
                "prefix": ">",
                "brand_name": "Emergency Response Management",
                "thumbnail_url": "",
                "footer_text": "Staff Logging Systems",
                "ban_channel": None,
            },
        }

        options = [
            discord.SelectOption(
                label="All features",
                value="all",
                description="All features of the bot, contains all of the features below",
            ),
            discord.SelectOption(
                label="Staff Management",
                value="staff_management",
                description="Inactivity Notices, and managing staff members",
            ),
            discord.SelectOption(
                label="Punishments",
                value="punishments",
                description="Punishing community members for rule infractions",
            ),
            discord.SelectOption(
                label="Shift Management",
                value="shift_management",
                description="Shifts (duty manage, duty admin), and where logs should go",
            ),
        ]

        welcome = discord.Embed(
            color=0xED4348,
        )
        welcome.description = "<:ERMCheck:1111089850720976906> **All *(default)***\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>All features of the bot\n\n<:ERMAdmin:1111100635736187011> **Staff Management**\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Manage your staff members, LoAs, and more!\n\n<:ERMPunish:1111095942075138158> **Punishments**\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Roblox moderation, staff logging systems, and more!\n\n<:ERMSchedule:1111091306089939054> **Shift Management**\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>Manage staff member's shifts, view who's in game!"

        view = MultiSelectMenu(ctx.author.id, options)

        await ctx.reply(
            embed=welcome,
            view=view,
            content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name}**, setting up ERM is easy! You're on the interactive setup wizard. Below, select the module(s) you would like to enable.",
        )

        await view.wait()
        if not view.value:
            return await failure_embed(
                ctx,
                "you took too long to respond. Try again.",
            )

        if "all" in view.value:
            settingContents["staff_management"]["enabled"] = True
            settingContents["punishments"]["enabled"] = True
            settingContents["shift_management"]["enabled"] = True
        else:
            if "punishments" in view.value:
                settingContents["punishments"]["enabled"] = True
            if "shift_management" in view.value:
                settingContents["shift_management"]["enabled"] = True
            if "staff_management" in view.value:
                settingContents["staff_management"]["enabled"] = True

        if settingContents["staff_management"]["enabled"]:
            question = "what channel do you want to use for staff management?"
            view = ChannelSelect(ctx.author.id, limit=1)
            await pending_embed(ctx, question, view=view)
            await view.wait()
            convertedContent = view.value
            settingContents["staff_management"]["channel"] = (
                convertedContent[0].id if convertedContent else None
            )

            question = "what role would you like to use for your staff role? (e.g. @Staff)\n*You can select multiple roles.*"
            view = RoleSelect(ctx.author.id)
            await pending_embed(ctx, question, view=view)
            await view.wait()
            convertedContent = view.value
            settingContents["staff_management"]["role"] = (
                [role.id for role in convertedContent] if convertedContent else []
            )

            question = "what role would you like to use for your Management role? (e.g. @Management)\n*You can select multiple roles.*"
            view = RoleSelect(ctx.author.id)
            await pending_embed(ctx, question, view=view)
            await view.wait()
            convertedContent = view.value
            settingContents["staff_management"]["management_role"] = (
                [role.id for role in convertedContent] if convertedContent else []
            )

            view = YesNoMenu(ctx.author.id)
            question = "do you want a role to be assigned to staff members when they are on LoA (Leave of Absence)?"
            await pending_embed(ctx, question, view=view)
            await view.wait()
            if view.value is not None:
                if view.value:
                    question = "what role(s) would you like to be given?\n*You can select multiple roles.*"
                    view = RoleSelect(ctx.author.id)
                    await pending_embed(ctx, question, view=view)
                    await view.wait()
                    convertedContent = view.value
                    settingContents["staff_management"]["loa_role"] = (
                        [role.id for role in convertedContent]
                        if convertedContent
                        else []
                    )

            view = YesNoMenu(ctx.author.id)
            question = "do you want a role to be assigned to staff members when they are on RA (Reduced Activity)?"
            await pending_embed(ctx, question, view=view)
            await view.wait()
            if view.value is not None:
                if view.value:
                    question = "what role(s) would you like to be given?\n*You can select multiple roles.*"
                    view = RoleSelect(ctx.author.id)
                    await pending_embed(ctx, question, view=view)
                    await view.wait()
                    convertedContent = view.value
                    settingContents["staff_management"]["ra_role"] = (
                        [role.id for role in convertedContent]
                        if convertedContent
                        else []
                    )
        if settingContents["punishments"]["enabled"]:
            question = "what channel do you want to use for punishments?"
            view = ChannelSelect(ctx.author.id, limit=1)
            await pending_embed(ctx, question, view=view)
            await view.wait()
            convertedContent = view.value
            settingContents["punishments"]["channel"] = (
                convertedContent[0].id if convertedContent else None
            )
        if settingContents["shift_management"]["enabled"]:
            question = "what channel do you want to use for shift management? (e.g. shift signups, etc.)"
            view = ChannelSelect(ctx.author.id, limit=1)
            await pending_embed(ctx, question, view=view)
            await view.wait()
            convertedContent = view.value
            settingContents["shift_management"]["channel"] = (
                convertedContent[0].id if convertedContent else None
            )

            view = YesNoMenu(ctx.author.id)
            question = "do you want a role to be assigned to staff members when they are in game?"
            await pending_embed(ctx, question, view=view)
            await view.wait()
            if view.value is not None:
                if view.value:
                    question = "what role(s) would you like to be given?\n*You can select multiple roles.*"
                    view = RoleSelect(ctx.author.id, limit=1)
                    await pending_embed(ctx, question, view=view)
                    await view.wait()
                    convertedContent = view.value
                    settingContents["shift_management"]["role"] = (
                        [role.id for role in convertedContent]
                        if convertedContent
                        else []
                    )

            view = YesNoMenu(ctx.author.id)
            question = "do you have a weekly quota? (e.g. `2h`, `90m`, `7h`)"
            await pending_embed(ctx, question, view=view)
            await view.wait()
            if view.value is not None:
                if view.value:
                    content = (
                        await request_response(
                            bot, ctx, "what would you like the quota to be? (s/m/h/d)"
                        )
                    ).content
                    content = content.strip()
                    total_seconds = 0

                    try:
                        if content.endswith(("s", "m", "h", "d")):
                            if content.endswith("s"):
                                total_seconds = int(content.removesuffix("s"))
                            if content.endswith("m"):
                                total_seconds = int(content.removesuffix("m")) * 60
                            if content.endswith("h"):
                                total_seconds = int(content.removesuffix("h")) * 60 * 60
                            if content.endswith("d"):
                                total_seconds = (
                                    int(content.removesuffix("d")) * 60 * 60 * 24
                                )
                        else:
                            await failure_embed(ctx,
                                                'we could not translate your time. Though, setup will continue and you can set your Shift Management quota later.')

                        settingContents["shift_management"]["quota"] = total_seconds
                    except:
                        await failure_embed(ctx, 'we could not translate your time. Though, setup will continue and you can set your Shift Management quota later.')

            # privacyDefault = {"_id": ctx.guild.id, "global_warnings": True}

            # view = YesNoMenu(ctx.author.id)
            # question = "Do you want your server's warnings to be able to be queried across the bot? (e.g. `globalsearch`)"
            # embed = discord.Embed(
            #     color=0xED4348, description=f"<:ArrowRight:1035003246445596774> {question}"
            # )
            #
            # await ctx.reply(embed=embed, view=view)
            # await view.wait()
            # if view.value is not None:
            #     if view.value == True:
            #         privacyDefault["global_warnings"] = True
            #     else:
            #         privacyDefault["global_warnings"] = False
            #
            # if not await bot.privacy.find_by_id(ctx.guild.id):
            #     await bot.privacy.insert(privacyDefault)
            # else:
            #     await bot.privacy.update_by_id(privacyDefault)

        settingContents["_id"] = ctx.guild.id
        if not await bot.settings.find_by_id(ctx.guild.id):
            await bot.settings.insert(settingContents)
        else:
            await bot.settings.update_by_id(settingContents)

        await ctx.reply(
            content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, your configuration has been changed."
        )


async def setup(bot):
    await bot.add_cog(Configuration(bot))
