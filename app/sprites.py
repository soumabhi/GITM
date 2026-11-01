"""Load SpriteForge strips. A missing ghost is skipped, never invented."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from PIL import Image

log = logging.getLogger(__name__)


def tint_image(image: Image.Image, color: tuple[int, int, int] | None) -> Image.Image:
    if color is None:
        return image
    image = image.convert("RGBA")
    stained = Image.new("RGBA", image.size, (*color, 255))
    blended = Image.blend(image, stained, 0.45)
    blended.putalpha(image.getchannel("A"))
    return blended


def fit_frame(image: Image.Image, box: int = 150) -> Image.Image:
    image = image.convert("RGBA")
    width, height = image.size
    if width <= 0 or height <= 0:
        return image
    scale = min(box / width, box / height)
    size = (max(1, int(width * scale)), max(1, int(height * scale)))
    resample = Image.Resampling.NEAREST if max(width, height) <= 256 else Image.Resampling.LANCZOS
    return image.resize(size, resample)

_FRAME_RE = re.compile(r"(?:frame[_-]?)?(\d+)$", re.IGNORECASE)


def _frame_key(path: Path) -> tuple[int, str]:
    match = _FRAME_RE.search(path.stem)
    number = int(match.group(1)) if match else 10**9
    return number, path.name.lower()


def load_strip(png_path: Path, meta: dict) -> list[Image.Image]:
    image = Image.open(png_path).convert("RGBA")
    width = int(meta.get("frameWidth") or image.width)
    height = int(meta.get("frameHeight") or image.height)
    count = int(meta.get("frames") or max(1, image.width // max(width, 1)))
    frames: list[Image.Image] = []
    for index in range(count):
        left = index * width
        if left + width > image.width or height > image.height:
            log.warning("Missing frame %s in %s; using the first frame", index, png_path.name)
            frames.append(frames[0] if frames else image.copy())
            continue
        frames.append(image.crop((left, 0, left + width, height)))
    if not frames:
        log.warning("Empty strip %s; using the whole image", png_path.name)
        frames.append(image.copy())
    return frames


def load_character_dir(folder: Path) -> list[Image.Image]:
    if not folder.is_dir():
        log.warning("Ghost folder missing: %s", folder.name)
        return []
    json_files = sorted(folder.glob("*.json"))
    for meta_path in json_files:
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            log.warning("Could not read sprite json %s", meta_path.name)
            continue
        if not isinstance(meta, dict):
            continue
        image_name = str(meta.get("image") or f"{meta_path.stem}.png")
        png_path = meta_path.with_name(Path(image_name).name)
        if not png_path.exists():
            png_path = meta_path.with_suffix(".png")
        if png_path.exists():
            return load_strip(png_path, meta)
    frames = sorted(folder.glob("*.png"), key=_frame_key)
    loaded = []
    for path in frames:
        try:
            loaded.append(Image.open(path).convert("RGBA"))
        except OSError:
            log.warning("Could not open frame %s", path.name)
    if not loaded:
        log.warning("No frames in %s", folder.name)
    return loaded


class SpriteLibrary:
    def __init__(self, pack: Path, mapping: dict[str, str]) -> None:
        self.pack = pack
        self.mapping = mapping
        self._cache: dict[str, list[Image.Image]] = {}

    def frames_for(self, event: str, pumpkin: bool) -> list[Image.Image]:
        if event == "pet":
            sets = self.pet_visit_sets()
            return sets[0] if sets else []
        if event == "typing" and pumpkin:
            holiday = self._load_named(self.mapping.get("halloween_typing", "pumpkin"))
            if holiday:
                return holiday
            log.warning("No pumpkin ghost export; Halloween keeps the tint only")
        name = self.mapping.get(event, "")
        return self._load_named(name)

    def pet_visit_sets(self) -> list[list[Image.Image]]:
        """All filled visit sheets, in order. Falls back to pet/idle."""
        options: list[list[Image.Image]] = []
        root = self.pack / "characters" / "pet" / "visits"
        for index in range(3):
            frames = load_character_dir(root / str(index))
            if frames:
                options.append(frames)
        if options:
            return options
        fallback = self._load_named(self.mapping.get("pet", "pet"))
        return [fallback] if fallback else []

    def _load_named(self, name: str) -> list[Image.Image]:
        if not name:
            return []
        if name in self._cache:
            return self._cache[name]
        folder = self.pack / "characters" / name
        frames = load_character_dir(folder)
        self._cache[name] = frames
        return frames
