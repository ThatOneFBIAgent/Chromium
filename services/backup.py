import discord
from discord.ext import tasks, commands
import asyncio
import datetime
from config import shared_config
from utils.drive import drive_manager
from utils.logger import get_logger
import shutil
import os

log = get_logger()

DB_PATH = "chromium_database.sqlite"

class BackupService(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Start the backup loop if Drive is configured
        if shared_config.DRIVE_CREDS_B64 and shared_config.DRIVE_FOLDER_ID:
            self.backup_loop.start()
            log.info("Automated Backup Service started.")
        else:
            log.warning("Google Drive credentials or Folder ID missing. Automated backups disabled.")

    def cog_unload(self):
        self.backup_loop.cancel()

    @tasks.loop(hours=2)
    async def backup_loop(self):
        """
        Runs every 2 hours. Backs up the SQLite database to Google Drive.
        """
        await self.perform_backup()

    @backup_loop.before_loop
    async def before_backup_loop(self):
        await self.bot.wait_until_ready()
        # Wait 2 hours on startup so we skip the immediate execution (since we just restored or booted)
        # The first backup will happen 2 hours after boot.
        await asyncio.sleep(7200)

    async def perform_backup(self):
        log.info("Starting automated database backup...")
        try:
            # Fixed filename for rotation (overwrite strategy)
            backup_filename = "chromium_database_backup.sqlite"
            
            if not os.path.exists(DB_PATH):
                log.error("Database file not found for backup.")
                return

            # Read file in binary mode
            try:
                with open(DB_PATH, 'rb') as f:
                    content_bytes = f.read()
            except Exception as e:
                log.error("Failed to read database file for backup", exc_info=e)
                return
            
            # Check if exists
            existing_id = drive_manager.find_file(backup_filename)
            
            if existing_id:
                link = drive_manager.update_file(existing_id, content_bytes, mimetype='application/x-sqlite3')
                action = "Updated"
            else:
                link = drive_manager.upload_file(backup_filename, content_bytes, mimetype='application/x-sqlite3')
                action = "Uploaded"
            
            if link:
                log.info(f"Backup successful ({action}): {link}")
            else:
                log.error("Backup upload failed.")

        except Exception as e:
            log.error("Automated backup failed", exc_info=e)



async def setup(bot: commands.Bot):
    await bot.add_cog(BackupService(bot))
