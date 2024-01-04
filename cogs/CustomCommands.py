import discord
from discord import app_commands
from discord.ext import commands

from erm import is_management
from utils.constants import BLANK_COLOR, GREEN_COLOR
from utils.utils import generator
from menus import (
    ChannelSelect,
    CustomModalView,
    CustomSelectMenu,
    EmbedCustomisation,
    MessageCustomisation,
    RemoveCustomCommand,
    YesNoColourMenu, CustomCommandOptionSelect, CustomCommandModification,
)
from utils.autocompletes import command_autocomplete
from utils.utils import (
    interpret_content,
    interpret_embed,
    invis_embed,
    request_response,
)


class CustomCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.hybrid_group(name="custom")
    @is_management()
    async def custom(self, ctx):
        pass

    @custom.command(
        name="manage",
        description="Manage your custom commands.",
        extras={"category": "Custom Commands"},
    )
    @is_management()
    async def custom_manage(self, ctx):
        bot = self.bot
        Data = await bot.custom_commands.find_by_id(ctx.guild.id)

        if Data is None:
            Data = {"_id": ctx.guild.id, "commands": []}

        embed = discord.Embed(
            title="Custom Commands",
            color=BLANK_COLOR
        )
        embed.set_author(
            name=ctx.guild.name,
            icon_url=ctx.guild.icon.url if ctx.guild.icon else ''
        )
        embed.set_thumbnail(
            url=ctx.guild.icon.url if ctx.guild.icon else ''
        )

        for item in Data["commands"]:
            embed.add_field(
                name=f"{item['name']}",
                value=f"<:replytop:1138257149705863209> **Name:** {item['name']}\n"
                      f"<:replymiddle:1138257195121791046> **Command ID:** `{item['id']}`\n"
                      f"<:replybottom:1138257250448855090> **Creator:** {'<@{}>'.format(item.get('author') if item.get('author') is not None else 'Unknown')}",
                inline=False,
            )
        if len(embed.fields) == 0:
            embed.add_field(
                name="No Custom Commands",
                value=f"<:replybottom:1138257250448855090> No Custom Commands were found to be associated with this server."
            )


        view = CustomCommandOptionSelect(ctx.author.id)


        new_msg = await ctx.reply(
            embed=embed,
            view=view,
        )

        timeout = await view.wait()
        if timeout:
            return

        if view.value == "create":
            name = view.modal.name.value
            data = {
                "name": name,
                "id": next(generator),
                "message": None,
                "author": ctx.author.id
            }
            view = CustomCommandModification(ctx.author.id, data)
            # timeout = await view.wait()
            # if timeout:
            #     return
            await new_msg.edit(view=view, embed=discord.Embed(
                title="Custom Commands",
                description=(
                    "**Command Information**\n"
                    f"<:replytop:1138257149705863209> **Command ID:** `{data['id']}`\n"
                    f"<:replymiddle:1138257195121791046> **Command Name:** {data['name']}\n"
                    f"<:replybottom:1138257250448855090> **Creator:** <@{data['author']}>\n"
                    f"\n**Message:**\n"
                    f"View the message below by clicking 'View Message'."
                ),
                color=BLANK_COLOR
            ))
            await view.wait()
            data = view.command_data

            for item in Data["commands"]:
                if item["name"] == name:
                    return await ctx.reply(
                        embed=discord.Embed(
                            title="Command Mismatch",
                            description="This custom command already exists.",
                            color=BLANK_COLOR
                        )
                    )

            custom_command_data = {
                "_id": ctx.guild.id,
                "commands": [
                    data
                ],
            }

            if Data:
                Data["commands"].append(
                    data
                )
            else:
                Data = custom_command_data

            await bot.custom_commands.upsert(Data)
            await new_msg.edit(
                embed=discord.Embed(
                    title="<:success:1163149118366040106> Command Created",
                    description="This custom command has been successfully created",
                    color=GREEN_COLOR
                ),
                view=None,
            )
        elif view.value == "delete":
            identifier = view.modal.name.value

            for item in Data["commands"]:
                if str(item["name"]).strip() == str(identifier).strip():
                    Data["commands"].remove(item)
                    await bot.custom_commands.upsert(Data)
                    break
            else:
                return await new_msg.edit(
                    embed=discord.Embed(
                        title="Command Mismatch",
                        description="This custom command doesn't exist.",
                        color=BLANK_COLOR
                    ),
                    view=None
                )

            return await new_msg.edit(
                embed=discord.Embed(
                    title="<:success:1163149118366040106> Deleted Command",
                    description="This custom command has been successfully deleted",
                    color=GREEN_COLOR
                ),
                view=None,
            )

    @custom.command(
        name="run",
        description="Run a custom command.",
        extras={"category": "Custom Commands", "ephemeral": True},
    )
    @app_commands.autocomplete(command=command_autocomplete)
    @is_management()
    @app_commands.describe(command="What custom command would you like to run?")
    @app_commands.describe(
        channel="Where do you want this custom command's output to go? (e.g. #general)"
    )
    async def run(self, ctx, command: str, channel: discord.TextChannel = None):
        bot = self.bot
        Data = await bot.custom_commands.find_by_id(ctx.guild.id)
        if Data is None:
            return await ctx.reply(
                embed=discord.Embed(
                    title="No Commands",
                    description="There are no custom commands in this server."
                )
            )

        is_command = False
        selected = None
        if "commands" in Data.keys():
            if isinstance(Data["commands"], list):
                for cmd in Data["commands"]:
                    if cmd["name"].lower().replace(" ", "") == command.lower().replace(
                        " ", ""
                    ):
                        is_command = True
                        selected = cmd

        if not is_command:
            return await ctx.reply(
                embed=discord.Embed(
                    title="Command Mismatch",
                    description="This custom command doesn't exist.",
                    color=BLANK_COLOR
                )
            )

        if not channel:
            if selected.get("channel") is None:
                channel = ctx.channel
            else:
                channel = (
                    discord.utils.get(ctx.guild.text_channels, id=selected["channel"])
                    if discord.utils.get(
                        ctx.guild.text_channels, id=selected["channel"]
                    )
                    is not None
                    else ctx.channel
                )
        embeds = []
        for embed in selected["message"]["embeds"]:
            embeds.append(await interpret_embed(bot, ctx, channel, embed))

        view = discord.ui.View()
        for item in selected.get('buttons', []):
            view.add_item(discord.ui.Button(
                label=item['label'],
                url=item['url'],
                row=item['row'],
                style=discord.ButtonStyle.url
            ))


        if ctx.interaction:
            if selected['message']['content'] in [None, ""] and len(selected['message']['embeds']) == 0:
                return await ctx.interaction.followup.send(
                    embed=discord.Embed(
                        title='Empty Command',
                        description='Due to Discord limitations, I am unable to send your reminder. Your message is most likely empty.',
                        color=BLANK_COLOR
                    )
                )
            await ctx.interaction.followup.send(
                embed=discord.Embed(
                    title="<:success:1163149118366040106> Command Ran",
                    description=f"I've just ran the custom command in {channel.mention}.",
                    color=GREEN_COLOR
                )
            )
            await channel.send(
                content=await interpret_content(
                    bot, ctx, channel, selected["message"]["content"]
                ),
                embeds=embeds,
                view=view,
                allowed_mentions=discord.AllowedMentions(
                    everyone=True, users=True, roles=True, replied_user=True
                )
            )
        else:
            if selected['message']['content'] in [None, ""] and len(selected['message']['embeds']) == 0:
                return await ctx.reply(
                    embed=discord.Embed(
                        title='Empty Command',
                        description='Due to Discord limitations, I am unable to send your reminder. Your message is most likely empty.',
                        color=BLANK_COLOR
                    )
                )
            await ctx.reply(
                embed=discord.Embed(
                    title="<:success:1163149118366040106> Command Ran",
                    description=f"I've just ran the custom command in {channel.mention}.",
                    color=GREEN_COLOR
                )
            )

            await channel.send(
                content=await interpret_content(
                    bot, ctx, channel, selected["message"]["content"]
                ),
                embeds=embeds,
                view=view,
                allowed_mentions=discord.AllowedMentions(
                    everyone=True, users=True, roles=True, replied_user=True
                ),
            )


async def setup(bot):
    await bot.add_cog(CustomCommands(bot))
