# Ghost in the Machine (GITM)

A Windows desktop ghost that stays quiet until your computer is busy — then peeks in for a moment, maybe whispers one short line, and leaves.

No cloud account. No always-on mascot stuck in the corner. Everything runs on your machine.

---

## What it is

GITM has two parts that work together:

1. **Studio (Electron)** — a project desk where you turn actions on/off, drop sprite sheets, tune size / opacity / speed, and decide which actions may talk through Gemma.
2. **Engine (Python + Qt)** — a tray app with a transparent, click-through overlay. It watches keyboard / mouse / clipboard / folders (kinds of events only), plays the matching animation on screen, then fades or slides away.

You design the ghost in the studio. The engine lives in the system tray and reacts while you work.

---

## What it does (feature by feature)

### Action ghosts

When something happens on the PC, the ghost can react — if that action is **Show**’n and has sprites:

| Action | What you see |
| --- | --- |
| **Typing** | Peeks from a screen edge (left / right slant, or upside-down from the top), holds while you type, then slides back out. No Across/Down placement. |
| **Copy** (and other keyboard shortcuts you enable) | Plays at the position you set in the studio. |
| **Drag / move** | Follows the drag briefly. |
| **Idle** | After you stop working for a bit, a soft swarm can appear, then leave. |
| **Pet** | **Triple-click** anywhere to spawn the pet at that spot (triple-click again to dismiss). It stays there and cycles your visit PNGs. Sometimes it slowly strolls near the mouse, then walks home. |

Only the *kind* of action is used (e.g. “typing”, “copy”). Typed text, clipboard contents, and file names are not written into scores or logs.

### Show and Gemma

- **Show** — per-action checkbox. Off = that action never plays.
- **Gemma** — per-action toggle. Off = that action animates silently. On = local Gemma (via Ollama) may speak one short line for that action. If Ollama is down, a fallback line from `assets/lines/` is used.

### Sprites

Drop or import PNG sheets (SpriteForge-style). The studio cuts a grid into frames and saves a horizontal strip:

```text
sprites/characters/<action>/idle.png
sprites/characters/<action>/idle.json
```

**Pet** uses up to three visit sheets (cycled while parked):

```text
sprites/characters/pet/visits/0/
sprites/characters/pet/visits/1/
sprites/characters/pet/visits/2/
```

Missing art → warning in the log; no crash.

### Overlay

Always on top, transparent, **click-through** — clicks go to the app underneath. The ghost does not steal focus.

### Scores, badges, holidays

Ectoplasm, mood, candy, and badges live in `%APPDATA%\GhostInTheMachine\state.json`.  
Oct 31 can tint Halloween; Nov 1–2 can use Día de los Muertos marigold. `preview_date` in config can fake the calendar for testing.

### Disk “Haunt”

Tray → **Haunt the disk** lists heavy folders. **Sweep temp** can clear temp / thumbnails / Recycle Bin after you confirm. Cursor / Windows / Documents / Desktop are never suggested for delete. Optional TabPFN scoring is in `requirements.txt` but not required.

### Projects

The studio opens on a project list. Each project keeps its own action set and looks so you can run different “casts” (e.g. Halloween vs everyday).

---

## How it works (architecture)

```text
You work on Windows
        │
        ▼
 Engine hooks (keyboard / mouse / clipboard / folders)
        │  emit event name only  ("typing", "copy", "pet", …)
        ▼
 Runtime  →  cooldown / Show check / sprites / looks
        │
        ├─ main overlay  →  typing peek, copy, idle, drag, …
        └─ buddy overlay →  pet (so typing can still peek while the pet is parked)
        │
        └─ optional Whisperer → local Ollama Gemma → one line on the overlay
```

- **Studio bridge** (`app/studio_bridge.py`) talks to Electron over stdin/stdout JSON so the UI can save looks, import sheets, and toggle Show without restarting by hand.
- **Config** (`config.yaml`) is the live control panel: `show`, `sprites`, `cooldowns_ms`, `overlay`, `ollama`, `looks`.
- **Single engine** — a Windows mutex keeps only one engine instance running.

---

## Run

```powershell
.\GITM.bat
```

Opens the Electron studio and starts the ghost engine in the tray.

Engine only:

```powershell
.\.venv\Scripts\pythonw.exe main.py --engine
```

Tray menu: Configure, Badges, Haunt the disk, Sweep temp, Pause, Quit.

---

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd desktop
npm install
npm run build
cd ..
```

Voice (optional):

```powershell
ollama pull gemma3:1b
```

Tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Packaged build:

```powershell
.\build_exe.ps1
```

Output: `dist\GITM\GITM.exe` with `config.yaml` and sprites beside it.

---

## Layout

```text
main.py              engine entry
app/                 hooks, overlay, tray, whisper, dust, studio bridge
desktop/             React + Electron studio
sprites/             character sheets (+ pet/visits)
assets/              icons, fallback lines, dust seed
config.yaml          live settings
GITM.bat             launch studio + engine
```

AppData (`%APPDATA%\GhostInTheMachine\`): `state.json`, `app.log`, `look.json`, dust history, pet state.

---

## Privacy

Local only.

**Stored:** action counts, scores, dust feature table, log warnings.

**Not stored:** what you typed, clipboard text, screen contents, whisper lines, or file names inside the score file. Clipboard change detection uses an in-memory hash that dies with the process.

**Network:** only optional local Ollama. Nothing is uploaded.

---

## Quick control guide

| Want this | Do this |
| --- | --- |
| Ghost reacts when I type | Studio → Typing → Show on; drop a sheet; type anywhere |
| No talk on that action | Gemma toggle off for that action |
| Silence one action entirely | Show off |
| Call / dismiss the pet | Triple-click the desktop |
| Pet animations | Pet → drop up to 3 visit PNGs |
| Pause everything | Tray → Pause |
