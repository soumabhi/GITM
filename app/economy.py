"""Ectoplasm, mood, candy, and one-time badges. Stored as counts only."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

BADGES: tuple[tuple[str, str], ...] = (
    ("chatterbox", "100 typing moments"),
    ("echo", "5 pastes"),
    ("gravekeeper", "10 deletes"),
    ("poltergeist", "10 moves"),
    ("lights_out", "300 quiet seconds"),
    ("first_haunting", "the first reaction"),
    ("halloween_haunter", "a reaction on October 31"),
)

EVENTS = (
    "typing",
    "copy",
    "paste",
    "delete",
    "move",
    "pet",
    "cut",
    "undo",
    "redo",
    "save",
    "select_all",
    "find",
    "enter",
    "backspace",
    "escape",
    "screenshot",
    "click",
    "right_click",
    "double_click",
    "scroll",
    "new_file",
    "rename",
    "download",
    "alt_tab",
    "alt_f4",
    "idle",
)


def mood_for(ectoplasm: int) -> str:
    if ectoplasm <= 0:
        return "dormant"
    if ectoplasm < 10:
        return "restless"
    if ectoplasm < 30:
        return "haunted"
    return "possessed"


def fresh_state() -> dict:
    return {
        "ectoplasm": 0,
        "mood": "dormant",
        "candy": 0,
        "counters": {name: 0 for name in EVENTS},
        "badges": [],
        "bytes_freed": 0,
        "idle_seconds": 0,
    }


@dataclass
class Economy:
    path: Path
    state: dict

    @classmethod
    def load(cls, path: Path) -> Economy:
        state = fresh_state()
        if path.exists():
            try:
                saved = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                saved = {}
            if isinstance(saved, dict):
                state.update({key: saved[key] for key in state if key in saved})
                counters = dict(fresh_state()["counters"])
                counters.update(saved.get("counters") or {})
                state["counters"] = {name: int(counters.get(name, 0)) for name in EVENTS}
                state["badges"] = [name for name in saved.get("badges", []) if isinstance(name, str)]
        state["mood"] = mood_for(int(state["ectoplasm"]))
        return cls(path, state)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def record(self, event: str) -> None:
        if event not in self.state["counters"]:
            return
        self.state["counters"][event] = int(self.state["counters"][event]) + 1
        self.state["ectoplasm"] = int(self.state["ectoplasm"]) + 1
        self.state["mood"] = mood_for(int(self.state["ectoplasm"]))
        self.state["idle_seconds"] = 0

    def add_candy(self) -> None:
        self.state["candy"] = int(self.state["candy"]) + 1

    def add_freed(self, nbytes: int) -> None:
        self.state["bytes_freed"] = int(self.state["bytes_freed"]) + max(0, int(nbytes))

    def tick_idle(self, seconds: int = 1) -> None:
        self.state["idle_seconds"] = int(self.state["idle_seconds"]) + max(0, seconds)

    def newly_unlocked(self, now: datetime) -> list[str]:
        owned = set(self.state["badges"])
        counters = self.state["counters"]
        reactions = sum(int(counters[name]) for name in EVENTS)
        halloween = now.month == 10 and now.day == 31 and reactions >= 1
        checks = {
            "chatterbox": int(counters["typing"]) >= 100,
            "echo": int(counters["paste"]) >= 5,
            "gravekeeper": int(counters["delete"]) >= 10,
            "poltergeist": int(counters["move"]) >= 10,
            "lights_out": int(self.state["idle_seconds"]) >= 300,
            "first_haunting": reactions >= 1,
            "halloween_haunter": halloween,
        }
        fresh = [name for name, ok in checks.items() if ok and name not in owned]
        if fresh:
            self.state["badges"] = [*self.state["badges"], *fresh]
        return fresh

    def reset(self) -> None:
        self.state = fresh_state()
        self.save()

    def tooltip(self, extra: str = "") -> str:
        text = (
            f"GITM | Ectoplasm: {self.state['ectoplasm']} | "
            f"Mood: {self.state['mood']} | "
            f"Badges: {len(self.state['badges'])}/7 | "
            f"Candy: {self.state['candy']}"
        )
        if extra:
            text = f"{text} | {extra}"
        return text
