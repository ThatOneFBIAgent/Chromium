import os
import base64
import json
from enum import Enum
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"

class Config:
    def __init__(self):
        self.DISCORD_TOKEN = self._get_required("DISCORD_TOKEN") # i really need a way to differiantiate between beta and prod tokens
        self.GUI_TEST_MODE = os.getenv("GUI_TEST_MODE", "false").lower() == "true"
        self.ENVIRONMENT = Environment(os.getenv("ENVIRONMENT", "development"))
        
        # Google Drive
        self.DRIVE_CREDS_B64 = os.getenv("DRIVE_CREDS_B64")
        self.DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
        
        # Deployment Environment Checks
        self.IS_RAILWAY = os.getenv("RAILWAY_ENVIRONMENT") is not None
        
        # Sharding defaults (can be overridden by args if needed, but nice to have here)
        self.SHARD_COUNT = int(os.getenv("SHARD_COUNT", "1")) # Default to AutoSharded logic usually, but sometimes explicit

    def _get_required(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            # In a real scenario we might stop, but for now we log and raise
            raise ValueError(f"Missing required environment variable: {key}")
        return value

    def get_drive_creds(self) -> Optional[dict]:
        """Decodes the Base64 Google Drive Service Account credentials."""
        if not self.DRIVE_CREDS_B64:
            return None
        
        try:
            # Clean potential whitespace/newlines which might break loose base64 parsers
            clean_b64 = self.DRIVE_CREDS_B64.strip().replace('\n', '').replace(' ', '')
            
            decoded = base64.b64decode(clean_b64).decode('utf-8')
            return json.loads(decoded)
        except Exception as e:
            print(f"[ERROR] Failed to decode DRIVE_CREDS_B64: {e}")
            return None

# Singleton instance
shared_config = Config()
