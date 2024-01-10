import datetime

import discord
from bson import ObjectId
from discord.ext import commands
from datamodels.ShiftManagement import ShiftItem
from utils.constants import BLANK_COLOR
from utils.timestamp import td_format


class OnShiftEnd(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_shift_end(self, object_id: ObjectId):

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
            total_shift_types = guild_settings.get('shift_types', {"types": []})
            for item in total_shift_types['types']:
                if item['name'] == shift_type:
                    custom_shift_type = item

        assigned_roles = []
        if custom_shift_type is None:
            try:
                channel = await guild.fetch_channel(guild_settings.get('shift_management').get('channel', 0))
            except discord.HTTPException:
                channel = None
            nickname_prefix = guild_settings.get('shift_management').get('nickname_prefix', None)
            assigned_roles = guild_settings.get('shift_management').get('role', [])
        else:
            try:
                channel = await guild.fetch_channel(custom_shift_type.get('channel', 0))
            except discord.HTTPException:
                try:
                    channel = await guild.fetch_channel(guild_settings.get('shift_management').get('channel', 0))
                except discord.HTTPException:
                    channel = None
            nickname_prefix = custom_shift_type.get('nickname', None)
            assigned_roles = custom_shift_type.get('role', [])

        try:
            staff_member: discord.Member = await guild.fetch_member(shift.user_id)
        except discord.NotFound:
            return

        if not staff_member:
            return
        for role in (assigned_roles or []):
            discord_role: discord.Role = guild.get_role(role)
            if discord_role is None:
                continue
            try:
                await staff_member.remove_roles(discord_role, atomic=True)
            except discord.HTTPException:
                pass

        if nickname_prefix is not None:
            try:
                await staff_member.edit(nick=f"{(staff_member.nick or staff_member.display_name).removeprefix(nickname_prefix)}")
            except discord.HTTPException:
                pass

        if channel is not None:
            await channel.send(embed=discord.Embed(
                title="Shift Ended",
                color=BLANK_COLOR
            ).add_field(
                name="Shift Information",
                value=(
                    f"> **Staff Member:** {staff_member.mention}\n"
                    f"> **Shift Type:** {shift_type}\n"
                ),
                inline=False
            ).add_field(
                name="Other Information",
                value=(
                    f"> **Shift Start:** <t:{int(shift.start_epoch)}>\n"
                    f"> **Shift End:** <t:{int(shift.end_epoch)}>\n"
                    f"> **Shift Length:** {td_format(datetime.timedelta(seconds=shift.end_epoch - shift.start_epoch - (sum((br.end_epoch) - (br.start_epoch) for br in shift.breaks)) + (shift.added_time if shift.added_time > (86400 * 7) else 0) - (shift.removed_time if shift.removed_time > (86400 * 7) else 0)))}\n"
                    f"> **Nickname:** `{shift.nickname}`\n"
                ),
                inline=False
            ).set_author(
                name=guild.name,
                icon_url=guild.icon.url if guild.icon else ''
            ).set_thumbnail(
                url=staff_member.display_avatar.url
            ))


async def setup(bot: commands.Bot):
    await bot.add_cog(OnShiftEnd(bot))


