import discord
import jishaku
from discord.ext import commands
from jishaku.codeblocks import codeblock_converter, Codeblock
from jishaku.cog import STANDARD_FEATURES, OPTIONAL_FEATURES
from jishaku.features.baseclass import Feature

OWNER = 1165311055728226444
LOGGING_CHANNEL = 1084950208842039326


class CustomDebugCog(*OPTIONAL_FEATURES, *STANDARD_FEATURES):
    """
    Custom Jishaku Cog for command logging
    """

    @Feature.Command(parent="jsk", name="creator")
    async def jsk_creator(self, ctx: commands.Context):
        try:
            owner = await ctx.guild.fetch_member(OWNER)
        except discord.NotFound:
            owner = None

        if owner is None:
            return await ctx.send(
                f"The creator of {self.bot.user.mention} is <@{OWNER}>"
            )

        embed = discord.Embed(
            title=f"{owner.name}#{owner.discriminator}", color=0x2A2D31
        )
        embed.add_field(
            name=f"Owner of {self.bot.user.name}",
            value=f"{owner.mention}",
            inline=False,
        )
        embed.add_field(name="ID", value=f"{owner.id}", inline=False)
        embed.set_footer(
            text=f"{owner.name}#{owner.discriminator} is the owner of {self.bot.user.name}",
            icon_url=ctx.guild.icon,
        )
        embed.set_thumbnail(url=owner.display_avatar.url)
        await ctx.send(embed=embed)

    # async def cog_before_invoke(self, ctx: commands.Context):
    #     try:
    #         channel: discord.TextChannel = await self.bot.fetch_channel(LOGGING_CHANNEL)
    #     except (discord.NotFound, discord.Forbidden):
    #         pass
    #     else:
    #         selected_webhook = None
    #         try:
    #             for webhook in await channel.webhooks():
    #                 if webhook.name == f"{ctx.author.name}#{ctx.author.discriminator}":
    #                     selected_webhook = webhook
    #         except discord.Forbidden:
    #             return
    #
    #         if not selected_webhook:
    #             selected_webhook = await channel.create_webhook(
    #                 name=f"{ctx.author.name}#{ctx.author.discriminator}",
    #                 avatar=(await ctx.author.display_avatar.read()),
    #                 reason="Logs",
    #             )
    #
    #         embed = discord.Embed()
    #         if "`" in ctx.message.content:
    #             codeblock = codeblock_converter(
    #                 ctx.message.content[ctx.message.content.index("`") - 1 :]
    #             )
    #         else:
    #             codeblock = None
    #         if codeblock is not None:
    #             if ctx.guild:
    #                 embed.description = f"```\n{ctx.message.content[:ctx.message.content.index('`')-1]}```\n{codeblock.content}\n\n```\nServer Name: {ctx.guild.name}\nChannel Name: {ctx.channel.name}\nMember Count: {ctx.guild.member_count}\nOwner: {f'{ctx.guild.owner.name}#{ctx.guild.owner.discriminator}'}```"
    #             else:
    #                 embed.description = f"```\n{ctx.message.content[:ctx.message.content.index('`') - 1]}```\n{codeblock.content}"
    #         else:
    #             if ctx.guild:
    #                 embed.description = f"```\n{ctx.message.content}```\n\n```\nServer Name: {ctx.guild.name}\nChannel Name: {ctx.channel.name}\nMember Count: {ctx.guild.member_count}\nOwner: {f'{ctx.guild.owner.name}#{ctx.guild.owner.discriminator}'}```"
    #             else:
    #                 embed.description = f"```\n{ctx.message.content}```"
    #         embed.title = "Jishaku Logging"
    #         embed.set_author(
    #             name=f"{ctx.author.name}#{ctx.author.discriminator}",
    #             icon_url=ctx.author.display_avatar.url,
    #         )
    #         embed.set_footer(text="️️©️ ERM Systems - Jishaku Logging Systems")
    #         try:
    #             await selected_webhook.send(embed=embed)
    #         except ValueError:
    #             await selected_webhook.delete()
    #             selected_webhook = await channel.create_webhook(
    #                 name=f"{ctx.author.name}#{ctx.author.discriminator}",
    #                 avatar=(await ctx.author.display_avatar.read()),
    #                 reason="Logs",
    #             )
    #             await selected_webhook.send(embed=embed)


async def setup(bot):
    await bot.add_cog(CustomDebugCog(bot=bot))
