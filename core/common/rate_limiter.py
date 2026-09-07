import threading
import time


class InteractionRateLimiter:
    """Thread-safe rate limiter for UI interactions and Discord commands."""

    def __init__(self, default_cooldown: float = 2.5):
        self.default_cooldown = default_cooldown
        self._lock = threading.Lock()
        self._last_interaction: dict[tuple[int, str], float] = {}

    def is_limited(self, user_id: int, action: str, cooldown: float | None = None) -> tuple[bool, float]:
        """Checks whether the given user is rate limited for the action.
        Returns:
            (is_limited: bool, remaining_seconds: float)
        """
        cooldown_sec = cooldown if cooldown is not None else self.default_cooldown
        now = time.monotonic()
        key = (user_id, action)

        with self._lock:
            # Clean expired keys if dictionary grows large
            if len(self._last_interaction) > 5000:
                cutoff = now - 60.0
                self._last_interaction = {k: v for k, v in self._last_interaction.items() if v > cutoff}

            last_time = self._last_interaction.get(key, 0.0)
            elapsed = now - last_time

            if elapsed < cooldown_sec:
                remaining = cooldown_sec - elapsed
                return True, round(remaining, 1)

            self._last_interaction[key] = now
            return False, 0.0

    def reset(self, user_id: int | None = None, action: str | None = None) -> None:
        """Resets rate limiting state."""
        with self._lock:
            if user_id is None and action is None:
                self._last_interaction.clear()
            else:
                to_delete = [
                    k
                    for k in self._last_interaction
                    if (user_id is None or k[0] == user_id) and (action is None or k[1] == action)
                ]
                for k in to_delete:
                    del self._last_interaction[k]


__all__ = ["InteractionRateLimiter"]
