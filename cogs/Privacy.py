import discord
from discord.ext import commands

from menus import CustomExecutionButton, CustomSelectMenu
from utils.utils import create_invis_embed


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
                document.get("punishments") if document.get("punishments") is not None else True
            )
            shift_reports_enabled = (
                document.get("shift_reports") if document.get("shift_reports") is not None else True
            )
            ai_enabled = (
                document.get('ai_predictions') if document.get('ai_predictions') is not None else True
            )
            selected = document
        embed = discord.Embed(
            title="<:SettingIcon:1035353776460152892> Notification Settings",
            description=f"*This is where you change user settings of ERM.*\n\n<:ArrowRightW:1035023450592514048> **Punishment Alerts:** `{'Enabled' if punishments_enabled is True else 'Disabled'}` {'<:CheckIcon:1035018951043842088>' if punishments_enabled is True else '<:ErrorIcon:1035000018165321808>'}\n<:ArrowRightW:1035023450592514048> **Shift Reports:** `{'Enabled' if shift_reports_enabled is True else 'Disabled'}` {'<:CheckIcon:1035018951043842088>' if shift_reports_enabled is True else '<:ErrorIcon:1035000018165321808>'}\n<:ArrowRightW:1035023450592514048> **AI Predictions:** `{'Enabled' if ai_enabled is True else 'Disabled'}` {'<:CheckIcon:1035018951043842088>' if ai_enabled is True else '<:ErrorIcon:1035000018165321808>'}",
            color=0x2A2D31,
        ).set_thumbnail(url=ctx.author.display_avatar.url)

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
                embed = discord.Embed(
                    title="<:SettingIcon:1035353776460152892> Notification Settings",
                    description=f"*This is where you change user settings of ERM.*\n\n<:ArrowRightW:1035023450592514048> **Punishment Alerts:** `{'Enabled' if punishments_enabled is True else 'Disabled'}` {'<:CheckIcon:1035018951043842088>' if punishments_enabled is True else '<:ErrorIcon:1035000018165321808>'}\n<:ArrowRightW:1035023450592514048> **Shift Reports:** `{'Enabled' if shift_reports_enabled is True else 'Disabled'}` {'<:CheckIcon:1035018951043842088>' if shift_reports_enabled is True else '<:ErrorIcon:1035000018165321808>'}\n<:ArrowRightW:1035023450592514048> **AI Predictions:** `{'Enabled' if ai_enabled is True else 'Disabled'}` {'<:CheckIcon:1035018951043842088>' if ai_enabled is True else '<:ErrorIcon:1035000018165321808>'}",
                    color=0x2A2D31,
                ).set_thumbnail(url=ctx.author.display_avatar.url)
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
                    embed = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success!",
                        description="<:ArrowRight:1035003246445596774> You have enabled punishment alerts.",
                        color=0x71C15F,
                    )
                    await interaction.edit_original_response(
                        embed=embed, view=None
                    )
                elif view.value == "disable":
                    if selected is None:
                        await bot.consent.insert(
                            {"_id": ctx.author.id, "punishments": False}
                        )
                    else:
                        selected["punishments"] = False
                        await bot.consent.update_by_id(selected)
                    embed = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success!",
                        description="<:ArrowRight:1035003246445596774> You have disabled punishment alerts.",
                        color=0x71C15F,
                    )
                    await interaction.edit_original_response(embed=embed, view=None)

            else:
                await interaction.response.send_message(
                    embed=create_invis_embed(
                        "You are not the individual that has activated this menu. Refrain from interacting with this view."
                    ),
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
                    title="<:SettingIcon:1035353776460152892> Notification Settings",
                    description=f"*This is where you change user settings of ERM.*\n\n<:ArrowRightW:1035023450592514048> **Punishment Alerts:** `{'Enabled' if punishments_enabled is True else 'Disabled'}` {'<:CheckIcon:1035018951043842088>' if punishments_enabled is True else '<:ErrorIcon:1035000018165321808>'}\n<:ArrowRightW:1035023450592514048> **Shift Reports:** `{'Enabled' if shift_reports_enabled is True else 'Disabled'}` {'<:CheckIcon:1035018951043842088>' if shift_reports_enabled is True else '<:ErrorIcon:1035000018165321808>'}\n<:ArrowRightW:1035023450592514048> **AI Predictions:** `{'Enabled' if ai_enabled is True else 'Disabled'}` {'<:CheckIcon:1035018951043842088>' if ai_enabled is True else '<:ErrorIcon:1035000018165321808>'}",
                    color=0x2A2D31,
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
                    embed = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success!",
                        description="<:ArrowRight:1035003246445596774> You have enabled AI Predictions.",
                        color=0x71C15F,
                    )
                    await interaction.edit_original_response(
                        embed=embed, view=None
                    )
                elif view.value == "disable":
                    if selected is None:
                        await bot.consent.insert(
                            {"_id": ctx.author.id, "ai_predictions": False}
                        )
                    else:
                        selected["ai_predictions"] = False
                        await bot.consent.update_by_id(selected)
                    embed = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success!",
                        description="<:ArrowRight:1035003246445596774> You have disabled AI Predictions.",
                        color=0x71C15F,
                    )
                    await interaction.edit_original_response(embed=embed, view=None)

            else:
                await interaction.response.send_message(
                    embed=create_invis_embed(
                        "You are not the individual that has activated this menu. Refrain from interacting with this view."
                    ),
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
                    title="<:SettingIcon:1035353776460152892> Notification Settings",
                    description=f"*This is where you change user settings of ERM.*\n\n<:ArrowRightW:1035023450592514048> **Punishment Alerts:** `{'Enabled' if punishments_enabled is True else 'Disabled'}` {'<:CheckIcon:1035018951043842088>' if punishments_enabled is True else '<:ErrorIcon:1035000018165321808>'}\n<:ArrowRightW:1035023450592514048> **Shift Reports:** `{'Enabled' if shift_reports_enabled is True else 'Disabled'}` {'<:CheckIcon:1035018951043842088>' if shift_reports_enabled is True else '<:ErrorIcon:1035000018165321808>'}\n<:ArrowRightW:1035023450592514048> **AI Predictions:** `{'Enabled' if ai_enabled is True else 'Disabled'}` {'<:CheckIcon:1035018951043842088>' if ai_enabled is True else '<:ErrorIcon:1035000018165321808>'}",
                    color=0x2A2D31,
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
                    embed = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success!",
                        description="<:ArrowRight:1035003246445596774> You have enabled shift reports.",
                        color=0x71C15F,
                    )

                    await interaction.edit_original_response(embed=embed, view=None)


                elif view.value == "disable":
                    if selected is None:
                        await bot.consent.insert(
                            {"_id": ctx.author.id, "shift_reports": False}
                        )
                    else:
                        selected["shift_reports"] = False
                        await bot.consent.update_by_id(selected)
                    embed = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success!",
                        description="<:ArrowRight:1035003246445596774> You have disabled shift reports.",
                        color=0x71C15F,
                    )
                    await interaction.edit_original_response(embed=embed, view=None)


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
                func=punishment_predictions
            )
        ]

        for child in buttons:
            custom_view.add_item(child)

        await ctx.send(embed=embed, view=custom_view)


async def setup(bot):
    await bot.add_cog(Privacy(bot))
