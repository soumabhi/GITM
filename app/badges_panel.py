"""A plain list of the seven badges."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QListWidget, QVBoxLayout

from app.economy import BADGES


class BadgesPanel(QDialog):
    def __init__(self, unlocked: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Badges")
        owned = set(unlocked)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"{len(owned)} of 7"))
        listing = QListWidget()
        for name, detail in BADGES:
            mark = "unlocked" if name in owned else "locked"
            listing.addItem(f"{name} — {detail} ({mark})")
        layout.addWidget(listing)
        self.resize(360, 280)
