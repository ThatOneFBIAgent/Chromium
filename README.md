# Modular Discord Logger

A production-ready, modular, and sharding-safe Discord logger built with `discord.py` 2.0+.
Key features include per-guild isolated logging, suspicion heuristics, database log rotation (SQLite), and optional Google Drive integration.

## Features

- **Modular Logging**: 8+ distinct logging modules (Message Delete, Edit, Join, Leave, Voice, Role, Channel, Error) that can be enabled/disabled per guild.
- **Per-Guild Isolation**: Configurations and logs are strictly isolated.
- **Log Rotation**: Automatically keeps only the latest 50 logs per guild to save space.
- **Suspicious Activity Detection**: Detects spam deletes/edits/joins and flags them in logs.
- **Slash Commands**: Full setup and management via `/setup`, `/log`, and `/export`.
- **Exports**: Export logs to a JSON file, with optional Google Drive upload.
- **Blacklisting & Whitelisting**: Blacklist/Whitelist users, roles, channels from logging.
- **Sharding**: Built on `AutoShardedBot` for scalability.
- **Docker Ready**: Includes production-grade Dockerfile with non-root user.

## Structure

```
.
├── bot.py                  # Entry point
├── config.py               # Configuration management
├── database/               # Database layer (SQLite + Rotation Logic)
├── logging_modules/        # Independent logging modules
├── commands/               # Slash commands
├── utils/                  # Utilities (Logger, Drive, Suspicion)
├── Dockerfile              # Deployment
└── requirements.txt        # Dependencies
```

## Setup

### Prerequisites
- Python 3.11+
- Discord Bot Token (with Message Content, Server Members, and Presence Intents enabled)

### Local Run

1. **Clone the repository**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment**:
   Copy `.env.example` to `.env` and fill in your details.
   ```env
   DISCORD_TOKEN=your_token
   DRIVE_CREDS_B64=base64_encoded_service_account_json (Optional)
   DRIVE_FOLDER_ID=your_folder_id (Optional)
   ```
4. **Run the bot**:
   ```bash
   python bot.py
   ```

### Docker Run

1. **Build the image**:
   ```bash
   docker build -t discord-bot .
   ```
2. **Run the container**:
   ```bash
   docker run -d --name my-bot --env-file .env -v $(pwd)/data:/app/data discord-bot
   ```
   *Note: You might want to mount the database path if you change `DB_PATH` in `database/core.py` to a persistent volume location.*

### Railway
1.R **Deploy from github**
   Make sure it's uploaded a public or private repo, and that railway has access to it.
   Deploying should be as easy as adding the ENV variables and making sure `RAILPACK` is set.

   If any problems occur, check the logs and open an issue on github. I'll try my best to help you.

## Permissions

The bot requires the following permissions to function fully:
- **Manage Channels**: For `/setup complex`.
- **View Audit Log**: For more detailed logging (future expansion).
- **Send Messages / Embed Links**: For logging.
- **Manage Webhooks**: (Optional) if using webhook logging in future.

## Google Drive Integration

To enable export uploads:
1. Create a Google Cloud Service Account.
2. Download the JSON key.
3. Base64 encode the content of the JSON file:
   ```bash
   cat service-account.json | base64
   ```
4. Set the result as `DRIVE_CREDS_B64` in `.env`.
5. Share your target Drive folder with the Service Account email.
6. Set `DRIVE_FOLDER_ID` in `.env`.

## Sharding

The bot automatically uses `AutoShardedBot`. You can force a specific shard count using the `SHARD_COUNT` env var, but leaving it to default is recommended for most use cases.

### TODO:
- [ ] Make/copy a token helper for the google drive stuff
- [X] Add signal handlers for when Railways shuts the bot down
- this is mainly for housekeeping and immediately backing up the database
- [ ] Make the code a bit more readable
- [X] Make the logger more dynamic and actually colored

## License

This project is licensed under the GNUv3 License - see the [LICENSE](LICENSE) file for details.

## Contact/Support

If you have any questions or need support, feel free to open an issue on github. I'll try my best to help you.
Or you can contact me thru discord at `_izacarlos`
