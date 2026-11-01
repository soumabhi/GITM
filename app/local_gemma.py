"""Start the Gemma runner that lives inside this app folder on D:."""

from __future__ import annotations

import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import requests

log = logging.getLogger(__name__)

HOST = "127.0.0.1"
PORT = 11434

CHOICES = (
    {"id": "gemma3:1b", "label": "Gemma 3 1B", "size": "0.8 GB", "note": "Short lines. Already in this app."},
    {"id": "gemma3:4b", "label": "Gemma 3 4B", "size": "3.4 GB", "note": "Can look at a picture. Stays in this app folder."},
)
ALLOWED = {item["id"] for item in CHOICES}


def models_dir(root: Path) -> Path:
    path = root / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def runner_exe(root: Path) -> Path | None:
    exe = root / "ollama" / "ollama.exe"
    return exe if exe.exists() else None


def _listening() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=0.4):
            return True
    except OSError:
        return False


def start_bundled_gemma(root: Path) -> None:
    exe = runner_exe(root)
    if exe is None:
        log.info("Gemma runner is not inside the app folder")
        return
    if _listening():
        log.info("Gemma runner is already up")
        return
    env = os.environ.copy()
    env["OLLAMA_MODELS"] = str(models_dir(root))
    env["OLLAMA_HOST"] = f"{HOST}:{PORT}"
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    subprocess.Popen(
        [str(exe), "serve"],
        cwd=str(exe.parent),
        env=env,
        creationflags=flags,
    )
    log.info("Started the Gemma runner from %s", exe.parent.name)


def _status_path(root: Path) -> Path:
    return models_dir(root) / "pull.json"


def _read_pull(root: Path) -> dict:
    path = _status_path(root)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_pull(root: Path, payload: dict) -> None:
    _status_path(root).write_text(json.dumps(payload), encoding="utf-8")


def installed_models() -> set[str]:
    try:
        response = requests.get(f"http://{HOST}:{PORT}/api/tags", timeout=2)
        response.raise_for_status()
        names = set()
        for item in response.json().get("models") or []:
            name = str(item.get("name") or item.get("model") or "")
            if name:
                names.add(name.split()[0])
        return names
    except (OSError, requests.RequestException, ValueError):
        return set()


def model_status(root: Path) -> dict:
    ready = installed_models()
    pull = _read_pull(root)
    if pull.get("status") == "pulling" and time.time() - float(pull.get("at") or 0) > 30:
        pull = {**pull, "status": "stalled"}
    return {
        "choices": [{**item, "ready": item["id"] in ready} for item in CHOICES],
        "pull": pull,
    }


def begin_pull(root: Path, model: str) -> dict:
    if model not in ALLOWED:
        return {"error": "Choose Gemma 3 1B or Gemma 3 4B."}
    if model in installed_models():
        return {"ok": True, "ready": True}
    current = _read_pull(root)
    if current.get("model") == model and current.get("status") == "pulling" and time.time() - float(current.get("at") or 0) < 30:
        return {"ok": True, "pull": current}
    free = shutil.disk_usage(models_dir(root)).free
    if free < 6 * 1024**3:
        return {"error": "This drive needs 6 GB free before that model can be stored here."}
    start_bundled_gemma(root)
    _write_pull(root, {"model": model, "status": "pulling", "completed": 0, "total": 0, "at": time.time()})
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
    subprocess.Popen(
        [sys.executable, "-m", "app.local_gemma", model],
        cwd=str(root),
        env={**os.environ, "PYTHONPATH": str(root), "OLLAMA_MODELS": str(models_dir(root)), "OLLAMA_HOST": f"{HOST}:{PORT}"},
        creationflags=flags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    return {"ok": True}


def pull_model(root: Path, model: str) -> None:
    if model not in ALLOWED:
        _write_pull(root, {"model": model, "status": "error", "error": "Choose Gemma 3 1B or Gemma 3 4B.", "at": time.time()})
        return
    layers: dict[str, tuple[int, int]] = {}
    try:
        with requests.post(
            f"http://{HOST}:{PORT}/api/pull",
            json={"name": model, "stream": True},
            stream=True,
            timeout=None,
        ) as response:
            response.raise_for_status()
            for raw in response.iter_lines():
                if not raw:
                    continue
                try:
                    line = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if line.get("error"):
                    raise RuntimeError(str(line["error"]))
                digest = str(line.get("digest") or "")
                if digest and line.get("total"):
                    layers[digest] = (int(line.get("completed") or 0), int(line["total"]))
                done = sum(item[0] for item in layers.values())
                total = sum(item[1] for item in layers.values())
                _write_pull(
                    root,
                    {
                        "model": model,
                        "status": "success" if line.get("status") == "success" else "pulling",
                        "detail": str(line.get("status") or ""),
                        "completed": done,
                        "total": total,
                        "at": time.time(),
                    },
                )
    except (OSError, requests.RequestException, RuntimeError, ValueError) as exc:
        _write_pull(root, {"model": model, "status": "error", "error": str(exc), "at": time.time()})


def delete_model(model: str) -> dict:
    if model not in ALLOWED:
        return {"error": "Choose Gemma 3 1B or Gemma 3 4B."}
    try:
        response = requests.delete(
            f"http://{HOST}:{PORT}/api/delete",
            json={"model": model, "name": model},
            timeout=120,
        )
        if response.status_code >= 400:
            return {"error": "That model is still in use. Try again in a moment."}
    except (OSError, requests.RequestException) as exc:
        return {"error": str(exc)}
    return {"ok": True}


def main() -> None:
    from app.config import project_root

    model = sys.argv[1] if len(sys.argv) > 1 else ""
    pull_model(project_root(), model)


if __name__ == "__main__":
    main()
