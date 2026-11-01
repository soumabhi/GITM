---
title: GITM — Ghost in the Machine
published: false
tags: devchallenge, hf26challenge
---

# A ghost that only shows up when the machine is busy

I wanted something that felt like Halloween without becoming another window I have to feed. GITM (Ghost in the Machine) is a Windows tray app. The corner of the screen stays empty. When I type, copy, paste, delete, or drag a file, a small character plays for about three seconds, says one line, and fades out.

The character art is exported from SpriteForge, a local studio I already had on disk. The voice is Gemma 3 1B through Ollama. The disk advice is TabPFN 3.5, Prior Labs' open table model, running in the same process. Both models stay on the laptop.

## Why the ghost is invisible

A pet that sits on the screen all day is just another sticker. This one is closer to a noise in the house: you notice it because something happened. The window is 192 by 192 pixels, always on top, and click-through, so a click still lands on the program underneath. If the click lands on the ghost while it is visible, it also counts as candy. The two facts can both be true because the window never swallows the click.

Scores live in a small JSON file under AppData: ectoplasm, a mood, seven badges, candy. One hundred typing moments makes a chatterbox. Three hundred quiet seconds turns the lights out. October 31 is the only day the Halloween badge can unlock. November 1 and 2 swap the orange tint for a marigold drawn in code, for Día de los Muertos.

## Gemma, on a drive that was almost full

C: had under a gigabyte free when I started. A large model was not going to fit, and sending keystrokes to a hosted model was the wrong trade. `gemma3:1b` is about 800 MB. The prompt it receives is the event name and the mood. Not the letters, not the clipboard, not the file name. It has two seconds to answer, on a background thread, and at most one line every thirty seconds. If Ollama is asleep, a line from a local JSON file is used instead, and the caption says so.

That is the open-model advantage I actually felt. A closed API would be a worse ghost: it would want the text in order to be clever, it would fail when the house Wi-Fi does, and it would add a bill to a joke. The small local model is willing to be brief.

## TabPFN learned the cleanup I had already done

The same laptop was full of leftovers from tools I am not using: Antigravity caches, Codex runtimes, npm, Gradle. I deleted the caches and kept Cursor, because I am using it, and I kept the Antigravity chat folder, because that is history rather than a download.

A rule that deletes anything with "cache" in the name gets the easy piles and then stops. It cannot tell a 6 GB chat folder from a 6 GB Gradle cache. TabPFN 3.5 can, because that choice is a tiny table, and tiny tables are what it is for. The app fits `TabPFNClassifier` on a local CSV of kind, size, age, drive, and the keep-or-sweep label from that cleanup. The dialog shows the chance, such as sweep 91%. Cursor, Windows, Documents, and Desktop are refused in code even if the model is confident. Nothing deletes until I press the button.

The weights sit on D:, which had room. C: does not have to hold the model. After the one-time download, and after accepting Prior Labs' non-commercial license, the suggestion runs with the network off. Cost so far: zero.

## What stays on the machine

The score file stores counts. The dust table stores the features above and stays under AppData. Whisper lines are shown and then forgotten. There is no account, no cloud folder, and no analytics. Wi-Fi off, the ghost still appears, and a model that is already downloaded still answers.

Open weights mattered here because the interesting data is boring and personal: which folders I trust, and the fact that I was typing at all. I did not want either of those in someone else's log.

## Try it

The project is a Windows tray app. `python main.py` starts it. `config.yaml` is the only settings screen. SpriteForge exports drop into `sprites/characters/<name>/`. Ollama serves `gemma3:1b`. TabPFN 3.5 scores the heavy folders from the tray item Haunt the disk.
