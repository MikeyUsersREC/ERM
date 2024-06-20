import datetime

import discord
import pytz
from discord import app_commands
from discord.ext import commands
import typing
from menus import CustomExecutionButton
from utils.constants import BLANK_COLOR, GREEN_COLOR, RED_COLOR
from erm import is_management
from utils.paginators import SelectPagination, CustomPage
from utils.timestamp import td_format
from utils.utils import require_settings, time_converter, get_elapsed_time, generalised_interaction_check_failure


class ActivityMonitoring(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(
        name="activity",
        description="Monitor activity across an entire Staff Team effectively.",
        extras={"category": "Activity Management"}
    )
    async def activity(self, ctx: commands.Context):
        pass

    @commands.guild_only()
    @activity.command(
        name="show",
        description="Show newest activity monitoring report across a time period.",
        extras={"category": "Activity Management"}
    )
    @is_management()
    @require_settings()
    async def activity_show(self, ctx: commands.Context, duration: str, selected_role: typing.Optional[discord.Role]):

        settings = await self.bot.settings.find_by_id(ctx.guild.id)
        if not settings.get('shift_management').get('enabled'):
            return await ctx.send(
                embed=discord.Embed(
                    title="Not Enabled",
                    description="Shift Logging is not enabled on this server.",
                    color=BLANK_COLOR
                )
            )

        try:
            actual_conversion = time_converter(duration)
        except ValueError:
            return await ctx.send(embed=discord.Embed(
                title="Invalid Time",
                description="This time format is not accepted by ERM. Please seek the documentation for details",
                color=BLANK_COLOR
            ))

        timestamp_pre = datetime.datetime.now(tz=pytz.UTC).timestamp() - actual_conversion
        timestamp_now = datetime.datetime.now(tz=pytz.UTC).timestamp()

        all_staff = {}
        specified_quota_roles = settings.get('shift_management', {}).get('role_quotas', [])

        async for shift_document in self.bot.shift_management.shifts.db.find({
            "Guild": ctx.guild.id,
            "StartEpoch": {"$gt": timestamp_pre},
            "EndEpoch": {"$lt": timestamp_now}
        }):

            shift_time = get_elapsed_time(shift_document)
            if shift_time > 100_000_000:
                continue
            if shift_document['UserID'] not in all_staff.keys():
                try:
                    member = await ctx.guild.fetch_member(shift_document['UserID'])
                except discord.NotFound:
                    continue
                if not member:
                    continue
                roles = member.roles
                if selected_role is not None:
                    if selected_role not in roles:
                        continue
                sorted_roles = sorted(member.roles, key=lambda x: x.position)
                selected_quota = 0
                for role in sorted_roles:
                    # print(role)
                    # print(specified_quota_roles)
                    if role.id in [t['role'] for t in specified_quota_roles]:
                        found_item = [t for t in specified_quota_roles if t['role'] == role.id][0]
                        selected_quota = found_item['quota']


                if selected_quota == 0:
                    selected_quota = settings.get('shift_management').get('quota', 0)
                all_staff[shift_document['UserID']] = [shift_time, selected_quota]
            else:
                all_staff[shift_document['UserID']][0] += shift_time

        if selected_role is not None:
            for item in selected_role.members:
                if item.id not in all_staff.keys():
                    all_staff[item.id] = [0, settings.get('shift_management').get('quota', 0)]

        sorted_all_staff = sorted(all_staff.items(), key= lambda x: x[1], reverse=True)
        # print(sorted_all_staff)
        sorted_staff = dict(zip([item[0] for item in sorted_all_staff], [item[1] for item in sorted_all_staff]))
        # print(sorted_staff)
        leaderboard_string = ""
        loa_string = ""

        for index, (user_id, (seconds, quota)) in enumerate(sorted_staff.items()):
            # print(seconds, quota)
            leaderboard_string += f"**{index+1}.** <@{user_id}> • {td_format(datetime.timedelta(seconds=seconds))} {'<:check:1163142000271429662>' if seconds > quota else '<:xmark:1166139967920164915>'}\n"
            if index == len(sorted_staff)-1:
                break
        else:
            return await ctx.send(
                embed=discord.Embed(
                    title="No Data",
                    description="There is no data to show for this period.",
                    color=BLANK_COLOR
                )
            )
        embeds = []
        embed = discord.Embed(
            title=f"Activity Report ({duration})",
            color=BLANK_COLOR
        )
        embed.description = f"**Leaderboard**\n"
        embed.set_author(
            name=ctx.guild.name,
            icon_url=ctx.guild.icon
        )
        embeds.append(embed)
        for item in leaderboard_string.split('\n'):
            if len(embeds[-1].description.splitlines()) > 9:
                embed = discord.Embed(
                    title=f"Activity Report ({duration})",
                    color=BLANK_COLOR
                )
                embed.set_author(
                    name=ctx.guild.name,
                    icon_url=ctx.guild.icon
                )
                embeds.append(embed)
                embeds[-1].description = f"**Leaderboard**\n"
            embeds[-1].description += f"{item}\n"

        actual_loas = []
        async for loa_item in self.bot.loas.db.find({
            "guild_id": ctx.guild.id
        }):
            starting_epoch = loa_item['_id'].split('_')[2]
            if int(starting_epoch) >= timestamp_pre and loa_item.get('accepted', True):
                loa_item['start_epoch'] = int(starting_epoch)
                actual_loas.append(loa_item)



        async def interaction_callback(interaction: discord.Interaction, _):
            if interaction.user.id != ctx.author.id:
                return await generalised_interaction_check_failure(interaction.response)
            def setup_embed() -> discord.Embed:
                embed = discord.Embed(
                    title="Activity Notices",
                    color=BLANK_COLOR
                )
                embed.set_author(
                    name=ctx.guild.name,
                    icon_url=ctx.guild.icon
                )
                return embed

            embeds = []
            for item in actual_loas:
                if len(embeds) == 0:
                    embeds.append(setup_embed())

                if len(embeds[-1].fields) > 4:
                    embeds.append(setup_embed())

                find_shift_staff = all_staff.get(item['user_id'])

                if find_shift_staff:
                    embeds[-1].add_field(
                        name=f"{item['type']}",
                        value=(
                            f"> **Staff:** <@{item['user_id']}>\n"
                            f"> **Reason:** {item['reason']}\n"
                            f"> **Shift Time:** {td_format(datetime.timedelta(seconds=find_shift_staff[0]))} {'<:check:1163142000271429662>' if seconds > find_shift_staff[1] else '<:xmark:1166139967920164915>'}\n"
                            f"> **Started At:** <t:{int(item['start_epoch'])}>\n"
                            f"> **Ended At:** <t:{int(item['expiry'])}>"
                        ),
                        inline=False
                    )
                else:
                    embeds[-1].add_field(
                        name=f"{item['type']}",
                        value=(
                            f"> **Staff:** <@{item['user_id']}>\n"
                            f"> **Reason:** {item['reason']}\n"
                            f"> **Shift Time:** {td_format(datetime.timedelta(seconds=0))} {'<:check:1163142000271429662>' if seconds > 0 else '<:xmark:1166139967920164915>'}\n"
                            f"> **Started At:** <t:{int(item['start_epoch'])}>\n"
                            f"> **Ended At:** <t:{int(item['expiry'])}>"
                        ),
                        inline=False
                    )
            pages = [
                CustomPage(
                    embeds=[embed],
                    identifier=str(index+1)
                ) for index, embed in enumerate(embeds)
            ]
            paginator = SelectPagination(ctx.author.id, pages=pages)
            await interaction.response.send_message(
                embed=embeds[0],
                view=paginator,
                ephemeral=True
            )


        button = CustomExecutionButton(
            ctx.author.id,
            "View LOAs",
            style=discord.ButtonStyle.secondary,
            func=interaction_callback
        )
        extra_view = discord.ui.View()
        if len(actual_loas) != 0:
            extra_view.add_item(button)

        view = SelectPagination(ctx.author.id, [
            CustomPage(embeds=[embed], view=extra_view, identifier=str(index+1)) for index, embed in enumerate(embeds)
        ])

        await ctx.send(embed=embeds[0], view=view.get_current_view() if len(embeds) > 1 else extra_view)



async def setup(bot):
    await bot.add_cog(ActivityMonitoring(bot))
