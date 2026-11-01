"""GITM — Ghost in the Machine."""

from __future__ import annotations

import ctypes
import logging
import os
import sys

# Cursor/agent shells sometimes export QT_QPA_PLATFORM=offscreen. That makes the
# ghost "play" into a fake buffer with no desktop window — typing looks broken.
if sys.platform == "win32":
    os.environ["QT_QPA_PLATFORM"] = "windows"
else:
    os.environ.pop("QT_QPA_PLATFORM", None)

from PySide6.QtWidgets import QApplication

from app.config import load_config, setup_logging
from app.runtime import Runtime

log = logging.getLogger(__name__)

_ENGINE_MUTEX = None


def _claim_engine() -> bool:
    """Only one engine may run. Extra launches exit quietly."""
    global _ENGINE_MUTEX
    if sys.platform != "win32":
        return True
    kernel32 = ctypes.windll.kernel32
    kernel32.SetLastError(0)
    handle = kernel32.CreateMutexW(None, True, "Local\\GITMEngine")
    if not handle:
        return True
    if kernel32.GetLastError() == 183:
        kernel32.CloseHandle(handle)
        return False
    _ENGINE_MUTEX = handle
    return True


def main() -> None:
    setup_logging()
    engine = "--engine" in sys.argv
    if engine and not _claim_engine():
        log.info("Engine already running; this launch exits")
        raise SystemExit(0)
    argv = [arg for arg in sys.argv if arg != "--engine"]
    app = QApplication(argv)
    app.setApplicationName("GITM")
    app.setQuitOnLastWindowClosed(False)
    runtime = Runtime(load_config(), engine=engine)
    runtime.start()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
