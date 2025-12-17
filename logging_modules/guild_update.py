import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class GuildUpdate(BaseLogger):
    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        changes = []
        fields = []
        
        if before.name != after.name:
            changes.append(f"Name changed")
            fields.append(("Before", before.name, True))
            fields.append(("After", after.name, True))
            
        if before.icon != after.icon:
            changes.append("Server Icon changed")
            # We can't easily show old icon unless we cached it or rely on CDN link validity
            
        if before.owner != after.owner:
            changes.append(f"Owner transferred: {before.owner.mention} -> {after.owner.mention}")
            
        if not changes:
            return

        embed = EmbedBuilder.warning(
            title="Server Updated",
            description="\n".join(changes),
            footer=f"Guild ID: {after.id}",
            fields=fields
        )
        
        await self.log_event(after, embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(GuildUpdate(bot))
