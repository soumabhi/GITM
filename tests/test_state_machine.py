from app.state_machine import CooldownGate


def test_first_event_is_allowed():
    gate = CooldownGate({"typing": 3000})
    assert gate.allow("typing", 10.0)


def test_cooldown_blocks_then_opens():
    gate = CooldownGate({"copy": 1500, "move": 2000})
    assert gate.allow("copy", 0.0)
    assert not gate.allow("copy", 1.0)
    assert gate.allow("copy", 1.5)
    assert gate.allow("move", 1.0)


def test_events_do_not_share_a_cooldown():
    gate = CooldownGate({"typing": 3000, "delete": 1000})
    assert gate.allow("typing", 0.0)
    assert gate.allow("delete", 0.1)
