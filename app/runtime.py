"""Wires the ghost, the hooks, and the disk suggestion together."""

from __future__ import annotations

import json
import logging
import os
import random
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from app.badges_panel import BadgesPanel
from app.config import app_data_dir, config_path, load_config, project_root
from app.dust import append_decision, delete_tree, safe_to_delete, scan_roots, seed_history, sweep_temp
from app.dust_dialog import DustDialog
from app.economy import Economy
from app.events.clipboard_hook import ClipboardWatch
from app.events.fs_hook import FolderWatch
from app.events.keyboard_hook import KeyboardHook
from app.events.mouse_hook import MouseHook
from app.halloween import parse_preview, theme_for
from app.local_gemma import start_bundled_gemma
from app.prompts import BY_ID
from app.settings_window import SettingsWindow
from app.sprites import SpriteLibrary
from app.state_machine import CooldownGate
from app.tabpfn_dust import suggest
from app.tray import Tray
from app.whisper import Whisperer, ask_gemma, load_fallback_lines

log = logging.getLogger(__name__)


def make_tray_icon(path: Path) -> QIcon:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        fill = (232, 230, 242, 255)
        eye = (18, 18, 28, 255)
        sensor = (70, 72, 90, 255)
        draw.ellipse((16, 6, 28, 24), fill=fill)
        draw.ellipse((36, 4, 48, 22), fill=fill)
        draw.ellipse((8, 16, 56, 58), fill=fill)
        draw.ellipse((10, 48, 24, 62), fill=fill)
        draw.ellipse((25, 50, 39, 64), fill=fill)
        draw.ellipse((40, 48, 54, 62), fill=fill)
        draw.ellipse((22, 30, 30, 38), fill=eye)
        draw.ellipse((36, 30, 44, 38), fill=eye)
        draw.rectangle((38, 32, 42, 36), fill=sensor)
        image.save(path)
    return QIcon(str(path))


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


class Runtime(QObject):
    incoming = Signal(str)
    dragging = Signal()
    line_ready = Signal(str, str)
    dust_ready = Signal(object, str)
    freed_ready = Signal(int, str)

    def __init__(self, cfg: dict, engine: bool = False) -> None:
        super().__init__()
        self.cfg = cfg
        self.paused = False
        self.hidden = False
        self._warned_sprites = False
        self._keyboard_copy_at = 0.0
        self._last_event = time.monotonic()
        self._using_tk = False
        root = project_root()
        data = app_data_dir()
        self.economy = Economy.load(data / "state.json")
        sprites = cfg.get("sprites") or {}
        self.library = SpriteLibrary(self._pack_path(sprites), sprites)
        self.gate = CooldownGate(cfg.get("cooldowns_ms") or {})
        animation = cfg.get("animation") or {}
        overlay_cfg = cfg.get("overlay") or {}
        self.overlay = self._make_overlay(overlay_cfg, animation)
        # Separate window so typing/copy keep working while the pet stays parked.
        self.buddy = self._make_overlay(overlay_cfg, animation)
        ollama = cfg.get("ollama") or {}
        self.model_name = str(ollama.get("model", "gemma3:1b"))
        self.whisper = Whisperer(
            str(ollama.get("url", "http://127.0.0.1:11434")),
            self.model_name,
            float(ollama.get("timeout_s", 45)),
            float(ollama.get("min_interval_s", 30)),
            load_fallback_lines(root / "assets" / "lines" / "fallback_lines.json"),
            lambda line, source: self.line_ready.emit(line, source),
        )
        seed_history(root / "assets" / "dust" / "seed_labels.csv", data / "dust_history.csv")
        self.history_path = data / "dust_history.csv"
        self.clipboard = ClipboardWatch()
        self.keyboard = KeyboardHook(self.incoming.emit)
        self.folders = FolderWatch(self.incoming.emit, (cfg.get("watch") or {}).get("extra_dirs"))
        self.mouse = MouseHook(self.incoming.emit, self._hit, self.dragging.emit)
        self.dragging.connect(self._shove)
        icon = make_tray_icon(root / "assets" / "icons" / "tray.png")
        self._engine = engine
        self.settings = None if engine else SettingsWindow(self.cfg, self.apply_config)
        self.tray = Tray(
            icon,
            self.show_settings,
            self.toggle_hidden,
            self.toggle_paused,
            self.show_badges,
            self.haunt,
            self.confirm_temp,
            self.reset,
            self.quit,
        )
        self.incoming.connect(self._on_event, Qt.ConnectionType.QueuedConnection)
        self.line_ready.connect(self._on_line)
        self.dust_ready.connect(self._on_dust)
        self.freed_ready.connect(self._on_freed)
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(1000)
        self._idle_timer.timeout.connect(self._idle)
        self._save_timer = QTimer(self)
        self._save_timer.setInterval(10000)
        self._save_timer.timeout.connect(self.economy.save)
        self._clip_timer = QTimer(self)
        self._clip_timer.setInterval(500)
        self._clip_timer.timeout.connect(self._poll_clipboard)
        self._bounds = (0, 0, 0, 0)
        self._bounds_timer = QTimer(self)
        self._bounds_timer.setInterval(100)
        self._bounds_timer.timeout.connect(self._cache_bounds)
        if self._using_tk:
            self._pump = QTimer(self)
            self._pump.setInterval(33)
            self._pump.timeout.connect(self.overlay.pump)
        self._config_mtime = _mtime(config_path())
        self._config_timer = QTimer(self)
        self._config_timer.setInterval(1000)
        self._config_timer.timeout.connect(self._reload_config)
        self._look_mtime = _mtime(app_data_dir() / "look.json")
        self._look_timer = QTimer(self)
        self._look_timer.setInterval(40)
        self._look_timer.timeout.connect(self._poll_look)
        self._heard_question = ("", False)

    def _make_overlay(self, overlay_cfg: dict, animation: dict):
        kwargs = dict(
            size=int(overlay_cfg.get("size", 192)),
            margin=int(overlay_cfg.get("margin", 16)),
            corner=str(overlay_cfg.get("corner", "top-right")),
            play_ms=int(animation.get("play_ms", 2500)),
            hold_ms=int(animation.get("hold_ms", 500)),
            fade_ms=int(animation.get("fade_ms", 300)),
        )
        try:
            from app.overlay import GhostOverlay

            overlay = GhostOverlay(**kwargs)
            overlay.apply_look(
                int(overlay_cfg.get("size", 192)),
                float(overlay_cfg.get("opacity", 1)),
                float(overlay_cfg.get("x", 100)),
                float(overlay_cfg.get("y", 0)),
            )
            log.info("Using the Qt overlay")
            return overlay
        except Exception:
            log.exception("Qt overlay failed; using the tk fallback")
            from app.overlay_tk import GhostOverlayTk

            self._using_tk = True
            overlay = GhostOverlayTk(**kwargs)
            overlay.apply_look(
                int(overlay_cfg.get("size", 192)),
                float(overlay_cfg.get("opacity", 1)),
                float(overlay_cfg.get("x", 100)),
                float(overlay_cfg.get("y", 0)),
            )
            return overlay

    def start(self) -> None:
        start_bundled_gemma(project_root())
        self._warm_gemma()
        self.keyboard.start()
        self.folders.start()
        self.mouse.start()
        self._idle_timer.start()
        self._save_timer.start()
        self._clip_timer.start()
        self._bounds_timer.start()
        if self._using_tk:
            self._pump.start()
        theme = theme_for(self.now())
        self.overlay.set_marigold(theme.marigold)
        self._refresh_tooltip()
        self._config_timer.start()
        self._look_timer.start()
        if self.settings is not None:
            self.settings.show()
        log.info("GITM is in the tray")

    def _warm_gemma(self) -> None:
        if not (self.cfg.get("ollama") or {}).get("enabled", True):
            return

        def run() -> None:
            try:
                ask_gemma(self.whisper.url, self.whisper.model, "idle", "dormant", 120)
                log.info("Gemma is ready")
            except Exception:
                log.info("Gemma is not ready yet")

        threading.Thread(target=run, name="gemma-warm", daemon=True).start()

    def now(self) -> datetime:
        return parse_preview(str(self.cfg.get("preview_date") or ""), datetime.now())

    def _cache_bounds(self) -> None:
        self._bounds = self.overlay.bounds()

    def _hit(self, x: int, y: int) -> bool:
        left, top, width, height = self._bounds
        return width > 0 and left <= x <= left + width and top <= y <= top + height

    def _shove(self) -> None:
        if hasattr(self.overlay, "shove"):
            self.overlay.shove()

    def _wake(self) -> None:
        self._last_event = time.monotonic()
        if getattr(self, "_shown_action", "") != "idle":
            return
        if hasattr(self.overlay, "is_showing") and self.overlay.is_showing() and hasattr(self.overlay, "begin_leave"):
            self.overlay.begin_leave()

    def _toggle_pet(self) -> None:
        shown = self.cfg.get("show") or {}
        if shown.get("pet", True) is False:
            return
        look = self._look_for("pet")
        if hasattr(self.buddy, "pet_parked") and self.buddy.pet_parked():
            self.buddy.dismiss_pet()
            log.info("Pet dismissed")
            return
        sheets = self.library.pet_visit_sets() if hasattr(self.library, "pet_visit_sets") else []
        if not sheets:
            log.warning("No sprite frames for pet")
            return
        point = getattr(self.mouse, "_pet_at", None)
        screen = QApplication.primaryScreen()
        if point is None or screen is None:
            return
        area = screen.availableGeometry()
        across = max(0.0, min(100.0, (point[0] - area.x()) / max(1, area.width()) * 100))
        down = max(0.0, min(100.0, (point[1] - area.y()) / max(1, area.height()) * 100))
        if hasattr(self.buddy, "apply_look"):
            self.buddy.apply_look(int(look["size"]), float(look["opacity"]), across, down)
        if hasattr(self.buddy, "set_pace"):
            self.buddy.set_pace(int(look.get("speed", 100)))
        if hasattr(self.buddy, "set_swarm"):
            self.buddy.set_swarm(False)
        if hasattr(self.buddy, "set_push"):
            self.buddy.set_push(False)
        self.buddy.park_pet(sheets, across, down)
        self.economy.record("pet")
        log.info("Pet parked at %.0f,%.0f with %s sheets", across, down, len(sheets))

    def _on_event(self, name: str) -> None:
        if name == "presence":
            self._wake()
            return
        if name == "candy":
            return
        if name == "pet":
            if self.cfg.get("enabled", True) is False or self.paused or self.hidden:
                return
            self._toggle_pet()
            return
        if name not in BY_ID:
            return
        if self.cfg.get("enabled", True) is False or self.paused or self.hidden:
            log.info("Ghost skipped %s (enabled=%s paused=%s hidden=%s)", name, self.cfg.get("enabled", True), self.paused, self.hidden)
            return
        shown = self.cfg.get("show") or {}
        if shown.get(name, True) is False:
            return
        moment = time.monotonic()
        if name == "copy":
            self._keyboard_copy_at = moment
        allowed = self.gate.allow(name, moment)
        showing = hasattr(self.overlay, "is_showing") and self.overlay.is_showing()
        if not allowed and showing and name == getattr(self, "_shown_action", ""):
            if hasattr(self.overlay, "note_activity"):
                self.overlay.note_activity()
            return
        if allowed and name != "idle":
            self._last_event = moment
            if hasattr(self, "buddy") and hasattr(self.buddy, "maybe_wander"):
                self.buddy.maybe_wander()
        if allowed:
            self.economy.record(name)
            self._announce(self.economy.newly_unlocked(self.now()))
        theme = theme_for(self.now())
        shown = self.cfg.get("show") or {}
        frames = self.library.frames_for(name, theme.pumpkin and shown.get("halloween", True))
        if not frames:
            log.warning("No sprite frames for %s", name)
            if not self._warned_sprites:
                self._warned_sprites = True
                self.tray.show_message(
                    "Sprites",
                    "Ghost window mein PNG drop karo",
                )
        look = self._look_for(name)
        if name == "typing":
            if hasattr(self.overlay, "apply_look"):
                # Keep size/opacity; peek owns on-screen placement (no Across/Down).
                self.overlay.apply_look(int(look["size"]), float(look["opacity"]), 50, 50)
        elif hasattr(self.overlay, "apply_look"):
            self.overlay.apply_look(int(look["size"]), float(look["opacity"]), float(look["x"]), float(look["y"]))
        if hasattr(self.overlay, "set_pace"):
            self.overlay.set_pace(int(look.get("speed", 100)))
        if hasattr(self.overlay, "set_swarm"):
            self.overlay.set_swarm(name == "idle")
        if hasattr(self.overlay, "set_push"):
            self.overlay.set_push(name == "move")
        previous = getattr(self, "_shown_action", "")
        if not frames:
            log.warning("Skip play for %s; no frames", name)
            return
        if name == "typing" and hasattr(self.overlay, "start_peek"):
            self.overlay.start_peek(frames)
        elif showing and hasattr(self.overlay, "adopt"):
            self.overlay.adopt(frames)
        else:
            self.overlay.play(frames, theme.tint)
        self._shown_action = name
        try:
            import ctypes

            geo = self.overlay.frameGeometry()
            hwnd = int(self.overlay.winId())
            real = bool(hwnd and ctypes.windll.user32.IsWindow(hwnd))
            log.info(
                "Playing %s (%s frames) at %s,%s size %sx%s visible=%s hwnd=%s real=%s",
                name,
                len(frames),
                geo.x(),
                geo.y(),
                geo.width(),
                geo.height(),
                self.overlay.isVisible(),
                hwnd,
                real,
            )
        except Exception:
            log.info("Playing %s (%s frames)", name, len(frames))
        writing = hasattr(self.overlay, "writing") and self.overlay.writing()
        ask = bool(look.get("ask")) and (self.cfg.get("ollama") or {}).get("enabled", True)
        if ask and not writing and (not showing or previous != name):
            if self.whisper.request(name, str(self.economy.state["mood"]), str(look.get("question") or "")):
                self._speak_for = name
                if hasattr(self.overlay, "expect_line"):
                    self.overlay.expect_line()
        elif not ask:
            self._speak_for = ""
        self._refresh_tooltip()

    def _look_for(self, name: str) -> dict:
        overlay = self.cfg.get("overlay") or {}
        looks = self.cfg.get("looks") if isinstance(self.cfg.get("looks"), dict) else {}
        raw = looks.get(name) if isinstance(looks.get(name), dict) else {}
        opacity = raw.get("opacity", overlay.get("opacity", 1))
        try:
            opacity_f = float(opacity)
        except (TypeError, ValueError):
            opacity_f = 1.0
        if opacity_f > 1:
            opacity_f = opacity_f / 100
        return {
            "size": int(raw.get("size", overlay.get("size", 192))),
            "opacity": max(0.2, min(1.0, opacity_f)),
            "x": int(raw.get("x", overlay.get("x", 100))),
            "y": int(raw.get("y", overlay.get("y", 0))),
            "ask": bool(raw.get("ask", False)) if name in looks else bool(overlay.get("ask", False)),
            "question": str(raw.get("question", overlay.get("question", "")) or ""),
            "speed": max(25, min(200, int(raw.get("speed", overlay.get("speed", 100))))),
        }

    def _on_line(self, line: str, source: str) -> None:
        if not getattr(self, "_speak_for", ""):
            return
        if not self._look_for(self._speak_for).get("ask"):
            return
        self.overlay.set_caption(line, source)
        try:
            (app_data_dir() / "line.json").write_text(json.dumps({"text": line, "at": time.time()}), encoding="utf-8")
        except OSError:
            pass

    def _poll_look(self) -> None:
        path = app_data_dir() / "look.json"
        mtime = _mtime(path)
        if not mtime or mtime == self._look_mtime:
            return
        self._look_mtime = mtime
        if self.cfg.get("enabled", True) is False or self.paused or self.hidden:
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        action = str(data.get("action") or "")
        looks = self.cfg.setdefault("looks", {})
        slot = looks.setdefault(action, {}) if action else self.cfg.setdefault("overlay", {})
        slot["size"] = max(80, min(420, int(data.get("size", slot.get("size", 192)))))
        slot["opacity"] = max(0.2, min(1.0, float(data.get("opacity", slot.get("opacity", 1)))))
        slot["x"] = max(0, min(100, int(data.get("x", slot.get("x", 100)))))
        slot["y"] = max(0, min(100, int(data.get("y", slot.get("y", 0)))))
        slot["ask"] = bool(data.get("ask", False))
        slot["question"] = str(data.get("question") or "")[:240]
        slot["speed"] = max(25, min(200, int(data.get("speed", slot.get("speed", 100)))))
        if not slot["ask"]:
            self._speak_for = ""
            if hasattr(self.overlay, "quiet"):
                self.overlay.quiet()
        frames = self.library.frames_for(action, False) if action else []
        if hasattr(self.overlay, "live_look"):
            self.overlay.live_look(slot["size"], slot["opacity"], slot["x"], slot["y"], frames, "")
        if hasattr(self.overlay, "set_pace"):
            self.overlay.set_pace(int(slot.get("speed", 100)))
    def _ask_topic(self) -> None:
        overlay = self.cfg.get("overlay") or {}
        question = str(overlay.get("question") or "").strip()
        if not overlay.get("ask") or not question:
            return
        if (self.cfg.get("ollama") or {}).get("enabled", True) is False:
            return
        self._heard_question = (question, True)
        self.whisper.request("typing", str(self.economy.state["mood"]), question, fresh=True)

    def _poll_clipboard(self) -> None:
        recent = (time.monotonic() - self._keyboard_copy_at) < 1.5
        event = self.clipboard.poll(recent)
        if event:
            self._on_event(event)

    def _idle(self) -> None:
        if self.cfg.get("enabled", True) is False:
            return
        quiet = time.monotonic() - self._last_event
        if quiet < 1:
            return
        self.economy.tick_idle(1)
        self._announce(self.economy.newly_unlocked(self.now()))
        if quiet >= 12:
            self._on_event("idle")

    def _announce(self, badges: list[str]) -> None:
        for name in badges:
            self.tray.show_message("Badge unlocked", name)
            log.info("Badge unlocked: %s", name)

    def _refresh_tooltip(self) -> None:
        theme = theme_for(self.now())
        alive = self.cfg.get("enabled", True) is not False and not self.hidden
        self.overlay.set_marigold(theme.marigold and alive)
        try:
            free_gb = shutil.disk_usage("C:\\").free / (1024**3)
        except OSError:
            free_gb = 0.0
        extra = [f"C: {free_gb:.1f} GB free", f"Voice: {self.model_name}"]
        warn = float((self.cfg.get("dust") or {}).get("warn_below_gb", 15))
        if free_gb < warn:
            extra.append("drive choking")
        if theme.tooltip:
            extra.append(theme.tooltip)
        self.tray.set_tooltip(self.economy.tooltip(" | ".join(extra)))

    def _pack_path(self, sprites: dict) -> Path:
        raw = Path(str(sprites.get("pack", "sprites")))
        return raw if raw.is_absolute() else project_root() / raw

    def show_settings(self, _checked: bool = False) -> None:
        if self.settings is not None:
            self.settings.show()
            self.settings.raise_()
            self.settings.activateWindow()
            return
        shell = os.environ.get("GHOST_SHELL", "")
        if not shell:
            return
        arg = os.environ.get("GHOST_SHELL_ARG", "")
        subprocess.Popen([shell, arg] if arg else [shell], cwd=os.environ.get("GHOST_SHELL_CWD") or None)

    def _reload_config(self) -> None:
        path = config_path()
        mtime = _mtime(path)
        if mtime == self._config_mtime:
            return
        self._config_mtime = mtime
        try:
            self.apply_config(load_config())
        except Exception:
            log.warning("Could not reload config")

    def apply_config(self, cfg: dict) -> None:
        self.cfg = cfg
        sprites = cfg.get("sprites") or {}
        self.library = SpriteLibrary(self._pack_path(sprites), sprites)
        self.gate = CooldownGate(cfg.get("cooldowns_ms") or {})
        ollama = cfg.get("ollama") or {}
        self.model_name = str(ollama.get("model", "gemma3:1b"))
        self.whisper.url = str(ollama.get("url", "http://127.0.0.1:11434"))
        self.whisper.model = self.model_name
        self.whisper.timeout_s = float(ollama.get("timeout_s", 45))
        if cfg.get("enabled", True) is False:
            self.overlay.hide_ghost()
            if hasattr(self, "buddy") and hasattr(self.buddy, "dismiss_pet"):
                self.buddy.dismiss_pet()
        overlay_cfg = cfg.get("overlay") or {}
        if hasattr(self.overlay, "apply_look"):
            self.overlay.apply_look(
                int(overlay_cfg.get("size", 192)),
                float(overlay_cfg.get("opacity", 1)),
                float(overlay_cfg.get("x", 100)),
                float(overlay_cfg.get("y", 0)),
            )
        self._refresh_tooltip()

    def toggle_hidden(self, _checked: bool = False) -> None:
        self.hidden = not self.hidden
        if self.hidden:
            self.overlay.hide_ghost()
            if hasattr(self, "buddy") and hasattr(self.buddy, "dismiss_pet"):
                self.buddy.dismiss_pet()
        self.tray.set_hidden(self.hidden)

    def toggle_paused(self, _checked: bool = False) -> None:
        self.paused = not self.paused
        self.tray.set_paused(self.paused)

    def show_badges(self, _checked: bool = False) -> None:
        BadgesPanel(list(self.economy.state["badges"])).exec()

    def haunt(self, _checked: bool = False) -> None:
        threading.Thread(target=self._scan, name="dust-scan", daemon=True).start()

    def _scan(self) -> None:
        dust = self.cfg.get("dust") or {}
        rows = scan_roots((self.cfg.get("watch") or {}).get("extra_dirs"))
        cache = Path(str(dust.get("tabpfn_cache_dir", "D:/tabpfn-cache")))
        scored, note = suggest(self.history_path, rows, cache)
        self.dust_ready.emit(scored, note)

    def _on_dust(self, rows, note: str) -> None:
        minimum = float((self.cfg.get("dust") or {}).get("sweep_min_prob", 0.7))
        dialog = DustDialog(list(rows), note, minimum)
        if dialog.exec() != DustDialog.DialogCode.Accepted:
            return
        chosen = [row for row in dialog.chosen() if safe_to_delete(Path(row.path))]
        threading.Thread(target=self._delete_rows, args=(chosen,), daemon=True).start()

    def _delete_rows(self, rows) -> None:
        freed = 0
        for row in rows:
            path = Path(row.path)
            got = delete_tree(path)
            if got:
                freed += got
                append_decision(self.history_path, row, "sweep")
        self.freed_ready.emit(freed, "sweep")

    def confirm_temp(self, _checked: bool = False) -> None:
        answer = QMessageBox.question(
            None,
            "Sweep temp",
            "Clear temp files, thumbnails, and the Recycle Bin?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        threading.Thread(target=self._run_temp, daemon=True).start()

    def _run_temp(self) -> None:
        freed = sweep_temp()
        self.freed_ready.emit(freed, "temp")

    def _on_freed(self, nbytes: int, kind: str) -> None:
        self.economy.add_freed(nbytes)
        self.economy.save()
        megabytes = nbytes / (1024 * 1024)
        self.tray.show_message("Dust", f"Freed about {megabytes:.1f} MB")
        log.info("Freed bytes from %s: %s", kind, nbytes)
        self._refresh_tooltip()

    def reset(self, _checked: bool = False) -> None:
        self.economy.reset()
        self.gate.clear()
        self._refresh_tooltip()
        self.tray.show_message("Reset", "Haunting scores cleared")

    def quit(self, _checked: bool = False) -> None:
        self.economy.save()
        self.keyboard.stop()
        self.mouse.stop()
        self.folders.stop()
        QApplication.quit()
