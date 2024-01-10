import datetime

import discord
from discord.ext import commands

from menus import CustomExecutionButton, CustomSelectMenu
from utils.constants import BLANK_COLOR


class Privacy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.hybrid_command(
        name="consent",
        description="Change your privacy settings.",
        extras={"category": "Privacy"},
    )
    async def consent(self, ctx):
        bot = self.bot
        punishments_enabled = True
        ai_enabled = True
        selected = None
        shift_reports_enabled = True

        async for document in bot.consent.db.find({"_id": ctx.author.id}):
            punishments_enabled = (
                document.get("punishments")
                if document.get("punishments") is not None
                else True
            )
            shift_reports_enabled = (
                document.get("shift_reports")
                if document.get("shift_reports") is not None
                else True
            )
            ai_enabled = (
                document.get("ai_predictions")
                if document.get("ai_predictions") is not None
                else True
            )
            selected = document
        embed = discord.Embed(
            title="User Settings",
            color=BLANK_COLOR
        )
        embed.add_field(
            name="Configurations",
            value=(
                f"> **Punishment Alerts:** {'<:check:1163142000271429662>' if punishments_enabled is True else '<:xmark:1166139967920164915>'}\n"
                f"> **Shift Reports:** {'<:check:1163142000271429662>' if shift_reports_enabled is True else '<:xmark:1166139967920164915>'}\n"
                f"> **AI Predictions:** {'<:check:1163142000271429662>' if ai_enabled is True else '<:xmark:1166139967920164915>'}\n"
            ),
            inline=False
        )
        embed.set_author(
            name=ctx.guild.name,
            icon_url=ctx.guild.icon.url if ctx.guild.icon else ''
        )
        embed.set_thumbnail(
            url=ctx.author.display_avatar.url
        )
        embed.set_footer(
            text="User Settings"
        )
        embed.timestamp = datetime.datetime.now()

        custom_view = discord.ui.View()

        async def punishment_alerts(
            interaction: discord.Interaction, button: discord.ui.Button
        ):
            nonlocal selected
            nonlocal punishments_enabled
            if interaction.user.id == ctx.author.id:
                await interaction.response.defer()
                view = CustomSelectMenu(
                    ctx.author.id,
                    [
                        discord.SelectOption(
                            label="Enable",
                            value="enable",
                            description="Enable punishment alerts.",
                        ),
                        discord.SelectOption(
                            label="Disable",
                            value="disable",
                            description="Disable punishment alerts.",
                        ),
                    ],
                )

                await interaction.message.edit(
                    view=view
                )
                await view.wait()
                if view.value == "enable":
                    if selected is None:
                        await bot.consent.insert(
                            {"_id": ctx.author.id, "punishments": True}
                        )
                    else:
                        selected["punishments"] = True
                        if not selected.get('_id'):
                            selected['_id'] = ctx.author.id
                        await bot.consent.update_by_id(selected)
                    punishments_enabled = True
                    embed = discord.Embed(
                        title="User Settings",
                        color=BLANK_COLOR
                    )
                    embed.add_field(
                        name="Configurations",
                        value=(
                            f"> **Punishment Alerts:** {'<:check:1163142000271429662>' if punishments_enabled is True else '<:xmark:1166139967920164915>'}\n"
                            f"> **Shift Reports:** {'<:check:1163142000271429662>' if shift_reports_enabled is True else '<:xmark:1166139967920164915>'}\n"
                            f"> **AI Predictions:** {'<:check:1163142000271429662>' if ai_enabled is True else '<:xmark:1166139967920164915>'}\n"
                        ),
                        inline=False
                    )
                    embed.set_author(
                        name=ctx.guild.name,
                        icon_url=ctx.guild.icon.url if ctx.guild.icon else ''
                    )
                    embed.set_thumbnail(
                        url=ctx.author.display_avatar.url
                    )
                    embed.set_footer(
                        text="User Settings"
                    )
                    embed.timestamp = datetime.datetime.now()
                    button.style = discord.ButtonStyle.success
                    await interaction.message.edit(
                        content='',
                        embed=embed,
                        view=button.view,
                    )
                elif view.value == "disable":
                    if selected is None:
                        selected = {"_id": ctx.author.id, "punishments": False}
                        await bot.consent.insert(
                            {"_id": ctx.author.id, "punishments": False}
                        )
                    else:
                        selected["punishments"] = False
                        if not selected.get('_id'):
                            selected['_id'] = ctx.author.id
                        await bot.consent.update_by_id(selected)
                    punishments_enabled = False
                    embed = discord.Embed(
                        title="User Settings",
                        color=BLANK_COLOR
                    )
                    embed.add_field(
                        name="Configurations",
                        value=(
                            f"> **Punishment Alerts:** {'<:check:1163142000271429662>' if punishments_enabled is True else '<:xmark:1166139967920164915>'}\n"
                            f"> **Shift Reports:** {'<:check:1163142000271429662>' if shift_reports_enabled is True else '<:xmark:1166139967920164915>'}\n"
                            f"> **AI Predictions:** {'<:check:1163142000271429662>' if ai_enabled is True else '<:xmark:1166139967920164915>'}\n"
                        ),
                        inline=False
                    )
                    embed.set_author(
                        name=ctx.guild.name,
                        icon_url=ctx.guild.icon.url if ctx.guild.icon else ''
                    )
                    embed.set_thumbnail(
                        url=ctx.author.display_avatar.url
                    )
                    embed.set_footer(
                        text="User Settings"
                    )
                    embed.timestamp = datetime.datetime.now()
                    button.style = discord.ButtonStyle.danger

                    await interaction.message.edit(
                        content='',
                        embed=embed,
                        view=button.view,
                    )
            else:
                await interaction.response.send_message(embed=discord.Embed(
                    title="Not Permitted",
                    description="You are not permitted to interact with these buttons.",
                    color=BLANK_COLOR
                ), ephemeral=True)

        async def punishment_predictions(
            interaction: discord.Interaction, button: discord.ui.Button
        ):
            if interaction.user.id == ctx.author.id:
                nonlocal selected
                nonlocal ai_enabled
                await interaction.response.defer()
                view = CustomSelectMenu(
                    ctx.author.id,
                    [
                        discord.SelectOption(
                            label="Enable",
                            value="enable",
                            description="Enable AI Predictions.",
                        ),
                        discord.SelectOption(
                            label="Disable",
                            value="disable",
                            description="Disable AI Predictions.",
                        ),
                    ],
                )

                await interaction.message.edit(
                    view=view
                )
                await view.wait()
                if view.value == "enable":
                    if selected is None:
                        selected = {"_id": ctx.author.id, "ai_predictions": True}
                        await bot.consent.insert(
                            selected
                        )
                    else:
                        selected["ai_predictions"] = True
                        if not selected.get('_id'):
                            selected['_id'] = ctx.author.id
                        await bot.consent.update_by_id(selected)
                    ai_enabled = True
                    embed = discord.Embed(
                        title="User Settings",
                        color=BLANK_COLOR
                    )
                    embed.add_field(
                        name="Configurations",
                        value=(
                            f"> **Punishment Alerts:** {'<:check:1163142000271429662>' if punishments_enabled is True else '<:xmark:1166139967920164915>'}\n"
                            f"> **Shift Reports:** {'<:check:1163142000271429662>' if shift_reports_enabled is True else '<:xmark:1166139967920164915>'}\n"
                            f"> **AI Predictions:** {'<:check:1163142000271429662>' if ai_enabled is True else '<:xmark:1166139967920164915>'}\n"
                        ),
                        inline=False
                    )
                    embed.set_author(
                        name=ctx.guild.name,
                        icon_url=ctx.guild.icon.url if ctx.guild.icon else ''
                    )
                    embed.set_thumbnail(
                        url=ctx.author.display_avatar.url
                    )
                    embed.set_footer(
                        text="User Settings"
                    )
                    embed.timestamp = datetime.datetime.now()
                    button.style = discord.ButtonStyle.success
                    await interaction.message.edit(
                        embed=embed,
                        view=button.view,
                    )
                elif view.value == "disable":
                    if selected is None:
                        selected = {"_id": ctx.author.id, "ai_predictions": False}
                        await bot.consent.insert(
                            selected
                        )
                    else:
                        selected["ai_predictions"] = False
                        if not selected.get('_id'):
                            selected['_id'] = ctx.author.id
                        await bot.consent.update_by_id(selected)
                    ai_enabled = False
                    embed = discord.Embed(
                        title="User Settings",
                        color=BLANK_COLOR
                    )
                    embed.add_field(
                        name="Configurations",
                        value=(
                            f"> **Punishment Alerts:** {'<:check:1163142000271429662>' if punishments_enabled is True else '<:xmark:1166139967920164915>'}\n"
                            f"> **Shift Reports:** {'<:check:1163142000271429662>' if shift_reports_enabled is True else '<:xmark:1166139967920164915>'}\n"
                            f"> **AI Predictions:** {'<:check:1163142000271429662>' if ai_enabled is True else '<:xmark:1166139967920164915>'}\n"
                        ),
                        inline=False
                    )
                    embed.set_author(
                        name=ctx.guild.name,
                        icon_url=ctx.guild.icon.url if ctx.guild.icon else ''
                    )
                    embed.set_thumbnail(
                        url=ctx.author.display_avatar.url
                    )
                    embed.set_footer(
                        text="User Settings"
                    )
                    embed.timestamp = datetime.datetime.now()
                    button.style = discord.ButtonStyle.danger
                    await interaction.message.edit(
                        content='',
                        embed=embed,
                        view=button.view,
                    )

            else:
                await interaction.response.send_message(embed=discord.Embed(
                    title="Not Permitted",
                    description="You are not permitted to interact with these buttons.",
                    color=BLANK_COLOR
                ), ephemeral=True)

        async def shift_reports(
            interaction: discord.Interaction, button: discord.ui.Button
        ):
            if interaction.user.id == ctx.author.id:
                nonlocal selected
                nonlocal shift_reports_enabled
                await interaction.response.defer()
                view = CustomSelectMenu(
                    ctx.author.id,
                    [
                        discord.SelectOption(
                            label="Enable",
                            value="enable",
                            description="Enable shift reports.",
                        ),
                        discord.SelectOption(
                            label="Disable",
                            value="disable",
                            description="Disable shift reports.",
                        ),
                    ],
                )

                await interaction.message.edit(
                    view=view
                )
                await view.wait()
                if view.value == "enable":
                    if selected is None:
                        selected = {"_id": ctx.author.id, "shift_reports": True}
                        await bot.consent.insert(
                            selected
                        )
                    else:
                        selected["shift_reports"] = True
                        if not selected.get('_id'):
                            selected['_id'] = ctx.author.id
                        await bot.consent.update_by_id(selected)
                    shift_reports_enabled = True
                    embed = discord.Embed(
                        title="User Settings",
                        color=BLANK_COLOR
                    )
                    embed.add_field(
                        name="Configurations",
                        value=(
                            f"> **Punishment Alerts:** {'<:check:1163142000271429662>' if punishments_enabled is True else '<:xmark:1166139967920164915>'}\n"
                            f"> **Shift Reports:** {'<:check:1163142000271429662>' if shift_reports_enabled is True else '<:xmark:1166139967920164915>'}\n"
                            f"> **AI Predictions:** {'<:check:1163142000271429662>' if ai_enabled is True else '<:xmark:1166139967920164915>'}\n"
                        ),
                        inline=False
                    )
                    embed.set_author(
                        name=ctx.guild.name,
                        icon_url=ctx.guild.icon.url if ctx.guild.icon else ''
                    )
                    embed.set_thumbnail(
                        url=ctx.author.display_avatar.url
                    )
                    embed.set_footer(
                        text="User Settings"
                    )
                    embed.timestamp = datetime.datetime.now()
                    button.style = discord.ButtonStyle.success

                    await interaction.edit_original_response(
                        content='',
                        embed=embed,
                        view=button.view,
                    )

                elif view.value == "disable":
                    if selected is None:
                        selected = {"_id": ctx.author.id, "shift_reports": False}
                        await bot.consent.insert(
                            selected
                        )
                    else:
                        selected["shift_reports"] = False
                        if not selected.get('_id'):
                            selected['_id'] = ctx.author.id

                        await bot.consent.update_by_id(selected)
                    shift_reports_enabled = False
                    embed = discord.Embed(
                        title="User Settings",
                        color=BLANK_COLOR
                    )
                    embed.add_field(
                        name="Configurations",
                        value=(
                            f"> **Punishment Alerts:** {'<:check:1163142000271429662>' if punishments_enabled is True else '<:xmark:1166139967920164915>'}\n"
                            f"> **Shift Reports:** {'<:check:1163142000271429662>' if shift_reports_enabled is True else '<:xmark:1166139967920164915>'}\n"
                            f"> **AI Predictions:** {'<:check:1163142000271429662>' if ai_enabled is True else '<:xmark:1166139967920164915>'}\n"
                        ),
                        inline=False
                    )
                    embed.set_author(
                        name=ctx.guild.name,
                        icon_url=ctx.guild.icon.url if ctx.guild.icon else ''
                    )
                    embed.set_thumbnail(
                        url=ctx.author.display_avatar.url
                    )
                    embed.set_footer(
                        text="User Settings"
                    )
                    embed.timestamp = datetime.datetime.now()
                    button.style = discord.ButtonStyle.danger
                    await interaction.message.edit(
                        content='',
                        embed=embed,
                        view=button.view,
                    )
            else:
                await interaction.response.send_message(embed=discord.Embed(
                    title="Not Permitted",
                    description="You are not permitted to interact with these buttons.",
                    color=BLANK_COLOR
                ), ephemeral=True)

        buttons = [
            CustomExecutionButton(
                ctx.author.id,
                label="Punishment Alerts",
                style=discord.ButtonStyle.danger if not punishments_enabled else discord.ButtonStyle.success,
                func=punishment_alerts,
            ),
            CustomExecutionButton(
                ctx.author.id,
                label="Shift Reports",
                style=discord.ButtonStyle.danger if not shift_reports_enabled else discord.ButtonStyle.success,
                func=shift_reports,
            ),
            CustomExecutionButton(
                ctx.author.id,
                label="AI Predictions",
                style=discord.ButtonStyle.danger if not ai_enabled else discord.ButtonStyle.success,
                func=punishment_predictions,
            ),
        ]

        for child in buttons:
            custom_view.add_item(child)

        await ctx.reply(embed=embed, view=custom_view)


async def setup(bot):
    await bot.add_cog(Privacy(bot))
