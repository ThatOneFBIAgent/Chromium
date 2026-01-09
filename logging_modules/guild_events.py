import discord
from discord.ext import commands
from database.queries import delete_guild_settings, check_soft_deleted_settings, restore_guild_settings, hard_delete_guild_settings
from utils.logger import get_logger
from utils.embed_builder import EmbedBuilder

log = get_logger()

class RestorationView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.value = None

    @discord.ui.button(label="Restore Settings", style=discord.ButtonStyle.green, emoji="♻️")
    async def restore_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await restore_guild_settings(self.guild_id)
        
        embed = EmbedBuilder.success(
            "Configuration Restored",
            "Your previous settings have been restored. \n"
            "If channels were deleted, logs will fallback to the main server channel (if available). \n"
            "Use `/log list` to check status."
        )
        await interaction.followup.send(embed=embed)
        self.value = True
        self.stop()
        # Disable buttons
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Start Fresh", style=discord.ButtonStyle.red, emoji="🆕")
    async def fresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await hard_delete_guild_settings(self.guild_id)
        
        embed = EmbedBuilder.info(
            "Fresh Start",
            "Previous settings wiped. Please run `/setup` to configure the bot."
        )
        await interaction.followup.send(embed=embed)
        self.value = False
        self.stop()
        # Disable buttons
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

class GuildEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """
        Triggered when the bot is kicked, banned, or leaves a guild.
        Soft-deletes configuration data (kept for 60 days).
        """
        log.discord(f"Bot removed from guild: {guild.name} ({guild.id}). Soft-deleting settings.")
        try:
            await delete_guild_settings(guild.id)
        except Exception as e:
            log.error(f"Failed to soft-delete guild settings: {e}")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """
        Triggered when the bot joins a guild.
        Checks for soft-deleted settings and prompts for restoration.
        """
        log.discord(f"Joined guild: {guild.name} ({guild.id}). Checking for previous settings.")
        
        is_returning = await check_soft_deleted_settings(guild.id)
        if not is_returning:
            # Just a fresh join, usually we might send a welcome message here, 
            # but for now we only care about restoration.
            return

        # Find a channel to send the prompt to
        target_channel = guild.system_channel
        if not target_channel or not target_channel.permissions_for(guild.me).send_messages:
            # Try to find general or any text channel
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    target_channel = channel
                    break
        
        if not target_channel:
            log.discord(f"Could not find channel to send restoration prompt in {guild.name}")
            return

        view = RestorationView(guild.id)
        embed = EmbedBuilder.info(
            "Welcome Back! 👋",
            f"I found previous configuration settings for **{guild.name}**.\n"
            "Would you like to restore them?",
            footer="These settings will be permanently deleted in 60 days if not restored."
        )
        
        await target_channel.send(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(GuildEvents(bot))
