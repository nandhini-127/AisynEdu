import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List, Tuple
from app.core.config import settings


class LoginRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter for login attempts.
    Tracks failed attempts per identity (IP address or user email).
    """

    def __init__(self):
        self._lock = Lock()
        self._attempts: Dict[str, List[float]] = defaultdict(list)

    def _cleanup_expired(self, key: str, window_seconds: int, now: float) -> None:
        threshold = now - window_seconds
        self._attempts[key] = [ts for ts in self._attempts[key] if ts > threshold]
        if not self._attempts[key]:
            del self._attempts[key]

    def is_rate_limited(
        self,
        key: str,
        max_attempts: int = settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
        window_seconds: int = settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    ) -> Tuple[bool, int]:
        """
        Checks whether the specified key is currently rate-limited.
        Returns: (is_limited, seconds_until_reset)
        """
        now = time.time()
        with self._lock:
            self._cleanup_expired(key, window_seconds, now)
            timestamps = self._attempts.get(key, [])
            if len(timestamps) >= max_attempts:
                oldest = timestamps[0]
                retry_after = max(1, int(window_seconds - (now - oldest)))
                return True, retry_after
            return False, 0

    def record_failure(
        self,
        key: str,
        window_seconds: int = settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    ) -> None:
        """Records a failed attempt."""
        now = time.time()
        with self._lock:
            self._cleanup_expired(key, window_seconds, now)
            self._attempts[key].append(now)

    def reset(self, key: str) -> None:
        """Clears all recorded failures for a key upon successful login."""
        with self._lock:
            if key in self._attempts:
                del self._attempts[key]

    def clear_all(self) -> None:
        """Clears all tracked keys (primarily used in testing)."""
        with self._lock:
            self._attempts.clear()


login_rate_limiter = LoginRateLimiter()

