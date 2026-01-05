import discord
from discord import app_commands
from discord.ext import commands
from database.queries import upsert_guild_settings
from utils.embed_builder import EmbedBuilder
from utils.views import ConfirmationView
import discord.utils

class Setup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    setup_group = app_commands.Group(name="setup", description="Configure the bot for your server")
    
    @app_commands.command(name="commands", description="Show available commands")
    async def cmd_help(self, interaction: discord.Interaction):
        embed = EmbedBuilder.build(
            title="Chromium Help",
            description="Here are the available commands:",
            fields=[
                ("/setup simple", "Configure logs to the current channel.", False),
                ("/setup complex", "Create dedicated logging channels/categories.", False),
                ("/log list", "List status of all logging modules.", False),
                ("/log enable <module>", "Enable a specific logging module.", False),
                ("/log disable <module>", "Disable a specific logging module.", False),
                ("/export", "Export the last 50 logs to a JSON file.", False),
                ("/blacklist add|remove|show", "Blacklist a user, role or channel from logging.", False),
                ("/whitelist add|remove|show", "Whitelist a user or role from logging.", False)
            ]
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    


    @setup_group.command(name="simple", description="Use the current channel for all logs")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 40, key=lambda i: (i.guild_id, i.user.id))
    async def simple_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False) 
        
        # Confirmation Stage
        view = ConfirmationView(timeout=180.0, author_id=interaction.user.id)
        embed = EmbedBuilder.warning(
            title="Confirm Simple Setup",
            description=f"This will configure **{interaction.channel.mention}** as the log channel for ALL modules.\nExisting settings will be overwritten.",
            footer="You have 3 minutes to confirm."
        )
        msg = await interaction.followup.send(embed=embed, view=view)
        
        await view.wait()
        
        if view.value is None:
            await msg.edit(content="Setup timed out.", view=None, embed=None)
            return
        elif view.value is False:
            await msg.edit(content="Setup cancelled.", view=None, embed=None)
            return
            
        # Proceed with Setup
        await msg.edit(content="Configuring...", view=None, embed=None)

        default_modules = {
            "MessageDelete": True, "MessageEdit": True, "MemberJoin": True, 
            "MemberLeave": True, "VoiceState": True, "RoleUpdate": True, 
            "ChannelUpdate": True, "ErrorLogger": True, "MemberBan": True,
            "GuildUpdate": True, "EmojiUpdate": True, "MemberKick": True,
            "NicknameUpdate": True, "TimeoutUpdate": True, "WebhookUpdate": True,
            "InviteUpdate": True, "RolePermissionUpdate": True, "AutoModUpdate": True
        }
        
        # In simple setup, everything goes to log_channel_id (legacy field used for fallback/server)
        await upsert_guild_settings(
            interaction.guild_id, 
            log_channel_id=interaction.channel_id,
            message_log_id=interaction.channel_id,
            member_log_id=interaction.channel_id,
            enabled_modules=default_modules
        )
        
        embed = EmbedBuilder.success(
            title="Setup Complete",
            description=f"Logging configured for {interaction.channel.mention}. All modules enabled."
        )
        await interaction.followup.send(embed=embed)

    @setup_group.command(name="complex", description="Create dedicated channels and categories")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 40, key=lambda i: (i.guild_id, i.user.id))
    async def complex_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        guild = interaction.guild
        
        # Confirmation Stage
        view = ConfirmationView(timeout=180.0, author_id=interaction.user.id)
        embed = EmbedBuilder.warning(
            title="Confirm Complex Setup",
            description="This will create a 'ChromiumLogs' category and 3 channels (server-logs, message-logs, member-logs).\nExisting settings will be overwritten.",
            footer="You have 3 minutes to confirm."
        )
        msg = await interaction.followup.send(embed=embed, view=view)
        
        await view.wait()
        
        if view.value is None:
            await msg.edit(content="Setup timed out.", view=None, embed=None)
            return
        elif view.value is False:
            await msg.edit(content="Setup cancelled.", view=None, embed=None)
            return

        # Proceed with Setup
        await msg.edit(content="Configuring...", view=None, embed=None)
        
        try:
            # Check for existing Category
            # this would be better if discord allowed categories to have IDs to check for but oh well
            category = discord.utils.get(guild.categories, name="ChromiumLogs")
            if not category:
                category = await guild.create_category("ChromiumLogs")
            
            # Permissions: Deny view for everyone, Allow for bot
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True)
            }
            
            # Create Channels if they don't exist
            # server-logs
            server_logs = discord.utils.get(category.text_channels, name="server-logs")
            if not server_logs:
                server_logs = await guild.create_text_channel("server-logs", category=category, overwrites=overwrites)
                
            # message-logs
            message_logs = discord.utils.get(category.text_channels, name="message-logs")
            if not message_logs:
                message_logs = await guild.create_text_channel("message-logs", category=category, overwrites=overwrites)
                
            # member-logs (user-logs)
            member_logs = discord.utils.get(category.text_channels, name="member-logs")
            if not member_logs:
                member_logs = await guild.create_text_channel("member-logs", category=category, overwrites=overwrites)
            
            default_modules = {
                "MessageDelete": True, "MessageEdit": True, "MemberJoin": True, 
                "MemberLeave": True, "VoiceState": True, "RoleUpdate": True, 
                "ChannelUpdate": True, "ErrorLogger": True, "MemberBan": True,
                "GuildUpdate": True, "EmojiUpdate": True, "MemberKick": True,
                "NicknameUpdate": True, "TimeoutUpdate": True, "WebhookUpdate": True,
                "InviteUpdate": True, "RolePermissionUpdate": True, "AutoModUpdate": True
            }
            
            await upsert_guild_settings(
                guild.id, 
                log_channel_id=server_logs.id,
                message_log_id=message_logs.id,
                member_log_id=member_logs.id,
                susp_channel_id=server_logs.id,
                enabled_modules=default_modules
            )
            
            embed = EmbedBuilder.success(
                title="Complex Setup Complete",
                description="Server logging channels created.",
                fields=[
                    ("Category", category.name, True),
                    ("Server Logs", server_logs.mention, True),
                    ("Message Logs", message_logs.mention, True),
                    ("Member Logs", member_logs.mention, True)
                ]
            )
            await interaction.followup.send(embed=embed)
            
        except discord.Forbidden:
            await interaction.followup.send(
                embed=EmbedBuilder.error("Permission Error", "I need 'Manage Channels' permission to perform complex setup.")
            )
        except Exception as e:
            await interaction.followup.send(
                embed=EmbedBuilder.error("Setup Failed", f"An error occurred: {str(e)}")
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(Setup(bot))
