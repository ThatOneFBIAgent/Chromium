from abc import ABC, abstractmethod
import discord
import re
from typing import Optional, Union, List
from discord.ext import commands
from database.queries import get_guild_settings, add_log, get_all_list_items
from utils.embed_builder import EmbedBuilder
from utils.logger import get_logger
from utils.suspicious import suspicious_detector
from utils.rate_limiter import send_with_backoff

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
        # 0 - Dashboard Global Module Toggle
        if hasattr(self.bot, "config_sync"):
            normalized_cog = re.sub(r'(?<!^)(?=[A-Z])', '_', self.module_name).lower()
            guild_cfg = self.bot.config_sync.get(guild.id)
            if guild_cfg:
                enabled_modules = guild_cfg.get("enabled_modules", {})
                if enabled_modules.get(normalized_cog) is False:
                    return False

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
            # Robustness: Check for valid data
            if item.get('guild_id') != guild.id:
                continue
            
            list_type = item.get('list_type')
            entity_type = item.get('entity_type')
            e_id = item.get('entity_id')

            if not list_type or not entity_type or not e_id:
                continue

            if list_type == 'blacklist':
                if entity_type == 'user': user_bl.add(e_id)
                elif entity_type == 'role': role_bl.add(e_id)
                elif entity_type == 'channel': channel_bl.add(e_id)
            elif list_type == 'whitelist':
                if entity_type == 'user': user_wl.add(e_id)
                elif entity_type == 'role': role_wl.add(e_id)
                elif entity_type == 'channel': channel_wl.add(e_id)

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
        # 1. Prefer Dashboard Log Channel
        if hasattr(self.bot, "config_sync"):
            guild_cfg = self.bot.config_sync.get(guild.id)
            if guild_cfg:
                dashboard_log_id = guild_cfg.get("log_channel_id")
                if dashboard_log_id:
                    channel = guild.get_channel(int(dashboard_log_id))
                    if channel:
                        return channel

        # 2. Fallback to Local DB
        res = await get_guild_settings(guild.id)
        if not res or not res[0]:
             return None
        
        log_id, msg_id, mem_id = res[0], res[1], res[2]
        enabled_modules = res[6]
        
        import re
        normalized_name = re.sub(r'(?<!^)(?=[A-Z])', '_', self.module_name).lower()
        if not enabled_modules.get(normalized_name, False):
            return None
            
        # Routing Logic
        target_id = log_id # Default to server-logs
        
        if self.module_name in ["MessageDelete", "MessageEdit"]:
            if msg_id: target_id = msg_id
        elif self.module_name in [
            "MemberJoin", "MemberLeave", "MemberBan", "VoiceState", "NicknameUpdate", "MemberKick", "TimeoutUpdate"
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
            # 1. Fetch Local Settings for Fallback & Webhooks
            res = await get_guild_settings(guild.id)
            local_log_id = res[0] if res else None
            local_msg_id = res[1] if res else None
            local_mem_id = res[2] if res else None
            local_log_wh = res[3] if res else None
            local_msg_wh = res[4] if res else None
            local_mem_wh = res[5] if res else None
            local_enabled = res[6] if res else {}

            # 2. Check Dashboard Config
            dash_cfg = {}
            if hasattr(self.bot, "config_sync"):
                dash_cfg = self.bot.config_sync.get(guild.id)
            
            dash_log_id = dash_cfg.get("log_channel_id")
            dash_complex = dash_cfg.get("complex_logs", {})
            dash_enabled = dash_cfg.get("enabled_modules", {})
            dash_mode = dash_cfg.get("log_mode", "simple")

            import re
            normalized_name = re.sub(r'(?<!^)(?=[A-Z])', '_', self.module_name).lower()
            
            # Module Enablement Check (Combined)
            if dash_enabled.get(normalized_name) is False:
                log.trace(f"[{self.module_name}] Blocked: Disabled in Dashboard.")
                return
            if not local_enabled.get(self.module_name, False):
                # If it's disabled in local DB, we only log if it's explicitly enabled in dash
                if not dash_enabled.get(normalized_name):
                    log.trace(f"[{self.module_name}] Blocked: Disabled in Local DB.")
                    return

            # 3. Routing Logic (Prioritize Dashboard)
            target_id = None
            target_wh = None
            
            if dash_mode == "complex" and dash_complex:
                if self.module_name in ["MessageDelete", "MessageEdit"]:
                    target_id = dash_complex.get("message")
                elif self.module_name in [
                    "MemberJoin", "MemberLeave", "MemberBan", "VoiceState", "NicknameUpdate", "MemberKick", "TimeoutUpdate"
                ]:
                    target_id = dash_complex.get("member")
                else:
                    target_id = dash_complex.get("system")
            
            if not target_id:
                target_id = dash_log_id or local_log_id
            
            # Webhook Routing (Dashboard doesn't support webhooks yet, so use local)
            target_wh = local_log_wh
            if self.module_name in ["MessageDelete", "MessageEdit"]:
                if local_msg_wh: target_wh = local_msg_wh
                if not target_id: target_id = local_msg_id
            elif self.module_name in [
                "MemberJoin", "MemberLeave", "MemberBan", "VoiceState", "NicknameUpdate", "MemberKick", "TimeoutUpdate"
            ]:
                if local_mem_wh: target_wh = local_mem_wh
                if not target_id: target_id = local_mem_id

            if suspicious:
                embed.color = discord.Color.dark_red()
                embed.title = f"⚠️ Suspicious Activity: {embed.title}"
                
            sent_successfully = False
            
            # Try Webhook
            if target_wh:
                success, _ = await send_with_backoff(
                    lambda: discord.Webhook.from_url(
                        target_wh, session=self.bot.http_session, client=self.bot
                    ).send(embed=embed)
                )
                if success:
                    sent_successfully = True

            # Fallback to Channel
            if not sent_successfully and target_id:
                channel = guild.get_channel(int(target_id))
                if channel:
                    await send_with_backoff(lambda: channel.send(embed=embed))
                    sent_successfully = True
            
            if not sent_successfully:
                log.warning(f"[{self.module_name}] Failed to send log to guild {guild.id}")
                return

            # DB Persist (only if we successfully sent)
            if sent_successfully:
                content = f"{embed.title}: {embed.description}"
                if embed.fields:
                    content += " | " + " | ".join([f"{f.name}: {f.value}" for f in embed.fields])
                
                await add_log(guild.id, self.module_name, content)
                
        except discord.errors.Forbidden:
            log.error(f"Forbidden to send log in {guild.name}, bot may have been kicked")
        except Exception as e:
            log.error(f"Error logging event in {self.module_name}", exc_info=e)
