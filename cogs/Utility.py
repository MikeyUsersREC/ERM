import logging

import discord
from discord import app_commands
from discord.app_commands import AppCommandGroup
from discord.ext import commands

from menus import LinkView, CustomSelectMenu, MultiPaginatorMenu
from utils.utils import invis_embed, failure_embed


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="ping",
        description="Shows information of the bot, such as uptime and latency",
        extras={"category": "Utility"},
    )
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        await ctx.reply(
            f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** all is good! My ping is **{latency}ms**!"
        )

    @commands.hybrid_command(
        name="support",
        aliases=["support-server"],
        description="Information about the ERM Support Server",
        extras={"category": "Utility"},
    )
    async def support_server(self, ctx):
        # using an embed
        # [**Support Server**](https://discord.gg/5pMmJEYazQ)
        embed = discord.Embed(
            color=0xED4348,
            description="<:ERMModify:1111100050718867577> **PRO TIP:** Most of your questions can be answered on our [documentation](https://docs.ermbot.xyz)!",
        )

        await ctx.reply(
            content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** need some help? **Join the support server by clicking the button below!**",
            embed=embed,
            view=LinkView(label="Support Server", url="https://discord.gg/5pMmJEYazQ"),
        )

    @commands.hybrid_command(
        name="help",
        aliases=["h", "commands", "cmds", "cmd", "command"],
        description="Get a list of commands.",
        extras={"category": "Utility"},
        usage="<command>",
        with_app_command=True,
    )
    @app_commands.describe(
        command="Would you like more information on a command? If so, please enter the command name."
    )
    async def help(self, ctx, *, command=None):
        bot = self.bot
        configItem = await bot.settings.find_by_id(ctx.guild.id)
        if configItem is None:
            return await failure_embed(
                ctx,
                "the server has not been set up yet. Please run `/setup` to set up the server.",
            )

        if command == None:
            embed = discord.Embed(
                title="<:support:1035269007655321680> Command List | Emergency Response Management",
                color=0xED4348,
            )

            categories = []
            commands = []

            category_to_emoji = {
                "Punishments": "<:ERMPunish:1111095942075138158> ",
                "Staff Management": "<:ERMStaff:1058104030280286278>",
                "Configuration": "<:ERMConfig:1113208218521456835>",
                "Miscellaneous": "<:ERMMisc:1113215605424795648>",
                "Search": "<:ERMSearch:1113208889626865684>",
                "Utility": "<:ERMUtility:1113208636320272414>",
                "Shift Management": "<:Clock:1035308064305332224>",
                "Reminders": "<:ERMReminder:1113211641736208506>",
                "Activity Management": "<:ERMActivity:1113209176664064060>",
                "Custom Commands": "<:QMark:1035308059532202104>",
                "Verification": "<:ERMVerify:1113210530719600741>",
                "Game Logging": "<:ERMLog:1113210855891423302>",
                "Game Sync": "<:ERMSync:1113209904979771494>",
                "Privacy": "<:ERMSecurity:1113209656370802879>",
            }

            temps = {}
            temp_cmds = []
            for cmd in bot.walk_commands():
                if cmd is None:
                    continue

                if cmd.extras.get("legacy") is True:
                    continue

                if isinstance(cmd, discord.ext.commands.core.Group):
                    for c in cmd.commands:
                        if c is None:
                            continue
                        if (
                            isinstance(c.parent, discord.ext.commands.core.Group)
                            and not c.parent.name == "jishaku"
                            and not c.parent.name == "jsk"
                        ):
                            if c.parent.name not in ["voice"]:
                                c.full_name = f"{c.parent.name} {c.name}"
                                temps[c] = None
                            else:
                                continue
                        else:
                            continue
                    continue

                if cmd.parent is not None:
                    if (
                        isinstance(cmd.parent, discord.ext.commands.core.Group)
                        and not cmd.parent.name == "jishaku"
                        and not cmd.parent.name == "jsk"
                    ):
                        if cmd.parent.name not in ["voice"]:
                            cmd.full_name = f"{cmd.parent.name} {cmd.name}"

                        else:
                            continue
                    else:
                        continue
                else:
                    cmd.full_name = f"{cmd.name}"
                temps[cmd] = None
            print(temps)
            temp_apps = []

            for command in await bot.tree.fetch_commands():
                # print(repr(command))
                # if command.name == "activity":
                #     print(dir(command))

                if command.options:
                    for a in command.options:
                        if f"{command.name} {a.name}" in [
                            cd.qualified_name for cd in temps
                        ]:
                            temps[
                                list(
                                    filter(
                                        lambda x: x is not None,
                                        [
                                            cd
                                            if cd.qualified_name
                                            == f"{command.name} {a.name}"
                                            else None
                                            for cd in temps
                                        ],
                                    )
                                )[0]
                            ] = a
                else:
                    if command.name in [cd.qualified_name for cd in temps]:
                        temps[
                            list(
                                filter(
                                    lambda x: x is not None,
                                    [
                                        cd
                                        if cd.qualified_name == command.name
                                        else None
                                        for cd in temps
                                    ],
                                )
                            )[0]
                        ] = command

                # if isinstance(command, discord.app_commands.AppCommand):
                #
                #     # if command.parent is not None:
                #     #     if (
                #     #         isinstance(command.parent, discord.ext.commands.core.Group)
                #     #         and not command.parent.name == "jishaku"
                #     #         and not command.parent.name == "jsk"
                #     #     ):
                #     #         if command.parent.name not in ["voice"]:
                #     #             command.full_name = (
                #     #                 f"{command.parent.name} {command.name}"
                #     #             )
                #     #         else:
                #     #             continue
                #     #     else:
                #     #         continue
                #     # else:
                #     #     command.full_name = f"{command.name}"
                #

                # if isinstance(command, discord.ext.commands.core.Group):
                #     continue
                #
                # if (command.extras.get("category", "Miscellaneous")) not in categories:
                #     categories.append(command.category)
                #     commands.append(command)
                # else:
                #     commands.append(command)
            #
            # for i in temp_cmds.copy():
            #     if i is None:
            #         temp_cmds.remove(i)
            #
            # for i in temp_apps.copy():
            #     if i is None:
            #         temp_apps.remove(i)

            # return await ctx.reply(temps)
            for k, v in temps.copy().items():
                if v is None:
                    del temps[k]

            for command, app_command in temps.items():
                if (command.extras.get("category", "Miscellaneous")) not in categories:
                    categories.append(command.extras.get("category", "Miscellaneous"))
                    # commands.append(command)

            category_embeds = {}

            for category in categories:
                embed = discord.Embed(
                    color=0xED4348, title="<:ERMHelp:1111318459305951262> Command Help"
                )
                full_category = category_to_emoji[category] + " " + category
                print(commands)
                string = "\n".join(
                    [
                        f"<:ERMList:1111099396990435428> {app.mention}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{app.description}"
                        if isinstance(app, AppCommandGroup)
                        else f"<:ERMList:1111099396990435428> </{app.name}:{app.id}>\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>{app.description}"
                        for command, app in temps.items()
                        if (command.extras.get("category", "Miscellaneous")) == category
                    ]
                )
                embed.description = string

                logging.info(len(string))
                embed.set_author(
                    name=ctx.author.name, icon_url=ctx.author.display_avatar.url
                )
                embed.set_footer(
                    text="Use the dropdown below to select a module to view the commands of."
                )
                category_embeds[category] = embed

            await ctx.reply(
                f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** select an option.",
                view=MultiPaginatorMenu(
                    ctx.author.id,
                    [
                        discord.SelectOption(
                            label="Punishments",
                            description="Commands related to punishments.",
                            emoji="<:ERMPunish:1111095942075138158>",
                            value="Punishments",
                        ),
                        discord.SelectOption(
                            label="Staff Management",
                            description="Commands related to staff management.",
                            emoji="<:ERMStaff:1058104030280286278>",
                            value="Staff Management",
                        ),
                        discord.SelectOption(
                            label="Configuration",
                            description="Commands related to configuration.",
                            emoji="<:ERMConfig:1113208218521456835>",
                            value="Configuration",
                        ),
                        discord.SelectOption(
                            label="Miscellaneous",
                            description="Commands that don't fit into any other category.",
                            emoji="<:ERMMisc:1113215605424795648>",
                            value="Miscellaneous",
                        ),
                        discord.SelectOption(
                            label="Search",
                            description="Commands related to ROBLOX searching.",
                            emoji="<:ERMSearch:1113208889626865684>",
                            value="Search",
                        ),
                        discord.SelectOption(
                            label="Utility",
                            description="Commands that are useful",
                            emoji="<:ERMUtility:1113208636320272414>",
                            value="Utility",
                        ),
                        discord.SelectOption(
                            label="Shift Management",
                            description="Commands related to shift management.",
                            emoji="<:ERMSchedule:1111091306089939054>",
                            value="Shift Management",
                        ),
                        discord.SelectOption(
                            label="Reminders",
                            description="Commands related to reminders.",
                            emoji="<:ERMReminder:1113211641736208506>",
                            value="Reminders",
                        ),
                        discord.SelectOption(
                            label="Activity Management",
                            description="Commands related to activity management.",
                            emoji="<:ERMActivity:1113209176664064060>",
                            value="Activity Management",
                        ),
                        discord.SelectOption(
                            label="Custom Commands",
                            description="Commands related to custom commands.",
                            emoji="<:ERMCustomCommands:1113210178448396348>",
                            value="Custom Commands",
                        ),
                        discord.SelectOption(
                            label="Verification",
                            description="Commands related to verification.",
                            emoji="<:ERMVerify:1113210530719600741>",
                            value="Verification",
                        ),
                        discord.SelectOption(
                            label="Game Logging",
                            description="Commands related to game logging.",
                            emoji="<:ERMLog:1113210855891423302>",
                            value="Game Logging",
                        ),
                        discord.SelectOption(
                            label="Game Sync",
                            description="Commands related to game syncing.",
                            emoji="<:ERMSync:1113209904979771494>",
                            value="Game Sync",
                        ),
                        discord.SelectOption(
                            label="Privacy",
                            description="Commands related to privacy.",
                            emoji="<:ERMSecurity:1113209656370802879>",
                            value="Privacy",
                        ),
                    ],
                    category_embeds,
                ),
            )

        else:
            command = bot.get_command(command)
            if command is None:
                return await failure_embed(ctx, "that command does not exist.")

            embed = discord.Embed(
                title="<:ERMConfig:1113208218521456835> Command Information | {}".format(
                    command.name
                ),
                description=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> {command.description.split('[')[0]}",
                color=0xED4348,
            )

            embed.set_footer(
                text="More help with a command can be asked in our support server."
            )

            embed.add_field(
                name="<:ERMList:1111099396990435428> Usage",
                value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912> `{}`".format(
                    command.usage
                ),
                inline=False,
            )

            if command.aliases:
                embed.add_field(
                    name="<:ERMList:1111099396990435428> Aliases",
                    value="<:Space:1100877460289101954><:ERMArrow:1111091707841359912> `{}`".format(
                        ", ".join(command.aliases)
                    ),
                    inline=False,
                )
            embed.set_author(
                name=ctx.author.name,
                icon_url=ctx.author.display_avatar.url,
            )
            embed.set_thumbnail(url=ctx.guild.icon.url)
            await ctx.reply(
                content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name}**, looks like you want to know about a specific command. You'll find helpful information below.",
                embed=embed,
            )

    @commands.hybrid_command(
        name="about",
        aliases=["info"],
        description="Information about ERM",
        extras={"category": "Utility"},
    )
    async def about(self, ctx):
        # using an embed
        # [**Support Server**](https://discord.gg/5pMmJEYazQ)
        embed = discord.Embed(
            title="<:erm:1067182038685323274> About ERM",
            color=0xED4348,
        )
        embed.add_field(
            name=f"<:ERMList:1111099396990435428> What is ERM?",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>ERM is a Discord bot that is used for things like Shift Logging, Punishment Logging, Leave of Absences, and much more. We integrate many next-gen Discord features to our bot and are commonly known as the most feature-rich bot of our market.",
            inline=False,
        )
        embed.add_field(
            name=f"<:ERMList:1111099396990435428> Links",
            value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>[**Website**](https://ermbot.xyz)\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>[**Support Server**](https://discord.gg/erm-systems-987798554972143728)\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>[**Invite**](https://discord.com/oauth2/authorize?client_id=978662093408591912&scope=bot%20applications.commands&permissions=8)\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>[**Documentation**](https://docs.ermbot.xyz)",
            inline=False,
        )
        embed.set_author(
            name=ctx.author.name,
            icon_url=ctx.author.display_avatar.url,
        )
        await ctx.reply(
            content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** looks like you're interested in ERM, let me run down what we are.",
            embed=embed,
            view=LinkView(
                label="Feature List",
                url="https://docs.ermbot.xyz/overview/our-features",
            ),
        )


async def setup(bot):
    await bot.add_cog(Utility(bot))
