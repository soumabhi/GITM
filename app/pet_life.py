"""Desktop Tamagotchi. The clock advances while this app is running."""

from __future__ import annotations

import json
import random
import time
from datetime import datetime
from pathlib import Path

EGG_S = 5 * 60
BABY_S = 65 * 60
CALL_S = 15 * 60
HUNGER_S = 15 * 60
HAPPY_S = 18 * 60
POOP_S = 40 * 60
POOP_SICK_S = 20 * 60
SICK_DEATH_S = 45 * 60
SNACK_WINDOW_S = 30 * 60
CATCH_UP = 8

# group, id, title, how, hint
# how "frames": every PNG plays in order
# how "pick": the life picks one PNG from care, the way the toy picks a character
PLACES = (
    ("Who it is", "egg", "Egg", "frames", "Add another PNG and it plays as the next frame of the egg."),
    ("Who it is", "baby", "Baby", "frames", "Always this one after it hatches. Add PNGs for more frames."),
    ("Who it is", "child", "Child", "frames", "The child. Add PNGs for more frames."),
    ("Who it is", "teen", "Teen", "pick", "PNG 1 is good care, up to 2 mistakes. PNG 2 is 3 or more mistakes. The pet picks."),
    ("Who it is", "adult", "Adult", "pick", "Add them in order: perfect, one slip, undisciplined, poor but disciplined, poor, neglected. The pet picks."),
    ("Who it is", "die", "Death", "frames", "Shown at the end, then a new egg. Add PNGs for more frames."),
    ("What it is doing", "hatch", "Hatch", "frames", "The moment it breaks the egg."),
    ("What it is doing", "grow", "Grow", "frames", "The moment it changes form."),
    ("What it is doing", "idle", "Idle", "frames", "Used when that age has no pictures of its own yet."),
    ("What it is doing", "hungry", "Hungry", "frames", "No hungry hearts left."),
    ("What it is doing", "call", "Call", "frames", "It ran to you because it needs something."),
    ("What it is doing", "run", "Run", "frames", "On the way to the mouse."),
    ("What it is doing", "follow", "Follow", "frames", "When it decides to follow the mouse."),
    ("What it is doing", "meal", "Meal", "frames", "Eating a meal."),
    ("What it is doing", "snack", "Snack", "frames", "Eating a snack."),
    ("What it is doing", "play", "Play", "frames", "The left or right game."),
    ("What it is doing", "sleep", "Sleep", "frames", "Asleep."),
    ("What it is doing", "sick", "Sick", "frames", "Needs medicine."),
    ("What it is doing", "mess", "Mess", "frames", "Something to clean. It does not call for this."),
    ("What it is doing", "refuse", "Refuse", "frames", "Will not eat or play."),
    ("What it is doing", "scold", "Scold", "frames", "After you scold it."),
)

PLACE_IDS = {item[1] for item in PLACES}


def picture_files(root: Path, slot: str) -> list[Path]:
    folder = root / slot
    files = sorted(folder.glob("*.png")) if folder.is_dir() else []
    legacy = root / f"{slot}.png"
    if not files and legacy.exists():
        return [legacy]
    return files

_FIELDS = (
    "created",
    "stage",
    "age",
    "hunger",
    "happy",
    "discipline",
    "weight",
    "mistakes",
    "poops",
    "poop_at",
    "sick",
    "sick_at",
    "lights",
    "asleep",
    "slept",
    "call",
    "call_until",
    "home_x",
    "home_y",
    "pose",
    "pose_until",
    "follow_until",
    "next_hunger",
    "next_happy",
    "next_poop",
    "next_nag",
    "next_follow",
    "hatched",
    "snacks",
    "snack_at",
    "game_round",
    "game_wins",
    "dead_until",
    "disc_misses",
    "teen_form",
    "teen_type",
    "adult_form",
)


def fresh(now: float | None = None) -> dict:
    moment = time.time() if now is None else now
    return {
        "created": moment,
        "stage": "egg",
        "age": 0,
        "hunger": 4,
        "happy": 4,
        "discipline": 0,
        "weight": 5,
        "mistakes": 0,
        "poops": 0,
        "poop_at": 0.0,
        "sick": 0,
        "sick_at": 0.0,
        "lights": True,
        "asleep": False,
        "slept": False,
        "call": "",
        "call_until": 0.0,
        "home_x": 72.0,
        "home_y": 62.0,
        "pose": "egg",
        "pose_until": 0.0,
        "follow_until": 0.0,
        "next_hunger": moment + HUNGER_S,
        "next_happy": moment + HAPPY_S,
        "next_poop": moment + POOP_S,
        "next_nag": moment + 20 * 60,
        "next_follow": moment + 60,
        "hatched": 0.0,
        "snacks": 0,
        "snack_at": moment,
        "game_round": 0,
        "game_wins": 0,
        "dead_until": 0.0,
        "disc_misses": 0,
        "teen_form": 0,
        "teen_type": 1,
        "adult_form": 0,
    }


def adult_index(teen_form: int, teen_type: int, care: int, disc: int) -> int:
    """0 perfect, 1 one slip, 2 undisciplined, 3 poor but disciplined, 4 poor, 5 neglected."""
    if teen_form == 0 and teen_type == 1:
        if care <= 2 and disc <= 0:
            return 0
        if care <= 2 and disc == 1:
            return 1
        if care <= 2:
            return 2
        if disc <= 1:
            return 3
        if disc <= 3:
            return 4
        return 5
    if teen_form == 0:
        if care <= 3 and disc <= 1:
            return 1
        if care <= 3:
            return 2
        if disc <= 7:
            return 4
        return 5
    if teen_type == 1:
        if disc <= 1:
            return 3
        if disc == 2:
            return 4
        return 5
    if disc <= 5:
        return 4
    return 5


class PetLife:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._load()

    def _load(self) -> None:
        data = fresh()
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            saved = {}
        if isinstance(saved, dict):
            for key in _FIELDS:
                if key in saved:
                    data[key] = saved[key]
        self.__dict__.update(data)
        self.stage = str(self.stage or "egg")
        self.call = str(self.call or "")
        self.hunger = int(self.hunger)
        self.happy = int(self.happy)
        self.discipline = int(self.discipline)
        self.weight = int(self.weight)
        self.age = int(self.age)
        self.poops = int(self.poops)
        self.sick = int(self.sick)
        self.lights = bool(self.lights)
        self.asleep = bool(self.asleep)

    def save(self) -> None:
        payload = {key: getattr(self, key) for key in _FIELDS}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload), encoding="utf-8")
        temp.replace(self.path)

    def reset(self, now: float) -> None:
        home_x, home_y = self.home_x, self.home_y
        self.__dict__.update(fresh(now))
        self.home_x = home_x
        self.home_y = home_y
        self.save()

    def park(self, across: float, down: float) -> None:
        self.home_x = max(0.0, min(100.0, float(across)))
        self.home_y = max(0.0, min(100.0, float(down)))
        self.follow_until = 0.0
        self.save()

    def semantic_pose(self, now: float) -> str:
        if self.stage == "dead":
            return "die"
        if self.pose_until > now and self.pose:
            return str(self.pose)
        if self.stage == "egg":
            return "egg"
        if self.game_round:
            return "play"
        if self.asleep:
            return "sleep"
        if self.sick:
            return "sick"
        if self.poops:
            return "mess"
        if self.call:
            return "call"
        if self.follow_until > now:
            return "follow"
        if self.hunger <= 0:
            return "hungry"
        return "idle"

    def blurb(self, now: float) -> str:
        if self.stage == "dead":
            return "It is gone. A new egg is on the way."
        if self.stage == "egg":
            left = max(0, int(self.created + EGG_S - now))
            minutes, seconds = divmod(left, 60)
            return f"Egg on the desktop. It hatches in {minutes} min {seconds} sec. Mouse follow starts after it hatches."
        if self.game_round:
            return f"Guess which way it turns. Round {self.game_round} of 5."
        if self.call == "hunger":
            return "It ran to you. It is hungry."
        if self.call == "happy":
            return "It ran to you. It wants to play."
        if self.call == "light":
            return "It is asleep. Turn the light off."
        if self.call == "discipline":
            return "It is calling for nothing. Scold it."
        if self.asleep:
            return "Asleep."
        if self.sick:
            return "Sick. It needs medicine."
        if self.poops:
            return "There is a mess to clean. It will not call for that."
        if self.follow_until > now:
            return "Following your mouse. Keep moving and it stays with you."
        if self.hunger <= 1:
            return "Getting hungry."
        if self.happy <= 1:
            return "Getting bored."
        return f"{self.stage.capitalize()}. Move the mouse near it to pull it. Drag it to set a home."

    def view(self, now: float) -> dict:
        return {
            "stage": self.stage,
            "age": self.age,
            "hunger": self.hunger,
            "happy": self.happy,
            "discipline": self.discipline,
            "weight": self.weight,
            "mistakes": self.mistakes,
            "poops": self.poops,
            "sick": self.sick,
            "lights": self.lights,
            "asleep": self.asleep,
            "call": self.call,
            "following": self.follow_until > now,
            "pose": self.semantic_pose(now),
            "game": bool(self.game_round),
            "gameRound": self.game_round,
            "gameWins": self.game_wins,
            "blurb": self.blurb(now),
            "homeX": self.home_x,
            "homeY": self.home_y,
            "place": (shown := self.showing(now))[0],
            "placeIndex": shown[1],
        }

    def _hold(self, name: str, now: float, seconds: float = 2.4) -> None:
        self.pose = name
        self.pose_until = now + seconds

    def _clear_call(self) -> None:
        self.call = ""
        self.call_until = 0.0

    def _start_call(self, reason: str, now: float) -> None:
        if self.stage in {"egg", "dead"} or self.call:
            return
        self.call = reason
        self.call_until = now + CALL_S
        self.follow_until = 0.0
        self.game_round = 0
        self.game_wins = 0

    def _awake_body(self) -> bool:
        return self.stage not in {"egg", "dead"} and not self.asleep

    def act(self, action: str, now: float) -> None:
        name = str(action or "")
        if name == "reset":
            self.reset(now)
            return
        if self.stage == "dead":
            return
        if name == "left":
            self._guess(False, now)
            return
        if name == "right":
            self._guess(True, now)
            return
        if name == "light":
            self.lights = not self.lights
            if self.call == "light" and not self.lights:
                self._clear_call()
            self._hold("sleep" if self.asleep else "idle", now, 1.2)
            return
        if name == "clean":
            self.poops = 0
            self.poop_at = 0.0
            self._hold("idle", now, 1.2)
            return
        if name == "medicine":
            if self.sick > 0:
                self.sick -= 1
                self._hold("sick" if self.sick else "idle", now)
                if self.sick <= 0:
                    self.sick_at = 0.0
            return
        if name == "scold":
            if self.call == "discipline":
                self.discipline = min(4, self.discipline + 1)
                self._clear_call()
                self._hold("scold", now)
            return
        if name == "meal":
            self._feed(now)
            return
        if name == "snack":
            self._snack(now)
            return
        if name == "play":
            self._play(now)

    def _refuses(self, now: float) -> bool:
        if not self._awake_body() or self.sick:
            self._hold("refuse", now)
            return True
        return False

    def _feed(self, now: float) -> None:
        if self._refuses(now):
            return
        if self.hunger >= 4:
            self._hold("refuse", now)
            return
        self.hunger += 1
        self.weight = min(99, self.weight + 1)
        if self.call == "hunger":
            self._clear_call()
        self._hold("meal", now)

    def _snack(self, now: float) -> None:
        if self.stage in {"egg", "dead"} or self.asleep:
            self._hold("refuse", now)
            return
        if now - float(self.snack_at) > SNACK_WINDOW_S:
            self.snacks = 0
            self.snack_at = now
        self.snacks = int(self.snacks) + 1
        self.happy = min(4, self.happy + 1)
        self.weight = min(99, self.weight + 2)
        if self.call == "happy":
            self._clear_call()
        if self.snacks >= 4:
            self.sick = max(int(self.sick), 2)
            if not self.sick_at:
                self.sick_at = now
        self._hold("snack", now)

    def _play(self, now: float) -> None:
        if self._refuses(now):
            return
        self.game_round = 1
        self.game_wins = 0
        self._hold("play", now, 30)

    def _guess(self, right: bool, now: float) -> None:
        if not self.game_round or not self._awake_body():
            return
        if right == random.choice((True, False)):
            self.game_wins = int(self.game_wins) + 1
        if self.game_round >= 5:
            won = self.game_wins >= 3
            self.game_round = 0
            self.game_wins = 0
            self.pose_until = 0
            if won:
                self.happy = min(4, self.happy + 1)
                self.weight = max(1, self.weight - 1)
                if self.call == "happy":
                    self._clear_call()
            self._hold("play", now, 1.4)
            return
        self.game_round = int(self.game_round) + 1

    def _grow(self, stage: str, now: float) -> None:
        self.stage = stage
        self.discipline = max(0, self.discipline - 1)
        self._hold("grow", now, 3)

    def tick(self, now: float, hour: int | None = None) -> None:
        when = datetime.fromtimestamp(now)
        clock = when.hour if hour is None else hour
        if self.stage == "dead":
            if self.dead_until and now >= self.dead_until:
                self.reset(now)
            return
        if self.stage == "egg":
            if now >= float(self.created) + EGG_S:
                self.stage = "baby"
                self.hatched = now
                self.next_hunger = now + HUNGER_S
                self.next_happy = now + HAPPY_S
                self.next_poop = now + 15 * 60
                self._hold("hatch", now, 3)
            return
        self._sleep_clock(now, clock)
        if self.call and now >= float(self.call_until):
            if self.call in {"hunger", "happy", "light"}:
                self.mistakes = int(self.mistakes) + 1
            elif self.call == "discipline":
                self.disc_misses = int(self.disc_misses) + 1
            self._clear_call()
        if not self.asleep:
            self._drain(now)
            self._mess(now)
            self._nag(now)
            self._follow_roll(now)
        if self.sick and self.sick_at and now - float(self.sick_at) >= SICK_DEATH_S:
            self._die(now)
            return
        self._evolve(now)

    def _sleep_clock(self, now: float, hour: int) -> None:
        night = hour >= 22 or hour < 8
        if night and not self.asleep:
            self.asleep = True
            self.slept = True
            self.game_round = 0
            self.follow_until = 0.0
            if self.lights:
                self._start_call("light", now)
            return
        if not night and self.asleep:
            self.asleep = False
            self.lights = True
            if self.call == "light":
                self._clear_call()
            if self.slept:
                self.age = int(self.age) + 1
                self.slept = False

    def _drain(self, now: float) -> None:
        steps = 0
        while now >= float(self.next_hunger) and steps < CATCH_UP:
            self.hunger = max(0, int(self.hunger) - 1)
            self.next_hunger = float(self.next_hunger) + HUNGER_S
            steps += 1
            if self.hunger <= 0:
                self._start_call("hunger", now)
        if steps >= CATCH_UP and now >= float(self.next_hunger):
            self.next_hunger = now + HUNGER_S
        steps = 0
        while now >= float(self.next_happy) and steps < CATCH_UP:
            self.happy = max(0, int(self.happy) - 1)
            self.next_happy = float(self.next_happy) + HAPPY_S
            steps += 1
            if self.happy <= 0:
                self._start_call("happy", now)
        if steps >= CATCH_UP and now >= float(self.next_happy):
            self.next_happy = now + HAPPY_S

    def _mess(self, now: float) -> None:
        if now >= float(self.next_poop):
            self.poops = min(4, int(self.poops) + 1)
            if self.poops == 1:
                self.poop_at = now
            self.next_poop = now + POOP_S
        if self.poops and self.poop_at and now - float(self.poop_at) >= POOP_SICK_S:
            if not self.sick:
                self.sick = 1
                self.sick_at = now

    def _nag(self, now: float) -> None:
        if now < float(self.next_nag):
            return
        self.next_nag = now + random.randint(12, 25) * 60
        if self.call or self.discipline >= 4 or self.hunger <= 0 or self.happy <= 0:
            return
        if random.random() < 0.55:
            self._start_call("discipline", now)

    def _can_chase(self) -> bool:
        return (
            self.stage not in {"egg", "dead"}
            and not self.asleep
            and not self.call
            and not self.sick
            and not self.game_round
        )

    def notice_mouse(self, now: float, near: bool, moving: bool) -> None:
        """Mouse movement sticks to the pet. Near = follow. Keep moving = keep following."""
        if not self._can_chase():
            return
        if near:
            self.follow_until = max(float(self.follow_until), now + 5.5)
            return
        if moving and self.follow_until > now:
            self.follow_until = now + 4.0
            return
        if moving and random.random() < 0.08:
            self.follow_until = now + random.randint(6, 12)

    def _follow_roll(self, now: float) -> None:
        if now < float(self.next_follow):
            return
        self.next_follow = now + random.randint(35, 80)
        if not self._can_chase():
            return
        if random.random() < 0.55:
            self.follow_until = now + random.randint(10, 18)

    def form_picture(self) -> tuple[str, int | None]:
        if self.stage == "dead":
            return "die", None
        if self.stage == "egg":
            return "egg", None
        if self.stage == "teen":
            return "teen", int(self.teen_form)
        if self.stage == "adult":
            return "adult", int(self.adult_form)
        if self.stage in {"baby", "child"}:
            return self.stage, None
        return "idle", None

    def showing(self, now: float) -> tuple[str, int | None]:
        pose = self.semantic_pose(now)
        if pose == "idle":
            return self.form_picture()
        return pose, None

    def _evolve(self, now: float) -> None:
        if self.stage == "baby" and self.hatched and now - float(self.hatched) >= BABY_S:
            self._grow("child", now)
        elif self.stage == "child" and self.age >= 3:
            self.teen_form = 0 if int(self.mistakes) <= 2 else 1
            self.teen_type = 1 if int(self.disc_misses) <= 2 else 2
            self._grow("teen", now)
        elif self.stage == "teen" and self.age >= 6:
            self.adult_form = adult_index(int(self.teen_form), int(self.teen_type), int(self.mistakes), int(self.disc_misses))
            self._grow("adult", now)
        elif self.stage == "adult" and self.age >= 16:
            self._die(now)

    def _die(self, now: float) -> None:
        self.stage = "dead"
        self._clear_call()
        self.game_round = 0
        self.follow_until = 0.0
        self.asleep = False
        self._hold("die", now, 12)
        self.dead_until = now + 12
