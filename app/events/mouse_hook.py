"""Drag detection and candy clicks. Positions are not stored."""

from __future__ import annotations

import logging
import time

from pynput import mouse

log = logging.getLogger(__name__)


class MouseHook:
    def __init__(self, emit, hit_test, on_drag=None, occupies=None, blocks_drag=None) -> None:
        self._emit = emit
        self._hit_test = hit_test
        self._on_drag = on_drag
        self._occupies = occupies
        self._blocks_drag = blocks_drag
        self._down: tuple[int, int, float] | None = None
        self._fired = False
        self._last_emit = 0.0
        self._last_presence = 0.0
        self._last_xy: tuple[int, int] | None = None
        self._click_times: list[float] = []
        self._pet_at: tuple[int, int] | None = None
        self._listener = mouse.Listener(on_click=self._on_click, on_move=self._on_move, on_scroll=self._on_scroll)

    def start(self) -> None:
        try:
            self._listener.start()
            log.info("Mouse hook is up")
        except Exception:
            log.exception("Mouse hook failed")

    def stop(self) -> None:
        try:
            self._listener.stop()
        except Exception:
            log.exception("Mouse hook stop failed")

    def _note_presence(self, now: float) -> None:
        if now - self._last_presence < 0.15:
            return
        self._last_presence = now
        self._emit("presence")

    def _on_click(self, x, y, button, pressed) -> None:
        self._note_presence(time.monotonic())
        if button != mouse.Button.left:
            return
        if pressed:
            if self._blocked(int(x), int(y)):
                self._down = None
                self._fired = False
                return
            self._down = (int(x), int(y), time.monotonic())
            self._fired = False
            return
        # Triple-click (not a drag) toggles the pet on/off at that spot.
        if self._down is not None and not self._fired and not pressed:
            now = time.monotonic()
            x0, y0, _started = self._down
            self._click_times = [stamp for stamp in self._click_times if now - stamp <= 0.5]
            self._click_times.append(now)
            if len(self._click_times) >= 3:
                self._pet_at = (x0, y0)
                self._emit("pet")
                self._click_times = []
        self._down = None
        self._fired = False

    def _blocked(self, x: int, y: int) -> bool:
        if self._blocks_drag and self._blocks_drag():
            return True
        if self._occupies and self._occupies(x, y):
            return True
        return False

    def _on_move(self, x, y) -> None:
        now = time.monotonic()
        point = (int(x), int(y))
        if self._last_xy is not None:
            px, py = self._last_xy
            if (point[0] - px) ** 2 + (point[1] - py) ** 2 >= 16:
                self._last_xy = point
                self._note_presence(now)
        else:
            self._last_xy = point
        if self._down is None:
            return
        if self._blocked(point[0], point[1]):
            self._down = None
            self._fired = False
            return
        if self._fired:
            if now - self._last_emit >= 0.25:
                self._last_emit = now
                self._emit("move")
                if self._on_drag:
                    self._on_drag()
            return
        x0, y0, started = self._down
        if now - started > 0.6:
            return
        if (x - x0) ** 2 + (y - y0) ** 2 >= 50**2:
            self._fired = True
            self._last_emit = now
            self._emit("move")
            if self._on_drag:
                self._on_drag()

    def _on_scroll(self, x, y, dx, dy) -> None:
        del x, y, dx, dy
        now = time.monotonic()
        self._note_presence(now)
        if now - self._last_emit < 0.25:
            return
        self._last_emit = now
        self._emit("scroll")
