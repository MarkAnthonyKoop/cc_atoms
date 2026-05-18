# cc_atoms — atom convention for autonomous Claude Code work

cc_atoms is one contract file (`ATOM.md`) plus one installer (`install.sh`). That is the entire product. The v1 Python orchestrator is archived at `~/claude/cc_atoms_v1/`; everything it did is now native to Claude Code.

---

## User manual

### Adopt in 60 seconds

```bash
# 1. Get the repo (skip if already at ~/claude/cc_atoms/)
git clone https://github.com/MarkAnthonyKoop/cc_atoms ~/claude/cc_atoms

# 2. Install
~/claude/cc_atoms/install.sh
```

That copies `ATOM.md` to `~/ATOM.md` and patches `~/CLAUDE.md` with a sentinel-delimited pointer. Discovery (populating `~/INDEX.md`) is opt-in via `--discover` — see Reference below.

### Use atom mode

Atom mode is a behavior, not a command. There is no `atom` binary after this refactor. To work in atom mode:

1. `cd` to any directory (new or existing).
2. Write `USER_PROMPT.md` describing the task.
3. Open Claude Code in that directory.
4. Tell it: "Operate in atom mode per `~/ATOM.md`."

Claude reads the contract, keeps `README.md` and `CLAUDE.md` accurate as it works, delegates subtasks to child atoms via subdirectories, and marks `Status: COMPLETE` when done.

### Parallel fan-out (10 instances)

Create sibling subdirs, each with its own `USER_PROMPT.md`, then in a single Claude message issue one `Agent` tool call per subdir. Claude Code runs them concurrently. See `~/ATOM.md` § Spawning copies of yourself.

### Check progress

```bash
cat README.md       # Status section is the live log
# or, from inside a Claude Code session, ask: "summarize all README.md Status files under <dir>"
```

---

## Reference

### `install.sh` flags

| Flag | Effect |
|---|---|
| *(none)* | Install to `~` (where user-level `CLAUDE.md` lives). Skips discovery. |
| `--root <path>` | Use a different install root |
| `--extra-path <path>` | Extra dirs for INDEX.md discovery (repeatable; meaningful only with `--discover`) |
| `--force` | Overwrite `<root>/ATOM.md` even if it differs (previous contents backed up first) |
| `--discover` | Refresh `<root>/INDEX.md` via `claude -p`. Edits existing INDEX.md in place if present; creates fresh if absent. Off by default because discovery is slow and AI-billed, and a stale INDEX.md is more useful than a missing one. |

### Files placed at install root

| File | What it is |
|---|---|
| `<root>/ATOM.md` | The full convention — copied from `~/claude/cc_atoms/ATOM.md` |
| `<root>/CLAUDE.md` | Patched in-place: sentinel block added/replaced (see below) |
| `<root>/INDEX.md` | Discovered project index (or stub if `claude` CLI is unavailable) |

### Sentinel-delimited CLAUDE.md block

`install.sh` inserts or replaces exactly this block in `<root>/CLAUDE.md`:

```
<!-- atom:begin -->
### Autonomous recursion — the atom convention

When work is autonomous (recursion, parallel fan-out, multi-directory), use the **atom** convention. The contract is `<root>/ATOM.md` — read it for per-directory structure, recursion rule, spawning, status discipline, and the optional auditor. Discovered tools available to atom workers are indexed at `<root>/INDEX.md`.
<!-- atom:end -->
```

Idempotent: running `install.sh` twice produces the same result.

### Discovery

Opt-in via `--discover`. Runs `claude -p "<discovery prompt>"` with a 300s timeout (uses `--model sonnet`).

- If `<root>/INDEX.md` **already exists**, the prompt instructs Claude to **edit it in place**: keep accurate rows, add new projects, remove dead ones, preserve human-authored prose.
- If `<root>/INDEX.md` does **not** exist, Claude writes a fresh markdown table modeled on `~/claude/INDEX.md`.
- If discovery **fails or times out**, the existing `<root>/INDEX.md` is **left untouched** (the destructive "overwrite with stub on failure" behavior of earlier versions is gone). The error log is at `/tmp/atom_discovery.log`.

### Backups

Every overwrite or in-place patch backs the original up first. Backup root: `/mnt/d/downloads/cc_atoms/<UTC-timestamp>/<original-absolute-path>`. One timestamp per install run. The summary line at the bottom of `install.sh` output prints the backup directory when any backup was made.

### INDEX.md format

Modeled after `~/claude/INDEX.md`: a markdown table, one row per project, one-line description. Human-editable after generation.

---

## Architecture

### Why one contract file + one installer

cc_atoms v1 shipped ~thousands of lines: iteration loop, retry manager, complexity analyzer, memory provider, meta-agent dispatcher, quality gate, EXIT_LOOP_NOW protocol. **Every one of those concerns is now native to Claude Code.** See `~/ATOM.md` § Rationale for the full table.

What remains is the **convention**: every autonomous-work directory carries `USER_PROMPT.md` + `README.md` + `CLAUDE.md`, and recursion happens by creating subdirectories and calling the `Agent` tool. That fits in one file. The installer places it and wires the CLAUDE.md pointer.

### What is not here (intentionally)

- No `agents/`, `bin/`, `commands/`, `skills/`, `hooks/`, `templates/` directories.
- No registered subagent file. Atom mode is a behavior described in `ATOM.md`, not an installable agent.
- No `atom` binary. The convention is invoked by telling Claude to read `~/ATOM.md`.
- No Python, no package manager, no PyPI.

Adding any of these back conflates the convention with an engine. The v2 philosophy is: Claude Code is the engine; `ATOM.md` is the instruction set.

### Layout (flat by design)

```
~/claude/cc_atoms/
├── ATOM.md          the contract — source of truth for the convention
├── install.sh       places ATOM.md, patches CLAUDE.md, runs discovery
├── README.md        this file
└── CLAUDE.md        AI notes for modifying cc_atoms itself
```

---

## Status

**COMPLETE** — refactored 2026-05-16, hardened 2026-05-17.

### Done
- Deleted `agents/`, `bin/`, `commands/`, `skills/`, `hooks/`, `templates/` from cc_atoms
- Removed symlinks: `~/.claude/agents/atom.md`, `~/.claude/commands/atom.md`, `~/.claude/commands/atom-status.md`, `~/.local/bin/atom`
- Rewrote `README.md` (this file, ≤200 lines) and `CLAUDE.md` (≤100 lines)
- Updated `~/claude/INDEX.md` cc_atoms entry to contract-first framing
- Initialized git in this directory; pushed v2 to `github.com/MarkAnthonyKoop/cc_atoms` (HEAD is v2; v1 history preserved in the log). v1 also archived to its own repo `github.com/MarkAnthonyKoop/cc_atoms_v1`.
- Hardened `install.sh`: discovery is opt-in (`--discover`), INDEX.md is edited in place when present, every overwrite is backed up to `/mnt/d/downloads/cc_atoms/<UTC>/...`, discovery failure no longer destroys an existing INDEX.md, timeout bumped to 300s, default model is `sonnet`.

### Next
- (nothing — task complete)

### Delegated
- (none)
