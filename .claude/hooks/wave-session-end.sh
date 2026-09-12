#!/usr/bin/env bash
# SessionEnd: a wave paused at step 4.5 with its question unanswered is
# blocked when the session that was waiting on the answer ends (Phase 4 of
# docs/harness-conversion-plan.md). SessionEnd cannot block, so this only
# records; it never exits non-zero.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GATE="$ROOT/.claude/skills/bmad-dev-wave/scripts/wave_gate.py"
[ -f "$GATE" ] || { echo "wave-session-end: $GATE is missing; no wave was checked."; exit 0; }
python3 "$GATE" session-end --project-root "$ROOT" || true
exit 0
