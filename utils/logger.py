import logging
import sys
import os
import inspect
from datetime import datetime
from config import shared_config, Environment

# custom log levels
SUCCESS_LEVEL = 25
EVENT_LEVEL = 15
TRACE_LEVEL = 12
DATABASE_LEVEL = 19
NETWORK_LEVEL = 18
DISCORD_LEVEL = 17 

logging.SUCCESS_LEVEL = SUCCESS_LEVEL
logging.EVENT_LEVEL = EVENT_LEVEL
logging.DATABASE_LEVEL = DATABASE_LEVEL
logging.NETWORK_LEVEL = NETWORK_LEVEL
logging.DISCORD_LEVEL = DISCORD_LEVEL
logging.TRACE_LEVEL = TRACE_LEVEL

logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")
logging.addLevelName(EVENT_LEVEL, "EVENT")
logging.addLevelName(DATABASE_LEVEL, "DATABASE")
logging.addLevelName(NETWORK_LEVEL, "NETWORK")
logging.addLevelName(DISCORD_LEVEL, "DISCORD")
logging.addLevelName(TRACE_LEVEL, "TRACE")

class ColoredFormatter(logging.Formatter):
    COLORS = {
        TRACE_LEVEL: "\033[90m",                    # gray
        logging.DEBUG: "\033[90m",                  # gray
        logging.INFO: "\033[36m",                   # cyan
        DATABASE_LEVEL: "\033[35m",                 # purple
        DISCORD_LEVEL: "\033[35m",                  # purple
        EVENT_LEVEL: "\033[96m",                    # light blue
        NETWORK_LEVEL: "\033[34m",                  # blue
        SUCCESS_LEVEL: "\033[32m",                  # green text
        logging.WARNING: "\033[33m",                # yellow
        logging.ERROR: "\033[31m",                  # red
        logging.CRITICAL: "\033[41;97m",            # red bg with white text
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, "")
        
        # Dynamic Time Formatting
        if shared_config.IS_RAILWAY:
            # Show relative time (uptime) in ms truncated to 3 last digits
            ms = int(record.relativeCreated) % 1000
            time_str = f"{ms:03d}ms"
        else:
            # Show full timestamp for local debugging
            time_str = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')

        # Auto-context: simplify module path
        # If the logger name is set (via get_logger), usually we trust it?
        # But if we want to enforce the file-path logic regardless:
        module_path = record.pathname.replace(os.getcwd(), "").lstrip(os.sep)
        module_parts = module_path.split(os.sep)
        
        if len(module_parts) > 1:
            module_parts[-1] = os.path.splitext(module_parts[-1])[0]
        
        module_name = ".".join(p for p in module_parts if p and p != "__init__")
        
        # In Flurazide, get_logger sets the logger name. 
        # The formatter here uses the pathname to derive context dynamically. 
        # Ideally, we primarily use the logger name if it's meaningful, but the path fallback is robust.
        # Let's stick to the path fallback for consistency.
        
        formatted = f"[{time_str}] [{record.levelname:^8}] [{module_name}] {record.getMessage()}"

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            if record.exc_text:
                formatted += "\n" + record.exc_text

        return f"{color}{formatted}{self.RESET}"

# Configure root/base settings (so get_logger childs inherit or reuse)
# We won't set a root logger here to avoid conflicts, just a factory function.

def get_logger(name=None) -> logging.Logger:
    """
    Smart logger factory.
    Auto-detects the caller's module/filename if name is not provided.
    """
    if not name:
        # Inspect call stack
        try:
            frame = inspect.stack()[1]
            module = inspect.getmodule(frame[0])
            if module and hasattr(module, '__name__') and module.__name__ not in ("__main__",):
                name = module.__name__
            else:
                 # fallback to file-based path
                path = frame.filename.replace(os.getcwd(), "").lstrip(os.sep)
                parts = path.split(os.sep)
                parts[-1] = os.path.splitext(parts[-1])[0]
                name = ".".join(parts)
        except Exception:
            name = "Chromium"

    logger = logging.getLogger(name)
    logger.setLevel(logging.TRACE_LEVEL if shared_config.ENVIRONMENT == Environment.DEVELOPMENT else logging.EVENT_LEVEL)
    
    # Check if handler exists to avoid duplicates
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColoredFormatter())
        logger.addHandler(handler)
        
    return logger

# Add convenience methods to Logger class
def trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE_LEVEL):
        kwargs.setdefault('stacklevel', 2)
        self._log(TRACE_LEVEL, message, args, **kwargs)

def success(self, message, *args, **kwargs):
    if self.isEnabledFor(SUCCESS_LEVEL):
        kwargs.setdefault('stacklevel', 2)
        self._log(SUCCESS_LEVEL, message, args, **kwargs)

def event(self, message, *args, **kwargs):
    if self.isEnabledFor(EVENT_LEVEL):
        kwargs.setdefault('stacklevel', 2)
        self._log(EVENT_LEVEL, message, args, **kwargs)

def database(self, message, *args, **kwargs):
    if self.isEnabledFor(DATABASE_LEVEL):
        kwargs.setdefault('stacklevel', 2)
        self._log(DATABASE_LEVEL, message, args, **kwargs)

def network(self, message, *args, **kwargs):
    if self.isEnabledFor(NETWORK_LEVEL):
        kwargs.setdefault('stacklevel', 2)
        self._log(NETWORK_LEVEL, message, args, **kwargs)

def discord_log(self, message, *args, **kwargs):
    if self.isEnabledFor(DISCORD_LEVEL):
        kwargs.setdefault('stacklevel', 2)
        self._log(DISCORD_LEVEL, message, args, **kwargs)

# Wire up methods
logging.Logger.trace = trace
logging.Logger.success = success
logging.Logger.event = event
logging.Logger.database = database
logging.Logger.network = network
logging.Logger.discord = discord_log

# Legacy/Global instance for backward compat (files that import `logger`)
# We use a default one. 
logger = get_logger("Global")

# Helper functions that match previous API (proxies to the global logger)
def log_network(msg: str):
    logger.network(msg, stacklevel=2)

def log_discord(msg: str):
    logger.discord(msg, stacklevel=2)

def log_database(msg: str):
    logger.database(msg, stacklevel=2)

def log_error(msg: str, exc_info=None):
    logger.error(msg, exc_info=exc_info, stacklevel=2)
