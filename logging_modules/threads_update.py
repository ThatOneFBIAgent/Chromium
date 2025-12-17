import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class ThreadsUpdate(BaseLogger):
    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        embed = EmbedBuilder.info(
            title="Thread Created",
            description=f"Thread `{thread.name}` created in {thread.parent.mention}",
            fields=[
                ("Auto Archive", f"{thread.auto_archive_duration} minutes", True)
            ]
        )
        await self.log_event(thread.guild, embed)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread):
        embed = EmbedBuilder.info(
            title="Thread Deleted",
            description=f"Thread `{thread.name}` deleted in {thread.parent.mention}",
            fields=[
                ("Auto Archive", f"{thread.auto_archive_duration} minutes", True)
            ]
        )
        await self.log_event(thread.guild, embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ThreadsUpdate(bot))