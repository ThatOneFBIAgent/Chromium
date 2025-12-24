import json
import aiosqlite
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from .core import db, log_error, log_database

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
        log_error(f"Failed to upsert settings for guild {guild_id}", exc_info=e)

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
        log_error(f"Failed to fetch settings for guild {guild_id}", exc_info=e)
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
        log_error(f"Failed to add log for guild {guild_id}", exc_info=e)

async def get_recent_logs(guild_id: int, limit: int = 50):
    if not db.connection:
        return []
        
    try:
        db.connection.row_factory = aiosqlite.Row
        cursor = await db.connection.execute("SELECT * FROM logs WHERE guild_id = ? ORDER BY id DESC LIMIT ?", (guild_id, limit))
        rows = await cursor.fetchall()
        return rows
    except Exception as e:
        log_error(f"Failed to fetch logs for guild {guild_id}", exc_info=e)
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
        log_database(f"Soft-deleted settings for guild {guild_id}")
    except Exception as e:
        log_error(f"Failed to soft-delete settings for {guild_id}", exc_info=e)

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
        log_database(f"Hard-deleted settings for guild {guild_id}")
    except Exception as e:
        log_error(f"Failed to hard-delete settings for {guild_id}", exc_info=e)

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
        log_database(f"Restored settings for guild {guild_id}")
    except Exception as e:
        log_error(f"Failed to restore settings for {guild_id}", exc_info=e)

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
