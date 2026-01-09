import discord
from datetime import datetime, timezone
from typing import Optional

MAX_TITLE = 256
MAX_DESC = 4096
MAX_FIELD_NAME = 256
MAX_FIELD_VALUE = 1024
MAX_FOOTER = 2048

# Common error templates with troubleshooting steps
ERROR_TEMPLATES = {
    "not_configured": {
        "title": "❌ Not Configured",
        "description": "This server does not have Chromium configured!",
        "steps": [
            "Run `/setup simple` to use the current channel for logging",
            "Run `/setup complex` to create dedicated logging channels",
            "Contact a server administrator if you need help"
        ]
    },
    "missing_permissions": {
        "title": "🔒 Missing Permissions",
        "description": "You don't have permission to use this command.",
        "steps": [
            "Ask a server administrator for the required role",
            "The `Manage Server` permission is required for most commands"
        ]
    },
    "bot_missing_permissions": {
        "title": "⚠️ Bot Missing Permissions",
        "description": "I don't have the required permissions to do this.",
        "steps": [
            "Check my role in Server Settings → Roles",
            "Make sure I have the permissions listed above",
            "Try re-inviting me with the correct permissions"
        ]
    },
    "invalid_input": {
        "title": "❓ Invalid Input",
        "description": "The provided input is not valid.",
        "steps": [
            "Use the autocomplete suggestions when available",
            "Check the command syntax with `/commands`"
        ]
    },
    "webhook_failed": {
        "title": "⚠️ Webhook Unavailable",
        "description": "The logging webhook was deleted or is invalid.",
        "steps": [
            "Run `/setup` again to reconfigure webhooks",
            "Check the channel permissions for Manage Webhooks",
            "Logs are being sent directly to the channel as fallback"
        ]
    }
}

def clamp(text: str, limit: int) -> str:
    if not text:
        return text
    if len(text) <= limit:
        return text
    return text[:limit - 15] + "\n*(truncated)*"

class EmbedBuilder:
    @staticmethod
    def build(
        *,
        title: str,
        description: str,
        color: discord.Color = discord.Color.blue(),
        author: Optional[discord.User] = None,
        footer: str = "Chromium System",
        fields: Optional[list] = None
    ) -> discord.Embed:

        embed = discord.Embed(
            title=clamp(title, MAX_TITLE),
            description=clamp(description, MAX_DESC),
            color=color,
            timestamp=datetime.now(timezone.utc)
        )

        if author:
            embed.set_author(
                name=clamp(f"{author.name} ({author.id})", MAX_TITLE),
                icon_url=author.display_avatar.url
            )

        embed.set_footer(text=clamp(footer, MAX_FOOTER))

        if fields:
            for name, value, inline in fields:
                embed.add_field(
                    name=clamp(str(name), MAX_FIELD_NAME),
                    value=clamp(str(value), MAX_FIELD_VALUE),
                    inline=inline
                )

        return embed

    @staticmethod
    def success(title: str, description: str, **kwargs) -> discord.Embed:
        return EmbedBuilder.build(
            title=title,
            description=description,
            color=discord.Color.green(),
            **kwargs
        )

    @staticmethod
    def error(title: str, description: str, **kwargs) -> discord.Embed:
        return EmbedBuilder.build(
            title=title,
            description=description,
            color=discord.Color.red(),
            **kwargs
        )

    @staticmethod
    def warning(title: str, description: str, **kwargs) -> discord.Embed:
        return EmbedBuilder.build(
            title=title,
            description=description,
            color=discord.Color.gold(),
            **kwargs
        )

    @staticmethod
    def info(title: str, description: str, **kwargs) -> discord.Embed:
        """Blue informational embed."""
        return EmbedBuilder.build(
            title=title,
            description=description,
            color=discord.Color.blurple(),
            **kwargs
        )

    @staticmethod
    def troubleshoot(error_key: str, extra_context: str = "") -> discord.Embed:
        """
        Create an error embed with built-in troubleshooting steps.
        
        Args:
            error_key: Key from ERROR_TEMPLATES (e.g. 'not_configured')
            extra_context: Additional context to append to the description
        """
        template = ERROR_TEMPLATES.get(error_key, {
            "title": "Error",
            "description": "An unknown error occurred.",
            "steps": ["Please try again or contact support"]
        })
        
        description = template["description"]
        if extra_context:
            description += f"\n\n{extra_context}"
        
        # Format troubleshooting steps
        if template.get("steps"):
            description += "\n\n**Troubleshooting:**\n"
            for step in template["steps"]:
                description += f"• {step}\n"
        
        return EmbedBuilder.error(
            title=template["title"],
            description=description.strip()
        )
