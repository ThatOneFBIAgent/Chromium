from abc import ABC, abstractmethod
import discord
from typing import Optional, Union, List
from discord.ext import commands
from database.queries import get_guild_settings, add_log, get_all_list_items
from utils.embed_builder import EmbedBuilder
from utils.logger import get_logger
from utils.suspicious import suspicious_detector

log = get_logger()

class BaseLogger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.module_name = self.__class__.__name__

    async def should_log(self, guild: discord.Guild, user: Union[discord.User, discord.Member, None] = None, channel: Optional[discord.abc.GuildChannel] = None) -> bool:
        """
        Check if the event should be logged based on blacklists/whitelists.
        Order:
        1 - User Whitelist (The "Suspicious Person" check-log them no matter where they are).
        2 - User Blacklist (The "Privacy" check-if Joe is blocked, he is blocked everywhere).
        3 - Channel Whitelist (The "Important Room" check-if this room is whitelisted, log everyone, even blacklisted roles).
        4 - Role Whitelist (The "Staff/Fanatic" check-log them even in blacklisted channels).
        5 - Channel Blacklist (The "Private Room" check-don't log unless caught by a higher whitelist).
        6 - Role Blacklist (The "Ignore Bots/Spammers" check-don't log unless caught by a higher whitelist).
        7 - DEFAULT: LOG IT (Since the bot is Opt-Out).
        """
        # Fetch all list items for this guild
        items = await get_all_list_items(guild.id)
        
        if not items:
            return True

        # Organize items
        user_bl = set()
        user_wl = set()
        role_bl = set()
        role_wl = set()
        channel_bl = set()
        channel_wl = set()
        
        for item in items:
            # item: id, guild_id, list_type, entity_type, entity_id
            e_id = item['entity_id']
            if item['list_type'] == 'blacklist':
                if item['entity_type'] == 'user': user_bl.add(e_id)
                elif item['entity_type'] == 'role': role_bl.add(e_id)
                elif item['entity_type'] == 'channel': channel_bl.add(e_id)
            elif item['list_type'] == 'whitelist':
                if item['entity_type'] == 'user': user_wl.add(e_id)
                elif item['entity_type'] == 'role': role_wl.add(e_id)
                elif item['entity_type'] == 'channel': channel_wl.add(e_id)

        # 1. User Whitelist
        if user and user.id in user_wl:
            return True
            
        # 2. User Blacklist
        if user and user.id in user_bl:
            return False
            
        # 3. Channel Whitelist
        if channel and channel.id in channel_wl:
            return True
            
        # 4. Role Whitelist
        if user and isinstance(user, discord.Member):
            for role in user.roles:
                if role.id in role_wl:
                    return True
                    
        # 5. Channel Blacklist
        if channel and channel.id in channel_bl:
            return False
            
        # 6. Role Blacklist
        if user and isinstance(user, discord.Member):
             for role in user.roles:
                if role.id in role_bl:
                    return False
        
        # 7. Default
        return True

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
