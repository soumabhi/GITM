"""Keyboard events. The listener records kinds, never the letters."""

from __future__ import annotations

import logging

from pynput import keyboard

log = logging.getLogger(__name__)

_CTRL = {
    "\x03": "copy",
    "c": "copy",
    "\x16": "paste",
    "v": "paste",
    "\x18": "cut",
    "x": "cut",
    "\x1a": "undo",
    "z": "undo",
    "\x19": "redo",
    "y": "redo",
    "\x13": "save",
    "s": "save",
    "\x01": "select_all",
    "a": "select_all",
    "\x06": "find",
    "f": "find",
}


class KeyboardHook:
    def __init__(self, emit) -> None:
        self._emit = emit
        self._ctrl = False
        self._alt = False
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)

    def start(self) -> None:
        try:
            self._listener.start()
            log.info("Keyboard hook is up")
        except Exception:
            log.exception("Keyboard hook failed")

    def stop(self) -> None:
        try:
            self._listener.stop()
        except Exception:
            log.exception("Keyboard hook stop failed")

    def _on_press(self, key) -> None:
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self._ctrl = True
            return
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
            self._alt = True
            return
        self._emit("presence")
        if key == keyboard.Key.delete:
            self._emit("delete")
            return
        if key == keyboard.Key.backspace:
            self._emit("backspace")
            return
        if key == keyboard.Key.enter:
            self._emit("enter")
            return
        if key == keyboard.Key.esc:
            self._emit("escape")
            return
        if key == keyboard.Key.print_screen:
            self._emit("screenshot")
            return
        if key == keyboard.Key.tab and self._alt:
            self._emit("alt_tab")
            return
        if key == keyboard.Key.f4 and self._alt:
            self._emit("alt_f4")
            return
        char = getattr(key, "char", None)
        if isinstance(char, str):
            kind = _CTRL.get(char.lower()) if self._ctrl or char < " " else None
            if kind:
                self._emit(kind)
                return
        if char and char.isprintable() and not self._ctrl and not self._alt:
            self._emit("typing")

    def _on_release(self, key) -> None:
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self._ctrl = False
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
            self._alt = False
