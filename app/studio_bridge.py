"""JSON line bridge for the Electron window. Stdout is protocol only."""

from __future__ import annotations

import base64
import io
import json
import sys
import time
from pathlib import Path

from PIL import Image

from app.config import app_data_dir, load_config, project_root, save_config
from app.local_gemma import ALLOWED, begin_pull, delete_model, installed_models, model_status
from app.projects import create_project, delete_project, get_project, list_projects, load_studio, save_studio
from app.prompts import BY_ID, CATALOG, sheet_prompt
from app.sheet_import import import_dropped
from app.whisper import ask_gemma, fallback_line, load_fallback_lines


def sprite_key(event: str) -> str:
    if event == "halloween":
        return "halloween_typing"
    return event


def pack_dir(cfg: dict) -> Path:
    raw = Path(str((cfg.get("sprites") or {}).get("pack", "sprites")))
    return raw if raw.is_absolute() else project_root() / raw


def preview_clip(cfg: dict, name: str) -> dict:
    empty = {"src": "", "frameWidth": 0, "frameHeight": 0, "frames": 0}
    folder = pack_dir(cfg) / "characters" / name
    image_path = folder / "idle.png"
    if not name or not image_path.exists():
        return empty
    image = Image.open(image_path).convert("RGBA")
    width, height, count = image.width, image.height, 1
    meta_path = folder / "idle.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            width = int(meta.get("frameWidth") or width)
            height = int(meta.get("frameHeight") or height)
            count = int(meta.get("frames") or max(1, image.width // max(1, width)))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return {
        "src": f"data:image/png;base64,{encoded}",
        "frameWidth": width,
        "frameHeight": height,
        "frames": max(1, count),
    }


def state(req: dict | None = None) -> dict:
    cfg = load_config()
    project_id = str((req or {}).get("projectId") or "")
    project = get_project(project_id) if project_id else None
    if project_id and project is None:
        return {"error": "This project is not on this computer."}
    saved = load_studio(project_id) if project else None
    ollama = dict(cfg.get("ollama") or {})
    chosen = saved.get("actions") if saved else []
    if not isinstance(chosen, list):
        chosen = []
    stored = {str(action.get("id") or ""): action for action in chosen if isinstance(action, dict)}
    actions = []
    for spec in CATALOG:
        action = stored.get(spec.id) or {}
        actions.append(
            {
                "id": spec.id,
                "title": spec.title,
                "group": spec.group,
                "name": spec.id,
                "motion": spec.motion,
                "show": bool(action.get("show", True)) if action else True,
                "preview": preview_clip(cfg, spec.id),
            }
        )
    return {
        "project": project,
        "actions": actions,
        "catalog": [{"id": item.id, "title": item.title, "group": item.group} for item in CATALOG],
        "gemma": {
            "enabled": bool(ollama.get("enabled", True)),
            "model": str(ollama.get("model", "gemma3:1b")),
            "url": str(ollama.get("url", "http://127.0.0.1:11434")),
        },
        "look": look_view(cfg),
        "looks": looks_view(cfg),
    }


_LOOK_IDS = ("typing", "copy", "paste", "delete", "enter", "screenshot", "scroll", "idle", "move", "pet")


def _stored_look(raw: dict | None, overlay: dict) -> dict:
    src = raw if isinstance(raw, dict) else {}
    opacity = src.get("opacity", overlay.get("opacity", 1))
    try:
        opacity_f = float(opacity)
    except (TypeError, ValueError):
        opacity_f = 1.0
    if opacity_f > 1:
        opacity_f = opacity_f / 100
    return {
        "size": max(80, min(420, int(src.get("size", overlay.get("size", 192))))),
        "opacity": max(0.2, min(1.0, opacity_f)),
        "x": max(0, min(100, int(src.get("x", overlay.get("x", 100))))),
        "y": max(0, min(100, int(src.get("y", overlay.get("y", 0))))),
        "ask": bool(src.get("ask", overlay.get("ask", False))),
        "question": str(src.get("question", overlay.get("question", "")) or "")[:240],
        "speed": max(25, min(200, int(src.get("speed", overlay.get("speed", 100))))),
    }


def ensure_looks(cfg: dict) -> dict:
    overlay = cfg.get("overlay") or {}
    looks = cfg.setdefault("looks", {})
    for action in _LOOK_IDS:
        looks[action] = _stored_look(looks.get(action) if isinstance(looks.get(action), dict) else None, overlay)
    return looks


def look_for_ui(stored: dict) -> dict:
    return {
        "size": int(stored["size"]),
        "opacity": int(round(float(stored["opacity"]) * 100)),
        "x": int(stored["x"]),
        "y": int(stored["y"]),
        "ask": bool(stored["ask"]),
        "question": stored["question"],
        "say": "",
        "speed": int(stored.get("speed", 100)),
    }


def look_view(cfg: dict) -> dict:
    overlay = cfg.get("overlay") or {}
    return look_for_ui(_stored_look(None, overlay))


def looks_view(cfg: dict) -> dict:
    before = cfg.get("looks") if isinstance(cfg.get("looks"), dict) else {}
    missing = any(action not in before for action in _LOOK_IDS)
    view = {action: look_for_ui(stored) for action, stored in ensure_looks(cfg).items()}
    if missing:
        save_config(cfg)
    return view


def set_look(body: dict) -> dict:
    cfg = load_config()
    overlay = cfg.setdefault("overlay", {})
    action = str(body.get("id") or "typing")
    looks = ensure_looks(cfg)
    current = looks.get(action) if action in looks else _stored_look(None, overlay)
    nxt = _stored_look(current, overlay)
    if "size" in body:
        nxt["size"] = max(80, min(420, int(body.get("size", nxt["size"]))))
    if "opacity" in body:
        nxt["opacity"] = max(0.2, min(1.0, float(body.get("opacity", 100)) / 100))
    if "x" in body:
        nxt["x"] = max(0, min(100, int(body.get("x", nxt["x"]))))
    if "y" in body:
        nxt["y"] = max(0, min(100, int(body.get("y", nxt["y"]))))
    if "ask" in body:
        nxt["ask"] = bool(body.get("ask"))
    if "question" in body:
        nxt["question"] = str(body.get("question") or "")[:240]
    if "speed" in body:
        nxt["speed"] = max(25, min(200, int(body.get("speed", nxt.get("speed", 100)))))
    if action in _LOOK_IDS:
        looks[action] = nxt
    else:
        looks[action] = nxt
    save_config(cfg)
    signal = {
        "size": nxt["size"],
        "opacity": nxt["opacity"],
        "x": nxt["x"],
        "y": nxt["y"],
        "ask": nxt["ask"],
        "question": nxt["question"],
        "say": "",
        "speed": nxt.get("speed", 100),
        "action": action,
    }
    (app_data_dir() / "look.json").write_text(json.dumps(signal), encoding="utf-8")
    view = look_for_ui(nxt)
    view["id"] = action
    return view


def read_line() -> dict:
    path = app_data_dir() / "line.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"text": "", "at": 0}
    return {"text": str(data.get("text") or ""), "at": data.get("at") or 0}


def do_prompt(body: dict) -> dict:
    text = sheet_prompt(str(body.get("name") or "the character"), str(body.get("id") or ""))
    return {"text": text}


def do_save(body: dict) -> dict:
    project_id = str(body.get("projectId") or "")
    if project_id:
        if get_project(project_id) is None:
            return {"error": "This project is not on this computer."}
        save_studio(project_id, body)
    cfg = load_config()
    cfg.setdefault("sprites", {})
    cfg.setdefault("show", {})
    present: set[str] = set()
    for action in body.get("actions") or []:
        event = str(action.get("id") or "")
        if event not in BY_ID:
            continue
        present.add(event)
        cfg["sprites"][sprite_key(event)] = event
        cfg["show"][event] = bool(action.get("show", True))
    for event in BY_ID:
        if event not in present:
            cfg["show"][event] = False
    if "gemma" in body:
        gemma = body.get("gemma") or {}
        cfg.setdefault("ollama", {})
        chosen = str(gemma.get("model") or "gemma3:1b").strip()
        cfg["ollama"]["model"] = chosen if chosen in ALLOWED else "gemma3:1b"
        cfg["ollama"]["url"] = str(gemma.get("url") or "http://127.0.0.1:11434").strip() or "http://127.0.0.1:11434"
        cfg["ollama"]["enabled"] = bool(gemma.get("enabled", True))
    fresh = load_config()
    if isinstance(fresh.get("overlay"), dict):
        cfg["overlay"] = fresh["overlay"]
    if isinstance(fresh.get("looks"), dict):
        cfg["looks"] = fresh["looks"]
    save_config(cfg)
    return {"ok": True}


def do_import(body: dict) -> dict:
    event = str(body.get("id") or "").strip()
    if event not in BY_ID:
        return {"error": "Choose an action."}
    cfg = load_config()
    folder = pack_dir(cfg) / "characters" / event
    import_dropped([Path(str(body.get("path") or ""))], folder, 4, 2)
    cfg.setdefault("sprites", {})
    cfg["sprites"][sprite_key(event)] = event
    save_config(cfg)
    return {"ok": True, "preview": preview_clip(cfg, event)}


def models_view() -> dict:
    cfg = load_config()
    ollama = cfg.get("ollama") or {}
    status = model_status(project_root())
    status["active"] = str(ollama.get("model") or "gemma3:1b")
    status["enabled"] = bool(ollama.get("enabled", True))
    return status


def use_model(body: dict) -> dict:
    cfg = load_config()
    ollama = cfg.setdefault("ollama", {})
    model = str(body.get("model") or "").strip()
    if model:
        if model not in ALLOWED:
            return {"error": "Choose Gemma 3 1B or Gemma 3 4B."}
        ollama["model"] = model
    if "enabled" in body:
        ollama["enabled"] = bool(body.get("enabled"))
    save_config(cfg)
    return models_view()


def remove_model(model: str) -> dict:
    current = model_status(project_root()).get("pull") or {}
    if current.get("model") == model and current.get("status") == "pulling":
        return {"error": "Wait until the download finishes."}
    removed = delete_model(model)
    if removed.get("error"):
        return removed
    cfg = load_config()
    ollama = cfg.setdefault("ollama", {})
    if str(ollama.get("model") or "") == model:
        other = next((item for item in ALLOWED if item != model and item in installed_models()), "")
        ollama["model"] = other or "gemma3:1b"
    save_config(cfg)
    return models_view()


def set_power(body: dict) -> dict:
    cfg = load_config()
    if "enabled" in body:
        cfg["enabled"] = bool(body.get("enabled"))
        save_config(cfg)
    return {"enabled": bool(load_config().get("enabled", True))}


def _slot_preview(png: Path, meta_path: Path) -> dict:
    empty = {"src": "", "frameWidth": 0, "frameHeight": 0, "frames": 0}
    if not png.exists():
        return empty
    image = Image.open(png).convert("RGBA")
    width, height, count = image.width, image.height, 1
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            width = int(meta.get("frameWidth") or width)
            height = int(meta.get("frameHeight") or height)
            count = int(meta.get("frames") or max(1, image.width // max(1, width)))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return {
        "src": f"data:image/png;base64,{encoded}",
        "frameWidth": width,
        "frameHeight": height,
        "frames": max(1, count),
    }


def pet_visits_folder(cfg: dict) -> Path:
    return pack_dir(cfg) / "characters" / "pet" / "visits"


def pet_state() -> dict:
    folder = pet_visits_folder(load_config())
    visits = []
    for index in range(3):
        place = folder / str(index)
        sheet = place / "idle.png"
        preview = _slot_preview(sheet, place / "idle.json") if sheet.exists() else None
        visits.append(
            {
                "id": str(index),
                "title": f"Visit {index + 1}",
                "preview": preview,
            }
        )
    return {"visits": visits}


def pet_image(body: dict) -> dict:
    from app.sheet_import import knock_out_green, save_character

    slot = str(body.get("slot") or "")
    if slot not in {"0", "1", "2"}:
        return {"error": "Choose visit 1, 2, or 3."}
    place = pet_visits_folder(load_config()) / slot
    place.mkdir(parents=True, exist_ok=True)
    if body.get("remove"):
        for path in place.glob("*"):
            try:
                path.unlink()
            except OSError:
                pass
        return pet_state()
    source = Path(str(body.get("path") or ""))
    if source.suffix.lower() != ".png" or not source.exists():
        return {"error": "PNG only"}
    image = knock_out_green(Image.open(source).convert("RGBA"))
    if image.width >= int(image.height * 1.8):
        count = max(1, round(image.width / image.height))
        frame_w = max(1, image.width // count)
        frames = [image.crop((index * frame_w, 0, (index + 1) * frame_w, image.height)) for index in range(count)]
    else:
        frames = [image]
    save_character(frames, place)
    return pet_state()


def pet_care(body: dict) -> dict:
    del body
    return {"ok": True}


def do_gemma(body: dict) -> dict:
    model = str(body.get("model") or "gemma3:1b").strip() or "gemma3:1b"
    if model not in ALLOWED:
        model = "gemma3:1b"
    url = str(body.get("url") or "http://127.0.0.1:11434").strip() or "http://127.0.0.1:11434"
    try:
        line = ask_gemma(url, model, "typing", "restless", 20)
        source = model
    except Exception:
        lines = load_fallback_lines(project_root() / "assets" / "lines" / "fallback_lines.json")
        line = fallback_line(lines)
        source = "fallback"
    return {"source": source, "line": line}


def handle(req: dict) -> dict:
    op = req.get("op")
    if op == "projects":
        return {"projects": list_projects(), "enabled": bool(load_config().get("enabled", True))}
    if op == "power":
        return set_power(req)
    if op == "look":
        return set_look(req)
    if op == "line":
        return read_line()
    if op == "petState":
        return pet_state()
    if op == "petImage":
        return pet_image(req)
    if op == "petCare":
        return pet_care(req)
    if op == "createProject":
        return create_project(str(req.get("name") or ""), str(req.get("notes") or ""))
    if op == "deleteProject":
        return delete_project(str(req.get("id") or ""))
    if op == "state":
        return state(req)
    if op == "prompt":
        return do_prompt(req)
    if op == "save":
        return do_save(req)
    if op == "import":
        return do_import(req)
    if op == "gemma":
        return do_gemma(req)
    if op == "models":
        return models_view()
    if op == "useModel":
        return use_model(req)
    if op == "pull":
        return begin_pull(project_root(), str(req.get("model") or ""))
    if op == "deleteModel":
        return remove_model(str(req.get("model") or ""))
    return {"error": "unknown"}


def main() -> None:
    for line in sys.stdin:
        text = line.strip()
        if not text:
            continue
        try:
            result = handle(json.loads(text))
        except Exception as exc:
            result = {"error": exc.__class__.__name__}
        sys.stdout.write(json.dumps(result) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
