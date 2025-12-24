from abc import ABC, abstractmethod
import discord
from typing import Optional
from discord.ext import commands
from database.queries import get_guild_settings, add_log
from utils.embed_builder import EmbedBuilder
from utils.logger import get_logger
from utils.suspicious import suspicious_detector

log = get_logger()

class BaseLogger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.module_name = self.__class__.__name__

    async def get_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        log_id, msg_id, mem_id, susp_id, enabled_modules = await get_guild_settings(guild.id)
        
        if not enabled_modules.get(self.module_name, False):
            return None
            
        # Routing Logic
        target_id = log_id # Default to server-logs
        
        if self.module_name in ["MessageDelete", "MessageEdit"]:
            if msg_id: target_id = msg_id
        elif self.module_name in [
            "MemberJoin", "MemberLeave", "MemberBan", "VoiceState", "NicknameUpdate", "MemberKick", "MemberTimeout"
            ]:
            if mem_id: target_id = mem_id
            
        # Fallback Logic:
        # 1. Try Specific Channel
        channel = None
        if target_id:
            channel = guild.get_channel(target_id)
            
        # 2. If Specific Channel is missing/deleted, try Generic Server Log (log_id)
        if not channel and log_id and log_id != target_id:
             channel = guild.get_channel(log_id)
             
        # 3. If Generic Channel is also missing, fail safely (return None)
        return channel

    async def log_event(self, guild: discord.Guild, embed: discord.Embed, suspicious: bool = False):
        try:
            log_id, msg_id, mem_id, susp_id, enabled_modules = await get_guild_settings(guild.id)
            
            if not enabled_modules.get(self.module_name, False):
                return

            target_id = log_id
            
            # Module Category Routing
            if self.module_name in ["MessageDelete", "MessageEdit"]:
                if msg_id: target_id = msg_id
            elif self.module_name in ["MemberJoin", "MemberLeave", "MemberBan", "VoiceState", "NicknameUpdate", "MemberKick"]:
                if mem_id: target_id = mem_id

            if suspicious:
                # Force to server logs for visibility, or susp_id if configured
                target_id = susp_id if susp_id else log_id
                
                embed.color = discord.Color.dark_red()
                embed.title = f"⚠️ Suspicious Activity: {embed.title}"

            if not target_id:
                return

            channel = guild.get_channel(target_id)
            
            # Fallback Logic: If specific channel is missing, try main log_id
            if not channel and target_id != log_id and log_id:
                channel = guild.get_channel(log_id)
                if channel:
                    if embed.footer and embed.footer.text:
                        embed.set_footer(text=f"{embed.footer.text} | Note: Original channel missing. Run /setup to fix.")
                    else:
                        embed.set_footer(text="Note: Original channel missing. Run /setup to fix.")
            
            if channel:
                await channel.send(embed=embed)

            # DB Persist
            content = f"{embed.title}: {embed.description}"
            if embed.fields:
                content += " | " + " | ".join([f"{f.name}: {f.value}" for f in embed.fields])
            
            await add_log(guild.id, self.module_name, content)
            
        except Exception as e:
            log.error(f"Error logging event in {self.module_name}", exc_info=e)
