import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class ActivityTracker:
    deletes: deque = field(default_factory=lambda: deque(maxlen=20))
    edits: deque = field(default_factory=lambda: deque(maxlen=20))
    joins: deque = field(default_factory=lambda: deque(maxlen=20))
    bans: deque = field(default_factory=lambda: deque(maxlen=20))
    kicks: deque = field(default_factory=lambda: deque(maxlen=20))

class SuspiciousDetector:
    def __init__(self):
        # Nested dicts: guild_id -> user_id -> ActivityTracker
        self.trackers: Dict[int, Dict[int, ActivityTracker]] = defaultdict(lambda: defaultdict(ActivityTracker))
        self.guild_joins: Dict[int, deque] = defaultdict(lambda: deque(maxlen=20)) # Track joins per guild specifically

    def is_spam(self, timestamps: deque, threshold_count: int, time_window: float) -> bool:
        if len(timestamps) < threshold_count:
            return False
            
        recent = [t for t in timestamps if time.time() - t < time_window]
        return len(recent) >= threshold_count

    def prune(self, timestamps: deque, time_window: float):
        cutoff = time.time() - time_window
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()

    def check_message_delete(self, guild_id: int, user_id: int) -> bool:
        tracker = self.trackers[guild_id][user_id]
        tracker.deletes.append(time.time())
        # Heuristic: 5 deletes in 10 seconds
        return self.is_spam(tracker.deletes, 5, 10.0)

    def check_message_edit(self, guild_id: int, user_id: int) -> bool:
        tracker = self.trackers[guild_id][user_id]
        tracker.edits.append(time.time())
        # Heuristic: 5 edits in 10 seconds
        return self.is_spam(tracker.edits, 5, 10.0)

    def check_member_join(self, guild_id: int) -> bool:
        # Check for raid (many joins in short time)
        self.guild_joins[guild_id].append(time.time())
        # Heuristic: 10 joins in 20 seconds
        return self.is_spam(self.guild_joins[guild_id], 10, 20.0)

    def check_member_ban(self, guild_id: int, user_id: int) -> bool:
        tracker = self.trackers[guild_id][user_id]
        tracker.bans.append(time.time())
        # Heuristic: 4 bans in 10 seconds
        return self.is_spam(tracker.bans, 4, 10.0)

    def check_member_kick(self, guild_id: int, user_id: int) -> bool:
        tracker = self.trackers[guild_id][user_id]
        tracker.kicks.append(time.time())
        # Heuristic: 4 kicks in 10 seconds
        return self.is_spam(tracker.kicks, 4, 10.0)
    
    def cleanup_expired(self, max_age_seconds: float = 3600.0):
        # Clean up user trackers
        for guild_id in list(self.trackers.keys()):
            guild_trackers = self.trackers[guild_id]
            for user_id in list(guild_trackers.keys()):
                tracker = guild_trackers[user_id]
                
                self.prune(tracker.deletes, max_age_seconds)
                self.prune(tracker.edits, max_age_seconds)
                self.prune(tracker.joins, max_age_seconds)
                self.prune(tracker.bans, max_age_seconds)
                self.prune(tracker.kicks, max_age_seconds)
                
                # If all empty, remove tracker
                if not any((tracker.deletes, tracker.edits, tracker.joins, tracker.bans, tracker.kicks)):
                    del guild_trackers[user_id]
            
            if not guild_trackers:
                del self.trackers[guild_id]

        # Clean up guild joins
        for guild_id in list(self.guild_joins.keys()):
            self.prune(self.guild_joins[guild_id], max_age_seconds)
            if not self.guild_joins[guild_id]:
                del self.guild_joins[guild_id]

suspicious_detector = SuspiciousDetector()
