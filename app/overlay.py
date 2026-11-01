"""Transparent, click-through ghost window."""

from __future__ import annotations

import math
import random
import time

from PIL import Image
from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QFont, QFontDatabase, QFontMetrics, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

def pil_to_pixmap(image: Image.Image) -> QPixmap:
    image = image.convert("RGBA")
    buffer = image.tobytes("raw", "RGBA")
    qimage = QImage(buffer, image.width, image.height, QImage.Format.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimage)


class _Flash(QWidget):
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(180, 20, 20, 80))
        painter.end()


def _click_through(widget: QWidget) -> None:
    """Pass clicks through. Do not touch WS_EX_LAYERED — Qt owns per-pixel alpha."""
    import ctypes

    hwnd = int(widget.winId())
    if not hwnd or not ctypes.windll.user32.IsWindow(hwnd):
        return
    gwl_exstyle = -20
    ws_ex_transparent = 0x00000020
    ws_ex_toolwindow = 0x00000080
    style = ctypes.windll.user32.GetWindowLongW(hwnd, gwl_exstyle)
    # OR-ing WS_EX_LAYERED (0x80000) here makes the translucent window go blank on Windows.
    ctypes.windll.user32.SetWindowLongW(hwnd, gwl_exstyle, style | ws_ex_transparent | ws_ex_toolwindow)
    swp_nosize = 0x0001
    swp_nomove = 0x0002
    swp_nozorder = 0x0004
    swp_framechanged = 0x0020
    ctypes.windll.user32.SetWindowPos(
        hwnd,
        0,
        0,
        0,
        0,
        0,
        swp_nosize | swp_nomove | swp_nozorder | swp_framechanged,
    )


class GhostOverlay(QWidget):
    def __init__(self, size: int = 192, margin: int = 16, play_ms: int = 2500, hold_ms: int = 500, fade_ms: int = 300, corner: str = "top-right") -> None:
        super().__init__()
        self._size = size
        self._margin = margin
        self._corner = corner if corner in {"top-right", "bottom-right"} else "top-right"
        self._strength = 1.0
        self._across = 100.0
        self._down = 0.0
        self._base_play_ms = play_ms
        self._play_ms = play_ms
        self._pace = 1.0
        self._hold_ms = hold_ms
        self._fade_ms = max(1, fade_ms)
        self._frames: list[QPixmap] = []
        self._sources: list[Image.Image] = []
        self._frame_index = 0
        self._caption = ""
        self._source = ""
        self._phase = "hidden"
        self._phase_at = 0.0
        self._marigold = False
        self._opacity = 1.0
        self._frame_w = size
        self._frame_h = size
        self._sprite_x = 0
        self._preview_until = 0.0
        self._say = None
        self._fit_key = None
        self._full = ""
        self._shown = 0
        self._typed_at = 0.0
        self._caret = True
        self._caret_at = 0.0
        self._line_done_at = 0.0
        self._live = False
        self._active_until = 0.0
        self._frame_clock = 0.0
        self._awaiting_line = False
        self._await_until = 0.0
        self._swarm = False
        self._leaving = False
        self._push = False
        self._push_until = 0.0
        self._copies: list[dict] = []
        self._swarm_clock = 0.0
        self._visit = ""
        self._visit_at = 0.0
        self._visit_follow_until = 0.0
        self._home_across = 100.0
        self._home_down = 80.0
        self.setFixedSize(size, size)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._flash = _Flash()
        self._flash.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self._flash.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._flash.hide)
        self._place()

    def _pixel_ratio(self) -> float:
        screen = QApplication.primaryScreen()
        ratio = screen.devicePixelRatio() if screen is not None else 1.0
        return ratio if ratio > 0 else 1.0

    def _place(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        char_w = max(1, self._frame_w)
        char_h = max(1, self._frame_h)
        span_x = max(0, area.width() - char_w)
        span_y = max(0, area.height() - char_h)
        char_x = area.left() + round(span_x * self._across / 100)
        char_y = area.top() + round(span_y * self._down / 100)
        x = char_x - self._sprite_x
        y = char_y
        x = min(max(area.left(), x), max(area.left(), area.right() - self.width() + 1))
        y = min(max(area.top(), y), max(area.top(), area.bottom() - self.height() + 1))
        self.move(x, y)

    def apply_look(self, size: int, opacity: float, across: float, down: float) -> None:
        self._size = max(80, min(420, int(size)))
        self._strength = max(0.2, min(1.0, float(opacity)))
        self._across = max(0.0, min(100.0, float(across)))
        self._down = max(0.0, min(100.0, float(down)))
        if self._sources and self._phase != "hidden":
            self._present(self._sources, restart=False, fast=True)
        elif self._phase != "hidden":
            self.setWindowOpacity(self._opacity * self._strength)
            self._place()

    def live_look(self, size: int, opacity: float, across: float, down: float, frames: list[Image.Image] | None = None, say: str | None = None) -> None:
        self._size = max(80, min(420, int(size)))
        self._strength = max(0.2, min(1.0, float(opacity)))
        self._across = max(0.0, min(100.0, float(across)))
        self._down = max(0.0, min(100.0, float(down)))
        if frames:
            ready = [frame.convert("RGBA") for frame in frames if frame is not None]
            if ready:
                self._sources = ready
        line_on = bool(self._full) and self._phase != "hidden"
        self._live = not line_on
        if say is not None and say != self._say:
            self._say = say
        if not self._sources:
            return
        key = (self._size, round(self._pixel_ratio(), 2), 1 if str(self._caption or "").strip() else 0)
        if key != self._fit_key or not self._frames or self._phase == "hidden":
            self._fit_key = key
            self._present(self._sources, restart=False, fast=True)
        else:
            self.setWindowOpacity(self._opacity * self._strength)
            self._place()
            self.show()
        if line_on:
            self.update()
            return
        self._opacity = 1.0
        self._phase = "holding"
        self._preview_until = time.monotonic() + 1.2
        if not self._timer.isActive():
            self._timer.start(33)
        self.update()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        _click_through(self)

    def play(self, frames: list[Image.Image], tint: tuple[int, int, int] | None, caption: str = "", source: str = "") -> None:
        del tint
        ready = [frame.convert("RGBA") for frame in frames if frame is not None]
        if not ready:
            self._frames = []
            self._sources = []
            return
        self._visit = ""
        self._sources = ready
        self._caption = ""
        self._full = ""
        self._shown = 0
        self._line_done_at = 0.0
        self._live = False
        self._source = source
        self._awaiting_line = False
        self._frame_clock = 0.0
        self._present(ready, restart=True)
        if self._swarm:
            self._fill_copies()
        self.note_activity()

    def start_visit(self, frames: list[Image.Image], home_across: float, home_down: float) -> None:
        """Come from a fixed home, hang by the mouse, then leave."""
        ready = [frame.convert("RGBA") for frame in frames if frame is not None]
        if not ready:
            return
        self._swarm = False
        self._leaving = False
        self._push = False
        self._copies = []
        self._home_across = max(0.0, min(100.0, float(home_across)))
        self._home_down = max(0.0, min(100.0, float(home_down)))
        self._across = self._home_across
        self._down = self._home_down
        self._sources = ready
        self._caption = ""
        self._full = ""
        self._shown = 0
        self._line_done_at = 0.0
        self._live = False
        self._source = ""
        self._awaiting_line = False
        self._frame_clock = 0.0
        self._visit = "approach"
        self._visit_at = time.monotonic()
        self._visit_follow_until = 0.0
        self._present(ready, restart=True)
        self._active_until = time.monotonic() + 12.0
        self.note_activity()
        self._active_until = time.monotonic() + 12.0

    def _present(self, ready: list[Image.Image], restart: bool, fast: bool = False) -> None:
        native = ready[0].size
        logical_h = max(80, self._size)
        logical_w = max(1, round(native[0] * logical_h / max(1, native[1])))
        bubble = 0 if self._swarm else (262 if str(self._caption or "").strip() else 0)
        self._frame_w = logical_w
        self._frame_h = logical_h
        self._sprite_x = bubble
        if self._swarm:
            area = self._screen_area()
            if area is not None:
                self.setFixedSize(area.width(), area.height())
                self.move(area.left(), area.top())
        else:
            self.setFixedSize(logical_w + bubble, logical_h)
        pixel_w = max(1, round(logical_w * 2))
        pixel_h = max(1, round(logical_h * 2))
        resample = Image.Resampling.BILINEAR if fast else Image.Resampling.LANCZOS
        prepared = []
        for frame in ready:
            if frame.size != (pixel_w, pixel_h):
                frame = frame.resize((pixel_w, pixel_h), resample)
            pixmap = pil_to_pixmap(frame)
            prepared.append(pixmap)
        self._frames = prepared
        if restart:
            self._frame_index = 0
            self._phase = "playing"
            self._phase_at = time.monotonic()
            self._opacity = 1.0
            self._preview_until = 0.0
            self._timer.start(33)
        self.setWindowOpacity(self._opacity * self._strength)
        if self._swarm:
            if len(self._copies) < 5:
                self._fill_copies()
        elif self._push and time.monotonic() < self._push_until:
            self._stick()
        else:
            self._place()
        self.show()
        self.raise_()
        self.update()

    def _begin_line(self, caption: str) -> None:
        self._full = str(caption or "")
        self._shown = 0
        self._line_done_at = 0.0
        self._typed_at = time.monotonic()
        self._caret = True
        self._caret_at = self._typed_at
        self._caption = self._full
        self._fit_key = None

    def set_push(self, enabled: bool) -> None:
        self._push = bool(enabled)
        if not self._push:
            self._push_until = 0.0

    def shove(self) -> None:
        self._push = True
        self._push_until = time.monotonic() + 0.45
        if self._phase != "hidden":
            self._stick()

    def _stick(self) -> None:
        area = self._screen_area()
        if area is None:
            return
        cursor = QCursor.pos()
        x = cursor.x() + 16 - self._sprite_x
        y = cursor.y() - self._frame_h // 2
        x = min(max(area.left(), x), max(area.left(), area.right() - self.width() + 1))
        y = min(max(area.top(), y), max(area.top(), area.bottom() - self.height() + 1))
        self.move(x, y)

    def set_pace(self, speed: int) -> None:
        self._pace = max(0.25, min(2.0, int(speed) / 100))

    def set_swarm(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._swarm:
            return
        self._leaving = False
        self._swarm = enabled
        self._copies = []
        self._swarm_clock = 0.0
        if not enabled and self._phase != "hidden" and self._sources:
            self._present(self._sources, restart=False, fast=True)

    def begin_leave(self) -> None:
        if self._leaving:
            return
        if not self._swarm or self._phase == "hidden" or not self._copies:
            self.end_swarm()
            return
        self._leaving = True
        kinds = ["fade", "shrink", "pop", "fly", "drop", "spin", "rise"]
        random.shuffle(kinds)
        now = time.monotonic()
        wait = 0.0
        for index, copy in enumerate(self._copies):
            copy["leave_at"] = now + wait
            copy["leave_kind"] = kinds[index % len(kinds)]
            copy["leave_dur"] = random.uniform(0.5, 0.9)
            copy["spin"] = random.choice((-1, 1))
            angle = random.uniform(0, math.tau)
            copy["fly"] = (math.cos(angle) * random.uniform(320, 560), math.sin(angle) * random.uniform(220, 480))
            wait += random.uniform(0.32, 0.5)
        if not self._timer.isActive():
            self._timer.start(33)

    def end_swarm(self) -> None:
        self._swarm = False
        self._leaving = False
        self._copies = []
        self._swarm_clock = 0.0
        if self._phase != "hidden":
            self.hide_ghost()

    def _screen_area(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            return None
        return screen.availableGeometry()

    def _aim(self, copy: dict) -> None:
        width = max(1, self.width())
        height = max(1, self.height())
        span_x = max(1, width - self._frame_w)
        span_y = max(1, height - self._frame_h)
        copy["x"] = random.uniform(0, span_x)
        copy["y"] = random.uniform(0, span_y)
        angle = random.uniform(0, math.tau)
        speed = random.uniform(80, 170)
        copy["vx"] = math.cos(angle) * speed
        copy["vy"] = math.sin(angle) * speed

    def _fill_copies(self) -> None:
        count = 5
        frames = max(1, len(self._frames))
        order = list(range(frames))
        random.shuffle(order)
        now = time.monotonic()
        self._copies = []
        self._swarm_clock = now
        for index in range(count):
            copy = {
                "frame": order[index % frames],
                "frame_at": now - random.uniform(0, 0.4),
                "pace": random.uniform(0.7, 1.4),
                "alpha": 1.0,
                "scale": 1.0,
                "rot": 0.0,
            }
            self._aim(copy)
            self._copies.append(copy)

    def _advance_copy(self, copy: dict, now: float) -> None:
        if not self._frames:
            return
        gap = (self._base_play_ms / 1000) / len(self._frames) / max(0.25, self._pace) / max(0.5, copy.get("pace", 1))
        if now - copy.get("frame_at", now) < gap:
            return
        jumps = int((now - copy["frame_at"]) / gap)
        copy["frame"] = (int(copy.get("frame", 0)) + jumps) % len(self._frames)
        copy["frame_at"] = copy.get("frame_at", now) + jumps * gap

    def _drift(self, now: float) -> None:
        if self._leaving or not self._swarm or not self._copies or self._phase == "hidden":
            return
        if self._swarm_clock <= 0:
            self._swarm_clock = now
            return
        step = min(0.05, max(0.0, now - self._swarm_clock))
        self._swarm_clock = now
        width = self.width()
        height = self.height()
        for copy in self._copies:
            self._advance_copy(copy, now)
            copy["x"] += copy["vx"] * step
            copy["y"] += copy["vy"] * step
            if copy["x"] > width or copy["y"] > height or copy["x"] + self._frame_w < 0 or copy["y"] + self._frame_h < 0:
                held = copy["frame"]
                pace = copy.get("pace", 1)
                self._aim(copy)
                copy["frame"] = held
                copy["pace"] = pace

    def _step_leave(self, now: float) -> None:
        if self._swarm_clock <= 0:
            self._swarm_clock = now
        step = min(0.05, max(0.0, now - self._swarm_clock))
        self._swarm_clock = now
        alive: list[dict] = []
        for copy in self._copies:
            self._advance_copy(copy, now)
            start = copy.get("leave_at", now)
            if now < start:
                copy["x"] += copy["vx"] * step
                copy["y"] += copy["vy"] * step
                alive.append(copy)
                continue
            if "leave_x" not in copy:
                copy["leave_x"] = copy["x"]
                copy["leave_y"] = copy["y"]
            span = max(0.2, float(copy.get("leave_dur", 0.6)))
            done = (now - start) / span
            if done >= 1:
                continue
            kind = copy.get("leave_kind", "fade")
            ox = copy["leave_x"]
            oy = copy["leave_y"]
            if kind == "shrink":
                copy["scale"] = max(0.04, 1 - done)
                copy["alpha"] = 1.0
            elif kind == "pop":
                copy["scale"] = 1 + 0.85 * done
                copy["alpha"] = 1 - done
            elif kind == "fly":
                fx, fy = copy.get("fly", (400, 0))
                copy["x"] = ox + fx * done
                copy["y"] = oy + fy * done
                copy["alpha"] = 1 - done
            elif kind == "drop":
                copy["y"] = oy + 340 * done * done
                copy["alpha"] = 1 - done
                copy["rot"] = copy.get("spin", 1) * 30 * done
            elif kind == "spin":
                copy["rot"] = copy.get("spin", 1) * 240 * done
                copy["scale"] = max(0.04, 1 - 0.55 * done)
                copy["alpha"] = 1 - done
            elif kind == "rise":
                copy["y"] = oy - 180 * done
                copy["scale"] = max(0.04, 1 - 0.2 * done)
                copy["alpha"] = 1 - done
            else:
                copy["alpha"] = 1 - done
            alive.append(copy)
        self._copies = alive

    def is_showing(self) -> bool:
        return self._phase != "hidden" and bool(self._frames)

    def writing(self) -> bool:
        return self._writing()

    def note_activity(self) -> None:
        self._active_until = time.monotonic() + (self._base_play_ms / 1000)
        if self._phase == "fading":
            self._phase = "holding"
            self._opacity = 1.0
            self.setWindowOpacity(self._strength)
            self.show()
        if self._phase != "hidden" and not self._timer.isActive():
            self._timer.start(33)

    def expect_line(self) -> None:
        self._awaiting_line = True
        self._await_until = time.monotonic() + 50.0

    def adopt(self, frames: list[Image.Image]) -> None:
        ready = [frame.convert("RGBA") for frame in frames if frame is not None]
        if self._phase == "hidden" or not self._frames:
            if ready:
                self.play(ready, None)
            return
        self.note_activity()
        if not ready:
            return
        self._sources = ready
        if self._phase == "fading":
            self._phase = "holding"
            self._opacity = 1.0
        self._present(ready, restart=False, fast=True)
        if self._frames and self._frame_index >= len(self._frames):
            self._frame_index = 0
        self.setWindowOpacity(self._strength)

    def _writing(self) -> bool:
        return bool(self._full) and self._shown < len(self._full)

    def _reveal(self, now: float) -> None:
        gap = 0.03
        if self._shown < len(self._full) and now - self._typed_at >= gap:
            step = max(1, int((now - self._typed_at) / gap))
            self._shown = min(len(self._full), self._shown + step)
            self._typed_at = now
            if self._shown >= len(self._full) and not self._line_done_at:
                self._line_done_at = now
        elif self._full and self._shown >= len(self._full) and not self._line_done_at:
            self._line_done_at = now

    def set_caption(self, caption: str, source: str) -> None:
        self._awaiting_line = False
        self._source = source
        self._live = False
        self._begin_line(caption)
        if not self._sources:
            self.update()
            return
        if self._phase == "hidden":
            self._opacity = 1.0
            self._phase = "holding"
        self._present(self._sources, restart=False, fast=True)
        self._fit_key = (self._size, round(self._pixel_ratio(), 2), 1 if str(self._caption or "").strip() else 0)
        self._preview_until = max(self._preview_until, time.monotonic() + 2.6 + len(self._full) * 0.03)
        if self._phase != "playing":
            self._phase = "holding"
            self._opacity = 1.0
            self.setWindowOpacity(self._strength)
        if not self._timer.isActive():
            self._timer.start(33)
        self.update()

    def set_marigold(self, enabled: bool) -> None:
        del enabled
        self._marigold = False
        if self._phase == "hidden":
            self.hide()

    def quiet(self) -> None:
        self._awaiting_line = False
        self._full = ""
        self._caption = ""
        self._shown = 0
        self._line_done_at = 0.0
        if self._phase == "hidden" or not self._sources:
            return
        self._present(self._sources, restart=False, fast=True)

    def hide_ghost(self) -> None:
        self._phase = "hidden"
        self._frames = []
        self._caption = ""
        self._full = ""
        self._shown = 0
        self._line_done_at = 0.0
        self._awaiting_line = False
        self._active_until = 0.0
        self._leaving = False
        self._swarm = False
        self._push = False
        self._push_until = 0.0
        self._copies = []
        self._visit = ""
        self._visit_at = 0.0
        self._visit_follow_until = 0.0
        self._timer.stop()
        self._preview_until = 0.0
        self._fit_key = None
        self.setWindowOpacity(1.0)
        self.hide()

    def _cursor_percent(self) -> tuple[float, float]:
        area = self._screen_area()
        if area is None:
            return self._across, self._down
        cursor = QCursor.pos()
        across = (cursor.x() - area.x()) / max(1, area.width()) * 100
        down = (cursor.y() - area.y()) / max(1, area.height()) * 100
        return max(0.0, min(100.0, across)), max(0.0, min(100.0, down))

    def _lerp_toward(self, target_x: float, target_y: float, step: float) -> float:
        dx = target_x - self._across
        dy = target_y - self._down
        dist = math.hypot(dx, dy)
        if dist <= 0.01:
            self._across = target_x
            self._down = target_y
            self._place()
            return 0.0
        move = min(dist, step)
        self._across += dx / dist * move
        self._down += dy / dist * move
        self._place()
        return dist - move

    def _step_visit(self, now: float) -> bool:
        if not self._visit:
            return False
        if self._visit == "approach":
            tx, ty = self._cursor_percent()
            # Sit a little behind/beside the cursor, not on top of it.
            tx = max(0.0, min(100.0, tx - 6))
            ty = max(0.0, min(100.0, ty + 4))
            left = self._lerp_toward(tx, ty, 3.2)
            self._active_until = max(self._active_until, now + 1.0)
            if left <= 2.5 or now - self._visit_at > 4.0:
                self._visit = "follow"
                self._visit_at = now
                self._visit_follow_until = now + 2.8
            self._stay()
            return True
        if self._visit == "follow":
            tx, ty = self._cursor_percent()
            tx = max(0.0, min(100.0, tx - 5))
            ty = max(0.0, min(100.0, ty + 3))
            self._lerp_toward(tx, ty, 4.5)
            self._active_until = max(self._active_until, now + 0.6)
            if now >= self._visit_follow_until:
                self._visit = "leave"
                self._visit_at = now
            self._stay()
            return True
        if self._visit == "leave":
            left = self._lerp_toward(self._home_across, self._home_down, 3.6)
            self._active_until = max(self._active_until, now + 0.4)
            if left <= 2.0 or now - self._visit_at > 3.5:
                self._visit = ""
                self.hide_ghost()
            else:
                self._stay()
            return True
        return False

    def bounds(self) -> tuple[int, int, int, int]:
        if not self.isVisible() or self._phase == "hidden":
            return (0, 0, 0, 0)
        origin = self.mapToGlobal(QPoint(0, 0))
        return (origin.x(), origin.y(), self.width(), self.height())

    def flash(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        self._flash.setGeometry(screen.geometry())
        self._flash.show()
        _click_through(self._flash)
        self._flash.update()
        self._flash_timer.start(150)

    def _advance_frames(self, now: float) -> None:
        if not self._frames or self._phase == "hidden":
            return
        gap = (self._base_play_ms / 1000) / max(1, len(self._frames)) / max(0.25, self._pace)
        if self._frame_clock <= 0:
            self._frame_clock = now
            return
        elapsed = now - self._frame_clock
        if elapsed < gap:
            return
        jumps = int(elapsed / gap)
        self._frame_index = (self._frame_index + jumps) % len(self._frames)
        self._frame_clock += jumps * gap

    def _stay(self) -> None:
        self._opacity = 1.0
        self.setWindowOpacity(self._strength)
        if self._phase == "fading":
            self._phase = "holding"
        self.show()
        self.update()

    def _fade(self, now: float, started: float) -> None:
        if self._phase != "fading":
            self._phase = "fading"
            self._phase_at = started
        done = (now - self._phase_at) / (self._fade_ms / 1000)
        if done >= 1:
            self.hide_ghost()
            return
        self._opacity = max(0.0, 1.0 - done)
        self.setWindowOpacity(self._opacity * self._strength)
        self.update()

    def _tick(self) -> None:
        now = time.monotonic()
        if self._phase == "hidden":
            return
        if self._visit and self._step_visit(now):
            self._advance_frames(now)
            return
        if self._push and now < self._push_until and not self._swarm and not self._leaving:
            self._stick()
        if self._leaving:
            self._step_leave(now)
            if not self._copies:
                self._leaving = False
                self._swarm = False
                self.hide_ghost()
                return
            self._opacity = 1.0
            self.setWindowOpacity(self._strength)
            self.update()
            return
        self._drift(now)
        if self._awaiting_line and now >= self._await_until:
            self._awaiting_line = False
        self._reveal(now)
        self._advance_frames(now)
        active = now < self._active_until
        if active or self._writing() or self._awaiting_line:
            self._stay()
            return
        if self._full and self._line_done_at:
            if now - self._line_done_at < 2.0:
                self._stay()
                return
            self._fade(now, self._line_done_at + 2.0)
            return
        if self._preview_until and now < self._preview_until:
            self._phase = "holding"
            self._opacity = 1.0
            self.setWindowOpacity(self._strength)
            self.update()
            return
        if self._active_until and now >= self._active_until and not self._full:
            self._fade(now, self._active_until)
            return
        if self._preview_until and now >= self._preview_until and self._phase == "holding":
            self._preview_until = 0.0
            self._fade(now, now)
            return
        if self._phase == "fading":
            self._fade(now, self._phase_at)
            return
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        if self._caption and self._phase != "hidden" and not self._leaving:
            self._draw_bubble(painter)
        if self._frames and self._phase != "hidden":
            if (self._swarm or self._leaving) and self._copies:
                for copy in self._copies:
                    frame = self._frames[int(copy.get("frame", 0)) % len(self._frames)]
                    painter.save()
                    painter.setOpacity(max(0.0, float(copy.get("alpha", 1))) * max(0.0, self._opacity))
                    center_x = float(copy["x"]) + self._frame_w / 2
                    center_y = float(copy["y"]) + self._frame_h / 2
                    painter.translate(center_x, center_y)
                    painter.rotate(float(copy.get("rot", 0)))
                    scale = max(0.04, float(copy.get("scale", 1)))
                    painter.scale(scale, scale)
                    painter.translate(-self._frame_w / 2, -self._frame_h / 2)
                    painter.drawPixmap(QRect(0, 0, self._frame_w, self._frame_h), frame)
                    painter.restore()
            else:
                frame = self._frames[min(self._frame_index, len(self._frames) - 1)]
                painter.drawPixmap(QRect(self._sprite_x, 0, self._frame_w, self._frame_h), frame)
        painter.end()

    def _mono(self) -> QFont:
        families = set(QFontDatabase.families())
        name = next((item for item in ("JetBrains Mono", "Cascadia Mono", "Cascadia Code", "Consolas") if item in families), "Consolas")
        font = QFont(name)
        font.setPixelSize(15)
        font.setStyleHint(QFont.StyleHint.Monospace)
        return font

    def _wrap(self, text: str, metrics: QFontMetrics, width: int) -> list[str]:
        lines: list[str] = []
        for paragraph in (text or "").split("\n"):
            current = ""
            for word in paragraph.split(" "):
                trial = word if not current else f"{current} {word}"
                if not current or metrics.horizontalAdvance(trial) <= width:
                    current = trial
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
        return lines or [""]

    def _draw_bubble(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        font = self._mono()
        metrics = QFontMetrics(font)
        text = self._full[: self._shown]
        text_width = 194
        lines = self._wrap(text, metrics, text_width)
        line_h = round(15 * 1.45)
        box_h = max(96, 16 + len(lines) * line_h + 18)
        anchor = self.height() // 2 if self._swarm else int(self._frame_h * 0.36)
        top = max(8, min(anchor - box_h // 2, max(8, self.height() - box_h - 8)))
        rect = QRect(8, top, 230, box_h)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 28))
        painter.drawRoundedRect(rect.adjusted(0, 6, 0, 8), 18, 18)
        painter.setBrush(QColor("#121110"))
        painter.drawRoundedRect(rect, 18, 18)
        tail_top = max(rect.top() + 16, min(anchor - 7, rect.bottom() - 22))
        painter.drawPolygon([QPoint(rect.right() - 1, tail_top), QPoint(rect.right() + 10, tail_top + 7), QPoint(rect.right() - 1, tail_top + 14)])
        painter.setPen(QPen(QColor("#f4efe4")))
        painter.setFont(font)
        y = rect.top() + 16 + metrics.ascent()
        for line in lines:
            painter.drawText(rect.left() + 18, y, line)
            y += line_h
