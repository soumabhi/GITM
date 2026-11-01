from datetime import datetime

from app.economy import Economy, fresh_state, mood_for


def test_mood_steps():
    assert mood_for(0) == "dormant"
    assert mood_for(1) == "restless"
    assert mood_for(10) == "haunted"
    assert mood_for(30) == "possessed"


def test_reaction_and_first_badge(tmp_path):
    economy = Economy(tmp_path / "state.json", fresh_state())
    economy.record("typing")
    unlocked = economy.newly_unlocked(datetime(2026, 10, 30, 12, 0))
    assert economy.state["ectoplasm"] == 1
    assert economy.state["counters"]["typing"] == 1
    assert "first_haunting" in unlocked
    assert "halloween_haunter" not in unlocked


def test_halloween_badge_only_on_october_31(tmp_path):
    economy = Economy(tmp_path / "state.json", fresh_state())
    economy.record("delete")
    economy.newly_unlocked(datetime(2026, 11, 1, 12, 0))
    assert "halloween_haunter" not in economy.state["badges"]
    unlocked = economy.newly_unlocked(datetime(2026, 10, 31, 21, 0))
    assert "halloween_haunter" in unlocked


def test_badges_unlock_once_and_round_trip(tmp_path):
    path = tmp_path / "state.json"
    economy = Economy(path, fresh_state())
    for _ in range(5):
        economy.record("paste")
    economy.newly_unlocked(datetime(2026, 1, 1))
    economy.save()
    again = Economy.load(path)
    assert again.state["badges"].count("echo") == 1
    assert again.newly_unlocked(datetime(2026, 1, 1)) == []


def test_lights_out_after_quiet_time(tmp_path):
    economy = Economy(tmp_path / "state.json", fresh_state())
    economy.tick_idle(300)
    assert "lights_out" in economy.newly_unlocked(datetime(2026, 6, 1))


def test_state_file_has_no_text_fields(tmp_path):
    path = tmp_path / "state.json"
    economy = Economy(path, fresh_state())
    economy.record("copy")
    economy.save()
    text = path.read_text(encoding="utf-8")
    assert "password" not in text
    assert "clipboard" not in text
