"""Studio window in the SpriteForge layout: sticky rail, one action page, Gemma in the same window."""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import project_root, save_config
from app.prompts import CATALOG, sheet_prompt

DEFAULT_LOOK = "the character"
from app.sheet_import import import_dropped
from app.whisper import ask_gemma, fallback_line, load_fallback_lines

STUDIO_STYLE = """
QWidget#studio, QWidget#page, QFrame#side, QScrollArea, QWidget#holder, QStackedWidget {
  background: #fbfbfa;
  color: #37352f;
  font-size: 13px;
}
QFrame#side { border-right: 1px solid #e9e9e7; }
QLabel#muted { color: #787774; }
QLabel#kicker { color: #787774; font-size: 11px; letter-spacing: 0.08em; }
QLabel#title { font-size: 15px; }
QLabel#crumb { color: #787774; }
QPushButton#nav {
  text-align: left;
  border: none;
  border-radius: 6px;
  padding: 6px 8px;
  background: transparent;
  color: #37352f;
}
QPushButton#nav:hover { background: #f1f1ef; }
QPushButton#nav:checked { background: #f1f1ef; }
QPushButton#save {
  color: #f7f6f3;
  border: none;
  border-radius: 6px;
  background: #2a2a28;
  min-height: 32px;
}
QPushButton#save:hover { background: #3a3a38; }
QPushButton#copy {
  color: white;
  background: #3a74e8;
  border: none;
  border-radius: 6px;
  padding: 6px 12px;
  min-height: 32px;
}
QPushButton#quiet {
  border: 1px solid #e9e9e7;
  border-radius: 6px;
  background: #fbfbfa;
  padding: 6px 12px;
  min-height: 32px;
}
QPushButton#quiet:hover { background: #f1f1ef; }
QLineEdit, QSpinBox {
  border: 1px solid #e9e9e7;
  border-radius: 6px;
  background: #fbfbfa;
  padding: 4px 6px;
  min-height: 28px;
}
QPlainTextEdit {
  border: none;
  background: transparent;
  color: #37352f;
}
QFrame#card {
  background: #f7f7f5;
  border: 1px solid #e3e3e0;
  border-radius: 16px;
}
QFrame#slice {
  background: #f7f7f5;
  border: 1px solid #e3e3e0;
  border-radius: 14px;
}
QCheckBox { spacing: 8px; }
QScrollArea { border: none; }
"""


class DropBox(QFrame):
    dropped = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(168)
        self.setStyleSheet(
            "DropBox { border: 1px dashed #e9e9e7; border-radius: 6px; background: #f1f1ef; }"
        )
        self._label = QLabel("Drop the ChatGPT PNG here")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("color: #787774; background: transparent; border: none;")
        layout = QVBoxLayout(self)
        layout.addWidget(self._label)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        images = [path for path in paths if path.suffix.lower() == ".png"]
        if images:
            self.dropped.emit(images)
            event.acceptProposedAction()
        else:
            self._label.setText("PNG only")
            event.ignore()

    def set_ready(self, name: str) -> None:
        self._label.setText(name)

    def set_preview(self, pixmap: QPixmap | None) -> None:
        if pixmap is None or pixmap.isNull():
            self._label.setPixmap(QPixmap())
            self._label.setText("Drop the ChatGPT PNG here")
            return
        self._label.setText("")
        self._label.setPixmap(
            pixmap.scaled(280, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
        )


class SettingsWindow(QWidget):
    tried = Signal(str)

    def __init__(self, cfg: dict, on_save) -> None:
        super().__init__()
        self.setObjectName("studio")
        self.setWindowTitle("GITM")
        self.resize(1080, 740)
        self.setStyleSheet(STUDIO_STYLE)
        font = QFont("Cascadia Mono", 10)
        if not font.exactMatch():
            font = QFont("Consolas", 10)
        self.setFont(font)
        self._on_save = on_save
        self._cfg = cfg
        self._cards: dict[str, dict] = {}
        self.tried.connect(self._show_try)

        sprites = cfg.get("sprites") or {}
        show = cfg.get("show") or {}
        ollama = cfg.get("ollama") or {}
        self.look = QLineEdit(str(cfg.get("character_look") or DEFAULT_LOOK))
        self.model = QLineEdit(str(ollama.get("model", "gemma3:1b")))
        self.url = QLineEdit(str(ollama.get("url", "http://127.0.0.1:11434")))
        self.gemma_on = QCheckBox("Gemma se line bolo")
        self.gemma_on.setChecked(bool(ollama.get("enabled", True)))
        self.gemma_status = QLabel("Ollama band ho to fallback line chalega.")
        self.gemma_status.setObjectName("muted")
        self.gemma_status.setWordWrap(True)
        self.status = QLabel("")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)

        side = QFrame()
        side.setObjectName("side")
        side.setFrameShape(QFrame.Shape.NoFrame)
        side.setFixedWidth(248)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(12, 12, 12, 12)
        side_layout.setSpacing(8)
        title = QLabel("GITM")
        title.setObjectName("title")
        side_layout.addWidget(title)
        look_label = QLabel("LOOK")
        look_label.setObjectName("kicker")
        side_layout.addWidget(look_label)
        self.look.setPlaceholderText("Character look")
        side_layout.addWidget(self.look)

        actions = QLabel("ACTIONS")
        actions.setObjectName("kicker")
        side_layout.addSpacing(8)
        side_layout.addWidget(actions)

        self._nav = QButtonGroup(self)
        self._nav.setExclusive(True)
        self.stack = QStackedWidget()
        for index, action in enumerate(CATALOG):
            button = QPushButton(action.title)
            button.setObjectName("nav")
            button.setCheckable(True)
            self._nav.addButton(button, index)
            side_layout.addWidget(button)
            page = self._action_page(
                action.id,
                action.title,
                str(sprites.get(_sprite_key(action.id), "")),
                action.motion,
                bool(show.get(action.id, True)),
            )
            self.stack.addWidget(page)
        self._nav.button(0).setChecked(True)
        self._nav.idClicked.connect(self.stack.setCurrentIndex)

        voice = QLabel("VOICE")
        voice.setObjectName("kicker")
        side_layout.addSpacing(10)
        side_layout.addWidget(voice)
        gemma_button = QPushButton("Gemma")
        gemma_button.setObjectName("nav")
        gemma_button.setCheckable(True)
        self._nav.addButton(gemma_button, len(CATALOG))
        side_layout.addWidget(gemma_button)
        self.stack.addWidget(self._gemma_page())

        side_layout.addStretch(1)
        side_layout.addWidget(self.status)
        save = QPushButton("Save")
        save.setObjectName("save")
        save.clicked.connect(lambda: self._save(False))
        side_layout.addWidget(save)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(side)
        root.addWidget(self.stack, 1)
        self.look.textChanged.connect(lambda _text: self._sync_all_prompts())
        self._sync_all_prompts()

    def _action_page(self, event: str, title: str, ghost: str, motion: str, shown: bool) -> QWidget:
        page = QWidget()
        page.setObjectName("page")
        body = QVBoxLayout()
        body.setContentsMargins(24, 16, 24, 24)
        body.setSpacing(14)

        header = QHBoxLayout()
        crumb = QLabel(f"GITM   /   {title}")
        crumb.setObjectName("crumb")
        check = QCheckBox("Show")
        check.setChecked(shown)
        header.addWidget(crumb)
        header.addStretch(1)
        header.addWidget(check)
        body.addLayout(header)

        steps = QLabel("1. Copy the prompt.\n2. Paste it into ChatGPT.\n3. Drop the picture onto the box below.")
        steps.setObjectName("muted")
        body.addWidget(steps)

        drop = DropBox()
        drop.dropped.connect(lambda paths, ev=event: self._import(ev, paths))
        body.addWidget(drop)

        prompt = QPlainTextEdit()
        prompt.setReadOnly(True)
        prompt.setMinimumHeight(180)
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_head = QHBoxLayout()
        card_title = QLabel("Prompt to copy")
        copy = QPushButton("Copy")
        copy.setObjectName("copy")
        copy.clicked.connect(lambda _checked=False, ev=event, button=copy: self._copy(ev, button))
        card_head.addWidget(card_title)
        card_head.addStretch(1)
        card_head.addWidget(copy)
        card_layout.addLayout(card_head)
        card_layout.addWidget(prompt)
        body.addWidget(card)

        slice_box = QFrame()
        slice_box.setObjectName("slice")
        slice_layout = QVBoxLayout(slice_box)
        slice_title = QLabel("How the picture is sliced")
        slice_note = QLabel("Columns run across. Rows run down. Set them before you drop the PNG.")
        slice_note.setObjectName("muted")
        slice_note.setWordWrap(True)
        slice_layout.addWidget(slice_title)
        slice_layout.addWidget(slice_note)
        grid = QHBoxLayout()
        cols = QSpinBox()
        rows = QSpinBox()
        cols.setRange(1, 8)
        rows.setRange(1, 8)
        cols.setValue(2)
        rows.setValue(2)
        name = QLineEdit(ghost)
        grid.addWidget(self._field("Columns", cols))
        grid.addWidget(self._field("Rows", rows))
        grid.addWidget(self._field("Name", name), 1)
        slice_layout.addLayout(grid)
        body.addWidget(slice_box)
        body.addStretch(1)

        holder = QWidget()
        holder.setObjectName("holder")
        holder.setLayout(body)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(holder)

        wrap = QVBoxLayout(page)
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.addWidget(scroll)

        self._cards[event] = {
            "motion": motion,
            "show": check,
            "name": name,
            "cols": cols,
            "rows": rows,
            "drop": drop,
            "prompt": prompt,
        }
        name.textChanged.connect(lambda _text, ev=event: self._sync_prompt(ev))
        cols.valueChanged.connect(lambda _value, ev=event: self._sync_prompt(ev))
        rows.valueChanged.connect(lambda _value, ev=event: self._sync_prompt(ev))
        self._refresh_preview(event)
        return page

    def _gemma_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("page")
        body = QVBoxLayout()
        body.setContentsMargins(24, 16, 24, 24)
        body.setSpacing(12)
        crumb = QLabel("GITM   /   Gemma")
        crumb.setObjectName("crumb")
        body.addWidget(crumb)
        note = QLabel("Gemma isi window ka hissa hai. Sirf event aur mood jaata hai, koi typing nahi.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        body.addWidget(note)
        body.addWidget(self.gemma_on)
        body.addWidget(self._field("Model", self.model))
        body.addWidget(self._field("Address", self.url))
        try_button = QPushButton("Try")
        try_button.setObjectName("quiet")
        try_button.clicked.connect(self._try_gemma)
        body.addWidget(try_button, 0, Qt.AlignmentFlag.AlignLeft)
        body.addWidget(self.gemma_status)
        body.addStretch(1)
        holder = QWidget()
        holder.setObjectName("holder")
        holder.setLayout(body)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(holder)
        wrap = QVBoxLayout(page)
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.addWidget(scroll)
        return page

    def _field(self, label: str, widget: QWidget) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        name = QLabel(label)
        name.setObjectName("muted")
        layout.addWidget(name)
        layout.addWidget(widget)
        return box

    def _sync_all_prompts(self) -> None:
        for event in self._cards:
            self._sync_prompt(event)

    def _sync_prompt(self, event: str) -> None:
        card = self._cards[event]
        card["prompt"].setPlainText(
            sheet_prompt(
                card["name"].text().strip() or "the character",
                event,
                card["cols"].value(),
                card["rows"].value(),
            )
        )
        self._refresh_preview(event)

    def _copy(self, event: str, button: QPushButton) -> None:
        QApplication.clipboard().setText(self._cards[event]["prompt"].toPlainText())
        button.setText("Copied")
        self.status.setText("Prompt copy ho gaya. ChatGPT mein paste karo.")
        QTimer.singleShot(1500, lambda: button.setText("Copy"))

    def _import(self, event: str, paths: list) -> None:
        card = self._cards[event]
        name = card["name"].text().strip() or "ghost"
        folder = self._pack_dir() / "characters" / name
        try:
            import_dropped(paths, folder, card["cols"].value(), card["rows"].value())
        except Exception as exc:
            self.status.setText(f"Drop fail: {exc.__class__.__name__}")
            return
        card["drop"].set_ready(name)
        self._refresh_preview(event)
        self._save(quiet=True)
        self.status.setText(f"{name} save ho gaya")

    def _refresh_preview(self, event: str) -> None:
        card = self._cards[event]
        image = self._pack_dir() / "characters" / card["name"].text().strip() / "idle.png"
        if not image.exists():
            card["drop"].set_preview(None)
            return
        pixmap = QPixmap(str(image))
        card["drop"].set_preview(None if pixmap.isNull() else pixmap)

    def _pack_dir(self) -> Path:
        raw = Path(str((self._cfg.get("sprites") or {}).get("pack", "sprites")))
        return raw if raw.is_absolute() else project_root() / raw

    def _try_gemma(self) -> None:
        self.gemma_status.setText("Gemma se pooch raha hoon...")
        threading.Thread(target=self._ask, daemon=True).start()

    def _ask(self) -> None:
        model = self.model.text().strip() or "gemma3:1b"
        url = self.url.text().strip() or "http://127.0.0.1:11434"
        try:
            line = ask_gemma(url, model, "typing", "restless", 20)
            source = model
        except Exception:
            lines = load_fallback_lines(project_root() / "assets" / "lines" / "fallback_lines.json")
            line = fallback_line(lines)
            source = "fallback"
        self.tried.emit(f"{source}: {line}")

    def _show_try(self, text: str) -> None:
        self.gemma_status.setText(text)

    def _save(self, quiet: bool = False) -> None:
        cfg = self._cfg
        cfg["character_look"] = self.look.text().strip() or DEFAULT_LOOK
        cfg.setdefault("sprites", {})
        cfg.setdefault("show", {})
        for action in CATALOG:
            event = action.id
            card = self._cards[event]
            name = card["name"].text().strip()
            cfg["sprites"][_sprite_key(event)] = name
            cfg["show"][event] = card["show"].isChecked()
        cfg.setdefault("ollama", {})
        cfg["ollama"]["model"] = self.model.text().strip() or "gemma3:1b"
        cfg["ollama"]["url"] = self.url.text().strip() or "http://127.0.0.1:11434"
        cfg["ollama"]["enabled"] = self.gemma_on.isChecked()
        save_config(cfg)
        self._on_save(cfg)
        if not quiet:
            self.status.setText("Save ho gaya")

    def closeEvent(self, event) -> None:  # noqa: N802
        event.ignore()
        self.hide()


def _sprite_key(event: str) -> str:
    if event == "halloween":
        return "halloween_typing"
    return event
