# Installing cc_atoms

You don't run an install script. You ask Claude Code.

Open a Claude Code session in this directory and tell it what you want, in any words you like. The recipes below are what Claude will do — pick the one that sounds right, or describe your own. There are no flags to memorize.

```
cd ~/claude/cc_atoms   # or wherever you cloned it
claude                 # opens Claude Code with this dir in scope
```

Then say something like *"install cc_atoms"* or *"walk me through the installation options."*

---

## The basic install

> *"Install cc_atoms."*

Claude will copy this directory's `ATOM.md` to your home (`~/ATOM.md`) and add a small block to your top-level `~/CLAUDE.md`, set off by `<!-- atom:begin -->` and `<!-- atom:end -->` sentinels. The block is one paragraph long and tells every future Claude Code session you start: *"when work calls for autonomous recursion, the convention lives at `~/ATOM.md`."*

That's the whole install. No network calls, no AI billing, a few seconds.

If a file is about to be overwritten, Claude first copies the original to `/mnt/d/downloads/cc_atoms/<UTC-timestamp>/` in a mirror of its original path. Nothing ever vanishes silently. To skip backups, say so: *"install but don't bother with backups."*

To install somewhere other than your home directory, name the place: *"install cc_atoms to `/opt/shared/atoms`."*

---

## With a project index

> *"Install cc_atoms and discover my projects."*

Same as above, plus Claude walks your home directory (and any extra paths you mention) looking for things that look like projects — directories marked by `.git`, `pyproject.toml`, `package.json`, or a `README.md` — and writes a one-line description of each to `~/INDEX.md`. Atom workers consult this index to find what already exists before reinventing it.

This step takes roughly thirty seconds and counts against your Claude usage. If `~/INDEX.md` already exists, Claude edits it in place: it keeps rows whose project is still there and still described correctly, adds rows for anything new, and removes rows for things that have moved on. Your hand-written notes survive.

---

## With the auditor

> *"Install cc_atoms and set me up for long autonomous runs."*

Most atom work finishes inside a single Claude session. For runs that last hours or days — many children, deep trees, real risk that a node will time out or hit a Claude Max usage limit — there's an auditor pattern that catches collapsed atoms and starts them back up.

Ask for this and Claude will materialize a template auditor at `~/atom_runs/_audit_template/` with three files: a `USER_PROMPT.md` that describes what the audit atom does, and two short shell scripts that run it on a schedule. When you later kick off a long atom project, copy this template alongside it and start the loop. The scripts are below — Claude reads them and writes them to disk verbatim.

### `USER_PROMPT.md` — the audit atom's brief

```markdown
# Audit and revive an atom tree

## Target

The atom tree at `<TARGET_DIR>` (replace at copy time, or pass via env).

## What to do this pass

1. **Walk the tree.** Find every directory under the target that has a `README.md`. Read its `## Status` block. Note: the status word, the most recent `Done` items, and any `Delegated` entries.

2. **Check liveness.** Run `ps -eo pid,etime,cmd | grep -E '[c]laude.*dangerously'` to see which claude processes are alive. Cross-reference with each directory's most recent log file under `/tmp/atom_*.log`.

3. **Decide per directory:**
   - `COMPLETE` — leave alone.
   - `IN_PROGRESS` with a live claude process — leave alone.
   - `IN_PROGRESS` with no live process and no log update in the last ten minutes — the atom has collapsed. Respawn it: `cd <dir> && env -u ANTHROPIC_API_KEY claude --dangerously-skip-permissions --model opus -p "Operate as an atom per ~/ATOM.md and USER_PROMPT.md here. Resume any incomplete work."` in the background, logging to `/tmp/atom_<basename>_$(date +%s).log`.
   - `BLOCKED` with a specific blocker named — leave alone; that's the user's call.
   - `BLOCKED` without a real blocker — respawn and say so in the prompt.
   - `DELEGATED` — walk into the children and apply the same rules.

4. **Write a dashboard** to `<TARGET_DIR>/AUDIT.md` with: the UTC timestamp of this pass, a tree of directories and their Status words, the live claude processes, what you respawned this pass, and any directory that has been `BLOCKED` for more than two consecutive audits (flag those for the user).

5. **Update your own `README.md` Status** in this directory with what you did this pass.

## Rules

- No more than five respawns in one pass. If more are needed, list them under `Next` for the next pass to pick up.
- Never modify a sub-atom's files. The sub-atom owns its files. You only orchestrate respawns and write to `AUDIT.md`.
- Re-running this audit twice in a row with no state change between them produces the same actions. Check log mtimes before respawning anything you might have respawned thirty seconds ago.
- Budget: five minutes per pass.
```

### `run_audit_pass.sh` — one audit pass

```bash
#!/usr/bin/env bash
# One audit pass. Invoked by the loop driver. Spawns claude on this directory
# to read USER_PROMPT.md and execute one audit. Five-minute cap per pass.

set -euo pipefail

AUDIT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
WORKER_ID="${AUDIT_WORKER_ID:-x}"
LOG="/tmp/atom_audit_${WORKER_ID}_${TS}.log"

cd "$AUDIT_DIR"

timeout 300 env -u ANTHROPIC_API_KEY claude \
    --dangerously-skip-permissions \
    --model sonnet \
    -p "Operate as an atom per ~/ATOM.md and ./USER_PROMPT.md here. Audit worker $WORKER_ID, pass $TS." \
    > "$LOG" 2>&1

EXIT=$?
echo "[$(date -u +%Y%m%dT%H%M%SZ)] worker=$WORKER_ID exit=$EXIT log=$LOG" >> "$AUDIT_DIR/heartbeat.log"
exit $EXIT
```

### `audit_loop.sh` — the schedule

```bash
#!/usr/bin/env bash
# Audit loop. Two copies of this run in parallel, offset by fifteen minutes,
# so the tree sees an audit pass every fifteen minutes.
#
# Usage: audit_loop.sh <worker_id> <initial_sleep_seconds> <max_passes>

set -euo pipefail

WORKER_ID="${1:-x}"
INITIAL_SLEEP="${2:-0}"
MAX_PASSES="${3:-10}"

AUDIT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
export AUDIT_WORKER_ID="$WORKER_ID"

echo "[$(date -u +%Y%m%dT%H%M%SZ)] worker=$WORKER_ID start initial=${INITIAL_SLEEP}s max=$MAX_PASSES" \
    >> "$AUDIT_DIR/heartbeat.log"

sleep "$INITIAL_SLEEP"

for pass in $(seq 1 "$MAX_PASSES"); do
    echo "[$(date -u +%Y%m%dT%H%M%SZ)] worker=$WORKER_ID pass=$pass starting" \
        >> "$AUDIT_DIR/heartbeat.log"
    "$AUDIT_DIR/run_audit_pass.sh" \
        || echo "[$(date -u +%Y%m%dT%H%M%SZ)] worker=$WORKER_ID pass=$pass FAILED" \
            >> "$AUDIT_DIR/heartbeat.log"
    [[ $pass -lt $MAX_PASSES ]] && sleep 1800
done
```

To kick off the auditor against a real atom tree later, the recipe is the same — copy this template directory beside the work and run two loops offset by fifteen minutes:

```
cp -r ~/atom_runs/_audit_template ~/atom_runs/<your_project>/_audit
cd ~/atom_runs/<your_project>/_audit
nohup bash audit_loop.sh A 0    10 > /tmp/audit_a.log 2>&1 &
nohup bash audit_loop.sh B 900  10 > /tmp/audit_b.log 2>&1 &
```

Or just tell Claude Code *"start the auditor on `~/atom_runs/<your_project>/`"* and it'll do all of that for you.

---

## Uninstall

> *"Uninstall cc_atoms."*

Claude removes the sentinel block from `~/CLAUDE.md`, deletes `~/ATOM.md` (after backing it up), and — if you ask — removes `~/INDEX.md` too. The auditor template, if you installed it, is left alone in case you've customized it.

---

## What else you can ask

The recipes above are the common ones. Because the install is just file operations, anything reasonable works. Examples that get the right answer:

> *"Show me what installing cc_atoms would change on my system, but don't change anything yet."*
> *"I already have an `~/ATOM.md`. Diff it against this repo's version before deciding."*
> *"Reinstall cc_atoms and force-overwrite my customized `~/ATOM.md` — I want the fresh version."*
> *"I'm on macOS — adapt the install for me."*
> *"Install cc_atoms for my whole team — generate a script we can check into our dotfiles repo."*

Claude reads this file and the project's `CLAUDE.md` to know how to do each of these. If something here is unclear, ask Claude to explain it back to you in its own words — the prose either holds up or it doesn't.
