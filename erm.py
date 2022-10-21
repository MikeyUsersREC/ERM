import datetime
from io import BytesIO
import json
import random
import time
from discord.ext import commands, tasks
import discord
from decouple import config
import motor.motor_asyncio
import pytz
import requests
from snowflake import SnowflakeGenerator
import DiscordUtils
import sentry_sdk
from sentry_sdk import capture_exception, push_scope
from menus import CustomSelectMenu, SettingsSelectMenu, Setup, YesNoMenu
from utils.mongo import Document
from roblox import client as roblox
from discord import app_commands
from zuid import ZUID
from utils.timestamp import td_format
import logging

sentry_url = config('SENTRY_URL')

sentry_sdk.init(
	sentry_url,
	traces_sample_rate=1.0
)

discord.utils.setup_logging()


def removesuffix(input_string, suffix):
	if suffix and input_string.endswith(suffix):
		return input_string[:-len(suffix)]
	return input_string


def get_guild_icon(guild: discord.Guild):
	if guild.icon is None:
		return bot.user.avatar.url
	else:
		return guild.icon.url


async def get_prefix(bot, message):
	if not message.guild:
		return commands.when_mentioned_or('>')(bot, message)

	try:
		prefix = await bot.settings.find_by_id(message.guild.id)
		prefix = prefix['customisation']['prefix']
	except:
		return discord.ext.commands.when_mentioned_or('>')(bot, message)

	return commands.when_mentioned_or(prefix)(bot, message)


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.AutoShardedBot(command_prefix=get_prefix, case_insensitive=True, intents=intents, help_command=None)
bot.is_synced = False
environment = config('ENVIRONMENT', default='DEVELOPMENT')

@bot.before_invoke
async def DeferInteraction(ctx):
	if isinstance(ctx, discord.Interaction):
		await ctx.defer()
@bot.event
async def on_ready():
	await bot.wait_until_ready()

	# load IPC extension
	try:
		await bot.load_extension('utils.routes')
		logging.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n{} is online!'.format(bot.user.name))
		global startTime
		startTime = time.time()
		change_status.start()
		update_bot_status.start()
		GDPR.start()
		bot.mongo = motor.motor_asyncio.AsyncIOMotorClient(str(mongo_url))
		if environment == 'DEVELOPMENT':
			bot.db = bot.mongo['beta']
		elif environment == "PRODUCTION":
			bot.db = bot.mongo["erm"]
		else:
			raise Exception("Invalid enviroment")

		bot.start_time = time.time()
		bot.warnings = Document(bot.db, "warnings")
		bot.settings = Document(bot.db, "settings")
		bot.shifts = Document(bot.db, "shifts")
		bot.errors = Document(bot.db, "errors")
		bot.shift_storage = Document(bot.db, "shift_storage")
		bot.error_list = []
		logging.info('Connected to MongoDB!')

		await bot.load_extension('jishaku')
		if not bot.is_synced:  # check if slash commands have been synced
			bot.tree.copy_global_to(guild=discord.Object(id=987798554972143728))
			for item in bot.tree._get_all_commands():
				logging.info(item.name)
		if environment == 'DEVELOPMENT':
			await bot.tree.sync(guild=discord.Object(id=987798554972143728))
		else:
			await bot.tree.sync()  # guild specific: leave blank if global (global registration can take 1-24 hours)
		bot.is_synced = True
	except commands.errors.ExtensionAlreadyLoaded:
		logging.info('Already loaded extensions + bot. (Sharded)')


client = roblox.Client()

def is_staff():
	async def predicate(ctx):
		guild_settings = await bot.settings.find_by_id(ctx.guild.id)
		if guild_settings:
			if 'role' in guild_settings['staff_management'].keys():
				if guild_settings['staff_management']['role'] != "":
					if guild_settings['staff_management']['role'] in [role.id for role in ctx.author.roles]:
						return True
		if ctx.author.guild_permissions.manage_messages:
			return True

		return False
	return commands.check(predicate)

async def warning_json_to_mongo(jsonName: str, guildId: int):
	f = None
	with open(f'{jsonName}', 'r') as f:
		logging.info(f)
		f = json.load(f)

	logging.info(f)

	for key, value in f.items():
		structure = {
			'_id': key.lower(),
			'warnings': []
		}
		logging.info([key, value])
		logging.info(key.lower())

		if await bot.warnings.find_by_id(key.lower()):
			data = await bot.warnings.find_by_id(key.lower())
			for item in data['warnings']:
				structure['warnings'].append(item)

		for item in value:
			item.pop('ID', None)
			item['id'] = next(generator)
			item['Guild'] = guildId
			structure['warnings'].append(item)

		logging.info(structure)

		if await bot.warnings.find_by_id(key.lower()) == None:
			await bot.warnings.insert(structure)
		else:
			await bot.warnings.update(structure)


bot.staff_members = {
	"i_imikey": "Bot Developer",
	"kiper4k": "Support Team",
	"mbrinkley": "Lead Support",
	"ruru0303": "Support Team",
	"myles_cbcb1421": "Support Team",
	"theoneandonly_5567": "Manager",
	"l0st_nations": "Junior Support"
}


async def staff_field(embed, query):
	embed.add_field(name="Flags",
					value=f"<:erm:1001323537023389817>  **ERM Staff Member** ({bot.staff_members[query.lower()]})",
					inline=False)
	return embed


bot.warning_json_to_mongo = warning_json_to_mongo

bot.colors = {
	"WHITE": 0xFFFFFF,
	"AQUA": 0x1ABC9C,
	"GREEN": 0x2ECC71,
	"BLUE": 0x3498DB,
	"PURPLE": 0x9B59B6,
	"LUMINOUS_VIVID_PINK": 0xE91E63,
	"GOLD": 0xF1C40F,
	"ORANGE": 0xE67E22,
	"RED": 0xE74C3C,
	"NAVY": 0x34495E,
	"DARK_AQUA": 0x11806A,
	"DARK_GREEN": 0x1F8B4C,
	"DARK_BLUE": 0x206694,
	"DARK_PURPLE": 0x71368A,
	"DARK_VIVID_PINK": 0xAD1457,
	"DARK_GOLD": 0xC27C0E,
	"DARK_ORANGE": 0xA84300,
	"DARK_RED": 0x992D22,
	"DARK_NAVY": 0x2C3E50,
}
bot.color_list = [c for c in bot.colors.values()]


async def generate_random(ctx) -> discord.Color:
	if await bot.settings.find_by_id(ctx.guild.id):
		settings = await bot.settings.find_by_id(ctx.guild.id)
		if settings['customisation']['color'] != "":
			return settings['customisation']['color']

	RandomNumber = random.randint(0, len(bot.color_list) - 1)
	return bot.color_list[RandomNumber]


bot.generate_random = generate_random

# include environment variables
if environment == "PRODUCTION":
	bot_token = config('PRODUCTION_BOT_TOKEN')
	logging.info('Using production token...')
elif environment == "DEVELOPMENT":
	bot_token = config('DEVELOPMENT_BOT_TOKEN')
	logging.info('Using development token...')
else:
	raise Exception("Invalid enviroment")
mongo_url = config('MONGO_URL')
github_token = config('GITHUB_TOKEN')
generator = SnowflakeGenerator(192)
error_gen = ZUID(prefix="error_", length=10)


async def requestResponse(ctx, question):
	await ctx.send(question)
	try:
		response = await bot.wait_for('message', check=lambda message: message.author == ctx.author, timeout=300)
	except:
		raise Exception('No response')
	return response


# status change discord.ext.tasks
@tasks.loop(seconds=10)
async def change_status():
	mcl = [guild.member_count for guild in bot.guilds]
	member_count = sum(mcl)

	status = [
		'Emergency Response: Liberty County',
		'Roblox',
		'with the owners',
		'some games',
		'[L] commands',
		'games with Shawnyg',
		'games with mrfergie',
		'[L] punishments',
		'[W] over staff members'
		'[W] over everyone',
		f'[W] over {len(bot.guilds)} servers',
		f'[W] over {member_count} users',
		'virtual reality games',
		'[W] PRC on Twitch',
		'[L] \'Created by Mikey!\'',
		'[L] \'not officially endorsed by PRC\'',
		'[L] \'not affiliated with PRC\'',
		"[N] Version [R]"
	]

	chosen = random.choice(status)
	if chosen.startswith('[W] '):
		await bot.change_presence(status=discord.Status.online,
								  activity=discord.Activity(type=discord.ActivityType.watching, name=chosen[4:]))
	elif chosen.startswith('[L] '):
		await bot.change_presence(status=discord.Status.online,
								  activity=discord.Activity(type=discord.ActivityType.listening, name=chosen[4:]))
	elif chosen.startswith('[C] '):
		await bot.change_presence(status=discord.Status.online,
								  activity=discord.Activity(type=discord.ActivityType.custom, name=chosen[4:]))
	elif chosen.startswith('[N] '):
		request = requests.get('https://api.github.com/repos/mikeyusersrec/erm/commits', headers={
			"Accept": "application/vnd.github+json",
			"Authorization": f"Bearer {github_token}"
		})
		requestjson = request.json()
		requestResponse = requestjson[0]['sha'][:7]
		chosen = chosen.replace('[R]', requestResponse)
		chosen = chosen[4:]
		await bot.change_presence(status=discord.Status.online, activity=discord.Game(name=chosen))
	else:
		await bot.change_presence(status=discord.Status.online, activity=discord.Game(name=chosen))


# status change discord.ext.tasks
@tasks.loop(seconds=30)
async def update_bot_status():
	try:
		# get channel from bot
		channel = bot.get_channel(988082136542236733)
		# get last message from channel
		last_message = None
		async for message in channel.history(limit=1):
			last_message = message
		# get last message content
		if last_message == None:
			embed = discord.Embed(
				title='Bot Status',
				color=discord.Color.red()
			)
			embed.set_thumbnail(url=bot.user.avatar.url)
			embed.add_field(name='Last ping', value=f'<t:{int(datetime.datetime.now().timestamp())}:R>')
			embed.add_field(name='Status', value='<:online:989218581764014161> Online')
			embed.add_field(name='Pings', value='1')
			embed.add_field(name='Note',
							value=f'This is updated every 30 seconds. If you see the last ping was over 30 seconds ago, contact {discord.utils.get(channel.guild.members, id=635119023918415874).mention}',
							inline=False)

			await channel.send(embed=embed)
		else:
			last_embed = last_message.embeds[0]
			pings = None

			for field in last_embed.fields:
				if field.name == 'Pings':
					pings = int(field.value)

			embed = discord.Embed(
				title='Bot Status',
				color=discord.Color.red()
			)
			embed.set_thumbnail(url=bot.user.avatar.url)
			embed.add_field(name='Last ping', value=f'<t:{int(datetime.datetime.now().timestamp())}:R>')
			embed.add_field(name='Status', value='<:online:989218581764014161> Online')
			embed.add_field(name='Pings', value=str(pings + 1))
			embed.add_field(name='Note',
							value=f'This is updated every 30 seconds. If you see the last ping was over 30 seconds ago, contact {discord.utils.get(channel.guild.members, id=635119023918415874).mention}',
							inline=False)

			await last_message.edit(embed=embed)
	except:
		logging.info('Failing updating the status.')


@tasks.loop(hours=24)
async def GDPR():
	# if the date in each warning is more than 30 days ago, redact the staff's username and tag
	# using mongodb (warnings)
	# get all warnings
	warnings = await bot.warnings.get_all()
	# iterate through each warning, to check the date via the time variable stored in "d/m/y h:m:s"
	for userentry in warnings:
		for warning in userentry['warnings']:
			try:
				date = datetime.datetime.strptime(warning['Time'], '%m/%d/%Y, %H:%M:%S')
				now = datetime.datetime.now()
				diff = now - date
				diff_days = diff.days
				if diff_days > 30:
					# get the staff's id
					if type(warning['Moderator']) == list:
						warning['Moderator'][0] = "[redacted ~ GDPR]"
					else:
						warning['Moderator'] = "[redacted ~ GDPR]"

						await bot.warnings.update_by_id(userentry)
			except:
				pass


@bot.event
async def on_command_error(ctx, error):
	error_id = error_gen()
	if isinstance(error, commands.CommandNotFound):
		return

	try:
		embed = discord.Embed(
			title='Error',
			color=discord.Color.red()
		)

		embed.add_field(name='Explanation',
						value="An error has occured whilst running this command. To gain more information about this error and how to prevent it, please contact us in our support server and provide the error ID below.")
		embed.add_field(name="Error", value=str(error))
		embed.add_field(name='Error ID', value=f"`{error_id}`", inline=False)
		embed.add_field(name="Support Server", value="[Click here](https://discord.gg/5pMmJEYazQ)", inline=True)

		await ctx.send(embed=embed)
	except Exception as e:
		logging.info(e)
	finally:
		with push_scope() as scope:
			scope.set_tag('error_id', error_id)
			scope.level = 'error'
			await bot.errors.insert({
				"_id": error_id,
				"error": str(error),
				"time": datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
				"channel": ctx.channel.id,
				"guild": ctx.guild.id
			})
			capture_exception(error)


@bot.event
async def on_guild_join(guild: discord.Guild):
	logging.info(f'{bot.user.name} has been added to a new server!')
	logging.info('List of servers the bot is in: ')

	for guild in bot.guilds:
		logging.info(f'  - {guild.name}')

	try:
		await guild.system_channel.send(
			'Hello! I am the Emergency Response Management bot!\n\nFor me to work properly, you need to set me using `>setup`. If you need help, contact me on Discord at Mikey#0008 or at the support server below. Other than that, have a good day! :wave:\n\nhttps://discord.gg/BGfyfqU5fx'
		)
	except:
		await guild.owner.send(
			'Hello! I am the Emergency Response Management bot!\n\nFor me to work properly, you need to set me using `>setup`. If you need help, contact me on Discord at Mikey#0008. Other than that, have a good day! :wave:\n\nhttps://discord.gg/BGfyfqU5fx'
		)
	finally:
		channel = bot.get_channel(1033021466381398086)
		await channel.send(f'{bot.user.name} is now in **{len(bot.guilds)} servers**.')
		logging.info('Server has been sent welcome sequence.')


@bot.event
async def on_message(message: discord.Message):
	bypass_role = None

	if message.author == bot.user:
		return

	if message.author.bot:
		return

	if not message.guild:
		await bot.process_commands(message)
		return

	dataset = await bot.settings.find_by_id(message.guild.id)
	if dataset == None:
		await bot.process_commands(message)
		return

	if "bypass_role" in dataset['antiping'].keys():
		bypass_role = dataset['antiping']['bypass_role']

	if dataset['antiping']['enabled'] == False or dataset['antiping']['role'] == None:
		await bot.process_commands(message)
		return

	bypass_role = discord.utils.get(message.guild.roles, id=bypass_role)
	AntipingRole = discord.utils.get(message.guild.roles, id=dataset['antiping']['role'])

	if AntipingRole == None:
		await bot.process_commands(message)
		return

	if bypass_role != None:
		if bypass_role in message.author.roles:
			await bot.process_commands(message)
			return

	for mention in message.mentions:
		isStaffPermitted = False
		logging.info(isStaffPermitted)

		if mention.bot:
			await bot.process_commands(message)
			return

		if mention == message.author:
			await bot.process_commands(message)
			return

		if message.author.top_role.position > AntipingRole.position or message.author.top_role.position == AntipingRole.position:
			await bot.process_commands(message)
			return

		if message.author == message.guild.owner:
			await bot.process_commands(message)
			return

		if not isStaffPermitted:
			if mention.top_role.position > AntipingRole.position:
				Embed = discord.Embed(
					title=f'Do not ping {AntipingRole.name} or above!',
					color=discord.Color.red(),
					description=f'Do not ping {AntipingRole.name} or above!\nIt is a violation of the rules, and you will be punished if you continue.'
				)
				try:
					msg = await message.channel.fetch_message(message.reference.message_id)
					if msg.author == mention:
						Embed.set_image(url="https://i.imgur.com/pXesTnm.gif")
				except:
					pass

				Embed.set_footer(text=f'Thanks, {dataset["customisation"]["brand_name"]}',
								 icon_url=get_guild_icon(message.guild))

				ctx = await bot.get_context(message)
				await ctx.reply(f'{message.author.mention}', embed=Embed)
				return
		else:
			await bot.process_commands(message)
			return
	await bot.process_commands(message)


@bot.hybrid_command(
	name='setup',
	description='Sets up the bot for use.',
	brief='Sets up the bot for use. [Configuration]',
	aliases=['setupbot'],
	with_app_command=True,
)
@is_staff()
async def setup(ctx):

	settingContents = {
		'_id': 0,
		'verification': {
			'enabled': False,
			'role': None,
		},
		'antiping': {
			'enabled': False,
			'role': None,
			"role_bypass": "None"
		},

		'staff_management': {
			'enabled': False,
			'channel': None
		},
		'punishments': {
			'enabled': False,
			'channel': None
		},
		'shift_management': {
			'enabled': False,
			'channel': None,
			'role': None
		},
		'customisation': {
			'color': '',
			'prefix': '>',
			'brand_name': 'Emergency Response Management',
			'thumbnail_url': '',
			'footer_text': 'Staff Logging Systems',
			'ban_channel': None
		}
	}

	await ctx.send(
		':wave: Hey! Welcome to the setup tool. We\'ll need a few things from you to get the bot up and running.')

	view = Setup(ctx.author.id)
	await ctx.send(
		'What features do you want enabled? (default: `all`)\n\n- All (recommended)\n- Staff management\n- Punishments\n- Shift management',
		view=view)

	await view.wait()
	if view.value == 'all' or view.value == 'default':
		settingContents['staff_management']['enabled'] = True
		settingContents['punishments']['enabled'] = True
		settingContents['shift_management']['enabled'] = True
	elif view.value == 'punishments':
		settingContents['punishments']['enabled'] = True
	elif view.value == 'shift management':
		settingContents['shift_management']['enabled'] = True
	elif view.value == 'staff management':
		settingContents['staff_management']['enabled'] = True
	else:
		return await ctx.send(':gear: You have took too long to respond. Please try again.')

	if settingContents['staff_management']['enabled']:
		question = 'What channel do you want to use for staff management? (e.g. LOA requests, demotions, etc.)'
		content = (await requestResponse(ctx, question)).content
		convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
		settingContents['staff_management']['channel'] = convertedContent.id

	if settingContents['punishments']['enabled']:
		content = (await requestResponse(ctx, 'What channel do you want to use for punishments?')).content
		convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
		settingContents['punishments']['channel'] = convertedContent.id
	if settingContents['shift_management']['enabled']:
		content = (await requestResponse(ctx,
										 'What channel do you want to use for shift management? (e.g. shift signups, etc.)')).content
		convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
		settingContents['shift_management']['channel'] = convertedContent.id

	settingContents['_id'] = ctx.guild.id
	if not await bot.settings.find_by_id(ctx.guild.id):
		await bot.settings.insert(settingContents)
	else:
		await bot.settings.update_by_id(settingContents)

	await ctx.send(
		'Successfully set up the bot! You can now use it as usual. If you ever want to change any of these settings, feel free to run this command again. :wave:')


@bot.hybrid_command(
	name='quicksetup',
	description='Sets up the bot for use. Not recommended for non-experienced users. [Configuration]',
	aliases=['qsetup'],
	with_app_command=True,
)
@is_staff()
async def quicksetup(ctx, featuresenabled='default', staffmanagementchannel: discord.TextChannel = None,
					 punishmentschannel: discord.TextChannel = None,
					 shiftmanagementchannel: discord.TextChannel = None):
	## Setup sequence;
	## 1. What features do you want enabled?
	## - Staff management
	## - Punishments
	## - Shift management

	## 2. Punishment system: what channel do you want to use for punishments?
	## 3. Staff management: what channel do you want to use for staff management? (e.g. LOA requests, demotions, etc.)
	## 4. Shift management: what channel do you want to use for shift management? (e.g. shift signups, etc.)

	settingContents = {
		'_id': 0,
		'verification': {
			'enabled': False,
			'role': None,
		},
		'antiping': {
			'enabled': False,
			'role': None,
			"role_bypass": "None"
		},

		'staff_management': {
			'enabled': False,
			'channel': None
		},
		'punishments': {
			'enabled': False,
			'channel': None
		},
		'shift_management': {
			'enabled': False,
			'channel': None,
			'role': None
		},
		'customisation': {
			'color': '',
			'prefix': '>',
			'brand_name': 'Emergency Response Management',
			'thumbnail_url': '',
			'footer_text': 'Staff Logging Systems',
			'ban_channel': None,
			"server_code": None
		}
	}

	view = YesNoMenu(ctx.author.id)
	await ctx.send(
		'Are you sure you want to run this comamnd? If you have any settings saved with ERM, they will be reset to factory default.',
		view=view)
	await view.wait()

	if view.value != True:
		return await ctx.send('Cancelled.')

	if featuresenabled == 'all' or featuresenabled == 'default':
		settingContents['staff_management']['enabled'] = True
		settingContents['punishments']['enabled'] = True
		settingContents['shift_management']['enabled'] = True
	elif featuresenabled == 'punishments':
		settingContents['punishments']['enabled'] = True
	elif featuresenabled == 'shift_management':
		settingContents['shift_management']['enabled'] = True
	elif featuresenabled == 'staff_management':
		settingContents['staff_management']['enabled'] = True
	else:
		await ctx.send(
			'Invalid argument 0. Please pick one of the options. `staff_management`, `punishments`, `shift_management`, `default`, `all`.')

	if settingContents['staff_management']['enabled']:
		if staffmanagementchannel != None:
			settingContents['staff_management']['channel'] = staffmanagementchannel.id
			await ctx.send('Successfully set the staff management channel to `{}`.'.format(staffmanagementchannel.name))

	if settingContents['punishments']['enabled']:
		if punishmentschannel != None:
			settingContents['punishments']['channel'] = punishmentschannel.id
			await ctx.send('Successfully set the punishments channel to `{}`.'.format(punishmentschannel.name))
	if settingContents['shift_management']['enabled']:
		if shiftmanagementchannel != None:
			settingContents['shift_management']['channel'] = shiftmanagementchannel.id
			await ctx.send('Successfully set the shift management channel to `{}`.'.format(shiftmanagementchannel.name))

	settingContents['_id'] = ctx.guild.id
	if not await bot.settings.find_by_id(ctx.guild.id):
		await bot.settings.insert(settingContents)
	else:
		await bot.settings.update_by_id(settingContents)

	await ctx.send(
		'Quicksetup is now completed. You can now use it as usual. If you ever want to change any of these settings, feel free to run the `>config` command.')


@bot.hybrid_group(
	name='config'
)
@commands.has_permissions(manage_guild=True)
@app_commands.checks.has_permissions(manage_guild=True)
async def config(ctx, option: str = None):
	if option == None:
		option = 'view'

	if not await bot.settings.find_by_id(ctx.guild.id):
		await ctx.send('This server has not yet been set up. Please run `>setup` to set it up.')
		return

	settingContents = await bot.settings.find_by_id(ctx.guild.id)

	if option == 'view':
		try:
			verification_role = ctx.guild.get_role(settingContents['staff_management']['verification_role']).mention
		except:
			verification_role = 'None'
		try:
			shift_role = ctx.guild.get_role(settingContents['shift_management']['role']).mention
		except:
			shift_role = 'None'
		try:
			antiping_role = ctx.guild.get_role(settingContents['anti_ping']['role']).mention
		except:
			antiping_role = 'None'

		try:
			bypass_role = ctx.guild.get_role(settingContents['anti_ping']['bypass_role']).mention
		except:
			bypass_role = 'None'

		# staff management channel
		try:
			staff_management_channel = ctx.guild.get_channel(settingContents['staff_management']['channel']).mention
		except:
			staff_management_channel = 'None'

		# punishments channel
		try:
			punishments_channel = ctx.guild.get_channel(settingContents['punishments']['channel']).mention
		except:
			punishments_channel = 'None'

		# shift management channel
		try:
			shift_management_channel = ctx.guild.get_channel(settingContents['shift_management']['channel']).mention
		except:
			shift_management_channel = 'None'

		try:
			ban_channel = ctx.guild.get_channel(settingContents['customisation']['ban_channel']).mention
		except:
			ban_channel = 'None'

		embed = discord.Embed(
			title='Server Configuration',
			description='Here are the current settings for this server.',
			color=await generate_random(ctx)
		)
		embed.add_field(
			name='Verification',
			value='Enabled: {}\nRole: {}'
			.format(
				settingContents['verification']['enabled'],
				verification_role
			),
			inline=False
		)

		embed.add_field(
			name='Anti-ping',
			value='Enabled: {}\nRole: {}\nBypass Role: {}'
			.format(
				settingContents['antiping']['enabled'],
				antiping_role,
				bypass_role
			),
			inline=False
		)

		embed.add_field(
			name='Staff Management',
			value='Enabled: {}\nChannel: {}'
			.format(
				settingContents['staff_management']['enabled'],
				staff_management_channel
			),
			inline=False
		)
		embed.add_field(
			name='Punishments',
			value='Enabled: {}\nChannel: {}'
			.format(
				settingContents['punishments']['enabled'],
				punishments_channel
			),
			inline=False
		)
		embed.add_field(
			name='Shift Management',
			value='Enabled: {}\nChannel: {}\nRole: {}'
			.format(
				settingContents['shift_management']['enabled'],
				shift_management_channel,
				shift_role
			),
			inline=False
		)
		embed.add_field(
			name='Customisation',
			value='Color: {}\nPrefix: `{}`\nBrand Name: {}\nThumbnail URL: {}\nFooter Text: {}\nBan Channel: {}'
			.format(
				settingContents['customisation']['color'],
				settingContents['customisation']['prefix'],
				settingContents['customisation']['brand_name'],
				settingContents['customisation']['thumbnail_url'],
				settingContents['customisation']['footer_text'],
				ban_channel
			),
			inline=False
		)

		for field in embed.fields:
			field.inline = False

		await ctx.send(embed=embed)
	elif option == 'edit' or option == 'change':
		category = await requestResponse(ctx,
										 'Please pick one of the options. `verification`, `antiping`, `staff_management`, `punishments`, `shift_management`, `customisation`.')
		category = category.content
		if category == 'verification':
			question = 'What do you want to do with verification? `enable`, `disable`, `role`'
			content = (await requestResponse(ctx, question)).content
			if content == 'enable':
				settingContents['verification']['enabled'] = True
			elif content == 'disable':
				settingContents['verification']['enabled'] = False
			elif content == 'role':
				content = (await requestResponse(ctx,
												 'What role do you want to use for verification? (e.g. `@Verified`)')).content
				convertedContent = await discord.ext.commands.RoleConverter().convert(ctx, content)
				settingContents['verification']['role'] = convertedContent.id
			else:
				return await ctx.send(
					'Please pick one of the options. `enable`, `disable`, `role`. Please run this command again with correct parameters.')
			await ctx.send('Successfully set verification to `{}`.'.format(content))
		elif category == 'antiping':
			question = 'What do you want to do with anti-ping? `enable`, `disable`, `role`'
			content = (await requestResponse(ctx, question)).content
			if content == 'enable':
				settingContents['antiping']['enabled'] = True
			elif content == 'disable':
				settingContents['antiping']['enabled'] = False
			elif content == 'role':
				content = (await requestResponse(ctx,
												 'What role do you want to use for anti-ping? (e.g. `@Anti-ping`)')).content
				convertedContent = await discord.ext.commands.RoleConverter().convert(ctx, content)
				settingContents['antiping']['role'] = convertedContent.id
			else:
				return await ctx.send(
					'Please pick one of the options. `enable`, `disable`, `role`. Please run this command again with correct parameters.')
			await ctx.send('Successfully set anti-ping to `{}`.'.format(content))
		elif category == 'staff_management':
			question = 'What do you want to do with staff management? `enable`, `disable`, `channel`'
			content = (await requestResponse(ctx, question)).content
			if content == 'enable':
				settingContents['staff_management']['enabled'] = True
			elif content == 'disable':
				settingContents['staff_management']['enabled'] = False
			elif content == 'channel':
				content = (await requestResponse(ctx,
												 'What channel do you want to use for staff management? (e.g. `#staff-management`)')).content
				convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
				settingContents['staff_management']['channel'] = convertedContent.id
			else:
				return await ctx.send(
					'Please pick one of the options. `enable`, `disable`, `channel`. Please run this command again with correct parameters.')
			await ctx.send('Successfully set staff management to `{}`.'.format(content))
		elif category == 'punishments':
			question = 'What do you want to do with punishments? `enable`, `disable`, `channel`'
			content = (await requestResponse(ctx, question)).content
			if content == 'enable':
				settingContents['punishments']['enabled'] = True
			elif content == 'disable':
				settingContents['punishments']['enabled'] = False
			elif content == 'channel':
				content = (await requestResponse(ctx,
												 'What channel do you want to use for punishments? (e.g. `#punishments`)')).content
				convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
				settingContents['punishments']['channel'] = convertedContent.id
			else:
				return await ctx.send(
					'Please pick one of the options. `enable`, `disable`, `channel`. Please run this command again with correct parameters.')
			await ctx.send('Successfully set punishments to `{}`.'.format(content))
		elif category == 'shift_management':
			question = 'What do you want to do with shift management? `enable`, `disable`, `channel`, `role`'
			content = (await requestResponse(ctx, question)).content
			if content == 'enable':
				settingContents['shift_management']['enabled'] = True
			elif content == 'disable':
				settingContents['shift_management']['enabled'] = False
			elif content == 'channel':
				content = (await requestResponse(ctx,
												 'What channel do you want to use for shift management? (e.g. `#shift-management`)')).content
				convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
				settingContents['shift_management']['channel'] = convertedContent.id
			elif content == 'role':
				content = (await requestResponse(ctx,
												 'What role do you want to use for "Currently in game moderating"? (e.g. `@Currently In-game moderating`)')).content
				convertedContent = await discord.ext.commands.RoleConverter().convert(ctx, content)
				settingContents['shift_management']['role'] = convertedContent.id
			else:
				return await ctx.send(
					'Please pick one of the options. `enable`, `disable`, `channel`. Please run this command again with correct parameters.')
			await ctx.send('Successfully set shift management to `{}`.'.format(content))
		elif category == 'customisation':
			# color, prefix, brand name, thumbnail url, footer text, ban channel
			question = 'What do you want to do with customisation? `color`, `prefix`, `brand_name`, `thumbnail_url`, `footer_text`, `ban_channel`'
			content = (await requestResponse(ctx, question)).content
			if content == 'color':
				content = (await requestResponse(ctx,
												 'What color do you want to use for the server? (e.g. `#00FF00`)')).content
				convertedContent = await discord.ext.commands.ColourConverter().convert(ctx, content)
				settingContents['customisation']['color'] = convertedContent.value
			elif content == 'prefix':
				content = (
					await requestResponse(ctx, 'What prefix do you want to use for the server? (e.g. `!`)')).content
				settingContents['customisation']['prefix'] = content
			elif content == 'brand_name':
				content = (await requestResponse(ctx,
												 'What brand name do you want to use for the server? (e.g. `My Server`)')).content
				settingContents['customisation']['brand_name'] = content
			elif content == 'thumbnail_url':
				content = (await requestResponse(ctx,
												 'What thumbnail url do you want to use for the server? (e.g. `https://i.imgur.com/...`)')).content
				settingContents['customisation']['thumbnail_url'] = content
			elif content == 'footer_text':
				content = (await requestResponse(ctx,
												 'What footer text do you want to use for the server? (e.g. `My Server`)')).content
				settingContents['customisation']['footer_text'] = content
			elif content == 'ban_channel':
				content = (
					await requestResponse(ctx, 'What channel do you want to use for banning? (e.g. `#bans`)')).content
				convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
				settingContents['customisation']['ban_channel'] = convertedContent.id
			else:
				return await ctx.send(
					'You did not pick any of the options. Please run this command again with correct parameters.')
		else:
			return await ctx.send(
				'You did not pick one of the options. `anti-ping`, `staff_management`, `punishments`, `shift_management`, `customisation`. Please run this command again with correct parameters.')

		await bot.settings.update_by_id(settingContents)
		await ctx.send('Successfully set {} to `{}`.'.format(category, content))


@config.command(
	name='view',
	description='View the current configuration of the server.'
)
@commands.has_permissions(manage_guild=True)
@app_commands.checks.has_permissions(manage_guild=True)
async def viewconfig(ctx):
	if not await bot.settings.find_by_id(ctx.guild.id):
		await ctx.send('This server has not yet been set up. Please run `>setup` to set it up.')
		return

	settingContents = await bot.settings.find_by_id(ctx.guild.id)

	try:
		verification_role = ctx.guild.get_role(settingContents['staff_management']['verification_role']).mention
	except:
		verification_role = 'None'
	try:
		shift_role = ctx.guild.get_role(settingContents['shift_management']['role']).mention
	except:
		shift_role = 'None'
	try:
		antiping_role = ctx.guild.get_role(settingContents['anti_ping']['role']).mention
	except:
		antiping_role = 'None'

	try:
		bypass_role = ctx.guild.get_role(settingContents['anti_ping']['bypass_role']).mention
	except:
		bypass_role = 'None'

	# staff management channel
	try:
		staff_management_channel = ctx.guild.get_channel(settingContents['staff_management']['channel']).mention
	except:
		staff_management_channel = 'None'

	# punishments channel
	try:
		punishments_channel = ctx.guild.get_channel(settingContents['punishments']['channel']).mention
	except:
		punishments_channel = 'None'

	# shift management channel
	try:
		shift_management_channel = ctx.guild.get_channel(settingContents['shift_management']['channel']).mention
	except:
		shift_management_channel = 'None'

	try:
		ban_channel = ctx.guild.get_channel(settingContents['customisation']['ban_channel']).mention
	except:
		ban_channel = 'None'

	embed = discord.Embed(
		title='Server Configuration',
		description='Here are the current settings for this server.',
		color=await generate_random(ctx)
	)
	embed.add_field(
		name='Verification',
		value='Enabled: {}\nRole: {}'
		.format(
			settingContents['verification']['enabled'],
			verification_role
		),
		inline=False
	)

	embed.add_field(
		name='Anti-ping',
		value='Enabled: {}\nRole: {}\nBypass Role: {}'
		.format(
			settingContents['antiping']['enabled'],
			antiping_role,
			bypass_role
		),
		inline=False
	)

	embed.add_field(
		name='Staff Management',
		value='Enabled: {}\nChannel: {}'
		.format(
			settingContents['staff_management']['enabled'],
			staff_management_channel
		),
		inline=False
	)
	embed.add_field(
		name='Punishments',
		value='Enabled: {}\nChannel: {}'
		.format(
			settingContents['punishments']['enabled'],
			punishments_channel
		),
		inline=False
	)
	embed.add_field(
		name='Shift Management',
		value='Enabled: {}\nChannel: {}\nRole: {}'
		.format(
			settingContents['shift_management']['enabled'],
			shift_management_channel,
			shift_role
		),
		inline=False
	)
	embed.add_field(
		name='Customisation',
		value='Color: {}\nPrefix: `{}`\nBrand Name: {}\nThumbnail URL: {}\nFooter Text: {}\nBan Channel: {}'
		.format(
			settingContents['customisation']['color'],
			settingContents['customisation']['prefix'],
			settingContents['customisation']['brand_name'],
			settingContents['customisation']['thumbnail_url'],
			settingContents['customisation']['footer_text'],
			ban_channel
		),
		inline=False
	)

	for field in embed.fields:
		field.inline = False

	await ctx.send(embed=embed)


@config.command(
	name='change',
	description='Change the configuration of the server.'
)
@commands.has_permissions(manage_guild=True)
@app_commands.checks.has_permissions(manage_guild=True)
async def changeconfig(ctx):
	if not await bot.settings.find_by_id(ctx.guild.id):
		await ctx.send('This server has not yet been set up. Please run `>setup` to set it up.')
		return

	settingContents = await bot.settings.find_by_id(ctx.guild.id)

	# category = await requestResponse(ctx, 'Please pick one of the options. `verification`, `antiping`, `staff_management`, `punishments`, `shift_management`, `customisation`.')
	category = SettingsSelectMenu(ctx.author.id)

	await ctx.send('Please select which category you would like to modify.', view=category)
	await category.wait()
	category = category.value

	if category == 'verification':
		question = 'What do you want to do with verification?'
		customselect = CustomSelectMenu(ctx.author.id, ["enable", "disable", "role"])
		await ctx.send(question, view=customselect)
		await customselect.wait()
		content = customselect.value
		if content == 'enable':
			settingContents['verification']['enabled'] = True
		elif content == 'disable':
			settingContents['verification']['enabled'] = False
		elif content == 'role':
			content = (
				await requestResponse(ctx, 'What role do you want to use for verification? (e.g. `@Verified`)')).content
			convertedContent = await discord.ext.commands.RoleConverter().convert(ctx, content)
			settingContents['verification']['role'] = convertedContent.id
		else:
			return await ctx.send(
				'Please pick one of the options. `enable`, `disable`, `role`. Please run this command again with correct parameters.')
	elif category == 'antiping':
		question = 'What do you want to do with antiping?'
		customselect = CustomSelectMenu(ctx.author.id, ["enable", "disable", "role", "bypass_role"])
		await ctx.send(question, view=customselect)
		await customselect.wait()
		content = customselect.value
		if content == 'enable':
			settingContents['antiping']['enabled'] = True
		elif content == 'disable':
			settingContents['antiping']['enabled'] = False
		elif content == 'role':
			content = (
				await requestResponse(ctx, 'What role do you want to use for anti-ping? (e.g. `@Anti-ping`)')).content
			convertedContent = await discord.ext.commands.RoleConverter().convert(ctx, content)
			settingContents['antiping']['role'] = convertedContent.id
		elif content == "bypass_role" or content == "bypass" or content == "bypass-role":
			content = (
				await requestResponse(ctx, 'What role do you want to use for anti-ping? (e.g. `@Anti-ping`)')).content
			convertedContent = await discord.ext.commands.RoleConverter().convert(ctx, content)
			settingContents['antiping']['role_bypass'] = convertedContent.id
		else:
			return await ctx.send('You have not selected one of the options. Please run this command again.')
	elif category == 'staff_management':
		question = 'What do you want to do with staff management?'
		customselect = CustomSelectMenu(ctx.author.id, ["enable", "disable", "channel", "role"])
		await ctx.send(question, view=customselect)
		await customselect.wait()
		content = customselect.value
		if content == 'enable':
			settingContents['staff_management']['enabled'] = True
		elif content == 'disable':
			settingContents['staff_management']['enabled'] = False
		elif content == 'channel':
			content = (await requestResponse(ctx,
											 'What channel do you want to use for staff management? (e.g. `#staff-management`)')).content
			convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
			settingContents['staff_management']['channel'] = convertedContent.id
		elif content == 'role':
			content = (
				await requestResponse(ctx, 'What role do you want to use as a staff role? (e.g. `@Staff`\n**Note:** All members you want to be able to run advanced permission commands (punishments, staff management, shift management) must have this role.')).content
			convertedContent = await discord.ext.commands.RoleConverter().convert(ctx, content)
			settingContents['staff_management']['role'] = convertedContent.id
		else:
			return await ctx.send('You have not selected one of the options. Please run this command again.')
	elif category == 'punishments':
		question = 'What do you want to do with punishments?'
		customselect = CustomSelectMenu(ctx.author.id, ["enable", "disable", "channel", "ban_channel"])
		await ctx.send(question, view=customselect)
		await customselect.wait()
		content = customselect.value
		if content == 'enable':
			settingContents['punishments']['enabled'] = True
		elif content == 'disable':
			settingContents['punishments']['enabled'] = False
		elif content == 'channel':
			content = (await requestResponse(ctx,
											 'What channel do you want to use for punishments? (e.g. `#punishments`)')).content
			convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
			settingContents['punishments']['channel'] = convertedContent.id
		elif content == 'ban_channel':
			content = (
				await requestResponse(ctx, 'What channel do you want to use for banning? (e.g. `#bans`)')).content
			convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
			settingContents['customisation']['ban_channel'] = convertedContent.id
		else:
			return await ctx.send('You have not selected one of the options. Please run this command again.')
	elif category == 'shift_management':
		question = 'What do you want to do with shift management?'
		customselect = CustomSelectMenu(ctx.author.id, ["enable", "disable", "channel", "role"])
		await ctx.send(question, view=customselect)
		await customselect.wait()
		content = customselect.value
		if content == 'enable':
			settingContents['shift_management']['enabled'] = True
		elif content == 'disable':
			settingContents['shift_management']['enabled'] = False
		elif content == 'channel':
			content = (await requestResponse(ctx,
											 'What channel do you want to use for shift management? (e.g. `#shift-management`)')).content
			convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
			settingContents['shift_management']['channel'] = convertedContent.id
		elif content == 'role':
			content = (await requestResponse(ctx,
											 'What role do you want to use for "Currently in game moderating"? (e.g. `@Currently In-game moderating`)')).content
			convertedContent = await discord.ext.commands.RoleConverter().convert(ctx, content)
			settingContents['shift_management']['role'] = convertedContent.id
		else:
			return await ctx.send(
				'Please pick one of the options. `enable`, `disable`, `channel`. Please run this command again with correct parameters.')
	elif category == 'customisation':
		# color, prefix, brand name, thumbnail url, footer text, ban channel
		question = 'What would you like to customize?'
		customselect = CustomSelectMenu(ctx.author.id, ["color", "prefix", "brand_name", "thumbnail_url", "footer_text",
														"server_code"])
		await ctx.send(question, view=customselect)
		await customselect.wait()
		content = customselect.value
		if content == 'color':
			content = (
				await requestResponse(ctx, 'What color do you want to use for the server? (e.g. `#00FF00`)')).content
			convertedContent = await discord.ext.commands.ColourConverter().convert(ctx, content)
			settingContents['customisation']['color'] = convertedContent.value
		elif content == 'prefix':
			content = (await requestResponse(ctx, 'What prefix do you want to use for the server? (e.g. `!`)')).content
			settingContents['customisation']['prefix'] = content
		elif content == 'brand_name':
			content = (await requestResponse(ctx,
											 'What brand name do you want to use for the server? (e.g. `My Server`)')).content
			settingContents['customisation']['brand_name'] = content
		elif content == 'thumbnail_url':
			content = (await requestResponse(ctx,
											 'What thumbnail url do you want to use for the server? (e.g. `https://i.imgur.com/...`)')).content
			settingContents['customisation']['thumbnail_url'] = content
		elif content == 'footer_text':
			content = (await requestResponse(ctx,
											 'What footer text do you want to use for the server? (e.g. `My Server`)')).content
			settingContents['customisation']['footer_text'] = content
		elif content == 'ban_channel':
			content = (
				await requestResponse(ctx, 'What channel do you want to use for banning? (e.g. `#bans`)')).content
			convertedContent = await discord.ext.commands.TextChannelConverter().convert(ctx, content)
			settingContents['customisation']['ban_channel'] = convertedContent.id
		elif content == 'server_code':
			content = (await requestResponse(ctx, 'What server code do you use for your ER:LC server?')).content
			settingContents['customisation']['server_code'] = content
		else:
			return await ctx.send(
				'You did not pick any of the options. Please run this command again with correct parameters.')
	else:
		return await ctx.send(
			'You did not pick any of the options. Please run this command again with correct parameters.')

	await bot.settings.update_by_id(settingContents)
	await ctx.send('Successfully set.')


# support server invite command
@bot.hybrid_command(name='support', aliases=['support-server'],
					description="Information about the ERM Support Server [Utility]")
async def support_server(ctx):
	# using an embed
	embed = discord.Embed(title='Support Server', description='Join the support server to get help with the bot!',
						  color=await generate_random(ctx))
	embed.add_field(name='Support Server', value='[Click here](https://discord.gg/5pMmJEYazQ)', inline=False)
	await ctx.send(embed=embed)


# uptime command
# * Finally works, basic and uses the bot on_ready event
@bot.hybrid_command(name='uptime', description="Shows the uptime of the bot [Utility]")
async def uptime(ctx):
	# using an embed
	current_time = time.time()
	difference = int(round(current_time - bot.start_time))
	text = datetime.timedelta(seconds=difference)
	embed = discord.Embed(color=await generate_random(ctx))
	embed.add_field(name='Started at', value=f"<t:{int(bot.start_time)}>")
	embed.add_field(name='Uptime', value=td_format(text))
	embed.set_footer(text="Information | Emergency Response Management", icon_url=bot.user.avatar.url)
	await ctx.send(embed=embed)


@bot.hybrid_command(
	name="warn",
	aliases=['w', 'wa'],
	description="Warns a user. [Punishments]",
	usage="<user> <reason>",
	brief="Warns a user.",
	with_app_command=True,
)
@is_staff()
async def warn(ctx, user, *, reason):
	request = requests.get(f'https://users.roblox.com/v1/users/search?keyword={user}&limit=10')
	if request.status_code != 200:
		oldRequest = requests.get(f'https://api.roblox.com/users/get-by-username?username={user.lower()}')
		oldRequestJSON = oldRequest.json()
		if 'success' in oldRequestJSON.keys():
			if not oldRequestJSON['success']:
				return await ctx.send('User does not exist.')
		Id = oldRequestJSON['Id']
		request = requests.get(f'https://users.roblox.com/v1/users/{Id}')
		requestJson = request.json()

	else:
		requestJson = request.json()
		data = requestJson['data']

	if not 'data' in locals():
		data = [requestJson]

	Embeds = []

	for dataItem in data:
		Embed = discord.Embed(
			title=dataItem['name'],
			color=await generate_random(ctx)
		)

		Headshot_URL = "https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
			dataItem['id'])

		Embed.set_author(name='Roblox',
						 icon_url='https://doy2mn9upadnk.cloudfront.net/uploads/default/original/4X/0/3/2/0327107c890e461c1417bc00631e460b1114b38d.png')
		Embed.set_thumbnail(url=Headshot_URL)
		for key, value in dataItem.items():
			if not isinstance(value, list):
				Embed.add_field(name=key.capitalize(), value=value)
		Embeds.append(Embed)

	paginator = DiscordUtils.Pagination.CustomEmbedPaginator(ctx)
	paginator.add_reaction('✅', 'lock')
	paginator.add_reaction('❎', "delete")

	try:
		await ctx.send(
			'Is this the correct user? Not the correct one? Cycle through them using the reactions below and then select by saying \'yes\' or \'cancel\'.')
		EmbedMsg = await paginator.run(Embeds)
	except:
		return await ctx.reply('That user does not exist on the Roblox platform.')

	try:
		await ctx.channel.fetch_message(EmbedMsg.id)
	except discord.errors.NotFound:
		return await ctx.reply('Successfully cancelled.')

	logging.info(EmbedMsg)
	logging.info(EmbedMsg.embeds)

	user = EmbedMsg.embeds[0].title

	default_warning_item = {
		'_id': user.lower(),
		'warnings': [{
			'id': next(generator),
			"Type": "Warning",
			"Reason": reason,
			"Moderator": [ctx.author.name, ctx.author.id],
			"Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
			"Guild": ctx.guild.id
		}]
	}

	singular_warning_item = {
		'id': next(generator),
		"Type": "Warning",
		"Reason": reason,
		"Moderator": [ctx.author.name, ctx.author.id],
		"Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
		"Guild": ctx.guild.id
	}

	configItem = await bot.settings.find_by_id(ctx.guild.id)
	if configItem is None:
		return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')

	if not configItem['punishments']['enabled']:
		return await ctx.send(
			'This server has punishments disabled. Please run `>config change` to enable punishments.')

	embed = discord.Embed(title=user, color=await generate_random(ctx))
	embed.set_thumbnail(url=EmbedMsg.embeds[0].thumbnail.url)
	try:
		embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
		embed.set_footer(icon_url=get_guild_icon(ctx.guild), text="{} | {}".format(configItem['customisation']['footer_text'],
																			configItem['customisation']['brand_name']))
	except:
		pass
	embed.add_field(name="Moderator", value=ctx.author.name, inline=False)
	embed.add_field(name="Violator", value=EmbedMsg.embeds[0].title, inline=False)
	embed.add_field(name="Type", value="Warning", inline=False)
	embed.add_field(name="Reason", value=reason, inline=False)

	channel = discord.utils.get(ctx.guild.channels, id=configItem['punishments']['channel'])

	if not channel:
		return await ctx.send(
			'The channel in the configuration does not exist. Please tell the server owner to run `>config change` for the channel to be changed.')

	if not await bot.warnings.find_by_id(user.lower()):
		await bot.warnings.insert(default_warning_item)
	else:
		dataset = await bot.warnings.find_by_id(user.lower())
		dataset['warnings'].append(singular_warning_item)
		await bot.warnings.update_by_id(dataset)

	await ctx.reply(f'{user} has been warned successfully.')
	await channel.send(embed=embed)


@bot.hybrid_command(
	name="kick",
	aliases=['k', 'ki'],
	description="Kick a user. [Punishments]",
	usage="<user> <reason>",
	brief="Kicks a user.",
	with_app_command=True,
)
@is_staff()
async def kick(ctx, user, *, reason):
	request = requests.get(f'https://users.roblox.com/v1/users/search?keyword={user}&limit=10')
	if request.status_code != 200:
		oldRequest = requests.get(f'https://api.roblox.com/users/get-by-username?username={user.lower()}')
		oldRequestJSON = oldRequest.json()
		if not oldRequestJSON['success']:
			return await ctx.send('User does not exist.')
		Id = oldRequestJSON['Id']
		request = requests.get(f'https://users.roblox.com/v1/users/{Id}')
		requestJson = request.json()

	else:
		requestJson = request.json()
		data = requestJson['data']

	if not 'data' in locals():
		data = [requestJson]

	Embeds = []

	for dataItem in data:
		Embed = discord.Embed(
			title=dataItem['name'],
			color=await generate_random(ctx)
		)

		Headshot_URL = "https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
			dataItem['id'])

		Embed.set_author(name='Roblox',
						 icon_url='https://doy2mn9upadnk.cloudfront.net/uploads/default/original/4X/0/3/2/0327107c890e461c1417bc00631e460b1114b38d.png')
		Embed.set_thumbnail(url=Headshot_URL)
		for key, value in dataItem.items():
			if not isinstance(value, list):
				Embed.add_field(name=key.capitalize(), value=value)
		Embeds.append(Embed)

	paginator = DiscordUtils.Pagination.CustomEmbedPaginator(ctx)
	paginator.add_reaction('✅', 'lock')
	paginator.add_reaction('❎', "delete")

	try:
		await ctx.send(
			'Is this the correct user? Not the correct one? Cycle through them using the reactions below and then select by saying \'yes\' or \'cancel\'.')
		EmbedMsg = await paginator.run(Embeds)
	except:
		return await ctx.reply('That user does not exist on the Roblox platform.')

	try:
		await ctx.channel.fetch_message(EmbedMsg.id)
	except discord.errors.NotFound:
		return await ctx.reply('Successfully cancelled.')

	logging.info(EmbedMsg)
	logging.info(EmbedMsg.embeds)

	user = EmbedMsg.embeds[0].title

	default_warning_item = {
		'_id': user.lower(),
		'warnings': [{
			'id': next(generator),
			"Type": "Kick",
			"Reason": reason,
			"Moderator": [ctx.author.name, ctx.author.id],
			"Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
			"Guild": ctx.guild.id
		}]
	}

	singular_warning_item = {
		'id': next(generator),
		"Type": "Kick",
		"Reason": reason,
		"Moderator": [ctx.author.name, ctx.author.id],
		"Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
		"Guild": ctx.guild.id
	}

	configItem = await bot.settings.find_by_id(ctx.guild.id)
	if configItem is None:
		return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')

	if not configItem['punishments']['enabled']:
		return await ctx.send(
			'This server has punishments disabled. Please run `>config change` to enable punishments.')

	embed = discord.Embed(title=user, color=await generate_random(ctx))
	embed.set_thumbnail(url=EmbedMsg.embeds[0].thumbnail.url)
	try:
		embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
		embed.set_footer(icon_url=get_guild_icon(ctx.guild), text="{} | {}".format(configItem['customisation']['footer_text'],
																			configItem['customisation']['brand_name']))
	except:
		pass
	embed.add_field(name="Moderator", value=ctx.author.name, inline=False)
	embed.add_field(name="Violator", value=EmbedMsg.embeds[0].title, inline=False)
	embed.add_field(name="Type", value="Kick", inline=False)
	embed.add_field(name="Reason", value=reason, inline=False)

	channel = discord.utils.get(ctx.guild.channels, id=configItem['punishments']['channel'])

	if not channel:
		return await ctx.send(
			'The channel in the configuration does not exist. Please tell the server owner to run `>config change` for the channel to be changed.')

	if not await bot.warnings.find_by_id(user.lower()):
		await bot.warnings.insert(default_warning_item)
	else:
		dataset = await bot.warnings.find_by_id(user.lower())
		dataset['warnings'].append(singular_warning_item)
		await bot.warnings.update_by_id(dataset)

	await ctx.reply(f'{user} has been warned successfully.')
	await channel.send(embed=embed)


@bot.hybrid_command(
	name="ban",
	aliases=['b', 'ba'],
	description="Bans a user. [Punishments]",
	usage="<user> <reason>",
	brief="Bans a user.",
	with_app_command=True,
)
@is_staff()
async def ban(ctx, user, *, reason):
	request = requests.get(f'https://users.roblox.com/v1/users/search?keyword={user}&limit=10')
	if request.status_code != 200:
		oldRequest = requests.get(f'https://api.roblox.com/users/get-by-username?username={user.lower()}')
		oldRequestJSON = oldRequest.json()
		if not oldRequestJSON['success']:
			return await ctx.send('User does not exist.')
		Id = oldRequestJSON['Id']
		request = requests.get(f'https://users.roblox.com/v1/users/{Id}')
		requestJson = request.json()

	else:
		requestJson = request.json()
		data = requestJson['data']

	if not 'data' in locals():
		data = [requestJson]

	Embeds = []

	for dataItem in data:
		Embed = discord.Embed(
			title=dataItem['name'],
			color=await generate_random(ctx)
		)

		Headshot_URL = "https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
			dataItem['id'])

		Embed.set_author(name='Roblox',
						 icon_url='https://doy2mn9upadnk.cloudfront.net/uploads/default/original/4X/0/3/2/0327107c890e461c1417bc00631e460b1114b38d.png')
		Embed.set_thumbnail(url=Headshot_URL)
		for key, value in dataItem.items():
			if not isinstance(value, list):
				Embed.add_field(name=key.capitalize(), value=value)
		Embeds.append(Embed)

	paginator = DiscordUtils.Pagination.CustomEmbedPaginator(ctx)
	paginator.add_reaction('✅', 'lock')
	paginator.add_reaction('❎', "delete")

	try:
		await ctx.send(
			'Is this the correct user? Not the correct one? Cycle through them using the reactions below and then select by saying \'yes\' or \'cancel\'.')
		EmbedMsg = await paginator.run(Embeds)
	except:
		return await ctx.reply('That user does not exist on the Roblox platform.')

	try:
		await ctx.channel.fetch_message(EmbedMsg.id)
	except discord.errors.NotFound:
		return await ctx.reply('Successfully cancelled.')

	logging.info(EmbedMsg)
	logging.info(EmbedMsg.embeds)

	user = EmbedMsg.embeds[0].title

	default_warning_item = {
		'_id': user.lower(),
		'warnings': [{
			'id': next(generator),
			"Type": "Ban",
			"Reason": reason,
			"Moderator": [ctx.author.name, ctx.author.id],
			"Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
			"Guild": ctx.guild.id
		}]
	}

	singular_warning_item = {
		'id': next(generator),
		"Type": "Ban",
		"Reason": reason,
		"Moderator": [ctx.author.name, ctx.author.id],
		"Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
		"Guild": ctx.guild.id
	}

	configItem = await bot.settings.find_by_id(ctx.guild.id)
	if configItem is None:
		return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')

	if not configItem['punishments']['enabled']:
		return await ctx.send(
			'This server has punishments disabled. Please run `>config change` to enable punishments.')

	embed = discord.Embed(title=user, color=await generate_random(ctx))
	embed.set_thumbnail(url=EmbedMsg.embeds[0].thumbnail.url)
	try:
		embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
		embed.set_footer(icon_url=get_guild_icon(ctx.guild), text="{} | {}".format(configItem['customisation']['footer_text'],
																			configItem['customisation']['brand_name']))
	except:
		pass
	embed.add_field(name="Moderator", value=ctx.author.name, inline=False)
	embed.add_field(name="Violator", value=EmbedMsg.embeds[0].title, inline=False)
	embed.add_field(name="Type", value="Ban", inline=False)
	embed.add_field(name="Reason", value=reason, inline=False)

	if not configItem['customisation']['ban_channel'] == None:
		channel = ctx.guild.get_channel(configItem['customisation']['ban_channel'])
	else:
		channel = discord.utils.get(ctx.guild.channels, id=configItem['punishments']['channel'])

	if not channel:
		return await ctx.send(
			'The channel in the configuration does not exist. Please tell the server owner to run `>config change` for the channel to be changed.')

	if not await bot.warnings.find_by_id(user.lower()):
		await bot.warnings.insert(default_warning_item)
	else:
		dataset = await bot.warnings.find_by_id(user.lower())
		dataset['warnings'].append(singular_warning_item)
		await bot.warnings.update_by_id(dataset)

	await ctx.reply(f'{user} has been warned successfully.')
	await channel.send(embed=embed)


@bot.hybrid_command(
	name="messagelog",
	aliases=['m', 'mlog'],
	description="Logs the in-game :m usage of a staff member. [Staff Management]",
	usage="<message>",
	with_app_command=True,
)
@is_staff()
async def mlog(ctx, *, message):
	configItem = await bot.settings.find_by_id(ctx.guild.id)
	if configItem is None:
		return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')

	if not configItem['staff_management']['enabled']:
		return await ctx.send(
			'This server has punishments disabled. Please run `>config change` to enable punishments.')

	embed = discord.Embed(title='In-game message', color=await generate_random(ctx))
	try:
		embed.set_thumbnail(url=ctx.author.avatar.url)
		embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
		embed.set_footer(icon_url=get_guild_icon(ctx.guild), text="{} | {}".format(configItem['customisation']['footer_text'],
																			configItem['customisation']['brand_name']))
	except:
		pass
	embed.add_field(name="Moderator", value=ctx.author.name, inline=False)
	embed.add_field(name="Message", value=message, inline=False)

	if not configItem['staff_management']['channel'] == None:
		channel = ctx.guild.get_channel(configItem['staff_management']['channel'])
	if not channel:
		return await ctx.send(
			'The channel in the configuration does not exist. Please tell the server owner to run `>config change` for the channel to be changed.')

	await ctx.reply(f'Message has been logged successfully.')
	await channel.send(embed=embed)


@bot.hybrid_command(
	name="tempban",
	aliases=['tb', 'tba'],
	description="Tempbans a user. [Punishments]",
	with_app_command=True,
)
@is_staff()
async def tempban(ctx, user, time: str, *, reason):
	reason = ''.join(reason)

	timeObj = list(reason)[-1]
	reason = list(reason)

	if not time.endswith(('h', 'm', 's', 'd', 'w')):
		reason.insert(0, time)
		if not timeObj.endswith(('h', 'm', 's', 'd', 'w')):
			return await ctx.reply(
				'A time must be provided at the start or at the end of the command. Example: >tban i_iMikey 12h LTAP / >tban i_iMikey LTAP 12h')
		else:
			time = timeObj
			reason.pop()

	if time.endswith('s'):
		time = int(removesuffix(time, 's'))
	elif time.endswith('m'):
		time = int(removesuffix(time, 'm')) * 60
	elif time.endswith('h'):
		time = int(removesuffix(time, 'h')) * 60 * 60
	elif time.endswith('d'):
		time = int(removesuffix(time, 'd')) * 60 * 60 * 24
	elif time.endswith('w'):
		time = int(removesuffix(time, 'w')) * 60 * 60 * 24 * 7

	startTimestamp = datetime.datetime.timestamp(ctx.message.created_at)
	endTimestamp = int(startTimestamp + time)

	reason = ''.join([str(item) for item in reason])

	request = requests.get(f'https://users.roblox.com/v1/users/search?keyword={user}&limit=10')
	if request.status_code != 200:
		oldRequest = requests.get(f'https://api.roblox.com/users/get-by-username?username={user.lower()}')
		oldRequestJSON = oldRequest.json()
		if not oldRequestJSON['success']:
			return await ctx.send('User does not exist.')
		Id = oldRequestJSON['Id']
		request = requests.get(f'https://users.roblox.com/v1/users/{Id}')
		requestJson = request.json()

	else:
		requestJson = request.json()
		data = requestJson['data']

	if not 'data' in locals():
		data = [requestJson]

	Embeds = []

	for dataItem in data:
		Embed = discord.Embed(
			title=dataItem['name'],
			color=await generate_random(ctx)
		)

		Headshot_URL = "https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
			dataItem['id'])

		Embed.set_author(name='Roblox',
						 icon_url='https://doy2mn9upadnk.cloudfront.net/uploads/default/original/4X/0/3/2/0327107c890e461c1417bc00631e460b1114b38d.png')
		Embed.set_thumbnail(url=Headshot_URL)
		for key, value in dataItem.items():
			if not isinstance(value, list):
				Embed.add_field(name=key.capitalize(), value=value)
		Embeds.append(Embed)

	paginator = DiscordUtils.Pagination.CustomEmbedPaginator(ctx)
	paginator.add_reaction('✅', 'lock')
	paginator.add_reaction('❎', "delete")

	try:
		await ctx.send(
			'Is this the correct user? Not the correct one? Cycle through them using the reactions below and then select by saying \'yes\' or \'cancel\'.')
		EmbedMsg = await paginator.run(Embeds)
	except:
		return await ctx.reply('That user does not exist on the Roblox platform.')

	try:
		await ctx.channel.fetch_message(EmbedMsg.id)
	except discord.errors.NotFound:
		return await ctx.reply('Successfully cancelled.')

	logging.info(EmbedMsg)
	logging.info(EmbedMsg.embeds)

	user = EmbedMsg.embeds[0].title

	default_warning_item = {
		'_id': user.lower(),
		'warnings': [{
			'id': next(generator),
			"Type": "Temporary Ban",
			"Reason": reason,
			"Moderator": [ctx.author.name, ctx.author.id],
			"Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
			"Until": endTimestamp,
			"Guild": ctx.guild.id
		}]
	}

	singular_warning_item = {
		'id': next(generator),
		"Type": "Temporary Ban",
		"Reason": reason,
		"Moderator": [ctx.author.name, ctx.author.id],
		"Time": ctx.message.created_at.strftime('%m/%d/%Y, %H:%M:%S'),
		"Until": endTimestamp,
		"Guild": ctx.guild.id
	}

	configItem = await bot.settings.find_by_id(ctx.guild.id)
	if configItem is None:
		return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')

	if not configItem['punishments']['enabled']:
		return await ctx.send(
			'This server has punishments disabled. Please run `>config change` to enable punishments.')

	embed = discord.Embed(title=user, color=await generate_random(ctx))
	embed.set_thumbnail(url=EmbedMsg.embeds[0].thumbnail.url)
	try:
		embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
		embed.set_footer(icon_url=get_guild_icon(ctx.guild), text="{} | {}".format(configItem['customisation']['footer_text'],
																			configItem['customisation']['brand_name']))
	except:
		pass
	embed.add_field(name="Moderator", value=ctx.author.name, inline=False)
	embed.add_field(name="Violator", value=EmbedMsg.embeds[0].title, inline=False)
	embed.add_field(name="Type", value="Temporary Ban", inline=False)
	embed.add_field(name="Reason", value=reason, inline=False)

	if not configItem['customisation']['ban_channel'] == None:
		channel = discord.utils.get(ctx.guild.channels, id=configItem['customisation']['ban_channel'])
	else:
		channel = discord.utils.get(ctx.guild.channels, id=configItem['punishments']['channel'])

	if not channel:
		return await ctx.send(
			'The channel in the configuration does not exist. Please tell the server owner to run `>config change` for the channel to be changed.')

	if not await bot.warnings.find_by_id(user.lower()):
		await bot.warnings.insert(default_warning_item)
	else:
		dataset = await bot.warnings.find_by_id(user.lower())
		dataset['warnings'].append(singular_warning_item)
		await bot.warnings.update_by_id(dataset)

	await ctx.reply(f'{user} has been warned successfully.')
	await channel.send(embed=embed)


@bot.hybrid_command(
	name="search",
	aliases=["s"],
	description="Searches for a user in the warning database. [Search]",
	usage="<user>",
	with_app_command=True,
)
async def search(ctx, *, query):
	alerts = {
		'NoAlerts': '+ ✅ No alerts found for this account!',
		'AccountAge': '- ⚠️ The account age of the user is less than 100 days.',
		'NoDescription': '- ⚠️ This account has no description, and is likely to be an alt.',
		'SuspiciousUsername': '- ⚠️ The name of this account is suspicious, and could be an alt account.',
		'MassPunishments': '- ⚠️ The amount of punishments this user has is above the regular amount and should be monitored.',
		'UserDoesNotExist': '- ⚠️ This user does not exist. They have been most likely deleted from the platform or a mistake in the database. Contact Mikey for more information.',
		'IsBanned': '- ⚠️ This user is banned from the Roblox platform.',
		'NotManyFriends': '- 🚧 This user has less than 30 friends.',
		'NotManyGroups': '- 🚧 This user has less than 5 groups.'
	}

	logging.info(query)
	query = query.split('.')
	query = query[0]

	logging.info(query)
	RESULTS = []

	dataset = await bot.warnings.find_by_id(query.lower())
	if dataset:
		logging.info(dataset)
		logging.info(dataset['warnings'][0])

		dataset['warnings'][0]['name'] = query.lower()
		RESULTS.append(dataset['warnings'])

	if len(RESULTS) == 0:
		User = await client.get_user_by_username(query)
		if not User:
			return await ctx.send('No user matches your query.')
		triggered_alerts = []

		if User.is_banned:
			triggered_alerts.append('IsBanned')
		if (pytz.utc.localize(datetime.datetime.now()) - User.created).days < 100:
			triggered_alerts.append('AccountAge')
		if not User:
			triggered_alerts.append('UserDoesNotExist')
		if len(User.description) < 10:
			triggered_alerts.append('NoDescription')
		if any(x in User.name for x in ['alt', 'alternative', 'account']):
			triggered_alerts.append('SuspiciousUsername')
		if await User.get_friend_count() <= 30:
			triggered_alerts.append('NotManyFriends')
		if len(await User.get_group_roles()) <= 5:
			triggered_alerts.append('NotManyGroups')

		if len(triggered_alerts) == 0:
			triggered_alerts.append('NoAlerts')

		embed1 = discord.Embed(title=query, color=await generate_random(ctx))
		embed1.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
		embed1.add_field(name='Username', value=embed1.title, inline=False)
		if query.lower() in bot.staff_members.keys():
			await staff_field(embed1, query.lower())
		embed1.add_field(name='Punishments', value=f'0', inline=False)
		string = "\n".join([alerts[i] for i in triggered_alerts])

		embed1.add_field(name='Alerts', value=f'```diff\n{string}\n```', inline=False)
		embed1.set_thumbnail(
			url="https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
				User.id))
		await ctx.send(embed=embed1)

	if len(RESULTS) > 1:
		return await ctx.send(
			'More than one result match your query. If this is unexpected, join the [support server](https://discord.gg/5pMmJEYazQ) and contact a Support Team member.')

	if len(RESULTS) == 1:

		message = ctx.message

		embed1 = discord.Embed(title=RESULTS[0][0]['name'], color=await generate_random(ctx))
		embed2 = discord.Embed(title=RESULTS[0][0]['name'], color=await generate_random(ctx))

		result_var = None
		logging.info(message.content.lower())

		for result in RESULTS:
			if result[0]['name'] == RESULTS[0][0]['name']:
				result_var = RESULTS[0]

		result = result_var

		triggered_alerts = []

		User = await client.get_user_by_username(result[0]['name'], expand=True, exclude_banned_users=False)

		listOfPerGuild = []
		for item in result:
			if item['Guild'] == ctx.guild.id:
				listOfPerGuild.append(item)

		if User.is_banned:
			triggered_alerts.append('IsBanned')
		if (pytz.utc.localize(datetime.datetime.now()) - User.created).days < 100:
			triggered_alerts.append('AccountAge')
		if not User:
			triggered_alerts.append('UserDoesNotExist')
		if len(User.description) < 10:
			triggered_alerts.append('NoDescription')
		if any(x in User.name for x in ['alt', 'alternative', 'account']):
			triggered_alerts.append('SuspiciousUsername')
		if len(listOfPerGuild) > 5:
			triggered_alerts.append('MassPunishments')
		if await User.get_friend_count() <= 30:
			triggered_alerts.append('NotManyFriends')
		if len(await User.get_group_roles()) <= 5:
			triggered_alerts.append('NotManyGroups')

		if len(triggered_alerts) == 0:
			triggered_alerts.append('NoAlerts')

		configItem = await bot.settings.find_by_id(ctx.guild.id)
		if configItem is None:
			return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')

		if not configItem['punishments']['enabled']:
			return await ctx.send(
				'This server has punishments disabled. Please run `>config change` to enable punishments.')

		embeds = []
		embeds.append(embed1)
		embeds.append(embed2)

		embeds[0].add_field(name='Username', value=embed1.title, inline=False)
		embeds[0].add_field(name='Punishments', value=f'{len(listOfPerGuild)}', inline=False)
		if embed1.title in bot.staff_members.keys():
			await staff_field(embeds[0], embed1.title)
		string = "\n".join([alerts[i] for i in triggered_alerts])

		embeds[0].add_field(name='Alerts', value=f'```diff\n{string}\n```', inline=False)

		del result[0]['name']

		for action in result:
			if action['Guild'] == ctx.guild.id:
				if isinstance(action['Moderator'], list):
					user = discord.utils.get(ctx.guild.members, id=action['Moderator'][1])
					if user:
						action['Moderator'] = user.mention
				if 'Until' in action.keys():
					if len(embeds[-1].fields) <= 25:
						embeds[-1].add_field(
							name=action['Type'],
							value=f"Reason: {action['Reason']}\nModerator: {action['Moderator']}\nTime: {action['Time']}\nUntil: <t:{action['Until']}>\nID: {action['id']}",
							inline=False
						)
					else:
						embeds.append(discord.Embed(title=embeds[0].title, color=await generate_random(ctx)))
						embeds[-1].add_field(
							name=action['Type'],
							value=f"Reason: {action['Reason']}\nModerator: {action['Moderator']}\nTime: {action['Time']}\nUntil: <t:{action['Until']}>\nID: {action['id']}",
							inline=False
						)
				else:
					if len(embeds[-1].fields) <= 25:
						embeds[-1].add_field(
							name=action['Type'],
							value=f"Reason: {action['Reason']}\nModerator: {action['Moderator']}\nTime: {action['Time']}\nID: {action['id']}",
							inline=False
						)
					else:
						embeds.append(discord.Embed(title=embeds[0].title, color=await generate_random(ctx)))
						embeds[-1].add_field(
							name=action['Type'],
							value=f"Reason: {action['Reason']}\nModerator: {action['Moderator']}\nTime: {action['Time']}\nID: {action['id']}",
							inline=False
						)

		for embed in embeds:
			embed.set_thumbnail(
				url="https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
					User.id))
			embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
			embed.set_footer(icon_url=get_guild_icon(ctx.guild),
							 text="{} | {}".format(configItem['customisation']['brand_name'],
												   configItem['customisation']['footer_text']))

		paginator = DiscordUtils.Pagination.CustomEmbedPaginator(ctx)
		paginator.add_reaction('⏪', "back")
		paginator.add_reaction('🗑️', 'lock')
		paginator.add_reaction('⏩', "next")
		await paginator.run(embeds)


# @search.autocomplete('query')
# async def autocomplete_callback(interaction: discord.Interaction, current: str):
# 	datasets = await bot.warnings.get_all()
# 	applicable_data = []
# 	for item in datasets:
# 		for _item in item['warnings']:
# 			if _item['Guild'] == interaction.guild.id:
# 				if item not in applicable_data:
# 					applicable_data.append(item)

# 	logging.info(applicable_data)
# 	applicable_data = [x['_id'] for x in applicable_data if x['_id'].lower().startswith(current.lower())]
# 	logging.info(applicable_data)

# 	choices = []
# 	for item in applicable_data:
# 		if len(choices) >= 25:
# 			break
# 		choices.append(app_commands.Choice(name = item, value = item))
# 	return choices

@bot.hybrid_command(
	name="globalsearch",
	aliases=["gs"],
	description="Searches for a user in the warning database. This will show warnings from all servers. [Search]",
	usage="<user>",
	with_app_command=True,
)
async def globalsearch(ctx, *, query):
	alerts = {
		'NoAlerts': '+ ✅ No alerts found for this account!',
		'AccountAge': '- ⚠️ The account age of the user is less than 100 days.',
		'NoDescription': '- ⚠️ This account has no description, and is likely to be an alt.',
		'SuspiciousUsername': '- ⚠️ The name of this account is suspicious, and could be an alt account.',
		'MassPunishments': '- ⚠️ The amount of punishments this user has is above the regular amount and should be monitored.',
		'UserDoesNotExist': '- ⚠️ This user does not exist. They have been most likely deleted from the platform or a mistake in the database. Contact Mikey for more information.',
		'IsBanned': '- ⚠️ This user is banned from the Roblox platform.',
		'NotManyFriends': '- 🚧 This user has less than 30 friends.',
		'NotManyGroups': '- 🚧 This user has less than 5 groups.'
	}

	logging.info(query)
	query = query.split('.')
	query = query[0]

	logging.info(query)
	RESULTS = []

	dataset = await bot.warnings.find_by_id(query.lower())
	if dataset:
		logging.info(dataset)
		logging.info(dataset['warnings'][0])

		dataset['warnings'][0]['name'] = query.lower()
		RESULTS.append(dataset['warnings'])

	if len(RESULTS) == 0:
		User = await client.get_user_by_username(query)
		if not User:
			return await ctx.send('No user matches your query.')
		triggered_alerts = []

		if User.is_banned:
			triggered_alerts.append('IsBanned')
		if (pytz.utc.localize(datetime.datetime.now()) - User.created).days < 100:
			triggered_alerts.append('AccountAge')
		if not User:
			triggered_alerts.append('UserDoesNotExist')
		if len(User.description) < 10:
			triggered_alerts.append('NoDescription')
		if any(x in User.name for x in ['alt', 'alternative', 'account']):
			triggered_alerts.append('SuspiciousUsername')
		if await User.get_friend_count() <= 30:
			triggered_alerts.append('NotManyFriends')
		if len(await User.get_group_roles()) <= 5:
			triggered_alerts.append('NotManyGroups')

		if len(triggered_alerts) == 0:
			triggered_alerts.append('NoAlerts')

		embed1 = discord.Embed(title=query, color=await generate_random(ctx))
		embed1.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
		embed1.add_field(name='Username', value=embed1.title, inline=False)
		if query.lower() in bot.staff_members.keys():
			await staff_field(embed1, query.lower())
		embed1.add_field(name='Punishments', value=f'0', inline=False)
		string = "\n".join([alerts[i] for i in triggered_alerts])
		embed1.add_field(name='Alerts', value=f'```diff\n{string}\n```', inline=False)
		embed1.set_thumbnail(
			url="https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
				User.id))
		await ctx.send(embed=embed1)

	if len(RESULTS) > 1:
		return await ctx.send(
			'More than one result match your query. If this is unexpected, join the [support server](https://discord.gg/5pMmJEYazQ) and contact a Support Team member.')

	if len(RESULTS) == 1:

		message = ctx.message

		embed1 = discord.Embed(title=RESULTS[0][0]['name'], color=await generate_random(ctx))
		embed2 = discord.Embed(title=RESULTS[0][0]['name'], color=await generate_random(ctx))

		result_var = None

		for result in RESULTS:
			if result[0]['name'] == RESULTS[0][0]['name']:
				result_var = RESULTS[0]

		result = result_var
		triggered_alerts = []

		User = await client.get_user_by_username(result[0]['name'], expand=True, exclude_banned_users=False)

		if User.is_banned:
			triggered_alerts.append('IsBanned')
		if (pytz.utc.localize(datetime.datetime.now()) - User.created).days < 100:
			triggered_alerts.append('AccountAge')
		if not User:
			triggered_alerts.append('UserDoesNotExist')
		if len(User.description) < 10:
			triggered_alerts.append('NoDescription')
		if any(x in User.name for x in ['alt', 'alternative', 'account']):
			triggered_alerts.append('SuspiciousUsername')
		if len(result) > 5:
			triggered_alerts.append('MassPunishments')
		if await User.get_friend_count() <= 30:
			triggered_alerts.append('NotManyFriends')
		if len(await User.get_group_roles()) <= 5:
			triggered_alerts.append('NotManyGroups')

		if len(triggered_alerts) == 0:
			triggered_alerts.append('NoAlerts')

		configItem = await bot.settings.find_by_id(ctx.guild.id)
		if configItem is None:
			return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')

		embeds = []
		embeds.append(embed1)
		embeds.append(embed2)

		embeds[0].add_field(name='Username', value=embed1.title, inline=False)
		if embed1.title in bot.staff_members.keys():
			await staff_field(embed1, embed1.title)
		embeds[0].add_field(name='Punishments', value=f'{len(result)}', inline=False)

		string = "\n".join([alerts[i] for i in triggered_alerts])

		embeds[0].add_field(name='Alerts', value=f'```diff\n{string}\n```', inline=False)

		del result[0]['name']

		for index, action in enumerate(result):
			logging.info(index)
			if 'Until' in action.keys():
				if len(embeds[-1].fields) <= 25:
					embeds[-1].add_field(
						name=action['Type'],
						value=f"Reason: {action['Reason']}\nTime: {action['Time']}\nUntil: <t:{action['Until']}>\nID: {action['id']}\nGuild: {action['Guild']}",
						inline=False
					)
				else:
					embeds.append(discord.Embed(title=embeds[0].title, color=await generate_random(ctx)))
					embeds[-1].add_field(
						name=action['Type'],
						value=f"Reason: {action['Reason']}\nTime: {action['Time']}\nUntil: <t:{action['Until']}>\nID: {action['id']}\nGuild: {action['Guild']}",
						inline=False
					)
			else:
				if len(embeds[-1].fields) <= 25:
					embeds[-1].add_field(
						name=action['Type'],
						value=f"Reason: {action['Reason']}\nTime: {action['Time']}\nID: {action['id']}\nGuild: {action['Guild']}",
						inline=False
					)
				else:
					embeds.append(discord.Embed(title=embeds[0].title, color=await generate_random(ctx)))
					embeds[-1].add_field(
						name=action['Type'],
						value=f"Reason: {action['Reason']}\nTime: {action['Time']}\nID: {action['id']}\nGuild: {action['Guild']}",
						inline=False
					)

		for embed in embeds:
			embed.set_thumbnail(
				url="https://www.roblox.com/headshot-thumbnail/image?userId={}&width=420&height=420&format=png".format(
					User.id))
			embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
			embed.set_footer(icon_url=get_guild_icon(ctx.guild),
							 text="{} | {}".format(configItem['customisation']['brand_name'],
												   configItem['customisation']['footer_text']))

		paginator = DiscordUtils.Pagination.CustomEmbedPaginator(ctx)
		paginator.add_reaction('⏪', "back")
		paginator.add_reaction('🗑️', 'lock')
		paginator.add_reaction('⏩', "next")
		await paginator.run(embeds)


@globalsearch.autocomplete('query')
async def autocomplete_callback(interaction: discord.Interaction, current: str):
	datasets = await bot.warnings.get_all()
	applicable_data = []
	for item in datasets:
		if item not in applicable_data:
			applicable_data.append(item)

	logging.info(applicable_data)
	applicable_data = [x['_id'] for x in applicable_data if x['_id'].lower().startswith(current.lower())]
	logging.info(applicable_data)

	choices = []
	for item in applicable_data:
		if len(choices) >= 25:
			break
		choices.append(app_commands.Choice(name=item, value=item))
	return choices


@bot.hybrid_command(
	name='removewarning',
	aliases=['rw', 'delwarn', 'dw', 'removewarnings', 'rws', 'dws', 'delwarnings'],
	description='Remove a warning from a user. [Management]',
	usage='<user> <warning id>',
	with_app_command=True,
)
@is_staff()
async def removewarning(ctx, id: str):
	try:
		id = int(id)
	except:
		return await ctx.send('`id` is not a valid ID.')

	keyStorage = None
	selected_item = None
	selected_items = []
	item_index = 0

	for item in await bot.warnings.get_all():
		for index, _item in enumerate(item['warnings']):
			if _item['id'] == id:
				selected_item = _item
				selected_items.append(_item)
				parent_item = item
				item_index = index
				break

	if selected_item is None:
		return await ctx.send('That warning does not exist.')

	if selected_item['Guild'] != ctx.guild.id:
		return await ctx.send('You are trying to remove a warning that is not apart of this guild.')

	if len(selected_items) > 1:
		return await ctx.send(
			'There is more than one warning associated with this ID. Please contact Mikey as soon as possible. I have cancelled the removal of this warning since it is unsafe to continue.')

	await ctx.send(
		f"Reason: {selected_item['Reason']}\nModerator: {selected_item['Moderator']}\nID: {selected_item['id']}")

	view = YesNoMenu(ctx.author.id)
	await ctx.send('Are you sure you want to remove this warning?', view=view)
	await view.wait()

	if view.value == True:
		parent_item['warnings'].remove(selected_item)
		await bot.warnings.update_by_id(parent_item)
		await ctx.send('Successfully removed warning.')
	else:
		await ctx.send('Cancelled.')


@bot.hybrid_command(
	name='help',
	aliases=['h', 'commands', 'cmds', 'cmd', 'command'],
	description='Get a list of commands. [Utility]',
	usage='<command>',
	with_app_command=True,
)
async def help(ctx, *, command=None):
	configItem = await bot.settings.find_by_id(ctx.guild.id)
	if configItem is None:
		return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')

	if command == None:

		embed = discord.Embed(
			title='Help | {}'.format(configItem['customisation']['brand_name']),
			description='Use `>help <command>` to get more information about a command.',
			color=await generate_random(ctx)
		)

		try:
			embed.set_thumbnail(url=configItem['customisation']['thumbnail_url'] or get_guild_icon(ctx.guild))
			embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
			embed.set_footer(icon_url=get_guild_icon(ctx.guild),
							 text="{} | {}".format(configItem['customisation']['brand_name'],
												   configItem['customisation']['footer_text']))
		except:
			await ctx.send(
				'Failed to add extensive embed edits. Please add an image to your server for this to work correctly.')
		categories = []
		commands = []
		for command in bot.walk_commands():

			try:
				command.category = command.description.split('[')[1].replace('[', '').replace(']', '')
			except:
				command.category = 'Miscellaneous'

			if isinstance(command, discord.ext.commands.core.Command):
				if command.hidden:
					continue
				if command.parent is not None:
					continue

			if isinstance(command, discord.ext.commands.core.Group):
				continue

			if command.category not in categories:
				categories.append(command.category)
				commands.append(command)
			else:
				commands.append(command)

		for category in categories:
			logging.info(category)
			string = '\n'.join(
				[f'**{configItem["customisation"]["prefix"]}{command.name}** | {command.description.split("[")[0]}' for
				 command in commands if command.category == category])

			logging.info(len(string))
			if len(string) < 1024:
				embed.add_field(
					name=category,
					value=string,
					inline=False
				)

			else:
				embed.add_field(
					name=category,
					value=string[:1024].split('\n')[0],
					inline=False
				)

				embed.add_field(
					name='\u200b',
					value=string[1024:].split('\n')[0],
					inline=False
				)

		await ctx.send(embed=embed)
	else:
		command = bot.get_command(command)
		if command is None:
			return await ctx.send('That command does not exist.')

		embed = discord.Embed(
			title='Help | {}'.format(command.name),
			description=command.description.split('[')[0],
			color=await generate_random(ctx)
		)

		try:
			embed.set_thumbnail(url=ctx.author.avatar.url)
			embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
			embed.set_footer(icon_url=get_guild_icon(ctx.guild), text="{} | {}".format(configItem['customisation']['footer_text'],
																				configItem['customisation']['brand_name']))
		except:
			pass

		embed.add_field(
			name='Usage',
			value='`{}`'.format(command.usage),
			inline=False
		)

		if command.aliases:
			embed.add_field(
				name='Aliases',
				value='`{}`'.format(', '.join(command.aliases)),
				inline=False
			)

		await ctx.send(embed=embed)


@bot.hybrid_group(
	name='duty'
)
async def duty(ctx):
	await ctx.send('You have not picked a subcommand. Subcommand options: `on`, `off`, `time`, `void`')


@duty.command(
	name="on",
	description="Allows for you to clock in. [Shift Management]",
	with_app_command=True,
)
@is_staff()
async def dutyon(ctx):
	configItem = await bot.settings.find_by_id(ctx.guild.id)
	if configItem is None:
		return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')

	if configItem['shift_management']['enabled'] == False:
		return await ctx.send('Shift management is not enabled on this server.')
	try:
		shift_channel = discord.utils.get(ctx.guild.channels, id=configItem['shift_management']['channel'])
		role = discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])
	except:
		return await ctx.send(
			f'Some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.')

	if configItem['shift_management']['enabled'] == False:
		return await ctx.send('Shift management is not enabled on this server.')

	if await bot.shifts.find_by_id(ctx.author.id):
		return await ctx.send('You are already on duty.')

	embed = discord.Embed(
		title=ctx.author.name,
		color=await generate_random(ctx)
	)

	try:
		embed.set_thumbnail(url=ctx.author.avatar.url)
		embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
		embed.set_footer(icon_url=get_guild_icon(ctx.guild), text="{} | {}".format(configItem['customisation']['footer_text'],
																			configItem['customisation']['brand_name']))
	except:
		pass

	embed.add_field(
		name="Name",
		value=ctx.author.name,
		inline=False
	)

	embed.add_field(
		name="Type",
		value="Clocking in.",
		inline=False
	)

	embed.add_field(
		name="Current Time",
		value=ctx.message.created_at.strftime("%m/%d/%Y, %H:%M:%S")
	)

	await bot.shifts.insert({
		'_id': ctx.author.id,
		'name': ctx.author.name,
		'startTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
		'guild': ctx.guild.id
	})

	await shift_channel.send(embed=embed)
	await ctx.send('Successfully clocked in!')

	role = discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])

	if role:
		if not role in ctx.author.roles:
			await ctx.author.add_roles(role)


@duty.command(
	name="off",
	description="Allows for you to clock out. [Shift Management]",
	with_app_command=True,
)
@is_staff()
async def dutyoff(ctx):
	configItem = await bot.settings.find_by_id(ctx.guild.id)
	if configItem is None:
		return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')

	if configItem['shift_management']['enabled'] == False:
		return await ctx.send('Shift management is not enabled on this server.')
	try:
		shift_channel = discord.utils.get(ctx.guild.channels, id=configItem['shift_management']['channel'])
		role = discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])
	except:
		return await ctx.send(
			f'Some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.')

	if configItem['shift_management']['enabled'] == False:
		return await ctx.send('Shift management is not enabled on this server.')

	global_check = 0
	shift = None

	if await bot.shifts.find_by_id(ctx.author.id):
		global_check = 1
	else:
		global_check = 0

	if global_check > 1:
		return await ctx.send(
			'You have more than one concurrent shift. This should be impossible. Contact Mikey for more inforamtion.')
	if global_check == 0:
		return await ctx.send('You have no concurrent shifts! Please clock in before clocking out.')

	if global_check == 1:
		shift = await bot.shifts.find_by_id(ctx.author.id)

	embed = discord.Embed(
		title=ctx.author.name,
		color=await generate_random(ctx)
	)

	try:
		embed.set_thumbnail(url=ctx.author.avatar.url)
		embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
		embed.set_footer(icon_url=get_guild_icon(ctx.guild), text="{} | {}".format(configItem['customisation']['footer_text'],
																			configItem['customisation']['brand_name']))
	except:
		pass

	embed.add_field(
		name="Name",
		value=ctx.author.name,
		inline=False
	)

	embed.add_field(
		name="Type",
		value="Clocking out.",
		inline=False
	)

	embed.add_field(
		name="Elapsed Time",
		value=td_format(
			ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(shift['startTimestamp'])),
		inline=False
	)

	time_delta = ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
		shift['startTimestamp']).replace(tzinfo=None)

	await shift_channel.send(embed=embed)

	if not await bot.shift_storage.find_by_id(ctx.author.id):
		await bot.shift_storage.insert({
			'_id': ctx.author.id,
			'shifts': [
				{
					'name': ctx.author.name,
					'startTimestamp': shift['startTimestamp'],
					'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
					'totalSeconds': time_delta.total_seconds(),
					'guild': ctx.guild.id
				}],
			'totalSeconds': time_delta.total_seconds()

		})
	else:
		if "shifts" in await bot.shift_storage.find_by_id(ctx.author.id):
			if not None in dict(await bot.shift_storage.find_by_id(ctx.author.id)).values():

				await bot.shift_storage.update_by_id(
					{
						'_id': ctx.author.id,
						'shifts': [(await bot.shift_storage.find_by_id(ctx.author.id))['shifts']].append(

							{
								'name': ctx.author.name,
								'startTimestamp': shift['startTimestamp'],
								'endTimestamp': ctx.message.created_at.replace(tzinfo=None).timestamp(),
								'totalSeconds': time_delta.total_seconds(),
								'guild': ctx.guild.id
							}

						),
						'totalSeconds': sum(
							[(await bot.shift_storage.find_by_id(ctx.author.id))['shifts'][i]['totalSeconds'] for i in
							 range(len((await bot.shift_storage.find_by_id(ctx.author.id))['shifts']))])
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
							'guild': ctx.guild.id
						}],
					'totalSeconds': time_delta.total_seconds()

				})

	await bot.shifts.delete_by_id(ctx.author.id)
	await ctx.send('Successfully clocked out!')

	role = discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])

	if role:
		if not role in ctx.author.roles:
			await ctx.author.remove_roles(role)


@duty.command(
	name="time",
	description="Allows for you to check your shift time. [Shift Management]",
	with_app_command=True,
)
@is_staff()
async def dutytime(ctx):
	configItem = await bot.settings.find_by_id(ctx.guild.id)
	if configItem is None:
		return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')

	if configItem['shift_management']['enabled'] == False:
		return await ctx.send('Shift management is not enabled on this server.')
	try:
		shift_channel = discord.utils.get(ctx.guild.channels, id=configItem['shift_management']['channel'])
		role = discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])
	except:
		return await ctx.send(
			f'Some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.')

	if configItem['shift_management']['enabled'] == False:
		return await ctx.send('Shift management is not enabled on this server.')

	global_check = 0
	shift = None

	if await bot.shifts.find_by_id(ctx.author.id):
		global_check = 1
	else:
		global_check = 0

	if global_check > 1:
		return await ctx.send(
			'You have more than one concurrent shift. This should be impossible. Contact Mikey for more inforamtion.')
	if global_check == 0:
		return await ctx.send('You have no concurrent shifts! Please clock in before requesting shift estimation.')

	if global_check == 1:
		shift = await bot.shifts.find_by_id(ctx.author.id)

	embed = discord.Embed(
		title=ctx.author.name,
		color=await generate_random(ctx)
	)

	try:
		embed.set_thumbnail(url=ctx.author.avatar.url)
		embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
		embed.set_footer(icon_url=get_guild_icon(ctx.guild), text="{} | {}".format(configItem['customisation']['footer_text'],
																			configItem['customisation']['brand_name']))
	except:
		pass

	embed.add_field(
		name="Name",
		value=ctx.author.name,
		inline=False
	)

	embed.add_field(
		name="Elapsed Time",
		value=str(ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
			shift['startTimestamp']).replace(tzinfo=None)).split('.')[0])

	await ctx.send(embed=embed)


@duty.command(
	name="void",
	description="Allows for you to void your shift. [Shift Management]",
	with_app_command=True,
)
@is_staff()
async def dutyvoid(ctx):
	configItem = await bot.settings.find_by_id(ctx.guild.id)
	if configItem is None:
		return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')

	if configItem['shift_management']['enabled'] == False:
		return await ctx.send('Shift management is not enabled on this server.')
	try:
		shift_channel = discord.utils.get(ctx.guild.channels, id=configItem['shift_management']['channel'])
		role = discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])
	except:
		return await ctx.send(
			f'Some of the required values needed to use this command are missing from your database entry. Try setting up the bot via `{(await bot.settings.find_by_id(ctx.guild.id))["customisation"]["prefix"]}setup`.')

	if configItem['shift_management']['enabled'] == False:
		return await ctx.send('Shift management is not enabled on this server.')

	global_check = 0
	shift = None

	if await bot.shifts.find_by_id(ctx.author.id):
		global_check = 1
	else:
		global_check = 0

	if global_check > 1:
		return await ctx.send(
			'You have more than one concurrent shift. This should be impossible. Contact Mikey for more inforamtion.')
	if global_check == 0:
		return await ctx.send('You have no concurrent shifts! Please clock in before requesting shift cancelling.')
	if global_check == 1:
		shift = await bot.shifts.find_by_id(ctx.author.id)

	view = YesNoMenu(ctx.author.id)
	await ctx.send(
		'Are you sure you would like to void your shift? This is **irreversible** and will remove your shift from the database forever.',
		view=view)
	await view.wait()

	if view.value == False:
		return await ctx.send('Cancelled.')

	embed = discord.Embed(
		title=ctx.author.name,
		color=await generate_random(ctx)
	)

	try:
		embed.set_thumbnail(url=ctx.author.avatar.url)
		embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
		embed.set_footer(icon_url=get_guild_icon(ctx.guild), text="{} | {}".format(configItem['customisation']['footer_text'],
																			configItem['customisation']['brand_name']))
	except:
		pass

	embed.add_field(
		name="Name",
		value=ctx.author.name,
		inline=False
	)

	embed.add_field(
		name="Elapsed Time",
		value=str(ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
			shift['startTimestamp'])).split('.')[0]
	)

	await ctx.send('`VOID`: Shift has been cancelled successfully.', embed=embed)

	embed = discord.Embed(title=ctx.author.name, color=await generate_random(ctx))
	try:
		embed.set_thumbnail(url=ctx.author.avatar.url)
		embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
		embed.set_footer(icon_url=get_guild_icon(ctx.guild), text="{} | {}".format(configItem['customisation']['footer_text'],
																			configItem['customisation']['brand_name']))
	except:
		pass
	embed.add_field(name="Name", value=ctx.author.name, inline=False)
	embed.add_field(name="Type", value=f"Voided time (performed by {ctx.author.mention}).", inline=False)
	embed.add_field(name="Elapsed Time", value=
	str(ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(shift['startTimestamp']).replace(
		tzinfo=None)).split('.')[0])

	await bot.shifts.delete_by_id(ctx.author.id)
	role = discord.utils.get(ctx.guild.roles, id=configItem['shift_management']['role'])
	await shift_channel.send(embed=embed)

	if role:
		if not role in ctx.author.roles:
			await ctx.author.remove_roles(role)


@duty.autocomplete('setting')
async def autocomplete_callback(interaction: discord.Interaction, current: str):
	# Do stuff with the "current" parameter, e.g. querying it search results...

	# Then return a list of app_commands.Choice
	return [
		app_commands.Choice(name='Go on duty', value='on'),
		app_commands.Choice(name='Go off duty', value='off'),
		app_commands.Choice(name='Estimate time', value='time'),
		app_commands.Choice(name='Cancel shift', value='cancel'),
	]


@bot.hybrid_command(
	name='reducedactivity',
	aliases=['rarq', 'rrq', 'ra'],
	description='File a Reduced Activity request [Staff Management]',
	with_app_command=True,
)
async def rarequest(ctx, time, *, reason):
	configItem = await bot.settings.find_by_id(ctx.guild.id)
	if configItem is None:
		return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')

	timeObj = list(reason)[-1]
	reason = list(reason)

	if not time.endswith(('h', 'm', 's', 'd', 'w')):
		reason.insert(0, time)
		if not timeObj.endswith(('h', 'm', 's', 'd', 'w')):
			return await ctx.reply(
				'A time must be provided at the start or at the end of the command. Example: `>ra 12h Going to walk my shark` / `>ra Mopping the ceiling 12h`')
		else:
			time = timeObj
			reason.pop()

	if time.endswith('s'):
		time = int(removesuffix(time, 's'))
	elif time.endswith('m'):
		time = int(removesuffix(time, 'm')) * 60
	elif time.endswith('h'):
		time = int(removesuffix(time, 'h')) * 60 * 60
	elif time.endswith('d'):
		time = int(removesuffix(time, 'd')) * 60 * 60 * 24
	elif time.endswith('w'):
		time = int(removesuffix(time, 'w')) * 60 * 60 * 24 * 7

	startTimestamp = datetime.datetime.timestamp(ctx.message.created_at)
	endTimestamp = int(startTimestamp + time)

	Embed = discord.Embed(
		title="Reduced Activity",
		color=await generate_random(ctx)
	)

	try:
		Embed.set_thumbnail(url=ctx.author.avatar.url)
		Embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
		Embed.set_footer(icon_url=get_guild_icon(ctx.guild), text="{} | {}".format(configItem['customisation']['footer_text'],
																			configItem['customisation']['brand_name']))
	except:
		pass
	Embed.add_field(
		name="Staff Member",
		value=ctx.author.mention,
		inline=False
	)

	Embed.add_field(
		name="Start",
		value=f'<t:{int(startTimestamp)}>',
		inline=False
	)

	Embed.add_field(
		name="End",
		value=f'<t:{int(endTimestamp)}>',
		inline=False
	)

	reason = ''.join(reason)

	Embed.add_field(
		name='Reason',
		value=f'{reason}',
		inline=False
	)

	channel = discord.utils.get(ctx.guild.channels, id=configItem['staff_management']['channel'])
	await channel.send(embed=Embed)
	await ctx.reply('Sent your RA request.')


@bot.hybrid_command(
	name='leaveofabsence',
	aliases=['loarq', 'lorq', 'loa'],
	description='File a Leave of Absence request [Staff Management]',
	with_app_command=True,
)
async def loarequest(ctx, time, *, reason):
	configItem = await bot.settings.find_by_id(ctx.guild.id)
	if configItem is None:
		return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')

	try:
		timeObj = reason.split(' ')[-1]
	except:
		timeObj = ""
	reason = list(reason)

	if not time.endswith(('h', 'm', 's', 'd', 'w')):
		reason.insert(0, time)
		if not timeObj.endswith(('h', 'm', 's', 'd', 'w')):
			return await ctx.reply(
				'A time must be provided at the start or at the end of the command. Example: `>loa 12h Going to walk my shark` / `>loa Mopping the ceiling 12h`')
		else:
			time = timeObj
			reason.pop()

	if time.endswith('s'):
		time = int(removesuffix(time, 's'))
	elif time.endswith('m'):
		time = int(removesuffix(time, 'm')) * 60
	elif time.endswith('h'):
		time = int(removesuffix(time, 'h')) * 60 * 60
	elif time.endswith('d'):
		time = int(removesuffix(time, 'd')) * 60 * 60 * 24
	elif time.endswith('w'):
		time = int(removesuffix(time, 'w')) * 60 * 60 * 24 * 7

	startTimestamp = datetime.datetime.timestamp(ctx.message.created_at)
	endTimestamp = int(startTimestamp + time)

	Embed = discord.Embed(
		title="Leave of Absence",
		color=await generate_random(ctx)
	)

	try:
		Embed.set_thumbnail(url=ctx.author.avatar.url)
		Embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
		Embed.set_footer(icon_url=get_guild_icon(ctx.guild), text="{} | {}".format(configItem['customisation']['footer_text'],
																			configItem['customisation']['brand_name']))
	except:
		pass
	Embed.add_field(
		name="Staff Member",
		value=ctx.author.mention,
		inline=False
	)

	Embed.add_field(
		name="Start",
		value=f'<t:{int(startTimestamp)}>',
		inline=False
	)

	Embed.add_field(
		name="End",
		value=f'<t:{int(endTimestamp)}>',
		inline=False
	)

	reason = ''.join(reason)

	Embed.add_field(
		name='Reason',
		value=f'{reason}',
		inline=False
	)

	channel = discord.utils.get(ctx.guild.channels, id=configItem['staff_management']['channel'])
	await channel.send(embed=Embed)
	await ctx.reply('Sent your LOA request.')


# context menus
@bot.tree.context_menu(name='Force end shift')
@app_commands.checks.has_permissions(manage_guild=True)
async def force_end_shift(interaction: discord.Interaction, member: discord.Member):
	try:
		configItem = await bot.settings.find_by_id(interaction.guild.id)
	except:
		return await interaction.response.send_message(
			'The server has not been set up yet. Please run `>setup` to set up the server.', ephemeral=True)

	shift = await bot.shifts.find_by_id(member.id)
	if configItem['shift_management']['enabled'] == False:
		return await interaction.response.send_message('Shift management is not enabled on this server.',
													   ephemeral=True)
	try:
		shift_channel = discord.utils.get(interaction.guild.channels, id=configItem['shift_management']['channel'])
	except:
		return await interaction.response.send_message('Shift management channel not found.', ephemeral=True)

	if shift is None:
		return await interaction.response.send_message('This member is not currently on shift.', ephemeral=True)
	if shift['guild'] != interaction.guild.id:
		return await interaction.response.send_message('This member is not currently on shift.', ephemeral=True)

	view = YesNoMenu(interaction.user.id)
	await interaction.response.send_message(f'Are you sure you want to force end the shift of {member.mention}?',
											view=view, ephemeral=True)
	await view.wait()

	if view.value == False:
		return await interaction.response.send_message('Cancelled.', ephemeral=True)
	elif view.value == None:
		return await interaction.response.send_message('Timed out.', ephemeral=True)
	elif view.value == True:
		time_delta = interaction.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
			shift['startTimestamp']).replace(tzinfo=None)

		embed = discord.Embed(title=member.name, color=await generate_random(interaction))
		try:
			embed.set_thumbnail(url=member.avatar.url)
			embed.set_author(name=member.name, icon_url=member.avatar.url)
			embed.set_footer(icon_url=get_guild_icon(interaction.guild),
							 text="{} | {}".format(configItem['customisation']['brand_name'],
												   configItem['customisation']['footer_text']))
		except:
			pass
		embed.add_field(name="Name", value=member.name, inline=False)
		embed.add_field(name="Type", value="Clocking out.", inline=False)
		embed.add_field(name="Elapsed Time", value=
		str(interaction.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
			shift['startTimestamp']).replace(tzinfo=None)).split('.')[0])

		if not await bot.shift_storage.find_by_id(member.id):
			await bot.shift_storage.insert({
				'_id': member.id,
				'shifts': [
					{
						'name': member.name,
						'startTimestamp': shift['startTimestamp'],
						'endTimestamp': interaction.created_at.replace(tzinfo=None).timestamp(),
						'totalSeconds': time_delta.total_seconds(),
						'guild': interaction.guild.id
					}],
				'totalSeconds': time_delta.total_seconds()

			})
		else:
			logging.info((await bot.shift_storage.find_by_id(member.id))['shifts'])
			await bot.shift_storage.update_by_id(
				{
					'_id': member.id,
					'shifts': [(await bot.shift_storage.find_by_id(member.id))['shifts']].append(

						{
							'name': member.name,
							'startTimestamp': shift['startTimestamp'],
							'endTimestamp': interaction.created_at.replace(tzinfo=None).timestamp(),
							'totalSeconds': time_delta.total_seconds(),
							'guild': interaction.guild.id
						}

					),
					'totalSeconds': sum(
						[(await bot.shift_storage.find_by_id(member.id))['shifts'][i]['totalSeconds'] for i in
						 range(len((await bot.shift_storage.find_by_id(member.id))['shifts']))])
				}
			)

		logging.info(await bot.warnings.find_by_id(member.id))
		await bot.shifts.delete_by_id(member.id)
		await shift_channel.send(embed=embed)

		role = discord.utils.get(interaction.guild.roles, id=configItem['shift_management']['role'])

		if role:
			if role in member.roles:
				await member.remove_roles(role)


@bot.tree.context_menu(name='Force start shift')
@app_commands.checks.has_permissions(manage_guild=True)
async def force_start_shift(interaction: discord.Interaction, member: discord.Member):
	try:
		configItem = await bot.settings.find_by_id(interaction.guild.id)
	except:
		return await interaction.response.send_message(
			'The server has not been set up yet. Please run `>setup` to set up the server.', ephemeral=True)

	shift = await bot.shifts.find_by_id(member.id)
	if configItem['shift_management']['enabled'] == False:
		return await interaction.response.send_message('Shift management is not enabled on this server.',
													   ephemeral=True)
	try:
		shift_channel = discord.utils.get(interaction.guild.channels, id=configItem['shift_management']['channel'])
	except:
		return await interaction.response.send_message('Shift management channel not found.', ephemeral=True)

	if shift is not None:
		return await interaction.response.send_message('This member is currently on shift.', ephemeral=True)

	view = YesNoMenu(interaction.user.id)
	await interaction.response.send_message(f'Are you sure you want to force start the shift of {member.mention}?',
											view=view, ephemeral=True)
	await view.wait()

	if view.value == False:
		return await interaction.response.send_message('Cancelled.', ephemeral=True)
	elif view.value == None:
		return await interaction.response.send_message('Timed out.', ephemeral=True)
	elif view.value == True:

		embed = discord.Embed(title=member.name, color=await generate_random(interaction))
		try:
			embed.set_thumbnail(url=member.avatar.url)
			embed.set_author(name=member.name, icon_url=member.avatar.url)
			embed.set_footer(icon_url=get_guild_icon(interaction.guild),
							 text="{} | {}".format(configItem['customisation']['brand_name'],
												   configItem['customisation']['footer_text']))
		except:
			pass

		embed.add_field(name="Name", value=member.name, inline=False)
		embed.add_field(name="Type", value="Clocking in.", inline=False)

		await bot.shifts.insert({
			'_id': member.id,
			'name': member.name,
			'startTimestamp': interaction.created_at.replace(tzinfo=None).timestamp(),
			'guild': interaction.guild.id
		})

		await shift_channel.send(embed=embed)

		role = discord.utils.get(interaction.guild.roles, id=configItem['shift_management']['role'])

		if role:
			if role in member.roles:
				await member.add_roles(role)


@bot.tree.context_menu(name='Get shift time')
@app_commands.checks.has_permissions(manage_guild=True)
async def get_shift_time(interaction: discord.Interaction, member: discord.Member):
	try:
		configItem = await bot.settings.find_by_id(interaction.guild.id)
	except:
		return await interaction.response.send_message(
			'The server has not been set up yet. Please run `>setup` to set up the server.', ephemeral=True)

	shift = await bot.shifts.find_by_id(member.id)
	if configItem['shift_management']['enabled'] == False:
		return await interaction.response.send_message('Shift management is not enabled on this server.',
													   ephemeral=True)
	try:
		shift_channel = discord.utils.get(interaction.guild.channels, id=configItem['shift_management']['channel'])
	except:
		return await interaction.response.send_message('Shift management channel not found.', ephemeral=True)

	if shift is None:
		return await interaction.response.send_message('This member is not currently on shift.', ephemeral=True)
	if shift['guild'] != interaction.guild.id:
		return await interaction.response.send_message('This member is not currently on shift.', ephemeral=True)

	await interaction.response.send_message(
		f'{member.mention} has been on-shift for `{str(datetime.datetime.now() - datetime.datetime.fromtimestamp(shift["startTimestamp"])).split(".")[0]}`.',
		ephemeral=True)


# context menus
@bot.tree.context_menu(name='Void shift')
@app_commands.checks.has_permissions(manage_guild=True)
async def force_end_shift(interaction: discord.Interaction, member: discord.Member):
	try:
		configItem = await bot.settings.find_by_id(interaction.guild.id)
	except:
		return await interaction.response.send_message(
			'The server has not been set up yet. Please run `>setup` to set up the server.', ephemeral=True)

	shift = await bot.shifts.find_by_id(member.id)
	if configItem['shift_management']['enabled'] == False:
		return await interaction.response.send_message('Shift management is not enabled on this server.',
													   ephemeral=True)
	try:
		shift_channel = discord.utils.get(interaction.guild.channels, id=configItem['shift_management']['channel'])
	except:
		return await interaction.response.send_message('Shift management channel not found.', ephemeral=True)

	if shift is None:
		return await interaction.response.send_message('This member is not currently on shift.', ephemeral=True)
	if shift['guild'] != interaction.guild.id:
		return await interaction.response.send_message('This member is not currently on shift.', ephemeral=True)

	view = YesNoMenu(interaction.user.id)
	await interaction.response.send_message(f'Are you sure you want to void the shift of {member.mention}?', view=view,
											ephemeral=True)
	await view.wait()

	if view.value == False:
		return await interaction.response.send_message('Cancelled.', ephemeral=True)
	elif view.value == None:
		return await interaction.response.send_message('Timed out.', ephemeral=True)
	elif view.value == True:

		embed = discord.Embed(title=member.name, color=generate_random(interaction))
		try:
			embed.set_thumbnail(url=member.avatar.url)
			embed.set_author(name=member.name, icon_url=member.avatar.url)
			embed.set_footer(icon_url=get_guild_icon(interaction.guild),
							 text="{} | {}".format(configItem['customisation']['brand_name'],
												   configItem['customisation']['footer_text']))
		except:
			pass

		embed.add_field(name="Name", value=member.name, inline=False)
		embed.add_field(name="Type", value=f"Voided time (performed by {interaction.user.mention}).", inline=False)
		embed.add_field(name="Elapsed Time", value=
		str(interaction.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
			shift['startTimestamp']).replace(tzinfo=None)).split('.')[0])

		logging.info(await bot.warnings.find_by_id(member.id))
		await bot.shifts.delete_by_id(member.id)
		await shift_channel.send(embed=embed)

		role = discord.utils.get(interaction.guild.roles, id=configItem['shift_management']['role'])

		if role:
			if role in member.roles:
				await member.remove_roles(role)


# clockedin, to get all the members of a specific guild currently on duty
@bot.hybrid_command(name='clockedin', description='Get all members of the server currently on shift.',
					aliases=['on-duty'])
@is_staff()
async def clockedin(ctx):
	try:
		configItem = await bot.settings.find_by_id(ctx.guild.id)
	except:
		return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')

	shift_channel = discord.utils.get(ctx.guild.channels, id=configItem['shift_management']['channel'])

	if shift_channel is None:
		return await ctx.send('Shift management channel not found.')

	embed = discord.Embed(title='Currently on shift', color=await generate_random(ctx))
	try:
		embed.set_footer(icon_url=get_guild_icon(ctx.guild), text="{} | {}".format(configItem['customisation']['brand_name'],
																			configItem['customisation']['footer_text']))
	except:
		pass

	for shift in await bot.shifts.get_all():
		if shift['guild'] == ctx.guild.id:
			member = discord.utils.get(ctx.guild.members, id=shift['_id'])
			if member:
				embed.add_field(name=member.name, value=td_format(
					ctx.message.created_at.replace(tzinfo=None) - datetime.datetime.fromtimestamp(
						shift['startTimestamp'])), inline=False)

	await ctx.send(embed=embed)


# staff info command, to get total seconds worked on a specific member
@duty.command(name='info', description='Get the total seconds worked on a specific member. [Shift Management]',
			  aliases=['staff-stats'])
@is_staff()
async def staff_info(ctx, member: discord.Member = None):
	if member == None:
		member = ctx.author

	try:
		configItem = await bot.settings.find_by_id(ctx.guild.id)
	except:
		return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')

	shift_channel = discord.utils.get(ctx.guild.channels, id=configItem['shift_management']['channel'])

	if shift_channel is None:
		return await ctx.send('Shift management channel not found.')

	embed = discord.Embed(title=f'{member.name}\'s total time worked', color=await generate_random(ctx))
	try:
		embed.set_footer(icon_url=get_guild_icon(ctx.guild), text="{} | {}".format(configItem['customisation']['brand_name'],
																			configItem['customisation']['footer_text']))
	except:
		pass

	if not await bot.shift_storage.find_by_id(member.id):
		await ctx.send(f'{member.name} has not worked on any shifts.')
		return

	total_seconds = 0
	for shift in (await bot.shift_storage.find_by_id(member.id))['shifts']:
		if isinstance(shift, dict):
			if shift['guild'] == ctx.guild.id:
				total_seconds += int(shift['totalSeconds'])

	if td_format(datetime.timedelta(seconds=total_seconds)) not in ["", None]:
		embed.add_field(name='Total Time', value=td_format(datetime.timedelta(seconds=total_seconds)), inline=False)
	else:
		embed.add_field(name="Total Time", value="No shifts found", inline=False)
	await ctx.send(embed=embed)


@duty.command(name='leaderboard',
			  description='Get the total time worked for the whole of the staff team. [Shift Management]',
			  aliases=['shift-lb'])
@is_staff()
async def shift_leaderboard(ctx):
	try:
		configItem = await bot.settings.find_by_id(ctx.guild.id)
	except:
		return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')
	# if not await bot.shift_storage.find_by_id(member.id):
	# 	await ctx.send(f'{member.name} has not worked on any shifts.')
	# 	return

	all_staff = [{"id": None, "total_seconds": 0}]

	for document in await bot.shift_storage.get_all():
		total_seconds = 0
		if "shifts" in document.keys():
			if isinstance(document['shifts'], list):
				for shift in document['shifts']:
					if isinstance(shift, dict):
						if shift['guild'] == ctx.guild.id:
							total_seconds += int(shift['totalSeconds'])
							if document['_id'] not in [item['id'] for item in all_staff]:
								all_staff.append({'id': document['_id'], 'total_seconds': total_seconds})
							else:
								for item in all_staff:
									if item['id'] == document['_id']:
										item['total_seconds'] = item['total_seconds'] + total_seconds
	if len(all_staff) == 0:
		return await ctx.send('No shifts were made in your server.')
	for item in all_staff:
		if item['id'] is None:
			all_staff.remove(item)

	sorted_staff = sorted(all_staff, key=lambda x: x['total_seconds'], reverse=True)

	buffer = None
	for i in sorted_staff:
		member = discord.utils.get(ctx.guild.members, id=i['id'])
		if member:
			if buffer is None:
				buffer = "%s - %s" % (member.name, td_format(datetime.timedelta(seconds=i['total_seconds'])))
			else:
				buffer = buffer + "\n%s - %s" % (member.name, td_format(datetime.timedelta(seconds=i['total_seconds'])))

	bbytes = buffer.encode('utf-8')
	await ctx.send(file=discord.File(fp=BytesIO(bbytes), filename='shift_leaderboard.txt'))



@duty.command(name='clear',
			  description='Clears all of a member\'s shift data. [Shift Management]',
			  aliases=['shift-cl'])
@app_commands.checks.has_permissions(administrator=True)
async def clearmember(ctx, member: discord.Member = None):
	if member is None:
		member = ctx.author
	try:
		configItem = await bot.settings.find_by_id(ctx.guild.id)
	except:
		return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')
	# if not await bot.shift_storage.find_by_id(member.id):
	# 	await ctx.send(f'{member.name} has not worked on any shifts.')
	# 	return

	view = YesNoMenu(ctx.author.id)
	await ctx.send(f'Are you sure you would like to clear `{member.nick}`\'s shift data?', view=view)
	await view.wait()
	if view.value is False:
		return await ctx.send('Successfully cancelled.')

	document = await bot.shift_storage.find_by_id(member.id)
	if "shifts" in document.keys():
		if isinstance(document['shifts'], list):
			for shift in document['shifts']:
				if isinstance(shift, dict):
					if shift['guild'] == ctx.guild.id:
						document['shifts'].remove(shift)
			await bot.shift_storage.update_by_id(document)

	await ctx.send(f'Shift data of `{member.nick}` cleared.')


@duty.command(name='clearall',
			  description='Clears all of the shift data. [Shift Management]',
			  aliases=['shift-cla'])
@app_commands.checks.has_permissions(administrator=True)
async def clearall(ctx):
	try:
		configItem = await bot.settings.find_by_id(ctx.guild.id)
	except:
		return await ctx.send('The server has not been set up yet. Please run `>setup` to set up the server.')
	# if not await bot.shift_storage.find_by_id(member.id):
	# 	await ctx.send(f'{member.name} has not worked on any shifts.')
	# 	return

	view = YesNoMenu(ctx.author.id)
	await ctx.send('Are you sure you would like to clear all shift data?', view=view)
	await view.wait()
	if view.value is False:
		return await ctx.send('Successfully cancelled.')

	for document in await bot.shift_storage.get_all():
		if "shifts" in document.keys():
			if isinstance(document['shifts'], list):
				for shift in document['shifts']:
					if isinstance(shift, dict):
						if shift['guild'] == ctx.guild.id:
							document['shifts'].remove(shift)
				await bot.shift_storage.update_by_id(document)

	await ctx.send('Shift data cleared.')

if __name__ == "__main__":
	bot.run(bot_token)
