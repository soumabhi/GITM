# Privacy

GITM (Ghost in the Machine) watches for kinds of actions so a small ghost can react. It does not watch what those actions contain.

## Collected

- Counts of typing, copy, paste, delete, and move
- Ectoplasm, mood, candy, badges, idle seconds, and bytes freed
- A local dust table: folder kind, size, age, whether it is on C:, whether the name looks like a cache, and whether you kept or swept it

That table is how the on-device TabPFN model suggests the next pile. The suggestion dialog also shows the folder path so you can see what a yes would delete.

## Not collected

- Keystroke content
- Clipboard content
- File names inside the log or the score file
- Screen contents
- Whisper text

Clipboard changes are detected with an in-memory hash that is never written down. The hash is discarded when the app closes.

## Storage

`%APPDATA%\GhostInTheMachine\state.json` holds the scores.

`%APPDATA%\GhostInTheMachine\dust_history.csv` holds the dust table.

`%APPDATA%\GhostInTheMachine\app.log` holds warnings such as a missing sprite. It records event kinds and badge names, not what you typed.

## Network

None, except two optional local programs on this PC:

- Ollama at `http://127.0.0.1:11434`, for the Gemma whisper
- TabPFN, which runs in this process

Nothing is uploaded. The dust table is not sent to a server. After Gemma and the TabPFN weights have been downloaded once, the app works with Wi-Fi off.
