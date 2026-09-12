#!/usr/bin/env bash
# PreToolUse: the wave rules a tool call cannot cross (Phase 4 of
# docs/harness-conversion-plan.md). The rules live in the wave skill's own
# scripts, not here; this only finds the script and runs it. A missing script
# is reported on every call (exit 1 is shown to the user, never to the model)
# and caught for real by ./install.sh --validate-only.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GATE="$ROOT/.claude/skills/bmad-dev-wave/scripts/wave_gate.py"
if [ ! -f "$GATE" ]; then
  echo "wave-gate: $GATE is missing; the wave rules are not being checked. Run ./install.sh --validate-only." >&2
  exit 1
fi
exec python3 "$GATE" pre-tool-use --project-root "$ROOT"
