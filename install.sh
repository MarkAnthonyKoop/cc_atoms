#!/usr/bin/env bash
# install.sh — place ATOM.md + sentinel block at install root; optionally refresh INDEX.md.
#
# Idempotent. Re-run freely. Every overwrite is backed up first to
# /mnt/d/downloads/cc_atoms/<UTC-timestamp>/ mirroring the original absolute path.
#
# Usage:
#   ./install.sh [--root <path>] [--extra-path <path>]... [--force] [--discover]
#
# Flags:
#   --root <path>        Install root (default: ~, where user-level CLAUDE.md lives)
#   --extra-path <path>  Extra directories for discovery (repeatable; only meaningful with --discover)
#   --force              Overwrite <root>/ATOM.md even if it already exists and differs
#   --discover           Refresh <root>/INDEX.md via claude -p. Default is OFF — discovery is
#                        slow and AI-billed, and a stale INDEX.md is more useful than no INDEX.md.
#                        If INDEX.md already exists, the prompt asks claude to EDIT it (preserve
#                        accurate rows, add new projects, remove dead ones), not rewrite it.
#                        If discovery fails or times out, the existing INDEX.md is left untouched.

set -euo pipefail

CC_ATOMS_HOME="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
INSTALL_ROOT="$HOME"
EXTRA_PATHS=()
FORCE=0
DISCOVER=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --root)        INSTALL_ROOT="$2"; shift 2 ;;
        --extra-path)  EXTRA_PATHS+=("$2"); shift 2 ;;
        --force)       FORCE=1; shift ;;
        --discover)    DISCOVER=1; shift ;;
        -h|--help)     sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "Unknown arg: $1" >&2; exit 1 ;;
    esac
done

SRC_ATOM="$CC_ATOMS_HOME/ATOM.md"
DST_ATOM="$INSTALL_ROOT/ATOM.md"
DST_CLAUDE="$INSTALL_ROOT/CLAUDE.md"
DST_INDEX="$INSTALL_ROOT/INDEX.md"

PLACED_ATOM=0
PATCHED_CLAUDE=0
DISCOVERED_INDEX=0

# ── Backup helper ────────────────────────────────────────────────────────────
# All backups for this install run share one timestamp under /mnt/d/downloads/cc_atoms/.
# Originals are mirrored under <ts>/ preserving their absolute path (leading slash stripped).
BACKUP_ROOT_BASE="/mnt/d/downloads/cc_atoms"
BACKUP_TS="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_ROOT="$BACKUP_ROOT_BASE/$BACKUP_TS"
BACKUP_DONE=0

backup_file() {
    # Copy $1 (an existing file) into the timestamped backup dir mirroring its absolute path.
    # No-op if the file doesn't exist.
    local src="$1"
    [[ -f "$src" ]] || return 0
    if ! mkdir -p "$BACKUP_ROOT_BASE" 2>/dev/null; then
        echo "  warn  cannot create backup root $BACKUP_ROOT_BASE — skipping backup of $src" >&2
        return 0
    fi
    local dst="$BACKUP_ROOT${src}"
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    BACKUP_DONE=1
    echo "  back  $src → $dst"
}

# ── 1. Copy ATOM.md ──────────────────────────────────────────────────────────
if [[ -f "$DST_ATOM" ]]; then
    if cmp -s "$SRC_ATOM" "$DST_ATOM"; then
        echo "  ok    $DST_ATOM (unchanged)"
    elif [[ $FORCE -eq 1 ]]; then
        backup_file "$DST_ATOM"
        cp "$SRC_ATOM" "$DST_ATOM"
        echo "  copy  $DST_ATOM (forced overwrite, prior contents backed up)"
        PLACED_ATOM=1
    else
        echo "  skip  $DST_ATOM (differs — use --force to overwrite)"
    fi
else
    cp "$SRC_ATOM" "$DST_ATOM"
    echo "  copy  $DST_ATOM"
    PLACED_ATOM=1
fi

# ── 2. Patch CLAUDE.md with sentinel block ────────────────────────────────────
SENTINEL_BEGIN="<!-- atom:begin -->"
SENTINEL_END="<!-- atom:end -->"
BLOCK="${SENTINEL_BEGIN}
### Autonomous recursion — the atom convention

When work is autonomous (recursion, parallel fan-out, multi-directory), use the **atom** convention. The contract is \`${INSTALL_ROOT}/ATOM.md\` — read it for per-directory structure, recursion rule, spawning, status discipline, and the optional auditor. Discovered tools available to atom workers are indexed at \`${INSTALL_ROOT}/INDEX.md\`.
${SENTINEL_END}"

if [[ ! -f "$DST_CLAUDE" ]]; then
    echo "  warn  $DST_CLAUDE not found — appending sentinel block skipped"
else
    # Check whether a patch is actually needed before backing up
    NEEDS_PATCH=1
    if grep -qF "$SENTINEL_BEGIN" "$DST_CLAUDE"; then
        EXISTING_BLOCK="$(python3 -c "
import re,sys
text=open('$DST_CLAUDE').read()
m=re.search(r'<!-- atom:begin -->.*?<!-- atom:end -->', text, re.DOTALL)
print(m.group(0) if m else '')")"
        [[ "$EXISTING_BLOCK" == "$BLOCK" ]] && NEEDS_PATCH=0
    fi

    if [[ $NEEDS_PATCH -eq 0 ]]; then
        echo "  ok    $DST_CLAUDE (sentinel block already current)"
    else
        backup_file "$DST_CLAUDE"
        if grep -qF "$SENTINEL_BEGIN" "$DST_CLAUDE"; then
            python3 - "$DST_CLAUDE" "$BLOCK" <<'PYEOF'
import sys, re
path, block = sys.argv[1], sys.argv[2]
text = open(path).read()
pattern = r'<!-- atom:begin -->.*?<!-- atom:end -->'
new_text = re.sub(pattern, block, text, flags=re.DOTALL)
open(path, 'w').write(new_text)
PYEOF
            echo "  patch $DST_CLAUDE (replaced existing sentinel block)"
        elif grep -qF '### Autonomous recursion — the `atom` convention' "$DST_CLAUDE"; then
            python3 - "$DST_CLAUDE" "$BLOCK" <<'PYEOF'
import sys, re
path, block = sys.argv[1], sys.argv[2]
text = open(path).read()
pattern = r"### Autonomous recursion — the `atom` convention.*?(?=\n---|\Z)"
new_text = re.sub(pattern, block, text, flags=re.DOTALL)
open(path, 'w').write(new_text)
PYEOF
            echo "  patch $DST_CLAUDE (replaced old atom section with sentinel block)"
        else
            printf '\n%s\n' "$BLOCK" >> "$DST_CLAUDE"
            echo "  patch $DST_CLAUDE (appended sentinel block)"
        fi
        PATCHED_CLAUDE=1
    fi
fi

# ── 3. Discovery: refresh INDEX.md (only when --discover is given) ──────────
if [[ $DISCOVER -eq 1 ]]; then
    if ! command -v claude &>/dev/null; then
        echo "  warn  --discover requested but claude CLI not found — skipping"
    else
        DISCOVERY_DIRS="$INSTALL_ROOT"
        for ep in "${EXTRA_PATHS[@]}"; do DISCOVERY_DIRS="$DISCOVERY_DIRS $ep"; done

        if [[ -f "$DST_INDEX" ]]; then
            DISCOVERY_PROMPT="Edit (do not rewrite) ${DST_INDEX}. The file is the index of project directories under: ${DISCOVERY_DIRS}. Project markers: .git, pyproject.toml, package.json, README.md. Walk those directories, then update ${DST_INDEX} in place: (1) keep rows whose project still exists and whose description is still accurate, (2) add a one-line row for any new project, (3) remove rows whose project no longer exists. Preserve the file's existing structure, headings, and any human-authored prose. Write the file directly — do not print it."
            ACTION_DESC="edit"
        else
            DISCOVERY_PROMPT="Scan the directories: ${DISCOVERY_DIRS}. Find project directories (markers: .git, pyproject.toml, package.json, README.md). Write ${DST_INDEX} as a markdown table with columns Project and Description. One row per project, one-line description. Model it after the style of ~/claude/INDEX.md. Write the file directly — do not print it."
            ACTION_DESC="create"
        fi

        # Back up the existing INDEX.md before letting claude touch it.
        backup_file "$DST_INDEX"

        echo "  disc  Running claude -p (${ACTION_DESC}, may take up to 300s)..."
        if timeout 300 env -u ANTHROPIC_API_KEY claude --dangerously-skip-permissions --model sonnet -p "$DISCOVERY_PROMPT" >/tmp/atom_discovery.log 2>&1; then
            echo "  disc  Discovery complete — see $DST_INDEX"
            DISCOVERED_INDEX=1
        else
            # Non-destructive: leave existing INDEX.md alone (we backed it up but the file on disk is unchanged).
            echo "  warn  claude -p failed or timed out; existing $DST_INDEX left untouched. Log: /tmp/atom_discovery.log"
        fi
    fi
else
    if [[ -f "$DST_INDEX" ]]; then
        echo "  skip  $DST_INDEX (discovery off by default; pass --discover to refresh)"
    else
        echo "  warn  $DST_INDEX does not exist (discovery off by default; pass --discover to create it)"
    fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo
echo "=== install.sh summary ==="
echo "  ATOM.md  : $DST_ATOM$( [[ $PLACED_ATOM -eq 1 ]] && echo ' (placed/updated)' || echo ' (already current)')"
echo "  CLAUDE.md: $DST_CLAUDE$( [[ $PATCHED_CLAUDE -eq 1 ]] && echo ' (sentinel block patched)' || echo ' (unchanged or missing)')"
if [[ $DISCOVER -eq 1 ]]; then
    echo "  INDEX.md : $DST_INDEX$( [[ $DISCOVERED_INDEX -eq 1 ]] && echo ' (refreshed)' || echo ' (unchanged — discovery failed)')"
else
    echo "  INDEX.md : $DST_INDEX (not touched — re-run with --discover to refresh)"
fi
echo "  Install root: $INSTALL_ROOT"
[[ $BACKUP_DONE -eq 1 ]] && echo "  Backups   : $BACKUP_ROOT/"
echo "  To use atom mode: cd to any directory, write USER_PROMPT.md, open claude, say 'operate in atom mode per ~/ATOM.md'."
