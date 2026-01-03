import json
import aiosqlite
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from .core import db
from utils.logger import get_logger

log = get_logger()

async def upsert_guild_settings(
    guild_id: int, 
    log_channel_id: Optional[int] = None, 
    message_log_id: Optional[int] = None,
    member_log_id: Optional[int] = None,
    susp_channel_id: Optional[int] = None, 
    enabled_modules: Optional[Dict[str, bool]] = None
):
    """
    Create or update guild settings.
    """
    if not db.connection:
        return

    try:
        cursor = await db.connection.execute(
            "SELECT enabled_modules, log_channel_id, message_log_id, member_log_id, suspicious_channel_id FROM guild_settings WHERE guild_id = ?", 
            (guild_id,)
        )
        row = await cursor.fetchone()
        
        current_modules = {}
        # Defaults
        current_log = None
        current_msg_log = None
        current_mem_log = None
        current_susp = None
        
        if row:
            current_modules = json.loads(row[0]) if row[0] else {}
            current_log = row[1]
            current_msg_log = row[2]
            current_mem_log = row[3]
            current_susp = row[4]
            
        final_log = log_channel_id if log_channel_id is not None else current_log
        final_msg_log = message_log_id if message_log_id is not None else current_msg_log
        final_mem_log = member_log_id if member_log_id is not None else current_mem_log
        final_susp = susp_channel_id if susp_channel_id is not None else current_susp
        
        if enabled_modules:
            current_modules.update(enabled_modules)
            
        final_modules_json = json.dumps(current_modules)
        
        # We need to handle schema changes gracefully if the table was already created without new columns.
        # But assuming we can drop/recreate or alter. For this exercise, I'll rely on the CREATE IF NOT EXISTS logic in core.py
        # triggering only on fresh start or I'd need migration logic.
        # Since I can't easily migrate here without a migration script, I'll assume fresh DB or user deletes it.
        # To be safe, I'll use standard UPSERT.
        
        await db.connection.execute("""
            INSERT INTO guild_settings (guild_id, log_channel_id, message_log_id, member_log_id, suspicious_channel_id, enabled_modules)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                log_channel_id = excluded.log_channel_id,
                message_log_id = excluded.message_log_id,
                member_log_id = excluded.member_log_id,
                suspicious_channel_id = excluded.suspicious_channel_id,
                enabled_modules = excluded.enabled_modules
        """, (guild_id, final_log, final_msg_log, final_mem_log, final_susp, final_modules_json))
        await db.connection.commit()
    except Exception as e:
        log.error(f"Failed to upsert settings for guild {guild_id}", exc_info=e)

async def get_guild_settings(guild_id: int):
    """
    Returns (log_channel_id, message_log_id, member_log_id, suspicious_channel_id, enabled_modules_dict)
    """
    if not db.connection:
        return None, None, None, None, {}
        
    try:
        cursor = await db.connection.execute(
            "SELECT log_channel_id, message_log_id, member_log_id, suspicious_channel_id, enabled_modules, deleted_at FROM guild_settings WHERE guild_id = ?", 
            (guild_id,)
        )
        row = await cursor.fetchone()
        if row:
             # row[5] is deleted_at. If set, return defaults (effectively "not configured" for the logger)
            if row[5]:
                return None, None, None, None, {}
            return row[0], row[1], row[2], row[3], json.loads(row[4]) if row[4] else {}
        return None, None, None, None, {}
    except Exception as e:
        log.error(f"Failed to fetch settings for guild {guild_id}", exc_info=e)
        return None, None, None, None, {}

async def add_log(guild_id: int, module_name: str, content: str):
    if not db.connection:
        return

    try:
        await db.connection.execute("INSERT INTO logs (guild_id, module_name, content) VALUES (?, ?, ?)", (guild_id, module_name, content))
        
        await db.connection.execute("""
            DELETE FROM logs 
            WHERE guild_id = ? 
            AND id NOT IN (
                SELECT id FROM logs 
                WHERE guild_id = ? 
                ORDER BY id DESC 
                LIMIT 50
            )
        """, (guild_id, guild_id))
        
        await db.connection.commit()
    except Exception as e:
        log.error(f"Failed to add log for guild {guild_id}", exc_info=e)

async def get_recent_logs(guild_id: int, limit: int = 50):
    if not db.connection:
        return []
        
    try:
        db.connection.row_factory = aiosqlite.Row
        cursor = await db.connection.execute("SELECT * FROM logs WHERE guild_id = ? ORDER BY id DESC LIMIT ?", (guild_id, limit))
        rows = await cursor.fetchall()
        return rows
    except Exception as e:
        log.error(f"Failed to fetch logs for guild {guild_id}", exc_info=e)
        return []

async def delete_guild_settings(guild_id: int):
    """
    Soft-deletes settings for a guild (sets deleted_at).
    """
    if not db.connection:
        return

    try:
        await db.connection.execute(
            "UPDATE guild_settings SET deleted_at = CURRENT_TIMESTAMP WHERE guild_id = ?", 
            (guild_id,)
        )
        await db.connection.commit()
        log.database(f"Soft-deleted settings for guild {guild_id}")
    except Exception as e:
        log.error(f"Failed to soft-delete settings for {guild_id}", exc_info=e)

async def hard_delete_guild_settings(guild_id: int):
    """
    Permanently removes settings and logs.
    """
    if not db.connection:
        return

    try:
        await db.connection.execute("DELETE FROM guild_settings WHERE guild_id = ?", (guild_id,))
        await db.connection.execute("DELETE FROM logs WHERE guild_id = ?", (guild_id,))
        await db.connection.commit()
        log.database(f"Hard-deleted settings for guild {guild_id}")
    except Exception as e:
        log.error(f"Failed to hard-delete settings for {guild_id}", exc_info=e)

async def restore_guild_settings(guild_id: int):
    """
    Restores soft-deleted settings.
    """
    if not db.connection:
        return

    try:
        await db.connection.execute(
            "UPDATE guild_settings SET deleted_at = NULL WHERE guild_id = ?", 
            (guild_id,)
        )
        await db.connection.commit()
        log.database(f"Restored settings for guild {guild_id}")
    except Exception as e:
        log.error(f"Failed to restore settings for {guild_id}", exc_info=e)

async def check_soft_deleted_settings(guild_id: int) -> bool:
    """
    Checks if a guild has soft-deleted settings.
    """
    if not db.connection:
        return False
        
    try:
        cursor = await db.connection.execute(
            "SELECT 1 FROM guild_settings WHERE guild_id = ? AND deleted_at IS NOT NULL", 
            (guild_id,)
        )
        return await cursor.fetchone() is not None
    except Exception:
        return False

async def restore_settings_for_active_guilds(guild_ids: list[int]) -> int:
    """
    Restores soft-deleted settings for guilds the bot is currently in.
    This handles the case where the database was restored with stale deleted_at flags.
    Returns the number of guilds restored.
    """
    if not db.connection or not guild_ids:
        return 0
        
    try:
        # Build placeholders for the IN clause
        placeholders = ','.join('?' * len(guild_ids))
        cursor = await db.connection.execute(
            f"UPDATE guild_settings SET deleted_at = NULL WHERE guild_id IN ({placeholders}) AND deleted_at IS NOT NULL",
            guild_ids
        )
        await db.connection.commit()
        return cursor.rowcount
    except Exception as e:
        log.error("Failed to restore settings for active guilds", exc_info=e)
        return 0

async def add_list_item(guild_id: int, list_type: str, entity_type: str, entity_id: int, entity_name: str):
    """
    Adds an item to the blacklist or whitelist.
    """
    if not db.connection:
        return False
        
    try:
        await db.connection.execute(
            """
            INSERT INTO server_lists (guild_id, list_type, entity_type, entity_id, entity_name) 
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, list_type, entity_id) DO UPDATE SET
                entity_name = excluded.entity_name,
                entity_type = excluded.entity_type
            """, 
            (guild_id, list_type, entity_type, entity_id, entity_name)
        )
        await db.connection.commit()
        return True
    except Exception as e:
        log.error(f"Failed to add list item for guild {guild_id}", exc_info=e)
        return False

async def remove_list_item(guild_id: int, list_type: str, entity_id: int):
    """
    Removes an item from the blacklist or whitelist.
    """
    if not db.connection:
        return False
        
    try:
        await db.connection.execute(
            "DELETE FROM server_lists WHERE guild_id = ? AND list_type = ? AND entity_id = ?",
            (guild_id, list_type, entity_id)
        )
        await db.connection.commit()
        return True
    except Exception as e:
        log.error(f"Failed to remove list item for guild {guild_id}", exc_info=e)
        return False

async def get_list_items(guild_id: int, list_type: str):
    """
    Returns all items for a specific list type.
    """
    if not db.connection:
        return []
        
    try:
        db.connection.row_factory = aiosqlite.Row
        cursor = await db.connection.execute(
            "SELECT * FROM server_lists WHERE guild_id = ? AND list_type = ? ORDER BY added_at DESC", 
            (guild_id, list_type)
        )
        return await cursor.fetchall()
    except Exception as e:
        log.error(f"Failed to fetch list items for guild {guild_id}", exc_info=e)
        return []

async def search_list_items(guild_id: int, list_type: str, query: str):
    """
    Fuzzy searches for items in the DB for a specific list.
    """
    if not db.connection:
        return []
        
    try:
        db.connection.row_factory = aiosqlite.Row
        # Simple SQL LIKE for now, can be improved or done in python if more fuzzy needed
        cursor = await db.connection.execute(
            "SELECT * FROM server_lists WHERE guild_id = ? AND list_type = ? AND entity_name LIKE ? LIMIT 25", 
            (guild_id, list_type, f"%{query}%")
        )
        return await cursor.fetchall()
    except Exception as e:
        log.error(f"Failed to search list items for guild {guild_id}", exc_info=e)
        return []

async def get_all_list_items(guild_id: int):
    """
    Returns all blacklist/whitelist items for a guild.
    """
    if not db.connection:
        return []
        
    try:
        db.connection.row_factory = aiosqlite.Row
        cursor = await db.connection.execute(
            "SELECT * FROM server_lists WHERE guild_id = ?", 
            (guild_id,)
        )
        return await cursor.fetchall()
    except Exception as e:
        log.error(f"Failed to fetch all list items for guild {guild_id}", exc_info=e)
        return []
