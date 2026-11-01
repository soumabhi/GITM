from datetime import datetime

from app.halloween import theme_for


def test_halloween_day_and_evening():
    day = theme_for(datetime(2026, 10, 31, 13, 0))
    night = theme_for(datetime(2026, 10, 31, 20, 0))
    assert day.tooltip == "Halloween Mode"
    assert day.pumpkin and day.tint == (255, 140, 0)
    assert night.tint == (170, 20, 20)


def test_dia_de_los_muertos_and_ordinary_day():
    holiday = theme_for(datetime(2026, 11, 2, 9, 0))
    ordinary = theme_for(datetime(2026, 11, 3, 9, 0))
    assert not holiday.marigold and holiday.tooltip == "Dia de los Muertos"
    assert ordinary.tint is None and not ordinary.marigold
