"""Named projects for the Ghost window. Each one keeps its own studio."""

from __future__ import annotations

import json
import re
import secrets
import shutil
from pathlib import Path

from app.config import project_root

_ID = re.compile(r"^prj_[A-Za-z0-9_-]{6,40}$")


def projects_root() -> Path:
    path = project_root() / "projects"
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_projects() -> list[dict]:
    return [_public(item) for item in _index()]


def create_project(name: str, notes: str) -> dict:
    title = name.strip()
    if not title:
        return {"error": "Name the project"}
    item = {"id": "prj_" + secrets.token_urlsafe(8), "name": title, "notes": notes.strip()}
    if not _ID.match(item["id"]):
        item["id"] = "prj_" + secrets.token_hex(6)
    rows = _index()
    rows.append(item)
    _write_index(rows)
    folder = projects_root() / item["id"]
    folder.mkdir(parents=True, exist_ok=True)
    _write_studio(item["id"], snapshot_config())
    return {"project": _public(item)}


def delete_project(project_id: str) -> dict:
    if get_project(project_id) is None:
        return {"error": "This project is not on this computer."}
    _write_index([item for item in _index() if item["id"] != project_id])
    folder = projects_root() / project_id
    if folder.is_dir():
        shutil.rmtree(folder)
    return {"ok": True}


def get_project(project_id: str) -> dict | None:
    if not _ID.match(project_id):
        return None
    for item in _index():
        if item["id"] == project_id:
            return _public(item)
    return None


def load_studio(project_id: str) -> dict | None:
    if get_project(project_id) is None:
        return None
    path = projects_root() / project_id / "studio.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def save_studio(project_id: str, body: dict) -> None:
    if get_project(project_id) is None:
        return
    _write_studio(
        project_id,
        {
            "actions": [
                {
                    "id": str(action.get("id") or ""),
                    "name": str(action.get("name") or "").strip(),
                    "show": bool(action.get("show", True)),
                }
                for action in body.get("actions") or []
                if str(action.get("id") or "")
            ],
        },
    )


def snapshot_config() -> dict:
    return {"actions": []}


def _public(item: dict) -> dict:
    return {"id": item["id"], "name": item["name"], "notes": item.get("notes") or ""}


def _index_path() -> Path:
    return projects_root() / "index.json"


def _index() -> list[dict]:
    path = _index_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = data.get("projects") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []
    return [item for item in rows if isinstance(item, dict) and _ID.match(str(item.get("id") or ""))]


def _write_index(rows: list[dict]) -> None:
    _index_path().write_text(json.dumps({"projects": rows}, indent=2), encoding="utf-8")


def _write_studio(project_id: str, studio: dict) -> None:
    path = projects_root() / project_id / "studio.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(studio, indent=2), encoding="utf-8")
