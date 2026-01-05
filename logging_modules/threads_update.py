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
            description=f"Thread `{thread.name}` deleted in {thread.parent.mention if thread.parent else 'Unknown'}",
            fields=[
                ("Auto Archive", f"{thread.auto_archive_duration} minutes", True)
            ]
        )
        await self.log_event(thread.guild, embed)

    @commands.Cog.listener()
    async def on_thread_remove(self, thread):
        embed = EmbedBuilder.info(
            title="Thread Removed",
            description=f"Thread `{thread.name}` removed in {thread.parent.mention if thread.parent else 'Unknown'}",
            fields=[
                ("Auto Archive", f"{thread.auto_archive_duration} minutes", True)
            ]
        )
        await self.log_event(thread.guild, embed)

    @commands.Cog.listener()
    async def on_thread_update(self, before, after):
        if before.name != after.name:
            embed = EmbedBuilder.info(
                title="Thread Name Changed",
                description=f"Thread `{before.name}` renamed to `{after.name}` in {after.parent.mention if after.parent else 'Unknown'}",
                fields=[
                    ("Auto Archive", f"{after.auto_archive_duration} minutes", True)
                ]
            )
            await self.log_event(after.guild, embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ThreadsUpdate(bot))