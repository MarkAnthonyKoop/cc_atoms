# CLAUDE.md — cc_atoms

AI-only notes for modifying cc_atoms itself. Universal rules in `~/CLAUDE.md`; workspace rules in `~/claude/CLAUDE.md`. Do not restate them here.

---

## File roles (do not conflate)

| File | Role |
|---|---|
| `ATOM.md` | **The contract.** Source of truth for the convention. Do not duplicate its content in README or here. |
| `install.sh` | **The installer.** Copies ATOM.md, patches CLAUDE.md sentinel, runs discovery. ~127 lines. |
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
# Verify install artifacts
diff ~/ATOM.md ~/claude/cc_atoms/ATOM.md && echo "ATOM.md byte-identical"
grep -c 'atom:begin' ~/CLAUDE.md && echo "sentinel present in ~/CLAUDE.md"
grep -v 'atom.*command\|/atom\|atom-status\|cc_atoms v2\|subagent_type=atom' ~/CLAUDE.md | grep -c 'atom' || true

# Verify cc_atoms is flat
ls ~/claude/cc_atoms/ | grep -v '\.md\|install\.sh' && echo "UNEXPECTED FILES" || echo "flat: only .md + install.sh"
```

## v1 archive

`~/claude/cc_atoms_v1/` — archaeology only. Its `task_analyzer.py`, `runtime.py`, EXIT_LOOP_NOW sentinel, and `cc` CLI clone are superseded. Do not import or reference them from here.

## Discovery fallback

If `claude -p` times out or fails during `install.sh`, a stub `~/INDEX.md` is written. The stub contains the manual command to run discovery. This is intentional — discovery is best-effort, not blocking.
