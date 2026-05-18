# CLAUDE.md — cc_atoms

AI-only notes for modifying cc_atoms itself. Universal rules in `~/CLAUDE.md`; workspace rules in `~/claude/CLAUDE.md`. Do not restate them here.

---

## File roles (do not conflate)

| File | Role |
|---|---|
| `ATOM.md` | **The contract.** Source of truth for the convention. Do not duplicate its content in README or here. |
| `install.sh` | **The installer.** Copies ATOM.md, patches CLAUDE.md sentinel, optionally refreshes INDEX.md (only with `--discover`). Every overwrite is backed up first. |
| `README.md` | **Docs.** Human-facing: user manual, reference, architecture, status. Links to ATOM.md; does not restate it. |
| `CLAUDE.md` | This file. AI-facing notes for modifying cc_atoms. |

## The sentinel block (idempotency rule)

`install.sh` patches `<root>/CLAUDE.md` with a block delimited by:

```
<!-- atom:begin -->
...
<!-- atom:end -->
```

Detection order:
1. If sentinels exist → sed-replace between them (idempotent).
2. Else if old heading `### Autonomous recursion — the \`atom\` convention` exists → replace section up to next `---`.
3. Else → append at end.

Running `install.sh` twice must produce the same `CLAUDE.md`. If you change the sentinel block content in `install.sh`, bump a comment in `install.sh` explaining why — the block is load-bearing.

## Constraint: no subdirectories may be reintroduced

cc_atoms is intentionally flat: four files, no subdirs. If a future feature seems to need `agents/`, `bin/`, `commands/`, `skills/`, `hooks/`, or `templates/`, push back:
- Registered subagent → atom mode is a behavior in `ATOM.md`, not a file.
- CLI launcher → users invoke atom mode by telling Claude to read `~/ATOM.md`.
- Templates → templates live in `ATOM.md` § Per-directory templates.
- Hooks / settings → out of scope; document as a future concern in README if needed.

If a feature genuinely requires a new file at this level, it must be a single flat file (not a subdir) and must be justified in a comment at the top of that file.

## Smoke test

```bash
# Install artifacts
diff -q ~/ATOM.md ~/claude/cc_atoms/ATOM.md && echo "ATOM.md byte-identical"
grep -cF '<!-- atom:begin -->' ~/CLAUDE.md && echo "sentinel present in ~/CLAUDE.md"

# Project layout — flat: only ATOM.md, CLAUDE.md, LICENSE, README.md, install.sh (+ .git)
ls ~/claude/cc_atoms/ | grep -vE '^(ATOM\.md|CLAUDE\.md|LICENSE|README\.md|install\.sh)$' \
  && echo "UNEXPECTED FILES" || echo "flat as expected"

# Idempotency — re-running must be a no-op
~/claude/cc_atoms/install.sh
```

## v1 archive

`~/claude/cc_atoms_v1/` — archaeology only. Its `task_analyzer.py`, `runtime.py`, EXIT_LOOP_NOW sentinel, and `cc` CLI clone are superseded. Do not import or reference them from here.

## Discovery is opt-in and non-destructive

Discovery only runs when `install.sh --discover` is passed. The earlier behavior — running discovery on every install and overwriting `~/INDEX.md` with a stub on failure — was destructive and surprised users. The current rule:

- No `--discover` → INDEX.md is not touched at all.
- `--discover` + INDEX.md exists → prompt tells claude to **edit** in place (keep accurate rows, add new projects, remove dead ones). Existing INDEX.md is backed up first.
- `--discover` + INDEX.md absent → claude writes a fresh table.
- `--discover` + discovery times out / fails → INDEX.md is left untouched. Log at `/tmp/atom_discovery.log`.

## Backups

`install.sh` backs up any file before overwriting or in-place patching it. Backup root: `/mnt/d/downloads/cc_atoms/<UTC-timestamp>/<original-absolute-path>`. One timestamp per install run. The summary line prints the backup directory when any backup was made. If you modify the script's destructive paths, route them through `backup_file` first.
