import discord
from discord.ext import commands
from menus import LinkPathwayMenu, EnterRobloxUsername, Verification
import aiohttp
from utils.utils import invis_embed

class ModerationSync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="link",
        description="Link your Roblox account to your Discord account via verification methods such as Bloxlink and ERM",
        extras={"category": "Moderation Sync"},
        usage="link"
    )
    async def link(self, ctx):
        bot = self.bot
        is_erm_verified = False
        erm_roblox_id = 0
        async for document in bot.verification.db.find({"_id": ctx.author.id}):
            if document.get('is_verified'):
                is_erm_verified = True
                erm_roblox_id = document.get('roblox')

        if is_erm_verified:
            embed = discord.Embed(
                title="<:SyncIcon:1071821068551073892> ROBLOX Account Linking",
                description=f"<:ArrowRight:1035003246445596774> You can link your Roblox account to your Discord account via verification methods such as Bloxlink and ERM.\n\n<:ArrowRight:1035003246445596774> You seem to be already verified with ERM! Would you like to use your account linked with ERM or use Bloxlink?",
                color=0x2e3136
            )
            view = LinkPathwayMenu(ctx.author.id)
            await ctx.send(embed=embed, view=view)
            timeout = await view.wait()
            if timeout:
                return

            pathway = view.value
        else:
            embed = discord.Embed(
                title="<:SyncIcon:1071821068551073892> ROBLOX Account Linking",
                description=f"<:ArrowRight:1035003246445596774> You can link your Roblox account to your Discord account via verification methods such as Bloxlink and ERM. Please pick a verification provider to continue this process with.",
                color=0x2e3136
            )
            view = LinkPathwayMenu(ctx.author.id)
            await ctx.send(embed=embed, view=view)
            timeout = await view.wait()
            if timeout:
                return

            pathway = view.value

        if pathway == "bloxlink":
            ex_code = 0

            async def run_pathway():
                async with aiohttp.ClientSession(headers={
                    "api-key": bot.bloxlink_api_key
                }) as session:
                    try:
                        async with session.get(
                                f"https://v3.blox.link/developer/discord/{ctx.author.id}") as resp:
                            rbx = await resp.json()
                            if rbx['success']:
                                if rbx['user']['primaryAccount'] not in [None, 0]:
                                    verified_user = rbx['user']['primaryAccount']
                                else:
                                    verified_user = rbx['user']['robloxId']
                                status = True
                            else:
                                status = False
                    except:
                        status = None

                if status:
                    embed = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success!",
                        description=f"<:ArrowRight:1035003246445596774> You have successfully linked your Roblox account to your Discord account!",
                        color=0x71c15f
                    )
                    if await bot.synced_users.find_by_id(ctx.author.id):
                        await bot.synced_users.update_by_id({"_id": ctx.author.id, "roblox": verified_user})
                    else:
                        await bot.synced_users.insert({
                            "_id": ctx.author.id,
                            "roblox": verified_user
                        })
                    await ctx.send(embed=embed)
                elif status is False:
                    embed = discord.Embed(
                        title="<:SyncIcon:1071821068551073892> ROBLOX Account Linking",
                        description=f"<:ArrowRight:1035003246445596774> You have not verified your account with Bloxlink. You can verify your account with Bloxlink by following the instructions below.\n\n<:ArrowRight:1035003246445596774> Follow [this link](https://blox.link/dashboard/verifications) to verify your account with Bloxlink. If you have verified, click **Done** below.",
                        color=0x2e3136)
                    view = Verification(ctx.author.id)
                    await ctx.send(embed=embed, view=view)
                    timeout = await view.wait()
                    if timeout:
                        return
                    if view.value == "cancel":
                        return
                    else:
                        await run_pathway()
                elif status is None:
                    ex_code = 1
                    pathway = "erm"

            if ex_code == 0:
                await run_pathway()
        if pathway == "erm":
            async def run_pathway():
                user = None
                verified = False
                verified_user = await bot.verification.find_by_id(ctx.author.id)

                if verified_user:
                    if 'isVerified' in verified_user.keys():
                        if verified_user['isVerified']:
                            verified = True
                        else:
                            verified_user = None
                    else:
                        verified = True

                if user is None and verified_user is None:
                    view = EnterRobloxUsername(ctx.author.id)
                    embed = discord.Embed(
                        title="<:LinkIcon:1044004006109904966> ERM Verification",
                        description="<:ArrowRight:1035003246445596774> Click `Verify` and input your ROBLOX username.",
                        color=0x2E3136
                    )
                    embed.set_footer(text="ROBLOX Verification provided by ERM")
                    await ctx.send(embed=embed, view=view)
                    await view.wait()
                    if view.modal:
                        try:
                            user = view.modal.name.value
                        except:
                            return await invis_embed(ctx, 'You have not submitted a username. Please try again.')
                    else:
                        return await invis_embed(ctx, 'You have not submitted a username. Please try again.')
                else:
                    if user is None:
                        user = verified_user['roblox']
                        verified = True
                    else:
                        user = user
                        verified = False

                async def after_verified(roblox_user):
                    embed = discord.Embed(
                        title="<:CheckIcon:1035018951043842088> Success!",
                        description=f"<:ArrowRight:1035003246445596774> You have successfully linked your Roblox account to your Discord account!",
                        color=0x71c15f
                    )
                    if await bot.synced_users.find_by_id(ctx.author.id):
                        await bot.synced_users.update_by_id({"_id": ctx.author.id, "roblox": str(roblox_user)})
                    else:
                        await bot.synced_users.insert({
                            "_id": ctx.author.id,
                            "roblox": str(roblox_user)
                        })
                    await ctx.send(embed=embed)

                if verified:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f'https://users.roblox.com/v1/users/{user}') as r:
                            if r.status == 200:
                                roblox_user = await r.json()
                                roblox_id = roblox_user['id']
                                return await after_verified(roblox_user['id'])

                async with aiohttp.ClientSession() as session:
                    async with session.post(f'https://users.roblox.com/v1/usernames/users',
                                            json={"usernames": [user]}) as r:
                        if 'success' in (await r.json()).keys():
                            if not (await r.json())['success']:
                                async with session.get(f'https://users.roblox.com/v1/users/{user}') as r:
                                    if r.status == 200:
                                        roblox_user = await r.json()
                                        roblox_id = roblox_user['id']
                                    else:
                                        return await invis_embed(ctx,
                                                                 'That is not a valid roblox username. Please try again.')

                        else:
                            roblox_user = await r.json()
                            roblox_user = roblox_user['data'][0]
                            roblox_id = roblox_user['id']

                if not verified:
                    await bot.verification.upsert({
                        "_id": ctx.author.id,
                        "roblox": roblox_id,
                        "isVerified": False,
                    })

                    embed = discord.Embed(color=0x2E3136)
                    embed.title = f"<:LinkIcon:1044004006109904966> {roblox_user['name']}, let's get you verified!"
                    embed.description = f"<:ArrowRight:1035003246445596774> Go to our [ROBLOX game](https://www.roblox.com/games/11747455621/Verification)\n<:ArrowRight:1035003246445596774> Click on <:Resume:1035269012445216858>\n<:ArrowRight:1035003246445596774> Verify your ROBLOX account in the game.\n<:ArrowRight:1035003246445596774> Click **Done**!"
                    embed.set_footer(text=f'ROBLOX Verification provided by Emergency Response Management')
                    view = Verification(ctx.author.id)
                    await ctx.send(embed=embed, view=view)
                    await view.wait()
                    if view.value:
                        if view.value == "done":
                            new_data = await bot.verification.find_by_id(ctx.author.id)
                            print(new_data)
                            if 'isVerified' in new_data.keys():
                                if new_data['isVerified']:
                                    return await after_verified(roblox_user['id'])
                                else:
                                    await invis_embed(ctx,
                                                      'You have not verified using the verification game. Please retry.')
                                    return await run_pathway()
                            else:
                                await invis_embed(ctx,
                                                  'You have not verified using the verification game. Please retry.')
                                return await run_pathway()

            await run_pathway()


async def setup(bot):
    await bot.add_cog(ModerationSync(bot))

