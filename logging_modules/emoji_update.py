import discord
from discord.ext import commands
from .base import BaseLogger
from utils.embed_builder import EmbedBuilder

class EmojiUpdate(BaseLogger):
    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: discord.Guild, before: list[discord.Emoji], after: list[discord.Emoji]):
        # Convert to sets for easy comparison
        before_ids = set(e.id for e in before)
        after_ids = set(e.id for e in after)
        
        added = [e for e in after if e.id not in before_ids]
        removed = [e for e in before if e.id not in after_ids]
        # Renamed logic is complex because ID matches but name differs, skipping for brevity/simplicity unless critical
        
        if not added and not removed:
            return

        db_embeds = []
        
        # Log Added
        for emoji in added:
            embed = EmbedBuilder.success(
                title="Emoji Added",
                description=f"Emoji {emoji} (`{emoji.name}`) was added.",
                fields=[("ID", emoji.id, True), ("Animated", str(emoji.animated), True)]
            )
            if emoji.is_custom_emoji():
                 embed.set_thumbnail(url=emoji.url)
            await self.log_event(guild, embed)
            
        # Log Removed
        for emoji in removed:
             embed = EmbedBuilder.error(
                title="Emoji Deleted",
                description=f"Emoji `{emoji.name}` was deleted.",
                fields=[("ID", emoji.id, True)]
            )
             if emoji.is_custom_emoji():
                embed.set_thumbnail(url=emoji.url)
             await self.log_event(guild, embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(EmojiUpdate(bot))
