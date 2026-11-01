"""Tk fallback if the Qt transparent window cannot be created."""

from __future__ import annotations

import time
import tkinter as tk

from PIL import Image, ImageTk


class GhostOverlayTk:
    def __init__(self, size: int = 192, margin: int = 16, play_ms: int = 2500, hold_ms: int = 500, fade_ms: int = 300, corner: str = "top-right") -> None:
        self._size = size
        self._margin = margin
        self._corner = corner if corner in {"top-right", "bottom-right"} else "top-right"
        self._strength = 1.0
        self._across = 100.0
        self._down = 0.0
        self._draw_w = size
        self._draw_h = size
        self._sources: list[Image.Image] = []
        self._play_ms = play_ms
        self._hold_ms = hold_ms
        self._fade_ms = max(1, fade_ms)
        self._frames: list[Image.Image] = []
        self._photos: list[ImageTk.PhotoImage] = []
        self._index = 0
        self._phase = "hidden"
        self._phase_at = 0.0
        self._marigold = False
        self._caption = ""
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "magenta")
        self.root.configure(bg="magenta")
        self.root.geometry(self._geometry())
        self.canvas = tk.Canvas(self.root, width=size, height=size, bg="magenta", highlightthickness=0)
        self.canvas.pack()
        self.root.withdraw()

    def _geometry(self) -> str:
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        width = self._draw_w
        height = self._draw_h
        span_x = max(0, screen_w - width)
        span_y = max(0, screen_h - height)
        x = round(span_x * self._across / 100)
        y = round(span_y * self._down / 100)
        return f"{width}x{height}+{x}+{y}"

    def apply_look(self, size: int, opacity: float, across: float, down: float) -> None:
        self._size = max(80, min(420, int(size)))
        self._strength = max(0.2, min(1.0, float(opacity)))
        self._across = max(0.0, min(100.0, float(across)))
        self._down = max(0.0, min(100.0, float(down)))
        try:
            self.root.attributes("-alpha", self._strength)
        except tk.TclError:
            pass
        if self._sources and self._phase != "hidden":
            self._present(self._sources, restart=False)
        elif self._phase != "hidden":
            self.root.geometry(self._geometry())

    def live_look(self, size: int, opacity: float, across: float, down: float, frames=None, say: str | None = None) -> None:
        self.apply_look(size, opacity, across, down)
        if frames:
            ready = [frame.convert("RGBA") for frame in frames if frame is not None]
            if ready:
                self._sources = ready
        if say is not None and say != getattr(self, "_say", None):
            self._say = say
            self._caption = say
        if self._sources:
            self._present(self._sources, restart=False)
            self._phase = "holding"
            self._preview_until = time.monotonic() + 1.2

    def _present(self, frames, restart: bool) -> None:
        ready = [frame.convert("RGBA") for frame in frames if frame is not None]
        if not ready:
            return
        native = ready[0].size
        logical_h = max(80, self._size)
        logical_w = max(1, round(native[0] * logical_h / max(1, native[1])))
        bubble = 248 if str(self._caption or "").strip() else 0
        self._sprite_x = bubble
        self._draw_w = logical_w + bubble
        self._draw_h = logical_h
        scaled = [
            frame if frame.size == (logical_w, logical_h) else frame.resize((logical_w, logical_h), Image.Resampling.BILINEAR)
            for frame in ready
        ]
        self._frames = scaled
        self._photos = [ImageTk.PhotoImage(frame) for frame in scaled]
        self.canvas.configure(width=self._draw_w, height=logical_h)
        self.root.geometry(self._geometry())
        if restart:
            self._index = 0
            self._phase = "playing"
            self._phase_at = time.monotonic()
        self.root.deiconify()
        self._draw()

    def play(self, frames, tint, caption: str = "", source: str = "") -> None:
        del tint
        ready = [frame.convert("RGBA") for frame in frames if frame is not None]
        if not ready:
            return
        self._sources = ready
        self._caption = caption
        self._present(ready, restart=True)

    def set_caption(self, caption: str, source: str) -> None:
        self._caption = caption
        if self._sources:
            if self._phase == "hidden":
                self._phase = "holding"
            self._present(self._sources, restart=False)
            self._preview_until = time.monotonic() + 2.4
        else:
            self._draw()

    def set_marigold(self, enabled: bool) -> None:
        del enabled
        self._marigold = False
        if self._phase == "hidden":
            self.root.withdraw()

    def hide_ghost(self) -> None:
        self._phase = "hidden"
        self._frames = []
        self._photos = []
        self.root.withdraw()

    def bounds(self) -> tuple[int, int, int, int]:
        if self._phase == "hidden" or not self.root.winfo_viewable():
            return (0, 0, 0, 0)
        return (self.root.winfo_rootx(), self.root.winfo_rooty(), self._draw_w, self._draw_h)

    def flash(self) -> None:
        flash = tk.Toplevel(self.root)
        flash.overrideredirect(True)
        flash.attributes("-topmost", True)
        flash.configure(bg="red")
        flash.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
        flash.attributes("-alpha", 0.25)
        flash.after(150, flash.destroy)

    def pump(self) -> None:
        self._tick()
        self.root.update_idletasks()
        self.root.update()

    def _tick(self) -> None:
        if self._phase == "hidden":
            return
        now = time.monotonic()
        if getattr(self, "_preview_until", 0) and now < self._preview_until and self._phase != "playing":
            self._phase = "holding"
            self._draw()
            return
        if self._phase == "playing":
            elapsed = now - self._phase_at
            if elapsed >= self._play_ms / 1000:
                self._phase = "holding"
                self._phase_at = now
            elif self._frames:
                self._index = min(len(self._frames) - 1, int((elapsed / (self._play_ms / 1000)) * len(self._frames)))
        elif self._phase == "holding" and now - self._phase_at >= self._hold_ms / 1000:
            self._phase = "fading"
            self._phase_at = now
        elif self._phase == "fading" and now - self._phase_at >= self._fade_ms / 1000:
            self.hide_ghost()
            return
        self._draw()

    def _draw(self) -> None:
        self.canvas.delete("all")
        sprite_x = getattr(self, "_sprite_x", 0)
        if self._caption and self._phase != "hidden":
            box_h = min(132, max(72, self._draw_h - 16))
            top = max(8, (self._draw_h - box_h) // 2)
            self.canvas.create_rectangle(12, top, 226, top + box_h, fill="#fbfbfa", outline="#e4e3df", width=1)
            self.canvas.create_text(24, top + 12, text=self._caption[:180], anchor="nw", width=190, fill="#37352f", font=("Segoe UI", 10))
        if self._photos and self._phase != "hidden":
            photo = self._photos[min(self._index, len(self._photos) - 1)]
            self.canvas.create_image(sprite_x, 0, image=photo, anchor="nw")
