import discord
from discord.ext import commands
from database.queries import delete_guild_settings
from utils.logger import log_discord, log_error

class GuildEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """
        Triggered when the bot is kicked, banned, or leaves a guild.
        Removes all configuration data to prevent errors on re-entry or stale data.
        """
        log_discord(f"Bot removed from guild: {guild.name} ({guild.id}). Cleaning up settings.")
        try:
            await delete_guild_settings(guild.id)
        except Exception as e:
            log_error(f"Failed to delete guild settings: {e}")
        
async def setup(bot: commands.Bot):
    await bot.add_cog(GuildEvents(bot))
