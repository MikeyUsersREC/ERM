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
from utils.utils import create_invis_embed, invis_embed, request_response


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
            return await invis_embed(
                ctx,
                "The server has not been set up yet. Please run `/setup` to set up the server.",
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
            title="<:support:1035269007655321680> Server Configuration",
            description=f"<:ArrowRight:1035003246445596774> Here are the current settings for **{ctx.guild.name}**:",
            color=0x2A2D31,
        )
        embed.add_field(
            name="<:SettingIcon:1035353776460152892>Verification",
            value="<:ArrowRightW:1035023450592514048>**Enabled:** {}\n<:ArrowRightW:1035023450592514048>**Role:** {}".format(
                settingContents["verification"]["enabled"], verification_role
            ),
            inline=False,
        )

        embed.add_field(
            name="<:MessageIcon:1035321236793860116> Anti-ping",
            value="<:ArrowRightW:1035023450592514048>**Enabled:** {}\n<:ArrowRightW:1035023450592514048>**Role:** {}\n<:ArrowRightW:1035023450592514048>**Bypass Role:** {}\n<:ArrowRightW:1035023450592514048>**Use Hierarchy:** {}".format(
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
            name="<:staff:1035308057007230976> Staff Management",
            value="<:ArrowRightW:1035023450592514048>**Enabled:** {}\n<:ArrowRightW:1035023450592514048>**Channel:** {}\n<:ArrowRightW:1035023450592514048>**Staff Role:** {}\n<:ArrowRightW:1035023450592514048>**Management Role:** {}\n<:ArrowRightW:1035023450592514048>**LOA Role:** {}\n<:ArrowRightW:1035023450592514048>**RA Role:** {}".format(
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
            name="<:MalletWhite:1035258530422341672> Punishments",
            value="<:ArrowRightW:1035023450592514048>**Enabled:** {}\n<:ArrowRightW:1035023450592514048>**Channel:** {}".format(
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
            name="<:SyncIcon:1071821068551073892> Game Sync",
            value="<:ArrowRightW:1035023450592514048>**Enabled:** {}\n<:ArrowRightW:1035023450592514048>**Webhook Channel:** {}\n<:ArrowRightW:1035023450592514048>**Kick/Ban Webhook Channel:** {}".format(
                moderation_sync_enabled, sync_webhook_channel, kick_ban_webhook_channel
            ),
            inline=False,
        )

        embed.add_field(
            name="<:Search:1035353785184288788> Shift Management",
            value="<:ArrowRightW:1035023450592514048>**Enabled:** {}\n<:ArrowRightW:1035023450592514048>**Channel:** {}\n<:ArrowRightW:1035023450592514048>**Role:** {}\n<:ArrowRightW:1035023450592514048>**Nickname Prefix:** {}\n<:ArrowRightW:1035023450592514048>**Quota:** {}\n<:ArrowRightW:1035023450592514048>**Maximum Staff On Duty:** {}".format(
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
            name="<:FlagIcon:1035258525955395664> Customisation",
            value="<:ArrowRightW:1035023450592514048>**Color:** {}\n<:ArrowRightW:1035023450592514048>**Prefix:** `{}`\n<:ArrowRightW:1035023450592514048>**Brand Name:** {}\n<:ArrowRightW:1035023450592514048>**Thumbnail URL:** {}\n<:ArrowRightW:1035023450592514048>**Footer Text:** {}\n<:ArrowRightW:1035023450592514048>**Compact Mode:** {}\n<:ArrowRightW:1035023450592514048>**Ban Channel:** {}\n<:ArrowRightW:1035023450592514048>**Kick Channel:** {}\n<:ArrowRightW:1035023450592514048>**BOLO Channel:** {}".format(
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
            name="<:WarningIcon:1035258528149033090> Game Security",
            value="<:ArrowRightW:1035023450592514048>**Enabled:** {}\n<:ArrowRightW:1035023450592514048>**Channel:** {}\n<:ArrowRightW:1035023450592514048>**Role:** {}\n<:ArrowRightW:1035023450592514048>**Webhook Channel:** {}".format(
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
            name="<:SConductTitle:1053359821308567592> Game Logging",
            value="<:ArrowRightW:1035023450592514048>**Message Logging Enabled:** {}\n<:ArrowRightW:1035023450592514048>**Message Logging Channel:** {}\n<:ArrowRightW:1035023450592514048>**STS Logging Enabled:** {}\n<:ArrowRightW:1035023450592514048>**STS Logging Channel:** {}\n<:ArrowRightW:1035023450592514048>**Priority Logging Enabled:** {}\n<:ArrowRightW:1035023450592514048>**Priority Logging Channel:** {}".format(
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
            name="<:staff:1035308057007230976> Privacy",
            value="<:ArrowRightW:1035023450592514048>**Global Warnings:** {}".format(
                await check_privacy(bot, ctx.guild.id, "global_warnings")
            ),
            inline=False,
        )

        embed.add_field(
            name="<:Clock:1035308064305332224> Shift Types",
            value="<:ArrowRightW:1035023450592514048> **To view Shift Types, use the Select Menu below.**",
            inline=False,
        )

        view = CustomSelectMenu(
            ctx.author.id,
            [
                discord.SelectOption(
                    label="View Shift Types",
                    value="view",
                    description="View all shift types.",
                    emoji="<:Clock:1035308064305332224>",
                )
            ],
        )

        for field in embed.fields:
            field.inline = False

        await ctx.send(embed=embed, view=view)
        timeout = await view.wait()
        if timeout:
            return

        if view.value == "view":
            shift_types = settingContents.get("shift_types")
            if shift_types is None:
                shift_types = {"enabled": False, "types": []}

            embed = discord.Embed(
                title="<:Clock:1035308064305332224> Shift Types",
                description=f"<:ArrowRight:1035003246445596774> Here is the Shift Types configuration for **{ctx.guild.name}**:",
                color=0x2A2D31,
            )

            embed.add_field(
                name="<:QMark:1035308059532202104> Basic Configuration",
                value=f"<:ArrowRightW:1035023450592514048> **Enabled:** {shift_types.get('enabled')}",
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
                    name=f"<:Pause:1035308061679689859> {type.get('name')}",
                    value=f"<:ArrowRightW:1035023450592514048> **Name:** {type.get('name')}\n<:ArrowRightW:1035023450592514048> **Default:** {type.get('default')}\n<:ArrowRightW:1035023450592514048> **Role:** {roles}\n<:ArrowRightW:1035023450592514048> **Channel:** {channel}\n<:ArrowRightW:1035023450592514048> **Nickname Prefix:** {type.get('nickname') if type.get('nickname') else 'None'}",
                    inline=False,
                )

            if len(embed.fields) == 1:
                embed.add_field(
                    name="<:Pause:1035308061679689859> Shift Types",
                    value=f"<:ArrowRight:1035003246445596774> No shift types have been added.",
                    inline=False,
                )

            await ctx.send(embed=embed)
            return

    @config_group.command(
        name="change",
        description="Change the configuration of the server.",
        extras={"category": "Configuration"},
    )
    @is_management()
    async def changeconfig(self, ctx):
        bot = self.bot
        if not await bot.settings.find_by_id(ctx.guild.id):
            return await invis_embed(
                ctx,
                "The server has not been set up yet. Please run `/setup` to set up the server.",
            )

        settingContents = await bot.settings.find_by_id(ctx.guild.id)

        category = SettingsSelectMenu(ctx.author.id)

        embed = discord.Embed(
            title="<:EditIcon:1042550862834323597> Change Configuration",
            description="<:ArrowRight:1035003246445596774> What category would you like to configure?",
            color=0x2A2D31,
        )
        await ctx.send(embed=embed, view=category)

        await category.wait()
        category = category.value

        if category == "verification":
            question = "What do you want to do with verification?"
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

            embed = discord.Embed(
                title="<:EditIcon:1042550862834323597> Change Configuration",
                description=f"<:ArrowRight:1035003246445596774> {question}",
                color=0x2A2D31,
            )

            await ctx.send(embed=embed, view=customselect)

            await customselect.wait()
            content = customselect.value
            if content == "enable":
                settingContents["verification"]["enabled"] = True
            elif content == "disable":
                settingContents["verification"]["enabled"] = False
            elif content == "role":
                view = RoleSelect(ctx.author.id)
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> What roles do you want to be given on Verification?",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)
                await view.wait()
                settingContents["verification"]["role"] = (
                    [role.id for role in view.value]
                    if [role.id for role in view.value]
                    else []
                )
            else:
                return await invis_embed(
                    ctx,
                    "Please pick one of the options. `enable`, `disable`, `role`. Please run this command again with correct parameters.",
                )
        elif category == "antiping":
            question = "What do you want to do with antiping?"
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
            embed = discord.Embed(
                title="<:EditIcon:1042550862834323597> Change Configuration",
                description=f"<:ArrowRight:1035003246445596774> {question}",
                color=0x2A2D31,
            )

            await ctx.send(embed=embed, view=customselect)
            await customselect.wait()
            content = customselect.value
            if content == "enable":
                settingContents["antiping"]["enabled"] = True
            elif content == "disable":
                settingContents["antiping"]["enabled"] = False
            elif content == "role":
                view = RoleSelect(ctx.author.id)
                question = (
                    "What roles do you want to use for antiping? (e.g. `@Don't ping`)"
                )

                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )
                await ctx.send(embed=embed, view=view)
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
                question = "What roles do you want to use as a bypass role? (e.g. `@Antiping Bypass`)"
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)

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
                return await invis_embed(
                    ctx,
                    "You have not selected one of the options. Please run this command again.",
                )
        elif category == "staff_management":
            question = "What do you want to do with staff management?"
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
            embed = discord.Embed(
                title="<:EditIcon:1042550862834323597> Change Configuration",
                description=f"<:ArrowRight:1035003246445596774> {question}",
                color=0x2A2D31,
            )

            await ctx.send(embed=embed, view=customselect)
            await customselect.wait()
            content = customselect.value
            if content == "enable":
                settingContents["staff_management"]["enabled"] = True
            elif content == "disable":
                settingContents["staff_management"]["enabled"] = False
            elif content == "channel":
                view = ChannelSelect(ctx.author.id, limit=1)
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> What channel would you want to use for Staff Management (e.g. LOA Requests)",
                    color=0x2A2D31,
                )
                await ctx.send(embed=embed, view=view)
                await view.wait()
                settingContents["staff_management"]["channel"] = (
                    view.value[0].id if view.value else None
                )
            elif content == "staff_role":
                view = RoleSelect(ctx.author.id)
                question = (
                    "What roles do you want to use as staff roles? (e.g. `@Staff`)"
                )
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)
                await view.wait()
                settingContents["staff_management"]["role"] = (
                    [role.id for role in view.value]
                    if [role.id for role in view.value]
                    else []
                )

            elif content == "management_role":
                view = RoleSelect(ctx.author.id)
                question = "What roles do you want to use as management roles? (e.g. `@Management`)"
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)
                await view.wait()
                settingContents["staff_management"]["management_role"] = (
                    [role.id for role in view.value]
                    if [role.id for role in view.value]
                    else []
                )
            elif content == "loa_role":
                view = RoleSelect(ctx.author.id)
                question = "What roles do you want to use as a LOA role? (e.g. `@LOA`)"
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)
                await view.wait()
                settingContents["staff_management"]["loa_role"] = (
                    [role.id for role in view.value]
                    if [role.id for role in view.value]
                    else []
                )
            elif content == "ra_role":
                view = RoleSelect(ctx.author.id)
                question = "What roles do you want to use as a RA role? (e.g. `@RA`)"
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)
                await view.wait()
                settingContents["staff_management"]["ra_role"] = (
                    [role.id for role in view.value]
                    if [role.id for role in view.value]
                    else []
                )
            elif content == "privacy_mode":
                view = EnableDisableMenu(ctx.author.id)
                question = "Do you want to enable Privacy Mode? This will anonymize the person who denies/accepts/voids a LoA/RA."
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )
                await ctx.send(embed=embed, view=view)
                await view.wait()
                if view.value == True:
                    settingContents["staff_management"]["privacy_mode"] = True
                elif view.value == False:
                    settingContents["customisation"]["privacy_mode"] = False
            else:
                return await invis_embed(
                    ctx,
                    "You have not selected one of the options. Please run this command again.",
                )
        elif category == "punishments":
            question = "What do you want to do with punishments?"
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
            embed = discord.Embed(
                title="<:EditIcon:1042550862834323597> Change Configuration",
                description=f"<:ArrowRight:1035003246445596774> What would you like to change in the Punishments module?",
                color=0x2A2D31,
            )
            await ctx.send(embed=embed, view=customselect)
            await customselect.wait()
            content = customselect.value
            if content == "enable":
                settingContents["punishments"]["enabled"] = True
            elif content == "disable":
                settingContents["punishments"]["enabled"] = False
            elif content == "channel":
                view = ChannelSelect(ctx.author.id, limit=1)
                question = "What channel do you want to use for punishments? (e.g. `#punishments`)"
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)
                await view.wait()
                settingContents["punishments"]["channel"] = (
                    view.value[0].id if view.value else None
                )
            elif content == "ban_channel":
                view = ChannelSelect(ctx.author.id, limit=1)
                question = "What channel do you want to use for bans? (e.g. `#bans`)"
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)
                await view.wait()
                settingContents["customisation"]["ban_channel"] = (
                    view.value[0].id if view.value else None
                )
            elif content == "kick_channel":
                view = ChannelSelect(ctx.author.id, limit=1)
                question = "What channel do you want to use for kicks? (e.g. `#kicks`)"
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)
                await view.wait()
                settingContents["customisation"]["kick_channel"] = (
                    view.value[0].id if view.value else None
                )
            elif content == "bolo_channel":
                view = ChannelSelect(ctx.author.id, limit=1)
                question = "What channel do you want to use for BOLOs? (e.g. `#bolos`)"
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)
                await view.wait()
                settingContents["customisation"]["bolo_channel"] = (
                    view.value[0].id if view.value else None
                )
            else:
                return await invis_embed(
                    ctx,
                    "You have not selected one of the options. Please run this command again.",
                )
        elif category == "moderation_sync":
            question = "What do you want to do with Game Sync?"
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
            embed = discord.Embed(
                title="<:EditIcon:1042550862834323597> Change Configuration",
                description=f"<:ArrowRight:1035003246445596774> What would you like to change in the Game Sync module?",
                color=0x2A2D31,
            )
            await ctx.send(embed=embed, view=customselect)
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
                question = 'What channel do you want to use for Game Sync? (e.g. `#command-logs`)\n*This channel is where the "Command Usage" embeds are sent.*'
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)
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
                question = 'What channel do you want to use for Game Sync? (e.g. `#kick-ban-logs`)\n*This channel is where the "Player Kicked" embeds are sent.*'
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)
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
            question = "What do you want to do with shift management?"
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

            embed = discord.Embed(
                title="<:EditIcon:1042550862834323597> Change Configuration",
                description=f"<:ArrowRight:1035003246445596774> {question}",
                color=0x2A2D31,
            )

            await ctx.send(embed=embed, view=customselect)
            await customselect.wait()
            content = customselect.value
            if content == "enable":
                settingContents["shift_management"]["enabled"] = True
            elif content == "disable":
                settingContents["shift_management"]["enabled"] = False
            elif content == "quota":
                content = (
                    await request_response(
                        bot, ctx, "What would you like the quota to be? (s/m/h/d)"
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
                    return await invis_embed(
                        ctx,
                        "We could not translate your time. Remember to end it with s/m/h/d.",
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
                question = "What do you want to use a Nickname Prefix? (e.g. `𝗦𝘁𝗮𝗳𝗳 |`)"
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)
                await view.wait()
                settingContents["shift_management"][
                    "nickname"
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

                question = "What do you want the Maximum Staff limit to be?"
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)
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
                    question = "What do you want the maximum amount of staff allowed online to be? (e.g. 5)"
                    embed = discord.Embed(
                        title="<:EditIcon:1042550862834323597> Change Configuration",
                        description=f"<:ArrowRight:1035003246445596774> {question}",
                        color=0x2A2D31,
                    )

                    await ctx.send(embed=embed, view=view)
                    await view.wait()
                    try:
                        int(view.modal.max_staff.value)
                    except (ValueError, TypeError):
                        return await invis_embed(
                            ctx,
                            "That is not a valid number to set as a Maximum Staff Limit. Please try again by rerunning this command.",
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
                question = "What channel do you want to use for shift management? (e.g. shift logons)"
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)
                await view.wait()
                settingContents["shift_management"]["channel"] = (
                    view.value[0].id if view.value else None
                )
            elif content == "role":
                view = RoleSelect(ctx.author.id)
                question = (
                    "What roles do you want to use as a On-Duty role? (e.g. `@On-Duty`)"
                )
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)
                await view.wait()
                settingContents["shift_management"]["role"] = (
                    [role.id for role in view.value]
                    if [role.id for role in view.value]
                    else []
                )
            else:
                return await invis_embed(
                    ctx,
                    "Please pick one of the options. `enable`, `disable`, `channel`. Please run this command again with correct parameters.",
                )
        elif category == "shift_types":
            question = "What do you want to do with shift types?"

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

            embed = discord.Embed(
                title="<:EditIcon:1042550862834323597> Change Configuration",
                description=f"<:ArrowRight:1035003246445596774> {question}",
                color=0x2A2D31,
            )

            await ctx.send(embed=embed, view=customselect)

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
                    title="<:Clock:1035308064305332224> Shift Types",
                    description=f"<:ArrowRight:1035003246445596774> Here is the Shift Types configuration for **{ctx.guild.name}**:",
                    color=0x2A2D31,
                )

                embed.add_field(
                    name="<:QMark:1035308059532202104> Basic Configuration",
                    value=f"<:ArrowRightW:1035023450592514048> **Enabled:** {shift_types.get('enabled')}",
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
                        name=f"<:Pause:1035308061679689859> {type.get('name')}",
                        value=f"<:ArrowRightW:1035023450592514048> **Name:** {type.get('name')}\n<:ArrowRightW:1035023450592514048> **Default:** {type.get('default')}\n<:ArrowRightW:1035023450592514048> **Role:** {roles}\n<:ArrowRightW:1035023450592514048> **Channel:** {channel}\n<:ArrowRightW:1035023450592514048> **Nickname Prefix:** {type.get('nickname') if type.get('nickname') else 'None'}",
                        inline=False,
                    )

                if len(embed.fields) == 1:
                    embed.add_field(
                        name="<:Pause:1035308061679689859> Shift Types",
                        value=f"<:ArrowRight:1035003246445596774> No shift types have been added.",
                        inline=False,
                    )

                await ctx.send(embed=embed)
                return
            elif customselect.value == "manage":
                shift_types = settingContents.get("shift_types")
                if shift_types is None:
                    shift_types = {"enabled": False, "types": []}

                embed = discord.Embed(
                    title="<:Clock:1035308064305332224> Shift Types",
                    description=f"<:ArrowRight:1035003246445596774> Here is the Shift Types configuration for **{ctx.guild.name}**:",
                    color=0x2A2D31,
                )

                embed.add_field(
                    name="<:QMark:1035308059532202104> Basic Configuration",
                    value=f"<:ArrowRightW:1035023450592514048> **Enabled:** {shift_types.get('enabled')}",
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
                        name=f"<:Pause:1035308061679689859> {type.get('name')}",
                        value=f"<:ArrowRightW:1035023450592514048> **Name:** {type.get('name')}\n<:ArrowRightW:1035023450592514048> **Default:** {type.get('default')}\n<:ArrowRightW:1035023450592514048> **Role:** {roles}\n<:ArrowRightW:1035023450592514048> **Channel:** {channel}\n<:ArrowRightW:1035023450592514048> **Nickname Prefix:** {type.get('nickname') if type.get('nickname') else 'None'}",
                        inline=False,
                    )

                if len(embed.fields) == 1:
                    embed.add_field(
                        name="<:Pause:1035308061679689859> Shift Types",
                        value=f"<:ArrowRight:1035003246445596774> No shift types have been added.",
                        inline=False,
                    )

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

                await ctx.send(embed=embed, view=view)
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
                        return await invis_embed(
                            ctx,
                            "You cannot have more than 25 shift types due to discord limitations. Please remove some shift types before adding more.",
                        )

                    embed = discord.Embed(
                        title="<:Clock:1035308064305332224> Shift Types",
                        description=f"<:ArrowRight:1035003246445596774> Select the button below to begin the creation of a Shift Type.",
                        color=0x2A2D31,
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

                    await ctx.send(embed=embed, view=view)
                    timeout = await view.wait()
                    if timeout:
                        return

                    if view.modal.name.value:
                        name = view.modal.name.value
                    else:
                        return

                    embed = discord.Embed(
                        title="<:Clock:1035308064305332224> Shift Types",
                        description="<:ArrowRight:1035003246445596774> Would you like this Shift Type to be default?",
                        color=0x2A2D31,
                    )

                    view = YesNoColourMenu(ctx.author.id)

                    await ctx.send(embed=embed, view=view)
                    timeout = await view.wait()
                    if timeout:
                        return

                    if view.value is True:
                        default = True
                    else:
                        default = False

                    embed = discord.Embed(
                        title="<:Clock:1035308064305332224> Shift Types",
                        description="<:ArrowRight:1035003246445596774> Do you want a role to be assigned when someone is on shift for this type?",
                        color=0x2A2D31,
                    )

                    view = YesNoColourMenu(ctx.author.id)

                    await ctx.send(embed=embed, view=view)
                    timeout = await view.wait()
                    if timeout:
                        return

                    if view.value is True:
                        embed = discord.Embed(
                            title="<:Clock:1035308064305332224> Shift Types",
                            description="<:ArrowRight:1035003246445596774> What roles do you want to be assigned when someone is on shift for this type?",
                            color=0x2A2D31,
                        )

                        view = RoleSelect(ctx.author.id)

                        await ctx.send(embed=embed, view=view)
                        timeout = await view.wait()
                        if timeout:
                            return

                        roles = view.value
                    else:
                        roles = []

                    embed = discord.Embed(
                        title="<:Clock:1035308064305332224> Shift Types",
                        description="<:ArrowRight:1035003246445596774> Do you want a Nickname Prefix to be added to someone's name when they are on-duty for this shift type?",
                        color=0x2A2D31,
                    )

                    view = YesNoColourMenu(ctx.author.id)

                    await ctx.send(embed=embed, view=view)
                    timeout = await view.wait()
                    if timeout:
                        return

                    if view.value is True:
                        embed = discord.Embed(
                            title="<:Clock:1035308064305332224> Shift Types",
                            description="<:ArrowRight:1035003246445596774> What do you want to be the Nickname Prefix?",
                            color=0x2A2D31,
                        )

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

                        await ctx.send(embed=embed, view=view)
                        timeout = await view.wait()
                        if timeout:
                            return

                        nickname = view.modal.nickname.value
                    else:
                        nickname = None

                    embed = discord.Embed(
                        title="<:Clock:1035308064305332224> Shift Types",
                        description="<:ArrowRight:1035003246445596774> Do you want this type to send to a different channel than the currently configured one?",
                        color=0x2A2D31,
                    )

                    view = YesNoColourMenu(ctx.author.id)

                    await ctx.send(embed=embed, view=view)
                    timeout = await view.wait()
                    if timeout:
                        return

                    if view.value is True:
                        embed = discord.Embed(
                            title="<:Clock:1035308064305332224> Shift Types",
                            description="<:ArrowRight:1035003246445596774> What channel do you want to this type to send to?",
                            color=0x2A2D31,
                        )

                        view = ChannelSelect(ctx.author.id, limit=1)

                        await ctx.send(embed=embed, view=view)
                        timeout = await view.wait()
                        if timeout:
                            return

                        channel = view.value
                        if channel:
                            channel = channel[0].id
                        else:
                            return await ctx.send(
                                embed=create_invis_embed(
                                    "You did not select a channel. Please try again."
                                )
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
                    embed = discord.Embed(
                        title="<:Clock:1035308064305332224> Shift Types",
                        description=f"<:ArrowRight:1035003246445596774> Select the Shift Type you want to edit.",
                        color=0x2A2D31,
                    )
                    if len(shift_types.get("types")) == 0:
                        return await invis_embed(
                            ctx,
                            "There are no shift types to edit. Please create a shift type before attempting to delete one.",
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

                    await ctx.send(embed=embed, view=view)
                    timeout = await view.wait()
                    if timeout:
                        return

                    shift_type = [
                        type
                        for type in shift_types.get("types")
                        if type.get("id") == int(view.value)
                    ]
                    if len(shift_type) == 0:
                        return await invis_embed(ctx, "That shift type does not exist.")

                    shift_type = shift_type[0]

                    embed = discord.Embed(
                        title="<:Clock:1035308064305332224> Shift Types",
                        description=f"<:ArrowRight:1035003246445596774> What would you like to edit about this shift type?",
                        color=0x2A2D31,
                    )

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
                        name=f"<:Pause:1035308061679689859> {type.get('name')}",
                        value=f"<:ArrowRightW:1035023450592514048> **Name:** {type.get('name')}\n<:ArrowRightW:1035023450592514048> **Default:** {type.get('default')}\n<:ArrowRightW:1035023450592514048> **Role:** {roles}\n<:ArrowRightW:1035023450592514048> **Channel:** {channel}\n<:ArrowRightW:1035023450592514048> **Nickname Prefix:** {type.get('nickname') if type.get('nickname') else 'None'}",
                        inline=False,
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

                    await ctx.send(embed=embed, view=view)
                    timeout = await view.wait()
                    if timeout:
                        return

                    if view.value == "name":
                        embed = discord.Embed(
                            title="<:Clock:1035308064305332224> Shift Types",
                            description=f"<:ArrowRight:1035003246445596774> What would you like to change the name of this shift type to?",
                            color=0x2A2D31,
                        )

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

                        await ctx.send(embed=embed, view=view)
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
                        embed = discord.Embed(
                            title="<:Clock:1035308064305332224> Shift Types",
                            description=f"<:ArrowRight:1035003246445596774> Would you like this Shift Type to be default?",
                            color=0x2A2D31,
                        )

                        view = YesNoColourMenu(ctx.author.id)

                        await ctx.send(embed=embed, view=view)
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
                        embed = discord.Embed(
                            title="<:Clock:1035308064305332224> Shift Types",
                            description=f"<:ArrowRight:1035003246445596774> Do you want a role to be assigned when someone is on shift for this type?",
                            color=0x2A2D31,
                        )

                        view = YesNoColourMenu(ctx.author.id)

                        await ctx.send(embed=embed, view=view)
                        timeout = await view.wait()

                        if timeout:
                            return

                        if view.value is True:
                            embed = discord.Embed(
                                title="<:Clock:1035308064305332224> Shift Types",
                                description="<:ArrowRight:1035003246445596774> What roles do you want to be assigned when someone is on shift for this type?",
                                color=0x2A2D31,
                            )

                            view = RoleSelect(ctx.author.id)

                            await ctx.send(embed=embed, view=view)
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
                        embed = discord.Embed(
                            title="<:Clock:1035308064305332224> Shift Types",
                            description=f"<:ArrowRight:1035003246445596774> Do you want this shift type to be sent to a different channel than the one configured in Shift Management?",
                            color=0x2A2D31,
                        )

                        view = YesNoColourMenu(ctx.author.id)

                        await ctx.send(embed=embed, view=view)
                        timeout = await view.wait()

                        if timeout:
                            return

                        if view.value is True:
                            embed = discord.Embed(
                                title="<:Clock:1035308064305332224> Shift Types",
                                description="<:ArrowRight:1035003246445596774> What channel do you want logs of this shift type to be sent to?",
                                color=0x2A2D31,
                            )

                            view = ChannelSelect(ctx.author.id, limit=1)

                            await ctx.send(embed=embed, view=view)
                            timeout = await view.wait()

                            if timeout:
                                return

                            channel = view.value
                            if channel:
                                channel = channel[0].id
                            else:
                                return await ctx.send(
                                    embed=create_invis_embed(
                                        "You did not select a channel. Please try again."
                                    )
                                )
                        else:
                            channel = None

                        shift_type["channel"] = channel
                        settingContents["_id"] = (
                            settingContents.get("_id") or ctx.guild.id
                        )
                        await bot.settings.update_by_id(settingContents)
                    elif view.value == "nickname":
                        embed = discord.Embed(
                            title="<:Clock:1035308064305332224> Shift Types",
                            description=f"<:ArrowRight:1035003246445596774> What nickname prefix do you want for people on duty of this type?",
                            color=0x2A2D31,
                        )

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

                        await ctx.send(embed=embed, view=view)
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
                        return await invis_embed(
                            ctx, "There are no shift types to delete."
                        )

                    embed = discord.Embed(
                        title="<:Clock:1035308064305332224> Shift Types",
                        description=f"<:ArrowRight:1035003246445596774> Select the Shift Type you want to delete.",
                        color=0x2A2D31,
                    )

                    if len(shift_types.get("types")) == 0:
                        return await invis_embed(
                            ctx, "There are no shift types to delete."
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

                    await ctx.send(embed=embed, view=view)
                    timeout = await view.wait()
                    if timeout:
                        return

                    shift_type = [
                        type
                        for type in shift_types.get("types")
                        if type.get("id") == int(view.value)
                    ]
                    if len(shift_type) == 0:
                        return await invis_embed(ctx, "That shift type does not exist.")

                    shift_type = shift_type[0]

                    shift_types.get("types").remove(shift_type)
                    settingContents["_id"] = settingContents.get("_id") or ctx.guild.id
                    await bot.settings.update_by_id(settingContents)

        elif category == "customisation":
            # color, prefix, brand name, thumbnail url, footer text, ban channel
            question = "What would you like to customize?"
            customselect = CustomSelectMenu(
                ctx.author.id,
                [
                    discord.SelectOption(
                        label="Color",
                        description="Change the color of the embeds",
                        value="color",
                    ),
                    discord.SelectOption(
                        label="Prefix",
                        description="Change the prefix of the bot",
                        value="prefix",
                    ),
                    discord.SelectOption(
                        label="Brand Name",
                        description="Used in some embeds to identify the server",
                        value="brand_name",
                    ),
                    discord.SelectOption(
                        label="Thumbnail URL",
                        description="Used in some embeds for customisation",
                        value="thumbnail_url",
                    ),
                    discord.SelectOption(
                        label="Footer Text",
                        description="Used in some embeds for customisation",
                        value="footer_text",
                    ),
                ],
            )
            embed = discord.Embed(
                title="<:EditIcon:1042550862834323597> Change Configuration",
                description=f"<:ArrowRight:1035003246445596774> {question}",
                color=0x2A2D31,
            )

            await ctx.send(embed=embed, view=customselect)
            await customselect.wait()
            content = customselect.value
            if content == "color":
                content = (
                    await request_response(
                        bot,
                        ctx,
                        "What color do you want to use for the server? (e.g. `#00FF00`)",
                    )
                ).content
                convertedContent = await discord.ext.commands.ColourConverter().convert(
                    ctx, content
                )
                settingContents["customisation"]["color"] = convertedContent.value
            elif content == "prefix":
                content = (
                    await request_response(
                        bot,
                        ctx,
                        "What prefix do you want to use for the server? (e.g. `!`)",
                    )
                ).content
                settingContents["customisation"]["prefix"] = content
            elif content == "brand_name":
                content = (
                    await request_response(
                        bot,
                        ctx,
                        "What brand name do you want to use for the server? (e.g. `My Server`)",
                    )
                ).content
                settingContents["customisation"]["brand_name"] = content
            elif content == "thumbnail_url":
                content = (
                    await request_response(
                        bot,
                        ctx,
                        "What thumbnail url do you want to use for the server? (e.g. `https://i.imgur.com/...`)",
                    )
                ).content
                settingContents["customisation"]["thumbnail_url"] = content
            elif content == "footer_text":
                content = (
                    await request_response(
                        bot,
                        ctx,
                        "What footer text do you want to use for the server? (e.g. `My Server`)",
                    )
                ).content
                settingContents["customisation"]["footer_text"] = content
            elif content == "server_code":
                content = (
                    await request_response(
                        bot, ctx, "What server code do you use for your ER:LC server?"
                    )
                ).content
                settingContents["customisation"]["server_code"] = content
            elif content == "compact_mode":
                view = EnableDisableMenu(ctx.author.id)
                await invis_embed(
                    ctx,
                    "Do you want to enable Compact Mode? This will disable most of the emojis used within the bot.",
                    view=view,
                )
                await view.wait()
                if view.value == True:
                    settingContents["customisation"]["compact_mode"] = True
                elif view.value == False:
                    settingContents["customisation"]["compact_mode"] = False

            else:
                return await invis_embed(
                    ctx,
                    "You did not pick any of the options. Please run this command again with correct parameters.",
                )
        elif category == "privacy":
            privacyConfig = await bot.privacy.find_by_id(ctx.guild.id)
            if privacyConfig is None:
                privacyConfig = {"_id": ctx.guild.id, "global_warnings": True}
            question = "What would you like to change?"
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
            embed = discord.Embed(
                title="<:EditIcon:1042550862834323597> Change Configuration",
                description=f"<:ArrowRight:1035003246445596774> {question}",
                color=0x2A2D31,
            )

            await ctx.send(embed=embed, view=customselect)
            await customselect.wait()
            content = customselect.value
            if content == "enable_global_warnings":
                privacyConfig["global_warnings"] = True
            if content == "disable_global_warnings":
                privacyConfig["global_warnings"] = False
            await bot.privacy.upsert(privacyConfig)
            successEmbed = discord.Embed(
                title="<:CheckIcon:1035018951043842088> Success!",
                description="<:ArrowRight:1035003246445596774> Your configuration has been changed.",
                color=0x71C15F,
            )

            return await ctx.send(embed=successEmbed)
        elif category == "game_logging":
            if not settingContents.get("game_logging"):
                settingContents["game_logging"] = {
                    "message": {"enabled": False, "channel": None},
                    "sts": {"enabled": False, "channel": None},
                    "priority": {"enabled": False, "channel": None},
                }

            question = "What would you like to manage?"
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
            embed = discord.Embed(
                title="<:EditIcon:1042550862834323597> Change Configuration",
                description=f"<:ArrowRight:1035003246445596774> {question}",
                color=0x2A2D31,
            )

            await ctx.send(embed=embed, view=customselect)
            await customselect.wait()
            content = customselect.value

            if not content:
                return

            if content == "message":
                question = "What would you like to change?"

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
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=customselect)
                timeout = await customselect.wait()
                if timeout:
                    return

                content = customselect.value
                if content == "enable_message_logging":
                    settingContents["game_logging"]["message"]["enabled"] = True
                elif content == "disable_message_logging":
                    settingContents["game_logging"]["message"]["enabled"] = False
                elif content == "set_message_logging_channel":
                    embed = discord.Embed(
                        title="<:EditIcon:1042550862834323597> Change Configuration",
                        description=f"<:ArrowRight:1035003246445596774> What channel do you want to set for message logging?",
                        color=0x2A2D31,
                    )

                    view = ChannelSelect(ctx.author.id, limit=1)

                    await ctx.send(embed=embed, view=view)

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
                question = "What would you like to change?"

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

                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=customselect)
                timeout = await customselect.wait()
                if timeout:
                    return

                content = customselect.value
                if content == "enable_sts_logging":
                    settingContents["game_logging"]["sts"]["enabled"] = True
                elif content == "disable_sts_logging":
                    settingContents["game_logging"]["sts"]["enabled"] = False
                elif content == "set_sts_logging_channel":
                    embed = discord.Embed(
                        title="<:EditIcon:1042550862834323597> Change Configuration",
                        description=f"<:ArrowRight:1035003246445596774> What channel do you want to set for STS logging?",
                        color=0x2A2D31,
                    )

                    view = ChannelSelect(ctx.author.id, limit=1)

                    await ctx.send(embed=embed, view=view)
                    timeout = await view.wait()
                    if timeout:
                        return

                    if not view.value:
                        return

                    channel = view.value
                    settingContents["game_logging"]["sts"]["channel"] = (
                        channel[0].id if channel else None
                    )
            elif content == "priority":
                question = "What would you like to change?"

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

                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=customselect)
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
                        description=f"<:ArrowRight:1035003246445596774> What channel do you want to set for Priority logging?",
                        color=0x2A2D31,
                    )

                    view = ChannelSelect(ctx.author.id, limit=1)

                    await ctx.send(embed=embed, view=view)
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

            successEmbed = discord.Embed(
                title="<:CheckIcon:1035018951043842088> Success!",
                description="<:ArrowRight:1035003246445596774> Your configuration has been changed.",
                color=0x71C15F,
            )

            await bot.settings.update_by_id(settingContents)
            return await ctx.send(embed=successEmbed)
        elif category == "security":
            question = "What do you want to do with Game Security?"
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
            embed = discord.Embed(
                title="<:EditIcon:1042550862834323597> Change Configuration",
                description=f"<:ArrowRight:1035003246445596774> {question}",
                color=0x2A2D31,
            )

            await ctx.send(embed=embed, view=customselect)

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
                question = "What roles do you want to be mentioned when abuse is detected? (e.g. `@Leadership`)"

                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)
                await view.wait()
                settingContents["game_security"]["role"] = (
                    [role.id for role in view.value]
                    if [role.id for role in view.value]
                    else []
                )
            elif content == "webhook_channel":
                view = ChannelSelect(ctx.author.id, limit=1)
                question = (
                    "What channel are ER:LC webhooks sent to? (e.g. `#kicks-and-bans`)"
                )
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)
                await view.wait()
                settingContents["game_security"]["webhook_channel"] = (
                    view.value[0].id if view.value else None
                )
            elif content == "channel":
                view = ChannelSelect(ctx.author.id, limit=1)
                question = "What channel do you want Anti-Abuse reports to go to? (e.g. `#admin-abuse`)"
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Change Configuration",
                    description=f"<:ArrowRight:1035003246445596774> {question}",
                    color=0x2A2D31,
                )

                await ctx.send(embed=embed, view=view)
                await view.wait()
                settingContents["game_security"]["channel"] = (
                    view.value[0].id if view.value else None
                )
            else:
                return await invis_embed(
                    ctx,
                    "Please pick one of the options. `enable`, `disable`, `role`, `channel`, `webhook_channel`. Please run this command again with correct parameters.",
                )
        else:
            return await invis_embed(
                ctx,
                "You did not pick any of the options. Please run this command again with correct parameters.",
            )

        if category != "shift_types":
            await bot.settings.update_by_id(settingContents)

        successEmbed = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Success!",
            description="<:ArrowRight:1035003246445596774> Your configuration has been changed.",
            color=0x71C15F,
        )
        await ctx.send(embed=successEmbed)

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
                emoji="<:Setup:1035006520817090640>",
                description="All features of the bot, contains all of the features below",
            ),
            discord.SelectOption(
                label="Staff Management",
                value="staff_management",
                emoji="<:staff:1035308057007230976>",
                description="Inactivity Notices, and managing staff members",
            ),
            discord.SelectOption(
                label="Punishments",
                value="punishments",
                emoji="<:MalletWhite:1035258530422341672>",
                description="Punishing community members for rule infractions",
            ),
            discord.SelectOption(
                label="Shift Management",
                value="shift_management",
                emoji="<:Search:1035353785184288788>",
                description="Shifts (duty manage, duty admin), and where logs should go",
            ),
        ]

        welcome = discord.Embed(
            title="<:Setup:1035006520817090640> Which features would you like enabled?",
            color=0xFFFFFF,
        )
        welcome.description = "Toggle which modules of ERM you would like to use.\n\n<:ArrowRight:1035003246445596774> All *(default)*\n*All features of the bot*\n\n<:ArrowRight:1035003246445596774> Staff Management\n*Manage your staff members, LoAs, and more!*\n\n<:ArrowRight:1035003246445596774> Punishments\n*Roblox moderation, staff logging systems, and more!*\n\n<:ArrowRight:1035003246445596774> Shift Management\n*Manage staff member's shifts, view who's in game!*"

        view = MultiSelectMenu(ctx.author.id, options)

        await ctx.send(embed=welcome, view=view)

        await view.wait()
        if not view.value:
            return await invis_embed(
                ctx,
                "<:Setup:1035006520817090640> You have took too long to respond. Please try again.",
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
            question = "What channel do you want to use for staff management?"
            view = ChannelSelect(ctx.author.id, limit=1)
            await invis_embed(ctx, question, view=view)
            await view.wait()
            convertedContent = view.value
            settingContents["staff_management"]["channel"] = (
                convertedContent[0].id if convertedContent else None
            )

            question = "What role would you like to use for your staff role? (e.g. @Staff)\n*You can select multiple roles.*"
            view = RoleSelect(ctx.author.id)
            await invis_embed(ctx, question, view=view)
            await view.wait()
            convertedContent = view.value
            settingContents["staff_management"]["role"] = (
                [role.id for role in convertedContent] if convertedContent else []
            )

            question = "What role would you like to use for your Management role? (e.g. @Management)\n*You can select multiple roles.*"
            view = RoleSelect(ctx.author.id)
            await invis_embed(ctx, question, view=view)
            await view.wait()
            convertedContent = view.value
            settingContents["staff_management"]["management_role"] = (
                [role.id for role in convertedContent] if convertedContent else []
            )

            view = YesNoMenu(ctx.author.id)
            question = "Do you want a role to be assigned to staff members when they are on LoA (Leave of Absence)?"
            embed = discord.Embed(
                color=0x2A2D31,
                description=f"<:ArrowRight:1035003246445596774> {question}",
            )

            await ctx.send(embed=embed, view=view)
            await view.wait()
            if view.value is not None:
                if view.value:
                    question = "What role(s) would you like to be given?\n*You can select multiple roles.*"
                    view = RoleSelect(ctx.author.id)
                    await invis_embed(ctx, question, view=view)
                    await view.wait()
                    convertedContent = view.value
                    settingContents["staff_management"]["loa_role"] = (
                        [role.id for role in convertedContent]
                        if convertedContent
                        else []
                    )

            view = YesNoMenu(ctx.author.id)
            question = "Do you want a role to be assigned to staff members when they are on RA (Reduced Activity)?"
            embed = discord.Embed(
                color=0x2A2D31,
                description=f"<:ArrowRight:1035003246445596774> {question}",
            )

            await ctx.send(embed=embed, view=view)
            await view.wait()
            if view.value is not None:
                if view.value:
                    question = "What role(s) would you like to be given?\n*You can select multiple roles.*"
                    view = RoleSelect(ctx.author.id)
                    await invis_embed(ctx, question, view=view)
                    await view.wait()
                    convertedContent = view.value
                    settingContents["staff_management"]["ra_role"] = (
                        [role.id for role in convertedContent]
                        if convertedContent
                        else []
                    )
        if settingContents["punishments"]["enabled"]:
            question = "What channel do you want to use for punishments?"
            view = ChannelSelect(ctx.author.id, limit=1)
            await invis_embed(ctx, question, view=view)
            await view.wait()
            convertedContent = view.value
            settingContents["punishments"]["channel"] = (
                convertedContent[0].id if convertedContent else None
            )
        if settingContents["shift_management"]["enabled"]:
            question = "What channel do you want to use for shift management? (e.g. shift signups, etc.)"
            view = ChannelSelect(ctx.author.id, limit=1)
            await invis_embed(ctx, question, view=view)
            await view.wait()
            convertedContent = view.value
            settingContents["shift_management"]["channel"] = (
                convertedContent[0].id if convertedContent else None
            )

            view = YesNoMenu(ctx.author.id)
            question = "Do you want a role to be assigned to staff members when they are in game?"
            embed = discord.Embed(
                color=0x2A2D31,
                description=f"<:ArrowRight:1035003246445596774> {question}",
            )

            await ctx.send(embed=embed, view=view)
            await view.wait()
            if view.value is not None:
                if view.value:
                    question = "What role(s) would you like to be given?\n*You can select multiple roles.*"
                    view = RoleSelect(ctx.author.id, limit=1)
                    await invis_embed(ctx, question, view=view)
                    await view.wait()
                    convertedContent = view.value
                    settingContents["shift_management"]["role"] = (
                        [role.id for role in convertedContent]
                        if convertedContent
                        else []
                    )

            view = YesNoMenu(ctx.author.id)
            question = "Do you have a weekly quota? (e.g. `2h`, `90m`, `7h`)"
            embed = discord.Embed(
                color=0x2A2D31,
                description=f"<:ArrowRight:1035003246445596774> {question}",
            )

            await ctx.send(embed=embed, view=view)
            await view.wait()
            if view.value is not None:
                if view.value:
                    content = (
                        await request_response(
                            bot, ctx, "What would you like the quota to be? (s/m/h/d)"
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
                            total_seconds = (
                                int(content.removesuffix("d")) * 60 * 60 * 24
                            )
                    else:
                        return await invis_embed(
                            ctx,
                            "We could not translate your time. Remember to end it with s/m/h/d.",
                        )

                    settingContents["shift_management"]["quota"] = total_seconds

            view = YesNoMenu(ctx.author.id)
            question = "Do you have multiple shift types?"
            embed = discord.Embed(
                color=0x2A2D31,
                description=f"<:ArrowRight:1035003246445596774> {question}",
            )

            await ctx.send(embed=embed, view=view)
            await view.wait()
            if view.value is not None:
                if view.value is True:

                    async def func():
                        shift_types = settingContents.get("shift_types")
                        if shift_types is None:
                            shift_types = {"enabled": False, "types": []}

                        embed = discord.Embed(
                            title="<:Clock:1035308064305332224> Shift Types",
                            description=f"<:ArrowRight:1035003246445596774> Here is the Shift Types configuration for **{ctx.guild.name}**:",
                            color=0x2A2D31,
                        )

                        embed.add_field(
                            name="<:QMark:1035308059532202104> Basic Configuration",
                            value=f"<:ArrowRightW:1035023450592514048> **Enabled:** {shift_types.get('enabled')}",
                            inline=False,
                        )

                        for type in shift_types.get("types"):
                            roles = type.get("role")
                            if type.get("role") is None or len(type.get("role")) == 0:
                                roles = "None"
                            else:
                                roles = ", ".join(
                                    [f"<@&{role}>" for role in type.get("role")]
                                )

                            if type.get("channel") is None:
                                channel = "None"
                            else:
                                channel = f"<#{type.get('channel')}>"

                            embed.add_field(
                                name=f"<:Pause:1035308061679689859> {type.get('name')}",
                                value=f"<:ArrowRightW:1035023450592514048> **Name:** {type.get('name')}\n<:ArrowRightW:1035023450592514048> **Default:** {type.get('default')}\n<:ArrowRightW:1035023450592514048> **Role:** {roles}\n<:ArrowRightW:1035023450592514048> **Channel:** {channel}\n<:ArrowRightW:1035023450592514048> **Nickname Prefix:** {type.get('nickname') if type.get('nickname') else 'None'}",
                                inline=False,
                            )

                        if len(embed.fields) == 1:
                            embed.add_field(
                                name="<:Pause:1035308061679689859> Shift Types",
                                value=f"<:ArrowRight:1035003246445596774> No shift types have been added.",
                                inline=False,
                            )

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
                                    label="Finish",
                                    description="Finish the configuration",
                                    value="finish",
                                    emoji="<:CheckIcon:1035018951043842088>",
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

                        await ctx.send(embed=embed, view=view)
                        await view.wait()
                        if view.value == "enable":
                            shift_types["enabled"] = True
                            settingContents["shift_types"] = shift_types
                            settingContents["_id"] = (
                                settingContents.get("_id") or ctx.guild.id
                            )
                            await bot.settings.update_by_id(settingContents)
                            await func()
                        elif view.value == "disable":
                            shift_types["enabled"] = False
                            settingContents["shift_types"] = shift_types
                            settingContents["_id"] = (
                                settingContents.get("_id") or ctx.guild.id
                            )

                            await bot.settings.update_by_id(settingContents)
                            await func()
                        elif view.value == "add":
                            if len(shift_types.get("types")) >= 24:
                                return await invis_embed(
                                    ctx,
                                    "You cannot have more than 24 shift types due to Discord limitations. Please remove some shift types before adding more.",
                                )

                            embed = discord.Embed(
                                title="<:Clock:1035308064305332224> Shift Types",
                                description=f"<:ArrowRight:1035003246445596774> Select the button below to begin the creation of a Shift Type.",
                                color=0x2A2D31,
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

                            await ctx.send(embed=embed, view=view)
                            timeout = await view.wait()
                            if timeout:
                                return

                            if view.modal.name.value:
                                name = view.modal.name.value
                            else:
                                return

                            embed = discord.Embed(
                                title="<:Clock:1035308064305332224> Shift Types",
                                description="<:ArrowRight:1035003246445596774> Would you like this Shift Type to be default?",
                                color=0x2A2D31,
                            )

                            view = YesNoColourMenu(ctx.author.id)

                            await ctx.send(embed=embed, view=view)
                            timeout = await view.wait()
                            if timeout:
                                return

                            if view.value is True:
                                default = True
                            else:
                                default = False

                            embed = discord.Embed(
                                title="<:Clock:1035308064305332224> Shift Types",
                                description="<:ArrowRight:1035003246445596774> Do you want a role to be assigned when someone is on shift for this type?",
                                color=0x2A2D31,
                            )

                            view = YesNoColourMenu(ctx.author.id)

                            await ctx.send(embed=embed, view=view)
                            timeout = await view.wait()
                            if timeout:
                                return

                            if view.value is True:
                                embed = discord.Embed(
                                    title="<:Clock:1035308064305332224> Shift Types",
                                    description="<:ArrowRight:1035003246445596774> What roles do you want to be assigned when someone is on shift for this type?",
                                    color=0x2A2D31,
                                )

                                view = RoleSelect(ctx.author.id)

                                await ctx.send(embed=embed, view=view)
                                timeout = await view.wait()
                                if timeout:
                                    return

                                roles = view.value
                            else:
                                roles = []

                            embed = discord.Embed(
                                title="<:Clock:1035308064305332224> Shift Types",
                                description="<:ArrowRight:1035003246445596774> Do you want a Nickname Prefix to be added to someone's name when they are on-duty for this shift type?",
                                color=0x2A2D31,
                            )

                            view = YesNoColourMenu(ctx.author.id)

                            await ctx.send(embed=embed, view=view)
                            timeout = await view.wait()
                            if timeout:
                                return

                            if view.value is True:
                                embed = discord.Embed(
                                    title="<:Clock:1035308064305332224> Shift Types",
                                    description="<:ArrowRight:1035003246445596774> What do you want to be the Nickname Prefix?",
                                    color=0x2A2D31,
                                )

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

                                await ctx.send(embed=embed, view=view)
                                timeout = await view.wait()
                                if timeout:
                                    return

                                nickname = view.modal.nickname.value
                            else:
                                nickname = None

                            embed = discord.Embed(
                                title="<:Clock:1035308064305332224> Shift Types",
                                description="<:ArrowRight:1035003246445596774> Do you want this type to send to a different channel than the currently configured one?",
                                color=0x2A2D31,
                            )

                            view = YesNoColourMenu(ctx.author.id)

                            await ctx.send(embed=embed, view=view)
                            timeout = await view.wait()
                            if timeout:
                                return

                            if view.value is True:
                                embed = discord.Embed(
                                    title="<:Clock:1035308064305332224> Shift Types",
                                    description="<:ArrowRight:1035003246445596774> What channel do you want to this type to send to?",
                                    color=0x2A2D31,
                                )

                                view = ChannelSelect(ctx.author.id, limit=1)

                                await ctx.send(embed=embed, view=view)
                                timeout = await view.wait()
                                if timeout:
                                    return

                                channel = view.value
                                if channel:
                                    channel = channel[0]
                                else:
                                    return await ctx.send(
                                        embed=create_invis_embed(
                                            "You must select a channel for successful shift type creation. Please try again."
                                        )
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
                            settingContents["_id"] = (
                                settingContents.get("_id") or ctx.guild.id
                            )

                            await bot.settings.update_by_id(settingContents)
                            await func()
                        elif view.value == "edit":
                            embed = discord.Embed(
                                title="<:Clock:1035308064305332224> Shift Types",
                                description=f"<:ArrowRight:1035003246445596774> Select the Shift Type you want to edit.",
                                color=0x2A2D31,
                            )
                            if len(shift_types.get("types")) == 0:
                                return await invis_embed(
                                    ctx,
                                    "There are no shift types to edit. Please create a shift type before attempting to delete one.",
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

                            await ctx.send(embed=embed, view=view)
                            timeout = await view.wait()
                            if timeout:
                                return

                            shift_type = [
                                type
                                for type in shift_types.get("types")
                                if type.get("id") == int(view.value)
                            ]
                            if len(shift_type) == 0:
                                return await invis_embed(
                                    ctx, "That shift type does not exist."
                                )

                            shift_type = shift_type[0]

                            embed = discord.Embed(
                                title="<:Clock:1035308064305332224> Shift Types",
                                description=f"<:ArrowRight:1035003246445596774> What would you like to edit about this shift type?",
                                color=0x2A2D31,
                            )

                            roles = type.get("role")
                            if type.get("role") is None or len(type.get("role")) == 0:
                                roles = "None"
                            else:
                                roles = ", ".join(
                                    [f"<@&{role}>" for role in type.get("role")]
                                )

                            if type.get("channel") is None:
                                channel = "None"
                            else:
                                channel = f"<#{type.get('channel')}>"

                            embed.add_field(
                                name=f"<:Pause:1035308061679689859> {type.get('name')}",
                                value=f"<:ArrowRightW:1035023450592514048> **Name:** {type.get('name')}\n<:ArrowRightW:1035023450592514048> **Default:** {type.get('default')}\n<:ArrowRightW:1035023450592514048> **Role:** {roles}\n<:ArrowRightW:1035023450592514048> **Channel:** {channel}\n<:ArrowRightW:1035023450592514048> **Nickname Prefix:** {type.get('nickname') if type.get('nickname') else 'None'}",
                                inline=False,
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

                            await ctx.send(embed=embed, view=view)
                            timeout = await view.wait()
                            if timeout:
                                return

                            if view.value == "name":
                                embed = discord.Embed(
                                    title="<:Clock:1035308064305332224> Shift Types",
                                    description=f"<:ArrowRight:1035003246445596774> What would you like to change the name of this shift type to?",
                                    color=0x2A2D31,
                                )

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

                                await ctx.send(embed=embed, view=view)
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
                                embed = discord.Embed(
                                    title="<:Clock:1035308064305332224> Shift Types",
                                    description=f"<:ArrowRight:1035003246445596774> Would you like this Shift Type to be default?",
                                    color=0x2A2D31,
                                )

                                view = YesNoColourMenu(ctx.author.id)

                                await ctx.send(embed=embed, view=view)
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
                                embed = discord.Embed(
                                    title="<:Clock:1035308064305332224> Shift Types",
                                    description=f"<:ArrowRight:1035003246445596774> Do you want a role to be assigned when someone is on shift for this type?",
                                    color=0x2A2D31,
                                )

                                view = YesNoColourMenu(ctx.author.id)

                                await ctx.send(embed=embed, view=view)
                                timeout = await view.wait()

                                if timeout:
                                    return

                                if view.value is True:
                                    embed = discord.Embed(
                                        title="<:Clock:1035308064305332224> Shift Types",
                                        description="<:ArrowRight:1035003246445596774> What roles do you want to be assigned when someone is on shift for this type?",
                                        color=0x2A2D31,
                                    )

                                    view = RoleSelect(ctx.author.id)

                                    await ctx.send(embed=embed, view=view)
                                    timeout = await view.wait()

                                    if timeout:
                                        return

                                    roles = (
                                        [role.id for role in view.value]
                                        if [role.id for role in view.value]
                                        else None
                                    )
                                else:
                                    roles = []

                                shift_type["role"] = roles
                                settingContents["_id"] = (
                                    settingContents.get("_id") or ctx.guild.id
                                )
                                await bot.settings.update_by_id(settingContents)
                            elif view.value == "channel":
                                embed = discord.Embed(
                                    title="<:Clock:1035308064305332224> Shift Types",
                                    description=f"<:ArrowRight:1035003246445596774> Do you want this shift type to be sent to a different channel than the one configured in Shift Management?",
                                    color=0x2A2D31,
                                )

                                view = YesNoColourMenu(ctx.author.id)

                                await ctx.send(embed=embed, view=view)
                                timeout = await view.wait()

                                if timeout:
                                    return

                                if view.value is True:
                                    embed = discord.Embed(
                                        title="<:Clock:1035308064305332224> Shift Types",
                                        description="<:ArrowRight:1035003246445596774> What channel do you want logs of this shift type to be sent to?",
                                        color=0x2A2D31,
                                    )

                                    view = ChannelSelect(ctx.author.id, limit=1)

                                    await ctx.send(embed=embed, view=view)
                                    timeout = await view.wait()

                                    if timeout:
                                        return

                                    channel = view.value
                                    if channel:
                                        channel = channel[0].id
                                    else:
                                        return await ctx.send(
                                            embed=create_invis_embed(
                                                "You did not select a channel. Please try again."
                                            )
                                        )
                                else:
                                    channel = None

                                shift_type["channel"] = channel
                                settingContents["_id"] = (
                                    settingContents.get("_id") or ctx.guild.id
                                )
                                await bot.settings.update_by_id(settingContents)
                            elif view.value == "nickname":
                                embed = discord.Embed(
                                    title="<:Clock:1035308064305332224> Shift Types",
                                    description=f"<:ArrowRight:1035003246445596774> What nickname prefix do you want for people on duty of this type?",
                                    color=0x2A2D31,
                                )

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

                                await ctx.send(embed=embed, view=view)
                                timeout = await view.wait()
                                if timeout:
                                    await func()
                                    return

                                if view.modal.nickname.value:
                                    nickname = view.modal.nickname.value
                                else:
                                    await func()

                                shift_type["nickname"] = nickname

                                settingContents["_id"] = (
                                    settingContents.get("_id") or ctx.guild.id
                                )
                                await bot.settings.update_by_id(settingContents)
                                await func()
                            await func()
                        elif view.value == "delete":
                            if len(shift_types.get("types")) == 0:
                                return await invis_embed(
                                    ctx, "There are no shift types to delete."
                                )

                            embed = discord.Embed(
                                title="<:Clock:1035308064305332224> Shift Types",
                                description=f"<:ArrowRight:1035003246445596774> Select the Shift Type you want to delete.",
                                color=0x2A2D31,
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

                            await ctx.send(embed=embed, view=view)
                            timeout = await view.wait()
                            if timeout:
                                return

                            shift_type = [
                                type
                                for type in shift_types.get("types")
                                if type.get("id") == int(view.value)
                            ]
                            if len(shift_type) == 0:
                                return await invis_embed(
                                    ctx, "That shift type does not exist."
                                )

                            shift_type = shift_type[0]

                            shift_types.get("types").remove(shift_type)
                            settingContents["_id"] = (
                                settingContents.get("_id") or ctx.guild.id
                            )

                            await bot.settings.update_by_id(settingContents)
                            await func()

                    await func()

        privacyDefault = {"_id": ctx.guild.id, "global_warnings": True}

        view = YesNoMenu(ctx.author.id)
        question = "Do you want your server's warnings to be able to be queried across the bot? (e.g. `globalsearch`)"
        embed = discord.Embed(
            color=0x2A2D31, description=f"<:ArrowRight:1035003246445596774> {question}"
        )

        await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.value is not None:
            if view.value == True:
                privacyDefault["global_warnings"] = True
            else:
                privacyDefault["global_warnings"] = False

        if not await bot.privacy.find_by_id(ctx.guild.id):
            await bot.privacy.insert(privacyDefault)
        else:
            await bot.privacy.update_by_id(privacyDefault)

        settingContents["_id"] = ctx.guild.id
        if not await bot.settings.find_by_id(ctx.guild.id):
            await bot.settings.insert(settingContents)
        else:
            await bot.settings.update_by_id(settingContents)

        embed = discord.Embed(
            title="<:CheckIcon:1035018951043842088> Setup Complete",
            color=0x71C15F,
            description="<:ArrowRight:1035003246445596774>ERM has been set up and is ready for use!\n*If you want to change these settings, run the command again!*",
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Configuration(bot))
