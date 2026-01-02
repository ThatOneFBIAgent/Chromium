import pytest
import discord
from unittest.mock import AsyncMock, MagicMock
from logging_modules.member_join import MemberJoin
from logging_modules.message_delete import MessageDelete

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
