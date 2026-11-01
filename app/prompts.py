"""English prompts you copy into ChatGPT. Eight frames, one computer action."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComputerAction:
    id: str
    title: str
    group: str
    motion: str
    frames: tuple[str, ...]


def _act(action_id: str, title: str, group: str, motion: str, frames: tuple[str, ...]) -> ComputerAction:
    if len(frames) != 8:
        raise ValueError(action_id)
    return ComputerAction(action_id, title, group, motion, frames)


CATALOG: tuple[ComputerAction, ...] = (
    _act(
        "typing",
        "Typing",
        "Keyboard",
        "A typing loop, like eight frames of a video. The hands strike and lift. Hair, cape, or cloth follows a beat late. Feet stay on one ground point. Frame 8 leads back into frame 1.",
        (
            "Both hands raised, fingers open, weight even",
            "Near hand strikes down, that shoulder drops",
            "Near hand snaps up, far hand starts down, cloth swings forward",
            "Far hand fully pressed, near elbow high",
            "Both hands low, torso leans in, cloth at the front of the swing",
            "Near hand strikes again, far hand lifts, cloth swings back",
            "Hands rise, body straightens, cloth settles",
            "Hands almost at rest, a small difference from frame 1 so the loop continues",
        ),
    ),
    _act(
        "copy",
        "Copy",
        "Keyboard",
        "A copy loop, like eight frames of a video. The character leans in and a faint twin of the same design appears beside them, then fades. No readable marks. Frame 8 leads back into frame 1.",
        (
            "Upright, alone, looking forward",
            "Head turns and the near shoulder lifts",
            "A clear lean in, near hand rises to chest height",
            "A faint twin outline splits out to the side",
            "The twin is largest and clearest, still the same design",
            "The twin thins and shrinks",
            "The twin is a wisp, the character straightens",
            "Alone again, a small difference from frame 1 so the loop continues",
        ),
    ),
    _act(
        "paste",
        "Paste",
        "Keyboard",
        "A paste loop, like eight frames of a video. A twin steps out of the body, stands clear, then melts back in. Same design, same size. Frame 8 leads back into frame 1.",
        (
            "One figure, upright",
            "A second outline starts peeling off the near side",
            "The twin is halfway out, still overlapping",
            "The twin stands beside them, slightly transparent",
            "The twin is solid and fully separate",
            "Both hold, matched, a small opposite sway",
            "The twin slides back and turns faint",
            "One figure again, a small difference from frame 1 so the loop continues",
        ),
    ),
    _act(
        "delete",
        "Delete",
        "Keyboard",
        "A delete loop, like eight frames of a video. The body flinches hard from side to side, then settles. The figure stays recognizable and inside the cell. Frame 8 leads back into frame 1.",
        (
            "Upright and still",
            "Shoulders jerk up, head tucks",
            "The whole body snaps to the near side",
            "The body snaps to the far side, cloth whipping",
            "Knees dip, arms fly out",
            "A smaller shake the other way",
            "The shake dies, outline steadies",
            "Upright again, a small difference from frame 1 so the loop continues",
        ),
    ),
    _act(
        "move",
        "Drag",
        "Mouse",
        "A drag loop, like eight frames of a video. The body is pulled sideways while the feet stay on one ground point, then it swings back through center. Frame 8 leads back into frame 1.",
        (
            "Weight centered, arms down",
            "The torso starts leaning, near arm reaches",
            "A deep lean, far foot light, arms trailing",
            "Full lean, cloth stretched with the pull",
            "The pull lets go, body still tipped",
            "Weight swings back under the hips",
            "A sway past center the other way",
            "Centered again, a small difference from frame 1 so the loop continues",
        ),
    ),
    _act(
        "cut",
        "Cut",
        "Keyboard",
        "The character makes one clean snip in front of the body. The held item, if any, stays in the same hand. Nothing is severed from the character.",
        (
            "Hands ready",
            "Hands come together",
            "The snip starts",
            "The snip closes",
            "Hands hold the closed snip",
            "Hands open",
            "Hands lower",
            "Ready again, almost the first pose",
        ),
    ),
    _act(
        "undo",
        "Undo",
        "Keyboard",
        "The character takes the action backward in place: a small step back, then returns. The camera does not move.",
        (
            "Neutral stand",
            "Weight shifts back",
            "A short step back, feet still in the cell",
            "Lowest point of the step",
            "Weight settles back",
            "Step returns forward",
            "Almost upright",
            "Neutral stand, almost the first pose",
        ),
    ),
    _act(
        "redo",
        "Redo",
        "Keyboard",
        "The character steps forward in place and returns. The head stays at the same height.",
        (
            "Neutral stand",
            "Weight shifts forward",
            "A short step forward, still inside the cell",
            "Front foot planted",
            "Weight on the front foot",
            "The back foot catches up",
            "Settling to center",
            "Neutral stand, almost the first pose",
        ),
    ),
    _act(
        "save",
        "Save",
        "Keyboard",
        "The character presses both hands down once, as if setting something in place, then stands easy. No paper, no icon, no text.",
        (
            "Hands at the sides",
            "Hands rise in front",
            "Hands start down",
            "Hands press at waist height",
            "The press holds",
            "Hands lift",
            "Hands drop to the sides",
            "Easy stand, almost the first pose",
        ),
    ),
    _act(
        "select_all",
        "Select all",
        "Keyboard",
        "The arms open wide and come back in. The feet stay planted. Nothing else enters the cell.",
        (
            "Arms down",
            "Arms start to open",
            "Arms half open",
            "Arms wide",
            "A short hold, wide",
            "Arms come in",
            "Arms almost down",
            "Arms down, almost the first pose",
        ),
    ),
    _act(
        "find",
        "Find",
        "Keyboard",
        "The character looks around in place: near side, down, far side, then forward again. The feet do not travel.",
        (
            "Looking forward",
            "Head turns near",
            "Lean and look down",
            "Head turns far",
            "Look up a little",
            "Look forward again",
            "A smaller glance near",
            "Looking forward, almost the first pose",
        ),
    ),
    _act(
        "enter",
        "Enter",
        "Keyboard",
        "One firm step down in place, then rise. The figure scale never changes.",
        (
            "Standing",
            "Knee softens",
            "The step goes down",
            "Lowest point",
            "The press holds",
            "Rising",
            "Almost up",
            "Standing, almost the first pose",
        ),
    ),
    _act(
        "backspace",
        "Backspace",
        "Keyboard",
        "A small recoil backward, then the character returns to the same spot. Nothing is erased from the drawing.",
        (
            "Neutral stand",
            "Chin tucks",
            "A short recoil",
            "Farthest recoil, still in the cell",
            "Hold",
            "Coming forward",
            "Almost neutral",
            "Neutral stand, almost the first pose",
        ),
    ),
    _act(
        "escape",
        "Escape",
        "Keyboard",
        "The character turns a quarter away and turns back. The view stays the side view. Do not show the back of a new design.",
        (
            "Facing right",
            "Shoulder begins to turn",
            "A quarter turn away",
            "The turn holds",
            "Turning back",
            "Almost facing right",
            "A small settle",
            "Facing right, almost the first pose",
        ),
    ),
    _act(
        "screenshot",
        "Screenshot",
        "Keyboard",
        "The character holds still, blinks once, and is still again. No camera, no flash shape, no border.",
        (
            "Eyes open, still",
            "Still",
            "Eyes half shut",
            "Eyes shut",
            "Eyes half open",
            "Eyes open",
            "Still",
            "Eyes open, almost the first pose",
        ),
    ),
    _act(
        "click",
        "Left click",
        "Mouse",
        "The near hand jabs forward once and returns. The body stays on the same ground line.",
        (
            "Hand ready",
            "Hand starts forward",
            "Halfway",
            "The jab lands",
            "The jab holds",
            "Hand pulls back",
            "Almost ready",
            "Hand ready, almost the first pose",
        ),
    ),
    _act(
        "right_click",
        "Right click",
        "Mouse",
        "The far hand points once to the side and returns. The character does not turn around.",
        (
            "Hands down",
            "Far hand lifts",
            "Far hand points aside",
            "The point holds",
            "Hand eases",
            "Hand lowers",
            "Almost down",
            "Hands down, almost the first pose",
        ),
    ),
    _act(
        "double_click",
        "Double click",
        "Mouse",
        "Two quick jabs of the near hand, then rest. Both jabs stay inside the cell.",
        (
            "Hand ready",
            "First jab out",
            "First jab back",
            "Second jab out",
            "Second jab lands",
            "Hand pulls back",
            "Almost ready",
            "Hand ready, almost the first pose",
        ),
    ),
    _act(
        "scroll",
        "Scroll",
        "Mouse",
        "The body rises a little and settles, twice, on the same ground point. The scale does not change.",
        (
            "Level",
            "Rising",
            "High point",
            "Settling",
            "Level",
            "Rising again",
            "Settling again",
            "Level, almost the first pose",
        ),
    ),
    _act(
        "new_file",
        "New file",
        "Files and windows",
        "The hands present a small empty shape in front of the body, then lower. The shape has no text and no icon.",
        (
            "Hands down",
            "Hands come together",
            "A small blank shape appears between the hands",
            "The shape is fully there",
            "It is offered forward",
            "It thins",
            "Hands lower, the shape is gone",
            "Hands down, almost the first pose",
        ),
    ),
    _act(
        "rename",
        "Rename",
        "Files and windows",
        "The character tilts the head and the hands adjust something small, then return. No letters appear.",
        (
            "Neutral",
            "Head tilts",
            "Near hand rises",
            "Fingers adjust",
            "The adjustment holds",
            "Hand lowers",
            "Head level",
            "Neutral, almost the first pose",
        ),
    ),
    _act(
        "download",
        "Download",
        "Files and windows",
        "The character looks down, catches something falling into the hands, and stands with it. The caught shape is blank. No progress bar.",
        (
            "Looking forward",
            "Eyes drop",
            "Hands rise to catch",
            "The blank shape lands in the hands",
            "Hands hold it",
            "It tucks in",
            "The shape is gone, posture rises",
            "Standing, almost the first pose",
        ),
    ),
    _act(
        "alt_tab",
        "Switch window",
        "Files and windows",
        "The character glances aside, as if another window took the room, then looks forward again. No window frame.",
        (
            "Looking forward",
            "Eyes shift aside",
            "Head turns aside",
            "The glance holds",
            "Head starts back",
            "Eyes forward",
            "A small settle",
            "Looking forward, almost the first pose",
        ),
    ),
    _act(
        "alt_f4",
        "Close the app",
        "Files and windows",
        "The character gives a short bow and rises. The figure never leaves the cell and never shrinks away.",
        (
            "Upright",
            "Chin lowers",
            "A short bow",
            "The bow holds",
            "Rising",
            "Almost upright",
            "Upright",
            "Upright, almost the first pose",
        ),
    ),
    _act(
        "idle",
        "Idle",
        "Files and windows",
        "A quiet idle loop, like eight frames of a video. The character breathes in place. The feet stay on one ground point. Nothing else enters the cell. Frame 8 leads back into frame 1.",
        (
            "Standing easy, eyes open",
            "A small inhale, shoulders rise",
            "The inhale holds",
            "Shoulders settle",
            "A slow blink starts",
            "Eyes shut for the blink",
            "Eyes open, posture easy",
            "Standing easy, a small difference from frame 1 so the loop continues",
        ),
    ),
    _act(
        "pet",
        "Pet",
        "Mouse",
        "A short visit loop for when the pet comes to the mouse. Full body, upright or soft float. No extra props. Frame 8 leads back into frame 1. You can make up to three different sheets; the app picks one at random each visit.",
        (
            "Coming closer, still upright",
            "A clear step or drift toward the viewer",
            "Near the mouse, body angled in",
            "Settling beside the cursor",
            "Soft idle near the mouse",
            "A small weight shift or blink",
            "Turning as if ready to leave",
            "Leaving pose, a small difference from frame 5 so the loop continues",
        ),
    ),
)

_SHOWN = ("typing", "copy", "paste", "delete", "enter", "screenshot", "scroll", "idle", "move", "pet")
_catalog_by_id = {item.id: item for item in CATALOG}
CATALOG = tuple(_catalog_by_id[name] for name in _SHOWN)
BY_ID = {item.id: item for item in CATALOG}
STARTER = _SHOWN


def sheet_prompt(name: str, action_id: str, cols: int = 4, rows: int = 2) -> str:
    del name, cols, rows
    action = BY_ID.get(action_id)
    if action is None:
        raise KeyError(action_id)
    poses = list(action.frames) if len(action.frames) == 8 else _poses(action.frames, 8)
    return "\n".join(
        [
            "You are a senior game sprite designer.",
            "Do not draw anything yet.",
            "Ask me this, and wait for my answer: What would you like to generate?",
            "My answer is the only subject. It may be a person, an animal, an object, a style, or a full description. Draw exactly what I asked for.",
            "Do not replace my answer with a ghost, a default character, or the name of an action. Do not ask for a picture, a reference, or an example.",
            "After I answer, design that subject once and keep the same face, colors, outfit, outline, and scale in every cell.",
            "",
            "Then draw one sprite sheet of that subject. Eight frames. No title on the image.",
            "These eight cells are eight moments of one short loop, like frames pulled from a video.",
            "Each cell must be a clearly different pose. Flipping through them must show the action moving.",
            "Do not repeat one still picture eight times.",
            "Grid: 4 columns by 2 rows, read left to right, top to bottom.",
            "Sheet size: 2048 by 1024 pixels. Each cell is 512 by 512.",
            "",
            "The notes below are directions for you. Do not paint them. The sheet has no words, no digits, no captions, and no cell numbers.",
            f"Motion: {action.motion}",
            *[f"Frame {index + 1}: {line}" for index, line in enumerate(poses)],
            "",
            "Layout:",
            "- One full figure per cell, centered, performing the action in place. It never travels across the cell.",
            "- Same ground line in every cell at 90% of the cell height. The figure height stays the same in every cell.",
            "- Limbs, hair, cape, or cloth change from frame to frame so the loop feels alive.",
            "- 8% empty margin on every side. Cells touch. No borders, gridlines, numbers, labels, captions, or shadows.",
            "- Flat #00FF00 background. Never use #00FF00 on the subject.",
            "",
            "Side view, facing right, orthographic camera at body height. Never mirror.",
            "Style: clean high-resolution 2D game art. Crisp edges, cel shading with 2 to 3 tones per color, one dark outline.",
            "No painterly texture, no blur, no motion blur, no glow halos, no drop shadow.",
            "",
            "Do not: draw before I answer, ask for a reference image, write any text, write an action name, number the cells, mirror, change the camera, redesign the subject between cells, add scenery, or crop the figure at a cell edge.",
        ]
    )


def _poses(lines: tuple[str, ...], count: int) -> list[str]:
    if count == len(lines):
        return list(lines)
    return [lines[min(len(lines) - 1, int(index / count * len(lines)))] for index in range(count)]
