# GITM

**Ghost in the Machine** — a Windows desktop ghost. It stays invisible until you type, copy, paste, delete, or drag something. Then a SpriteForge character plays for a few seconds, Gemma says one line, and both fade away.

A second tray action looks at heavy folders. TabPFN 3.5, running on this PC, compares them with folders you already chose to keep or sweep and suggests the next pile. One yes deletes only that pile. Cursor, Windows, and Documents are never on the list.

## Run

```powershell
D:\GIMM\.venv\Scripts\pythonw.exe main.py
```

A settings window opens. Closing it leaves the ghost in the tray. There is also a desktop shortcut. Right-click the tray icon and choose Configure to open the window again.

`config.yaml` next to `main.py` (or next to the exe) is the control panel.

## Sprites

Characters come from SpriteForge in `D:\SPRITE`. Export the generic sprite-sheet pack and place each character here:

```
sprites/characters/sleepy/idle.png
sprites/characters/sleepy/idle.json
```

The json must include `frameWidth`, `frameHeight`, and `frames`. The png is a horizontal strip. The same layout is used for `curious`, `twin`, `angry`, `dizzy`, and an optional `pumpkin`.

The knight and swordswoman already in the SpriteForge workspace are unused. They are not ghosts.

If a character folder is missing, that reaction shows the whisper only and logs a warning.

## Voice

Install [Ollama](https://ollama.com), then:

```powershell
ollama pull gemma3:1b
```

The app asks `http://127.0.0.1:11434` for one short line. The prompt contains the event name and the mood only. Timeout is 2 seconds. If Gemma is not running, a line from `assets/lines/fallback_lines.json` is used and the caption marks it as a fallback.

## Disk suggestions

Tray → **Haunt the disk**. TabPFN is in `requirements.txt` but it is not installed yet, because `C:` only has about 1 GB free and the PyTorch download is large. When `C:` has room, install it onto `D:`:

```powershell
$env:TEMP="D:\tmp"; $env:TMP="D:\tmp"; $env:PIP_CACHE_DIR="D:\pip-cache"
D:\GIMM\.venv\Scripts\python.exe -m pip install tabpfn pandas
```

The first scoring run downloads the open weights into `D:\tabpfn-cache` after you accept Prior Labs' free non-commercial license. Later runs work with Wi-Fi off. Until then, Haunt the disk still lists heavy folders and Sweep temp still works.

**Sweep temp** clears temp files, thumbnails, and the Recycle Bin after you confirm.

## Scores

`%APPDATA%\GhostInTheMachine\state.json` stores ectoplasm, mood, candy, event counts, badges, and bytes freed. It is saved every 10 seconds and on exit.

`dust_history.csv` in that same folder is the local table TabPFN learns from. It stays on this PC.

## Tests

```powershell
D:\GIMM\.venv\Scripts\python.exe -m pytest
```

## Exe

```powershell
.\build_exe.ps1
```

The build writes `dist\GITM\`. `config.yaml` is copied beside the exe so you can still edit it.

## Halloween

October 31 uses an orange tint, or red after 6 p.m., and the tooltip says Halloween Mode. A pumpkin character is used for typing only if `sprites/characters/pumpkin` exists. November 1 and 2 draw a small marigold and the tooltip says Dia de los Muertos. Set `preview_date` in `config.yaml` to try another day without changing the Windows clock.
