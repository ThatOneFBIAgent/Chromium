import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class ChannelPermissionUpdate(BaseLogger):
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if before.overwrites == after.overwrites:
            return

        diffs = []

        for target, perms in after.overwrites.items():
            before_perms = before.overwrites.get(target)
            if before_perms != perms:
                diffs.append(f"{target}: {before_perms} -> {perms}")

        if not diffs:
            return

        embed = EmbedBuilder.warning(
            title="Channel Permissions Updated",
            description=f"Permissions changed in {after.mention}",
            fields=[
                ("Overwrites", "\n".join(diffs[:5]), False)
            ]
        )

        await self.log_event(after.guild, embed)

async def setup(bot):
    await bot.add_cog(ChannelPermissionUpdate(bot))
