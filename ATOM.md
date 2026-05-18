# ATOM.md — the convention

You are Claude Code. Someone has asked you to operate **in atom mode**, or you've landed in a directory that holds a `USER_PROMPT.md` and a sibling `README.md` with a `Status` block. Either way, what follows is how the work goes.

This file is short on purpose. The work is yours; the rules are few.

---

## What an atom is

An atom is one directory doing one job.

In the directory, three files speak for the work:

- **`USER_PROMPT.md`** — the task that brought you here. Read it. Don't change it. It's a handoff from whoever spawned this atom (a parent atom, or the person who started the run). If a person is at the keyboard talking to you instead, there's no `USER_PROMPT.md` and there doesn't need to be — *the conversation is the task.*

- **`README.md`** — what a human reading later will want to know. A short user guide on top, a reference section in the middle, an architecture note at the bottom, and a `Status` block that you keep accurate as you work. The `Status` block is the only part that changes often.

- **`CLAUDE.md`** — what a future Claude in this directory will need to know that isn't already in `README.md` or visible in the code. Quiet notes: the workaround you had to use, the constraint that isn't enforced, the credential that's already cached.

If `README.md` or `CLAUDE.md` is missing when you arrive, write them from the [templates at the bottom of this file](#templates). The first atom to land in a directory bootstraps these files; subsequent invocations only maintain them. Don't write a long `README.md` for a small dir; match the length to the work.

---

## When the work is bigger than one atom

> *If the task at hand fits comfortably in one atom, skip this whole section. Spawning children is the answer to size, not the default.*

Split it into pieces, give each piece a directory, and hand each one to a child.

**The rule: one piece, one directory, one child atom.** If a subtask is genuinely independent of its siblings, spawn them all at once and let them run in parallel.

There are three ways to spawn a child. Pick the one that fits.

### Through the Agent tool — when you need the result back this turn

Call the real `Agent` tool (don't paste the pseudo-form below as literal JSON; this is how the call reads in prose):

```
Agent(
  description: "<subdir> atom",
  prompt: "You are an atom. cd to <abs path to subdir>. Read ~/ATOM.md and USER_PROMPT.md. Do the work. Keep README.md Status accurate. Return a one-paragraph summary."
)
```

The child runs in its own context window. You see only its summary. To fan out, issue many Agent calls in a single message — they run together.

### As a detached `claude` process — when you want it to outlive this turn

```
cd <subdir> && env -u ANTHROPIC_API_KEY claude --dangerously-skip-permissions --model opus \
    -p "Operate as an atom per ~/ATOM.md and USER_PROMPT.md here." \
    > /tmp/atom_<id>.log 2>&1 &
```

Two flags are load-bearing. `env -u ANTHROPIC_API_KEY` strips a variable that the harness exports into subprocesses; if you leave it in place, the child quietly switches to API billing and fails with *"Credit balance is too low."* `--dangerously-skip-permissions` lets the non-interactive child auto-accept the permission prompts it would otherwise hang on. Opus is the right default for atom work; sonnet is fine for light leaves.

### As a resumed conversation — when picking up a paused atom

```
env -u ANTHROPIC_API_KEY claude --dangerously-skip-permissions --resume <conv-id> \
    -p "Continue per <pointer to the relevant file or fact>."
```

The conversation id lives under `~/.claude/projects/<slug>/`. Use this to wake a stalled atom rather than starting it fresh.

---

## Recursion, briefly

If the task is bigger than one atom can comfortably do in one session, decompose it by directory — not by Python loop, not by long single conversation.

For each piece of the work:

1. Make a subdirectory.
2. Write its `USER_PROMPT.md`.
3. Spawn a child atom against it (any of the three patterns above).
4. Record the delegation in *this* atom's `README.md` `Status` block.
5. When the child returns its summary, fold the summary into your `Status` block. Don't reach into the child's directory and rewrite its files — the child owns its files.

Context isolation is automatic. Each child gets its own fresh window. Yours stays clean no matter how deep the tree goes.

---

## Status discipline

The `Status` block in `README.md` is your single source of truth for "where this atom is right now." Keep it short, current, and honest.

Use one of four words for the top of the block:

- **`IN_PROGRESS`** — still working here.
- **`DELEGATED`** — children are doing the work; waiting on or folding in their summaries.
- **`BLOCKED`** — needs the user or an external thing. Name the thing.
- **`COMPLETE`** — done, verified.

Under the `## Status` heading, the state word goes on its own line as bold text followed by a one-line gloss (e.g. `**IN_PROGRESS** — wiring sub-atoms into main.py`). Beneath that, three short lists as their own `###` headings: `### Done` for what you finished and verified this session, `### Next` for what comes next, `### Delegated` for what you handed to children (one line per child, with that child's current state). The templates at the end of this file show the exact shape — match them.

If your smoke test or end-to-end check fails, stay `IN_PROGRESS`. Don't mark `COMPLETE` until you can re-run the verification and see it pass.

You return when the task is satisfied, when the work has been handed off, or when something outside this dir is in the way. One pass per invocation. If more iterations are needed, the user (or an auditor — see below) re-invokes you.

---

## Tools that already exist

Before you build something, check the install root's `INDEX.md` — usually `~/INDEX.md`, since the default install places `ATOM.md` and `INDEX.md` side by side in the user's home directory. It's a one-line-per-project map of what's already on this machine. atom mode workers consult it to avoid reinventing what's already written. If a tool lives outside the install root, the user has to tell you about it — either by editing `INDEX.md` or by mentioning it in `USER_PROMPT.md`.

---

## When a tree of atoms runs for a long time

For most work, a single atom — or a small tree — finishes inside one Claude session and you're done. For runs that span hours or days, with many children and real risk that a node will time out or hit a usage limit, spin up an **auditor**: another atom in its own directory beside the work, woken on a schedule, that walks the tree and respawns anything gone quiet without finishing.

The minimum auditor is a sibling directory (`<work_root>/_audit/`) with a `USER_PROMPT.md` describing the audit job (walk every `README.md`, check `Status`, ps-grep live `claude` processes, respawn any `IN_PROGRESS` directory whose process has died) and a small shell loop that wakes it every fifteen or thirty minutes:

```bash
# In <work_root>/_audit/, two parallel loops offset by 15 min.
nohup bash -c 'for i in {1..10}; do
  timeout 300 env -u ANTHROPIC_API_KEY claude --dangerously-skip-permissions --model sonnet \
    -p "Operate as an atom per ~/ATOM.md and ./USER_PROMPT.md here." >> /tmp/audit_a.log 2>&1
  sleep 1800
done' &
```

If you have the cc_atoms repo cloned, the full auditor scripts — including the dashboard write to `AUDIT.md` and the two-worker staggered loop — live as fenced code blocks in `INSTALLATION.md`. Open a Claude Code session in `~/claude/cc_atoms/` and say *"set up the auditor for `<work_root>`"* and Claude will materialize them.

---

## Why this fits in one file

Earlier versions of cc_atoms shipped thousands of lines: an iteration loop, a retry manager, a complexity analyzer, a memory layer, a meta-agent dispatcher, a quality gate, an exit-loop sentinel. Each of those pieces had a job. Claude Code now does each of those jobs natively — the Agent tool, hooks, the SDK, the `CLAUDE.md` cascade. The orchestration code became redundant.

What was left is what you're reading: the convention.

---

## Templates

### `README.md` for a fresh atom directory

```markdown
# <dir name>

## User manual
<one short paragraph: what does this dir do, how does a human use it>

## Reference
<every CLI flag, function signature, or file contract this dir exposes — or, for a single-script atom where the user manual already covers everything: "see User manual above">

## Architecture
<why the splits are where they are; what belongs here vs. a sibling — or, for a single-file leaf where there are no splits: "n/a — single file">

## Status
**IN_PROGRESS** — atom session started.

### Done
- (nothing yet)

### Next
- (read USER_PROMPT.md and begin)

### Delegated
- (none)
```

Match the section depth to the work. A small leaf can fold `Reference` into `User manual` and skip `Architecture`; a large dir with many sub-modules earns the full structure.

### `CLAUDE.md` for a fresh atom directory

```markdown
# CLAUDE.md — <dir name>

Quiet notes for the next Claude in this directory. Don't duplicate README.md.

- (decomposition decisions, cached credentials scoped to this dir,
  fragile workarounds and why, the smoke-test command)
```
