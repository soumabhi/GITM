"""Desktop and Downloads moves and deletes. Names are never recorded."""

from __future__ import annotations

from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class _Handler(FileSystemEventHandler):
    def __init__(self, emit) -> None:
        self._emit = emit

    def on_moved(self, event) -> None:
        if event.is_directory:
            return
        src = Path(getattr(event, "src_path", ""))
        dest = Path(getattr(event, "dest_path", ""))
        if src.parent == dest.parent:
            self._emit("rename")
            return
        self._emit("move")

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        folder = Path(getattr(event, "src_path", "")).parent.name.lower()
        self._emit("download" if folder == "downloads" else "new_file")

    def on_deleted(self, event) -> None:
        if event.is_directory:
            return
        self._emit("delete")


class FolderWatch:
    def __init__(self, emit, extra_dirs: list[str] | None = None) -> None:
        self._emit = emit
        self._extra = extra_dirs or []
        self._observer = Observer()

    def start(self) -> None:
        handler = _Handler(self._emit)
        home = Path.home()
        folders = [
            home / "Desktop",
            home / "Downloads",
            home / "OneDrive" / "Desktop",
            home / "OneDrive" / "Downloads",
        ]
        folders.extend(Path(item) for item in self._extra)
        for folder in folders:
            if folder.is_dir():
                self._observer.schedule(handler, str(folder), recursive=False)
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join(timeout=2)
