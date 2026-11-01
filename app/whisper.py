"""One-line whispers from local Gemma. Never blocks, never saves the line."""

from __future__ import annotations

import json
import logging
import random
import threading
import time
from pathlib import Path

import requests

log = logging.getLogger(__name__)


def load_fallback_lines(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = []
    lines = [str(item).strip() for item in data if str(item).strip()]
    return lines or ["The machine is not empty."]


def fallback_line(lines: list[str]) -> str:
    return random.choice(lines)


def ask_gemma(url: str, model: str, event: str, mood: str, timeout_s: float, topic: str = "") -> str:
    subject = " ".join(str(topic or "").split())[:180]
    about = f" Say one random thought about this subject: {subject}." if subject else ""
    prompt = (
        "You are a tiny ghost inside a computer. "
        "Reply with ONE spooky sentence under 12 words."
        f"{about} "
        f"The moment is: {event}. The mood is: {mood}. "
        "Do not ask questions. Do not mention private text."
    )
    response = requests.post(
        f"{url.rstrip('/')}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "30m",
            "options": {"num_ctx": 512, "num_predict": 24},
        },
        timeout=timeout_s,
    )
    response.raise_for_status()
    text = str(response.json().get("response", "")).strip().replace("\n", " ")
    if not text:
        raise ValueError("empty whisper")
    return text[:140]


class Whisperer:
    """Calls Gemma on a daemon thread and reports (line, source)."""

    def __init__(self, url: str, model: str, timeout_s: float, min_interval_s: float, lines: list[str], on_line) -> None:
        self.url = url
        self.model = model
        self.timeout_s = timeout_s
        self.min_interval_s = min_interval_s
        self.lines = lines
        self.on_line = on_line
        self._last = 0.0
        self._lock = threading.Lock()

    def request(self, event: str, mood: str, topic: str = "", fresh: bool = False) -> bool:
        now = time.monotonic()
        with self._lock:
            if not fresh and now - self._last < self.min_interval_s:
                return False
            self._last = now
        threading.Thread(target=self._run, args=(event, mood, topic), name="whisper", daemon=True).start()
        return True

    def _run(self, event: str, mood: str, topic: str = "") -> None:
        source = self.model
        try:
            line = ask_gemma(self.url, self.model, event, mood, self.timeout_s, topic)
        except Exception:
            log.info("Gemma whisper unavailable; using a local fallback line")
            line = fallback_line(self.lines)
            source = "fallback"
        try:
            self.on_line(line, source)
        except Exception:
            log.warning("Whisper could not reach the window")
