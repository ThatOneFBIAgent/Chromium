# Rate Limiting and Event Queue for Discord API Calls
# Prevents 429 errors and provides graceful handling of burst activity

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from collections import deque
import discord
from utils.logger import get_logger

log = get_logger()

@dataclass
class QueuedEvent:
    """Represents a queued embed send operation."""
    guild_id: int
    channel_id: Optional[int]
    webhook_url: Optional[str]
    embed: discord.Embed
    created_at: float = field(default_factory=time.time)
    attempts: int = 0

class ExponentialBackoff:
    """
    Implements exponential backoff for retrying failed operations.
    Starts at base_delay (1s) and doubles up to max_delay (32s).
    """
    def __init__(self, base_delay: float = 1.0, max_delay: float = 32.0, max_attempts: int = 5):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_attempts = max_attempts
        self._attempt = 0
    
    def reset(self):
        self._attempt = 0
    
    def get_delay(self) -> float:
        """Get the delay for the current attempt."""
        delay = min(self.base_delay * (2 ** self._attempt), self.max_delay)
        self._attempt += 1
        return delay
    
    @property
    def attempts_exhausted(self) -> bool:
        return self._attempt >= self.max_attempts

class EventQueue:
    """
    Async queue for batching Discord API calls.
    Processes events with rate limiting and exponential backoff.
    """
    def __init__(self, bot, max_queue_size: int = 500, batch_delay: float = 0.5):
        self.bot = bot
        self.queue: deque[QueuedEvent] = deque(maxlen=max_queue_size)
        self.batch_delay = batch_delay
        self._processing = False
        self._task: Optional[asyncio.Task] = None
        self._failed_webhooks: set[str] = set()  # Track webhooks that have failed
        
    def enqueue(self, event: QueuedEvent):
        """Add an event to the queue."""
        self.queue.append(event)
        log.trace(f"[Queue] Enqueued event for guild {event.guild_id}, queue size: {len(self.queue)}")
        
    def start_processing(self):
        """Start the background queue processor."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._process_loop())
            log.info("[Queue] Started event queue processor")
    
    def stop_processing(self):
        """Stop the background queue processor."""
        if self._task and not self._task.done():
            self._task.cancel()
            log.info("[Queue] Stopped event queue processor")
    
    async def _process_loop(self):
        """Main loop that processes queued events."""
        while True:
            try:
                if not self.queue:
                    await asyncio.sleep(self.batch_delay)
                    continue
                
                event = self.queue.popleft()
                await self._send_event(event)
                
                # Small delay between sends to prevent bursting
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                log.info("[Queue] Processing loop cancelled")
                break
            except Exception as e:
                log.error(f"[Queue] Error in processing loop: {e}")
                await asyncio.sleep(1.0)
    
    async def _send_event(self, event: QueuedEvent) -> bool:
        """
        Send a single event with exponential backoff.
        Returns True if successful, False otherwise.
        """
        backoff = ExponentialBackoff()
        
        while not backoff.attempts_exhausted:
            try:
                return await self._try_send(event)
            except discord.RateLimited as e:
                # 429 - TRUST THE RETRY_AFTER
                # Add a small buffer (0.1s) to be safe
                delay = e.retry_after + 0.1
                log.warning(f"[Queue] Rate limited (bucket: {e.bucket}), retry after {delay:.2f}s")
                await asyncio.sleep(delay)
                # Do NOT consume an attempt count for forced rate limits, just wait
                # But to prevent infinite loops, we might assume the backoff limiter handles it if we used it,
                # here we just sleep and continue loop.
                continue
                
            except discord.HTTPException as e:
                if e.status == 429: # Should be caught by RateLimited but just in case
                    delay = backoff.get_delay()
                    log.warning(f"[Queue] HTTP 429, backing off for {delay:.1f}s")
                    await asyncio.sleep(delay)
                    
                elif e.status in (408, 500, 502, 503, 504): # Retriable Server Errors
                    delay = backoff.get_delay()
                    log.warning(f"[Queue] Server error {e.status}, backing off for {delay:.1f}s")
                    await asyncio.sleep(delay)
                    
                elif e.status in (401, 403, 404, 410): # Fatal Errors
                    log.warning(f"[Queue] Fatal error {e.status} (Forbidden/Not Found/Gone). Stopping.")
                    # If it was a webhook, mark as failed
                    if event.webhook_url:
                        self._failed_webhooks.add(event.webhook_url)
                    return False
                    
                else:
                    log.error(f"[Queue] Unexpected HTTP error {e.status}: {e.text}")
                    return False
            except Exception as e:
                log.error(f"[Queue] Unexpected error sending event: {e}")
                return False
        
        log.error(f"[Queue] Exhausted retries for guild {event.guild_id}")
        return False

    async def _try_send(self, event: QueuedEvent) -> bool:
        """Attempt to send via webhook or channel."""
        # Try webhook first if available and not known to be failed
        if event.webhook_url and event.webhook_url not in self._failed_webhooks:
            try:
                webhook = discord.Webhook.from_url(
                    event.webhook_url, 
                    session=self.bot.http_session, 
                    client=self.bot
                )
                await webhook.send(embed=event.embed)
                return True
            except discord.NotFound:
                # Webhook is dead, mark it and fall through to channel send
                self._failed_webhooks.add(event.webhook_url)
                log.warning(f"[Queue] Webhook marked as failed: {event.webhook_url[:50]}...")
        
        # Fall back to channel send
        if event.channel_id:
            guild = self.bot.get_guild(event.guild_id)
            if guild:
                channel = guild.get_channel(event.channel_id)
                if channel:
                    await channel.send(embed=event.embed)
                    return True
        
        return False
    
    def is_webhook_failed(self, webhook_url: str) -> bool:
        """Check if a webhook is known to be failed."""
        return webhook_url in self._failed_webhooks
    
    def clear_failed_webhook(self, webhook_url: str):
        """Clear a webhook from the failed list (e.g., after reconfiguration)."""
        self._failed_webhooks.discard(webhook_url)


async def send_with_backoff(
    coro_factory: Callable[[], Any],
    max_attempts: int = 5,
    base_delay: float = 1.0
) -> tuple[bool, Optional[Exception]]:
    """
    Execute a coroutine with exponential backoff on rate limits.
    
    Args:
        coro_factory: A callable that returns a new coroutine each time (lambda: channel.send(...))
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        
    Returns:
        Tuple of (success: bool, last_exception: Optional[Exception])
    """
    backoff = ExponentialBackoff(base_delay=base_delay, max_attempts=max_attempts)
    last_error = None
    
    while not backoff.attempts_exhausted:
        try:
            await coro_factory()
            return True, None
            
        except discord.RateLimited as e:
            # Handle explicit rate limit exception
            delay = e.retry_after + 0.1
            log.warning(f"[Backoff] Rate limited, waiting {delay:.2f}s")
            await asyncio.sleep(delay)
            # Reset backoff attempt if we want to be generous, or just continue
            continue
            
        except discord.HTTPException as e:
            last_error = e
            
            if e.status == 429:
                delay = backoff.get_delay()
                log.warning(f"[Backoff] HTTP 429, waiting {delay:.1f}s")
                await asyncio.sleep(delay)
                
            elif e.status in (408, 500, 502, 503, 504):
                delay = backoff.get_delay()
                log.warning(f"[Backoff] HTTP {e.status}, waiting {delay:.1f}s")
                await asyncio.sleep(delay)
                
            elif e.status in (401, 403, 404, 410):
                log.warning(f"[Backoff] Fatal HTTP {e.status}, aborting.")
                return False, e
                
            else:
                return False, e
                
        except Exception as e:
            return False, e
    
    return False, last_error


# Singleton instance - initialized by bot startup
event_queue: Optional[EventQueue] = None

def init_event_queue(bot) -> EventQueue:
    """Initialize the global event queue with the bot instance."""
    global event_queue
    event_queue = EventQueue(bot)
    event_queue.start_processing()
    return event_queue

def get_event_queue() -> Optional[EventQueue]:
    """Get the global event queue instance."""
    return event_queue
