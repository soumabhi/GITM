"""Turn a dropped ChatGPT sheet into frames the ghost can play."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


def knock_out_green(image: Image.Image) -> Image.Image:
    """Drop whatever flat color sits in the corners. Green, white, or any other screen."""
    image = image.convert("RGBA")
    width, height = image.size
    raw = bytearray(image.tobytes())
    if not _already_clear(raw):
        key = _corner_key(raw, width, height)
        if _saturation(key) >= 40 and _border_ratio(raw, width, height, key) >= 0.7:
            _chroma(raw, key)
        elif _saturation(key) >= 40:
            _flood(raw, width, height, key)
        else:
            _flat(raw, key)
    _clean_rim(raw, width, height)
    return Image.frombytes("RGBA", (width, height), bytes(raw))


def slice_grid(image: Image.Image, cols: int, rows: int) -> list[Image.Image]:
    cols = max(1, cols)
    rows = max(1, rows)
    cell_w = max(1, image.width // cols)
    cell_h = max(1, image.height // rows)
    frames: list[Image.Image] = []
    for row in range(rows):
        for col in range(cols):
            box = (col * cell_w, row * cell_h, (col + 1) * cell_w, (row + 1) * cell_h)
            frames.append(image.crop(box))
    return frames


def save_character(frames: list[Image.Image], folder: Path) -> Path:
    if not frames:
        raise ValueError("no frames")
    folder.mkdir(parents=True, exist_ok=True)
    cell_w, cell_h = frames[0].size
    strip = Image.new("RGBA", (cell_w * len(frames), cell_h), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        strip.paste(frame, (index * cell_w, 0))
    image_path = folder / "idle.png"
    strip.save(image_path)
    meta = {
        "image": "idle.png",
        "frameWidth": cell_w,
        "frameHeight": cell_h,
        "frames": len(frames),
        "style": "detailed",
        "layout": "horizontal strip, frame N at x = N * frameWidth",
    }
    (folder / "idle.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return image_path


def import_dropped(paths: list[Path], folder: Path, cols: int, rows: int) -> Path:
    images = [knock_out_green(Image.open(path).convert("RGBA")) for path in paths if path.suffix.lower() == ".png"]
    if not images:
        raise ValueError("drop a png")
    frames = slice_grid(images[0], cols, rows) if len(images) == 1 else [knock_out_green(image) for image in images]
    return save_character(frames, folder)


def _ycbcr(red: int, green: int, blue: int) -> tuple[float, float]:
    cb = 128 - 0.168736 * red - 0.331264 * green + 0.5 * blue
    cr = 128 + 0.5 * red - 0.418688 * green - 0.081312 * blue
    return cb, cr


def _saturation(key: tuple[int, int, int]) -> int:
    return max(key) - min(key)


def _already_clear(raw: bytearray) -> bool:
    clear = 0
    solid = 0
    total = len(raw) // 4
    for index in range(3, len(raw), 4):
        alpha = raw[index]
        if alpha < 16:
            clear += 1
        elif alpha > 240:
            solid += 1
    return clear > total * 0.02 and solid > 0


def _corner_key(raw: bytearray, width: int, height: int) -> tuple[int, int, int]:
    points = (0, width - 1, (height - 1) * width, (height - 1) * width + width - 1)
    red = green = blue = 0
    for point in points:
        offset = point * 4
        red += raw[offset]
        green += raw[offset + 1]
        blue += raw[offset + 2]
    return red // 4, green // 4, blue // 4


def _border_ratio(raw: bytearray, width: int, height: int, key: tuple[int, int, int]) -> float:
    key_cb, key_cr = _ycbcr(*key)
    seen = 0
    hit = 0
    for x in range(width):
        for y in (0, height - 1):
            seen, hit = _count_border(raw, x, y, width, key_cb, key_cr, seen, hit)
    for y in range(1, height - 1):
        for x in (0, width - 1):
            seen, hit = _count_border(raw, x, y, width, key_cb, key_cr, seen, hit)
    return hit / seen if seen else 0


def _count_border(raw, x, y, width, key_cb, key_cr, seen, hit):
    offset = (y * width + x) * 4
    cb, cr = _ycbcr(raw[offset], raw[offset + 1], raw[offset + 2])
    seen += 1
    if (cb - key_cb) ** 2 + (cr - key_cr) ** 2 < 30 * 30:
        hit += 1
    return seen, hit


def _chroma(raw: bytearray, key: tuple[int, int, int]) -> None:
    key_cb, key_cr = _ycbcr(*key)
    green_screen = key[1] > key[0] and key[1] > key[2]
    red_screen = key[0] > key[1] and key[0] > key[2]
    blue_screen = key[2] > key[0] and key[2] > key[1]
    for index in range(0, len(raw), 4):
        red, green, blue, alpha = raw[index], raw[index + 1], raw[index + 2], raw[index + 3]
        cb, cr = _ycbcr(red, green, blue)
        dist = ((cb - key_cb) ** 2 + (cr - key_cr) ** 2) ** 0.5
        keep = _smooth(16, 42, dist)
        if green_screen:
            green = min(green, max(red, blue))
        elif red_screen:
            red = min(red, max(green, blue))
        elif blue_screen:
            blue = min(blue, max(red, green))
        raw[index] = red
        raw[index + 1] = green
        raw[index + 2] = blue
        raw[index + 3] = int(alpha * keep)


def _smooth(edge0: float, edge1: float, value: float) -> float:
    span = edge1 - edge0
    amount = 0 if span == 0 else max(0, min(1, (value - edge0) / span))
    return amount * amount * (3 - 2 * amount)


def _flat(raw: bytearray, key: tuple[int, int, int], tol: int = 12) -> None:
    limit = tol * tol
    for index in range(0, len(raw), 4):
        dr = raw[index] - key[0]
        dg = raw[index + 1] - key[1]
        db = raw[index + 2] - key[2]
        if dr * dr + dg * dg + db * db <= limit:
            raw[index + 3] = 0


def _clean_rim(raw: bytearray, width: int, height: int) -> None:
    """Peel the green fringe the way the sprite studio cleans an edge, then drop the leftover halo."""
    key_cb, key_cr = _ycbcr(0, 255, 0)
    count = width * height
    for _pass in range(2):
        alpha = bytearray(raw[index + 3] for index in range(0, len(raw), 4))
        for y in range(height):
            for x in range(width):
                point = y * width + x
                if alpha[point] <= 16:
                    raw[point * 4 + 3] = 0
                    continue
                if not _touches_clear(alpha, x, y, width, height):
                    continue
                offset = point * 4
                red, green, blue = raw[offset], raw[offset + 1], raw[offset + 2]
                cb, cr = _ycbcr(red, green, blue)
                dist = ((cb - key_cb) ** 2 + (cr - key_cr) ** 2) ** 0.5
                if dist < 48 or green > max(red, blue) + 18:
                    raw[offset + 3] = 0
                    continue
                if min(red, blue) > green + 40:
                    raw[offset] = (red + green) // 2
                    raw[offset + 2] = (blue + green) // 2
                raw[offset + 1] = min(green, max(red, blue))
                raw[offset + 3] = 0 if alpha[point] < 160 else 255
        del _pass
    alpha = bytearray(raw[index + 3] for index in range(0, len(raw), 4))
    alone: list[int] = []
    for y in range(height):
        for x in range(width):
            point = y * width + x
            if alpha[point] == 0:
                continue
            near = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and alpha[ny * width + nx] > 0:
                        near += 1
            if near < 2:
                alone.append(point)
    for point in alone:
        raw[point * 4 + 3] = 0
    for point in range(count):
        offset = point * 4
        pixel = raw[offset + 3]
        if pixel in (0, 255):
            continue
        x = point % width
        y = point // width
        if _neighbor_clear(raw, x, y, width, height):
            raw[offset + 3] = 0


def _touches_clear(alpha: bytearray, x: int, y: int, width: int, height: int) -> bool:
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if nx < 0 or ny < 0 or nx >= width or ny >= height or alpha[ny * width + nx] <= 16:
            return True
    return False


def _neighbor_clear(raw: bytearray, x: int, y: int, width: int, height: int) -> bool:
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if nx < 0 or ny < 0 or nx >= width or ny >= height:
            return True
        if raw[(ny * width + nx) * 4 + 3] == 0:
            return True
    return False


def _flood(raw: bytearray, width: int, height: int, key: tuple[int, int, int]) -> None:
    tol = 42
    seen = bytearray(width * height)
    stack: list[int] = []

    def push(x: int, y: int) -> None:
        if x < 0 or y < 0 or x >= width or y >= height:
            return
        point = y * width + x
        if seen[point]:
            return
        offset = point * 4
        dr = raw[offset] - key[0]
        dg = raw[offset + 1] - key[1]
        db = raw[offset + 2] - key[2]
        if (dr * dr + dg * dg + db * db) ** 0.5 > tol:
            return
        seen[point] = 1
        stack.append(point)

    for x in range(width):
        push(x, 0)
        push(x, height - 1)
    for y in range(height):
        push(0, y)
        push(width - 1, y)
    while stack:
        point = stack.pop()
        raw[point * 4 + 3] = 0
        x = point % width
        y = point // width
        push(x + 1, y)
        push(x - 1, y)
        push(x, y + 1)
        push(x, y - 1)
