import discord
from discord import app_commands
from discord.ext import commands

from erm import is_management
from utils.utils import generator
from menus import (
    AddCustomCommand,
    ChannelSelect,
    CustomModalView,
    CustomSelectMenu,
    EmbedCustomisation,
    MessageCustomisation,
    RemoveCustomCommand,
    YesNoColourMenu,
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

        view = CustomSelectMenu(
            ctx.author.id,
            [
                discord.SelectOption(
                    label="Create",
                    value="create",
                    description="Create a Custom Command",
                    emoji="<:ERMAdd:1113207792854106173>",
                ),
                discord.SelectOption(
                    label="List",
                    value="list",
                    description="List all of the Custom Commands",
                    emoji="<:ERMList:1111099396990435428>",
                ),
                discord.SelectOption(
                    label="Edit",
                    value="edit",
                    description="Edit an existing Custom Command.",
                    emoji="<:ERMMisc:1113215605424795648>",
                ),
                discord.SelectOption(
                    label="Delete",
                    value="delete",
                    description="Delete an existing Custom Command",
                    emoji="<:ERMTrash:1111100349244264508>",
                ),
            ],
        )

        new_msg = await ctx.reply(
            f"<:ERMPending:1111097561588183121> **{ctx.author.name},** select an option.",
            view=view,
        )

        timeout = await view.wait()
        if timeout:
            return

        if view.value == "create":
            await new_msg.edit(content=None)
            view = AddCustomCommand(ctx.author.id)
            await new_msg.edit(view=view)
            timeout = await view.wait()
            if timeout:
                return

            await view.view.wait()
            await view.view.newView.wait()

            try:
                name = view.information["name"]

            except:
                return await ctx.reply(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this has been cancelled."
                )

            for item in Data["commands"]:
                if item["name"] == name:
                    return await ctx.reply(
                        content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this command already exists"
                    )

            embeds = []
            resultingMessage = view.view.newView.msg
            for embed in resultingMessage.embeds:
                embeds.append(embed.to_dict())

            channel_view = YesNoColourMenu(ctx.author.id)
            new_msg = await ctx.reply(
                f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** would you like this custom command to have a default channel? If this isn't selected, the custom command will be run in the same channel as the command or the channel argument specified in the command.",
                view=channel_view,
            )
            await channel_view.wait()
            channel = None
            if channel_view.value is True:
                channel_view = ChannelSelect(ctx.author.id, limit=1)
                await new_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what would you like your default channel to be?",
                    view=channel_view,
                )
                await channel_view.wait()
                if channel_view.value:
                    channel = [ch.id for ch in channel_view.value][0]

            custom_command_data = {
                "_id": ctx.guild.id,
                "commands": [
                    {
                        "name": name,
                        "id": next(generator),
                        "message": {
                            "content": resultingMessage.content,
                            "embeds": embeds,
                            "channel": channel,
                        },
                    }
                ],
            }

            if Data:
                Data["commands"].append(
                    {
                        "name": name,
                        "id": next(generator),
                        "message": {
                            "content": resultingMessage.content,
                            "embeds": embeds,
                            "channel": channel,
                        },
                    }
                )
            else:
                Data = custom_command_data

            await bot.custom_commands.upsert(Data)
            await new_msg.edit(
                content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** got it, I've saved **{name}**!",
                view=None,
            ),

        elif view.value == "edit":
            view = CustomModalView(
                ctx.author.id,
                "Edit a Custom Command",
                "Edit a Custom Command",
                [
                    (
                        "name",
                        discord.ui.TextInput(
                            placeholder="Name of the custom command",
                            label="Name of the custom command",
                            style=discord.TextStyle.short,
                        ),
                    )
                ],
            )

            await new_msg.edit(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what is the name of the custom command you would like to edit?",
                view=view,
            ),
            await view.wait()

            try:
                command = view.modal.name.value
            except:
                return await new_msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this has been cancelled.",
                    view=None,
                )

            if command.lower() not in [c["name"].lower() for c in Data["commands"]]:
                return await new_msg.edit(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this command does not exist.",
                    view=None,
                )

            view = CustomSelectMenu(
                ctx.author.id,
                [
                    discord.SelectOption(
                        label="Name",
                        value="name",
                        description="Edit the name of the custom command.",
                    ),
                    discord.SelectOption(
                        label="Message",
                        value="message",
                        description="Edit the message of the custom command.",
                    ),
                    discord.SelectOption(
                        label="Channel",
                        value="channel",
                        description="Edit the channel overrides of the custom command.",
                    ),
                ],
            )

            await new_msg.edit(
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** okey-dokey, what do you want to edit?",
                view=view,
            )

            await view.wait()
            if view.value == "message":
                view = EmbedCustomisation(ctx.author.id)
                await new_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** your custom command is being sent."
                )

                cmd = None
                for c in Data["commands"]:
                    if c["name"].lower() == command.lower():
                        cmd = c

                message_data = cmd.get("message")
                if message_data is None:
                    await new_msg.edit(view=view)
                else:
                    content = message_data.get("content")

                embeds = message_data.get("embeds")
                if content is None:
                    content = ""
                if embeds is None:
                    embeds = []

                embed_list = []
                for embed in embeds:
                    embed_list.append(discord.Embed.from_dict(embed))
                if embed_list:
                    view = EmbedCustomisation(ctx.author.id, MessageCustomisation(ctx.author.id, data=cmd))
                    await new_msg.edit(content=content, embeds=embed_list, view=view)
                else:
                    view = MessageCustomisation(ctx.author.id)
                    await new_msg.edit(content=content, embeds=[], view=view)

                await view.wait()

                embeds = []
                resultingMessage = view.msg
               # ## # print(view.msg)
                if new_msg.embeds:
                    for embed in new_msg.embeds:
                        embeds.append(embed.to_dict())

                name = command

                updated_message = await ctx.channel.fetch_message(new_msg.id)
                embeds = [embed.to_dict() for embed in updated_message.embeds]


                custom_command_data = {
                    "_id": ctx.guild.id,
                    "commands": [
                        {
                            "name": cmd.get("name"),
                            "id": cmd.get("id"),
                            "message": {
                                "content": updated_message.content,
                                "embeds": embeds,
                            },
                            "channel": cmd.get("channel"),
                        }
                    ],
                }

                if Data:
                    ind = Data["commands"].index(cmd)
                    Data["commands"][ind] = {
                        "name": cmd["name"],
                        "id": cmd["id"],
                        "message": {
                            "content": updated_message.content,
                            "embeds": embeds,
                        },
                        "channel": cmd.get("channel"),
                    }
                else:
                    Data = custom_command_data

                await bot.custom_commands.upsert(Data)
                await ctx.reply(
                    f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** got it, I've edited **{name}**."
                )

            elif view.value == "channel":
                channel_view = ChannelSelect(ctx.author.id, limit=1)
                await new_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what would you like your default channel to be?",
                    view=channel_view,
                )
                await channel_view.wait()
                if channel_view.value:
                    channel = [ch.id for ch in channel_view.value][0]

                    cmd = None
                    for c in Data["commands"]:
                        if c["name"].lower() == command.lower():
                            cmd = c

                    name = command

                    custom_command_data = {
                        "_id": ctx.guild.id,
                        "commands": [
                            {
                                "name": name,
                                "id": next(generator),
                                "message": cmd.get("message"),
                                "channel": cmd.get("channel"),
                            }
                        ],
                    }

                    if Data:
                        ind = Data["commands"].index(cmd)
                        Data["commands"][ind] = {
                            "name": cmd["name"],
                            "id": cmd["id"],
                            "message": cmd["message"],
                            "channel": channel,
                        }
                    else:
                        Data = custom_command_data

                    await bot.custom_commands.upsert(Data)
                    await new_msg.edit(
                        content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** got it, I've edited **{name}**.",
                        view=None,
                    )

            elif view.value == "name":
                view = CustomModalView(
                    ctx.author.id,
                    "Edit Custom Command Name",
                    "Edit Command Name",
                    [
                        (
                            "new_name",
                            discord.ui.TextInput(
                                placeholder="New Name",
                                label="New Name",
                                min_length=1,
                                max_length=32,
                            ),
                        )
                    ],
                )

                await new_msg.edit(
                    content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** what would you like the name of this command to be changed to?",
                    view=view,
                )
                await view.wait()

                new_name = view.modal.new_name.value

                for item in Data["commands"]:
                    if item["name"] == new_name:
                        return await new_msg.edit(
                            content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this command already exists",
                            view=None,
                        )

                await new_msg.edit(
                    content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** sounds good, I've changed it to **{new_name}**.",
                    view=None,
                )

                cmd = None

                for c in Data["commands"]:
                    if c["name"].lower() == command.lower():
                        cmd = c

                custom_command_data = {
                    "_id": ctx.guild.id,
                    "commands": [
                        {
                            "name": new_name,
                            "id": cmd.get("id"),
                            "message": cmd.get("message"),
                            "channel": cmd.get("channel"),
                        }
                    ],
                }

                if Data:
                    ind = Data["commands"].index(cmd)
                    Data["commands"][ind] = {
                        "name": new_name,
                        "id": cmd["id"],
                        "message": cmd["message"],
                        "channel": cmd.get("channel"),
                    }
                else:
                    Data = custom_command_data

                await bot.custom_commands.upsert(Data)

        elif view.value == "delete":
            view = CustomModalView(
                ctx.author.id,
                "Delete a custom command",
                "Delete a custom command",
                [
                    (
                        "name",
                        discord.ui.TextInput(
                            placeholder="Command Name", label="Command Name"
                        ),
                    )
                ],
            )

            await new_msg.edit(
                view=view,
                content=f"<:ERMPending:1111097561588183121>  **{ctx.author.name},** get the name of your custom command ready and input it in the modal!",
            )
            await view.wait()
            name = view.modal.name.value

            for item in Data["commands"]:
                if item["name"].lower() == name.lower():
                    Data["commands"].remove(item)
                    await bot.custom_commands.upsert(Data)

            return await new_msg.edit(
                content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** I've deleted **{name}**.",
                view=None,
            )

        elif view.value == "list":
            content = f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** you're **viewing** all custom commands."
            embed = discord.Embed(
                title="<:ERMCustomCommands:1113210178448396348> Custom Commands",
                color=0xED4348,
            )
            embed.set_author(
                name=ctx.author.name,
                icon_url=ctx.author.display_avatar.url,
            )
            embed.set_thumbnail(url=ctx.guild.icon.url)
            for item in Data["commands"]:
                embed.add_field(
                    name=f"<:ERMList:1111099396990435428> {item['name']}",
                    value=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912> **ID:** {item['id']}",
                    inline=False,
                )
            if len(embed.fields) == 0:
                await ctx.reply(
                    f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** looks like you haven't created any custom commands!"
                )

            return await new_msg.edit(embed=embed, content=content, view=None)

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
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** looks like you haven't created any custom commands!"
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
                f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** there aren't any custom commands with that name!"
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


        if ctx.interaction:
            if selected['message']['content'] in [None, ""] and len(selected['message']['embeds']) == 0:
                return await ctx.interaction.followup.send(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name}**, due to Discord limitations - I am unable to send your reminder. Your message is most likely empty.")
            await ctx.interaction.followup.send(
                content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've just run the custom command in **{channel}**."
            ),
            await channel.send(
                content=await interpret_content(
                    bot, ctx, channel, selected["message"]["content"]
                ),
                embeds=embeds,
                allowed_mentions=discord.AllowedMentions(
                    everyone=True, users=True, roles=True, replied_user=True
                )
            )
        else:
            if selected['message']['content'] in [None, ""] and len(selected['message']['embeds']) == 0:
                return await ctx.reply(content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name}**, due to Discord limitations - I am unable to send your reminder. Your message is most likely empty.")
            await ctx.reply(
                content=f"<:ERMCheck:1111089850720976906> **{ctx.author.name},** I've just run the custom command in **{channel}**."
            )

            await channel.send(
                content=await interpret_content(
                    bot, ctx, channel, selected["message"]["content"]
                ),
                embeds=embeds,
                allowed_mentions=discord.AllowedMentions(
                    everyone=True, users=True, roles=True, replied_user=True
                ),
            )


async def setup(bot):
    await bot.add_cog(CustomCommands(bot))
