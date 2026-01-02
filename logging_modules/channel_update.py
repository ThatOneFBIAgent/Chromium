import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class ChannelUpdate(BaseLogger):
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        if not await self.should_log(channel.guild, channel=channel):
            return    
        
        embed = EmbedBuilder.success(
            title="Channel Created",
            description=f"Channel {channel.mention} (`{channel.name}`) was created."
        )
        await self.log_event(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if not await self.should_log(channel.guild, channel=channel):
            return    
        
        embed = EmbedBuilder.error(
            title="Channel Deleted",
            description=f"Channel `{channel.name}` was deleted."
        )
        await self.log_event(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        if not await self.should_log(before.guild, channel=before):
            return    
        
        if before.name == after.name:
            return 
            
        embed = EmbedBuilder.warning(
            title="Channel Updated",
            description=f"Channel {after.mention} was updated.",
            fields=[
                ("Before", before.name, True),
                ("After", after.name, True)
            ]
        )
        await self.log_event(after.guild, embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ChannelUpdate(bot))
