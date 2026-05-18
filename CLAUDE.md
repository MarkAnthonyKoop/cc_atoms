# CLAUDE.md — cc_atoms

You are Claude Code, in the cc_atoms directory. Quiet notes for the work you'll be asked to do here. Universal rules live in `~/CLAUDE.md`; the workspace's rules in `~/claude/CLAUDE.md`; this file adds only what's specific to this project.

---

## If the user is asking you to install cc_atoms

Read [`INSTALLATION.md`](INSTALLATION.md) and do what it describes. The user may ask in any words — *"install cc_atoms"*, *"set it up with the auditor"*, *"reinstall but force-overwrite my customized ATOM.md"*, *"show me what would change before doing it"*. The recipes in `INSTALLATION.md` cover the common ones; anything reasonable beyond that is just file operations against your existing tools.

Two rules that override convenience:

- **Back up before overwriting.** Before any `ATOM.md`, `CLAUDE.md`, or `INDEX.md` is touched, copy the existing file to `/mnt/d/downloads/cc_atoms/<UTC-timestamp>/<original-absolute-path>` so the original survives. Skip only if the user explicitly says to skip. One timestamp directory per install run.

- **Idempotent.** Running an install twice with no other changes between them must change nothing the second time. If your install would do anything on the second run, find out why and fix the install — don't just call it expected.

---

## If the user is editing the cc_atoms project itself

The files in this directory have distinct roles. Don't blur them:

| File | What it is for |
|---|---|
| `ATOM.md` | The contract. The source of truth for the convention. Don't restate its content in `README.md` or here. |
| `INSTALLATION.md` | English recipes for installing. Read by Claude Code at install time. The auditor scripts live in here as fenced code blocks Claude writes to disk on request. |
| `README.md` | Human-facing: what cc_atoms is, how to install in one line, a worked example, troubleshooting. |
| `CLAUDE.md` | This file. AI-facing notes for editing cc_atoms. |
| `LICENSE` | MIT. |

If you're tempted to add a sixth file, ask first. The flat layout is load-bearing — it's the thing that makes "five files, no subdirectories" a real adoption sell. The next subdirectory will not be the last one.

---

## The sentinel block (what makes installs idempotent)

`INSTALLATION.md` instructs you to patch the user's `~/CLAUDE.md` with this block, exactly:

```
<!-- atom:begin -->
### Autonomous recursion — the atom convention

When work is autonomous (recursion, parallel fan-out, multi-directory), use the **atom** convention. The contract is `<root>/ATOM.md` — read it for per-directory structure, recursion rule, spawning, status discipline, and the optional auditor. Discovered tools available to atom workers are indexed at `<root>/INDEX.md`.
<!-- atom:end -->
```

Detect what's already there before patching:

1. If the sentinels exist, replace what's between them.
2. If an old, sentinel-less heading like `### Autonomous recursion — the atom convention` exists, replace from that heading down to the next horizontal rule (`---`) or the end of the file.
3. Otherwise, append the whole block at the end.

If the block on disk already matches exactly, do nothing. That's how a second install becomes a no-op.

---

## v1 lives elsewhere

The pre-v2 Python orchestrator (iteration loop, retry manager, complexity analyzer, meta-agent dispatcher, EXIT_LOOP_NOW sentinel, `cc` CLI clone) is archived at `~/claude/cc_atoms_v1/` locally and at [`github.com/MarkAnthonyKoop/cc_atoms_v1`](https://github.com/MarkAnthonyKoop/cc_atoms_v1) remotely. It's for archaeology. Don't import from it. Don't reference it from here except to say "that's where it went."

---

## Smoke test

After any change to this project, run this from `~/claude/cc_atoms/`:

```bash
# Files at the right level
ls | grep -vE '^(ATOM\.md|INSTALLATION\.md|CLAUDE\.md|README\.md|LICENSE)$' \
    && echo "UNEXPECTED FILES" \
    || echo "flat layout intact"

# Contract is byte-identical between repo and install root (if installed)
[ -f ~/ATOM.md ] && diff -q ~/ATOM.md ATOM.md && echo "ATOM.md byte-identical at install root"

# Sentinel block exists in user's top-level CLAUDE.md (if installed)
[ -f ~/CLAUDE.md ] && grep -cF '<!-- atom:begin -->' ~/CLAUDE.md && echo "sentinel present"

# Idempotency: ask Claude to install again, observe that nothing changes
# (run claude in this dir, say "install cc_atoms again" — there should be zero file modifications)
```
