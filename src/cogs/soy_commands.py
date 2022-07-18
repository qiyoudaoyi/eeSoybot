from datetime import datetime
import discord
import asyncio

from discord import app_commands
from discord.ext import commands
from discord.app_commands import (
    guilds, describe, rename, choices, guild_only,
    Choice, Range,
    AppCommandError, CommandOnCooldown
)
from commands import Poll
from commands import starburst_stream
from utils import ANSI
from utils import Config
from utils import get_lumberjack


class SoyCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_member: discord.Member | discord.User | None = None

        bot.tree.on_error = self.on_app_command_error
        bot.tree.add_command(app_commands.ContextMenu(
            name='稽查頭貼',
            callback=self.avatar_ctx_menu,
        ))

        self.logger = get_lumberjack('SoyCommands', ANSI.BrightGreen)
        self.logger.info('initialized')

    # Starburst Stream slash command
    @app_commands.command(name="starburst", description='C8763')
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.channel.id, i.user.id))
    @guilds(*Config.guild_ids)
    async def starburst(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(await starburst_stream())

    # Poll slash command
    @app_commands.command(name="poll", description='預設設定：公開 單選 20秒')
    # @describe(anonymity='公開 or 匿名', format='單選 or 複選', duration='投票持續秒數')
    @rename(anonymity='計票方式', format='投票形式', duration='投票持續秒數')
    @choices(
        anonymity=[
            Choice(name='公開', value='public'),
            Choice(name='匿名', value='anonymous'),
        ],
        format=[
            Choice(name='單選', value='single'),
            Choice(name='複選', value='multiple'),
        ]
    )
    @guilds(*Config.guild_ids)
    @guild_only()
    async def poll_coro(
        self,
        interaction: discord.Interaction,
        anonymity: Choice[str] = 'public',
        format: Choice[str] = 'single',
        duration: Range[float, 10, 180] = 20.0
    ) -> None:
        settings = {
            'chat_interaction': interaction,
            'is_public': anonymity == 'public',
            'is_single': format == 'single',
            'duration': duration
        }
        poll = Poll(**settings)
        await poll.prompt_details()
        if await poll.modal.wait():
            return
        await poll.start()
        await asyncio.sleep(3)
        await poll.end()

    # manually prefixed sync commands
    @commands.command(name="sync")
    async def sync(self, ctx: commands.Context) -> None:
        await ctx.send('commands syncing...')
        await self.bot.tree.sync(guild=ctx.guild)
        await ctx.send('commands synced.')

    async def avatar_coro(self, interaction: discord.Interaction, target: discord.Member):
        description = f'**{interaction.user.display_name}** 稽查了 **{target.display_name}** 的頭貼'
        if interaction.user.id == target.id:
            description = f'**{interaction.user.display_name}** 稽查了自己的頭貼'

        color = target.color

        embed = discord.Embed(
            color=color,
            description=description,
            type='image',
            # url='user.display_avatar.url',
            timestamp=datetime.now(),
        )
        embed.set_image(url=target.display_avatar.url)
        await interaction.response.send_message(f'{target.mention} 的頭貼是 **伊織萌** {self.bot.get_emoji(780263339808522280)}', embed=embed)

    @app_commands.command(name="avatar", description='稽查頭貼')
    @rename(target='稽查對象')
    @guilds(*Config.guild_ids)
    @guild_only()
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.channel.id, i.user.id))
    async def avatar_slash(self, interaction: discord.Interaction, target: discord.Member) -> None:
        await self.avatar_coro(interaction, target)

    @guilds(*Config.guild_ids)
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.channel.id, i.user.id))
    async def avatar_ctx_menu(self, interaction: discord.Interaction, user: discord.Member):
        if user.id == self.bot.user.id:
            await interaction.response.send_message(f'不要ㄐ查豆漿ㄐㄐ人的頭貼好ㄇ', ephemeral=True)
            return
        await self.avatar_coro(interaction, target=user)

    async def on_app_command_error(self, interaction: discord.Interaction, error: AppCommandError):
        if isinstance(error, CommandOnCooldown):
            msg = f'冷卻中...\n請稍後**{str(round(error.retry_after, 2)).rstrip("0").rstrip(".")}**秒再試'
            await interaction.response.send_message(msg, ephemeral=True)
