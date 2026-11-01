"""Per-event cooldowns. Time is passed in so tests do not sleep."""

from __future__ import annotations


class CooldownGate:
    def __init__(self, cooldowns_ms: dict[str, int]) -> None:
        self._seconds = {name: max(0, int(ms)) / 1000 for name, ms in cooldowns_ms.items()}
        self._last: dict[str, float] = {}

    def allow(self, event: str, now: float) -> bool:
        wait = self._seconds.get(event, 1.0)
        previous = self._last.get(event)
        if previous is not None and (now - previous) < wait:
            return False
        self._last[event] = now
        return True

    def clear(self) -> None:
        self._last.clear()
