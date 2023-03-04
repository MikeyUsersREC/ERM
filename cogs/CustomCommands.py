import discord
from discord import app_commands
from discord.ext import commands

from erm import is_management, generator, command_autocomplete
from menus import CustomSelectMenu, AddCustomCommand, YesNoColourMenu, ChannelSelect, CustomModalView, \
    EmbedCustomisation, RemoveCustomCommand, MessageCustomisation
from utils.utils import invis_embed, request_response, interpret_embed, interpret_content


class CustomCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(
        name='custom'
    )
    @is_management()
    async def custom(self, ctx):
        pass

    @custom.command(
        name="manage",
        description="Manage your custom commands.",
        extras={
            "category": "Custom Commands"
        }
    )
    async def custom_manage(self, ctx):
        bot = self.bot
        Data = await bot.custom_commands.find_by_id(ctx.guild.id)

        if Data is None:
            Data = {
                '_id': ctx.guild.id,
                "commands": []
            }

        view = CustomSelectMenu(ctx.author.id, [
            discord.SelectOption(
                label="Create",
                value="create",
                description="Create a new custom command.",
                emoji="<:SConductTitle:1053359821308567592>"
            ),
            discord.SelectOption(
                label="List",
                value="list",
                description="List all of the custom commands",
                emoji="<:Pause:1035308061679689859>"
            ),
            discord.SelectOption(
                label="Edit",
                value="edit",
                description="Edit an existing custom command.",
                emoji="<:EditIcon:1042550862834323597>"
            ),
            discord.SelectOption(
                label="Delete",
                value="delete",
                description="Delete an existing custom command",
                emoji="<:TrashIcon:1042550860435181628>"
            )
        ])

        embed = discord.Embed(
            title="<:Resume:1035269012445216858> Manage Custom Commands",
            description="<:ArrowRight:1035003246445596774> What would you like to do?",
            color=0x2e3136
        )
        await ctx.send(embed=embed, view=view)

        timeout = await view.wait()
        if timeout:
            return

        if view.value == 'create':
            view = AddCustomCommand(ctx.author.id)
            await ctx.send(view=view)
            timeout = await view.wait()
            if timeout:
                return

            await view.view.wait()
            await view.view.newView.wait()

            try:
                name = view.information['name']
            except:
                return await invis_embed(ctx, 'This has been successfully cancelled.')

            for item in Data['commands']:
                if item['name'] == name:
                    return await invis_embed(ctx,
                                             'This command already exists. Please try again with a different name.')

            embeds = []
            resultingMessage = view.view.newView.msg
            for embed in resultingMessage.embeds:
                embeds.append(embed.to_dict())

            embed = discord.Embed(
                title="<:Resume:1035269012445216858> Custom Commands",
                description="<:ArrowRight:1035003246445596774> Would you like this custom command to have a default channel? If this isn't selected, the custom command will be run in the same channel as the command or the channel argument specified in the command.",
                color=0x2e3136
            )
            channel_view = YesNoColourMenu(ctx.author.id)
            await ctx.send(embed=embed, view=channel_view)
            await channel_view.wait()
            channel = None
            if channel_view.value is True:
                embed = discord.Embed(
                    title="<:Resume:1035269012445216858> Custom Commands",
                    description="<:ArrowRight:1035003246445596774> Would you like this custom command to have a default channel? If this isn't selected, the custom command will be run in the same channel as the command or the channel argument specified in the command.",
                    color=0x2e3136
                )

                channel_view = ChannelSelect(ctx.author.id, limit=1)
                await ctx.send(embed=embed, view=channel_view)
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
                            "channel": channel
                        }
                    }
                ]
            }

            if Data:
                Data['commands'].append({
                    "name": name,
                    "id": next(generator),
                    "message": {
                        "content": resultingMessage.content,
                        "embeds": embeds,
                        "channel": channel
                    }
                })
            else:
                Data = custom_command_data

            await bot.custom_commands.upsert(Data)
            successEmbed = discord.Embed(
                title="<:CheckIcon:1035018951043842088> Success!",
                description=f"<:ArrowRight:1035003246445596774> Your custom command has been added successfully.",
                color=0x71c15f
            )
            await ctx.send(embed=successEmbed)
        elif view.value == 'edit':

            embed = discord.Embed(
                title="<:EditIcon:1042550862834323597> Edit a Custom Command",
                description="<:ArrowRight:1035003246445596774> What custom command would you like to edit?",
                color=0x2e3136
            )

            view = CustomModalView(ctx.author.id, 'Edit a Custom Command', 'Edit a Custom Command', [
                (
                    'name',
                    discord.ui.TextInput(
                        placeholder="Name of the custom command",
                        label="Name of the custom command",
                        style=discord.TextStyle.short
                    )
                )
            ])

            await ctx.send(embed=embed, view=view)
            await view.wait()

            try:
                command = view.modal.name.value
            except:
                return await invis_embed(ctx, 'This has been successfully cancelled.')

            if command.lower() not in [c['name'].lower() for c in Data['commands']]:
                return await invis_embed(ctx, 'This command does not exist.')

            embed = discord.Embed(
                title="<:EditIcon:1042550862834323597> Edit a Custom Command",
                description="<:ArrowRight:1035003246445596774> What would you like to edit about this custom command?",
                color=0x2e3136
            )
            view = CustomSelectMenu(
                ctx.author.id,
                [
                    discord.SelectOption(
                        label="Name",
                        value="name",
                        description="Edit the name of the custom command."
                    ),
                    discord.SelectOption(
                        label="Message",
                        value="message",
                        description="Edit the message of the custom command."
                    ),
                    discord.SelectOption(
                        label="Channel",
                        value="channel",
                        description="Edit the channel overrides of the custom command."
                    )
                ]
            )

            await ctx.send(embed=embed, view=view)
            await view.wait()
            if view.value == "message":
                view = EmbedCustomisation(ctx.author.id)
                embed = discord.Embed(description="<a:Loading:1044067865453670441> We are loading your custom command.",
                                      color=0x2E3136)
                msg = await ctx.send(embed=embed)

                cmd = None
                for c in Data['commands']:
                    if c['name'].lower() == command.lower():
                        cmd = c

                message_data = cmd.get('message')
                if message_data is None:
                    await msg.edit(view=view)
                else:
                    content = message_data.get('content')
                    embeds = message_data.get('embeds')
                    if content is None:
                        content = ""
                    if embeds is None:
                        embeds = []
                    if embeds:
                        embed_list = []
                        for embed in embeds:
                            embed_list.append(discord.Embed.from_dict(embed))

                        await msg.edit(content=content, embeds=embed_list, view=view)
                    else:
                        view = MessageCustomisation(ctx.author.id)
                        await msg.edit(content=content, embeds=[], view=view)
                await view.wait()

                embeds = []
                resultingMessage = view.msg
                print(view.msg)
                if msg.embeds:
                    for embed in resultingMessage.embeds:
                        embeds.append(embed.to_dict())

                name = command

                custom_command_data = {
                    "_id": ctx.guild.id,
                    "commands": [
                        {
                            "name": cmd.get('name'),
                            "id": cmd.get("id"),
                            "message": {
                                "content": resultingMessage.content,
                                "embeds": embeds
                            },
                            "channel": cmd.get('channel')
                        }
                    ]
                }

                if Data:
                    ind = Data['commands'].index(cmd)
                    Data['commands'][ind] = {
                        "name": cmd['name'],
                        "id": cmd['id'],
                        "message": {
                            "content": resultingMessage.content,
                            "embeds": embeds
                        },
                        "channel": cmd.get('channel')
                    }
                else:
                    Data = custom_command_data

                await bot.custom_commands.upsert(Data)
                successEmbed = discord.Embed(
                    title="<:CheckIcon:1035018951043842088> Success!",
                    description=f"<:ArrowRight:1035003246445596774> Your custom command has been edited successfully.",
                    color=0x71c15f
                )
                await ctx.send(embed=successEmbed)
            elif view.value == "channel":
                embed = discord.Embed(
                    title="<:Resume:1035269012445216858> Custom Commands",
                    description="<:ArrowRight:1035003246445596774> Would you like this custom command to have a default channel? If this isn't selected, the custom command will be run in the same channel as the command or the channel argument specified in the command."
                    , color=0x2e3136
                )
                channel_view = YesNoColourMenu(ctx.author.id)
                await ctx.send(embed=embed, view=channel_view)
                await channel_view.wait()
                channel = None
                if channel_view.value is True:
                    embed = discord.Embed(
                        title="<:Resume:1035269012445216858> Custom Commands",
                        description="<:ArrowRight:1035003246445596774> Would you like this custom command to have a default channel? If this isn't selected, the custom command will be run in the same channel as the command or the channel argument specified in the command.",
                        color=0x2e3136
                    )

                    channel_view = ChannelSelect(ctx.author.id, limit=1)
                    await ctx.send(embed=embed, view=channel_view)
                    await channel_view.wait()
                    if channel_view.value:
                        channel = [ch.id for ch in channel_view.value][0]

                cmd = None
                for c in Data['commands']:
                    if c['name'].lower() == command.lower():
                        cmd = c

                name = command

                custom_command_data = {
                    "_id": ctx.guild.id,
                    "commands": [
                        {
                            "name": name,
                            "id": next(generator),
                            "message": cmd.get('message'),
                            "channel": cmd.get('channel')
                        }
                    ]
                }

                if Data:
                    ind = Data['commands'].index(cmd)
                    Data['commands'][ind] = {
                        "name": cmd['name'],
                        "id": cmd['id'],
                        "message": cmd['message'],
                        "channel": channel
                    }
                else:
                    Data = custom_command_data

                await bot.custom_commands.upsert(Data)
                successEmbed = discord.Embed(
                    title="<:CheckIcon:1035018951043842088> Success!",
                    description=f"<:ArrowRight:1035003246445596774> Your custom command has been edited successfully.",
                    color=0x71c15f
                )
                await ctx.send(embed=successEmbed)
            elif view.value == "name":
                embed = discord.Embed(
                    title="<:EditIcon:1042550862834323597> Edit a Custom Command",
                    description="<:ArrowRight:1035003246445596774> What would you like to change the name of this custom command to?",
                    color=0x2e3136
                )

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
                                max_length=32
                            )
                        )
                    ]
                )

                await ctx.send(embed=embed, view=view)
                await view.wait()

                new_name = view.modal.new_name.value

                cmd = None

                for c in Data['commands']:
                    if c['name'].lower() == command.lower():
                        cmd = c

                custom_command_data = {
                    "_id": ctx.guild.id,
                    "commands": [
                        {
                            "name": new_name,
                            "id": cmd.get("id"),
                            "message": cmd.get('message'),
                            "channel": cmd.get('channel')
                        }
                    ]
                }

                if Data:
                    ind = Data['commands'].index(cmd)
                    Data['commands'][ind] = {
                        "name": new_name,
                        "id": cmd['id'],
                        "message": cmd['message'],
                        "channel": cmd.get('channel')
                    }
                else:
                    Data = custom_command_data

                await bot.custom_commands.upsert(Data)



        elif view.value == "delete":
            embed = discord.Embed(title="<:Resume:1035269012445216858> Remove a custom command", color=0x2E3136)
            for item in Data['commands']:
                embed.add_field(name=f"<:Clock:1035308064305332224> {item['name']}",
                                value=f"<:ArrowRightW:1035023450592514048> **Name:** {item['name']}\n<:ArrowRightW:1035023450592514048> **ID:** {item['id']}",
                                inline=False)

            if len(embed.fields) == 0:
                embed.add_field(name="<:Clock:1035308064305332224> No custom commands",
                                value="<:ArrowRightW:1035023450592514048> No custom commands have been added.",
                                inline=False)
                return await ctx.send(embed=embed)

            view = RemoveCustomCommand(ctx.author.id)

            await ctx.send(embed=embed, view=view)
            await view.wait()

            if view.value == "delete":
                name = (await request_response(bot, ctx,
                                               "What custom command would you like to delete? (e.g. `1`)\n*Specify the ID to delete the custom command.*")).content

                for item in Data['commands']:
                    if item['id'] == int(name):
                        Data['commands'].remove(item)
                        await bot.custom_commands.upsert(Data)
                        successEmbed = discord.Embed(
                            title="<:CheckIcon:1035018951043842088> Command Removed",
                            description="<:ArrowRight:1035003246445596774> Your custom command has been removed successfully.",
                            color=0x71c15f
                        )

                        return await ctx.send(embed=successEmbed)

        elif view.value == "list":
            embed = discord.Embed(title="<:Resume:1035269012445216858> Custom Commands", color=0x2E3136)
            for item in Data['commands']:
                embed.add_field(name=f"<:Clock:1035308064305332224> {item['name']}",
                                value=f"<:ArrowRightW:1035023450592514048> **Name:** {item['name']}\n<:ArrowRightW:1035023450592514048> **ID:** {item['id']}",
                                inline=False)
            if len(embed.fields) == 0:
                embed.add_field(name="<:Clock:1035308064305332224> No custom commands",
                                value="<:ArrowRight:1035003246445596774> No custom commands have been added.",
                                inline=False
                                )

            return await ctx.send(embed=embed)

    @custom.command(
        name="run",
        description="Run a custom command.",
        extras={"category": "Custom Commands", "ephemeral": True},
    )
    @app_commands.autocomplete(command=command_autocomplete)
    @is_management()
    @app_commands.describe(command="What custom command would you like to run?")
    @app_commands.describe(channel="Where do you want this custom command's output to go? (e.g. #general)")
    async def run(self, ctx, command: str, channel: discord.TextChannel = None):
        bot = self.bot
        Data = await bot.custom_commands.find_by_id(ctx.guild.id)
        if Data is None:
            return await invis_embed(ctx, 'There are no custom commands associated with this server.')
        is_command = False
        selected = None
        if 'commands' in Data.keys():
            if isinstance(Data['commands'], list):
                for cmd in Data['commands']:
                    if cmd['name'].lower().replace(' ', '') == command.lower().replace(' ', ''):
                        is_command = True
                        selected = cmd

        if not is_command:
            return await invis_embed(ctx, 'There is no custom command with the associated name.')

        if not channel:
            if selected.get('channel') is None:
                channel = ctx.channel
            else:
                channel = discord.utils.get(ctx.guild.text_channels, id=selected['channel']) if discord.utils.get(
                    ctx.guild.text_channels, id=selected['channel']) is not None else ctx.channel
        embeds = []
        for embed in selected['message']['embeds']:
            embeds.append(await interpret_embed(bot, ctx, channel, embed))

        if ctx.interaction:
            embed = discord.Embed(
                description='<:ArrowRight:1035003246445596774> Successfully ran this custom command!',
                color=0x2e3136
            )

            await ctx.interaction.followup.send(embed=embed)

        else:
            await invis_embed(ctx, "Successfully ran this custom command!")
        await channel.send(content=await interpret_content(bot, ctx, channel, selected['message']['content']),
                           embeds=embeds)


async def setup(bot):
    await bot.add_cog(CustomCommands(bot))
