from copy import copy
from pprint import pformat

import discord
from discord import HTTPException
from discord.ext import commands

from erm import check_privacy, generator, is_management
from utils.constants import blank_color, BLANK_COLOR
from menus import (
    ChannelSelect,
    CustomSelectMenu,
    ERLCIntegrationConfiguration,
    RoleSelect,
    YesNoColourMenu,
    NextView, BasicConfiguration, LOAConfiguration, ShiftConfiguration, RAConfiguration,
    PunishmentsConfiguration, GameSecurityConfiguration, GameLoggingConfiguration, AntipingConfiguration,
    ActivityNoticeManagement, PunishmentManagement, ShiftLoggingManagement, ERMCommandLog, WhitelistVehiclesManagement
)
from utils.paginators import CustomPage, SelectPagination
from utils.utils import require_settings, generator, log_command_usage


class Configuration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.hybrid_command(
        name="setup",
        description="Begin using ERM!",
        extras={
            "category": "Configuration"
        }
    )
    @is_management()
    async def _setup(self, ctx: commands.Context):
        if isinstance(ctx, commands.Context):
            await log_command_usage(self.bot,ctx.guild, ctx.author, f"Setup")
        else:
            await log_command_usage(self.bot,ctx.guild, ctx.user, f"Setup")
        bot = self.bot
        from utils.constants import base_configuration
        current_settings = None
        # del base_configuration['_id']
        modifications = {"_id": ctx.guild.id, **base_configuration}
        modifications['_id'] = ctx.guild.id
        msg = None

        current_settings = await bot.settings.find_by_id(ctx.guild.id)
        if current_settings:
            msg = await ctx.send(embed=discord.Embed(
                title="Already Setup",
                description="You've already setup ERM in this server! Are you sure you would like to go through the setup process again?",
                color=blank_color
            ), view=(confirmation_view := YesNoColourMenu(ctx.author.id)))
            timeout = await confirmation_view.wait()
            if confirmation_view.value is False:
                return await msg.edit(embed=discord.Embed(
                    title="Successfully Cancelled",
                    description="Cancelled the setup process for this server. All settings have been kept.",
                    color=blank_color
                ), view=None)

        if msg is None:
            msg = await ctx.send(embed=discord.Embed(
                title="Let's get started!",
                description="To setup ERM, press the arrow button below!",
                color=blank_color
            ), view=(next_view := NextView(ctx.author.id)))
        else:
            await msg.edit(embed=discord.Embed(
                title="Let's get started!",
                description="To setup ERM, press the arrow button below!",
                color=blank_color
            ), view=(next_view := NextView(ctx.author.id)))

        timeout = await next_view.wait()
        if timeout or not next_view.value:
            await msg.edit(embed=discord.Embed(
                title="Cancelled",
                description="You have took too long to complete this part of the setup.",
                color=blank_color
            ), view=None)
            return

        secret_key = next(generator)

        def get_active_view_state() -> discord.ui.View | None:
            return self.bot.view_state_manager.get(secret_key)

        def set_active_view_state(view: discord.ui.View):
            self.bot.view_state_manager[secret_key] = view

        async def discard_unlock_override(interaction: discord.Interaction):
            await interaction.response.defer()

        async def check_unlock_override(interaction: discord.Interaction):
            view = get_active_view_state()
            # if view is None:
            #     return
            await interaction.response.defer()

            impurities = []
            for item in view.children:
                if isinstance(item, discord.ui.Select) or isinstance(item, discord.ui.RoleSelect) or isinstance(item, discord.ui.ChannelSelect):
                    if item.callback != discard_unlock_override:
                        if len(item.values) == 0:
                            impurities.append(item)
            # print(impurities)
            if len(impurities) == 0:
                buttons = list(filter(lambda x: isinstance(x, discord.ui.Button), view.children))
                # print(buttons)
                if len(buttons) != 0:
                    buttons[0].disabled = False
                    for item in view.children:
                        if isinstance(item, discord.ui.Select):
                            value = item.values[0]
                            stored_index = 0
                            for index, obj in enumerate(item.options):
                                if obj.value == value:
                                    stored_index = index
                            item.options[stored_index].default = True
                            for select_opt in item.options:
                                if item.options[stored_index] != select_opt:
                                    select_opt.default = False
                            # print(f'defaults: {len([i for i in item.options if i.default is True])}')
                    await interaction.message.edit(view=view)
            else:
                buttons = list(filter(lambda x: isinstance(x, discord.ui.Button), view.children))
                # print(buttons)
                if len(buttons) != 0:
                    if buttons[0].disabled is False:
                        buttons[0].disabled = True
                        await interaction.message.edit(view=view)

        async def callback_override(interaction: discord.Interaction, *args, **kwargs):
            await interaction.response.defer()

        basic_settings = discord.ui.View()
        next_button = NextView(ctx.author.id).children[0]
        next_button.row = 4
        next_button.disabled = True

        staff_roles = RoleSelect(ctx.author.id).children[0]
        staff_roles.row = 0
        staff_roles.placeholder = "Staff Roles"
        staff_roles.callback = check_unlock_override
        staff_roles.min_values = 0

        admin_roles = RoleSelect(ctx.author.id).children[0]
        admin_roles.row = 1
        admin_roles.placeholder = "Admin Roles"
        admin_roles.callback = check_unlock_override
        admin_roles.min_values = 0

        management_roles = RoleSelect(ctx.author.id).children[0]
        management_roles.row = 2
        management_roles.placeholder = "Management Roles"
        management_roles.callback = check_unlock_override
        management_roles.min_values = 0

        prefix_view = CustomSelectMenu(ctx.author.id, [
                discord.SelectOption(
                    label="!",
                    description="Use '!' as your custom prefix."
                ),
                discord.SelectOption(
                    label=">",
                    description="Use '>' as your custom prefix."
                ),
                discord.SelectOption(
                    label="?",
                    description="Use '?' as your custom prefix."
                ),
                discord.SelectOption(
                    label=":",
                    description="Use ':' as your custom prefix."
                )
            ])
        prefix = prefix_view.children[0]
        prefix.row = 3
        prefix.placeholder = "Prefix"
        prefix.callback = check_unlock_override



        async def stop_override(interaction: discord.Interaction):
            await interaction.response.defer()
            get_active_view_state().stop()


        # prefix.callback = callback_override
        next_button.callback = stop_override

        for item in [staff_roles,admin_roles, management_roles, prefix, next_button]:
            basic_settings.add_item(item)

        set_active_view_state(basic_settings)

        await msg.edit(
            embed=discord.Embed(
                title="Basic Settings",
                description=(
                    "**Staff Role:** A staff role is the role that is going to be able to use most ERM commands. You'd assign this role to the people you want to be able to use ERM's core functionalities.\n\n"
                    "**Admin Role:** An admin role is the role that can manage LOAs, RAs & other peoples' shifts but it can not use server manage and config.\n\n"
                    "**Management Role:** A management role is the roles of your server management members. These people will be able to delete punishments, modify people's shift time, and accept LOA Requests.\n\n"
                    "**Prefix:** This will be a prefix you are able to use instead of our slash command system. You can use this prefix to execute commands slightly faster and to take advantage of some extra features."
                ),
                color=blank_color
            ),
            view=basic_settings
        )
        await basic_settings.wait()


        for item in basic_settings.children:
            if isinstance(item, discord.ui.Select) or isinstance(item, discord.ui.RoleSelect):
                if len(item.values) > 0:
                    if item.placeholder == "Staff Roles":
                        modifications['staff_management']['role'] = [i.id for i in item.values]
                    if item.placeholder == "Prefix":
                        modifications['customisation']['prefix'] = item.values[0]
                    elif item.placeholder == "Management Roles":
                        modifications['staff_management']['management_role'] = [i.id for i in item.values]
                    elif item.placeholder == "Admin Roles":
                        modifications['staff_management']['admin_role'] = [i.id for i in item.values]

        loa_requests_settings = discord.ui.View()

        loa_channel_view = ChannelSelect(ctx.author.id, limit=1)
        loa_channel_select = loa_channel_view.children[0]
        loa_channel_select.placeholder = "LOA Channel"
        loa_channel_select.row = 1

        loa_role_view = RoleSelect(ctx.author.id, limit=1)
        loa_role_select = loa_role_view.children[0]
        loa_role_select.placeholder = "LOA Role"
        loa_role_select.row = 2

        loa_enabled_view = CustomSelectMenu(
            ctx.author.id,
            [
                discord.SelectOption(
                    label='Enabled',
                    value="enabled",
                    description="LOA Requests are enabled."
                ),
                discord.SelectOption(
                    label="Disabled",
                    value="disabled",
                    description="LOA Requests are disabled."
                )
            ]
        )
        loa_enabled_select = loa_enabled_view.children[0]
        loa_enabled_select.callback = callback_override
        loa_enabled_select.row = 0
        loa_enabled_select.placeholder = "LOA Requests"

        next_view = NextView(ctx.author.id)
        next_button = next_view.children[0]
        next_button.callback = stop_override
        next_button.row = 4

        for item in [loa_enabled_select, loa_role_select, loa_channel_select, next_button]:
            loa_requests_settings.add_item(item)

        await msg.edit(
            embed=discord.Embed(
                title="<:loa:1169799727143977090> LOA Requests",
                description=(
                        "**Enabled:** This setting enables or disables the LOA Requests module. When enabled, this allows your staff members to fill out Leave of Absence requests for your management members to approve.\n\n"
                        "**LOA Role:** This role is given to those who are on Leave of Absence, and is removed when they go off Leave of Absence.\n\n"
                        "**LOA Channel:** This channel will be where Leave of Absence requests will be logged, and where they will be accepted or denied. Make sure this is a channel that Management members can see, so that they can approve LOA requests."
                    ),
                color=blank_color
            ),
            view=loa_requests_settings
        )

        set_active_view_state(loa_requests_settings)
        await loa_requests_settings.wait()


        for item in loa_requests_settings.children:
            if isinstance(item, discord.ui.Select) or isinstance(item, discord.ui.RoleSelect) or isinstance(item, discord.ui.ChannelSelect):
                if len(item.values) > 0:
                    if item.placeholder == "LOA Role":
                        modifications['staff_management']['loa_role'] = [r.id for r in item.values]
                    elif item.placeholder == "LOA Channel":
                        modifications['staff_management']['channel'] = item.values[0].id
                    elif item.placeholder == "LOA Requests":
                        modifications['staff_management']['enabled'] = bool(item.values[0] == "enabled")

        ra_requests_settings = discord.ui.View()


        ra_role_view = RoleSelect(ctx.author.id, limit=1)
        ra_role_select = ra_role_view.children[0]
        ra_role_select.placeholder = "RA Role"
        ra_role_select.row = 2
        ra_role_select.min_values = 0


        next_view = NextView(ctx.author.id)
        next_button = next_view.children[0]
        next_button.callback = stop_override
        next_button.row = 4

        for item in [ra_role_select, next_button]:
            ra_requests_settings.add_item(item)

        await msg.edit(
            embed=discord.Embed(
                title="<:loa:1169799727143977090> RA Requests",
                description=(
                    "**What are RA Requests?** RA Requests, also called Reduced Activity Requests, are a form of Leave of Absence where the staff member isn't required to complete the full quota, but expects that they will be able to complete it partially.\n\n"
                    "**RA Role:** This role is given to those who are on Reduced Activity, and is removed when they go off Reduced Activity.\n\n"
                ),
                color=blank_color
            ),
            view=ra_requests_settings
        )
        set_active_view_state(ra_requests_settings)

        await ra_requests_settings.wait()


        for item in ra_requests_settings.children:
            if isinstance(item, discord.ui.Select) or isinstance(item, discord.ui.RoleSelect):
                if len(item.values) > 0:
                    if item.placeholder == "RA Role":
                        modifications['staff_management']['ra_role'] = item.values[0].id

        punishment_settings = discord.ui.View()

        next_view = NextView(ctx.author.id)
        next_button = next_view.children[0]
        next_button.callback = stop_override
        next_button.row = 4

        punishment_channel_view = ChannelSelect(ctx.author.id, limit=1)
        punishment_channel_select: discord.ui.ChannelSelect = punishment_channel_view.children[0]
        punishment_channel_select.min_values = 0
        punishment_channel_select.placeholder = "Punishments Channel"
        punishment_channel_select.row = 1

        punishments_enabled_view = CustomSelectMenu(ctx.author.id, [
            discord.SelectOption(
                label="Enabled",
                value="enabled",
                description="ROBLOX Punishments are enabled."
            ),
            discord.SelectOption(
                label="Disabled",
                value="disabled",
                description="ROBLOX Punishments are disabled."
            )
        ])
        punishments_enabled_item = punishments_enabled_view.children[0]
        punishments_enabled_item.placeholder = "ROBLOX Punishments"
        punishments_enabled_item.row = 0
        punishments_enabled_item.callback = callback_override

        for item in [punishments_enabled_item, punishment_channel_select, next_button]:
            punishment_settings.add_item(item)

        await msg.edit(
            embed=discord.Embed(
                title="<:log:1163524830319104171> ROBLOX Punishments",
                description=(
                    "**What is the ROBLOX Punishments module?** The ROBLOX Punishments module allows for members of your Staff Team to log punishments against a ROBLOX player using ERM! You can specify custom types of punishments, where they will go, as well as manage and search individual punishments.\n\n"
                    "**Enabled:** This setting toggles the ROBLOX Punishments module. When enabled, staff members will be able to use `/punish`, and management members will be able to additionally use `/punishment manage`.\n\n"
                    "**Punishments Channel:** This is where most punishments made with the ROBLOX Punishments go. Any logged actions of a ROBLOX player will go to this channel."
                ),
                color=blank_color
            ),
            view=punishment_settings
        )
        set_active_view_state(punishment_settings)
        await punishment_settings.wait()

        for item in punishment_settings.children:
            if isinstance(item, discord.ui.Select) or isinstance(item, discord.ui.RoleSelect) or isinstance(item, discord.ui.ChannelSelect):
                if len(item.values) > 0:
                    if item.placeholder == "ROBLOX Punishments":
                        if not modifications.get('punishments'):
                            modifications['punishments'] = {}
                        modifications['punishments']['enabled'] = bool(item.values[0] == "enabled")
                    elif item.placeholder == "Punishments Channel":
                        if not modifications.get('punishments'):
                            modifications['punishments'] = {}
                        modifications['punishments']['channel'] = item.values[0].id

        shift_management_settings = discord.ui.View()

        shift_enabled_view = CustomSelectMenu(
            ctx.author.id,
            [
                discord.SelectOption(
                    label="Enabled",
                    value="enabled",
                    description="Enable the Shift Management module."
                ),
                discord.SelectOption(
                    label="Disabled",
                    value="disabled",
                    description="Disable the Shift Management module."
                )
            ]
        )
        shift_enabled_select = shift_enabled_view.children[0]
        shift_enabled_select.placeholder = "Shift Management"
        shift_enabled_select.row = 0
        shift_enabled_select.callback = callback_override


        shift_channel_view = ChannelSelect(ctx.author.id, limit=1)
        shift_channel_select = shift_channel_view.children[0]
        shift_channel_select.row = 1
        shift_channel_select.placeholder = "Shift Channel"
        shift_channel_select.min_values = 0
        
        shift_role_view = RoleSelect(ctx.author.id, limit=5)
        shift_role_select = shift_role_view.children[0]
        shift_role_select.row = 2
        shift_role_select.placeholder = "On-Duty Role"
        shift_channel_select.min_values = 0

        next_menu = NextView(ctx.author.id)
        next_button = next_menu.children[0]
        next_button.disabled = False
        next_button.callback = stop_override
        next_button.row = 4

        for item in [shift_enabled_select, shift_role_select, shift_channel_select, next_button]:
            shift_management_settings.add_item(item)

        await msg.edit(
            embed=discord.Embed(
                title="<:shift:1169801400545452033> Shift Management",
                description=(
                    "**What is Shift Management?** The Shift Management module allows for staff members to log how much time they were in-game, or moderating, or on as a staff member. It allows for a comprehensive guide of who is the most active in your staff team.\n\n"
                    "**Enabled:** When enabled, staff members will be able to run `/duty` commands to manage their shift, see how much time they have, as well as see how much time other people have. Management members will be able to administrate people's shifts, add time, remove time, and clear people's shifts.\n\n"
                    "**Shift Channel:** This is where all shift logs will go to. This channel will be used for all modifications to shifts, any person that may be starting or ending their shift.\n\n"
                    "**On-Duty Role:** When someone is on shift, they will be given this role. When the staff member goes off shift, this role will be removed from them."
                ),
                color=blank_color
            ),
            view=shift_management_settings
        )
        set_active_view_state(shift_management_settings)
        await shift_management_settings.wait()

        for item in shift_management_settings.children:
            if isinstance(item, discord.ui.Select) or isinstance(item, discord.ui.RoleSelect) or isinstance(item, discord.ui.ChannelSelect):
                if len(item.values) > 0:
                    if item.placeholder == "Shift Management":
                        modifications['shift_management']['enabled'] = bool(item.values[0] == "enabled")
                    elif item.placeholder == "Shift Channel":
                        modifications['shift_management']['channel'] = item.values[0].id
                    elif item.placeholder == "On-Duty Role":
                        modifications['shift_management']['role'] = [role.id for role in item.values]

        new_configuration = copy(base_configuration)
        new_configuration.update(modifications)
        new_configuration['_id'] = ctx.guild.id
        await bot.settings.upsert(new_configuration)
        await msg.edit(
            embed=discord.Embed(
                title='<:success:1163149118366040106> Success!',
                description="You are now setup with ERM, and have finished the Setup Wizard! You should now be able to use ERM in your staff team. If you'd like to change any of these settings, use `/config`!\n\n**ERM has lots more modules than what's mentioned here! You can enable them by going into `/config`!**",
                color=0x1fd373
            ),
            view=None
        )

    @commands.guild_only()
    @commands.hybrid_command(
        name="config",
        description='View your ERM settings',
        aliases=['settings'],
        extras={
            "category": "Configuration"
        }
    )
    @require_settings()
    @is_management()
    async def _config(self, ctx: commands.Context):
        bot = self.bot
        settings = await bot.settings.find_by_id(ctx.guild.id)

        if isinstance(ctx, commands.Context):
            await log_command_usage(self.bot,ctx.guild, ctx.author, f"Config")
        else:
            await log_command_usage(self.bot,ctx.guild, ctx.user, f"Config")

        basic_settings_view = BasicConfiguration(bot, ctx.author.id, [
            (
                'Staff Roles',
                [
                    discord.utils.get(ctx.guild.roles, id=role) for role in settings['staff_management'].get('role') or [0]
                ]
            ),
            (
                'Admin Role',
                [
                    discord.utils.get(ctx.guild.roles, id=role) for role in settings['staff_management'].get('admin_role') or [0]
                ]
            ),
            (
                'Management Roles',
                [
                    discord.utils.get(ctx.guild.roles, id=role) for role in settings['staff_management'].get('management_role', []) or [0]
                ]
            ),
            (
                'Prefix',
                [
                    ['CUSTOM_CONF', {
                        '_FIND_BY_LABEL': True
                    }],
                    settings['customisation'].get('prefix') if settings['customisation'].get('prefix') in ['!', '>', '?', ':'] else None
                ]

            )
        ])
        
        loa_config = settings['staff_management'].get('loa_role')
        if isinstance(loa_config, list):
            loa_roles = [discord.utils.get(ctx.guild.roles, id=i) for i in loa_config]
        elif isinstance(loa_config, int):
            loa_roles = [discord.utils.get(ctx.guild.roles, id=loa_config)]
        else:
            loa_roles = [0]

        loa_configuration_view = LOAConfiguration(bot, ctx.author.id, [
            (
                'LOA Requests',
                [
                    [
                        'CUSTOM_CONF', {
                            '_FIND_BY_LABEL': True
                        }
                    ],
                    'Enabled' if settings['staff_management'].get('enabled') is True else 'Disabled'
                ]
            ),
            (
                'LOA Role',
                loa_roles
            ),
            (
                'LOA Channel',
                [
                    discord.utils.get(ctx.guild.channels, id=channel) if (channel := settings['staff_management'].get('channel')) else 0
                ]
            )
        ])

        shift_management_view = ShiftConfiguration(bot, ctx.author.id, [
            (
                'On-Duty Role',
                [
                    discord.utils.get(ctx.guild.roles, id=role) for role in (settings['shift_management'].get('role') or [0])
                ]
            ),
            (
                'Shift Channel',
                [
                    discord.utils.get(
                        ctx.guild.channels,
                        id=channel
                    ) if (channel := settings['shift_management'].get('channel')) else 0
                ]
            ),
            (
                'Shift Management',
                [
                    ['CUSTOM_CONF',
                        {
                            '_FIND_BY_LABEL': True
                        }
                     ],
                    'Enabled' if settings['shift_management'].get('enabled') is True else 'Disabled'
                ],
            )
        ])

        ra_config = settings['staff_management'].get('ra_role')
        if isinstance(ra_config, list):
            ra_roles = [discord.utils.get(ctx.guild.roles, id=i) for i in ra_config]
        elif isinstance(ra_config, int):
            ra_roles = [discord.utils.get(ctx.guild.roles, id=ra_config)]
        else:
            ra_roles = [0]

        ra_view = RAConfiguration(bot, ctx.author.id, [
            (
                'RA Role',
                ra_roles
            )
        ])

        roblox_punishments = PunishmentsConfiguration(bot, ctx.author.id, [
            (
                'Punishments Channel',
                [
                    discord.utils.get(
                        ctx.guild.channels,
                        id=channel
                    ) if (channel := settings['punishments'].get('channel')) else 0
                ]
            ),
            (
                'ROBLOX Punishments',
                [
                    ['CUSTOM_CONF',
                     {
                         '_FIND_BY_LABEL': True
                     }
                     ],
                    'Enabled' if settings['punishments'].get('enabled') is True else 'Disabled'
                ],
            )
        ])

        security_view = GameSecurityConfiguration(bot, ctx.author.id,
            [
                (
                    'Game Security',
                    [
                        ['CUSTOM_CONF',
                         {
                             '_FIND_BY_LABEL': True
                         }
                         ],
                        'Enabled' if settings.get('game_security', {}).get('enabled') is True else 'Disabled'
                    ],
                ),
                (
                    'Alert Channel',
                    [discord.utils.get(ctx.guild.channels, id=channel) if (channel := settings.get('game_security', {}).get('channel')) else 0]
                ),
                (
                    'Webhook Channel',
                    [discord.utils.get(ctx.guild.channels, id=channel) if (
                        channel := settings.get('game_security', {}).get('webhook_channel')) else 0]
                ),
                (
                    'Mentionables',
                    [discord.utils.get(ctx.guild.roles, id=role) for role in (settings.get('game_security', {}).get('role') or [0])]
                )
            ]
        )

        logging_view = GameLoggingConfiguration(
            bot,
            ctx.author.id,
            [
                (
                    'Message Logging',
                    [
                        ['CUSTOM_CONF',
                         {
                             '_FIND_BY_LABEL': True
                         }
                         ],
                        'Enabled' if settings.get('game_logging', {}).get('message', {}).get('enabled', None) is True else 'Disabled'
                    ],
                ),
                (
                    'STS Logging',
                    [
                        ['CUSTOM_CONF',
                         {
                             '_FIND_BY_LABEL': True
                         }
                         ],
                        'Enabled' if settings.get('game_logging', {}).get('sts', {}).get('enabled',
                                                                                              None) is True else 'Disabled'
                    ],
                ),
                (
                    'Priority Logging',
                    [
                        ['CUSTOM_CONF',
                         {
                             '_FIND_BY_LABEL': True
                         }
                         ],
                        'Enabled' if settings.get('game_logging', {}).get('priority', {}).get('enabled',
                                                                                              None) is True else 'Disabled'
                    ],
                ),
            ]
        )

        antiping_view = AntipingConfiguration(
            bot,
            ctx.author.id,
            [
                (
                    'Anti-Ping',
                    [
                        ['CUSTOM_CONF',
                         {
                             '_FIND_BY_LABEL': True
                         }
                         ],
                        'Enabled' if settings.get('antiping', {}).get('enabled', None) is True else 'Disabled'
                    ],
                ),
                (
                    'Use Hierarchy',
                    [
                        ['CUSTOM_CONF',
                         {
                             '_FIND_BY_LABEL': True
                         }
                         ],
                        'Enabled' if settings.get('antiping', {}).get('use_hierarchy', None) is True else 'Disabled'
                    ],
                ),
                (
                    'Affected Roles',
                    [discord.utils.get(ctx.guild.roles, id=role) for role in
                     (settings.get('antiping', {}).get('role') or [0])]
                ),
                (
                    'Bypass Roles',
                    [discord.utils.get(ctx.guild.roles, id=role) for role in
                     (settings.get('antiping', {}).get('bypass_role') or [0])]
                )
            ]
        )

        erlc_view = ERLCIntegrationConfiguration(
            bot,
            ctx.author.id,
            [
                (
                    'Elevation Required',
                    [
                        ['CUSTOM_CONF',
                         {
                             '_FIND_BY_LABEL': True
                         }
                         ],
                        'Enabled' if (settings.get('ERLC', {}) or {}).get('elevation_required', True) is True else 'Disabled'
                    ],
                ),
                (
                    'Player Logs Channel',
                    [discord.utils.get(ctx.guild.channels, id=channel) if (
                        channel := (settings.get('ERLC', {}) or {}).get('player_logs')) else 0]
                ),
                (
                    'Kill Logs Channel',
                    [discord.utils.get(ctx.guild.channels, id=channel) if (
                        channel := (settings.get('ERLC', {}) or {}).get('kill_logs')) else 0]
                ),
            ]
        )
        
        erm_command_log_view = ERMCommandLog(
            bot,
            ctx.author.id,
            [
                (
                    'ERM Log Channel',
                    [discord.utils.get(ctx.guild.channels, id=channel) if (
                        channel := settings.get('staff_management', {}).get('erm_log_channel')) else 0]
                )
            ]
        )

        pages = []

        for index, view in enumerate([basic_settings_view, loa_configuration_view, shift_management_view, ra_view, roblox_punishments, security_view, logging_view, antiping_view, erlc_view, erm_command_log_view]):
            corresponding_embeds = [
                discord.Embed(
                    title="Basic Settings",
                    description=(
                        "**Staff Role:** A staff role is the role that is going to be able to use most ERM commands. You'd assign this role to the people you want to be able to use ERM's core functionalities.\n\n"
                        "**Admin Role:** An admin role is the role that can manage LOAs, RAs & other peoples' shifts but it can not use server manage and config.\n\n"
                        "**Management Role:** A management role is the roles of your server management members. These people will be able to delete punishments, modify people's shift time, and accept LOA Requests.\n\n"
                        "**Prefix:** This will be a prefix you are able to use instead of our slash command system. You can use this prefix to execute commands slightly faster and to take advantage of some extra features."
                    ),
                    color=blank_color
                ),
                discord.Embed(
                    title="LOA Requests",
                    description=(
                        "**Enabled:** This setting enables or disables the LOA Requests module. When enabled, this allows your staff members to fill out Leave of Absence requests for your management members to approve.\n\n"
                        "**LOA Role:** This role is given to those who are on Leave of Absence, and is removed when they go off Leave of Absence.\n\n"
                        "**LOA Channel:** This channel will be where Leave of Absence requests will be logged, and where they will be accepted or denied. Make sure this is a channel that Management members can see, so that they can approve LOA requests."
                    ),
                    color=blank_color
                ),
                discord.Embed(
                    title="Shift Management",
                    description=(
                        "**What is Shift Management?** The Shift Management module allows for staff members to log how much time they were in-game, or moderating, or on as a staff member. It allows for a comprehensive guide of who is the most active in your staff team.\n\n"
                        "**Enabled:** When enabled, staff members will be able to run `/duty` commands to manage their shift, see how much time they have, as well as see how much time other people have. Management members will be able to administrate people's shifts, add time, remove time, and clear people's shifts.\n\n"
                        "**Shift Chanel:** This is where all shift logs will go to. This channel will be used for all modifications to shifts, any person that may be starting or ending their shift.\n\n"
                        "**On-Duty Role:** When someone is on shift, they will be given this role. When the staff member goes off shift, this role will be removed from them."
                    ),
                    color=blank_color
                ),
                discord.Embed(
                    title="RA Requests",
                    description=(
                        "**What are RA Requests?** RA Requests, also called Reduced Activity Requests, are a form of Leave of Absence where the staff member isn't required to complete the full quota, but expects that they will be able to complete it partially.\n\n"
                        "**RA Role:** This role is given to those who are on Reduced Activity, and is removed when they go off Reduced Activity.\n\n"
                    ),
                    color=blank_color
                ),
                discord.Embed(
                    title="ROBLOX Punishments",
                    description=(
                        "**What is the ROBLOX Punishments module?** The ROBLOX Punishments module allows for members of your Staff Team to log punishments against a ROBLOX player using ERM! You can specify custom types of punishments, where they will go, as well as manage and search individual punishments.\n\n"
                        "**Enabled:** This setting toggles the ROBLOX Punishments module. When enabled, staff members will be able to use `/punish`, and management members will be able to additionally use `/punishment manage`.\n\n"
                        "**Punishments Channel:** This is where most punishments made with the ROBLOX Punishments go. Any logged actions of a ROBLOX player will go to this channel."
                    ),
                    color=blank_color
                ),
                discord.Embed(
                    title="Game Security",
                    description=(
                        "**What is the Game Security module?** As of right now, this module only applies to private servers of Emergency Response: Liberty County. This module aims to protect and secure private servers by detecting if a staff member runs a potentially abusive command, and notifying management of this incident.\n\n"
                        "**Enabled:** Game Security is a module that aims to protect private servers from abuse of administrative privileges. This only works for particular games and servers. You should disable this if you aren't a game listed above.\n\n"
                        "**Webhook Channel:** This channel is where the bot will read the webhooks from the game server. This is not where alerts will be sent. Rather, this is where the bot will detect any admin abuse.\n\n"
                        "**Alert Channel:** This channel is where the bot will send the corresponding alerts for abuse of administrative privileges in your private server. It is recommended for this not to be the same as your Webhook Channel so that you don't miss any unresolved Security Alerts.\n\n"
                        "**Mentionables:** These roles will be mentioned when a security alert is sent by ERM. All of these roles will be mentioned in the message, and they should be able to deal with the situation at hand for maximum staff efficiency."

                    ),
                    color=blank_color
                ),
                discord.Embed(
                    title="Game Logging",
                    color=blank_color,
                    description=(
                        "**What is Game Logging?** Game Logging is an ERM module, particularly tailored towards private servers of Emergency Response: Liberty County, but can apply to other roleplay games in a similar genre. Game Logging allows for staff members to log events of interest, such as custom in-game messages, priority timers, as well as STS events. This allows for streamlined management of staff efficiency.\n\n"
                        "### Message Logging\n\n"
                        "**Enabled:** This dictates whether the in-game message section of the Game Logging module is enabled. This part of the module automatically and allows for manual logs of in-game messages and 'hints' so that management can effectively see if staff members are sending the correct amount of notifications.\n\n"
                        "**Message Logging Channel:** This channel will be where these message and notification logs will be sent to.\n\n"
                        "### STS Logging\n\n"
                        "**Enabled:** This dictates whether the Shoulder-to-Shoulder event logging section of the Game Logging module is enabled. When enabled, staff members can log the duration of their events, as well as who hosted them and other important information.\n\n"
                        "**STS Logging Channel:** This is where the event logs for Shoulder-to-Shoulder events will appear. Management members will be able to see all relevant information of an STS here.\n\n"
                        "### Priority Logging\n\n"
                        "**Enabled:** This section of the Game Logging module, correspondingly named the Priority Logging part, allows for staff members to log Priority Timer events, their reason, duration, as well as any notable information which may be necessary for management members.\n\n"
                        "**Priority Logging Channel:** This channel will be where priority timer events and event notifications will be logged accordingly for management members to view."
                    )
                ),
                discord.Embed(
                    title="Anti-Ping",
                    color=blank_color,
                    description=(
                        "**What is Anti-Ping?** Anti-ping is an ERM module which specialises in preventing mention abuse of High Ranks within a Discord server. ERM detects if an unauthorized individual mentions a High Ranking individual, and notifies them to discontinue any further attempts to violate the server's regulations.\n\n"
                        "**Enabled:** This setting dictates whether ERM will take action upon these users, and intervene when necessary. When disabled, the Anti-Ping module will not activate.\n\n"
                        "**Affected Roles:** These roles clarify the individuals who are affected by Anti-Ping, and are classed as important individuals to ERM. An individual who pings someone with these affected roles, will activate Anti-Ping.\n\n"
                        "**Bypass Roles:** An individual who holds one of these roles will not be able to trigger Anti-Ping filters, and will be able to ping any individual within the Affected Roles list without ERM intervening.\n\n"
                        "**Use Hierarchy:** This setting dictates whether Anti-Ping will take into account role hierarchy for each of the affected roles. For example, if you set Moderation as an affected role, it would also apply for all roles above Moderation, such as Administration or Management."
                    )
                ),
                discord.Embed(
                    title="ER:LC Integration",
                    color=blank_color,
                    description=(
                        "**What is the ER:LC Integration?** ER:LC Integration allows for ERM to communicate with the Police Roleplay Community APIs, and your Emergency Response: Liberty County server. In particular, these configurations allow for Join Logs, Leave Logs, and Kill Logs to be logged.\n\n"
                        "**Elevation Required:** This setting dictates whether elevated permissions are required to run commands such as `:admin` and `:unadmin`. In such case where this is enabled, Co-Owner permissions are required to run these commands to prevent security risk. If disabled, those with the Management Roles in your server can run these commands. **It is advised you keep this enabled unless you have a valid reason to turn it off.** Contact ERM Support if you are unsure what this setting does.\n\n"
                        "**Player Logs Channel:** This channel is where Player Join and Leave logs will be sent by ERM. ERM will check your server every 45 seconds to see if new members have joined or left, and report of their time accordingly.\n\n"
                        "**Kill Logs Channel:** This setting is where Kill Logs will be sent by ERM. ERM will check your server every 45 seconds and constantly contact your ER:LC private server to know if there are any new kill logs. If there are, to log them in the corresponding channel."
                    )
                ),
                discord.Embed(
                    title="ERM Logging",
                    color=blank_color,
                    description=(
                        "**ERM Log Channel:** This channel is where ERM will log all administrative commands and configuration changes made by Admin & Management Roles. This is useful for auditing purposes, ensuring transparency, and detecting any potential abuse of administrative privileges. This is a critical part of ERM and should be enabled for all servers using ERM.\n\n"
                        "All commands such as Duty Admin, LOA Admin, RA Admin, Server Manage, Config, etc., as well as nearly all configuration changes, will be logged in this channel."
                    )
                )

            ]
            embed = corresponding_embeds[index]
            page = CustomPage()
            page.embeds = [embed]
            page.identifier = embed.title
            page.view = view

            pages.append(
                page
            )



        paginator = SelectPagination(ctx.author.id, pages)
        try:
            await ctx.send(embeds=pages[0].embeds, view=paginator.get_current_view())
        except discord.HTTPException:
            await ctx.send(embed=discord.Embed(
                title="Critical Error",
                description="Configuration error; 827",
                color=BLANK_COLOR
            ))

    @commands.hybrid_group(name="server", description="This is a namespace for commands relating to the Server Management functionality", extras={
        'category': 'Configuration'
    })
    async def server(self, ctx: commands.Context):
        pass

    @commands.guild_only()
    @server.command(
        name="manage",
        description="Manage your server's ERM data!",
        extras={
            "category": "Configuration"
        }
    )
    @is_management()
    @require_settings()
    async def server_management(self, ctx: commands.Context):
        if isinstance(ctx, commands.Context):
            await log_command_usage(self.bot,ctx.guild, ctx.author, f"Server Manage")
        else:
            await log_command_usage(self.bot,ctx.guild, ctx.user, f"Server Manage")

        embeds = [
            discord.Embed(
                title="Introduction",
                description=
                (
                    "This **Server Management Panel** allows individuals who have access to it, to manage your data regarding ERM on your server. This contains any of the data contained within the 3 main modules, which are Activity Notices, ROBLOX Punishments, and Shift Logging.\n\n"
                    "Using this panel, you can clear certain parts of data, or erase the data of a particular module in its entirety. For some modules, you can also erase its data by a particular specification - such as removing all punishments from a punishment type.\n\n"
                    "Members with **Management** permissions can access this panel, and erase your server's data, so ensure you only give this access to people who you trust. As with particular parts of this panel, some actions are reversible when contacting ERM Support."
                ),
                color=BLANK_COLOR
            ).set_author(
                name=ctx.guild.name,
                icon_url=ctx.guild.icon
            ),
            discord.Embed(
                title="Activity Notices",
                description=(
                    "Activity Notices allow for routine and robust staff management and administration, with the implementation of Leave of Absence requests and Reduced Activity requests. Staff members can request for one of these facilities, and Management can approve and deny on a case-by-case basis.\n\n"
                    "Using this panel, you can perform 3 actions. You can **Erase Pending Requests** to remove all ongoing Activity Notice requests. You can also **Erase LOA Notices** and **Erase RA Notices** to erase their correspondent activity notices. **These will not automatically remove the LOA or RA roles, as these actions only erase these notices from our database.**"
                ),
                color=BLANK_COLOR
            ).set_author(
                name=ctx.guild.name,
                icon_url=ctx.guild.icon
            ),
            discord.Embed(
                title="ROBLOX Punishments",
                description=(
                    "ROBLOX Punishments allow for staff members to log their punishments on the ROBLOX platform using ERM. ERM allows a robust experience for a staff member utilising this module, as commands are easy to learn and execute, as well as to effectively be implemented into a staff member's workflow.\n\n"
                    "Using this panel, you can **Erase All Punishments**, as well as **Erase Punishments By Type** and **Erase Punishments By Username**."
                ),
                color=BLANK_COLOR
            ).set_author(
                name=ctx.guild.name,
                icon_url=ctx.guild.icon
            ),
            discord.Embed(
                title="Shift Logging",
                description=(
                    "Shift Logging allow for an easy experience for staff members looking to log their active shift time using ERM. Staff members can run simple commands to go \"on-duty\", as well as go on break to signify unavailability. Once they are ready, they can go \"off-duty\" to signify that they are no longer available for any administrative action.\n\n"
                    "Using this panel, you can **Erase All Shifts**, as well as utilise **Erase Past Shifts** and **Erase Active Shifts**. You can also **Erase Shifts By Type**."
                ),
                color=BLANK_COLOR
            ).set_author(
                name=ctx.guild.name,
                icon_url=ctx.guild.icon
            )
        ]
        views = [
            discord.ui.View(),
            ActivityNoticeManagement(self.bot, ctx.author.id),
            PunishmentManagement(self.bot, ctx.author.id),
            ShiftLoggingManagement(self.bot, ctx.author.id)
        ]

        paginator = SelectPagination(ctx.author.id, [
            CustomPage(embeds=[embed], identifier=embed.title, view=view) for embed, view in zip(embeds, views)
        ])

        await ctx.send(embed=embeds[0], view=paginator.get_current_view())








async def setup(bot):
    await bot.add_cog(Configuration(bot))
