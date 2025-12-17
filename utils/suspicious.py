import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class ActivityTracker:
    deletes: deque = field(default_factory=lambda: deque(maxlen=20))
    edits: deque = field(default_factory=lambda: deque(maxlen=20))
    joins: deque = field(default_factory=lambda: deque(maxlen=20))

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

suspicious_detector = SuspiciousDetector()
