import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils.utils import invis_embed


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="ping",
        description="Shows information of the bot, such as uptime and latency",
        extras={"category": "Utility"},
    )
    async def ping(self, ctx):
        uptime = f"<t:{int(self.bot.start_time)}>"

        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="<:SettingIcon:1035353776460152892> Service Status",
            color=0x2E3136,
            description="*This will go over the current status of ERM.*",
        )
        embed.add_field(
            name="<:UptimeIconW:1035269010272550932> Latency", value=f"{latency}ms"
        )

        embed.add_field(
            name="<:MessageIcon:1035321236793860116> Uptime", value=f"{uptime}"
        )

        data = await self.bot.db.command("ping")

        status: str | None = None

        if list(data.keys())[0] == "ok":
            status = "Connected"
        else:
            status = "Not Connected"
        embed.add_field(
            name="<:Search:1035353785184288788> Database", value=f"{status}"
        )
        if ctx.guild:
            embed.set_footer(
                text=f"Shard {str(ctx.guild.shard_id)} | Guild ID: {str(ctx.guild.id)}"
            )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="support",
        aliases=["support-server"],
        description="Information about the ERM Support Server",
        extras={"category": "Utility"},
    )
    async def support_server(self, ctx):
        # using an embed
        embed = discord.Embed(
            title="<:support:1035269007655321680> Support Server",
            description="<:ArrowRight:1035003246445596774> Join the [**Support Server**](https://discord.gg/5pMmJEYazQ) to get help with the bot!",
            color=0x2E3136,
        )
        embed.set_footer(
            text=f"Shard {str(ctx.guild.shard_id)} | Guild ID: {str(ctx.guild.id)}"
        )

        await ctx.send(embed=embed)

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
            return await invis_embed(
                ctx,
                "The server has not been set up yet. Please run `/setup` to set up the server.",
            )

        if command == None:
            embed = discord.Embed(
                title="<:support:1035269007655321680> Command List | Emergency Response Management",
                color=0x2E3136,
            )

            categories = []
            commands = []

            category_to_emoji = {
                "Punishments": "<:MalletWhite:1035258530422341672>",
                "Staff Management": "<:staff:1035308057007230976>",
                "Configuration": "<:FlagIcon:1035258525955395664>",
                "Miscellaneous": "<:QMark:1035308059532202104>",
                "Search": "<:Search:1035353785184288788>",
                "Utility": "<:SettingIcon:1035353776460152892>",
                "Shift Management": "<:Clock:1035308064305332224>",
                "Reminders": "<:Resume:1035269012445216858>",
                "Activity Management": "<:Pause:1035308061679689859>",
                "Custom Commands": "<:QMark:1035308059532202104>",
                "Verification": "<:SettingIcon:1035353776460152892>",
                "Game Logging": "<:SConductTitle:1053359821308567592>",
                "Moderation Sync": "<:SyncIcon:1071821068551073892>",
                "Privacy": "<:Privacy:1081047358810365993>",
            }

            for command in bot.walk_commands():
                try:
                    command.category = command.extras["category"]
                except:
                    command.category = "Miscellaneous"

                if command.extras.get("legacy") is True:
                    continue

                if isinstance(command, discord.ext.commands.core.Command):
                    if command.hidden:
                        continue
                    if command.parent is not None:
                        if (
                            isinstance(command.parent, discord.ext.commands.core.Group)
                            and not command.parent.name == "jishaku"
                            and not command.parent.name == "jsk"
                        ):
                            if command.parent.name not in ["voice"]:
                                command.full_name = (
                                    f"{command.parent.name} {command.name}"
                                )
                            else:
                                continue
                        else:
                            continue
                    else:
                        command.full_name = f"{command.name}"

                if isinstance(command, discord.ext.commands.core.Group):
                    continue

                if command.category not in categories:
                    categories.append(command.category)
                    commands.append(command)
                else:
                    commands.append(command)

            for category in categories:
                full_category = category_to_emoji[category] + " " + category
                print(commands)
                string = "\n".join(
                    [
                        f"<:ArrowRight:1035003246445596774> `/{command}` | *{command.description}*"
                        for command in commands
                        if command.category == category
                    ]
                )

                logging.info(len(string))

                if len(string) < 1024:
                    embed.add_field(name=full_category, value=string, inline=False)

                else:
                    splitted_lines = string.splitlines()

                    for i in range(0, len(splitted_lines), 5):
                        has_full_category = False
                        for field in embed.fields:
                            if field.name == full_category:
                                has_full_category = True

                        if not has_full_category:
                            embed.add_field(
                                name=full_category,
                                value="\n".join(splitted_lines[i : i + 5]),
                                inline=False,
                            )
                        else:
                            embed.add_field(
                                name="\u200b",
                                value="\n".join(splitted_lines[i : i + 5]),
                                inline=False,
                            )
            embed.set_footer(
                text="Use /help <command> for specific help on a command.",
                icon_url="https://cdn.discordapp.com/emojis/1035258528149033090.webp?size=60&quality=lossless",
            )

            await ctx.send(embed=embed)
        else:
            command = bot.get_command(command)
            if command is None:
                return await invis_embed(ctx, "That command does not exist.")

            embed = discord.Embed(
                title="<:SettingIcon:1035353776460152892> Command Information | {}".format(
                    command.name
                ),
                description=f"<:ArrowRight:1035003246445596774> {command.description.split('[')[0]}",
                color=0x2E3136,
            )

            embed.set_footer(
                text="More help with a command can be asked in our support server."
            )

            embed.add_field(
                name="<:QMark:1035308059532202104> Usage",
                value="<:ArrowRight:1035003246445596774> `{}`".format(command.usage),
                inline=False,
            )

            if command.aliases:
                embed.add_field(
                    name="<:Search:1035353785184288788> Aliases",
                    value="<:ArrowRight:1035003246445596774> `{}`".format(
                        ", ".join(command.aliases)
                    ),
                    inline=False,
                )

            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Utility(bot))
