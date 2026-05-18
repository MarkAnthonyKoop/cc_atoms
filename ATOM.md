# ATOM.md — the convention

This file teaches Claude Code an **autonomous mode** for hierarchical, massively parallel work. There is no Python, no registered agent, no install beyond placing this file (and a one-block pointer in CLAUDE.md) at the top of your workspace.

When you are told to "operate in atom mode" or you find a directory containing `USER_PROMPT.md`, follow this convention.

---

## The three artifacts in every atom directory

```
<cwd>/
├── USER_PROMPT.md   ← task for this directory (input — read first, never modify)
├── README.md        ← user guide + reference + architecture + Status (durable)
├── CLAUDE.md        ← AI-only notes for this dir and below (no duplication with README)
└── <work>           ← code, subdirs, deliverables
```

If `README.md` or `CLAUDE.md` is missing on entry, bootstrap them from the templates at the end of this file.

`README.md` structure:
1. **User manual** (top) — quickstart for a human entering this dir
2. **Reference** (middle) — every interface this dir exposes
3. **Architecture** (bottom) — why the splits are where they are
4. **Status** (the only mutable block) — one of `IN_PROGRESS / DELEGATED / BLOCKED / COMPLETE`, plus Done / Next / Delegated lists

---

## Spawning copies of yourself

Atom mode is built on **Claude spawning Claude**. Three flavors:

### 1. In-session subagents — parent waits for child

Use the `Agent` tool. The child runs in a fresh context window; the parent sees only the return summary.

```
Agent(
  description: "<subdir> atom",
  prompt: "You are an atom. cd to <abs path to subdir>. Read ~/ATOM.md and USER_PROMPT.md. Execute the work, keep README.md Status accurate. Return a one-paragraph summary."
)
```

For parallel sub-work, issue **multiple Agent tool calls in a single message** — the harness runs them concurrently.

### 2. Detached processes — massive parallel, fire-and-forget

When you need 10+ workers or want them to outlive this session:

```bash
cd <subdir> && env -u ANTHROPIC_API_KEY claude --dangerously-skip-permissions --model opus -p "Operate as an atom per ~/ATOM.md and USER_PROMPT.md here." >/tmp/atom_<id>.log 2>&1 &
```

Each is a separate OS process with its own conversation. The parent doesn't see results directly — the auditor (below) reconciles state via the README.md Status files.

**Both flags are load-bearing:**
- `env -u ANTHROPIC_API_KEY` — Claude Code's harness exports `ANTHROPIC_API_KEY` into subprocess env. The interactive CLI ignores it and uses Claude Max OAuth from `~/.claude/.credentials.json`, but any child `claude -p` invocation that inherits the env switches to API billing — and if that account has no credit, every spawn fails with `Credit balance is too low`. Stripping the env var forces the OAuth path.
- `--dangerously-skip-permissions` — `-p` is non-interactive, so any permission prompt blocks the process forever. This flag auto-accepts.

`--model opus` is optional but recommended for atom work.

### 3. Resuming a stalled conversation

```bash
env -u ANTHROPIC_API_KEY claude --dangerously-skip-permissions --model opus --resume <conv-id> -p "Continue per <pointer to relevant file or fact>"
```

`<conv-id>` is the UUID of an existing conversation under `~/.claude/projects/<slug>/`. Use to revive a paused atom rather than starting fresh.

---

## Recursion rule

If `USER_PROMPT.md` is bigger than one coherent session, decompose **by directory, not by Python loop**:

1. Pick 2–N subtasks (more if genuinely independent — fan-out arbitrarily wide).
2. For each: `mkdir <subdir>`, write `<subdir>/USER_PROMPT.md`.
3. Spawn a child atom for each (see "Spawning copies of yourself").
4. Update *this* directory's `README.md` Status `Delegated` list with one line per child.
5. When children return summaries, append them to Status; do not touch the child's files — the child owns them.
6. Integrate, test, and document the result here.

Context isolation is automatic — each child is a fresh window, so the parent context stays clean regardless of tree depth.

---

## Status discipline

Every meaningful change updates `README.md`'s Status section. Keep three short lists inside it:

- **Done** — what was actually completed and verified this session
- **Next** — concrete next steps
- **Delegated** — `<subdir>/` → one-line description + child's current status

Status values:
- `IN_PROGRESS` — still working here
- `DELEGATED` — children doing the work; waiting for or integrating their summaries
- `BLOCKED` — needs the user or an external dependency (be specific about what)
- `COMPLETE` — done, verified

---

## When to stop

- `USER_PROMPT.md` is satisfied → Status `COMPLETE`, return.
- Subtasks delegated, in flight elsewhere → Status `DELEGATED`, return.
- External blocker → Status `BLOCKED` with what's needed, return.

One pass per invocation. Re-invoke for more iterations. There is no `EXIT_LOOP_NOW` sentinel, no complexity analyzer, no iteration counter.

---

## Discovering existing tools

When useful work depends on tools that already exist on this machine, consult `<install-root>/INDEX.md` — the discovered-tools index, populated by `install.sh` and user-editable thereafter. Prefer extending an indexed tool over building parallel functionality.

If the tool you need is not below the install root, the user must tell you about it — either by editing `INDEX.md` or by including a pointer in `USER_PROMPT.md`.

---

## The auditor pattern (optional, for long-running hierarchies)

If a tree of atoms is running for hours or days and you need self-healing, kick off an auditor in a separate session:

```
loop 20m 'audit the atom tree at <root>: walk all README.md Status files; ps-grep running claude processes; respawn IN_PROGRESS atoms with no live process via claude -c <id>; start fresh atoms for BLOCKED-but-actionable dirs with prompts pointing at relevant files/convs; write a one-page dashboard to <root>/AUDIT.md'
```

The auditor is itself an atom in a single directory (e.g. `~/work/_audit/`) with its own `USER_PROMPT.md` describing scope and cadence. Use the `loop` skill (or cron) to wake it.

Not auto-started by `install.sh`. Spin up when you need it.

---

## Per-directory templates

### README.md template

```markdown
# <dir name>

## User manual
<one-paragraph quickstart for a human entering this directory>

## Reference
<every CLI / function / file contract this dir exposes>

## Architecture
<why the splits are where they are, what belongs here vs siblings>

## Status
**IN_PROGRESS** — atom session started.

### Done
- (nothing yet)

### Next
- (read USER_PROMPT.md and begin)

### Delegated
- (none)
```

### CLAUDE.md template

```markdown
# CLAUDE.md — <dir name>

AI-only notes for this directory and below. Do not duplicate README.md.

- (decomposition decisions, scoped credentials, fragile workarounds, smoke-test commands)
```

---

## Rationale (why this is just one file)

Every piece of orchestration that earlier atom frameworks (cc_atoms v1 Python, v2 with registered subagent) used to do has been absorbed by Claude Code natively:

| Old component | Native replacement |
|---|---|
| Python iteration loop | `Agent` tool + spawned `claude -p` processes |
| Registered subagent file | This file — atom mode is a behavior, not an installable agent |
| Decomposition planner | The atom itself, when told to delegate |
| Quality-gate red flags | Atom checks its own work before marking `COMPLETE` |
| Memory injection | `CLAUDE.md` cascade + auto memory |
| Retry / rate-limit | Built into the CLI |

What's left is the convention — and it fits in this file.
