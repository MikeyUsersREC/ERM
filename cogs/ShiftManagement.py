import copy
import datetime
from io import BytesIO
from decouple import config
import discord
from discord.ext import commands
from discord import app_commands
from reactionmenu.abc import _PageController
from reactionmenu import ViewMenu, ViewSelect, ViewButton, Page
from erm import is_staff, is_management, management_predicate, credentials_dict, scope
from menus import AdministrativeSelectMenu, CustomSelectMenu, ModificationSelectMenu, RequestGoogleSpreadsheet, \
    YesNoMenu, CustomExecutionButton
from utils.timestamp import td_format
from utils.utils import invis_embed, request_response
import num2words

class ShiftManagement(commands.Cog):
        def __init__(self, bot):
            self.bot = bot

        @commands.hybrid_group(
            name='duty'
        )
        async def duty(self, ctx):
            pass

        @duty.command(
            name="time",
            description="Allows for you to check your shift time, as well as your past data.",
            extras={"category": "Shift Management"},
            with_app_command=True,
        )
        @is_staff()
        async def dutytime(self, ctx, member: discord.Member = None):
            bot = self.bot
            if not member:
                member = ctx.author

            configItem = await bot.settings.find_by_id(ctx.guild.id)
            if configItem is None:
                return await invis_embed(ctx,
                                         'The server has not been set up yet. Please run `/setup` to set up the server.')

            if not configItem['shift_management']['enabled']:
                return await invis_embed(ctx, 'Shift management is not enabled on this server.')
            try:
                shift_channel = discord.utils.get(ctx.guild.channels, id=configItem['shift_management']['channel'])
            except:
                return await invis_embed(ctx,
                                         f'Some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.')

            if not configItem['shift_management']['enabled']:
                return await invis_embed(ctx, 'Shift management is not enabled on this server.')

            embed = discord.Embed(
                title=f"<:staff:1035308057007230976> {member.name}#{member.discriminator}",
                color=0x2e3136
            )

            # Get current shift
            shift = None
            shift_data = await bot.shifts.find_by_id(member.id)
            if shift_data:
                if 'data' in shift_data.keys():
                    if isinstance(shift_data['data'], list):
                        for dataItem in shift_data['data']:
                            if dataItem:
                                if isinstance(dataItem, dict):
                                    if 'guild' in dataItem.keys():
                                        if dataItem['guild'] == ctx.guild.id:
                                            shift = dataItem

            # Get all past shifts
            shifts = []
            storage_item = await bot.shift_storage.find_by_id(member.id)
            if storage_item:
                if storage_item.get('shifts'):
                    if isinstance(storage_item['shifts'], list):
                        for item in storage_item['shifts']:
                            if isinstance(item, dict):
                                if item['guild'] == ctx.guild.id:
                                    shifts.append(item)

            total_seconds = sum([s['totalSeconds'] for s in shifts])

            if shift:
                embed.add_field(
                    name="<:Clock:1035308064305332224> Current Shift Time",
                    value=f"<:ArrowRight:1035003246445596774> {td_format(datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(shift['startTimestamp']))}",
                    inline=False
                )

            embed.add_field(
                name="<:Pause:1035308061679689859> Total Shift Time",
                value=f"<:ArrowRight:1035003246445596774> {td_format(datetime.timedelta(seconds=total_seconds))}"
            )
            await ctx.send(embed=embed)

        @duty.command(
            name="admin",
            description="Allows for you to administrate someone else's shift",
            extras={"category": "Shift Management"}
        )
        @is_management()
        async def duty_admin(self, ctx, member: discord.Member):
            bot = self.bot
            configItem = await bot.settings.find_by_id(ctx.guild.id)
            if configItem is None:
                return await invis_embed(ctx,
                                         'The server has not been set up yet. Please run `/setup` to set up the server.')

            try:
                shift_channel = discord.utils.get(ctx.guild.channels, id=configItem['shift_management']['channel'])
            except:
                return await invis_embed(ctx,
                                         f'Some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.')

            if not configItem['shift_management']['enabled']:
                return await invis_embed(ctx, 'Shift management is not enabled on this server.')

            shift = None
            if await bot.shifts.find_by_id(member.id):
                if 'data' in (await bot.shifts.find_by_id(member.id)).keys():
                    var = (await bot.shifts.find_by_id(member.id))['data']
                    print(var)

                    for item in var:
                        if item['guild'] == ctx.guild.id:
                            parent_item = await bot.shifts.find_by_id(member.id)
                            shift = item
                            has_started = True
                else:
                    if 'guild' in (await bot.shifts.find_by_id(member.id)).keys():
                        if (await bot.shifts.find_by_id(member.id))['guild'] == ctx.guild.id:
                            shift = (await bot.shifts.find_by_id(member.id))
                            has_started = True

            if not shift:
                has_started = False
            print(shift)
            view = AdministrativeSelectMenu(ctx.author.id)

            embed = discord.Embed(
                color=0x2E3136,
                title=f"<:Clock:1035308064305332224> {member.name}#{member.discriminator}'s Shift Panel"
            )

            quota_seconds = None
            met_quota = None
            member_seconds = 0
            ordinal_place = None
            ordinal_formatted = None
            shift_type = None

            if 'quota' in configItem['shift_management'].keys():
                quota_seconds = configItem['shift_management']['quota']

            all_staff = [{"id": None, "total_seconds": 0, "quota_seconds": 0}]

            datetime_obj = datetime.datetime.utcnow()
            ending_period = datetime_obj
            starting_period = datetime_obj - datetime.timedelta(days=7)

            async for document in bot.shift_storage.db.find({"shifts": {"$elemMatch": {"guild": ctx.guild.id}}}):
                total_seconds = 0
                quota_seconds = 0
                for shift_doc in document['shifts']:
                    if isinstance(shift_doc, dict):
                        if shift_doc['guild'] == ctx.guild.id:
                            total_seconds += int(shift_doc['totalSeconds'])
                            print(shift_doc)
                            if shift_doc['startTimestamp'] >= starting_period.timestamp():
                                quota_seconds += int(shift_doc['totalSeconds'])

                if document['_id'] not in [item['id'] for item in all_staff]:
                    all_staff.append({"id": document['_id'], "total_seconds": total_seconds,
                                      "quota_seconds": quota_seconds})
                else:
                    for item in all_staff:
                        if item['id'] == document['_id']:
                            item['total_seconds'] = total_seconds
                            item['quota_seconds'] = quota_seconds

            if len(all_staff) == 0:
                return await invis_embed(ctx, 'No shifts were made in your server.')
            for item in all_staff:
                if item['id'] is None:
                    all_staff.remove(item)

            sorted_staff = sorted(all_staff, key=lambda x: x['total_seconds'], reverse=True)

            for index, value in enumerate(sorted_staff):
                m = discord.utils.get(ctx.guild.members, id=value['id'])
                if m:
                    if m.id == member.id:
                        member_seconds = value['total_seconds']
                        if quota_seconds is not None:
                            if value['total_seconds'] > quota_seconds:
                                met_quota = "Met "
                            else:
                                met_quota = "Not met"
                            ordinal_place = index + 1
                        else:
                            met_quota = "Not met"
                            ordinal_place = index + 1

            ordinal = lambda n: "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])  # NOQA: E731
            ms_delta = datetime.timedelta(seconds=member_seconds)

            if ordinal_place is not None:
                ordinal_formatted = ordinal(ordinal_place)

            if td_format(ms_delta) != "":
                embed.add_field(
                    name="<:Search:1035353785184288788> Previous Shift Data",
                    value=f"<:ArrowRight:1035003246445596774>{td_format(ms_delta)}\n<:ArrowRight:1035003246445596774>{met_quota} Quota\n<:ArrowRight:1035003246445596774>{ordinal_formatted} Place for Shift Time",
                    inline=False
                )
            status = None

            print(shift)
            if shift:
                if 'on_break' in shift.keys():
                    if shift['on_break']:
                        status = "break"
                    else:
                        status = "on"
                else:
                    status = "on"
            else:
                status = "off"

            embed.add_field(
                name="<:Setup:1035006520817090640> Shift Management",
                value=f"<:CurrentlyOnDuty:1045079678353932398> **On-Duty** {'(Current)' if status == 'on' else ''}\n<:Break:1045080685012062329> **On-Break** {'(Current)' if status == 'break' else ''}\n<:OffDuty:1045081161359183933> **Off-Duty** {'(Current)' if status == 'off' else ''}",
            )

            doc = [doc async for doc in bot.shifts.db.find({'data': {'$elemMatch': {'guild': ctx.guild.id}}})]
            currently_active = len(doc)

            if status == "on" or status == "break":
                warnings = 0
                kicks = 0
                bans = 0
                ban_bolos = 0
                custom = 0
                if 'moderations' in shift.keys():
                    for item in shift['moderations']:
                        if item["Type"] == "Warning":
                            warnings += 1
                        elif item["Type"] == "Kick":
                            kicks += 1
                        elif item["Type"] == "Ban" or item['Type'] == "Temporary Ban":
                            bans += 1
                        elif item["Type"] == "BOLO":
                            ban_bolos += 1
                        else:
                            custom += 1

                if 'type' in shift.keys():
                    if shift['type']:
                        raw_shift_type: int = shift['type']
                        settings = await bot.settings.find_by_id(ctx.guild.id)
                        shift_types = settings.get('shift_types')
                        shift_types = shift_types.get('types') if shift_types.get('types') not in [None, []] else []
                        if shift_types:
                            sh_typelist = [item for item in shift_types if item['id'] == raw_shift_type]
                            if len(sh_typelist) > 0:
                                shift_type = sh_typelist[0]
                            else:
                                shift_type = {
                                    'name': 'Unknown',
                                    'id': 0,
                                    'role': settings['shift_management'].get('role')
                                }
                        else:
                            shift_type = {
                                'name': 'Default',
                                'id': 0,
                                'role': settings['shift_management'].get('role')
                            }
                    else:
                        shift_type = None
                else:
                    shift_type = None

                if shift_type:
                    if shift_type.get('channel'):
                        temp_shift_channel = discord.utils.get(ctx.guild.channels, id=shift_type.get('channel'))
                        if temp_shift_channel:
                            shift_channel = temp_shift_channel

                print(datetime.datetime.fromtimestamp(shift['startTimestamp']))
                time_delta = datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(
                    shift['startTimestamp'])

                time_delta += datetime.timedelta(seconds=sum(shift.get('added_time'))) if shift.get(
                    'added_time') is not None else datetime.timedelta(seconds=0)
                time_delta -= datetime.timedelta(seconds=sum(shift.get('removed_time'))) if shift.get(
                    'removed_time') is not None else datetime.timedelta(seconds=0)

                embed2 = discord.Embed(
                    title=f"<:Clock:1035308064305332224> {member.name}#{member.discriminator}'s Current Shift",
                    color=0x2E3136
                )

                embed2.add_field(
                    name="<:Search:1035353785184288788> Moderation Details",
                    value="<:ArrowRight:1035003246445596774> {} Warnings\n<:ArrowRight:1035003246445596774> {} Kicks\n<:ArrowRight:1035003246445596774> {} Bans\n<:ArrowRight:1035003246445596774> {} Ban BOLOs\n<:ArrowRight:1035003246445596774> {} Custom".format(
                        warnings, kicks, bans, ban_bolos, custom),
                    inline=False
                )

                break_seconds = 0
                if 'breaks' in shift.keys():
                    for item in shift['breaks']:
                        if item['ended']:
                            break_seconds += item['ended'] - item['started']
                        else:
                            break_seconds += datetime.datetime.utcnow().timestamp() - item['started']

                break_seconds = int(break_seconds)

                doc = [doc async for doc in bot.shifts.db.find({'data': {'$elemMatch': {'guild': ctx.guild.id}}})]
                currently_active = len(doc)

                if shift_type:
                    embed2.add_field(
                        name="<:Setup:1035006520817090640> Shift Status",
                        value=f"<:ArrowRight:1035003246445596774> {'On-Duty' if status == 'on' else 'On-Break'} {'<:CurrentlyOnDuty:1045079678353932398>' if status == 'on' else '<:Break:1045080685012062329>'}\n<:ArrowRight:1035003246445596774> {td_format(time_delta)} on shift\n<:ArrowRight:1035003246445596774> {len(shift['breaks']) if 'breaks' in shift.keys() else '0'} breaks\n<:ArrowRight:1035003246445596774> {td_format(datetime.timedelta(seconds=break_seconds)) if td_format(datetime.timedelta(seconds=break_seconds)) != '' else '0 seconds'} on break\n<:ArrowRight:1035003246445596774> Current Shift Type: **{shift_type['name']}**",
                    )
                else:
                    embed2.add_field(
                        name="<:Setup:1035006520817090640> Shift Status",
                        value=f"<:ArrowRight:1035003246445596774> {'On-Duty' if status == 'on' else 'On-Break'} {'<:CurrentlyOnDuty:1045079678353932398>' if status == 'on' else '<:Break:1045080685012062329>'}\n<:ArrowRight:1035003246445596774> {td_format(time_delta)} on shift\n<:ArrowRight:1035003246445596774> {len(shift['breaks']) if 'breaks' in shift.keys() else '0'} breaks\n<:ArrowRight:1035003246445596774> {td_format(datetime.timedelta(seconds=break_seconds)) if td_format(datetime.timedelta(seconds=break_seconds)) != '' else '0 seconds'} on break\n<:ArrowRight:1035003246445596774> Current Shift Type: **Default**",
                    )

                embed2.set_footer(text=f"Currently online staff: {currently_active}")
                msg = await ctx.send(embeds=[embed, embed2], view=view)
            else:
                embed.set_footer(text=f"Currently online staff: {currently_active}")
                msg = await ctx.send(embed=embed, view=view)
            timeout = await view.wait()
            if timeout:
                return

            if view.value == "on":
                if status == "on":
                    return await invis_embed(ctx,
                                             f"{member.name}#{member.discriminator} is already on-duty. You can force them off-duty by selecting **Off-Duty**.")
                elif status == "break":
                    for item in shift['breaks']:
                        if item['ended'] is None:
                            item['ended'] = ctx.message.created_at.replace(tzinfo=None).timestamp()
                    for data in parent_item['data']:
                        if shift['startTimestamp'] == data['startTimestamp'] and shift['guild'] == data['guild']:
                            data['breaks'] = shift['breaks']
                            data['on_break'] = False
                            break
                    await bot.shifts.update_by_id(parent_item)

                    if shift_type:
                        if shift_type.get('role'):
                            if isinstance(shift.type.get('role'), list):
                                role = [discord.utils.get(ctx.guild.roles, id=role) for role in shift_type.get('role')]
                            else:
                                role = [discord.utils.get(ctx.guild.roles,
                                                          id=shift_type.get('role'))]
                    else:
                        if shift_type:
                            if shift_type.get('role'):
                                role = [discord.utils.get(ctx.guild.roles, id=role) for role
                                        in shift_type.get('role')]
                        else:
                            if configItem['shift_management']['role']:
                                if not isinstance(configItem['shift_management']['role'],
                                                  list):
                                    role = [discord.utils.get(ctx.guild.roles, id=
                                    configItem['shift_management']['role'])]
                                else:
                                    role = [discord.utils.get(ctx.guild.roles, id=role) for
                                            role in
                                            configItem['shift_management']['role']]
                    if role:
                        for rl in role:
                            if rl not in ctx.author.roles and rl is not None:
                                try:
                                    await ctx.author.add_roles(rl)
                                except:
                                    await invis_embed(ctx,
                                                      f'Could not add {rl} to {ctx.author.mention}')

                    success = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Break Ended",
                        description=f"<:ArrowRight:1035003246445596774> {member.name}#{member.discriminator} is no longer on break.",
                        color=0x71c15f
                    )
                    await msg.edit(embed=success, view=None)
                else:
                    settings = await bot.settings.find_by_id(ctx.guild.id)
                    shift_type = None

                    maximum_staff = settings['shift_management'].get('maximum_staff')
                    if maximum_staff not in [None, 0]:
                        if (currently_active + 1) > maximum_staff:
                            return await invis_embed(ctx,
                                                     f"Sorry, but the maximum amount of staff that can be on-duty at once is {maximum_staff}. Ask your server administration for more details.")

                    if settings.get('shift_types'):
                        if len(settings['shift_types'].get('types') or []) > 1 and settings['shift_types'].get(
                                'enabled') is True:
                            embed = discord.Embed(
                                title="<:Clock:1035308064305332224> Shift Types",
                                description=f"<:ArrowRight:1035003246445596774> You have {num2words.num2words(len(settings['shift_types']['types']))} shift types, {', '.join([f'`{i}`' for i in [item['name'] for item in settings['shift_types']['types']]])}. Select one of these options.",
                                color=0x2e3136
                            )
                            v = CustomSelectMenu(ctx.author.id, [
                                discord.SelectOption(label=item['name'], value=item['id'], description=item['name'],
                                                     emoji='<:Clock:1035308064305332224>') for item in
                                settings['shift_types']['types']
                            ])
                            await msg.edit(embed=embed, view=v)
                            timeout = await v.wait()
                            if timeout:
                                return
                            if v.value:
                                shift_type = [item for item in settings['shift_types']['types'] if
                                              item['id'] == int(v.value)]
                                if len(shift_type) == 1:
                                    shift_type = shift_type[0]
                                else:
                                    return await invis_embed(ctx,
                                                             'Something went wrong in the shift type selection. If you experience this error, please contact [ERM Support[(https://discord.gg/FAC629TzBy).')
                            else:
                                return
                        else:
                            if settings['shift_types'].get('enabled') is True and len(
                                    settings['shift_types'].get('types')) > 0:
                                shift_type = settings['shift_types']['types'][0]
                            else:
                                shift_type = None
                    nickname_prefix = None
                    changed_nick = False

                    if shift_type:
                        if shift_type.get('nickname'):
                            nickname_prefix = shift_type.get('nickname')
                    else:
                        if configItem['shift_management'].get('nickname'):
                            nickname_prefix = configItem['shift_management'].get('nickname')

                    if nickname_prefix:
                        current_name = member.nick if member.nick else member.name
                        new_name = "{}{}".format(nickname_prefix, current_name)

                        try:
                            await member.edit(nick=new_name)
                            changed_nick = True
                        except Exception as e:
                            print(e)
                            pass

                    try:
                        if changed_nick:
                            await bot.shifts.insert({
                                '_id': member.id,
                                'name': member.name,
                                'data': [
                                    {
                                        "guild": ctx.guild.id,
                                        "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                        "type": None if not shift_type else shift_type['id'],
                                        "nickname": {
                                            "old": current_name,
                                            "new": new_name
                                        }
                                    }
                                ]
                            })
                        else:
                            await bot.shifts.insert({
                                '_id': member.id,
                                'name': member.name,
                                'data': [
                                    {
                                        "guild": ctx.guild.id,
                                        "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                        "type": None if not shift_type else shift_type['id']
                                    }
                                ]
                            })
                    except:
                        if await bot.shifts.find_by_id(member.id):
                            shift = await bot.shifts.find_by_id(member.id)
                            if 'data' in shift.keys():
                                newData = shift['data']
                                if changed_nick:
                                    newData.append({
                                        "guild": ctx.guild.id,
                                        "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                        "type": None if not shift_type else shift_type['id'],
                                        "nickname": {
                                            "old": current_name,
                                            "new": new_name
                                        }
                                    })
                                else:
                                    newData.append({
                                        "guild": ctx.guild.id,
                                        "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                        "type": None if not shift_type else shift_type['id']
                                    })
                                await bot.shifts.update_by_id({
                                    '_id': member.id,
                                    'name': member.name,
                                    'data': newData
                                })
                            elif 'data' not in shift.keys():
                                if changed_nick:
                                    await bot.shifts.update_by_id({
                                        '_id': member.id,
                                        'name': member.name,
                                        'data': [
                                            {
                                                "guild": ctx.guild.id,
                                                "startTimestamp": ctx.message.created_at.replace(
                                                    tzinfo=None).timestamp(),
                                            },
                                            {
                                                "guild": shift['guild'],
                                                "startTimestamp": shift['startTimestamp'],
                                                "type": shift['type'] if 'type' in shift.keys() else None,
                                                "nicknames": {
                                                    "old": current_name,
                                                    "new": new_name
                                                }
                                            }
                                        ]
                                    })
                                else:
                                    await bot.shifts.update_by_id({
                                        '_id': member.id,
                                        'name': member.name,
                                        'data': [
                                            {
                                                "guild": ctx.guild.id,
                                                "startTimestamp": ctx.message.created_at.replace(
                                                    tzinfo=None).timestamp(),
                                            },
                                            {
                                                "guild": shift['guild'],
                                                "startTimestamp": shift['startTimestamp'],
                                                "type": shift['type'] if 'type' in shift.keys() else None
                                            }
                                        ]
                                    })
                    successEmbed = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success",
                        description=f"<:ArrowRight:1035003246445596774>  {member.name}#{member.discriminator}'s shift is now active.",
                        color=0x71c15f
                    )

                    role = None

                    if shift_type:
                        if shift_type.get('role'):
                            role = [discord.utils.get(ctx.guild.roles, id=role) for role in shift_type.get('role')]
                    else:
                        if configItem['shift_management']['role']:
                            if not isinstance(configItem['shift_management']['role'], list):
                                role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
                            else:
                                role = [discord.utils.get(ctx.guild.roles, id=role) for role in
                                        configItem['shift_management']['role']]

                    if role:
                        for rl in role:
                            if not rl in member.roles and rl is not None:
                                try:
                                    await member.add_roles(rl)
                                except:
                                    await invis_embed(ctx, f'Could not add {rl} to {member.mention}')

                    embed = discord.Embed(title=member.name, color=0x2E3136)
                    try:
                        embed.set_thumbnail(url=member.display_avatar.url)
                        embed.set_footer(text="Staff Logging Module")
                    except:
                        pass

                    if shift_type:
                        embed.add_field(name="<:MalletWhite:1035258530422341672> Type",
                                        value=f"<:ArrowRight:1035003246445596774> Clocking in. **({shift_type['name']})**",
                                        inline=False)
                    else:
                        embed.add_field(name="<:MalletWhite:1035258530422341672> Type",
                                        value="<:ArrowRight:1035003246445596774> Clocking in.", inline=False)
                    embed.add_field(name="<:Clock:1035308064305332224> Current Time",
                                    value=f"<:ArrowRight:1035003246445596774> <t:{int(ctx.message.created_at.timestamp())}>",
                                    inline=False)

                    await shift_channel.send(embed=embed)
                    await msg.edit(embed=successEmbed, view=None)
            elif view.value == "off":
                break_seconds = 0
                if shift:
                    if 'breaks' in shift.keys():
                        for item in shift["breaks"]:
                            if item['ended'] == None:
                                item['ended'] = ctx.message.created_at.replace(tzinfo=None).timestamp()
                            startTimestamp = item['started']
                            endTimestamp = item['ended']
                            break_seconds += int(endTimestamp - startTimestamp)
                else:
                    return await invis_embed(ctx,
                                             f"{member.name}#{member.discriminator} is not on-duty. You can force them on-duty by selecting **On-Duty**.")
                if status == "off":
                    return await invis_embed(ctx,
                                             f"{member.name}#{member.discriminator} is already off-duty. You can force them on-duty by selecting **On-Duty**.")

                embed = discord.Embed(
                    title=member.name,
                    color=0x2E3136
                )

                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text='Staff Logging Module')

                if shift.get('type'):
                    embed.add_field(name="<:MalletWhite:1035258530422341672> Type",
                                    value=f"<:ArrowRight:1035003246445596774> Clocking out. **({shift_type['name']})**",
                                    inline=False)
                else:
                    embed.add_field(name="<:MalletWhite:1035258530422341672> Type",
                                    value="<:ArrowRight:1035003246445596774> Clocking out.", inline=False)

                time_delta = ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
                    shift['startTimestamp']).replace(tzinfo=None)

                time_delta = time_delta - datetime.timedelta(seconds=break_seconds)

                added_seconds = 0
                removed_seconds = 0
                if 'added_time' in shift.keys():
                    for added in shift['added_time']:
                        added_seconds += added

                if 'removed_time' in shift.keys():
                    for removed in shift['removed_time']:
                        removed_seconds += removed

                try:
                    time_delta = time_delta + datetime.timedelta(seconds=added_seconds)
                    time_delta = time_delta - datetime.timedelta(seconds=removed_seconds)
                except OverflowError:
                    await invis_embed(ctx,
                                      f"{member.mention}'s added or removed time has been voided due to it being an unfeasibly massive numeric value. If you find a vulnerability in ERM, please report it via our Support Server.")

                if break_seconds > 0:
                    embed.add_field(
                        name="<:Clock:1035308064305332224> Elapsed Time",
                        value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)} ({td_format(datetime.timedelta(seconds=break_seconds))} on break)",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="<:Clock:1035308064305332224> Elapsed Time",
                        value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)}",
                        inline=False
                    )

                successEmbed = discord.Embed(
                    title="<:CheckIcon:1035018951043842088> Shift Ended",
                    description=f"<:ArrowRight:1035003246445596774> {member.name}#{member.discriminator}'s shift has now ended.",
                    color=0x71c15f
                )

                await msg.edit(embed=successEmbed, view=None)

                await shift_channel.send(embed=embed)

                embed = discord.Embed(title="<:MalletWhite:1035258530422341672> Shift Report",
                                      description="*This is the report for the shift you just ended, it goes over moderations you made during your shift, and any other information that may be useful.*",
                                      color=0x2e3136)

                moderations = len(shift.get('moderations') if shift.get('moderations') else [])
                synced_moderations = len(
                    [moderation for moderation in (shift.get('moderations') if shift.get('moderations') else []) if
                     moderation.get('synced')])

                moderation_list = shift.get('moderations') if shift.get('moderations') else []
                synced_moderation_list = [moderation for moderation in
                                          (shift.get('moderations') if shift.get('moderations') else []) if
                                          moderation.get('synced')]

                embed.set_author(
                    name=f"You have made {moderations} moderations during your shift.",
                    icon_url="https://cdn.discordapp.com/emojis/1035258528149033090.webp?size=96&quality=lossless"
                )

                embed.add_field(
                    name="<:Clock:1035308064305332224> Elapsed Time",
                    value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)} ({td_format(datetime.timedelta(seconds=break_seconds))} on break)",
                    inline=False
                )

                embed.add_field(
                    name="<:Search:1035353785184288788> Total Moderations",
                    value=f"<:ArrowRightW:1035023450592514048> **Warnings:** {len([moderation for moderation in moderation_list if moderation['Type'].lower() == 'warning'])}\n<:ArrowRightW:1035023450592514048> **Kicks:** {len([moderation for moderation in moderation_list if moderation['Type'].lower() == 'kick'])}\n<:ArrowRightW:1035023450592514048> **Bans:** {len([moderation for moderation in moderation_list if moderation['Type'].lower() == 'ban'])}\n<:ArrowRightW:1035023450592514048> **BOLO:** {len([moderation for moderation in moderation_list if moderation['Type'].lower() == 'bolo'])}\n<:ArrowRightW:1035023450592514048> **Custom:** {len([moderation for moderation in moderation_list if moderation['Type'].lower() not in ['warning', 'kick', 'ban', 'bolo']])}",
                    inline=False
                )
                dm_channel = (await member.create_dm())
                # dm_msg = await dm_channel.send(
                #     embed=create_invis_embed(
                #         'Your Shift Report is being generated. Please wait up to 5 seconds for complete generation.')
                # )
                new_ctx = copy.copy(ctx)
                new_ctx.guild = None
                new_ctx.channel = dm_channel

                menu = ViewMenu(new_ctx, menu_type=ViewMenu.TypeEmbed, timeout=None)
                menu.add_page(embed)

                moderation_embed = discord.Embed(title="<:MalletWhite:1035258530422341672> Shift Report",
                                                 description="*This is the report for the shift just ended, it goes over moderations you made during your shift, and any other information that may be useful.*",
                                                 color=0x2e3136)

                moderation_embed.set_author(
                    name=f"You have made {moderations} moderations during your shift.",
                    icon_url="https://cdn.discordapp.com/emojis/1035258528149033090.webp?size=96&quality=lossless"
                )

                moderation_embeds = []
                moderation_embeds.append(moderation_embed)
                print('9867')

                for moderation in moderation_list:
                    if len(moderation_embeds[-1].fields) >= 10:
                        moderation_embeds.append(discord.Embed(title="<:MalletWhite:1035258530422341672> Shift Report",
                                                               description="*This is the report for the shift you just ended, it goes over moderations you made during your shift, and any other information that may be useful.*",
                                                               color=0x2e3136))

                        moderation_embeds[-1].set_author(
                            name=f"You have made {moderations} moderations during your shift.",
                            icon_url="https://cdn.discordapp.com/emojis/1035258528149033090.webp?size=96&quality=lossless"
                        )

                    moderation_embeds[-1].add_field(
                        name=f"<:WarningIcon:1035258528149033090> {moderation['Type'].title()}",
                        value=f"<:ArrowRightW:1035023450592514048> **ID:** {moderation['id']}\n<:ArrowRightW:1035023450592514048> **Type:** {moderation['Type']}\n<:ArrowRightW:1035023450592514048> **Reason:** {moderation['Reason']}\n<:ArrowRightW:1035023450592514048> **Time:** <t:{int(datetime.datetime.strptime(moderation['Time'], '%m/%d/%Y, %H:%M:%S').timestamp()) if isinstance(moderation['Time'], str) else int(moderation['Time'])}>\n<:ArrowRightW:1035023450592514048> **Synced:** {str(moderation.get('synced')) if moderation.get('synced') else 'False'}",
                        inline=False
                    )

                synced_moderation_embed = discord.Embed(title="<:MalletWhite:1035258530422341672> Shift Report",
                                                        description="*This is the report for the shift you just ended, it goes over moderations you made during your shift, and any other information that may be useful.*",
                                                        color=0x2e3136)

                synced_moderation_embed.set_author(
                    name=f"You have made {synced_moderations} synced moderations during your shift.",
                    icon_url="https://cdn.discordapp.com/emojis/1071821068551073892.webp?size=128&quality=lossless"
                )

                synced_moderation_embeds = []
                synced_moderation_embeds.append(moderation_embed)
                print('9895')

                for moderation in synced_moderation_list:
                    if len(synced_moderation_embeds[-1].fields) >= 10:
                        moderation_embeds.append(discord.Embed(title="<:MalletWhite:1035258530422341672> Shift Report",
                                                               description="*This is the report for the shift that just ended, it goes over moderations you made during your shift, and any other information that may be useful.*",
                                                               color=0x2e3136))

                        synced_moderation_embeds[-1].set_author(
                            name=f"You have made {synced_moderations} synced moderations during your shift.",
                            icon_url="https://cdn.discordapp.com/emojis/1071821068551073892.webp?size=128&quality=lossless"
                        )

                    synced_moderation_embeds[-1].add_field(
                        name=f"<:WarningIcon:1035258528149033090> {moderation['Type'].title()}",
                        value=f"<:ArrowRightW:1035023450592514048> **ID:** {moderation['id']}\n<:ArrowRightW:1035023450592514048> **Type:** {moderation['Type']}\n<:ArrowRightW:1035023450592514048> **Reason:** {moderation['Reason']}\n<:ArrowRightW:1035023450592514048> **Time:** <t:{int(datetime.datetime.strptime(moderation['Time'], '%m/%d/%Y, %H:%M:%S').timestamp()) if isinstance(moderation['Time'], str) else int(moderation['Time'])}>",
                        inline=False
                    )

                time_embed = discord.Embed(title="<:MalletWhite:1035258530422341672> Shift Report",
                                           description="*This is the report for the shift just ended, it goes over moderations you made during your shift, and any other information that may be useful.*",
                                           color=0x2e3136)

                time_embed.set_author(
                    name=f"You were on-shift for {td_format(time_delta)}.",
                    icon_url="https://cdn.discordapp.com/emojis/1035308064305332224.webp?size=128&quality=lossless")
                print('9919')

                time_embed.add_field(
                    name="<:Resume:1035269012445216858> Shift Start",
                    value=f"<:ArrowRight:1035003246445596774> <t:{int(shift['startTimestamp'])}>",
                    inline=False
                )

                time_embed.add_field(
                    name="<:ArrowRightW:1035023450592514048> Shift End",
                    value=f"<:ArrowRight:1035003246445596774> <t:{int(datetime.datetime.now().timestamp())}>",
                    inline=False
                )

                time_embed.add_field(
                    name="<:SConductTitle:1053359821308567592> Added Time",
                    value=f"<:ArrowRight:1035003246445596774> {td_format(datetime.timedelta(seconds=added_seconds))}",
                    inline=False
                )

                time_embed.add_field(
                    name="<:FlagIcon:1035258525955395664> Removed Time",
                    value=f"<:ArrowRight:1035003246445596774> {td_format(datetime.timedelta(seconds=removed_seconds))}",
                    inline=False
                )

                time_embed.add_field(
                    name="<:LinkIcon:1044004006109904966> Total Time",
                    value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)}",
                    inline=False
                )

                menu.add_select(ViewSelect(title="Shift Report", options={
                    discord.SelectOption(label="Moderations", emoji="<:MalletWhite:1035258530422341672>",
                                         description="View all of your moderations during this shift"): [
                        Page(embed=embed) for
                        embed in
                        moderation_embeds],
                    discord.SelectOption(label="Synced Moderations", emoji="<:SyncIcon:1071821068551073892>",
                                         description="View all of your synced moderations during this shift"): [
                        Page(embed=embed) for embed in synced_moderation_embeds],
                    discord.SelectOption(label="Shift Time", emoji="<:Clock:1035308064305332224>",
                                         description="View your shift time"): [Page(embed=time_embed)]

                }))

                menu.add_button(ViewButton.back())
                menu.add_button(ViewButton.next())
                try:
                    if consent_obj := await ctx.bot.consent.find_by_id(ctx.author.id):
                        if consent_obj.get('shift_reports'):
                            if consent_obj.get('shift_reports') is False:
                                raise Exception()
                    await menu.start()
                except:
                    pass
                print('9960')

                if shift.get('nickname'):
                    if shift['nickname']['new'] == member.display_name:
                        try:
                            await member.edit(nick=shift['nickname']['old'])
                        except Exception as e:
                            print(e)
                            pass

                if not await bot.shift_storage.find_by_id(member.id):
                    await bot.shift_storage.insert({
                        '_id': member.id,
                        'shifts': [
                            {
                                'name': member.name,
                                'startTimestamp': shift['startTimestamp'],
                                'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                'totalSeconds': time_delta.total_seconds(),
                                'guild': ctx.guild.id,
                                'moderations': shift['moderations'] if 'moderations' in shift.keys() else [],
                                'type': shift['type'] if 'type' in shift.keys() else None,
                            }],
                        'totalSeconds': time_delta.total_seconds()

                    })
                else:
                    data = await bot.shift_storage.find_by_id(member.id)

                    if "shifts" in data.keys():
                        if data['shifts'] is None:
                            data['shifts'] = []

                        if data['shifts'] == []:
                            shifts = [
                                {
                                    'name': member.name,
                                    'startTimestamp': shift['startTimestamp'],
                                    'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                    'totalSeconds': time_delta.total_seconds(),
                                    'guild': ctx.guild.id,
                                    'moderations': shift['moderations'] if 'moderations' in shift.keys() else [],
                                    'type': shift['type'] if 'type' in shift.keys() else None,
                                }
                            ]
                        else:
                            object = {
                                'name': member.name,
                                'startTimestamp': shift['startTimestamp'],
                                'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                'totalSeconds': time_delta.total_seconds(),
                                'guild': ctx.guild.id,
                                'moderations': shift['moderations'] if 'moderations' in shift.keys() else [],
                                'type': shift['type'] if 'type' in shift.keys() else None,
                            }
                            shiftdata = data['shifts']
                            shifts = shiftdata + [object]

                        await bot.shift_storage.update_by_id(
                            {
                                '_id': member.id,
                                'shifts': shifts,
                                'totalSeconds': sum(
                                    [shifts[i]['totalSeconds'] for i in range(len(shifts)) if shifts[i] is not None])
                            }
                        )
                        await bot.shift_storage.update_by_id({
                            '_id': member.id,
                            'shifts': [
                                {
                                    'name': member.name,
                                    'startTimestamp': shift['startTimestamp'],
                                    'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                    'totalSeconds': time_delta.total_seconds(),
                                    'guild': ctx.guild.id,
                                    'moderations': shift['moderations'] if 'moderations' in shift.keys() else [],
                                    'type': shift['type'] if 'type' in shift.keys() else None,
                                }],
                            'totalSeconds': time_delta.total_seconds()

                        })
                    else:
                        pass

                if await bot.shifts.find_by_id(member.id):
                    dataShift = await bot.shifts.find_by_id(member.id)
                    if 'data' in dataShift.keys():
                        if isinstance(dataShift['data'], list):
                            for item in dataShift['data']:
                                if item['guild'] == ctx.guild.id:
                                    dataShift['data'].remove(item)
                                    break
                    await bot.shifts.update_by_id(dataShift)

                role = None
                if shift_type:
                    if shift_type.get('role'):
                        role = [discord.utils.get(ctx.guild.roles, id=role) for role in shift_type.get('role')]
                else:
                    if configItem['shift_management']['role']:
                        if not isinstance(configItem['shift_management']['role'], list):
                            role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
                        else:
                            role = [discord.utils.get(ctx.guild.roles, id=role) for role in
                                    configItem['shift_management']['role']]

                if role:
                    for rl in role:
                        if rl in member.roles and rl is not None:
                            try:
                                await member.remove_roles(rl)
                            except:
                                await invis_embed(ctx, f'Could not remove {rl} from {member.mention}')
            elif view.value == "break":
                if status == "off":
                    return await invis_embed(ctx,
                                             f'{member.name}#{member.discriminator} cannot be on break if they are not currently on-duty. If you would like them to be on-duty, select **On-Duty**')
                toggle = "on"

                if 'breaks' in shift.keys():
                    for item in shift['breaks']:
                        if item['ended'] is None:
                            toggle = "off"

                if toggle == "on":
                    if 'breaks' in shift.keys():
                        shift['breaks'].append({
                            'started': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                            'ended': None
                        })
                    else:
                        shift['breaks'] = [{
                            'started': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                            'ended': None
                        }]
                    shift['on_break'] = True
                    for data in parent_item['data']:
                        if shift['startTimestamp'] == data['startTimestamp'] and shift['guild'] == data['guild']:
                            data['breaks'] = shift['breaks']
                            data['on_break'] = True
                            break
                    await bot.shifts.update_by_id(parent_item)
                    success = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Break Started",
                        description="<:ArrowRight:1035003246445596774> You are now on break.",
                        color=0x71c15f
                    )
                    await msg.edit(embed=success, view=None)

                    if shift_type:
                        if shift_type.get('role'):
                            role = [discord.utils.get(ctx.guild.roles, id=role) for role in shift_type.get('role')]
                    else:
                        if configItem['shift_management']['role']:
                            if not isinstance(configItem['shift_management']['role'], list):
                                role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
                            else:
                                role = [discord.utils.get(ctx.guild.roles, id=role) for role in
                                        configItem['shift_management']['role']]

                    if role:
                        for rl in role:
                            if rl in member.roles and rl is not None:
                                try:
                                    await member.remove_roles(rl)
                                except:
                                    await invis_embed(ctx, f'Could not remove {rl} from {member.mention}')

                else:
                    for item in shift['breaks']:
                        if item['ended'] is None:
                            item['ended'] = ctx.message.created_at.replace(tzinfo=None).timestamp()
                    for data in parent_item['data']:
                        if shift['startTimestamp'] == data['startTimestamp'] and shift['guild'] == data['guild']:
                            data['breaks'] = shift['breaks']
                            data['on_break'] = False
                            break
                    await bot.shifts.update_by_id(parent_item)
                    success = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Break Ended",
                        description="<:ArrowRight:1035003246445596774> You are no longer on break.",
                        color=0x71c15f
                    )
                    await msg.edit(embed=success, view=None)
                    if shift_type:
                        if shift_type.get('role'):
                            role = [discord.utils.get(ctx.guild.roles, id=role) for role in shift_type.get('role')]
                    else:
                        if configItem['shift_management']['role']:
                            if not isinstance(configItem['shift_management']['role'], list):
                                role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
                            else:
                                role = [discord.utils.get(ctx.guild.roles, id=role) for role in
                                        configItem['shift_management']['role']]

                    if role:
                        for rl in role:
                            if not rl in member.roles and rl is not None:
                                try:
                                    await member.add_roles(rl)
                                except:
                                    await invis_embed(ctx, f'Could not add {rl} to {member.mention}')

            if view.admin_value:
                if view.admin_value == "add":
                    if not has_started:
                        try:
                            await bot.shifts.insert({
                                '_id': member.id,
                                'name': member.name,
                                'data': [
                                    {
                                        "guild": ctx.guild.id,
                                        "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                    }
                                ]
                            })
                            print('1')
                        except:
                            if await bot.shifts.find_by_id(member.id):
                                shift = await bot.shifts.find_by_id(member.id)
                                if 'data' in shift.keys():
                                    newData = shift['data']
                                    newData.append({
                                        "guild": ctx.guild.id,
                                        "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                    })
                                    await bot.shifts.update_by_id({
                                        '_id': member.id,
                                        'name': member.name,
                                        'data': newData
                                    })
                                    print('2')
                                elif 'data' not in shift.keys():
                                    await bot.shifts.update_by_id({
                                        '_id': member.id,
                                        'name': member.name,
                                        'data': [
                                            {
                                                "guild": ctx.guild.id,
                                                "startTimestamp": ctx.message.created_at.replace(
                                                    tzinfo=None).timestamp(),
                                            },
                                            {
                                                "guild": shift['guild'],
                                                "startTimestamp": shift['startTimestamp'],

                                            }
                                        ]
                                    })
                                    print('3')
                        shift = {
                            "guild": ctx.guild.id,
                            "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                        }

                    timestamp = shift['startTimestamp']
                    print('Timestamp: ', timestamp)
                    content = (
                        await request_response(bot, ctx,
                                               "How much time would you like to add to the shift? (s/m/h/d)")).content
                    content = content.strip()
                    if content.endswith(('s', 'm', 'h', 'd')):
                        full = None
                        if content.endswith('s'):
                            full = "seconds"
                            num = int(content[:-1])
                            if shift.get('added_time'):
                                shift['added_time'].append(num)
                            else:
                                shift['added_time'] = [num]
                            print('seconds')
                        if content.endswith('m'):
                            full = "minutes"
                            num = int(content[:-1])
                            if shift.get('added_time'):
                                shift['added_time'].append(num * 60)
                            else:
                                shift['added_time'] = [num * 60]
                            print('minutes')
                        if content.endswith('h'):
                            full = "hours"
                            num = int(content[:-1])
                            if shift.get('added_time'):
                                shift['added_time'].append(num * 60 * 60)
                            else:
                                shift['added_time'] = [num * 60 * 60]
                            print('hours')
                        if content.endswith('d'):
                            full = "days"
                            num = int(content[:-1])
                            if shift.get('added_time'):
                                shift['added_time'].append(num * 60 * 60 * 24)
                            else:
                                shift['added_time'] = [num * 60 * 60 * 24]
                            print('days')
                        if has_started:
                            if await bot.shifts.find_by_id(member.id):
                                dataShift = await bot.shifts.find_by_id(member.id)
                                if 'data' in dataShift.keys():
                                    if isinstance(dataShift['data'], list):
                                        for index, item in enumerate(dataShift['data']):
                                            if item['guild'] == ctx.guild.id:
                                                dataShift['data'][index] = shift
                                        await bot.shifts.update_by_id(dataShift)
                                else:
                                    await bot.shifts.update_by_id(shift)
                        successEmbed = discord.Embed(
                            title="<:CheckIcon:1035018951043842088> Added time",
                            description=f"<:ArrowRight:1035003246445596774> **{num} {full}** have been added to {member.display_name}'s shift.",
                            color=0x71c15f
                        )

                        await ctx.send(embed=successEmbed)
                    else:
                        return await invis_embed(ctx, "Invalid time format. (e.g. 120m)")

                if view.admin_value == "remove":
                    if not has_started:
                        try:
                            await bot.shifts.insert({
                                '_id': member.id,
                                'name': member.name,
                                'data': [
                                    {
                                        "guild": ctx.guild.id,
                                        "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                    }
                                ]
                            })
                        except:
                            if await bot.shifts.find_by_id(member.id):
                                shift = await bot.shifts.find_by_id(member.id)
                                if 'data' in shift.keys():
                                    newData = shift['data']
                                    newData.append({
                                        "guild": ctx.guild.id,
                                        "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                    })
                                    await bot.shifts.update_by_id({
                                        '_id': member.id,
                                        'name': member.name,
                                        'data': newData
                                    })
                                elif 'data' not in shift.keys():
                                    await bot.shifts.update_by_id({
                                        '_id': member.id,
                                        'name': member.name,
                                        'data': [
                                            {
                                                "guild": ctx.guild.id,
                                                "startTimestamp": ctx.message.created_at.replace(
                                                    tzinfo=None).timestamp(),
                                            },
                                            {
                                                "guild": shift['guild'],
                                                "startTimestamp": shift['startTimestamp'],

                                            }
                                        ]
                                    })
                        shift = {
                            "guild": ctx.guild.id,
                            "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                        }

                    timestamp = shift['startTimestamp']
                    dT = datetime.datetime.fromtimestamp(timestamp)
                    content = (
                        await request_response(bot, ctx,
                                               "How much time would you like to remove from the shift? (s/m/h/d)")).content
                    content = content.strip()
                    if content.endswith(('s', 'm', 'h', 'd')):
                        full = None
                        if content.endswith('s'):
                            full = "seconds"
                            num = int(content[:-1])
                            if shift.get('removed_time'):
                                shift['removed_time'].append(num)
                            else:
                                shift['removed_time'] = [num]
                        if content.endswith('m'):
                            full = "minutes"
                            num = int(content[:-1])
                            if shift.get('removed_time'):
                                shift['removed_time'].append(num * 60)
                            else:
                                shift['removed_time'] = [num * 60]
                        if content.endswith('h'):
                            full = "hours"
                            num = int(content[:-1])
                            if shift.get('removed_time'):
                                shift['removed_time'].append(num * 60 * 60)
                            else:
                                shift['removed_time'] = [num * 60 * 60]
                        if content.endswith('d'):
                            full = "days"
                            num = int(content[:-1])
                            if shift.get('removed_time'):
                                shift['removed_time'].append(num * 60 * 60 * 24)
                            else:
                                shift['removed_time'] = [num * 60 * 60 * 24]

                        if has_started:
                            if await bot.shifts.find_by_id(member.id):
                                dataShift = await bot.shifts.find_by_id(member.id)
                                if 'data' in dataShift.keys():
                                    if isinstance(dataShift['data'], list):
                                        for index, item in enumerate(dataShift['data']):
                                            if item['guild'] == ctx.guild.id:
                                                dataShift['data'][index] = shift
                                        await bot.shifts.update_by_id(dataShift)
                                else:
                                    await bot.shifts.update_by_id(shift)
                        successEmbed = discord.Embed(
                            title="<:CheckIcon:1035018951043842088> Removed time",
                            description=f"<:ArrowRight:1035003246445596774> **{num} {full}** have been removed from {member.display_name}'s shift.",
                            color=0x71c15f
                        )

                        await ctx.send(embed=successEmbed)

                    else:
                        return await invis_embed(ctx, "Invalid time format. (e.g. 120m)")

                if view.admin_value == "void":
                    if not has_started:
                        return await invis_embed(ctx,
                                                 "This user has not started a shift yet. You cannot void a shift that has not started.")
                    embed = discord.Embed(
                        title=f"{member.name}#{member.discriminator}",
                        color=0x2E3136
                    )

                    try:
                        embed.set_thumbnail(url=member.display_avatar.url)
                    except:
                        pass
                    embed.add_field(
                        name="<:MalletWhite:1035258530422341672> Type",
                        value=f"<:ArrowRight:1035003246445596774> Voided time, performed by ({ctx.author.display_name})",
                        inline=False
                    )

                    embed.add_field(
                        name="<:Clock:1035308064305332224> Elapsed Time",
                        value=f"<:ArrowRight:1035003246445596774> {td_format(ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(shift['startTimestamp']))}",
                        inline=False
                    )

                    successEmbed = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Shift Voided",
                        description="<:ArrowRight:1035003246445596774> Shift has been voided successfully.",
                        color=0x71c15f
                    )

                    embed.set_footer(text='Staff Logging Module')

                    if await bot.shifts.find_by_id(member.id):
                        dataShift = await bot.shifts.find_by_id(member.id)
                        if 'data' in dataShift.keys():
                            if isinstance(dataShift['data'], list):
                                for item in dataShift['data']:
                                    if item['guild'] == ctx.guild.id:
                                        dataShift['data'].remove(item)
                                        break
                            await bot.shifts.update_by_id(dataShift)
                        else:
                            await bot.shifts.delete_by_id(dataShift)

                    await shift_channel.send(embed=embed)
                    await msg.edit(embed=successEmbed, view=None)
                    role = None
                    if shift_type:
                        if shift_type.get('role'):
                            role = [discord.utils.get(ctx.guild.roles, id=role) for role in shift_type.get('role')]
                    else:
                        if configItem['shift_management']['role']:
                            if not isinstance(configItem['shift_management']['role'], list):
                                role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
                            else:
                                role = [discord.utils.get(ctx.guild.roles, id=role) for role in
                                        configItem['shift_management']['role']]

                    if role:
                        for rl in role:
                            if rl in member.roles and rl is not None:
                                try:
                                    await member.remove_roles(rl)
                                except:
                                    await invis_embed(ctx, f'Could not remove {rl} from {member.mention}')

                if view.admin_value == "clear":
                    document = await bot.shift_storage.find_by_id(member.id)
                    if 'shifts' in document.keys():
                        for shift in document['shifts'].copy():
                            if isinstance(shift, dict):
                                if shift['guild'] == ctx.guild.id:
                                    document['shifts'].remove(shift)
                        await bot.shift_storage.db.replace_one({'_id': document['_id']}, document)

                    successEmbed = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success!",
                        description=f"<:ArrowRight:1035003246445596774> {member.display_name}'s shifts in your server have been cleared.",
                        color=0x71c15f
                    )
                    await msg.edit(embed=successEmbed, view=None)
                if not has_started:
                    if view.admin_value in ["add", "remove"]:
                        time_delta = ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
                            shift['startTimestamp']).replace(tzinfo=None)

                        if shift.get('removed_time'):
                            time_delta -= datetime.timedelta(seconds=sum(shift['removed_time']))

                        if shift.get('added_time'):
                            time_delta += datetime.timedelta(seconds=sum(shift['added_time']))

                        if not await bot.shift_storage.find_by_id(member.id):
                            await bot.shift_storage.insert({
                                '_id': member.id,
                                'shifts': [
                                    {
                                        'name': member.name,
                                        'startTimestamp': shift['startTimestamp'],
                                        'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                        'totalSeconds': time_delta.total_seconds(),
                                        'guild': ctx.guild.id,
                                        'moderations': shift['moderations'] if 'moderations' in shift.keys() else [],
                                    }],
                                'totalSeconds': time_delta.total_seconds()

                            })
                        else:
                            data = await bot.shift_storage.find_by_id(member.id)

                            if "shifts" in data.keys():
                                if data['shifts'] is None:
                                    data['shifts'] = []

                                if data['shifts'] == []:
                                    shifts = [
                                        {
                                            'name': member.name,
                                            'startTimestamp': shift['startTimestamp'],
                                            'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                            'totalSeconds': time_delta.total_seconds(),
                                            'guild': ctx.guild.id
                                        }
                                    ]
                                else:
                                    object = {
                                        'name': member.name,
                                        'startTimestamp': shift['startTimestamp'],
                                        'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                        'totalSeconds': time_delta.total_seconds(),
                                        'guild': ctx.guild.id,
                                        'moderations': shift['moderations'] if 'moderations' in shift.keys() else [],
                                    }
                                    shiftdata = data['shifts']
                                    shifts = shiftdata + [object]

                                await bot.shift_storage.update_by_id(
                                    {
                                        '_id': member.id,
                                        'shifts': shifts,
                                        'totalSeconds': sum(
                                            [shifts[i]['totalSeconds'] for i in range(len(shifts)) if
                                             shifts[i] is not None])
                                    }
                                )
                            else:
                                await bot.shift_storage.update_by_id({
                                    '_id': member.id,
                                    'shifts': [
                                        {
                                            'name': member.name,
                                            'startTimestamp': shift['startTimestamp'],
                                            'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                            'totalSeconds': time_delta.total_seconds(),
                                            'guild': ctx.guild.id,
                                            'moderations': shift[
                                                'moderations'] if 'moderations' in shift.keys() else [],
                                        }],
                                    'totalSeconds': time_delta.total_seconds()

                                })

                        if await bot.shifts.find_by_id(member.id):
                            dataShift = await bot.shifts.find_by_id(member.id)
                            if 'data' in dataShift.keys():
                                if isinstance(dataShift['data'], list):
                                    for item in dataShift['data']:
                                        if item['guild'] == ctx.guild.id:
                                            dataShift['data'].remove(item)
                                            break
                                await bot.shifts.update_by_id(dataShift)
                            else:
                                await bot.shifts.delete_by_id(dataShift)
                        role = None
                        if shift_type:
                            if shift_type.get('role'):
                                role = [discord.utils.get(ctx.guild.roles, id=role) for role in shift_type.get('role')]
                        else:
                            if configItem['shift_management']['role']:
                                if not isinstance(configItem['shift_management']['role'], list):
                                    role = [
                                        discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
                                else:
                                    role = [discord.utils.get(ctx.guild.roles, id=role) for role in
                                            configItem['shift_management']['role']]

                        if role:
                            for rl in role:
                                if rl in member.roles and rl is not None:
                                    try:
                                        await member.remove_roles(rl)
                                    except:
                                        await invis_embed(ctx, f'Could not remove {rl} from {member.mention}')


        @duty.command(
            name="manage",
            description="Manage your own shift in an easy way!",
            extras={"category": "Shift Management"},
        )
        @is_staff()
        async def manage(self, ctx):
            bot = self.bot
            configItem = await bot.settings.find_by_id(ctx.guild.id)
            if configItem is None:
                return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

            try:
                shift_channel = discord.utils.get(ctx.guild.channels, id=configItem['shift_management']['channel'])
            except:
                return await invis_embed(ctx,
                                         f'Some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.')

            if not configItem['shift_management']['enabled']:
                return await invis_embed(ctx, 'Shift management is not enabled on this server.')

            shift = None
            if await bot.shifts.find_by_id(ctx.author.id):
                if 'data' in (await bot.shifts.find_by_id(ctx.author.id)).keys():
                    var = (await bot.shifts.find_by_id(ctx.author.id))['data']
                    print(var)

                    for item in var:
                        if item['guild'] == ctx.guild.id:
                            parent_item = await bot.shifts.find_by_id(ctx.author.id)
                            shift = item
                else:
                    if 'guild' in (await bot.shifts.find_by_id(ctx.author.id)).keys():
                        if (await bot.shifts.find_by_id(ctx.author.id))['guild'] == ctx.guild.id:
                            shift = (await bot.shifts.find_by_id(ctx.author.id))
            print(shift)
            view = ModificationSelectMenu(ctx.author.id)

            embed = discord.Embed(
                color=0x2E3136,
                title=f"<:Clock:1035308064305332224> {ctx.author.name}#{ctx.author.discriminator}'s Shift Panel"
            )

            quota_seconds = None
            met_quota = None
            member_seconds = 0
            ordinal_place = None
            ordinal_formatted = None

            if 'quota' in configItem['shift_management'].keys():
                quota_seconds = configItem['shift_management']['quota']

            all_staff = [{"id": None, "total_seconds": 0, "quota_seconds": 0}]

            datetime_obj = datetime.datetime.utcnow()
            ending_period = datetime_obj
            starting_period = datetime_obj - datetime.timedelta(days=7)

            async for document in bot.shift_storage.db.find({"shifts": {"$elemMatch": {"guild": ctx.guild.id}}}):
                total_seconds = 0
                quota_seconds = 0
                for shift_doc in document['shifts']:
                    if isinstance(shift_doc, dict):
                        if shift_doc['guild'] == ctx.guild.id:
                            total_seconds += int(shift_doc['totalSeconds'])
                            if shift_doc['startTimestamp'] >= starting_period.timestamp():
                                quota_seconds += int(shift_doc['totalSeconds'])
                                if document['_id'] not in [item['id'] for item in all_staff]:
                                    all_staff.append({"id": document['_id'], "total_seconds": total_seconds,
                                                      "quota_seconds": quota_seconds})
                                else:
                                    for item in all_staff:
                                        if item['id'] == document['_id']:
                                            item['total_seconds'] = total_seconds
                                            item['quota_seconds'] = quota_seconds
                            else:
                                if document['_id'] not in [item['id'] for item in all_staff]:
                                    all_staff.append({'id': document['_id'], 'total_seconds': total_seconds})
                                else:
                                    for item in all_staff:
                                        if item['id'] == document['_id']:
                                            item['total_seconds'] = total_seconds

            if len(all_staff) == 0:
                return await invis_embed(ctx, 'No shifts were made in your server.')
            for item in all_staff:
                if item['id'] is None:
                    all_staff.remove(item)

            sorted_staff = sorted(all_staff, key=lambda x: x['total_seconds'], reverse=True)

            for index, value in enumerate(sorted_staff):
                member = discord.utils.get(ctx.guild.members, id=value['id'])
                if member:
                    if member.id == ctx.author.id:
                        member_seconds = value['total_seconds']
                        if quota_seconds is not None:
                            if value['total_seconds'] > quota_seconds:
                                met_quota = "Met "
                            else:
                                met_quota = "Not met"
                            ordinal_place = index + 1
                        else:
                            met_quota = "Not met"
                            ordinal_place = index + 1

            ordinal = lambda n: "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])  # NOQA: E731
            ms_delta = datetime.timedelta(seconds=member_seconds)

            if ordinal_place is not None:
                ordinal_formatted = ordinal(ordinal_place)

            if td_format(ms_delta) != "":
                embed.add_field(
                    name="<:Search:1035353785184288788> Previous Shift Data",
                    value=f"<:ArrowRight:1035003246445596774>{td_format(ms_delta)}\n<:ArrowRight:1035003246445596774>{met_quota} Quota\n<:ArrowRight:1035003246445596774>{ordinal_formatted} Place for Shift Time",
                    inline=False
                )
            status = None

            print(shift)
            if shift:
                if 'on_break' in shift.keys():
                    if shift['on_break']:
                        status = "break"
                    else:
                        status = "on"
                else:
                    status = "on"
            else:
                status = "off"

            embed.add_field(
                name="<:Setup:1035006520817090640> Shift Management",
                value=f"<:CurrentlyOnDuty:1045079678353932398> **On-Duty** {'(Current)' if status == 'on' else ''}\n<:Break:1045080685012062329> **On-Break** {'(Current)' if status == 'break' else ''}\n<:OffDuty:1045081161359183933> **Off-Duty** {'(Current)' if status == 'off' else ''}",
            )

            doc = [doc async for doc in bot.shifts.db.find({'data': {'$elemMatch': {'guild': ctx.guild.id}}})]
            currently_active = len(doc)

            if status == "on" or status == "break":
                warnings = 0
                kicks = 0
                bans = 0
                ban_bolos = 0
                custom = 0
                if 'moderations' in shift.keys():
                    for item in shift['moderations']:
                        if item["Type"] == "Warning":
                            warnings += 1
                        elif item["Type"] == "Kick":
                            kicks += 1
                        elif item["Type"] == "Ban" or item['Type'] == "Temporary Ban":
                            bans += 1
                        elif item["Type"] == "BOLO":
                            ban_bolos += 1
                        else:
                            custom += 1

                if 'type' in shift.keys():
                    if shift['type']:
                        raw_shift_type: int = shift['type']
                        settings = await bot.settings.find_by_id(ctx.guild.id)
                        shift_types = settings.get('shift_types')
                        shift_types = shift_types.get('types') if shift_types.get('types') is not None else []
                        if shift_types:
                            sh_typelist = [item for item in shift_types if item['id'] == raw_shift_type]
                            if len(sh_typelist) > 0:
                                shift_type = sh_typelist[0]
                            else:
                                shift_type = {
                                    'name': 'Unknown',
                                    'id': 0,
                                    'role': settings['shift_management'].get('role')
                                }
                        else:
                            shift_type = {
                                'name': 'Default',
                                'id': 0,
                                'role': settings['shift_management'].get('role')
                            }
                    else:
                        shift_type = None
                else:
                    shift_type = None

                if shift_type:
                    if shift_type.get('channel'):
                        temp_shift_channel = discord.utils.get(ctx.guild.channels, id=shift_type['channel'])
                        if temp_shift_channel is not None:
                            shift_channel = temp_shift_channel

                print(datetime.datetime.fromtimestamp(shift['startTimestamp']))
                time_delta = datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(
                    shift['startTimestamp'])

                embed2 = discord.Embed(
                    title=f"<:Clock:1035308064305332224> {ctx.author.name}#{ctx.author.discriminator}'s Current Shift",
                    color=0x2E3136
                )

                embed2.add_field(
                    name="<:Search:1035353785184288788> Moderation Details",
                    value="<:ArrowRight:1035003246445596774> {} Warnings\n<:ArrowRight:1035003246445596774> {} Kicks\n<:ArrowRight:1035003246445596774> {} Bans\n<:ArrowRight:1035003246445596774> {} Ban BOLOs\n<:ArrowRight:1035003246445596774> {} Custom".format(
                        warnings, kicks, bans, ban_bolos, custom),
                    inline=False
                )

                break_seconds = 0
                if 'breaks' in shift.keys():
                    for item in shift['breaks']:
                        if item['ended']:
                            break_seconds += item['ended'] - item['started']
                        else:
                            break_seconds += datetime.datetime.utcnow().timestamp() - item['started']

                break_seconds = int(break_seconds)

                doc = [doc async for doc in bot.shifts.db.find({'data': {'$elemMatch': {'guild': ctx.guild.id}}})]
                currently_active = len(doc)

                if shift_type:
                    embed2.add_field(
                        name="<:Setup:1035006520817090640> Shift Status",
                        value=f"<:ArrowRight:1035003246445596774> {'On-Duty' if status == 'on' else 'On-Break'} {'<:CurrentlyOnDuty:1045079678353932398>' if status == 'on' else '<:Break:1045080685012062329>'}\n<:ArrowRight:1035003246445596774> {td_format(time_delta)} on shift\n<:ArrowRight:1035003246445596774> {len(shift['breaks']) if 'breaks' in shift.keys() else '0'} breaks\n<:ArrowRight:1035003246445596774> {td_format(datetime.timedelta(seconds=break_seconds)) if td_format(datetime.timedelta(seconds=break_seconds)) != '' else '0 seconds'} on break\n<:ArrowRight:1035003246445596774> Current Shift Type: **{shift_type['name']}**",
                    )
                else:
                    embed2.add_field(
                        name="<:Setup:1035006520817090640> Shift Status",
                        value=f"<:ArrowRight:1035003246445596774> {'On-Duty' if status == 'on' else 'On-Break'} {'<:CurrentlyOnDuty:1045079678353932398>' if status == 'on' else '<:Break:1045080685012062329>'}\n<:ArrowRight:1035003246445596774> {td_format(time_delta)} on shift\n<:ArrowRight:1035003246445596774> {len(shift['breaks']) if 'breaks' in shift.keys() else '0'} breaks\n<:ArrowRight:1035003246445596774> {td_format(datetime.timedelta(seconds=break_seconds)) if td_format(datetime.timedelta(seconds=break_seconds)) != '' else '0 seconds'} on break\n<:ArrowRight:1035003246445596774> Current Shift Type: **Default**",
                    )

                embed2.set_footer(text=f"Currently online staff: {currently_active}")
                msg = await ctx.send(embeds=[embed, embed2], view=view)
            else:
                embed.set_footer(text=f"Currently online staff: {currently_active}")
                msg = await ctx.send(embed=embed, view=view)
            await view.wait()
            if not view.value:
                return

            if view.value == "on":
                if status == "on":
                    return await invis_embed(ctx, "You are already on-duty. You can go off-duty by selecting **Off-Duty**.")
                elif status == "break":
                    for item in shift['breaks']:
                        if item['ended'] is None:
                            item['ended'] = ctx.message.created_at.replace(tzinfo=None).timestamp()
                    for data in parent_item['data']:
                        if shift['startTimestamp'] == data['startTimestamp'] and shift['guild'] == data['guild']:
                            data['breaks'] = shift['breaks']
                            data['on_break'] = False
                            break
                    await bot.shifts.update_by_id(parent_item)
                    role = None
                    if shift_type:
                        if shift_type.get('role'):
                            if isinstance(shift_type.get('role'), list):
                                role = [discord.utils.get(ctx.guild.roles,
                                                          id=rl) for rl in shift_type.get('role')]
                            else:
                                role = [discord.utils.get(ctx.guild.roles, id=shift_type.get('role'))]
                    else:
                        if configItem['shift_management']['role']:
                            if not isinstance(configItem['shift_management']['role'],
                                              list):
                                role = [discord.utils.get(ctx.guild.roles, id=
                                configItem['shift_management']['role'])] or []
                            else:
                                role = [discord.utils.get(ctx.guild.roles, id=role) for
                                        role in
                                        configItem['shift_management']['role']]
                    if role:
                        for rl in role:
                            if rl not in ctx.author.roles and rl is not None:
                                try:
                                    await ctx.author.add_roles(rl)
                                except:
                                    await invis_embed(ctx, f'Could not add {rl} to {ctx.author.mention}')

                    success = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Break Ended",
                        description="<:ArrowRight:1035003246445596774> You are no longer on break.",
                        color=0x71c15f
                    )
                    await msg.edit(embed=success, view=None)
                else:

                    settings = await bot.settings.find_by_id(ctx.guild.id)
                    shift_type = None

                    maximum_staff = settings['shift_management'].get('maximum_staff')
                    if maximum_staff not in [None, 0]:
                        if (currently_active + 1) > maximum_staff:
                            return await invis_embed(ctx,
                                                     f"Sorry, but the maximum amount of staff that can be on-duty at once is {maximum_staff}. Ask your server administration for more details.")

                    if settings.get('shift_types'):
                        if len(settings['shift_types'].get('types') or []) > 1 and settings['shift_types'].get(
                                'enabled') is True:
                            embed = discord.Embed(
                                title="<:Clock:1035308064305332224> Shift Types",
                                description=f"<:ArrowRight:1035003246445596774> You have {num2words.num2words(len(settings['shift_types']['types']))} shift types, {', '.join([f'`{i}`' for i in [item['name'] for item in settings['shift_types']['types']]])}. Select one of these options.",
                                color=0x2e3136
                            )
                            view = CustomSelectMenu(ctx.author.id, [
                                discord.SelectOption(label=item['name'], value=item['id'], description=item['name'],
                                                     emoji='<:Clock:1035308064305332224>') for item in
                                settings['shift_types']['types']
                            ])
                            await msg.edit(embed=embed, view=view)
                            timeout = await view.wait()
                            if timeout:
                                return
                            if view.value:
                                shift_type = [item for item in settings['shift_types']['types'] if
                                              item['id'] == int(view.value)]
                                if len(shift_type) == 1:
                                    shift_type = shift_type[0]
                                else:
                                    return await invis_embed(ctx,
                                                             'Something went wrong in the shift type selection. If you experience this error, please contact [ERM Support[(https://discord.gg/FAC629TzBy).')
                            else:
                                return
                        else:
                            if settings['shift_types'].get('enabled') is True and len(
                                    settings['shift_types'].get('types') or []) == 1:
                                shift_type = settings['shift_types']['types'][0]
                            else:
                                shift_type = None

                    nickname_prefix = None
                    changed_nick = False
                    if shift_type:
                        if shift_type.get('nickname'):
                            nickname_prefix = shift_type.get('nickname')
                    else:
                        if configItem['shift_management'].get('nickname'):
                            nickname_prefix = configItem['shift_management'].get('nickname')

                    if nickname_prefix:
                        current_name = ctx.author.nick if ctx.author.nick else ctx.author.name
                        new_name = "{}{}".format(nickname_prefix, current_name)

                        try:
                            await ctx.author.edit(nick=new_name)
                            changed_nick = True
                        except Exception as e:
                            print(e)
                            pass

                    try:
                        if shift_type:
                            if changed_nick:
                                await bot.shifts.insert({
                                    '_id': ctx.author.id,
                                    'name': ctx.author.name,
                                    'data': [
                                        {
                                            "guild": ctx.guild.id,
                                            "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                            "type": shift_type['id'],
                                            "nickname": {
                                                "old": current_name,
                                                "new": new_name
                                            }
                                        }
                                    ]
                                })
                            else:
                                await bot.shifts.insert({
                                    '_id': ctx.author.id,
                                    'name': ctx.author.name,
                                    'data': [
                                        {
                                            "guild": ctx.guild.id,
                                            "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                            "type": shift_type['id']
                                        }
                                    ]
                                })
                        else:
                            if changed_nick:
                                await bot.shifts.insert({
                                    '_id': ctx.author.id,
                                    'name': ctx.author.name,
                                    'data': [
                                        {
                                            "guild": ctx.guild.id,
                                            "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                            "nickname": {
                                                "old": current_name,
                                                "new": new_name
                                            }
                                        }
                                    ]
                                })
                            else:
                                await bot.shifts.insert({
                                    '_id': ctx.author.id,
                                    'name': ctx.author.name,
                                    'data': [
                                        {
                                            "guild": ctx.guild.id,
                                            "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp()
                                        }
                                    ]
                                })
                    except:
                        if await bot.shifts.find_by_id(ctx.author.id):
                            shift = await bot.shifts.find_by_id(ctx.author.id)
                            if 'data' in shift.keys():
                                if shift_type:
                                    newData = shift['data']
                                    if changed_nick:
                                        newData.append({
                                            "guild": ctx.guild.id,
                                            "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                            "type": shift_type['id'],
                                            "nickname": {
                                                "new": new_name,
                                                "old": current_name
                                            }
                                        })
                                    else:
                                        newData.append({
                                            "guild": ctx.guild.id,
                                            "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                            "type": shift_type['id']
                                        })
                                    await bot.shifts.update_by_id({
                                        '_id': ctx.author.id,
                                        'name': ctx.author.name,
                                        'data': newData
                                    })
                                else:
                                    newData = shift['data']
                                    if changed_nick:
                                        newData.append({
                                            "guild": ctx.guild.id,
                                            "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                            "nickname": {
                                                "old": current_name,
                                                "new": new_name
                                            }
                                        })
                                    else:
                                        newData.append({
                                            "guild": ctx.guild.id,
                                            "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                        })
                                    await bot.shifts.update_by_id({
                                        '_id': ctx.author.id,
                                        'name': ctx.author.name,
                                        'data': newData
                                    })
                            elif 'data' not in shift.keys():
                                if shift_type:
                                    if changed_nick:
                                        await bot.shifts.update_by_id({
                                            '_id': ctx.author.id,
                                            'name': ctx.author.name,
                                            'data': [
                                                {
                                                    "guild": ctx.guild.id,
                                                    "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                                    "type": shift_type['id'],
                                                    "nickname": {
                                                        "old": current_name,
                                                        "new": new_name
                                                    }
                                                },
                                                {
                                                    "guild": shift['guild'],
                                                    "startTimestamp": shift['startTimestamp'],

                                                }
                                            ]
                                        })
                                    else:
                                        await bot.shifts.update_by_id({
                                            '_id': ctx.author.id,
                                            'name': ctx.author.name,
                                            'data': [
                                                {
                                                    "guild": ctx.guild.id,
                                                    "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                                    "type": shift_type['id']
                                                },
                                                {
                                                    "guild": shift['guild'],
                                                    "startTimestamp": shift['startTimestamp'],

                                                }
                                            ]
                                        })
                                else:
                                    if changed_nick:
                                        await bot.shifts.update_by_id({
                                            '_id': ctx.author.id,
                                            'name': ctx.author.name,
                                            'data': [
                                                {
                                                    "guild": ctx.guild.id,
                                                    "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                                    "nickname": {
                                                        "old": current_name,
                                                        "new": new_name
                                                    }
                                                },
                                                {
                                                    "guild": shift['guild'],
                                                    "startTimestamp": shift['startTimestamp'],

                                                }
                                            ]
                                        })
                                    else:
                                        await bot.shifts.update_by_id({
                                            '_id': ctx.author.id,
                                            'name': ctx.author.name,
                                            'data': [
                                                {
                                                    "guild": ctx.guild.id,
                                                    "startTimestamp": ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                                },
                                                {
                                                    "guild": shift['guild'],
                                                    "startTimestamp": shift['startTimestamp'],

                                                }
                                            ]
                                        })
                    successEmbed = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success",
                        description="<:ArrowRight:1035003246445596774> Your shift is now active.",
                        color=0x71c15f
                    )

                    role = None

                    if shift_type:
                        if shift_type.get('role'):
                            if isinstance(shift_type.get('role'), list):
                                role = [discord.utils.get(ctx.guild.roles,
                                                          id=rl) for rl in shift_type.get('role')]
                            else:
                                role = [discord.utils.get(ctx.guild.roles, id=shift_type.get('role'))]
                    else:
                        if configItem['shift_management']['role']:
                            if not isinstance(configItem['shift_management']['role'],
                                              list):
                                role = [discord.utils.get(ctx.guild.roles, id=
                                configItem['shift_management']['role'])]
                            else:
                                role = [discord.utils.get(ctx.guild.roles, id=role) for
                                        role in
                                        configItem['shift_management']['role']]
                    if role:
                        for rl in role:
                            if rl not in ctx.author.roles and rl is not None:
                                try:
                                    await ctx.author.add_roles(rl)
                                except:
                                    await invis_embed(ctx,
                                                      f'Could not add {rl} to {ctx.author.mention}')

                    embed = discord.Embed(title=ctx.author.name, color=0x2E3136)
                    try:
                        embed.set_thumbnail(url=ctx.author.display_avatar.url)
                        embed.set_footer(text="Staff Logging Module")
                    except:
                        pass

                    if shift_type:
                        embed.add_field(name="<:MalletWhite:1035258530422341672> Type",
                                        value=f"<:ArrowRight:1035003246445596774> Clocking in. **({shift_type['name']})**",
                                        inline=False)
                    else:
                        embed.add_field(name="<:MalletWhite:1035258530422341672> Type",
                                        value="<:ArrowRight:1035003246445596774> Clocking in.", inline=False)
                    embed.add_field(name="<:Clock:1035308064305332224> Current Time",
                                    value=f"<:ArrowRight:1035003246445596774> <t:{int(ctx.message.created_at.timestamp())}>",
                                    inline=False)

                    await shift_channel.send(embed=embed)
                    await msg.edit(embed=successEmbed, view=None)
            elif view.value == "off":
                break_seconds = 0
                if shift:
                    if 'breaks' in shift.keys():
                        for item in shift["breaks"]:
                            if item['ended'] == None:
                                item['ended'] = ctx.message.created_at.replace(tzinfo=None).timestamp()
                            startTimestamp = item['started']
                            endTimestamp = item['ended']
                            break_seconds += int(endTimestamp - startTimestamp)
                else:
                    return await invis_embed(ctx, "You are not on-duty. You can go on-duty by selecting **On-Duty**.")
                if status == "off":
                    return await invis_embed(ctx, "You are already off-duty. You can go on-duty by selecting **On-Duty**.")

                embed = discord.Embed(
                    title=ctx.author.name,
                    color=0x2E3136
                )

                embed.set_thumbnail(url=ctx.author.display_avatar.url)
                embed.set_footer(text='Staff Logging Module')

                if shift.get('type'):
                    settings = await bot.settings.find_by_id(ctx.author.id)
                    shift_type = None
                    if settings:
                        if 'shift_types' in settings.keys():
                            for item in (settings['shift_types'].get('types') or []):
                                if item['id'] == shift['type']:
                                    shift_type = item

                if shift_type:
                    embed.add_field(
                        name="<:MalletWhite:1035258530422341672> Type",
                        value=f"<:ArrowRight:1035003246445596774> Clocking out. **({shift_type['name']})**",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="<:MalletWhite:1035258530422341672> Type",
                        value=f"<:ArrowRight:1035003246445596774> Clocking out.",
                        inline=False
                    )

                time_delta = ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
                    shift['startTimestamp']).replace(tzinfo=None)

                time_delta = time_delta - datetime.timedelta(seconds=break_seconds)

                added_seconds = 0
                removed_seconds = 0
                if 'added_time' in shift.keys():
                    for added in shift['added_time']:
                        added_seconds += added

                if 'removed_time' in shift.keys():
                    for removed in shift['removed_time']:
                        removed_seconds += removed

                try:
                    time_delta = time_delta + datetime.timedelta(seconds=added_seconds)
                    time_delta = time_delta - datetime.timedelta(seconds=removed_seconds)
                except OverflowError:
                    await invis_embed(ctx,
                                      f"{ctx.author.mention}'s added or removed time has been voided due to it being an unfeasibly massive numeric value. If you find a vulnerability in ERM, please report it via our Support Server.")

                if break_seconds > 0:
                    embed.add_field(
                        name="<:Clock:1035308064305332224> Elapsed Time",
                        value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)} ({td_format(datetime.timedelta(seconds=break_seconds))} on break)",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="<:Clock:1035308064305332224> Elapsed Time",
                        value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)}",
                        inline=False
                    )

                successEmbed = discord.Embed(
                    title="<:CheckIcon:1035018951043842088> Shift Ended",
                    description="<:ArrowRight:1035003246445596774> Your shift has now ended.",
                    color=0x71c15f
                )

                await msg.edit(embed=successEmbed, view=None)

                if shift.get('nickname'):
                    if shift['nickname']['new'] == ctx.author.display_name:
                        try:
                            await ctx.author.edit(nick=shift['nickname']['old'])
                        except Exception as e:
                            print(e)
                            pass

                await shift_channel.send(embed=embed)

                embed = discord.Embed(title="<:MalletWhite:1035258530422341672> Shift Report",
                                      description="*This is the report for the shift you just ended, it goes over moderations you made during your shift, and any other information that may be useful.*",
                                      color=0x2e3136)

                moderations = len(shift.get('moderations') if shift.get('moderations') else [])
                synced_moderations = len(
                    [moderation for moderation in (shift.get('moderations') if shift.get('moderations') else []) if
                     moderation.get('synced')])

                moderation_list = shift.get('moderations') if shift.get('moderations') else []
                synced_moderation_list = [moderation for moderation in
                                          (shift.get('moderations') if shift.get('moderations') else []) if
                                          moderation.get('synced')]

                embed.set_author(
                    name=f"You have made {moderations} moderations during your shift.",
                    icon_url="https://cdn.discordapp.com/emojis/1035258528149033090.webp?size=96&quality=lossless"
                )

                embed.add_field(
                    name="<:Clock:1035308064305332224> Elapsed Time",
                    value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)} ({td_format(datetime.timedelta(seconds=break_seconds))} on break)",
                    inline=False
                )

                embed.add_field(
                    name="<:Search:1035353785184288788> Total Moderations",
                    value=f"<:ArrowRightW:1035023450592514048> **Warnings:** {len([moderation for moderation in moderation_list if moderation['Type'].lower() == 'warning'])}\n<:ArrowRightW:1035023450592514048> **Kicks:** {len([moderation for moderation in moderation_list if moderation['Type'].lower() == 'kick'])}\n<:ArrowRightW:1035023450592514048> **Bans:** {len([moderation for moderation in moderation_list if moderation['Type'].lower() == 'ban'])}\n<:ArrowRightW:1035023450592514048> **BOLO:** {len([moderation for moderation in moderation_list if moderation['Type'].lower() == 'bolo'])}\n<:ArrowRightW:1035023450592514048> **Custom:** {len([moderation for moderation in moderation_list if moderation['Type'].lower() not in ['warning', 'kick', 'ban', 'bolo']])}",
                    inline=False
                )
                new_ctx = copy.copy(ctx)
                dm_channel = (await new_ctx.author.create_dm())

                new_ctx.guild = None
                new_ctx.channel = dm_channel

                menu = ViewMenu(new_ctx, menu_type=ViewMenu.TypeEmbed, timeout=None)
                menu.add_page(embed)

                moderation_embed = discord.Embed(title="<:MalletWhite:1035258530422341672> Shift Report",
                                                 description="*This is the report for the shift you just ended, it goes over moderations you made during your shift, and any other information that may be useful.*",
                                                 color=0x2e3136)

                moderation_embed.set_author(
                    name=f"You have made {moderations} moderations during your shift.",
                    icon_url="https://cdn.discordapp.com/emojis/1035258528149033090.webp?size=96&quality=lossless"
                )

                moderation_embeds = []
                moderation_embeds.append(moderation_embed)
                print('9867')

                for moderation in moderation_list:
                    if len(moderation_embeds[-1].fields) >= 10:
                        moderation_embeds.append(discord.Embed(title="<:MalletWhite:1035258530422341672> Shift Report",
                                                               description="*This is the report for the shift you just ended, it goes over moderations you made during your shift, and any other information that may be useful.*",
                                                               color=0x2e3136))

                        moderation_embeds[-1].set_author(
                            name=f"You have made {moderations} moderations during your shift.",
                            icon_url="https://cdn.discordapp.com/emojis/1035258528149033090.webp?size=96&quality=lossless"
                        )

                    moderation_embeds[-1].add_field(
                        name=f"<:WarningIcon:1035258528149033090> {moderation['Type'].title()}",
                        value=f"<:ArrowRightW:1035023450592514048> **ID:** {moderation['id']}\n<:ArrowRightW:1035023450592514048> **Type:** {moderation['Type']}\n<:ArrowRightW:1035023450592514048> **Reason:** {moderation['Reason']}\n<:ArrowRightW:1035023450592514048> **Time:** <t:{int(datetime.datetime.strptime(moderation['Time'], '%m/%d/%Y, %H:%M:%S').timestamp()) if isinstance(moderation['Time'], str) else int(moderation['Time'])}>\n<:ArrowRightW:1035023450592514048> **Synced:** {str(moderation.get('synced')) if moderation.get('synced') else 'False'}",
                        inline=False
                    )

                synced_moderation_embed = discord.Embed(title="<:MalletWhite:1035258530422341672> Shift Report",
                                                        description="*This is the report for the shift you just ended, it goes over moderations you made during your shift, and any other information that may be useful.*",
                                                        color=0x2e3136)

                synced_moderation_embed.set_author(
                    name=f"You have made {synced_moderations} synced moderations during your shift.",
                    icon_url="https://cdn.discordapp.com/emojis/1071821068551073892.webp?size=128&quality=lossless"
                )

                synced_moderation_embeds = []
                synced_moderation_embeds.append(moderation_embed)
                print('9895')

                for moderation in synced_moderation_list:
                    if len(synced_moderation_embeds[-1].fields) >= 10:
                        moderation_embeds.append(discord.Embed(title="<:MalletWhite:1035258530422341672> Shift Report",
                                                               description="*This is the report for the shift you just ended, it goes over moderations you made during your shift, and any other information that may be useful.*",
                                                               color=0x2e3136))

                        synced_moderation_embeds[-1].set_author(
                            name=f"You have made {synced_moderations} synced moderations during your shift.",
                            icon_url="https://cdn.discordapp.com/emojis/1071821068551073892.webp?size=128&quality=lossless"
                        )

                    synced_moderation_embeds[-1].add_field(
                        name=f"<:WarningIcon:1035258528149033090> {moderation['Type'].title()}",
                        value=f"<:ArrowRightW:1035023450592514048> **ID:** {moderation['id']}\n<:ArrowRightW:1035023450592514048> **Type:** {moderation['Type']}\n<:ArrowRightW:1035023450592514048> **Reason:** {moderation['Reason']}\n<:ArrowRightW:1035023450592514048> **Time:** <t:{int(datetime.datetime.strptime(moderation['Time'], '%m/%d/%Y, %H:%M:%S').timestamp()) if isinstance(moderation['Time'], str) else int(moderation['Time'])}>",
                        inline=False
                    )

                time_embed = discord.Embed(title="<:MalletWhite:1035258530422341672> Shift Report",
                                           description="*This is the report for the shift you just ended, it goes over moderations you made during your shift, and any other information that may be useful.*",
                                           color=0x2e3136)

                time_embed.set_author(
                    name=f"You were on-shift for {td_format(time_delta)}.",
                    icon_url="https://cdn.discordapp.com/emojis/1035308064305332224.webp?size=128&quality=lossless")
                print('9919')

                time_embed.add_field(
                    name="<:Resume:1035269012445216858> Shift Start",
                    value=f"<:ArrowRight:1035003246445596774> <t:{int(shift['startTimestamp'])}>",
                    inline=False
                )

                time_embed.add_field(
                    name="<:ArrowRightW:1035023450592514048> Shift End",
                    value=f"<:ArrowRight:1035003246445596774> <t:{int(datetime.datetime.now().timestamp())}>",
                    inline=False
                )

                time_embed.add_field(
                    name="<:SConductTitle:1053359821308567592> Added Time",
                    value=f"<:ArrowRight:1035003246445596774> {td_format(datetime.timedelta(seconds=added_seconds))}",
                    inline=False
                )

                time_embed.add_field(
                    name="<:FlagIcon:1035258525955395664> Removed Time",
                    value=f"<:ArrowRight:1035003246445596774> {td_format(datetime.timedelta(seconds=removed_seconds))}",
                    inline=False
                )

                time_embed.add_field(
                    name="<:LinkIcon:1044004006109904966> Total Time",
                    value=f"<:ArrowRight:1035003246445596774> {td_format(time_delta)}",
                    inline=False
                )

                menu.add_select(ViewSelect(title="Shift Report", options={
                    discord.SelectOption(label="Moderations", emoji="<:MalletWhite:1035258530422341672>",
                                         description="View all of your moderations during this shift"): [Page(embed=embed) for
                                                                                                         embed in
                                                                                                         moderation_embeds],
                    discord.SelectOption(label="Synced Moderations", emoji="<:SyncIcon:1071821068551073892>",
                                         description="View all of your synced moderations during this shift"): [
                        Page(embed=embed) for embed in synced_moderation_embeds],
                    discord.SelectOption(label="Shift Time", emoji="<:Clock:1035308064305332224>",
                                         description="View your shift time"): [Page(embed=time_embed)]

                }))

                menu.add_button(ViewButton.back())
                menu.add_button(ViewButton.next())
                try:
                    await menu.start()
                except:
                    pass

                print('9960')

                if not await bot.shift_storage.find_by_id(ctx.author.id):
                    await bot.shift_storage.insert({
                        '_id': ctx.author.id,
                        'shifts': [
                            {
                                'name': ctx.author.name,
                                'startTimestamp': shift['startTimestamp'],
                                'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                'totalSeconds': time_delta.total_seconds(),
                                'guild': ctx.guild.id,
                                'moderations': shift['moderations'] if 'moderations' in shift.keys() else [],
                                'type': shift['type'] if 'type' in shift.keys() else None,
                            }],
                        'totalSeconds': time_delta.total_seconds()

                    })
                else:
                    data = await bot.shift_storage.find_by_id(ctx.author.id)

                    if "shifts" in data.keys():
                        if data['shifts'] is None:
                            data['shifts'] = []

                        if data['shifts'] == []:
                            shifts = [
                                {
                                    'name': ctx.author.name,
                                    'startTimestamp': shift['startTimestamp'],
                                    'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                    'totalSeconds': time_delta.total_seconds(),
                                    'guild': ctx.guild.id,
                                    'moderations': shift['moderations'] if 'moderations' in shift.keys() else [],
                                    'type': shift['type'] if 'type' in shift.keys() else None,
                                }
                            ]
                        else:
                            object = {
                                'name': ctx.author.name,
                                'startTimestamp': shift['startTimestamp'],
                                'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                'totalSeconds': time_delta.total_seconds(),
                                'guild': ctx.guild.id,
                                'moderations': shift['moderations'] if 'moderations' in shift.keys() else [],
                                'type': shift['type'] if 'type' in shift.keys() else None,
                            }
                            shiftdata = data['shifts']
                            shifts = shiftdata + [object]

                        await bot.shift_storage.update_by_id(
                            {
                                '_id': ctx.author.id,
                                'shifts': shifts,
                                'totalSeconds': sum(
                                    [shifts[i]['totalSeconds'] for i in range(len(shifts)) if shifts[i] is not None])
                            }
                        )
                    else:
                        await bot.shift_storage.update_by_id({
                            '_id': ctx.author.id,
                            'shifts': [
                                {
                                    'name': ctx.author.name,
                                    'startTimestamp': shift['startTimestamp'],
                                    'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                                    'totalSeconds': time_delta.total_seconds(),
                                    'guild': ctx.guild.id,
                                    'moderations': shift['moderations'] if 'moderations' in shift.keys() else [],
                                    'type': shift['type'] if 'type' in shift.keys() else None,
                                }],
                            'totalSeconds': time_delta.total_seconds()

                        })

                if await bot.shifts.find_by_id(ctx.author.id):
                    dataShift = await bot.shifts.find_by_id(ctx.author.id)
                    if 'data' in dataShift.keys():
                        if isinstance(dataShift['data'], list):
                            for item in dataShift['data']:
                                if item['guild'] == ctx.guild.id:
                                    dataShift['data'].remove(item)
                                    break
                    await bot.shifts.update_by_id(dataShift)

                role = None
                if shift_type:
                    if shift_type.get('role'):
                        role = [discord.utils.get(ctx.guild.roles, id=role) for role in shift_type.get('role')]
                else:
                    if configItem['shift_management']['role']:
                        if not isinstance(configItem['shift_management']['role'], list):
                            role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
                        else:
                            role = [discord.utils.get(ctx.guild.roles, id=role) for role in
                                    configItem['shift_management']['role']]

                if role:
                    for rl in role:
                        if rl in ctx.author.roles and rl is not None:
                            try:
                                await ctx.author.remove_roles(rl)
                            except:
                                await invis_embed(ctx, f'Could not remove {rl} from {ctx.author.mention}')
            elif view.value == "break":
                if status == "off":
                    return await invis_embed(ctx,
                                             'You cannot be on break if you are not currently on-duty. If you would like to be on-duty, pick **On-Duty**')
                toggle = "on"

                if 'breaks' in shift.keys():
                    for item in shift['breaks']:
                        if item['ended'] is None:
                            toggle = "off"

                if toggle == "on":
                    if 'breaks' in shift.keys():
                        shift['breaks'].append({
                            'started': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                            'ended': None
                        })
                    else:
                        shift['breaks'] = [{
                            'started': ctx.message.created_at.replace(tzinfo=None).timestamp(),
                            'ended': None
                        }]
                    shift['on_break'] = True
                    for data in parent_item['data']:
                        if shift['startTimestamp'] == data['startTimestamp'] and shift['guild'] == data['guild']:
                            data['breaks'] = shift['breaks']
                            data['on_break'] = True
                            break
                    await bot.shifts.update_by_id(parent_item)
                    success = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Break Started",
                        description="<:ArrowRight:1035003246445596774> You are now on break.",
                        color=0x71c15f
                    )
                    await msg.edit(embed=success, view=None)

                    if shift_type:
                        if shift_type.get('role'):
                            role = [discord.utils.get(ctx.guild.roles, id=role) for role in shift_type.get('role')]
                    else:
                        if configItem['shift_management']['role']:
                            if not isinstance(configItem['shift_management']['role'], list):
                                role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
                            else:
                                role = [discord.utils.get(ctx.guild.roles, id=role) for role in
                                        configItem['shift_management']['role']]

                    if vars().get('role'):
                        if role is not None:
                            for rl in role:
                                if rl in ctx.author.roles and rl is not None:
                                    try:
                                        await ctx.author.remove_roles(rl)
                                    except:
                                        await invis_embed(ctx, f'Could not remove {rl} from {ctx.author.mention}')

                else:
                    for item in shift['breaks']:
                        if item['ended'] is None:
                            item['ended'] = ctx.message.created_at.replace(tzinfo=None).timestamp()
                    for data in parent_item['data']:
                        if shift['startTimestamp'] == data['startTimestamp'] and shift['guild'] == data['guild']:
                            data['breaks'] = shift['breaks']
                            data['on_break'] = False
                            break
                    await bot.shifts.update_by_id(parent_item)
                    success = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Break Ended",
                        description="<:ArrowRight:1035003246445596774> You are no longer on break.",
                        color=0x71c15f
                    )
                    await msg.edit(embed=success, view=None)
                    if shift_type:
                        if shift_type.get('role'):
                            role = [discord.utils.get(ctx.guild.roles, id=role) for role in shift_type.get('role')]
                    else:
                        if configItem['shift_management']['role']:
                            if not isinstance(configItem['shift_management']['role'], list):
                                role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
                            else:
                                role = [discord.utils.get(ctx.guild.roles, id=role) for role in
                                        configItem['shift_management']['role']]

                    if role:
                        for rl in role:
                            if not rl in ctx.author.roles and rl is not None:
                                try:
                                    await ctx.author.add_roles(rl)
                                except:
                                    await invis_embed(ctx, f'Could not add {rl} to {ctx.author.mention}')
            elif view.value == "void":
                if status == "off":
                    return await invis_embed(ctx,
                                             "This user has not started a shift yet. You cannot void a shift that has not started.")
                embed = discord.Embed(
                    title=f"{ctx.author.name}#{ctx.author.discriminator}",
                    color=0x2E3136
                )

                try:
                    embed.set_thumbnail(url=ctx.author.display_avatar.url)
                except:
                    pass
                embed.add_field(
                    name="<:MalletWhite:1035258530422341672> Type",
                    value=f"<:ArrowRight:1035003246445596774> Voided time.",
                    inline=False
                )

                embed.add_field(
                    name="<:Clock:1035308064305332224> Elapsed Time",
                    value=f"<:ArrowRight:1035003246445596774> {td_format(ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(shift['startTimestamp']))}",
                    inline=False
                )

                successEmbed = discord.Embed(
                    title="<:CheckIcon:1035018951043842088> Shift Voided",
                    description="<:ArrowRight:1035003246445596774> Shift has been voided successfully.",
                    color=0x71c15f
                )

                embed.set_footer(text='Staff Logging Module')

                if await bot.shifts.find_by_id(ctx.author.id):
                    dataShift = await bot.shifts.find_by_id(ctx.author.id)
                    if 'data' in dataShift.keys():
                        if isinstance(dataShift['data'], list):
                            for item in dataShift['data']:
                                if item['guild'] == ctx.guild.id:
                                    dataShift['data'].remove(item)
                                    break
                        await bot.shifts.update_by_id(dataShift)
                    else:
                        await bot.shifts.delete_by_id(dataShift)

                await shift_channel.send(embed=embed)
                await msg.edit(embed=successEmbed, view=None)
                role = None
                if shift_type:
                    if shift_type.get('role'):
                        role = [discord.utils.get(ctx.guild.roles, id=role) for role in shift_type.get('role')]
                else:
                    if configItem['shift_management']['role']:
                        if not isinstance(configItem['shift_management']['role'], list):
                            role = [discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])]
                        else:
                            role = [discord.utils.get(ctx.guild.roles, id=role) for role in
                                    configItem['shift_management']['role']]

                if role:
                    for rl in role:
                        if rl in ctx.author.roles and rl is not None:
                            try:
                                await ctx.author.remove_roles(rl)
                            except:
                                await invis_embed(ctx, f'Could not remove {rl} from {ctx.author.mention}')


        @duty.command(name='active', description="Get all members of the server currently on shift.",
                      extras={"category": "Shift Management"},
                      aliases=['ac', 'ison'])
        @is_staff()
        async def duty_active(self, ctx):
            bot = self.bot
            configItem = await bot.settings.find_by_id(ctx.guild.id)
            if not configItem:
                return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

            shift_type = None
            if configItem.get('shift_types'):
                shift_types = configItem.get('shift_types')
                if shift_types.get('enabled') is True:
                    if len(shift_types.get('types')) > 1:
                        shift_types = shift_types.get('types')

                        embed = discord.Embed(
                            title="<:Clock:1035308064305332224> Shift Types",
                            description=f"<:ArrowRight:1035003246445596774> You have {num2words.num2words(len(shift_types))} shift types, {', '.join([f'`{i}`' for i in [item['name'] for item in shift_types]])}. Select one of these options to show in this command. If you want to view the active time between these types, select `All`.",
                            color=0x2e3136
                        )

                        view = CustomSelectMenu(ctx.author.id, [
                            discord.SelectOption(label=i['name'], value=i['id'], emoji="<:Clock:1035308064305332224>",
                                                 description=i['name']) for i in shift_types
                        ] + [
                                                    discord.SelectOption(label="All", value="all",
                                                                         emoji="<:Clock:1035308064305332224>",
                                                                         description="Data from all shift types")
                                                ])

                        msg = await ctx.send(embed=embed, view=view)
                        timeout = await view.wait()
                        if timeout:
                            return

                        if view.value:
                            if view.value == "all":
                                shift_type = 0
                            else:
                                shift_type = view.value
                                shift_list = [i for i in shift_types if i['id'] == int(shift_type)]
                                if shift_list:
                                    shift_type = shift_list[0]
                                else:
                                    return await invis_embed(ctx,
                                                             'If you somehow encounter this error, please contact [ERM Support](https://discord.gg/FAC629TzBy)')

            embed = discord.Embed(title='<:Clock:1035308064305332224> Currently on Shift', color=0x2E3136)
            embed.description = "<:ArrowRight:1035003246445596774> *Only active shift times will be here. To view all shift time, run `/duty leaderboard`*\n\n<:SConductTitle:1053359821308567592> **Active Shifts**"
            embed.set_author(name=f"{ctx.author.name}#{ctx.author.discriminator}", icon_url=ctx.author.display_avatar.url)

            embeds = []
            embeds.append(embed)

            all_staff = []

            if not shift_type:
                async for shift in bot.shifts.db.find({"data": {"$elemMatch": {"guild": ctx.guild.id}}}):
                    if 'data' in shift.keys():
                        for s in shift['data']:
                            if s['guild'] == ctx.guild.id:
                                member = discord.utils.get(ctx.guild.members, id=shift['_id'])
                                if member:
                                    print(s)
                                    time_delta = ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
                                        s['startTimestamp']).replace(tzinfo=None)
                                    break_seconds = 0
                                    if 'breaks' in s.keys():
                                        for item in s["breaks"]:
                                            if item['ended'] == None:
                                                break_seconds = ctx.message.created_at.replace(tzinfo=None).timestamp() - item[
                                                    'started']

                                    time_delta = time_delta - datetime.timedelta(seconds=break_seconds)

                                    added_seconds = 0
                                    removed_seconds = 0
                                    if 'added_time' in s.keys():
                                        for added in s['added_time']:
                                            added_seconds += added

                                    if 'removed_time' in s.keys():
                                        for removed in s['removed_time']:
                                            removed_seconds += removed

                                    try:
                                        time_delta = time_delta + datetime.timedelta(seconds=added_seconds)
                                        time_delta = time_delta - datetime.timedelta(seconds=removed_seconds)
                                    except OverflowError:
                                        await invis_embed(
                                            f"{member.mention}'s added or removed time has been voided due to it being an unfeasibly massive numeric value. If you find a vulnerability in ERM, please report it via our Support Server.")

                                    all_staff.append({'id': shift['_id'], "total_seconds": time_delta.total_seconds(),
                                                      "break_seconds": break_seconds})


            else:
                async for shift in bot.shifts.db.find(
                        {"data": {"$elemMatch": {"guild": ctx.guild.id, "type": shift_type['id']}}}):
                    if 'data' in shift.keys():
                        for s in shift['data']:
                            if s['guild'] == ctx.guild.id:
                                member = discord.utils.get(ctx.guild.members, id=shift['_id'])
                                if member:
                                    print(s)
                                    time_delta = ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
                                        s['startTimestamp']).replace(tzinfo=None)
                                    break_seconds = 0
                                    if 'breaks' in s.keys():
                                        for item in s["breaks"]:
                                            if item['ended'] == None:
                                                break_seconds = ctx.message.created_at.replace(tzinfo=None).timestamp() - item[
                                                    'started']

                                    time_delta = time_delta - datetime.timedelta(seconds=break_seconds)

                                    added_seconds = 0
                                    removed_seconds = 0
                                    if 'added_time' in s.keys():
                                        for added in s['added_time']:
                                            added_seconds += added

                                    if 'removed_time' in s.keys():
                                        for removed in s['removed_time']:
                                            removed_seconds += removed

                                    try:
                                        time_delta = time_delta + datetime.timedelta(seconds=added_seconds)
                                        time_delta = time_delta - datetime.timedelta(seconds=removed_seconds)
                                    except OverflowError:
                                        await invis_embed(
                                            f"{member.mention}'s added or removed time has been voided due to it being an unfeasibly massive numeric value. If you find a vulnerability in ERM, please report it via our Support Server.")

                                    all_staff.append({'id': shift['_id'], "total_seconds": time_delta.total_seconds(),
                                                      "break_seconds": break_seconds})

            sorted_staff = sorted(all_staff, key=lambda x: x['total_seconds'], reverse=True)

            for index, staff in enumerate(sorted_staff):
                member = discord.utils.get(ctx.guild.members, id=staff['id'])
                if not member:
                    continue

                if len((embeds[-1].description or '').splitlines()) >= 16:
                    embed = discord.Embed(title='<:Clock:1035308064305332224> Currently on Shift', color=0x2E3136)
                    embed.description = "<:ArrowRight:1035003246445596774> *Only active shift times will be here. To view all shift time, run `/duty leaderboard`*\n\n<:SConductTitle:1053359821308567592> **Active Shifts**"
                    embed.set_author(name=f"{ctx.author.name}#{ctx.author.discriminator}",
                                     icon_url=ctx.author.display_avatar.url)
                    embeds.append(embed)

                embeds[
                    -1].description += f"\n<:ArrowRightW:1035023450592514048> **{index + 1}.** {member.mention} - {td_format(datetime.timedelta(seconds=staff['total_seconds']))}{(' (Currently on break: {})'.format(td_format(datetime.timedelta(seconds=staff['break_seconds'])))) if staff['break_seconds'] > 0 else ''}"

            if ctx.interaction:
                gtx = ctx.interaction
            else:
                gtx = ctx

            menu = ViewMenu(gtx, menu_type=ViewMenu.TypeEmbed, timeout=None)
            for embed in embeds:
                menu.add_page(embed=embed)
            menu._pc = _PageController(menu.pages)
            menu.add_buttons([ViewButton.back(), ViewButton.next()])
            if len(menu.pages) == 1:
                try:
                    return await msg.edit(embed=embed, view=None)
                except UnboundLocalError:
                    return await ctx.send(embed=embed)
            try:
                await msg.edit(embed=embeds[0], view=menu._ViewMenu__view)
            except UnboundLocalError:
                await ctx.send(embed=embeds[0], view=menu._ViewMenu__view)


        @duty.command(name='leaderboard',
                      description="Get the total time worked for the whole of the staff team.",
                      extras={"category": "Shift Management"},
                      aliases=['lb'])
        @is_staff()
        async def shift_leaderboard(self, ctx):
            bot = self.bot
            try:
                configItem = await bot.settings.find_by_id(ctx.guild.id)
                if configItem is None:
                    raise ValueError('Settings does not exist.')
            except:
                return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

            shift_type = None
            if configItem.get('shift_types'):
                shift_types = configItem.get('shift_types')
                if shift_types.get('enabled') is True:
                    if len(shift_types.get('types')) > 1:
                        shift_types = shift_types.get('types')

                        embed = discord.Embed(
                            title="<:Clock:1035308064305332224> Shift Types",
                            description=f"<:ArrowRight:1035003246445596774> You have {num2words.num2words(len(shift_types))} shift types, {', '.join([f'`{i}`' for i in [item['name'] for item in shift_types]])}. Select one of these options to show on the leaderboard. If you want to view the total time between these types, select `All`.",
                            color=0x2e3136
                        )

                        view = CustomSelectMenu(ctx.author.id, [
                            discord.SelectOption(label=i['name'], value=i['id'], emoji="<:Clock:1035308064305332224>",
                                                 description=i['name']) for i in shift_types
                        ] + [
                                                    discord.SelectOption(label="All", value="all",
                                                                         emoji="<:Clock:1035308064305332224>",
                                                                         description="Data from all shift types")
                                                ])

                        msg = await ctx.send(embed=embed, view=view)
                        timeout = await view.wait()
                        if timeout:
                            return

                        if view.value:
                            if view.value == "all":
                                shift_type = 0
                            else:
                                shift_type = view.value
                                shift_list = [i for i in shift_types if i['id'] == int(shift_type)]
                                if shift_list:
                                    shift_type = shift_list[0]
                                else:
                                    return await invis_embed(ctx,
                                                             'If you somehow encounter this error, please contact [ERM Support](https://discord.gg/FAC629TzBy)')

            all_staff = [{"id": None, "total_seconds": 0}]

            if shift_type != 0 and shift_type is not None:
                async for document in bot.shift_storage.db.find(
                        {"shifts": {"$elemMatch": {"guild": ctx.guild.id, "type": shift_type['id']}}}):
                    total_seconds = 0
                    moderations = 0
                    for shift in document['shifts']:
                        if isinstance(shift, dict):
                            if shift.get('type'):
                                if shift['guild'] == ctx.guild.id and shift['type'] == shift_type['id']:
                                    if 'moderations' in shift.keys():
                                        moderations += len(shift['moderations'])
                                    total_seconds += int(shift['totalSeconds'])

                    if document['_id'] not in [item['id'] for item in all_staff]:
                        all_staff.append({'id': document['_id'], 'total_seconds': total_seconds, 'moderations': moderations})
                    else:
                        for item in all_staff:
                            if item['id'] == document['_id']:
                                item['total_seconds'] = total_seconds
                                item['moderations'] = moderations
            else:
                async for document in bot.shift_storage.db.find(
                        {"shifts": {"$elemMatch": {"guild": ctx.guild.id}}}):
                    total_seconds = 0
                    moderations = 0
                    for shift in document['shifts']:
                        if isinstance(shift, dict):
                            if shift['guild'] == ctx.guild.id:
                                if 'moderations' in shift.keys():
                                    moderations += len(shift['moderations'])
                                total_seconds += int(shift['totalSeconds'])

                    if document['_id'] not in [item['id'] for item in all_staff]:
                        all_staff.append({'id': document['_id'], 'total_seconds': total_seconds, 'moderations': moderations})
                    else:
                        for item in all_staff:
                            if item['id'] == document['_id']:
                                item['total_seconds'] = total_seconds
                                item['moderations'] = moderations

            if len(all_staff) == 0:
                return await invis_embed(ctx, 'No shifts were made in your server.')
            for item in all_staff:
                if item['id'] is None:
                    all_staff.remove(item)

            sorted_staff = sorted(all_staff, key=lambda x: x['total_seconds'], reverse=True)

            buffer = None
            embeds = []

            embed = discord.Embed(
                color=0x2E3136,
                title="<:Clock:1035308064305332224> Duty Leaderboard"
            )
            embed.set_author(name=f"{ctx.author.name}#{ctx.author.discriminator}", icon_url=ctx.author.display_avatar.url)

            embeds.append(embed)
            print(sorted_staff)
            data = []
            if not sorted_staff:
                if shift_type != 0 and shift_type is not None:
                    await invis_embed(ctx, f"No shifts were made for the `{shift_type['name']}` shift type.")
                else:
                    await invis_embed(ctx, 'No shifts were made in your server.')
                return

            my_data = None

            for index, i in enumerate(sorted_staff):
                try:
                    member = await ctx.guild.fetch_member(i["id"])
                except:
                    member = None
                print(index)
                print(i)
                print(member)
                if member:
                    if member.id == ctx.author.id:
                        i['index'] = index
                        my_data = i

                    if buffer is None:
                        print('buffer none')
                        buffer = "%s - %s" % (
                            f"{member.name}#{member.discriminator}", td_format(datetime.timedelta(seconds=i['total_seconds'])))
                        data.append([index + 1, f"{member.name}#{member.discriminator}", member.top_role.name,
                                     td_format(datetime.timedelta(seconds=i['total_seconds'])), i['moderations']])
                    else:
                        print('buffer not none')
                        buffer = buffer + "\n%s - %s" % (
                            f"{member.name}#{member.discriminator}", td_format(datetime.timedelta(seconds=i['total_seconds'])))
                        data.append([index + 1, f"{member.name}#{member.discriminator}", member.top_role.name,
                                     td_format(datetime.timedelta(seconds=i['total_seconds'])), i['moderations']])

                    if len((embeds[-1].description or '').splitlines()) < 16:
                        if embeds[-1].description is None:
                            embeds[
                                -1].description = f"<:ArrowRight:1035003246445596774> *All shift times will be here. To view active shifts, run `/duty active`*\n\n<:SConductTitle:1053359821308567592> **Total Shifts**\n<:ArrowRightW:1035023450592514048> **{index + 1}.** {member.mention} - {td_format(datetime.timedelta(seconds=i['total_seconds']))}\n"
                        else:
                            embeds[
                                -1].description += f"<:ArrowRightW:1035023450592514048> **{index + 1}.** {member.mention} - {td_format(datetime.timedelta(seconds=i['total_seconds']))}\n"

                    else:
                        print('fields more than 24')
                        new_embed = discord.Embed(
                            color=0x2E3136,
                            title="<:Clock:1035308064305332224> Duty Leaderboard"
                        )

                        new_embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
                        new_embed.description = "<:ArrowRight:1035003246445596774> *All shift times will be here. To view active shifts, run `/duty active`*\n\n"
                        new_embed.description += f"<:SConductTitle:1053359821308567592> **Total Shifts**\n<:ArrowRightW:1035023450592514048> **{index + 1}.** {member.mention} - {td_format(datetime.timedelta(seconds=i['total_seconds']))}\n"
                        embeds.append(new_embed)

            staff_roles = []
            ordinal = lambda n: "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])  # NOQA: E731
            ordinal_formatted = None
            quota_seconds = 0

            if configItem['staff_management'].get('role'):
                if isinstance(configItem['staff_management']['role'], int):
                    staff_roles.append(configItem['staff_management']['role'])
                elif isinstance(configItem['staff_management']['role'], list):
                    for role in configItem['staff_management']['role']:
                        staff_roles.append(role)

            if configItem['staff_management'].get('management_role'):
                if isinstance(configItem['staff_management']['management_role'], int):
                    staff_roles.append(configItem['staff_management']['management_role'])
                elif isinstance(configItem['staff_management']['management_role'], list):
                    for role in configItem['staff_management']['management_role']:
                        staff_roles.append(role)
            staff_roles = [ctx.guild.get_role(role) for role in staff_roles]
            added_staff = []

            for role in staff_roles.copy():
                if role is None:
                    staff_roles.remove(role)

            for role in staff_roles:
                if role.members:
                    for member in role.members:
                        if member.id not in [item['id'] for item in sorted_staff]:
                            if member not in added_staff:
                                index = index + 1

                                if buffer is None:
                                    buffer = "%s - %s" % (f"{member.name}#{member.discriminator}", "0 seconds")
                                    data.append(
                                        [index, f"{member.name}#{member.discriminator}", member.top_role.name, "0 seconds",
                                         0])
                                    added_staff.append(member)
                                else:
                                    buffer = buffer + "\n%s - %s" % (f"{member.name}#{member.discriminator}", "0 seconds")
                                    data.append(
                                        [index, f"{member.name}#{member.discriminator}", member.top_role.name, "0 seconds",
                                         0])
                                    added_staff.append(member)

                                if len((embeds[-1].description or '').splitlines()) < 16:
                                    if embeds[-1].description is None:
                                        embeds[
                                            -1].description = f"<:ArrowRight:1035003246445596774> *All shift times will be here. To view active shifts, run `/duty active`*\n\n<:SConductTitle:1053359821308567592> **Total Shifts**\n<:ArrowRightW:1035023450592514048> **{index}.** {member.mention} - 0 seconds\n"
                                    else:
                                        embeds[
                                            -1].description += f"<:ArrowRightW:1035023450592514048> **{index}.** {member.mention} - 0 seconds\n"

                                else:
                                    print('fields more than 24')
                                    new_embed = discord.Embed(
                                        color=0x2E3136,
                                        title="<:Clock:1035308064305332224> Duty Leaderboard"
                                    )

                                    new_embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
                                    new_embed.description = "<:ArrowRight:1035003246445596774> *All shift times will be here. To view active shifts, run `/duty active`*\n\n"
                                    new_embed.description += f"<:SConductTitle:1053359821308567592> **Total Shifts**\n<:ArrowRightW:1035023450592514048> **{index}.** {member.mention} - {td_format(datetime.timedelta(seconds=i['total_seconds']))}\n"
                                    embeds.append(new_embed)
            perm_staff = list(
                filter(lambda m: (m.guild_permissions.manage_messages or m.guild_permissions.manage_guild) and not m.bot,
                       ctx.guild.members))
            for member in perm_staff:
                if member.id not in [item['id'] for item in sorted_staff]:
                    if member not in added_staff:
                        index = index + 1

                        if buffer is None:
                            buffer = "%s - %s" % (f"{member.name}#{member.discriminator}", "0 seconds")
                            data.append(
                                [index + 1, f"{member.name}#{member.discriminator}", member.top_role.name, "0 seconds", 0])
                            added_staff.append(member)

                        else:
                            buffer = buffer + "\n%s - %s" % (f"{member.name}#{member.discriminator}", "0 seconds")
                            data.append(
                                [index + 1, f"{member.name}#{member.discriminator}", member.top_role.name, "0 seconds", 0])
                            added_staff.append(member)

                        if len((embeds[-1].description or '').splitlines()) < 16:
                            if embeds[-1].description is None:
                                embeds[
                                    -1].description = f"<:ArrowRight:1035003246445596774> *All shift times will be here. To view active shifts, run `/duty active`*\n\n<:SConductTitle:1053359821308567592> **Total Shifts**\n<:ArrowRightW:1035023450592514048> **{index}.** {member.mention} - 0 seconds\n"
                            else:
                                embeds[
                                    -1].description += f"<:ArrowRightW:1035023450592514048> **{index + 1}.** {member.mention} - 0 seconds\n"

                        else:
                            print('fields more than 24')
                            new_embed = discord.Embed(
                                color=0x2E3136,
                                title="<:Clock:1035308064305332224> Duty Leaderboard"
                            )

                            new_embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
                            new_embed.description = "<:ArrowRight:1035003246445596774> *All shift times will be here. To view active shifts, run `/duty active`*\n\n"
                            new_embed.description += f"<:SConductTitle:1053359821308567592> **Total Shifts**\n<:ArrowRightW:1035023450592514048> **{index + 1}.** {member.mention} - 0 seconds\n"
                            embeds.append(new_embed)

            combined = []
            for list_item in data:
                for item in list_item:
                    combined.append(item)

            print(all_staff)
            print(sorted_staff)
            print(buffer)

            if my_data is not None:
                ordinal_formatted = ordinal(my_data['index'] + 1)
                if 'quota' in configItem['shift_management'].keys():
                    quota_seconds = configItem['shift_management']['quota']

                embeds[
                    0].description += f"\n\n<:staff:1035308057007230976> **Your Stats**\n<:ArrowRight:1035003246445596774> {td_format(datetime.timedelta(seconds=my_data['total_seconds']))}\n<:ArrowRight:1035003246445596774> {ordinal_formatted} Place on Leaderboard\n<:ArrowRight:1035003246445596774> {'Met Quota' if my_data['total_seconds'] >= quota_seconds else 'Not Met Quota'}"
            else:
                embeds[
                    0].description += f"\n\n<:staff:1035308057007230976> **Your Stats**\n<:ArrowRight:1035003246445596774> 0 seconds\n<:ArrowRight:1035003246445596774> Not Met Quota"

            try:
                bbytes = buffer.encode('utf-8')
            except Exception as e:
                print(e)
                if len(embeds) == 0:
                    return await invis_embed(ctx, 'No shift data has been found.')
                elif embeds[0].description is None:
                    return await invis_embed(ctx, 'No shift data has been found.')
                else:
                    if ctx.interaction:
                        interaction = ctx.interaction
                    else:
                        interaction = ctx

                    menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed, timeout=None)
                    for embed in embeds:
                        if embed is not None:
                            menu.add_pages([embed])

                    if len(menu.pages) == 1:
                        return await ctx.send(embed=embed)

                    menu.add_buttons([ViewButton.back(), ViewButton.next()])
                    await menu.start()

            if len(embeds) == 1:
                new_embeds = []
                for i in embeds:
                    new_embeds.append(i)
                if await management_predicate(ctx):
                    view = RequestGoogleSpreadsheet(ctx.author.id, credentials_dict, scope, combined,
                                                    config("DUTY_LEADERBOARD_ID"))
                else:
                    view = None
                await ctx.send(embeds=new_embeds, file=discord.File(fp=BytesIO(bbytes), filename='shift_leaderboard.txt'),
                               view=view)
            else:
                file = discord.File(fp=BytesIO(bbytes), filename='shift_leaderboard.txt')
                if ctx.interaction:
                    interaction = ctx
                else:
                    interaction = ctx

                if await management_predicate(ctx):
                    view = RequestGoogleSpreadsheet(ctx.author.id, credentials_dict, scope, combined,
                                                    config("DUTY_LEADERBOARD_ID"))
                else:
                    view = None

                async def response_func(interaction: discord.Interaction, button: discord.Button):
                    await interaction.response.send_message(file=file, ephemeral=True)

                menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed, show_page_director=True, timeout=None)
                for embed in embeds:
                    if embed is not None:
                        menu.add_page(embed=embed)

                menu._pc = _PageController(menu.pages)
                menu.add_buttons([ViewButton.back(), ViewButton.next()])
                menu._ViewMenu__view.add_item(CustomExecutionButton(
                    ctx.author.id,
                    "Download Shift Leaderboard",
                    discord.ButtonStyle.gray,
                    emoji=None,
                    func=response_func
                ))
                if len(menu.pages) == 1:
                    try:
                        return await msg.edit(embed=embed, file=file, view=view)
                    except UnboundLocalError:
                        return await ctx.send(embed=embed, file=file, view=view)
                if view:
                    for child in view.children:
                        menu._ViewMenu__view.add_item(child)

                try:
                    await msg.edit(embed=embeds[0], view=menu._ViewMenu__view)
                except UnboundLocalError:
                    await ctx.send(embed=embeds[0], view=menu._ViewMenu__view)


        @duty.command(name='clearall',
                      description="Clears all of the shift data.",
                      extras={"category": "Shift Management"},
                      aliases=['shift-cla'])
        @is_management()
        async def clearall(self, ctx):
            bot = self.bot
            try:
                configItem = await bot.settings.find_by_id(ctx.guild.id)
            except:
                return await invis_embed(ctx, 'The server has not been set up yet. Please run `/setup` to set up the server.')

            view = YesNoMenu(ctx.author.id)
            embed = discord.Embed(
                description='<:WarningIcon:1035258528149033090> **Are you sure you would like to clear ALL shift data?** This is irreversible.',
                color=0x2E3136)

            msg = await ctx.send(view=view, embed=embed)
            await view.wait()
            if view.value is False:
                return await invis_embed(ctx, 'Successfully cancelled.')

            async for document in bot.shift_storage.db.find({"shifts": {"$elemMatch": {"guild": ctx.guild.id}}}):
                if 'shifts' in document.keys():
                    for shift in document['shifts'].copy():
                        if isinstance(shift, dict):
                            if shift['guild'] == ctx.guild.id:
                                document['shifts'].remove(shift)
                    await bot.shift_storage.db.replace_one({'_id': document['_id']}, document)

            successEmbed = discord.Embed(
                title="<:CheckIcon:1035018951043842088> Success!",
                description=f"<:ArrowRight:1035003246445596774> All shifts in your server have been cleared.",
                color=0x71c15f
            )

            await msg.edit(embed=successEmbed, view=None)


async def setup(bot):
    await bot.add_cog(ShiftManagement(bot))