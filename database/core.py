import aiosqlite
import os
from utils.logger import get_logger

# Initialize logger
log = get_logger()

DB_PATH = "chromium_database.sqlite"

class DatabaseManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.connection = None

    async def connect(self):
        try:
            self.connection = await aiosqlite.connect(self.db_path)
            # Enable foreign keys
            await self.connection.execute("PRAGMA foreign_keys = ON")
            log.database(f"Connected to SQLite database at {self.db_path}")
            await self.init_schema()
        except Exception as e:
            log.error("Failed to connect to database", exc_info=e)
            raise

    async def restore_from_drive(self):
        """Attempts to support restoring database from Google Drive on startup."""
        from utils.drive import drive_manager # Lazy import to avoid circular dependency issues if any
        
        # Ensure service is ready (retry a few times if needed due to network lag)
        import asyncio
        for i in range(3):
            if drive_manager.service:
                break
            # Try to init if missing
            drive_manager.initialize_service()
            if not drive_manager.service:
                log.database(f"Drive service not ready, retrying in 2s... ({i+1}/3)")
                await asyncio.sleep(2)
        
        if not drive_manager.service:
            log.database("Drive restore skipped (No service after retries).")
            return
            
        filename = "chromium_database_backup.sqlite"
        try:
            file_id = drive_manager.find_file(filename)
            if not file_id:
                log.database(f"No remote backup found to restore: '{filename}'")
                drive_manager.debug_list_files()
                return
                
            log.database(f"Found remote backup ({file_id}). Downloading...")
            content = drive_manager.download_file(file_id)
            
            if content:
                # We assume no connection is active or we are pre-connect
                # Just overwrite the file
                with open(self.db_path, 'wb') as f:
                    f.write(content)
                log.database("Database restored from Drive backup successfully.")
            else:
                log.error("Failed to download backup content.")
                
        except Exception as e:
            log.error("Failed to restore database from Drive context", exc_info=e)

    async def init_schema(self):
        if not self.connection:
            return
            
        queries = [
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                log_channel_id INTEGER, -- General/Server logs
                message_log_id INTEGER, -- Message logs
                member_log_id INTEGER, -- Member/User logs
                suspicious_channel_id INTEGER, -- Optional override
                enabled_modules TEXT DEFAULT '{}', -- JSON string
                deleted_at DATETIME DEFAULT NULL -- Soft delete timestamp
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                module_name TEXT NOT NULL,
                content TEXT, -- JSON payload or text summary
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_logs_guild ON logs(guild_id);
            """
        ]
        
        try:
            for q in queries:
                await self.connection.execute(q)
            await self.connection.commit()
            log.database("Database schema initialization complete.")
        except Exception as e:
            log.error("Failed to initialize database schema", exc_info=e)
            raise

    async def close(self):
        if self.connection:
            await self.connection.close()
            log.database("Database connection closed.")

# Global DB instance
db = DatabaseManager()
