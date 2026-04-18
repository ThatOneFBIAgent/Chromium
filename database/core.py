import aiosqlite
import os
import asyncio
from utils.logger import get_logger

# Initialize logger
log = get_logger()

DB_PATH = "chromium_database.sqlite"

class DatabaseManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.connection = None
        self._log_counter = 0
        self._flush_task = None
        self._log_queue = asyncio.Queue()
        self._log_worker_task = None

    async def connect(self):
        try:
            self.connection = await aiosqlite.connect(self.db_path)
            # Enable foreign keys
            await self.connection.execute("PRAGMA foreign_keys = ON")
            log.database(f"Connected to SQLite database at {self.db_path}")
            await self.init_schema()
            
            # Start background tasks
            import asyncio
            if self._flush_task is None:
                self._flush_task = asyncio.create_task(self._periodic_flush())
            if self._log_worker_task is None:
                self._log_worker_task = asyncio.create_task(self._log_worker())
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
            await asyncio.to_thread(drive_manager.initialize_service)
            if not drive_manager.service:
                log.database(f"Drive service not ready, retrying in 2s... ({i+1}/3)")
                await asyncio.sleep(2)
        
        if not drive_manager.service:
            log.database("Drive restore skipped (No service after retries).")
            return
            
        filename = "chromium_database_backup.sqlite"
        try:
            file_id = await asyncio.to_thread(drive_manager.find_file, filename)
            if not file_id:
                log.database(f"No remote backup found to restore: '{filename}'")
                await asyncio.to_thread(drive_manager.debug_list_files)
                return
                
            log.database(f"Found remote backup ({file_id}). Downloading...")
            content = await asyncio.to_thread(drive_manager.download_file, file_id)
            
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
                log_webhook_url TEXT, -- Webhook for general logs
                message_webhook_url TEXT, -- Webhook for message logs
                member_webhook_url TEXT, -- Webhook for member logs
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
            """,
            """
            CREATE TABLE IF NOT EXISTS server_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                list_type TEXT NOT NULL, -- 'blacklist' or 'whitelist'
                entity_type TEXT NOT NULL, -- 'role', 'user', 'channel'
                entity_id INTEGER NOT NULL,
                entity_name TEXT, -- Stored for fuzzy matching in DB
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE,
                UNIQUE(guild_id, list_type, entity_id)
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_lists_guild ON server_lists(guild_id, list_type);
            """,
            """
            CREATE TABLE IF NOT EXISTS global_stats (
                stat_key TEXT PRIMARY KEY,
                stat_value INTEGER DEFAULT 0
            );
            """
        ]
        
        try:
            for q in queries:
                await self.connection.execute(q)
            
            # Migration for added columns
            cursor = await self.connection.execute("PRAGMA table_info(guild_settings)")
            columns = [row[1] for row in await cursor.fetchall()]
            
            if 'log_webhook_url' not in columns:
                log.database("Migrating guild_settings table to include webhook columns...")
                await self.connection.execute("ALTER TABLE guild_settings ADD COLUMN log_webhook_url TEXT")
                await self.connection.execute("ALTER TABLE guild_settings ADD COLUMN message_webhook_url TEXT")
                await self.connection.execute("ALTER TABLE guild_settings ADD COLUMN member_webhook_url TEXT")
            
            # Seed total_logs_sent if missing
            res = await self.connection.execute("SELECT 1 FROM global_stats WHERE stat_key = 'total_logs_sent'")
            if not await res.fetchone():
                log.database("Seeding total_logs_sent statistic from current logs table...")
                logs_res = await self.connection.execute("SELECT COUNT(*) FROM logs")
                current_count = (await logs_res.fetchone())[0]
                await self.connection.execute(
                    "INSERT INTO global_stats (stat_key, stat_value) VALUES ('total_logs_sent', ?)",
                    (current_count,)
                )

            await self.connection.commit()
            log.database("Database schema initialization complete.")
        except Exception as e:
            log.error("Failed to initialize database schema", exc_info=e)
            raise

    async def close(self):
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
        
        # Stop worker and wait for queue
        if self._log_worker_task:
            # We don't cancel immediately, we want to drain if possible
            # But during shutdown, we might just want to force it
            if not self._log_queue.empty():
                log.database(f"Draining {self._log_queue.qsize()} logs before closing...")
                # Allow a small window to drain
                try:
                    await asyncio.wait_for(self._log_queue.join(), timeout=5.0)
                except asyncio.TimeoutError:
                    log.warning("Timeout draining log queue, some logs may be lost.")
            
            self._log_worker_task.cancel()
            try:
                await self._log_worker_task
            except asyncio.CancelledError:
                pass
            self._log_worker_task = None
            
        # Final flush
        await self.flush_stats()
        
        if self.connection:
            await self.connection.close()
            log.database("Database connection closed.")

    async def _periodic_flush(self):
        """Background task to flush statistics to the database periodically."""
        import asyncio
        while True:
            try:
                await asyncio.sleep(60) # Flush every 60 seconds
                await self.flush_stats()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in periodic stats flush: {e}")

    async def flush_stats(self):
        """Flushes in-memory counters to the database."""
        if self._log_counter <= 0 or not self.connection:
            return

        count_to_add = self._log_counter
        self._log_counter = 0
        
        try:
            await self.connection.execute("""
                INSERT INTO global_stats (stat_key, stat_value) 
                VALUES ('total_logs_sent', ?) 
                ON CONFLICT(stat_key) DO UPDATE SET stat_value = stat_value + excluded.stat_value
            """, (count_to_add,))
            await self.connection.commit()
            log.trace(f"Flushed {count_to_add} log(s) to historical counter.")
        except Exception as e:
            # Restore the counter if it failed
            self._log_counter += count_to_add
            log.error(f"Failed to flush log counter: {e}")

    def increment_log_count(self):
        """Increments the in-memory log counter."""
        self._log_counter += 1

    def queue_log(self, guild_id: int, module_name: str, content: str):
        """Queues a log entry to be written in the next batch."""
        self._log_queue.put_nowait((guild_id, module_name, content))
        # We still increment the counter here
        self.increment_log_count()

    async def _log_worker(self):
        """Background task that writes logs in batches."""
        import asyncio
        while True:
            try:
                # Wait for at least one log
                batch = []
                item = await self._log_queue.get()
                batch.append(item)
                
                # Siphon up more if available
                while not self._log_queue.empty() and len(batch) < 100:
                    batch.append(self._log_queue.get_nowait())
                
                await self._write_log_batch(batch)
                
                # Mark as done
                for _ in range(len(batch)):
                    self._log_queue.task_done()
                    
                # Short break to allow other tasks to run if we are slammed
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in log worker: {e}")
                await asyncio.sleep(1) # Backoff on error

    async def _write_log_batch(self, batch):
        """Writes a batch of logs to the database in a single transaction."""
        if not self.connection or not batch:
            return
            
        try:
            # Insert logs
            await self.connection.executemany(
                "INSERT INTO logs (guild_id, module_name, content) VALUES (?, ?, ?)",
                batch
            )
            
            # Get unique guild IDs to trim their logs
            guild_ids = {item[0] for item in batch}
            
            # Trim logs for each guild
            # NOTE: Doing this for every batch might still be excessive if the same guild logs 100 times.
            # But it's better than doing it for EVERY single log.
            for guild_id in guild_ids:
                 await self.connection.execute("""
                    DELETE FROM logs 
                    WHERE guild_id = ? 
                    AND id NOT IN (
                        SELECT id FROM logs 
                        WHERE guild_id = ? 
                        ORDER BY id DESC 
                        LIMIT 50
                    )
                """, (guild_id, guild_id))
            
            await self.connection.commit()
        except Exception as e:
            log.error(f"Failed to write log batch: {e}")

# Global DB instance
db = DatabaseManager()
