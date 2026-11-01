"""Clipboard change backup for copy. The text is hashed in memory and dropped."""

from __future__ import annotations

import hashlib

import pyperclip


class ClipboardWatch:
    def __init__(self) -> None:
        self._last = ""
        self._ready = False

    def poll(self, keyboard_copy_recent: bool) -> str | None:
        try:
            text = pyperclip.paste()
        except Exception:
            return None
        digest = hashlib.sha256(text.encode("utf-8", "replace")).hexdigest() if text else ""
        if not self._ready:
            self._last = digest
            self._ready = True
            return None
        if digest == self._last:
            return None
        self._last = digest
        if not digest or keyboard_copy_recent:
            return None
        return "copy"
