import pytest
import discord
from unittest.mock import AsyncMock, MagicMock
from logging_modules.base import BaseLogger

# Configurable Test Table
# Logic:
# 1- User Whitelist (Allow)
# 2 - User Blacklist (Block)
# 3 - Channel Whitelist (Allow)
# 4 - Role Whitelist (Allow)
# 5 - Channel Blacklist (Block)
# 6 - Role Blacklist (Block)
# 7 - Default (Allow)

# Format: (Description, UserID, ChannelID, UserRoles, DB_Items, Expected_Result)
TEST_SCENARIOS = [
    (
        "No Lists - Default Allow",
        100, 200, [], 
        [], 
        True
    ),
    (
        "1. User Whitelist - Should Log",
        100, 200, [],
        [{'guild_id': 1, 'list_type': 'whitelist', 'entity_type': 'user', 'entity_id': 100}],
        True
    ),
    (
        "2. User Blacklist - Should Block",
        100, 200, [],
        [{'guild_id': 1, 'list_type': 'blacklist', 'entity_type': 'user', 'entity_id': 100}],
        False
    ),
    (
        "2. User Blacklist vs 3. Channel Whitelist - Block wins (User BL > Channel WL)",
        100, 200, [],
        [
            {'guild_id': 1, 'list_type': 'blacklist', 'entity_type': 'user', 'entity_id': 100},
            {'guild_id': 1, 'list_type': 'whitelist', 'entity_type': 'channel', 'entity_id': 200}
        ],
        False
    ),
    (
        "3. Channel Whitelist - Should Log (Overrides Role BL)",
        100, 200, [555], # 555 is Role BL
        [
            {'guild_id': 1, 'list_type': 'blacklist', 'entity_type': 'role', 'entity_id': 555},
            {'guild_id': 1, 'list_type': 'whitelist', 'entity_type': 'channel', 'entity_id': 200}
        ],
        True
    ),
    (
        "4. Role Whitelist - Should Log (Overrides Channel BL)",
        100, 200, [777], # 200 is Chan BL, 777 is Role WL
        [
             {'guild_id': 1, 'list_type': 'blacklist', 'entity_type': 'channel', 'entity_id': 200},
             {'guild_id': 1, 'list_type': 'whitelist', 'entity_type': 'role', 'entity_id': 777}
        ],
        True
    ),
    (
        "5. Channel Blacklist - Should Block",
        100, 200, [],
        [{'guild_id': 1, 'list_type': 'blacklist', 'entity_type': 'channel', 'entity_id': 200}],
        False
    ),
    (
        "6. Role Blacklist - Should Block",
        100, 200, [555],
        [{'guild_id': 1, 'list_type': 'blacklist', 'entity_type': 'role', 'entity_id': 555}],
        False
    ),
    (
        "1. User Whitelist overrides 2. User Blacklist (Wait, User WL > User BL)",
        100, 200, [],
        [
            {'guild_id': 1, 'list_type': 'blacklist', 'entity_type': 'user', 'entity_id': 100},
            {'guild_id': 1, 'list_type': 'whitelist', 'entity_type': 'user', 'entity_id': 100}
        ],
        True
    ),
        (
        "Duplicate User Whitelist entries should not change behavior",
        100, 200, [],
        [
            {'guild_id': 1, 'list_type': 'whitelist', 'entity_type': 'user', 'entity_id': 100},
            {'guild_id': 1, 'list_type': 'whitelist', 'entity_type': 'user', 'entity_id': 100}
        ],
        True
    ),

    (
        "Unknown Guild Rules Ignored",
        100, 200, [],
        [
            {'guild_id': 999, 'list_type': 'blacklist', 'entity_type': 'user', 'entity_id': 100}
        ],
        True
    ),

    (
        "Invalid Entry Without entity_type Should Not Crash And Should Ignore",
        100, 200, [],
        [
            {'guild_id': 1, 'list_type': 'blacklist', 'entity_id': 100}
        ],
        True
    ),
    (
        "Default Deny Mode - No Lists Should Allow (Bot is Opt-Out)",
        100, 200, [],
        [],
        True
    ),
    
    (
        "Conflicting Roles - Role Whitelist beats Role Blacklist (As per 7-step)",
        100, 200, [555, 777],
        [
            {'guild_id': 1, 'list_type': 'whitelist', 'entity_type': 'role', 'entity_id': 777},
            {'guild_id': 1, 'list_type': 'blacklist', 'entity_type': 'role', 'entity_id': 555}
        ],
        True 
    ),

    (
        "User Whitelist beats Role Blacklist",
        100, 200, [555],
        [
            {'guild_id': 1, 'list_type': 'blacklist', 'entity_type': 'role', 'entity_id': 555},
            {'guild_id': 1, 'list_type': 'whitelist', 'entity_type': 'user', 'entity_id': 100}
        ],
        True
    ),

    (
        "User Blacklist beats Role Whitelist",
        100, 200, [777],
        [
            {'guild_id': 1, 'list_type': 'whitelist', 'entity_type': 'role', 'entity_id': 777},
            {'guild_id': 1, 'list_type': 'blacklist', 'entity_type': 'user', 'entity_id': 100}
        ],
        False
    )
]

@pytest.mark.asyncio
@pytest.mark.parametrize("desc, uid, cid, roles, db_items, expected", TEST_SCENARIOS)
async def test_should_log_scenarios(mocker, mock_guild, mock_user, mock_channel, desc, uid, cid, roles, db_items, expected):
    """
    Data-driven test for BaseLogger.should_log
    """
    # Setup Mock Data
    mock_user.id = uid
    mock_channel.id = cid
    
    mock_roles = []
    for r_id in roles:
        r = MagicMock(spec=discord.Role)
        r.id = r_id
        mock_roles.append(r)
    mock_user.roles = mock_roles
    
    # Mock the DB call in BaseLogger
    mock_get_all = mocker.patch("logging_modules.base.get_all_list_items", new_callable=AsyncMock)
    mock_get_all.return_value = db_items
    
    # Initialize Logger
    bot = MagicMock()
    logger = BaseLogger(bot)
    
    # Act
    result = await logger.should_log(mock_guild, user=mock_user, channel=mock_channel)
    
    # Assert
    assert result == expected, f"Failed Scenario: {desc}"
