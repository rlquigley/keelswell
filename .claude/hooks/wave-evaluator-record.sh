#!/usr/bin/env bash
# The evaluator's report is written down by this hook and by nothing else (R3
# of docs/reviews/harness-engineering-review-v1.md). Registered three times,
# all for the keelswell-wave-evaluator subagent: SubagentStop, where its last
# message is the report; and PreToolUse and PostToolUse on SubagentHandback,
# the tool it reports through in auto mode. The rules live in the wave skill's
# own script, not here; this only finds the script and runs it.
#
# Fails toward no record. A missing script or python3 exits 1, which Claude
# Code shows the user as a hook error and otherwise ignores: nothing is
# written, `evaluate_wave.py verdict` then exits 3, and the wave cannot enter
# review without a recorded PASS. Never exit 2 from here: on SubagentStop that
# hands the subagent this script's stderr as its next instruction.
REL=".claude/skills/bmad-dev-wave/scripts/evaluate_wave.py"
HERE="${BASH_SOURCE[0]%/*}"
SCRIPT="$HERE/../../$REL"
if [ ! -f "$SCRIPT" ]; then
  # A checkout that carries this wrapper but not the skills: the main
  # checkout's copy, which is the one install.sh keeps current.
  COMMON="$(git -C "${CLAUDE_PROJECT_DIR:-$HERE}" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"
  SCRIPT="${COMMON%/.git}/$REL"
fi
if [ ! -f "$SCRIPT" ]; then
  echo "wave-evaluator-record: $REL is missing, so the evaluator's report was not recorded. From the Keelswell fork, ./install.sh --validate-only --skip-mcp-check --target-project <this project> names what is missing." >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "wave-evaluator-record: python3 is not on PATH, so the evaluator's report was not recorded." >&2
  exit 1
fi
exec python3 "$SCRIPT" record
