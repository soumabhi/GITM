"""Find heavy folders and clear only junk the user has agreed to."""

from __future__ import annotations

import csv
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

DENY_PARTS = {
    "cursor",
    ".cursor",
    "windows",
    "program files",
    "program files (x86)",
    "documents",
    "desktop",
    "package cache",
    "ghostinthemachine",
    "system32",
    "winsxs",
}

BROAD_NAMES = {
    "users",
    "appdata",
    "local",
    "roaming",
    "programdata",
    "windows",
    "downloads",
}


@dataclass
class FolderRow:
    path: str
    kind: str
    size_mb: float
    age_days: float
    on_c: int
    name_has_cache: int
    denied: bool
    partial: bool = False
    sweep_prob: float | None = None

    def features(self) -> dict:
        return {
            "kind": self.kind,
            "size_mb": round(self.size_mb, 1),
            "age_days": round(self.age_days, 1),
            "on_c": self.on_c,
            "name_has_cache": self.name_has_cache,
        }


def is_denied(path: Path) -> bool:
    parts = [part.lower() for part in path.parts]
    if any(part in DENY_PARTS for part in parts):
        return True
    if path.name.lower() in BROAD_NAMES:
        return True
    return False


def kind_of(path: Path) -> str:
    name = path.name.lower()
    parts = [part.lower() for part in path.parts]
    if "cursor" in parts:
        return "editor"
    if "windows" in parts or "package cache" in name:
        return "windows"
    if any("gemini" in part for part in parts) or name in {"conversations", "knowledge"}:
        return "chat"
    if "plugin" in name:
        return "plugins"
    if "runtime" in name:
        return "runtime"
    if "cache" in name or name in {"temp", "tmp", ".cache"}:
        return "cache"
    if name.startswith("."):
        return "dotfolder"
    return "other"


def quick_size(path: Path, max_files: int) -> tuple[float, bool]:
    total = 0
    seen = 0
    stack = [path]
    partial = False
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    seen += 1
                    if seen > max_files:
                        partial = True
                        return total / (1024 * 1024), partial
                    try:
                        if entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                        elif entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                    except OSError:
                        continue
        except OSError:
            continue
    return total / (1024 * 1024), partial


def row_for(path: Path, max_files: int = 2500) -> FolderRow:
    denied = is_denied(path)
    try:
        age_days = max(0.0, (time.time() - path.stat().st_mtime) / 86400)
    except OSError:
        age_days = 0.0
    if denied:
        size_mb, partial = 0.0, False
    else:
        size_mb, partial = quick_size(path, max_files)
    drive = str(path).upper().startswith("C:")
    return FolderRow(
        path=str(path),
        kind=kind_of(path),
        size_mb=size_mb,
        age_days=age_days,
        on_c=1 if drive else 0,
        name_has_cache=1 if "cache" in path.name.lower() else 0,
        denied=denied,
        partial=partial,
    )


def scan_roots(extra_dirs: list[str] | None = None) -> list[FolderRow]:
    home = Path.home()
    local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    roaming = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    roots = [home, local, roaming, Path("D:/")]
    rows: list[FolderRow] = []
    seen: set[str] = set()
    deadline = time.monotonic() + 12
    for root in roots:
        if not root.exists() or time.monotonic() > deadline:
            continue
        try:
            children = [child for child in root.iterdir() if child.is_dir()]
        except OSError:
            continue
        for child in children:
            if time.monotonic() > deadline:
                break
            key = str(child).lower()
            if key in seen:
                continue
            seen.add(key)
            budget = 8000 if "cache" in child.name.lower() or child.name.startswith(".") else 1500
            rows.append(row_for(child, budget))
    for extra in extra_dirs or []:
        path = Path(extra)
        if path.exists() and str(path).lower() not in seen:
            rows.append(row_for(path, 500))
    rows.sort(key=lambda item: item.size_mb, reverse=True)
    heavy = [item for item in rows if item.size_mb >= 50 or item.denied]
    return heavy[:20]


def safe_to_delete(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    if not resolved.exists() or not resolved.is_dir():
        return False
    if is_denied(resolved):
        return False
    if resolved == Path.home().resolve():
        return False
    anchor = Path(resolved.anchor)
    if resolved.parent == anchor:
        return False
    home = Path.home().resolve()
    under_home = False
    try:
        resolved.relative_to(home)
        under_home = True
    except ValueError:
        under_home = False
    under_d = resolved.drive.upper() == "D:" and resolved != anchor
    return under_home or under_d


def delete_tree(path: Path) -> int:
    if not safe_to_delete(path):
        return 0
    freed = 0
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            file_path = Path(root) / name
            try:
                freed += file_path.stat().st_size
                file_path.unlink()
            except OSError:
                continue
        for name in dirs:
            try:
                (Path(root) / name).rmdir()
            except OSError:
                continue
    try:
        path.rmdir()
    except OSError:
        pass
    return freed


def empty_children(path: Path) -> int:
    if not path.exists() or not path.is_dir() or is_denied(path):
        return 0
    freed = 0
    try:
        children = list(path.iterdir())
    except OSError:
        return 0
    for child in children:
        if is_denied(child):
            continue
        try:
            if child.is_dir():
                freed += delete_tree(child) if safe_to_delete(child) else 0
            else:
                size = child.stat().st_size
                child.unlink()
                freed += size
        except OSError:
            continue
    return freed


def temp_targets() -> list[Path]:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    targets = [
        Path(os.environ.get("TEMP", "")),
        local / "Temp",
        local / "CrashDumps",
        local / "pip" / "Cache",
        local / "Microsoft" / "Windows" / "WER",
        local / "Microsoft" / "Windows" / "DeliveryOptimization" / "Cache",
        local / "Microsoft" / "Windows" / "Explorer",
    ]
    return [path for path in targets if path.exists()]


def sweep_temp() -> int:
    freed = 0
    for path in temp_targets():
        if path.name.lower() == "explorer":
            for child in path.glob("thumbcache_*.db"):
                try:
                    size = child.stat().st_size
                    child.unlink()
                    freed += size
                except OSError:
                    continue
            continue
        freed += empty_children(path)
    freed += _empty_recycle_bin()
    return freed


def _empty_recycle_bin() -> int:
    try:
        import ctypes

        flags = 0x00000001 | 0x00000002 | 0x00000004
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
    except Exception:
        return 0
    return 0


def read_history(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_history(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["kind", "size_mb", "age_days", "on_c", "name_has_cache", "label"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def seed_history(seed: Path, dest: Path) -> None:
    if dest.exists() or not seed.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(seed, dest)


def append_decision(path: Path, row: FolderRow, label: str) -> None:
    history = read_history(path)
    features = row.features()
    features["label"] = label
    history.append(features)
    write_history(path, history)
