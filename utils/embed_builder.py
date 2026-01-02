import discord
from datetime import datetime, timezone
from typing import Optional

MAX_TITLE = 256
MAX_DESC = 4096
MAX_FIELD_NAME = 256
MAX_FIELD_VALUE = 1024
MAX_FOOTER = 2048

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
