#!/usr/bin/env bash
# PreToolUse: the wave rules a tool call cannot cross (Phase 4 of
# docs/harness-conversion-plan.md). The rules live in the wave skill's own
# scripts, not here; this only finds the script and runs it.
#
# Fails closed (R1 of docs/reviews/harness-engineering-review-v1.md). Claude
# Code lets a PreToolUse call through on any exit but 2, so a missing script,
# a missing python3 and a crash all become exit 2 here, with the fix on
# stderr. A broken gate blocks every call it matches until a human repairs
# it, which is the direction a gate should fail in.
#
# Registered in exec form as ${CLAUDE_PROJECT_DIR}/.claude/hooks/wave-gate.sh,
# so a `cd` cannot turn it into a path that does not resolve. No
# --project-root: the gate finds .bmad/ from the session's cwd itself.
REL=".claude/skills/bmad-dev-wave/scripts/wave_gate.py"
HERE="${BASH_SOURCE[0]%/*}"
GATE="$HERE/../../$REL"
if [ ! -f "$GATE" ]; then
  # A checkout that carries this wrapper but not the skills: the main
  # checkout's copy, which is the one install.sh keeps current.
  COMMON="$(git -C "${CLAUDE_PROJECT_DIR:-$HERE}" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"
  GATE="${COMMON%/.git}/$REL"
fi
if [ ! -f "$GATE" ]; then
  echo "wave-gate: $REL is missing, so the wave rules cannot be checked and this call is denied. A human must restore it outside this session: from the Keelswell fork, ./install.sh --validate-only --skip-mcp-check --target-project <this project> names what is missing." >&2
  exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "wave-gate: python3 is not on PATH, so the wave rules cannot be checked and this call is denied. Put python3 on PATH and retry." >&2
  exit 2
fi
python3 "$GATE" pre-tool-use
rc=$?
case "$rc" in 0|2) exit "$rc" ;; esac
echo "wave-gate: $GATE exited $rc, so the wave rules could not be checked and this call is denied. A human must repair it outside this session: python3 $GATE --help shows the error." >&2
exit 2
