---
name: bmad-resume-wave
description: |
  Resume an interrupted /bmad-dev-wave session from the correct re-entry
  step. Inspects worktree, branch, commits, and checkpoint files to decide
  where the previous session stopped, then re-dispatches /bmad-dev-wave with
  --from-step set to the chosen step. Refuses to act on dirty worktrees,
  already-completed waves, or contradictory state. Re-runs the open-questions
  gate against current memory.
tools:
  - Read
  - Glob
  - Grep
  - Bash
  - SlashCommand
when-to-use:
  - User invokes /bmad-resume-wave directly with a wave ID
  - Previous /bmad-dev-wave session was interrupted (crash, timeout,
    accidental /clear, machine reboot) and the wave has uncommitted or
    partially-committed state
  - /bmad-wrap surfaces an in-progress wave at session-end and the next
    session needs to pick it up
when-not-to-use:
  - Wave has not yet been started (use /bmad-dev-wave from step 1)
  - Wave is already complete and merged (no recovery needed)
  - Wave ID does not appear in waves.md (refuse with not-found error)
outputs:
  - .bmad/wave-<id>/resume-from-step-<N>.json
version: 1.0.0
---

# bmad-resume-wave
Resume an interrupted /bmad-dev-wave session from the correct re-entry step.

## Inputs
### Required
- **wave-id**: The wave label as it appears in waves.md (e.g. "1A", "2B").
  Used to locate the wave's worktree at ../<project>-wave-<id>/ and the
  checkpoint directory at .bmad/wave-<id>/. Must match a row in waves.md
  exactly.
### Optional
- **--from-step <N>**: Override the auto-detected re-entry step. Valid range:
  1 through 12. Warn-and-confirm semantics.
- **--dry-run**: Run all five state probes and write the resume-decision
  artifact, but do not re-dispatch /bmad-dev-wave.

## Outputs
### Resume-decision artifact
Path: .bmad/wave-<id>/resume-from-step-<N>.json
### Re-dispatch side effect
On successful auto-detection (or confirmed override), the skill invokes
/bmad-dev-wave with --wave-id <id> --from-step <N> and exits.

## State-Inspection Probes
Five probes run in order: wave-map, worktree, branch, commits, checkpoint.
- Wave-map: the ID resolves to a row in waves.md; refuse otherwise.
- Worktree: exists at the sibling path? on the expected branch? clean or
  dirty? Refuse to resume a dirty worktree.
- Branch: wave-<id>-* exists locally? tip SHA captured.
- Commits: which stories have per-story commits already (foundation commit
  plus per-story pattern for parallel waves; per-story only for serial).
- Checkpoint: read .bmad/wave-<id>/checkpoint.json and the step-N.done
  markers; the highest completed marker plus the commit probe fixes the
  re-entry step.

## Open-Questions Re-Check
Always re-run, regardless of checkpoint state, in case questions were
resolved (or new ones recorded) since the original dispatch.

## --from-step Override
Warn-and-confirm semantics: print the auto-detected step and the override,
require explicit confirmation before honoring the override.

## Error Handling
- Worktree deleted: cannot resume; re-run /bmad-dev-wave fresh (the wave map
  still stands).
- PR force-pushed by another session: report divergence; ask before
  continuing.
- Wave already merged and cleaned: nothing to resume; exit 0 with a note.
- HANDOFF.md Status red: refuse to resume without an explicit override.

## See Also
- /bmad-create-wave: produces the wave map this skill reads.
- /bmad-dev-wave: the executor this skill re-dispatches.
- /bmad-status-wave: shares the state-inspection probe set; reports state
  without re-dispatching.
- /bmad-merge-wave: refuses to merge waves whose state this skill would
  refuse to resume.
- /bmad-wrap: surfaces in-progress waves at session-end and recommends this
  skill for the next session.
