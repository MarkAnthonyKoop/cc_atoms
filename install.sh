#!/usr/bin/env bash
# install.sh — place ATOM.md + sentinel block at install root; discover tools into INDEX.md.
#
# Idempotent. Re-run freely; existing files are only touched if they differ.
#
# Usage:
#   ./install.sh [--root <path>] [--extra-path <path>]... [--force]
#
# Flags:
#   --root <path>       Install root (default: ~, i.e. where user-level CLAUDE.md lives)
#   --extra-path <path> Extra directories for discovery (repeatable)
#   --force             Overwrite <root>/ATOM.md even if it already exists and differs

set -euo pipefail

CC_ATOMS_HOME="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
INSTALL_ROOT="$HOME"
EXTRA_PATHS=()
FORCE=0

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --root)      INSTALL_ROOT="$2"; shift 2 ;;
        --extra-path) EXTRA_PATHS+=("$2"); shift 2 ;;
        --force)     FORCE=1; shift ;;
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

# ── 1. Copy ATOM.md ──────────────────────────────────────────────────────────
if [[ -f "$DST_ATOM" ]]; then
    if cmp -s "$SRC_ATOM" "$DST_ATOM"; then
        echo "  ok    $DST_ATOM (unchanged)"
    elif [[ $FORCE -eq 1 ]]; then
        cp "$SRC_ATOM" "$DST_ATOM"
        echo "  copy  $DST_ATOM (forced overwrite)"
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
    if grep -qF "$SENTINEL_BEGIN" "$DST_CLAUDE"; then
        # Sentinels exist — replace between them
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
        # Old heading without sentinels — replace the whole section up to the next ---
        python3 - "$DST_CLAUDE" "$BLOCK" <<'PYEOF'
import sys, re
path, block = sys.argv[1], sys.argv[2]
text = open(path).read()
# Replace from the heading to the next horizontal rule (---)
pattern = r"### Autonomous recursion — the `atom` convention.*?(?=\n---|\Z)"
new_text = re.sub(pattern, block, text, flags=re.DOTALL)
open(path, 'w').write(new_text)
PYEOF
        echo "  patch $DST_CLAUDE (replaced old atom section with sentinel block)"
    else
        # Append at end
        printf '\n%s\n' "$BLOCK" >> "$DST_CLAUDE"
        echo "  patch $DST_CLAUDE (appended sentinel block)"
    fi
    PATCHED_CLAUDE=1
fi

# ── 3. Discovery: populate INDEX.md ──────────────────────────────────────────
DISCOVERY_DIRS="$INSTALL_ROOT"
for ep in "${EXTRA_PATHS[@]}"; do DISCOVERY_DIRS="$DISCOVERY_DIRS $ep"; done

DISCOVERY_PROMPT="Scan the directories: ${DISCOVERY_DIRS}. Find project directories (markers: .git, pyproject.toml, package.json, README.md). Write ${DST_INDEX} as a markdown table with columns Project and Description. One row per project, one-line description. Model it after the style of ~/claude/INDEX.md. Write the file directly — do not print it."

if command -v claude &>/dev/null; then
    echo "  disc  Running claude -p for discovery (may take up to 60s)..."
    if timeout 60 env -u ANTHROPIC_API_KEY claude --dangerously-skip-permissions --model opus -p "$DISCOVERY_PROMPT" >/tmp/atom_discovery.log 2>&1; then
        echo "  disc  Discovery complete — see $DST_INDEX"
        DISCOVERED_INDEX=1
    else
        echo "  warn  claude -p returned non-zero or timed out; writing stub INDEX.md"
        printf '# INDEX.md\n\n# Run: claude -p "discover and populate INDEX.md per %s/ATOM.md"\n' "$INSTALL_ROOT" > "$DST_INDEX"
    fi
else
    echo "  warn  claude CLI not found; writing stub INDEX.md"
    printf '# INDEX.md\n\n# Run: claude -p "discover and populate INDEX.md per %s/ATOM.md"\n' "$INSTALL_ROOT" > "$DST_INDEX"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo
echo "=== install.sh summary ==="
echo "  ATOM.md  : $DST_ATOM$( [[ $PLACED_ATOM -eq 1 ]] && echo ' (placed/updated)' || echo ' (already current)')"
echo "  CLAUDE.md: $DST_CLAUDE$( [[ $PATCHED_CLAUDE -eq 1 ]] && echo ' (sentinel block patched)' || echo ' (unchanged or missing)')"
echo "  INDEX.md : $DST_INDEX$( [[ $DISCOVERED_INDEX -eq 1 ]] && echo ' (discovered)' || echo ' (stub written — run discovery manually)')"
echo "  Install root: $INSTALL_ROOT"
echo "  To use atom mode: cd to any directory, write USER_PROMPT.md, open claude, say 'operate in atom mode per ~/ATOM.md'."
