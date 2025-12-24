import discord
from discord.ext import commands
import os
import sys
import signal
import asyncio
from config import shared_config
from database.core import db
from utils.logger import logger, log_network, log_discord, log_error

class Chromium(commands.AutoShardedBot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.voice_states = True
        intents.presences = True
        intents.emojis_and_stickers = True # Required for emoji updates
        intents.bans = True # Required for bans
        
        super().__init__(
            command_prefix="cr!", # Fallback, we mainly use slash commands
            intents=intents,
            help_command=None,
            shard_count=shared_config.SHARD_COUNT if shared_config.SHARD_COUNT > 1 else None
        )

    async def setup_hook(self):
        """
        Async setup hook to initialize DB and load extensions.
        """
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
            synced = await self.tree.sync()
            log_discord(f"Synced {len(synced)} command(s) globally.")
        except Exception as e:
            log_error("Failed to sync commands", exc_info=e)

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
                    logger.info(f"Loaded extension: {extension_name}")
                except Exception as e:
                    failed_extensions.append(extension_name)
                    log_error(f"Failed to load extension {extension_name}", exc_info=e)

        if failed_extensions:
            log_error(f"Failed to load extensions: {failed_extensions}")
        else:
            log_discord("All extensions loaded successfully.")

    async def on_ready(self):
        log_network(f"Logged in as {self.user} (ID: {self.user.id})")
        log_network(f"Shards: {self.shard_count}")
        if shared_config.IS_RAILWAY:
            log_network("Creating connection... Detected Railway Environment.")
            
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name=f"over {len(self.guilds)} guilds | Shard {self.shard_id or 0}"
        ))
        
    async def close(self):
        await db.close()
        await super().close()

# Bot Instance
bot = Chromium()

if __name__ == "__main__":
    try:
        if not shared_config.DISCORD_TOKEN:
            log_error("No DISCORD_TOKEN found in environment config.")
        else:
            bot.run(shared_config.DISCORD_TOKEN, log_handler=None) 
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Shutting down.")
        # bot.run already handles cleanup, but we can ensure DB close here if needed
        bot.close()
        pass
    except Exception as e:
        log_error("Fatal error starting bot", exc_info=e)
    finally:
        pass
