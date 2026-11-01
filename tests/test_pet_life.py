"""The pet clock follows the Tamagotchi rules."""

from pathlib import Path

from app.pet_life import BABY_S, CALL_S, EGG_S, HUNGER_S, PetLife, adult_index


def life(tmp_path: Path) -> PetLife:
    pet = PetLife(tmp_path / "pet.json")
    pet.reset(1_000_000)
    return pet


def test_egg_hatches(tmp_path: Path) -> None:
    pet = life(tmp_path)
    pet.tick(pet.created + EGG_S - 1, hour=12)
    assert pet.stage == "egg"
    pet.tick(pet.created + EGG_S + 1, hour=12)
    assert pet.stage == "baby"
    assert pet.semantic_pose(pet.created + EGG_S + 1) == "hatch"


def test_meal_fills_one_heart(tmp_path: Path) -> None:
    pet = life(tmp_path)
    pet.stage = "child"
    pet.hunger = 2
    pet.weight = 10
    pet.act("meal", 2_000_000)
    assert pet.hunger == 3
    assert pet.weight == 11
    assert pet.semantic_pose(2_000_000) == "meal"


def test_full_meal_is_refused(tmp_path: Path) -> None:
    pet = life(tmp_path)
    pet.stage = "child"
    pet.hunger = 4
    pet.act("meal", 2_000_000)
    assert pet.hunger == 4
    assert pet.semantic_pose(2_000_000) == "refuse"


def test_missed_hunger_call_is_a_mistake(tmp_path: Path) -> None:
    pet = life(tmp_path)
    pet.stage = "child"
    pet.asleep = False
    now = 2_000_000
    pet.next_hunger = now
    pet.hunger = 1
    pet.tick(now, hour=12)
    assert pet.call == "hunger"
    later = now + CALL_S + 1
    pet.next_hunger = later + HUNGER_S
    pet.next_happy = later + HUNGER_S
    pet.next_poop = later + HUNGER_S
    pet.next_nag = later + HUNGER_S
    pet.next_follow = later + HUNGER_S
    pet.tick(later, hour=12)
    assert pet.call == ""
    assert pet.mistakes == 1


def test_scold_only_works_on_a_false_call(tmp_path: Path) -> None:
    pet = life(tmp_path)
    pet.stage = "child"
    pet.act("scold", 2_000_000)
    assert pet.discipline == 0
    pet.call = "discipline"
    pet.call_until = 9_000_000
    pet.act("scold", 2_000_000)
    assert pet.discipline == 1
    assert pet.call == ""


def test_too_many_snacks_make_it_sick(tmp_path: Path) -> None:
    pet = life(tmp_path)
    pet.stage = "child"
    now = 2_000_000
    for _ in range(4):
        pet.act("snack", now)
    assert pet.sick >= 2


def test_baby_grows_into_a_child(tmp_path: Path) -> None:
    pet = life(tmp_path)
    pet.stage = "baby"
    pet.hatched = 1_000
    pet.tick(1_000 + BABY_S + 1, hour=12)
    assert pet.stage == "child"


def test_lights_out_answers_bedtime(tmp_path: Path) -> None:
    pet = life(tmp_path)
    pet.stage = "child"
    pet.lights = True
    pet.tick(2_000_000, hour=23)
    assert pet.asleep
    assert pet.call == "light"
    pet.act("light", 2_000_100)
    assert pet.lights is False
    assert pet.call == ""


def test_hunger_waits_for_its_interval(tmp_path: Path) -> None:
    pet = life(tmp_path)
    pet.stage = "child"
    pet.hunger = 4
    pet.next_hunger = 5_000 + HUNGER_S
    pet.tick(5_000, hour=12)
    assert pet.hunger == 4


def test_teen_picks_from_care_mistakes(tmp_path: Path) -> None:
    pet = life(tmp_path)
    pet.stage = "child"
    pet.age = 3
    pet.mistakes = 0
    pet.disc_misses = 0
    pet.tick(2_000_000, hour=12)
    assert pet.stage == "teen"
    assert pet.teen_form == 0
    assert pet.form_picture() == ("teen", 0)


def test_poor_care_picks_second_teen(tmp_path: Path) -> None:
    pet = life(tmp_path)
    pet.stage = "child"
    pet.age = 3
    pet.mistakes = 3
    pet.tick(2_000_000, hour=12)
    assert pet.teen_form == 1
    assert pet.form_picture() == ("teen", 1)


def test_adult_index_matches_care() -> None:
    assert adult_index(0, 1, 0, 0) == 0
    assert adult_index(0, 1, 1, 1) == 1
    assert adult_index(0, 1, 2, 3) == 2
    assert adult_index(0, 1, 4, 0) == 3
    assert adult_index(1, 1, 4, 0) == 3
    assert adult_index(1, 2, 4, 6) == 5
