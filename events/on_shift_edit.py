import typing

import discord
from bson import ObjectId
from discord.ext import commands
from datamodels.ShiftManagement import ShiftItem
from utils.constants import BLANK_COLOR


class OnShiftEdit(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_shift_edit(
        self,
        object_id: ObjectId,
        edited_attribute: typing.Literal["added_time", "removed_time"],
        editor: discord.Member,
    ):

        document = await self.bot.shift_management.shifts.find_by_id(object_id)
        if not document:
            return
        shift: ShiftItem = await self.bot.shift_management.fetch_shift(object_id)

        guild: discord.Guild = self.bot.get_guild(shift.guild)
        if guild is None:
            return

        guild_settings = await self.bot.settings.find_by_id(guild.id)
        if not guild_settings:
            return

        shift_type = shift.type
        custom_shift_type = None
        if shift_type != "Default":
            total_shift_types = guild_settings.get("shift_types", {"types": []})
            for item in total_shift_types["types"]:
                if item["name"] == shift_type:
                    custom_shift_type = item

        if custom_shift_type is None:
            try:
                channel = await guild.fetch_channel(
                    guild_settings.get("shift_management").get("channel", 0)
                )
            except discord.HTTPException:
                channel = None
        else:
            try:
                channel = await guild.fetch_channel(custom_shift_type.get("channel", 0))
            except discord.HTTPException:
                try:
                    channel = await guild.fetch_channel(
                        guild_settings.get("shift_management").get("channel", 0)
                    )
                except discord.HTTPException:
                    channel = None

        try:
            staff_member: discord.Member = await guild.fetch_member(shift.user_id)
        except discord.NotFound:
            return

        if not staff_member:
            return
        if channel is not None:
            await channel.send(
                embed=discord.Embed(title="Shift Edited", color=BLANK_COLOR)
                .add_field(
                    name="Shift Information",
                    value=(
                        f"> **Staff Member:** {staff_member.mention}\n"
                        f"> **Shift Type:** {shift_type}\n"
                    ),
                    inline=False,
                )
                .add_field(
                    name="Other Information",
                    value=(
                        f"> **Shift Start:** <t:{int(shift.start_epoch)}>\n"
                        f"> **Nickname:** `{shift.nickname}`\n"
                    ),
                    inline=False,
                )
                .add_field(
                    name="Manager Information",
                    value=(
                        f"> **Edited By:** {editor.mention}\n"
                        f"> **Added Time:** `{shift.added_time}`\n"
                        if edited_attribute == "added_time"
                        else f"> **Removed Time:** `{shift.removed_time}`\n"
                    ),
                    inline=False,
                )
                .set_author(
                    name=guild.name, icon_url=guild.icon.url if guild.icon else ""
                )
                .set_thumbnail(url=staff_member.display_avatar.url)
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(OnShiftEdit(bot))
