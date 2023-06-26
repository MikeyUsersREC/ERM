import discord
from discord.ext import commands

from menus import CustomExecutionButton, CustomSelectMenu


class Privacy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="consent",
        description="Change your privacy settings.",
        extras={"category": "Privacy", "ephemeral": True},
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
        embed = (
            discord.Embed(
                title="<:ERMUser:1111098647485108315> Notification Settings",
                description=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Punishment Alerts:** {'<:ERMCheck:1111089850720976906>' if punishments_enabled is True else '<:ERMClose:1111101633389146223>'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Shift Reports:** {'<:ERMCheck:1111089850720976906>' if shift_reports_enabled is True else '<:ERMClose:1111101633389146223>'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**AI Predictions:** {'<:ERMCheck:1111089850720976906>' if ai_enabled is True else '<:ERMClose:1111101633389146223>'}",
                color=0xED4348,
            )
            .set_thumbnail(url=ctx.author.display_avatar.url)
            .set_author(icon_url=ctx.author.display_avatar.url, name=ctx.author.name)
        )

        custom_view = discord.ui.View()

        async def punishment_alerts(
            interaction: discord.Interaction, button: discord.ui.Button
        ):
            if interaction.user.id == ctx.author.id:
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
                embed = (
                    discord.Embed(
                        title="<:ERMUser:1111098647485108315> Notification Settings",
                        description=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Punishment Alerts:** {'<:ERMCheck:1111089850720976906>' if punishments_enabled is True else '<:ERMClose:1111101633389146223>'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Shift Reports:** {'<:ERMCheck:1111089850720976906>' if shift_reports_enabled is True else '<:ERMClose:1111101633389146223>'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**AI Predictions:** {'<:ERMCheck:1111089850720976906>' if ai_enabled is True else '<:ERMClose:1111101633389146223>'}",
                        color=0xED4348,
                    )
                    .set_thumbnail(url=ctx.author.display_avatar.url)
                    .set_author(
                        icon_url=ctx.author.display_avatar.url, name=ctx.author.name
                    )
                )
                await interaction.response.send_message(
                    embed=embed, view=view, ephemeral=True
                )
                button.view.stop()
                await view.wait()
                if view.value == "enable":
                    if selected is None:
                        await bot.consent.insert(
                            {"_id": ctx.author.id, "punishments": True}
                        )
                    else:
                        selected["punishments"] = True
                        await bot.consent.update_by_id(selected)

                    await interaction.edit_original_response(
                        content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** got it, I've enabled punishment alerts.",
                        embed=None,
                        view=None,
                    )
                elif view.value == "disable":
                    if selected is None:
                        await bot.consent.insert(
                            {"_id": ctx.author.id, "punishments": False}
                        )
                    else:
                        selected["punishments"] = False
                        await bot.consent.update_by_id(selected)
                    await interaction.edit_original_response(
                        content=f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** got it, I've disabled punishment alerts.",
                        embed=None,
                        view=None,
                    )
            else:
                await interaction.response.send_message(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this isn't your embed to modify.",
                    embed=None,
                    view=None,
                    ephemeral=True,
                )

        async def punishment_predictions(
            interaction: discord.Interaction, button: discord.ui.Button
        ):
            if interaction.user.id == ctx.author.id:
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
                embed = discord.Embed(
                    title="<:ERMUser:1111098647485108315> Notification Settings",
                    description=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Punishment Alerts:** {'<:ERMCheck:1111089850720976906>' if punishments_enabled is True else '<:ERMClose:1111101633389146223>'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Shift Reports:** {'<:ERMCheck:1111089850720976906>' if shift_reports_enabled is True else '<:ERMClose:1111101633389146223>'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**AI Predictions:** {'<:ERMCheck:1111089850720976906>' if ai_enabled is True else '<:ERMClose:1111101633389146223>'}",
                    color=0xED4348,
                ).set_thumbnail(url=ctx.author.display_avatar.url)
                await interaction.response.send_message(
                    embed=embed, view=view, ephemeral=True
                )
                button.view.stop()
                await view.wait()
                if view.value == "enable":
                    if selected is None:
                        await bot.consent.insert(
                            {"_id": ctx.author.id, "ai_predictions": True}
                        )
                    else:
                        selected["ai_predictions"] = True
                        await bot.consent.update_by_id(selected)
                    content = f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** got it, I've enabled AI Predictions."
                    await interaction.edit_original_response(
                        content=content, embed=None, view=None
                    )
                elif view.value == "disable":
                    if selected is None:
                        await bot.consent.insert(
                            {"_id": ctx.author.id, "ai_predictions": False}
                        )
                    else:
                        selected["ai_predictions"] = False
                        await bot.consent.update_by_id(selected)
                    content = f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** got it, I've disabled AI Predictions."
                    await interaction.edit_original_response(
                        content=content, embed=None, view=None
                    )

            else:
                await interaction.response.send_message(
                    content=f"<:ERMClose:1111101633389146223>  **{ctx.author.name},** this isn't your embed to modify.",
                    embed=None,
                    view=None,
                    ephemeral=True,
                )

        async def shift_reports(
            interaction: discord.Interaction, button: discord.ui.Button
        ):
            if interaction.user.id == ctx.author.id:
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
                embed = discord.Embed(
                    title="<:ERMUser:1111098647485108315> Notification Settings",
                    description=f"<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Punishment Alerts:** {'<:ERMCheck:1111089850720976906>' if punishments_enabled is True else '<:ERMClose:1111101633389146223>'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**Shift Reports:** {'<:ERMCheck:1111089850720976906>' if shift_reports_enabled is True else '<:ERMClose:1111101633389146223>'}\n<:Space:1100877460289101954><:ERMArrow:1111091707841359912>**AI Predictions:** {'<:ERMCheck:1111089850720976906>' if ai_enabled is True else '<:ERMClose:1111101633389146223>'}",
                    color=0xED4348,
                ).set_thumbnail(url=ctx.author.display_avatar.url)
                await interaction.response.send_message(
                    embed=embed, view=view, ephemeral=True
                )
                button.view.stop()
                await view.wait()
                if view.value == "enable":
                    if selected is None:
                        await bot.consent.insert(
                            {"_id": ctx.author.id, "shift_reports": True}
                        )
                    else:
                        selected["shift_reports"] = True
                        await bot.consent.update_by_id(selected)
                    content = f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** got it, I've enabled Shift Reports."
                    await interaction.edit_original_response(
                        content=content, embed=None, view=None
                    )

                elif view.value == "disable":
                    if selected is None:
                        await bot.consent.insert(
                            {"_id": ctx.author.id, "shift_reports": False}
                        )
                    else:
                        selected["shift_reports"] = False
                        await bot.consent.update_by_id(selected)
                    content = f"<:ERMCheck:1111089850720976906>  **{ctx.author.name},** got it, I've disabled Shift Reports."
                    await interaction.edit_original_response(
                        content=content, embed=None, view=None
                    )

        buttons = [
            CustomExecutionButton(
                ctx.author.id,
                label="Punishment Alerts",
                style=discord.ButtonStyle.secondary,
                func=punishment_alerts,
            ),
            CustomExecutionButton(
                ctx.author.id,
                label="Shift Reports",
                style=discord.ButtonStyle.secondary,
                func=shift_reports,
            ),
            CustomExecutionButton(
                ctx.author.id,
                label="AI Predictions",
                style=discord.ButtonStyle.secondary,
                func=punishment_predictions,
            ),
        ]

        for child in buttons:
            custom_view.add_item(child)

        await ctx.reply(embed=embed, view=custom_view)


async def setup(bot):
    await bot.add_cog(Privacy(bot))
