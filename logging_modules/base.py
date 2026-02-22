from abc import ABC, abstractmethod
import discord
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
        # Unpack
        res = await get_guild_settings(guild.id)
        if not res or not res[0]:
             return None
        
        log_id, msg_id, mem_id = res[0], res[1], res[2]
        enabled_modules = res[6]
        
        if not enabled_modules.get(self.module_name, False):
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
            res = await get_guild_settings(guild.id)
            if not res or not res[0]: # Need at least log_id
                return

            log_id, msg_id, mem_id = res[0], res[1], res[2]
            log_wh, msg_wh, mem_wh = res[3], res[4], res[5]
            enabled_modules = res[6]
            
            if not enabled_modules.get(self.module_name, False):
                return

            target_id = log_id
            target_wh = log_wh
            fallback_id = None  # For complex setup, server-logs as fallback
            
            log.trace(f"[{self.module_name}] Initial target_id={target_id}, target_wh={target_wh}")
            
            # Module Category Routing
            if self.module_name in ["MessageDelete", "MessageEdit"]:
                if msg_id: 
                    target_id = msg_id
                    fallback_id = log_id  # server-logs is fallback
                if msg_wh: target_wh = msg_wh
            elif self.module_name in ["MemberJoin", "MemberLeave", "MemberBan", "VoiceState", "NicknameUpdate", "MemberKick", "TimeoutUpdate"]:
                if mem_id: 
                    target_id = mem_id
                    fallback_id = log_id  # server-logs is fallback
                if mem_wh: target_wh = mem_wh

            if suspicious:
                # Apply suspicious formatting
                embed.color = discord.Color.dark_red()
                embed.title = f"⚠️ Suspicious Activity: {embed.title}"
                
            sent_successfully = False
            webhook_failed = False
            
            # Try Webhook First (with exponential backoff)
            if target_wh:
                success, err = await send_with_backoff(
                    lambda: discord.Webhook.from_url(
                        target_wh, session=self.bot.http_session, client=self.bot
                    ).send(embed=embed)
                )
                
                if success:
                    sent_successfully = True
                    log.trace(f"[{self.module_name}] Webhook send successful")
                elif err and isinstance(err, discord.NotFound):
                    # Webhook is dead
                    log.warning(f"[{self.module_name}] Webhook deleted or invalid, falling back")
                    webhook_failed = True
                elif err:
                    log.error(f"[{self.module_name}] Webhook send failed: {err}")
                    webhook_failed = True

            # Fallback when primary webhook fails
            if not sent_successfully and webhook_failed:
                # Step 1: Send error message via bot to the target channel
                channel = guild.get_channel(target_id) if target_id else None
                if channel:
                    warning_embed = EmbedBuilder.warning(
                        "⚠️ Webhook Unavailable",
                        "The logging webhook was deleted or is invalid.\n"
                        "Attempting to use server-logs webhook as fallback.\n\n"
                        "**Fix:** Run `/setup` to reconfigure webhooks."
                    )
                    await send_with_backoff(lambda: channel.send(embed=warning_embed))
                
                # Step 2: Try server-logs webhook (log_wh) as fallback
                if log_wh and log_wh != target_wh:
                    # Append fallback note to footer
                    if embed.footer and embed.footer.text:
                        embed.set_footer(text=f"{embed.footer.text} | Fallback: via server-logs webhook")
                    else:
                        embed.set_footer(text="Fallback: via server-logs webhook")
                    
                    success, err = await send_with_backoff(
                        lambda: discord.Webhook.from_url(
                            log_wh, session=self.bot.http_session, client=self.bot
                        ).send(embed=embed)
                    )
                    
                    if success:
                        sent_successfully = True
                        log.trace(f"[{self.module_name}] Fallback to server-logs webhook successful")
                    else:
                        log.warning(f"[{self.module_name}] Server-logs webhook also failed: {err}")
                
                # Step 3: Last resort - send via bot to server-logs channel
                if not sent_successfully and fallback_id and fallback_id != target_id:
                    fallback_channel = guild.get_channel(fallback_id)
                    if fallback_channel:
                        if embed.footer and embed.footer.text and "Fallback" not in embed.footer.text:
                            embed.set_footer(text=f"{embed.footer.text} | Fallback: direct send (webhooks unavailable)")
                        elif not embed.footer or not embed.footer.text:
                            embed.set_footer(text="Fallback: direct send (webhooks unavailable)")
                        
                        success, err = await send_with_backoff(lambda: fallback_channel.send(embed=embed))
                        if success:
                            sent_successfully = True
                        else:
                            log.error(f"[{self.module_name}] All fallback methods failed: {err}")

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
