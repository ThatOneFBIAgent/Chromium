#    Chromium - A more cleaner structure of Flurazide and logging system
#    (okay "cleaner" for the improved structure)
#    © 2024-2026  Iza Carlos (Aka Carlos E.)
#    Licensed under the GNU Affero General Public License v3.0

import discord
from discord.ext import commands
import os
import sys
import signal
import asyncio
import time
import contextlib
import aiohttp
from config import shared_config
from database.core import db
from utils.logger import get_logger
from utils.drive import drive_manager

log = get_logger()

class Chromium(commands.AutoShardedBot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.voice_states = True
        intents.presences = True # May or may not remove due to being obsolete/not used
        intents.emojis_and_stickers = True # Required for emoji updates
        intents.bans = True # Required for bans
        intents.guilds = True # Required for guild updates
        
        super().__init__(
            command_prefix="cr!", # Fallback, we mainly use slash commands
            intents=intents,
            help_command=None,
            shard_count=shared_config.SHARD_COUNT if shared_config.SHARD_COUNT > 1 else None
        )
        self.start_time = time.time()
        self._is_shutting_down = False
        self._ready_once = asyncio.Event()

    async def setup_hook(self):
        """
        Async setup hook to initialize DB and load extensions.
        """
        # Start shared http session early so it's available for extensions
        self.http_session = aiohttp.ClientSession()
        
        # Initialize event queue for rate-limited API calls
        from utils.rate_limiter import init_event_queue
        self.event_queue = init_event_queue(self)
        
        # Initialize Database
        await asyncio.sleep(5) # Give network some time to settle
        # Attempt to restore from Drive if available
        await db.restore_from_drive()
        await db.connect()
        
        # Load Logging Modules, Commands, and Services
        await self._load_extensions_from("logging_modules")
        await self._load_extensions_from("commands")
        await self._load_extensions_from("services")
        
        # Sync generic commands (global)
        try:
            log.info("Starting command tree sync...")
            synced = await asyncio.wait_for(self.tree.sync(), timeout=30.0)
            log.discord(f"Synced {len(synced)} command(s) globally.")
        except asyncio.TimeoutError:
            log.error("Command tree sync timed out after 30 seconds.")
        except Exception as e:
            log.error("Failed to sync commands", exc_info=e)

    async def _load_extensions_from(self, folder: str):
        if not os.path.exists(folder):
            os.makedirs(folder)
            return

        failed_extensions = []
        for filename in os.listdir(folder):
            if filename.endswith(".py") and not filename.startswith("__") and filename != "base.py":
                extension_name = f"{folder}.{filename[:-3]}"
                try:
                    await self.load_extension(extension_name)
                    log.info(f"Loaded extension: {extension_name}")
                except Exception as e:
                    failed_extensions.append(extension_name)
                    log.error(f"Failed to load extension {extension_name}", exc_info=e)

        if failed_extensions:
            log.error(f"Failed to load extensions: {failed_extensions}")
        else:
            log.discord("All extensions loaded successfully.")

    async def on_ready(self):
        # Only run once, even though each shard calls on_ready
        if not self._ready_once.is_set():
            total_shards = self.shard_count or 1
            log.network(f"Bot is online as {self.user} (ID: {self.user.id})")
            log.network(f"Connected to {len(self.guilds)} guilds across {total_shards} shard(s).")
            if shared_config.IS_RAILWAY:
                log.network("Environment: Railway Detected.")
            
            # Validate guild settings - restore any that were soft-deleted but bot is still in
            try:
                from database.queries import restore_settings_for_active_guilds, migrate_remove_automod_flag
                guild_ids = [g.id for g in self.guilds]
                restored = await restore_settings_for_active_guilds(guild_ids)
                if restored > 0:
                    log.database(f"Restored settings for {restored} guild(s) with stale deleted_at flags.")
                    
                # DB Migration: Remove AutoModUpdate flag
                await migrate_remove_automod_flag()
                
            except Exception as e:
                log.error("Failed to validate guild settings on startup", exc_info=e)
            
            # Global status set removed in favor of per-shard status in on_shard_ready
            
            self._ready_once.set()
        else:
            # Shard resumed event — bot reconnected
            log.network(f"[Shard {self.shard_id+1 or '?'}] resumed session in {time.time() - self.start_time:.2f} seconds.")

    async def close(self):
        # Note: Logic moved to graceful_shutdown primarily, this is just a super call wrapper now
        await super().close()

# Bot Instance
bot = Chromium()

@bot.event
async def on_shard_connect(shard_id):
    log.network(f"[Shard {shard_id+1}] connected successfully in {time.time() - bot.start_time:.2f} seconds.")

@bot.event
async def on_shard_ready(shard_id):
    guilds = [g for g in bot.guilds if g.shard_id == shard_id]
    log.network(f"[Shard {shard_id+1}] ready - handling {len(guilds)} guild(s).")
    
    # Set per-shard presence
    total_shards = bot.shard_count or 1
    activity = discord.Activity(
        type=discord.ActivityType.watching, 
        name=f"over {len(guilds)} guilds | Shard {shard_id+1}/{total_shards}"
    )
    # Ensure we set it for this specific shard
    await bot.change_presence(activity=activity, shard_id=shard_id)

@bot.event
async def on_shard_disconnect(shard_id):
    log.network(f"[Shard {shard_id+1}] disconnected - waiting for resume.")

@bot.event
async def on_shard_resumed(shard_id):
    log.network(f"[Shard {shard_id+1}] resumed connection.")

async def kill_all_tasks():
    current = asyncio.current_task()
    for task in asyncio.all_tasks():
        if task is current: continue
        task.cancel()
    await asyncio.sleep(1)

async def graceful_shutdown():
    log.info("Shutdown signal received - performing cleanup...")
    bot._is_shutting_down = True

    # Let ongoing tasks wrap up (simple sleep)
    await asyncio.sleep(1)

    if not shared_config.ENVIRONMENT == "production":
        log.info("Not running on production, skipping database backup.")
        return
    else:
        try:
            if os.path.exists(db.db_path):
                log.info("Uploading database backup...")

                # Read file content
                with open(db.db_path, 'rb') as f:
                    db_content = f.read()

                backup_name = "chromium_database_backup.sqlite"
                existing_id = await asyncio.to_thread(drive_manager.find_file, backup_name)

                if existing_id:
                    await asyncio.to_thread(drive_manager.update_file, existing_id, db_content)
                else:
                    await asyncio.to_thread(drive_manager.upload_file, backup_name, db_content)

                log.info("Database backup completed.")
        except Exception as e:
            log.error("Failed to perform final database backup", exc_info=e)

    # Close DB
    await db.close()
    
    # Stop event queue processing
    if hasattr(bot, 'event_queue') and bot.event_queue:
        bot.event_queue.stop_processing()
    
    # Close shared http session
    if bot.http_session and not bot.http_session.closed:
        await bot.http_session.close()

    # Close bot
    await kill_all_tasks()
    with contextlib.suppress(Exception):
        await bot.close()

    log.info("Shutdown complete. Chromium signing off.")
    sys.exit(0)

async def main():
    async with bot:
        # Register signal handlers
        shutdown_signal = asyncio.get_event_loop().create_future()

        def _signal_handler():
            if not shutdown_signal.done():
                shutdown_signal.set_result(True)

        loop = asyncio.get_event_loop()
        # Windows compatibility for signal handling
        if sys.platform != 'win32':
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(sig, _signal_handler)
                except Exception as e:
                    log.error(f"Failed to register signal handler for {sig!r}: {e}")
        else:
            # Windows doesn't support add_signal_handler for everything, 
            # but asyncio.run/main loop usually handles Ctrl+C as KeyboardInterrupt.
            # We will rely on KeyboardInterrupt catch below for Windows local dev.
            pass

        bot_task = asyncio.create_task(bot.start(shared_config.DISCORD_TOKEN))

        try:
            # Wait for shutdown signal (manual set or future) or KeyboardInterrupt
            if sys.platform != 'win32':
                await shutdown_signal
            else:
                # On Windows, we just wait on the bot task until it's cancelled or finishes
                # But actually, we want to catch Ctrl+C.
                await bot_task
        except asyncio.CancelledError:
            log.info("Main task cancelled; initiating cleanup.")
        except KeyboardInterrupt:
            log.info("KeyboardInterrupt received; initiating cleanup.")
        finally:
            if not bot_task.done():
                bot_task.cancel()
                try:
                    await bot_task
                except asyncio.CancelledError:
                    pass
            
            try:
                await graceful_shutdown()
            except Exception as e:
                log.error(f"Error during graceful shutdown: {e}", exc_info=e)
                sys.exit(1)

if __name__ == "__main__":
    try:
        if not shared_config.DISCORD_TOKEN:
             log.error("No DISCORD_TOKEN found in environment config.")
             sys.exit(1)
             
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        # We need a fallback logger here if log isn't defined, but it is global
        # im not gonna be nesting try clauses nuh uh
        # please ignore the comment above i was not aware of the guard clauses technique - sincerely Iza
        log.error("Fatal crash in main", exc_info=e)
        sys.exit(1)
