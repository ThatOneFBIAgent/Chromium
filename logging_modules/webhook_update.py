import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class WebhookUpdate(BaseLogger):
    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.TextChannel):
        embed = EmbedBuilder.warning(
            title="Webhooks Updated",
            description=f"Webhooks changed in {channel.mention}"
        )

        await self.log_event(channel.guild, embed, suspicious=True)

async def setup(bot):
    await bot.add_cog(WebhookUpdate(bot))
