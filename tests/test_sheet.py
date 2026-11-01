from PIL import Image

from app.prompts import sheet_prompt
from app.sheet_import import import_dropped, knock_out_green


def test_prompt_is_an_eight_frame_sheet():
    text = sheet_prompt("the character", "typing", 4, 2)
    assert "4 columns by 2 rows" in text
    assert "Eight frames" in text
    assert "Frame 1:" in text
    assert "Frame 8:" in text
    assert "#00FF00" in text
    assert "What would you like to generate?" in text
    assert "Do not draw anything yet." in text
    assert "My answer is the only subject." in text
    assert 'for "Typing"' not in text
    assert "no words, no digits" in text


def test_pet_prompt_is_a_simple_come_and_sit_sheet():
    text = sheet_prompt("the character", "pet")
    assert "Eight frames" in text
    assert "come-and-sit" in text or "Sitting" in text or "seated" in text.lower() or "sit" in text.lower()
    assert "What would you like to generate?" in text
    assert "Egg:" not in text


def test_green_screen_becomes_clear_and_saves_a_strip(tmp_path):
    image = Image.new("RGBA", (20, 10), (0, 255, 0, 255))
    image.paste(Image.new("RGBA", (8, 8), (255, 255, 255, 255)), (1, 1))
    image.paste(Image.new("RGBA", (8, 8), (0, 0, 0, 255)), (11, 1))
    source = tmp_path / "sheet.png"
    image.save(source)
    cleared = knock_out_green(Image.open(source))
    assert cleared.getpixel((0, 0))[3] == 0
    assert cleared.getpixel((2, 2))[3] == 255
    saved = import_dropped([source], tmp_path / "sleepy", 2, 1)
    assert saved.name == "idle.png"
    assert (tmp_path / "sleepy" / "idle.json").exists()
