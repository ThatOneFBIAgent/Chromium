import asyncio
from discord.ext import commands, tasks
from database.core import db
from utils.logger import get_logger

log = get_logger()

class CleanupService(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cleanup_task.start()

    def cog_unload(self):
        self.cleanup_task.cancel()

    @tasks.loop(hours=24)
    async def cleanup_task(self):
        """
        Runs every 24 hours to delete soft-deleted records older than 60 days.
        """
        if not db.connection:
            return

        try:
            # SQLite modifier for -60 days
            threshold_query = "datetime('now', '-60 days')"
            
            # Select IDs for logging purposes (optional, but good for tracking)
            # Or just delete directly.
            
            # Delete settings first (Logs cascade delete if we had ON DELETE CASCADE, 
            # but our hard_delete helper handles it manually.
            # However, since we are doing bulk SQL, let's trust a direct SQL DELETE for efficiency
            # IF foreign keys are enforcing it. 
            # core.py HAS "FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE"
            # So deleting guild_settings is enough!
            # goodie good schizophrenia
            
            cursor = await db.connection.execute(f"""
                DELETE FROM guild_settings 
                WHERE deleted_at IS NOT NULL 
                AND deleted_at < {threshold_query}
            """)
            
            # Note: We need to commit
            await db.connection.commit()
            
            if cursor.rowcount > 0:
                log.database(f"Cleanup Task: Permanently removed {cursor.rowcount} expired guild configurations.")
                
        except Exception as e:
            log.error("Failed to run cleanup task", exc_info=e)

    @cleanup_task.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(CleanupService(bot))
