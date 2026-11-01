"""Date-based Halloween and Día de los Muertos touches."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


ORANGE = (255, 140, 0)
RED = (170, 20, 20)


@dataclass(frozen=True)
class Theme:
    tint: tuple[int, int, int] | None
    tooltip: str
    pumpkin: bool
    marigold: bool
    halloween_badge: bool


def theme_for(now: datetime) -> Theme:
    if now.month == 10 and now.day == 31:
        tint = RED if now.hour >= 18 else ORANGE
        return Theme(tint, "Halloween Mode", True, False, True)
    if (now.month, now.day) in {(11, 1), (11, 2)}:
        return Theme(None, "Dia de los Muertos", False, False, False)
    return Theme(None, "", False, False, False)


def parse_preview(value: str, fallback: datetime) -> datetime:
    text = (value or "").strip()
    if not text:
        return fallback
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if fmt == "%Y-%m-%d":
            return parsed.replace(hour=fallback.hour, minute=fallback.minute, second=fallback.second)
        return parsed
    return fallback
