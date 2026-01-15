# Permission Requirements for Logging Modules
# Maps each module to the Discord permissions it requires to function properly

import discord
from typing import Dict, List, Tuple

# Module -> List of required permission names (as they appear in discord.Permissions)
MODULE_PERMISSIONS: Dict[str, List[str]] = {
    "MessageDelete": ["view_channel", "read_message_history"],
    "MessageEdit": ["view_channel", "read_message_history"],
    "MemberJoin": ["view_channel"],
    "MemberLeave": ["view_channel"],
    "MemberBan": ["view_audit_log"],
    "MemberKick": ["view_audit_log"],
    "VoiceState": ["view_channel"],
    "RoleUpdate": ["view_channel"],
    "ChannelUpdate": ["view_channel"],
    "ErrorLogger": [],  # No special permissions
    "GuildUpdate": ["view_channel"],
    "EmojiUpdate": ["view_channel"],
    "NicknameUpdate": ["view_channel"],
    "TimeoutUpdate": ["view_audit_log", "moderate_members"],
    "WebhookUpdate": ["manage_webhooks"],
    "InviteUpdate": ["manage_guild"],
    "RolePermissionUpdate": ["view_audit_log"],
    "RolePermissionUpdate": ["view_audit_log"],
}

# Human-readable permission names for display
PERMISSION_DISPLAY_NAMES: Dict[str, str] = {
    "view_channel": "View Channels",
    "read_message_history": "Read Message History",
    "view_audit_log": "View Audit Log",
    "manage_webhooks": "Manage Webhooks",
    "manage_guild": "Manage Server",
    "moderate_members": "Moderate Members",
}

def check_bot_permissions(guild: discord.Guild) -> Dict[str, List[str]]:
    """
    Check which modules have missing permissions.
    
    Returns:
        Dict mapping module names to list of missing permission names.
        Only includes modules that have missing permissions.
    """
    bot_perms = guild.me.guild_permissions
    missing: Dict[str, List[str]] = {}
    
    for module, required_perms in MODULE_PERMISSIONS.items():
        module_missing = []
        for perm_name in required_perms:
            if not getattr(bot_perms, perm_name, False):
                module_missing.append(perm_name)
        
        if module_missing:
            missing[module] = module_missing
    
    return missing

def format_missing_permissions(missing: Dict[str, List[str]]) -> str:
    """
    Format missing permissions for user display.
    
    Returns a formatted string like:
    • MemberBan: View Audit Log
    • WebhookUpdate: Manage Webhooks
    """
    lines = []
    for module, perms in missing.items():
        perm_names = [PERMISSION_DISPLAY_NAMES.get(p, p) for p in perms]
        lines.append(f"• **{module}**: {', '.join(perm_names)}")
    return "\n".join(lines)

def get_modules_to_disable(missing: Dict[str, List[str]]) -> Dict[str, bool]:
    """
    Get a dict of modules that should be disabled due to missing permissions.
    
    Returns:
        Dict like {"MemberBan": False, "WebhookUpdate": False}
    """
    return {module: False for module in missing.keys()}
