"""Load config.yaml and resolve folders that belong to this app."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return ROOT


def app_data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    path = Path(base) / "GhostInTheMachine"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    beside = project_root() / "config.yaml"
    if beside.exists():
        return beside
    bundled = ROOT / "config.yaml"
    return bundled


def load_config() -> dict[str, Any]:
    path = config_path()
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("config.yaml must be a mapping")
    return data


def save_config(data: dict[str, Any]) -> Path:
    path = config_path()
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def setup_logging() -> None:
    log_path = app_data_dir() / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
