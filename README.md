# cc_atoms

**To install:** open Claude Code in this directory and say *"install cc_atoms."* The full menu of installation options lives in [`INSTALLATION.md`](INSTALLATION.md), but you don't have to read it — Claude does. Ask in any words you like.

---

## What it is

cc_atoms is a convention for letting Claude Code do autonomous, multi-directory work without losing its mind.

It is one contract file (`ATOM.md`) and one installer (`INSTALLATION.md`, read and executed by Claude itself). That's the whole product. The convention says: every autonomous-work directory holds three short files (`USER_PROMPT.md`, `README.md`, `CLAUDE.md`), and when work is bigger than one session can handle, you split it by *directory* — make a child dir, write its task, spawn a child Claude against it.

The contract file is `ATOM.md` in this directory. Read it if you want to understand the convention from the inside. Or don't — Claude reads it for you.

---

## Adopting it

Three small things happen when you install:

1. The contract (`ATOM.md`) lands at your home as `~/ATOM.md`.
2. Your top-level `~/CLAUDE.md` gets one paragraph added between sentinels, pointing every future Claude session at that contract.
3. Optionally, `~/INDEX.md` gets populated with a one-line description of every project on your machine, so atom workers can find tools that already exist.

That's all. The install is reversible (`"uninstall cc_atoms"`), idempotent (running it twice changes nothing the second time), and protective (every overwrite is mirrored to `/mnt/d/downloads/cc_atoms/<UTC>/` before the change). Details: [`INSTALLATION.md`](INSTALLATION.md).

---

## Using it

After install, atom mode is *behavior*, not a binary. There is nothing to run.

Open Claude Code in any directory and say *"operate in atom mode"* — or just give it a task it would naturally want to decompose ("build me a small game", "audit this codebase", "transcribe and tag these MP3s"). Claude will read `~/ATOM.md`, recognize the shape of the work, write the three small files into your directory, do the work itself or hand pieces of it to child atoms, and keep the `Status` block in `README.md` honest as it goes.

For most tasks, the convention is enough. For long multi-hour runs, ask Claude to *"set up the auditor"* — a small loop that walks the tree every fifteen minutes and respawns anything that has gone quiet. The recipe is in [`INSTALLATION.md`](INSTALLATION.md).

---

## A worked example

In May 2026 I asked atom mode to build *"a fully functional Rocket League clone, only way better."* The first pass — sixteen minutes — produced a single-file pygame game with car physics, ball physics, two goals, an AI opponent, and three sub-atoms (`audio/`, `ai/`, `arena/`). The second pass — seventy minutes, stopped by a Claude Max usage limit — fanned out to sixty sub-atom directories across thirteen new subsystems (networking, splitscreen, replay export, telemetry, smarter AI, more game modes). The third pass — about four hours of wall-clock, broken up by usage limits and respawned each time by an auditor running on a fifteen-minute cycle — walked the sixty sub-atoms, wired them into `main.py`, rewrote the `Status` block, and verified the smoke test still passed.

The tree ended at one hundred and fifteen directories and roughly eight thousand lines of Python. The auditor was the only thing that kept it alive across the usage-limit interruptions. Nothing about the run required code that cc_atoms ships — just the convention and the recipe.

---

## What's in this directory

```
~/claude/cc_atoms/
├── ATOM.md           the convention — read by Claude (and by you, if you want)
├── INSTALLATION.md   English installation recipes Claude reads and executes
├── README.md         this file
├── CLAUDE.md         quiet notes for the Claude that maintains this project
└── LICENSE
```

Five files. No subdirectories. No Python. No package manager. The earlier version (v1) shipped thousands of lines of orchestration code; almost every line of it has a native counterpart in Claude Code now, so v2 deleted it. The v1 archive lives at [`MarkAnthonyKoop/cc_atoms_v1`](https://github.com/MarkAnthonyKoop/cc_atoms_v1) if you want to see what the old shape looked like.

---

## Troubleshooting

If a child `claude -p` invocation fails with *"Credit balance is too low,"* the parent process inherited an `ANTHROPIC_API_KEY` from the harness and the child switched to API billing. Strip it: `env -u ANTHROPIC_API_KEY claude …`. The contract mentions this; it's the most common surprise.

If a non-interactive `claude -p` hangs forever, it's waiting on a permission prompt that no one will answer. Add `--dangerously-skip-permissions`.

If you hit a Claude Max usage limit mid-run, the message tells you when it resets ("resets 11pm America/Chicago"). The auditor recipe in `INSTALLATION.md` exists for exactly this reason — it'll respawn collapsed atoms once the budget is back.

If atom mode is decomposing too aggressively for the task at hand, tell it so: *"keep this in one atom, no children."* The convention bends.

---

## Status

cc_atoms v2.4 — contract-only, installer-as-conversation, prose iterated on real reader feedback. **Stable.**

Two kinds of evidence stand behind that word.

The contract has been exercised end-to-end on a one-hundred-and-fifteen-directory autonomous run (the rocket league experiment described above), where the auditor recipe revived collapsed atoms across multiple Claude Max usage-limit interruptions. The install is idempotent and reversible. Every overwrite is mirrored to a timestamped backup directory before the change.

The prose has been iterated against real readers — fresh Claude Code atoms reading `ATOM.md` cold and building things: pong, snake, blackjack, tetris, a duplicate-file finder. Each test surfaced exactly the points where the prose was unclear; each clarification went into the next version. The fix-count per test ran 4 → 6 → 2 → 0 → 0 — diminishing returns, then convergence. The last two tests ran without an explicit "rate the doc" hook in their prompt, and the atoms volunteered nothing. That's the signal the doc is invisible to a working reader, which is what good prose does.

If you adopt it and something doesn't fit, the prose is at fault — open an issue or just edit it.
