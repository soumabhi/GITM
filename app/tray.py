"""System tray menu."""

from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class Tray:
    def __init__(self, icon: QIcon, on_configure, on_toggle, on_pause, on_badges, on_haunt, on_temp, on_reset, on_quit) -> None:
        self.icon = QSystemTrayIcon(icon)
        self.icon.setToolTip("GITM")
        menu = QMenu()
        configure = QAction("Configure")
        configure.triggered.connect(on_configure)
        menu.addAction(configure)
        self._toggle = QAction("Hide")
        self._pause = QAction("Pause reactions")
        self._pause.setCheckable(True)
        badges = QAction("Badges")
        haunt = QAction("Haunt the disk")
        temp = QAction("Sweep temp")
        reset = QAction("Reset haunting")
        quit_action = QAction("Quit")
        self._toggle.triggered.connect(on_toggle)
        self._pause.triggered.connect(on_pause)
        badges.triggered.connect(on_badges)
        haunt.triggered.connect(on_haunt)
        temp.triggered.connect(on_temp)
        reset.triggered.connect(on_reset)
        quit_action.triggered.connect(on_quit)
        for action in (self._toggle, self._pause, badges, haunt, temp, reset, quit_action):
            menu.addAction(action)
        self.icon.setContextMenu(menu)
        self.icon.show()

    def set_tooltip(self, text: str) -> None:
        self.icon.setToolTip(text[:250])

    def show_message(self, title: str, text: str) -> None:
        self.icon.showMessage(title, text, QSystemTrayIcon.MessageIcon.Information, 4000)

    def set_hidden(self, hidden: bool) -> None:
        self._toggle.setText("Show" if hidden else "Hide")

    def set_paused(self, paused: bool) -> None:
        self._pause.setChecked(paused)
