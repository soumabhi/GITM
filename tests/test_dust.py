import json
from pathlib import Path

from PIL import Image

from app.dust import is_denied, kind_of, read_history, safe_to_delete
from app.sprites import load_character_dir
from app.tabpfn_dust import both_labels


def test_cursor_documents_and_windows_are_denied():
    assert is_denied(Path(r"C:\Users\ABHISHEK\AppData\Roaming\Cursor"))
    assert is_denied(Path(r"D:\cursor"))
    assert is_denied(Path(r"C:\Users\ABHISHEK\Documents\notes"))
    assert is_denied(Path(r"C:\Windows\Temp"))
    assert not is_denied(Path(r"C:\Users\ABHISHEK\.gemini"))


def test_kinds_match_the_real_cleanup():
    assert kind_of(Path(r"C:\Users\ABHISHEK\.cache")) == "cache"
    assert kind_of(Path(r"C:\Users\ABHISHEK\.gemini")) == "chat"
    assert kind_of(Path(r"C:\Users\ABHISHEK\AppData\Roaming\Cursor")) == "editor"


def test_home_itself_cannot_be_deleted():
    assert not safe_to_delete(Path.home())


def test_seed_history_has_both_choices():
    rows = read_history(Path("assets/dust/seed_labels.csv"))
    assert both_labels(rows)


def test_sprite_strip_slices_on_the_json(tmp_path):
    image = Image.new("RGBA", (20, 10), (0, 0, 0, 0))
    image.paste(Image.new("RGBA", (10, 10), (255, 0, 0, 255)), (0, 0))
    image.paste(Image.new("RGBA", (10, 10), (0, 255, 0, 255)), (10, 0))
    image.save(tmp_path / "idle.png")
    (tmp_path / "idle.json").write_text(
        json.dumps({"image": "idle.png", "frameWidth": 10, "frameHeight": 10, "frames": 2, "style": "pixel"}),
        encoding="utf-8",
    )
    frames = load_character_dir(tmp_path)
    assert len(frames) == 2
    assert frames[0].getpixel((1, 1))[0] == 255
    assert frames[1].getpixel((1, 1))[1] == 255
