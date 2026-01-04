import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class VoiceState(BaseLogger):
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        if member.bot:
            return

        if not await self.should_log(member.guild, user=member):
            return

        guild = member.guild

        # Channel join / leave / move
        if before.channel != after.channel:

            if before.channel is None and after.channel is not None:
                title = "Voice Join"
                description = f"{member.mention} joined {after.channel.mention}"

            elif before.channel is not None and after.channel is None:
                title = "Voice Leave"
                description = f"{member.mention} left {before.channel.mention}"

            else:
                title = "Voice Move"
                description = (
                    f"{member.mention} moved from "
                    f"{before.channel.mention} to {after.channel.mention}"
                )

            embed = EmbedBuilder.build(
                title=title,
                description=description,
                footer=f"ID: {member.id}",
                author=member
            )

            await self.log_event(guild, embed)

        # Voice flag changes (server muted/deafened)
        changes = []

        def diff(label, a, b):
            if a != b:
                changes.append(f"{label}: {a} -> {b}")

        diff("Server Muted", before.mute, after.mute)
        diff("Server Deafened", before.deaf, after.deaf)

        if changes:
            embed = EmbedBuilder.warning(
                title="Voice State Updated",
                description=f"Voice state changed for {member.mention}",
                fields=[("Changes", "\n".join(changes), False)]
            )

            await self.log_event(guild, embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceState(bot))
