import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class VoiceState(BaseLogger):
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return
            
        if before.channel == after.channel:
            return # State update like mute/deaf, ignore for now to avoid spam
            
        guild = member.guild
        
        if before.channel is None and after.channel is not None:
            # Joined
            description = f"{member.mention} joined voice channel {after.channel.mention}"
            title = "Voice Join"
            color = discord.Color.green()
        elif before.channel is not None and after.channel is None:
            # Left
            description = f"{member.mention} left voice channel {before.channel.mention}"
            title = "Voice Leave"
            color = discord.Color.red()
        else:
            # Moved
            description = f"{member.mention} moved from {before.channel.mention} to {after.channel.mention}"
            title = "Voice Move"
            color = discord.Color.blue()
            
        embed = EmbedBuilder.build(
            title=title,
            description=description,
            color=color,
            author=member,
            footer=f"ID: {member.id}"
        )
        
        changes = []
        
        def diff(label, a, b):
            if a != b:
                changes.append(f"{label}: {a} -> {b}")
        
        diff("Server Muted", before.mute, after.mute)
        diff("Server Deafened", before.deaf, after.deaf)

        if not changes:
            return

        embed = EmbedBuilder.warning(
            title="Voice State Updated",
            description=f"Voice state changed for {member.mention}",
            fields=[
                ("Changes", "\n".join(changes), False)
            ]
        )

        await self.log_event(guild, embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceState(bot))
