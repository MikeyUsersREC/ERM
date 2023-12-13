import typing

import aiohttp
import discord
import roblox
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context


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

       # # print(commands)
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
       # # print(current)
       # # print(Data)
        return [
            app_commands.Choice(name=item, value=item)
            for item in ["Warning", "Kick", "Ban", "BOLO"]
        ]
    else:
       # # print(Data)
        commands = []
        for command in Data["types"]:
            if current not in ["", " "]:
               # # print(current)
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

       # # print(commands)
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
    async def fallback_completion():
        choices = []
        async for search in bot.punishments.db.find({}).limit(10):
            if search['Username'] in [choice.name for choice in choices]:
                continue
            choices.append(
                discord.app_commands.Choice(name=search['Username'], value=search["Username"])
            )
        return choices

    if current in [None, ""]:
        return await fallback_completion()

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f'https://www.roblox.com/search/users/results?keyword={current}&maxRows=12&startIndex=0') as resp:
                data_json = await resp.json()
                if data_json:
                    print(data_json)
                    if isinstance(data_json.get('UserSearchResults'), list):
                        items = [item for item in data_json['UserSearchResults'][:25]]
                    else:
                        items = []
                else:
                    items = []
    choices = []
    for item in items:
        choices.append(
            discord.app_commands.Choice(name=item["Name"], value=item["Name"])
        )
    return choices
