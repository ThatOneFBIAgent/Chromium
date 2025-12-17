import logging
import sys
from datetime import datetime
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

class CustomFormatter(logging.Formatter):
    """
    Custom formatter with color coding for different levels/tags.
    tags: ERROR, NETWORK, DISCORD, DATABASE
    """
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.MAGENTA + Style.BRIGHT,
        'NETWORK': Fore.BLUE,
        'DISCORD': Fore.MAGENTA,
        'DATABASE': Fore.CYAN
    }

    def format(self, record: logging.LogRecord) -> str:
        # Determine color based on custom tags or level
        tag = getattr(record, 'tag', record.levelname)
        color = self.COLORS.get(tag, Fore.WHITE)
        
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Structure: [TIMESTAMP] [TAG] Message
        log_fmt = f"{Style.DIM}[{timestamp}]{Style.RESET_ALL} {color}[{tag}]{Style.RESET_ALL} %(message)s"
        
        if record.exc_info:
            # If there's an exception, add it formatted
            return logging.Formatter(log_fmt).format(record)
        
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def setup_logger(name: str = "Bot") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CustomFormatter())
    
    if not logger.handlers:
        logger.addHandler(handler)
        
    return logger

# Global logger instance
logger = setup_logger("Core")

# Helper functions for specific tags
def log_network(msg: str):
    logger.info(msg, extra={'tag': 'NETWORK'})

def log_discord(msg: str):
    logger.info(msg, extra={'tag': 'DISCORD'})

def log_database(msg: str):
    logger.info(msg, extra={'tag': 'DATABASE'})

def log_error(msg: str, exc_info=None):
    logger.error(msg, exc_info=exc_info, extra={'tag': 'ERROR'})
