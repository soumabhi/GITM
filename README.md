# 👻 Ghost in the Machine (GITM)

### Your computer has a little ghost. It only wakes up when you're busy.

A tiny desktop companion. A little bit of personality. A machine that finally reacts to you.

**Ghost in the Machine (GITM)** is a local-first Windows desktop application that transforms everyday computer interactions into playful animated moments. Whether you're typing, copying, dragging files, or stepping away from your keyboard, your ghost quietly observes the type of activity and occasionally makes an appearance.

It peeks out. It reacts. It sometimes talks. Then it disappears.

No cloud accounts. No unnecessary background windows. No permanently stuck mascot. Just a little ghost living inside your desktop.

<p align="center">
  <a href="https://youtu.be/Od1qMNbtQxE">
    <img src="https://img.youtube.com/vi/Od1qMNbtQxE/maxresdefault.jpg" alt="Ghost in the Machine - Watch the Demo" width="85%">
  </a>
  <br>
  <strong>▶ Watch GITM in action</strong>
  <br>
  <sub>Click the preview to watch the full demonstration.</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows-0078D4?style=for-the-badge&logo=windows" alt="Windows">
  <img src="https://img.shields.io/badge/Python-Engine-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Electron-Studio-47848F?style=for-the-badge&logo=electron&logoColor=white" alt="Electron">
  <img src="https://img.shields.io/badge/AI-Local%20Gemma-8E75B2?style=for-the-badge" alt="Local AI">
  <img src="https://img.shields.io/badge/Privacy-Local%20First-2EA44F?style=for-the-badge" alt="Local First">
</p>

---

## ✨ The idea

What if your computer had a little companion that responded to the things you did?

Not another chatbot. Not another productivity dashboard. Not another animated wallpaper.

Something that feels alive without demanding your attention.

GITM explores a different kind of desktop experience: **event-driven character interactions.**

The ghost doesn't need to understand everything happening on your screen. It only needs to know that something happened.

You control its personality, appearance, behaviour, animations, and whether it is allowed to speak.

## 👻 Features

### ⌨️ 1. Action-based ghost interactions

Your ghost reacts to supported desktop events.

| Action | What happens |
|---|---|
| Typing | Peeks from the left or right edge, or upside-down from the top. Stays while typing continues, then retreats. |
| Copy | Plays a configured animation at your selected screen position. |
| Drag / Move | Briefly follows the drag interaction. |
| Idle | A soft ghost swarm can appear after inactivity. |
| Pet | Triple-click to summon a companion that stays on your desktop. |

Every action has independent controls. Turn individual interactions on or off, configure their animations, and adjust cooldowns.

### 🐾 2. Your personal desktop pet

Why should your ghost disappear every time?

The Pet system introduces a companion that can stay on your desktop independently of the main animation overlay.

- Triple-click anywhere to summon or dismiss.
- Import up to three visit animation sheets.
- Automatically cycle through available visit animations.
- Occasionally stroll near the mouse.
- Walk back to its original position.
- Continue existing independently while other ghost animations play.

The pet has its own buddy overlay, so it doesn't prevent typing animations from appearing.

### 🗣️ 3. Give your ghost a voice with local AI

Sometimes a ghost should have something to say.

GITM optionally integrates with **Gemma 3 through Ollama**, allowing your companion to generate short contextual dialogue locally.

- Enable or disable AI dialogue per action.
- Generate one short line for an interaction.
- Use local fallback dialogue when Ollama is unavailable.
- Keep individual actions completely silent.
- No external AI API key or cloud inference service is required.

Optional model:

```powershell
ollama pull gemma3:1b
```

### 🎨 4. Bring your own characters and sprite sheets

GITM is built around customizable sprite animations.

Import SpriteForge-style PNG sheets directly through Studio. Configure the grid, extract frames, and generate the animation assets automatically.

```text
sprites/
└── characters/
    ├── typing/
    │   ├── idle.png
    │   └── idle.json
    │
    ├── copy/
    ├── drag/
    ├── idle/
    │
    └── pet/
        └── visits/
            ├── 0/
            ├── 1/
            └── 2/
```

Customize:
- Sprite sheet rows and columns.
- Frame dimensions.
- Animation speed.
- Character size.
- Overlay opacity.
- Character-specific looks.
- Pet visit animations.

Missing sprites generate warnings instead of crashing the application.

### 🪟 5. A transparent, click-through overlay

Your ghost should never get in your way.

The overlay is designed to be:

- Always on top.
- Transparent.
- Click-through.
- Non-focus-stealing.
- Independent of the application you're currently using.

Your mouse interactions continue to reach the applications underneath.

### 🏆 6. Scores, badges and personality

Your companion has a little progression system.

GITM maintains local state for:

- Ectoplasm.
- Mood.
- Candy.
- Badges.
- Action scores.

It also supports seasonal visual themes:

- October 31: Halloween-inspired visual effects.
- November 1–2: Día de los Muertos-inspired marigold accents.

Use `preview_date` in your configuration to test seasonal appearances.

### 💾 7. Haunt the disk

Your ghost can also help you inspect disk usage.

Available through the system tray:

- **Haunt the disk:** Lists heavy folders.
- **Sweep temp:** Offers cleanup of temporary files, thumbnails, and Recycle Bin after confirmation.

Important directories such as Windows, Cursor, Documents, and Desktop are never suggested for deletion.

TabPFN-based scoring is optional and is not required to run GITM.

### 🎭 8. Multiple projects and personalities

One ghost doesn't have to be your only ghost.

Studio supports multiple projects, each with its own action configuration, sprites, and looks.

Create different experiences:

- Halloween ghost.
- Everyday desktop companion.
- Custom character collections.
- Different animation and interaction sets.

Switch projects without rebuilding your entire setup.

---

## 🛠️ Meet the two parts of GITM

GITM is divided into two applications that work together.

### 1. Studio — The creative workspace

Built with Electron and React.

Studio is where you design and configure your desktop companion.

- Create and manage projects.
- Enable or disable actions.
- Import and configure sprite sheets.
- Customize animation settings.
- Control AI dialogue permissions.
- Manage character looks.
- Preview and save configurations.

### 2. Engine — The ghost runtime

Built with Python and Qt.

The engine lives in the Windows system tray and manages the actual desktop interactions.

- Monitors supported keyboard, mouse, clipboard, and folder events.
- Emits event types rather than user content.
- Applies action-specific cooldowns.
- Selects the configured animations.
- Manages transparent overlays.
- Coordinates the optional local AI whisperer.
- Maintains local application state.

---

## 🧠 Architecture

```text
                    WINDOWS DESKTOP
                           │
                           ▼
                 ┌───────────────────┐
                 │    EVENT HOOKS    │
                 │                   │
                 │ Keyboard / Mouse  │
                 │ Clipboard / Files │
                 └─────────┬─────────┘
                           │
                           ▼
                   EVENT NAME ONLY
                  "typing", "copy"...
                           │
                           ▼
                 ┌───────────────────┐
                 │   RUNTIME MANAGER │
                 │                   │
                 │ Cooldowns         │
                 │ Show permissions │
                 │ Sprite selection │
                 │ Looks / Behaviour│
                 └─────────┬─────────┘
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
          ┌─────────────┐     ┌─────────────┐
          │ MAIN OVERLAY│     │BUDDY OVERLAY│
          │             │     │             │
          │ Typing      │     │ Pet         │
          │ Copy        │     │ Visits      │
          │ Idle        │     │ Movement    │
          │ Drag        │     │             │
          └──────┬──────┘     └──────┬──────┘
                 │                   │
                 └─────────┬─────────┘
                           │
                           ▼
                   OPTIONAL WHISPERER
                           │
                           ▼
                     LOCAL OLLAMA
                        GEMMA 3
                           │
                           ▼
                   SHORT AI DIALOGUE
```

### Studio-to-engine communication

The Studio bridge (`app/studio_bridge.py`) communicates with Electron through JSON messages over stdin/stdout.

It allows the Studio to save looks, import sprite sheets, and update action settings without requiring manual engine restarts.

### Configuration

`config.yaml` acts as the live control panel.

It manages:

- `show`
- `sprites`
- `cooldowns_ms`
- `overlay`
- `ollama`
- `looks`

A Windows mutex prevents multiple engine instances from running simultaneously.

---

## 🔐 Privacy by design

GITM is designed to run locally.

**It reacts to activity types, not the actual content of your activity.**

| Information | Stored? |
|---|---|
| Action counts | Yes |
| Scores and badges | Yes |
| Dust feature table | Yes |
| Application warnings | Yes |
| Typed text | No |
| Clipboard contents | No |
| Screen contents | No |
| File names in score storage | No |
| Generated whisper lines | No |

Clipboard change detection uses an in-memory hash that disappears when the process exits.

### Network usage

- No cloud account.
- No remote AI API.
- No activity uploads.
- Optional AI communication with a local Ollama instance.

Your application state is stored locally:

```text
%APPDATA%\GhostInTheMachine\
```

Your desktop should remain yours.

---

## 🚀 Installation

### Requirements

- Windows.
- Python.
- Node.js and npm.
- Ollama (optional, for AI dialogue).

### Step 1 — Clone the repository

```powershell
git clone YOUR_REPOSITORY_URL
cd Ghost-in-the-Machine
```

### Step 2 — Set up Python

```powershell
python -m venv .venv

.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Step 3 — Install Studio dependencies

```powershell
cd desktop

npm install
npm run build

cd ..
```

### Step 4 — Optional local AI setup

Install Ollama and download Gemma 3:

```powershell
ollama pull gemma3:1b
```

This step is optional. GITM can run without local AI.

### Step 5 — Launch GITM

```powershell
.\GITM.bat
```

This launches the Electron Studio and starts the Python engine in the system tray.

### Run the engine independently

```powershell
.\.venv\Scripts\pythonw.exe main.py --engine
```

---

## 🧪 Testing

Run the test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## 📦 Build a packaged application

```powershell
.\build_exe.ps1
```

Expected output:

```text
dist/
└── GITM/
    ├── GITM.exe
    ├── config.yaml
    └── sprites/
```

---

## 🎮 Quick controls

| Action | How to use it |
|---|---|
| Enable typing animation | Studio → Typing → Show ON |
| Disable an action | Studio → Select action → Show OFF |
| Silence an action | Turn its Gemma toggle OFF |
| Summon your pet | Triple-click the desktop |
| Dismiss your pet | Triple-click again |
| Customize pet animations | Studio → Pet → Import visit sheets |
| Pause all reactions | Tray → Pause |
| Inspect disk usage | Tray → Haunt the disk |
| Clean temporary files | Tray → Sweep temp |

---

## 📂 Project structure

```text
GITM/
│
├── main.py
├── GITM.bat
├── build_exe.ps1
├── config.yaml
├── requirements.txt
│
├── app/
│   ├── hooks/
│   ├── overlay/
│   ├── tray/
│   ├── whisper/
│   ├── dust/
│   └── studio_bridge.py
│
├── desktop/
│   └── React + Electron Studio
│
├── sprites/
│   └── characters/
│
├── assets/
│   ├── icons/
│   ├── lines/
│   └── dust/
│
└── tests/
```

Runtime state and logs are maintained separately under:

```text
%APPDATA%\GhostInTheMachine\
```

---

## 🗺️ What's next?

GITM is an evolving experiment in making desktop interactions feel more alive.

Some directions for future development:

- More character behaviours and animation types.
- Better sprite authoring and animation previews.
- Additional local AI personalities.
- More seasonal events and collectible badges.
- More customizable interaction triggers.
- Expanded character and animation collections.

---

## 🤝 Contributing

Have an interesting ghost character? A new animation? An idea for a desktop interaction?

Contributions, suggestions, bug reports, and custom sprite packs are welcome.

Feel free to open an issue or submit a pull request.

---

## 👻 The philosophy

Computers are great at responding to commands.

But what if they could respond with a little personality?

GITM is a small experiment in making everyday computing feel a little less mechanical.

**Not another assistant. Not another notification. Just a ghost that knows when you're busy.**

<p align="center">
  <strong>👻 Ghost in the Machine</strong>
  <br>
  <em>A little ghost for your everyday machine.</em>
  <br><br>
  <a href="https://youtu.be/Od1qMNbtQxE">Watch the demo</a>
</p>
