import discord
from discord.ext import commands
from discord.ext.commands import Context
import typing
from discord import app_commands
import aiohttp


async def command_autocomplete(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    bot = (await Context.from_interaction(interaction)).bot
    Data = await bot.custom_commands.find_by_id(interaction.guild.id)
    if Data is None:
        return [
            discord.app_commands.Choice(name="No custom commands found", value="NULL")
        ]
    else:
        commands = []
        for command in Data["commands"]:
            if current not in ["", " "]:
                if (
                    command["name"].startswith(current)
                    or current in command["name"]
                    or command["name"].endswith(current)
                ):
                    commands.append(command["name"])
            else:
                commands.append(command["name"])
        if len(commands) == 0:
            return [
                discord.app_commands.Choice(
                    name="No custom commands found", value="NULL"
                )
            ]

        print(commands)
        commandList = []
        for command in commands:
            if command not in [""]:
                commandList.append(
                    discord.app_commands.Choice(name=command, value=command)
                )
            else:
                cmd = None
                for c in Data["commands"]:
                    if c["name"].lower() == command.lower():
                        cmd = c
                commandList.append(
                    discord.app_commands.Choice(
                        name=cmd["message"]["content"][:20].replace(" ", "").lower(),
                        value=cmd["name"],
                    )
                )
        return commandList


async def punishment_autocomplete(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    bot = (await Context.from_interaction(interaction)).bot
    Data = await bot.punishment_types.find_by_id(interaction.guild.id)
    if Data is None:
        print(current)
        print(Data)
        return [
            app_commands.Choice(name=item, value=item)
            for item in ["Warning", "Kick", "Ban", "BOLO"]
        ]
    else:
        print(Data)
        commands = []
        for command in Data["types"]:
            if current not in ["", " "]:
                print(current)
                if isinstance(command, str):
                    if (
                        command.lower().startswith(current.lower())
                        or current.lower() in command.lower()
                        or command.lower().endswith(current.lower())
                    ):
                        commands.append(command)
                elif isinstance(command, dict):
                    if (
                        command["name"].lower().startswith(current)
                        or current.lower() in command["name"].lower()
                        or command["name"].lower().endswith(current.lower())
                        or current in command["name"].lower()
                    ):
                        commands.append(command["name"])
            else:
                if isinstance(command, str):
                    commands.append(command)
                elif isinstance(command, dict):
                    commands.append(command["name"])

        if len(commands) == 0:
            return [
                discord.app_commands.Choice(
                    name="No punishment types found", value="NULL"
                )
            ]

        print(commands)
        commandList = []
        for command in commands:
            if command not in [""]:
                commandList.append(
                    discord.app_commands.Choice(name=command, value=command)
                )
        return commandList


async def user_autocomplete(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    bot = (await Context.from_interaction(interaction)).bot

    if current in [None, ""]:
        searches = bot.warnings.db.find().sort([("$natural", -1)]).limit(10)
        choices = []
        async for search in searches:
            choices.append(
                discord.app_commands.Choice(name=search["_id"], value=search["_id"])
            )
        return choices
    else:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://users.roblox.com/v1/users/search?keyword={current}&limit=25"
            ) as resp:
                print(resp.status)
                if resp.status == 200:
                    data = await resp.json()
                    if "data" in data.keys():
                        choices = []
                        for user in data["data"]:
                            choices.append(
                                discord.app_commands.Choice(
                                    name=user["name"], value=user["name"]
                                )
                            )
                        return choices
                else:
                    searches = bot.warnings.db.find(
                        {"_id": {"$regex": f"{current.lower()}"}}
                    )

                    choices = []
                    index = 0
                    async for search in searches:
                        if index >= 25:
                            break
                        else:
                            index += 1
                            choices.append(
                                discord.app_commands.Choice(
                                    name=search["_id"], value=search["_id"]
                                )
                            )
                    if not choices:
                        searches = (
                            bot.warnings.db.find().sort([("$natural", -1)]).limit(25)
                        )
                        async for search in searches:
                            choices.append(
                                discord.app_commands.Choice(
                                    name=search["_id"], value=search["_id"]
                                )
                            )
                    return choices
