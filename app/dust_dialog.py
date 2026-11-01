"""One dialog: heavy folders, TabPFN chances, and a single yes."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QListWidget, QPushButton, QVBoxLayout

from app.dust import FolderRow


class DustDialog(QDialog):
    def __init__(self, rows: list[FolderRow], note: str, minimum: float, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Haunt the disk")
        self._chosen: list[FolderRow] = []
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(note))
        listing = QListWidget()
        suggested = []
        for row in rows:
            chance = "kept" if row.denied else "unscored"
            if row.sweep_prob is not None and not row.denied:
                chance = f"sweep {int(row.sweep_prob * 100)}%"
                if row.sweep_prob >= minimum:
                    suggested.append(row)
            size = f"{row.size_mb:.0f} MB"
            if row.partial:
                size = f"at least {size}"
            listing.addItem(f"{chance}  {size}  {row.kind}  {row.path}")
        layout.addWidget(listing)
        self._suggested = suggested
        button = QPushButton(f"Clear suggested ({len(suggested)})")
        button.clicked.connect(self._accept_suggested)
        layout.addWidget(button)
        self.resize(640, 420)

    def _accept_suggested(self) -> None:
        self._chosen = list(self._suggested)
        self.accept()

    def chosen(self) -> list[FolderRow]:
        return self._chosen
