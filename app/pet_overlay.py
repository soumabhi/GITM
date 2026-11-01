"""The pet window. Drag it to park it. It can walk to the mouse."""

from __future__ import annotations

import math
import time

from PIL import Image, ImageDraw
from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QBitmap, QColor, QCursor, QFont, QImage, QPainter, QPixmap, QRegion
from PySide6.QtWidgets import QApplication, QWidget

from app.overlay import pil_to_pixmap

_CARE = (
    ("meal", "Meal"),
    ("snack", "Snack"),
    ("light", "Light"),
    ("play", "Play"),
    ("clean", "Clean"),
    ("medicine", "Medicine"),
    ("scold", "Scold"),
)
_BAR = 48


def _placeholder(kind: str) -> Image.Image:
    size = 160
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    body = (28, 36, size - 28, size - 18)
    if kind == "egg":
        draw.ellipse((40, 22, size - 40, size - 16), fill=(244, 239, 228, 255))
    elif kind == "die":
        draw.ellipse(body, fill=(210, 208, 202, 180))
    else:
        draw.ellipse(body, fill=(244, 239, 228, 255))
        draw.ellipse((58, 70, 74, 86), fill=(28, 27, 24, 255))
        draw.ellipse((96, 70, 112, 86), fill=(28, 27, 24, 255))
    return image


class PetOverlay(QWidget):
    parked = Signal(float, float)
    care = Signal(str)
    dragging = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._sources: list[Image.Image] | None = None
        self._run_sources: list[Image.Image] | None = None
        self._fitted = 0
        self._frames: list[QPixmap] = []
        self._run: list[QPixmap] = []
        self._index = 0
        self._frame_at = 0.0
        self._gap = 0.3
        self._mode = "home"
        self._home = (72.0, 62.0)
        self._buttons: list[tuple[str, QRect]] = []
        self._game = False
        self._game_label = ""
        self._need = ""
        self._poops = 0
        self._sick = False
        self._lights = True
        self._size = 160
        self._drag: QPoint | None = None
        self._pressed = ""
        self._mask_key = None
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self.hide()

    def bounds(self) -> tuple[int, int, int, int]:
        if not self.isVisible():
            return (0, 0, 0, 0)
        geo = self.frameGeometry()
        return (geo.x(), geo.y(), geo.width(), geo.height())

    def set_scene(
        self,
        frames: list[Image.Image],
        run_frames: list[Image.Image],
        mode: str,
        home: tuple[float, float],
        buttons: bool,
        game: bool,
        game_label: str,
        need: str,
        poops: int,
        sick: bool,
        lights: bool,
        size: int,
        opacity: float,
        pace: float,
    ) -> None:
        self._mode = mode if mode in {"home", "follow", "call"} else "home"
        self._home = home
        self._game = game
        self._game_label = game_label
        self._need = need
        self._poops = poops
        self._sick = sick
        self._lights = lights
        self._size = max(80, min(420, int(size)))
        self.setWindowOpacity(max(0.2, min(1.0, float(opacity))))
        pace_gap = max(0.05, (2.5 / max(1, len(frames))) / max(0.25, min(2.0, pace)))
        self._gap = pace_gap
        refit = self._fitted != self._size
        if frames is not self._sources or refit:
            self._sources = frames
            self._fitted = self._size
            ready = frames or [_placeholder("idle")]
            self._frames = [pil_to_pixmap(self._fit(frame)) for frame in ready]
            self._index = 0
            self._mask_key = None
            self._run_sources = None
        if run_frames:
            if run_frames is not self._run_sources:
                self._run_sources = run_frames
                self._run = [pil_to_pixmap(self._fit(frame)) for frame in run_frames]
                self._mask_key = None
        elif self._run:
            self._run_sources = None
            self._run = []
            self._mask_key = None
        width = max(self._size + 24, 640 if buttons or game else self._size + 24)
        height = self._size + 16 + (_BAR + 22 if buttons or game else 0)
        if self.width() != width or self.height() != height:
            self.setFixedSize(width, height)
            self._mask_key = None
        if not self.isVisible():
            self._go_home()
            self.show()
        self._fit_mask()
        self.update()

    def _fit(self, image: Image.Image) -> Image.Image:
        image = image.convert("RGBA")
        scale = self._size / max(1, max(image.size))
        size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        resample = Image.Resampling.NEAREST if max(image.size) <= 256 else Image.Resampling.LANCZOS
        return image.resize(size, resample)

    def hide_pet(self) -> None:
        if self._drag is not None:
            self._drag = None
            self.dragging.emit(False)
        self.hide()

    def is_dragging(self) -> bool:
        return self._drag is not None

    def _sprite_origin(self, frame: QPixmap) -> QPoint:
        x = max(0, (self.width() - frame.width()) // 2)
        return QPoint(x, 8)

    def _tick(self) -> None:
        if not self.isVisible() or self._drag is not None:
            return
        now = time.monotonic()
        if now - self._frame_at >= self._gap:
            self._frame_at = now
            if self._frames:
                self._index = (self._index + 1) % len(self._frames)
                self._mask_key = None
            self.update()
        if self._mode == "home":
            self._step(self._home_point(), 10)
        elif self._mode in {"follow", "call"}:
            cursor = QCursor.pos()
            frame = self._current()
            origin = self._sprite_origin(frame)
            # Sit on the right of the mouse, same idea as drag-push, and keep up with it.
            target = QPoint(cursor.x() + 22 - origin.x(), cursor.y() - max(1, frame.height()) // 2)
            self._step(target, 22 if self._mode == "call" else 18)
        self._fit_mask()

    def _current(self) -> QPixmap:
        traveling = self._mode in {"follow", "call"} and self._far()
        frames = self._run if traveling and self._run else self._frames
        if not frames:
            return QPixmap()
        return frames[self._index % len(frames)]

    def _far(self) -> bool:
        cursor = QCursor.pos()
        frame = self._frames[self._index % len(self._frames)] if self._frames else QPixmap(self._size, self._size)
        origin = self.mapToGlobal(self._sprite_origin(frame))
        cx = origin.x() + frame.width() // 2
        cy = origin.y() + frame.height() // 2
        return math.hypot(cursor.x() - cx, cursor.y() - cy) > 70

    def _home_point(self) -> QPoint:
        screen = QApplication.primaryScreen()
        if screen is None:
            return self.pos()
        area = screen.availableGeometry()
        x = area.x() + int(area.width() * self._home[0] / 100) - self.width() // 2
        y = area.y() + int(area.height() * self._home[1] / 100) - self._size // 2
        return QPoint(
            max(area.left(), min(x, area.right() - self.width() + 1)),
            max(area.top(), min(y, area.bottom() - self.height() + 1)),
        )

    def _go_home(self) -> None:
        self.move(self._home_point())

    def _step(self, target: QPoint, speed: int) -> None:
        pos = self.pos()
        dx = target.x() - pos.x()
        dy = target.y() - pos.y()
        dist = math.hypot(dx, dy)
        if dist < 3:
            return
        step = min(dist, speed)
        self.move(int(pos.x() + dx / dist * step), int(pos.y() + dy / dist * step))

    def _bar_rect(self) -> QRect:
        return QRect(8, self._size + 16, self.width() - 16, _BAR)

    def _layout_buttons(self) -> list[tuple[str, str, QRect]]:
        if self._game:
            items = (("left", "Left"), ("right", "Right"))
        elif self._need or self._poops or self._sick:
            items = _CARE
        else:
            return []
        bar = self._bar_rect()
        gap = 6
        count = len(items)
        width = max(36, (bar.width() - gap * (count + 1)) // count)
        laid = []
        x = bar.x() + gap
        for key, label in items:
            rect = QRect(x, bar.y() + 8, width, bar.height() - 16)
            laid.append((key, label, rect))
            x += width + gap
        return laid

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        point = event.position().toPoint()
        for key, _label, rect in self._layout_buttons():
            if rect.contains(point):
                self._pressed = key
                self.update()
                return
        self._drag = event.globalPosition().toPoint() - self.pos()
        self.dragging.emit(True)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag is None:
            return
        self.move(event.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        point = event.position().toPoint()
        if self._pressed:
            for key, _label, rect in self._layout_buttons():
                if key == self._pressed and rect.contains(point):
                    self.care.emit(key)
            self._pressed = ""
            self.update()
            return
        if self._drag is None:
            return
        self._drag = None
        self.dragging.emit(False)
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        frame = self._current()
        origin = self.mapToGlobal(self._sprite_origin(frame))
        cx = origin.x() + frame.width() / 2
        cy = origin.y() + max(1, frame.height()) / 2
        across = (cx - area.x()) / max(1, area.width()) * 100
        down = (cy - area.y()) / max(1, area.height()) * 100
        self.parked.emit(across, down)

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        frame = self._current()
        origin = self._sprite_origin(frame)
        if not self._lights:
            painter.setOpacity(0.38)
        painter.drawPixmap(origin, frame)
        painter.setOpacity(1)
        if self._sick:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#1a1916"))
            painter.drawEllipse(origin.x() + frame.width() - 18, origin.y(), 14, 14)
        for index in range(min(4, self._poops)):
            painter.setBrush(QColor("#8a6a45"))
            painter.drawEllipse(origin.x() + 4 + index * 12, origin.y() + frame.height() - 10, 8, 8)
        laid = self._layout_buttons()
        self._buttons = [(key, rect) for key, _label, rect in laid]
        if laid:
            bar = self._bar_rect()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#121110"))
            painter.drawRoundedRect(bar, 16, 16)
            painter.setPen(QColor("#f4efe4"))
            painter.setFont(QFont("JetBrains Mono", 8))
            if self._game_label:
                painter.drawText(QRect(bar.x(), bar.y() - 16, bar.width(), 14), Qt.AlignmentFlag.AlignHCenter, self._game_label)
            for key, label, rect in laid:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor("#3a3834" if key == self._pressed else "#2a2926"))
                painter.drawRoundedRect(rect, 9, 9)
                painter.setPen(QColor("#f4efe4"))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
        painter.end()

    def _fit_mask(self) -> None:
        frame = self._current()
        if frame.isNull():
            return
        self._refresh_mask(frame, self._sprite_origin(frame), bool(self._layout_buttons()))

    def _refresh_mask(self, frame: QPixmap, origin: QPoint, bar: bool) -> None:
        key = (id(frame), origin.x(), origin.y(), bar, self._game, self.width(), self.height())
        if key == self._mask_key or frame.isNull():
            return
        self._mask_key = key
        image = frame.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        mask = image.createAlphaMask()
        region = QRegion(QBitmap.fromImage(mask)).translated(origin)
        if bar:
            region = region.united(QRegion(self._bar_rect().adjusted(0, -18, 0, 0)))
        if region.isEmpty():
            region = QRegion(origin.x(), origin.y(), max(8, frame.width()), max(8, frame.height()))
        self.setMask(region)
