import pytest
import discord
import time
from unittest.mock import AsyncMock, MagicMock
from logging_modules.member_join import MemberJoin
from logging_modules.message_delete import MessageDelete
from logging_modules.role_update import RoleUpdate
from logging_modules.webhook_update import WebhookUpdate
from logging_modules.voice_state import VoiceState
from utils.suspicious import suspicious_detector
from collections import deque

@pytest.mark.asyncio
async def test_member_join_logging(mocker, mock_guild, mock_user):
    """
    Verify that MemberJoin.on_member_join calls log_event when should_log returns True.
    """
    bot = MagicMock()
    cog = MemberJoin(bot)
    
    # Mock mocks / mock cubed coming soon at theathers
    mock_guild.owner = mock_user # Just to be safe, though not used anymore
    mock_user.guild = mock_guild
    mock_user.created_at = discord.utils.utcnow()
    
    # Mock should_log to return True
    mocker.patch.object(cog, 'should_log', return_value=True)
    
    # Mock log_event
    mock_log = mocker.patch.object(cog, 'log_event', new_callable=AsyncMock)
    
    # Trigger
    await cog.on_member_join(mock_user)
    
    # Assert
    mock_log.assert_called_once()
    assert mock_log.call_args[0][0] == mock_guild # First arg is guild

@pytest.mark.asyncio
async def test_member_join_blocked(mocker, mock_guild, mock_user):
    """
    Verify that MemberJoin.on_member_join DOES NOT call log_event when should_log returns False.
    """
    bot = MagicMock()
    cog = MemberJoin(bot)
    
    mock_user.guild = mock_guild
    mock_user.created_at = discord.utils.utcnow()
    
    # Mock should_log to return False
    mocker.patch.object(cog, 'should_log', return_value=False)
    
    mock_log = mocker.patch.object(cog, 'log_event', new_callable=AsyncMock)
    
    await cog.on_member_join(mock_user)
    
    mock_log.assert_not_called()

@pytest.mark.asyncio
async def test_message_delete_logging(mocker, mock_guild, mock_user, mock_channel):
    """
    Verify MessageDelete.on_message_delete integration.
    """
    bot = MagicMock()
    cog = MessageDelete(bot)

    mock_user.bot = False # Critical: Mocks are true by default!
    
    message = MagicMock(spec=discord.Message)
    message.guild = mock_guild
    message.author = mock_user
    message.channel = mock_channel
    message.content = "Test Content"
    message.attachments = []
    
    # Mock should_log to return True
    mocker.patch.object(cog, 'should_log', return_value=True)
    
    # Mock log_event
    mock_log = mocker.patch.object(cog, 'log_event', new_callable=AsyncMock)
    
    # Mock suspicious detector to avoid errors if imported
    mocker.patch("utils.suspicious.suspicious_detector.check_message_delete", return_value=False)
    
    await cog.on_message_delete(message)
    
    mock_log.assert_called_once()

@pytest.mark.asyncio
async def test_message_delete_blocked(mocker, mock_guild, mock_user, mock_channel):
    """
    Verify MessageDelete.on_message_delete integration blocked.
    """
    bot = MagicMock()
    cog = MessageDelete(bot)
    
    message = MagicMock(spec=discord.Message)
    message.guild = mock_guild
    message.author = mock_user
    message.channel = mock_channel
    
    # Mock should_log to return False
    mocker.patch.object(cog, 'should_log', return_value=False)
    
    mock_log = mocker.patch.object(cog, 'log_event', new_callable=AsyncMock)
    
    await cog.on_message_delete(message)
    
    mock_log.assert_not_called()

# Role Update Tests

@pytest.mark.asyncio
async def test_role_update_name_change(mocker, mock_guild):
    """
    Verify role update name change detection.
    """
    bot = MagicMock()
    cog = RoleUpdate(bot)
    
    before_role = MagicMock(spec=discord.Role)
    after_role = MagicMock(spec=discord.Role)
    
    before_role.name = "Old Name"
    after_role.name = "New Name"
    after_role.guild = mock_guild
    after_role.mention = "@New Name"
    
    # Ensure other attributes match
    before_role.color = after_role.color = discord.Color.blue()
    before_role.icon = after_role.icon = None
    before_role.hoist = after_role.hoist = False
    before_role.mentionable = after_role.mentionable = True
    before_role.permissions.value = after_role.permissions.value = 0
    
    mock_log = mocker.patch.object(cog, 'log_event', new_callable=AsyncMock)
    
    await cog.on_guild_role_update(before_role, after_role)
    
    mock_log.assert_called_once()
    # Check if embed description contains changes
    embed = mock_log.call_args[0][1] # Second arg is embed
    assert "Old Name" in embed.description
    assert "New Name" in embed.description
    assert "suspicious" not in mock_log.call_args.kwargs or not mock_log.call_args.kwargs['suspicious']

@pytest.mark.asyncio
async def test_role_update_perms_change(mocker, mock_guild):
    """
    Verify role update permission change detection.
    """
    bot = MagicMock()
    cog = RoleUpdate(bot)
    
    before_role = MagicMock(spec=discord.Role)
    after_role = MagicMock(spec=discord.Role)
    
    # Identities
    before_role.name = after_role.name = "Test Role"
    after_role.guild = mock_guild
    after_role.mention = "@Test Role"
    
    # Permissions setup - Need to iterate over them
    # Mocking permission iterator
    perms_list = [('view_channels', True), ('manage_messages', False)]
    before_role.permissions = MagicMock()
    before_role.permissions.__iter__.return_value = iter(perms_list)
    before_role.permissions.value = 10
    
    after_role.permissions = MagicMock()
    after_role.permissions.value = 20 # Changed
    
    # Simulate getattr for after.permissions
    def get_perm(name):
        if name == 'view_channels': return True
        if name == 'manage_messages': return True # Changed from False to True
        return False
    
    # We can't easily mock getattr on a Mock object in a loop unless we use specs or side_effect
    # Simplified approach: The loop iterates 'before', and checks 'after'.
    # We just need to make sure 'after.permissions.manage_messages' is different.
    configure_perm_mock(after_role.permissions, {'view_channels': True, 'manage_messages': True})
    
    # Mock matching attribs
    before_role.color = after_role.color
    before_role.icon = after_role.icon
    before_role.hoist = after_role.hoist
    before_role.mentionable = after_role.mentionable
    
    mock_log = mocker.patch.object(cog, 'log_event', new_callable=AsyncMock)
    
    await cog.on_guild_role_update(before_role, after_role)
    
    mock_log.assert_called_once()
    embed = mock_log.call_args[0][1]
    assert "manage_messages: False -> True" in embed.description

def configure_perm_mock(mock_perms, value_dict):
    """Helper to allow getattr(mock_perms, 'name') to work"""
    # Mocks usually return new mocks for attributes. We want specific values.
    # We can use specs, or just assign them.
    for k, v in value_dict.items():
        setattr(mock_perms, k, v)

@pytest.mark.asyncio
async def test_role_no_change(mocker, mock_guild):
    """
    Verify no event is logged if nothing important changes.
    """
    bot = MagicMock()
    cog = RoleUpdate(bot)
    
    before_role = MagicMock(spec=discord.Role)
    after_role = MagicMock(spec=discord.Role)
    
    before_role.name = after_role.name = "Role"
    before_role.color = after_role.color = discord.Color.red()
    before_role.icon = after_role.icon = None
    before_role.hoist = after_role.hoist = True
    before_role.mentionable = after_role.mentionable = False
    
    before_role.permissions.value = after_role.permissions.value = 8
    
    mock_log = mocker.patch.object(cog, 'log_event', new_callable=AsyncMock)
    
    await cog.on_guild_role_update(before_role, after_role)
    
    mock_log.assert_not_called()

@pytest.mark.asyncio
async def test_role_member_update_added(mocker, mock_guild, mock_user):
    """
    Verify role assignment logging.
    """
    bot = MagicMock()
    cog = RoleUpdate(bot)
    
    before_member = MagicMock(spec=discord.Member)
    after_member = MagicMock(spec=discord.Member)
    
    before_member.guild = after_member.guild = mock_guild
    after_member.mention = "@User"
    after_member.id = 12345
    
    # Setup Roles
    role1 = MagicMock(spec=discord.Role); role1.name = "Role1"; role1.mention = "@Role1"
    role2 = MagicMock(spec=discord.Role); role2.name = "Role2"; role2.mention = "@Role2"
    
    before_member.roles = [role1]
    after_member.roles = [role1, role2] # Added role2
    
    # Mock should_log
    mocker.patch.object(cog, 'should_log', return_value=True)
    
    mock_log = mocker.patch.object(cog, 'log_event', new_callable=AsyncMock)
    
    await cog.on_member_update(before_member, after_member)
    
    mock_log.assert_called_once()
    embed = mock_log.call_args[0][1]
    assert "**Added:** @Role2" in embed.description
    assert "**Removed:**" not in embed.description

@pytest.mark.asyncio
async def test_role_member_update_removed(mocker, mock_guild, mock_user):
    """
    Verify role removal logging.
    """
    bot = MagicMock()
    cog = RoleUpdate(bot)
    
    before_member = MagicMock(spec=discord.Member)
    after_member = MagicMock(spec=discord.Member)
    
    before_member.guild = after_member.guild = mock_guild
    after_member.mention = "@User"
    after_member.id = 12345
    
    role1 = MagicMock(spec=discord.Role); role1.name = "Role1"; role1.mention = "@Role1"
    
    before_member.roles = [role1]
    after_member.roles = [] # Removed role1
    
    mocker.patch.object(cog, 'should_log', return_value=True)
    mock_log = mocker.patch.object(cog, 'log_event', new_callable=AsyncMock)
    
    await cog.on_member_update(before_member, after_member)
    
    mock_log.assert_called_once()
    embed = mock_log.call_args[0][1]
    assert "**Removed:** @Role1" in embed.description

@pytest.mark.asyncio
async def test_webhook_created_logs(mocker, mock_guild):
    bot = MagicMock()
    cog = WebhookUpdate(bot)

    channel = MagicMock()
    channel.id = 123
    channel.guild = mock_guild
    channel.mention = "#logs"

    # Pretend there was nothing before
    cog._webhook_cache = {}

    fake_webhook = MagicMock()
    fake_webhook.id = 999
    fake_webhook.name = "sus-hook"
    fake_webhook.channel_id = channel.id

    # Now Discord "returns" one webhook
    channel.webhooks = AsyncMock(return_value=[fake_webhook])

    mock_log = mocker.patch.object(cog, "log_event", new_callable=AsyncMock)

    await cog.on_webhooks_update(channel)

    mock_log.assert_called_once()

    embed = mock_log.call_args[0][1]
    assert "Webhooks changed" in embed.title
    assert "#logs" in embed.title
    assert "sus-hook" in embed.description

@pytest.mark.asyncio
async def test_voice_join_logs(mocker, mock_guild):
    """
    Verify voice join logging.
    """
    bot = MagicMock()
    cog = VoiceState(bot)

    member = MagicMock()
    member.bot = False
    member.guild = mock_guild
    member.mention = "@User"
    member.id = 123

    channel = MagicMock()
    channel.mention = "#vc"

    before = MagicMock()
    before.channel = None
    before.mute = before.deaf = False

    after = MagicMock()
    after.channel = channel
    after.mute = after.deaf = False

    mocker.patch.object(cog, "should_log", return_value=True)
    mock_log = mocker.patch.object(cog, "log_event", new_callable=AsyncMock)

    await cog.on_voice_state_update(member, before, after)

    mock_log.assert_called_once()

    embed = mock_log.call_args[0][1]
    assert "joined" in embed.description.lower()
    assert "#vc" in embed.description

# Suspicious Detector Tests

def test_suspicious_logic():
    # Test basic is_spam
    timestamps = deque()
    # Fill with 3 items now
    now = time.time()
    for _ in range(3):
        timestamps.append(now)
    
    # Threshold 4, window 10 -> False
    assert not suspicious_detector.is_spam(timestamps, 4, 10.0)

    # Add 4th -> True
    timestamps.append(now)
    assert suspicious_detector.is_spam(timestamps, 4, 10.0)
    
    # Test prune
    timestamps.clear()
    timestamps.append(now - 20) # Old
    timestamps.append(now) # New
    
    suspicious_detector.prune(timestamps, 10.0) # Window 10
    assert len(timestamps) == 1
    assert timestamps[0] == now

def test_check_ban_heuristic():
    guild_id = 123
    user_id = 999
    
    # Clear existing
    if guild_id in suspicious_detector.trackers:
        del suspicious_detector.trackers[guild_id]
        
    # Add 3 bans
    for _ in range(3):
        assert not suspicious_detector.check_member_ban(guild_id, user_id)
        
    # 4th ban -> suspicious
    assert suspicious_detector.check_member_ban(guild_id, user_id)

def test_check_kick_heuristic():
    guild_id = 123
    user_id = 888
    
    if guild_id in suspicious_detector.trackers:
        del suspicious_detector.trackers[guild_id]
        
    for _ in range(3):
        assert not suspicious_detector.check_member_kick(guild_id, user_id)
        
    assert suspicious_detector.check_member_kick(guild_id, user_id)

def test_cleanup_expired():
    guild_id = 456
    user_id = 777
    
    # Add activity
    suspicious_detector.check_member_kick(guild_id, user_id)
    assert guild_id in suspicious_detector.trackers
    
    # Force timestamps to be old
    tracker = suspicious_detector.trackers[guild_id][user_id]
    tracker.kicks.clear()
    tracker.kicks.append(time.time() - 10000)
    
    suspicious_detector.cleanup_expired(max_age_seconds=100)
    
    # Should be gone
    assert user_id not in suspicious_detector.trackers.get(guild_id, {})
