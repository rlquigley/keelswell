---
name: bmad-dev-wave
description: >
  Execute one wave from the wave map. Creates a worktree, designs wave-scoped
  tests, scaffolds stories, dispatches one or more coding subagents, runs
  verify and party-mode gates, lands commits, opens a pull request, and halts
  before merge.
when-to-use: |
  Use at the start of each wave's implementation session, after
  /bmad-create-wave has written the wave map. Do not use for ad-hoc story
  implementation -- this skill is wave-shaped and refuses to run without a
  wave map; small waveless work belongs to Quick Dev.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash
  - Task
output-locations:
  - ../<project>-wave-<id>/                 # sibling worktree, branch wave-<id>-<suffix>
  - .bmad/wave-<id>/checkpoint.json         # plus step-N.done markers (main repo)
  - .bmad/wave-<id>/wave.md                 # lifecycle status record (main repo)
  - <worktree>/docs/wave-<id>/test-design.md
  - <worktree>/docs/wave-<id>/review-party.md   # required, every wave (register row 51)
  - <worktree>/docs/stories/                # JIT story files
  - pull request against main via gh pr create
version: 1.2.0
---

# bmad-dev-wave
Execute one wave from the wave map. Stage 2 of the four-stage wave cycle: it
consumes the map /bmad-create-wave produced, produces a worktree with
committed story implementations and an opened pull request, and halts before
merge. It never merges.

## Inputs
### Required
- Wave ID (positional). Example: 1A-auth-foundation, or just 1A.
- _bmad-output/planning-artifacts/waves.md (the wave map).
### Optional
- --resume: skip steps with a completed checkpoint; pick up at the first
  incomplete step. /bmad-resume-wave is the canonical entry point; this flag
  is the underlying mechanism.
- --no-party: skip the party-mode step even for a load-bearing wave. Only when
  party-mode ran in a prior session and its artifacts are still valid.
- --dry-run: walk every step and print what would happen without writing
  files, dispatching subagents, or opening a PR.
### Inferred
- Wave pattern (serial or parallel), load-bearing and spine-only flags: from
  the wave map row.
- Repo name and main checkout path: from the current working directory.
- GitHub remote: from `git remote get-url origin`.

## The Twelve-Step Workflow
Each step writes a checkpoint marker under .bmad/wave-<id>/; any step can be
re-entered by /bmad-resume-wave.
1.  Preflight: the status gate below decides whether this wave may be
    dispatched at all and at which step to re-enter; then clean tree, wave
    exists in waves.md, gh authenticated, and no earlier epic is
    closure-pending (see The Closure Gate).
2.  Worktree creation: sibling ../<project>-wave-<id> on branch
    wave-<id>-<suffix>.
3.  Wave-scoped test design (one QA-persona subagent) ->
    docs/wave-<id>/test-design.md.
4.  Just-in-time story creation for stories not yet on disk.
4.5 Open-questions gate: scan auto-memory for unresolved questions tagged to
    this wave's stories; HALT for user input on any hit. Never dispatch
    parallel subagents past an unfired gate.
5.  ATDD scaffolding: failing test stubs per the test design. On completion
    set the status to ready-for-dev.
6.  Implementation dispatch: set the status to in-progress before dispatching.
    Serial for spine waves; parallel (one coding
    subagent per story, capped by core/config.yaml
    parallelism.max_parallel_subagents) for parallel waves. Every subagent
    receives the Project Conventions Block verbatim (below).
7.  Test expansion and review: close coverage gaps found in review.
8.  Checkpoint preview: show the exact commits about to land; accept
    "approved", "edit: <instruction>", or "abort". A failing story may be
    demoted out of the wave (waves.md is updated and a follow-up wave queued).
9.  Verify: run tests/verify-fast.sh in the worktree; on FAIL offer
    edit / demote / abort.
10. Party-mode adversarial review -- load-bearing waves only (skipped by
    --no-party): set the status to in-review, then dispatch security, cost,
    and platform reviewers; block on
    HIGH or CRITICAL findings. Write docs/wave-<id>/review-party.md before
    step 11, always, including when the review found nothing and when it did
    not run (see The Review Record).
11. Commits and pull request. Parallel waves: exactly one foundation commit
    (every cross-cutting file every subagent edits -- pyproject.toml or the
    lockfile, errors.py, the CLI main, ci-fast.yml, the wave's
    test-design.md) then one commit per story touching only story-exclusive
    files. Serial waves: strict per-story commits. Either way the wave's
    review-party.md lands in this step; a wave whose pull request opens
    without it is the defect register row 51 names. Push branch; gh pr create.
12. Halt before merge. Print the PR URL. Merging is the human's decision;
    cleanup afterward is /bmad-merge-wave's job.

## Project Conventions Block
A single verbatim block defined once here and rendered identically into every
coding-subagent dispatch (subagents inherit neither auto-memory nor
conversation context). It carries: communication rules, git rules
(commit-message format, branch naming), language and tool conventions, the
test framework and verify harness location, CI constraints, standing policy
decisions, and coding discipline (touch only the story's files; no drive-by
improvements). Populate the block for your project before the first dispatch;
an empty block is a preflight warning.

## The Status Gate

This skill owns the wave lifecycle status and the script that reads and writes
it. Phase 2 of docs/harness-conversion-plan.md; the vocabulary is defined once,
in that script, and bmad-create-wave, bmad-merge-wave, bmad-resume-wave and
bmad-status-wave all read it from there rather than each restating the names.

Step 1 asks the script where this wave stands. The answer is not yours to
derive:

    python3 {skill-root}/scripts/wave_status.py route \
        --project-root {project-root} --wave <id>

Exit 0 proceeds, and its JSON names the `reentry_step` to start at -- use it
instead of assuming step 1, and instead of inferring the step from the
conversation. Exit 1, 2 or 3 is the refusal; quote its stderr, which names the
wave and the remedy. There is no flag and no override.

  0  proceed; the JSON carries status, stage and reentry_step
  1  the wave is blocked
  2  structural: no wave map, or the wave is not in it
  3  the record exists and its status is missing or unrecognized

The six statuses and the step each re-enters at:

| status | meaning | re-entry |
|---|---|---|
| draft | this skill has not run past step 5 | first incomplete of 1-5 |
| ready-for-dev | steps 1-5 done, nothing dispatched | step 6 |
| in-progress | implementation dispatched | first incomplete of 6-9 |
| in-review | review, commits, PR, awaiting merge | first incomplete of 10-12 |
| done | merged and swept by /bmad-merge-wave | step 10, a fresh follow-up pass |
| blocked | sticky halt | none |

No stage is added: every re-entry point above is a step this skill already
has. A status names the stage; the checkpoint markers name the step within it.

Advance the status with the same script, never by editing the record by hand:

    python3 {skill-root}/scripts/wave_status.py set \
        --project-root {project-root} --wave <id> --status <status>

Write points are steps 5, 6 and 10 above, and every refusal in Error Handling
that halts the wave, which writes `--status blocked --reason "<one line>"`.

## Blocked is sticky

A blocked wave halts every later dispatch, **including after the cause is
fixed**. Fixing the cause changes nothing the gate reads. There is no retry
flag, and `set` refuses to write over a blocked record, so this skill cannot
clear a block it created -- which is the point, since the run that blocked the
wave is the run that would argue it is safe to resume. A retry loop is not a
control mechanism.

Only a human clears it, by editing `status:` in `.bmad/wave-<id>/wave.md` to
another valid status or deleting that file. Deleting just the `status:` line
does not work: a record that exists with no readable status exits 3.

Taken from BMAD's bmad-build-auto, whose note on permanence is the part worth
copying -- a blocked record halts every later dispatch "even after the cause is
fixed. To retry, delete the story file."

## Waves with no status record

A wave whose record does not exist yet predates this field. `route` backfills
it once: it infers the stage from the same checkpoint and worktree evidence
/bmad-resume-wave's probes already used, prints an `UNMIGRATED` notice naming
the inferred status and the evidence, writes the record, and proceeds. The
inference runs once per wave; every dispatch after that routes on the record.

Read the notice before dispatching. Ambiguity resolves toward `draft`, which
re-enters at the earliest incomplete step, because re-running an idempotent
preflight costs minutes while guessing a wave forward past steps that never
ran skips its test design and its ATDD scaffolding.

A record that exists with an unreadable status is the opposite case and is
refused, not backfilled. That asymmetry is what stops deleting the status line
from working as a quiet override of blocked.

## The Closure Gate
Step 1 refuses to open a wave while an earlier epic is closure-pending
(register row 51, ruled by RQ 2026-09-10). Closure-pending means every story
of that epic has landed and no closure record exists: each of its waves'
pull requests reads `MERGED` via
`gh pr view <branch> --json number,state,mergedAt`, and
`_bmad-output/epic-closure/epic-<n>/` is absent.

Test merged, not cleaned up. A session cannot remove the worktree it runs
in, so cleanup always lags one session; gating on cleanup would leave open
the exact window Epic 4 fell through, where wave 4B merged on 2026-09-03 and
wave 5A opened the next day. /bmad-status-wave already computes this state
and, by its own charter, only surfaces it; this gate is what acts on it.

The gate does not fire for an epic still mid-flight. A wave running out of
epic order while an earlier epic has an unmerged wave is unaffected, which is
what keeps a ruled placement like wave 6A's (between 4A and 4B) legal.

Not overridable by a flag: a flag is how the gap recurs. A deliberate
deferral is a founder act, recorded as a dated amendment in waves.md naming
the epic and the reason, which this preflight reads and accepts. Refusal
names the epic, names the waves whose pull requests are merged, and points at
/bmad-close-epic.

## The Review Record
Step 10 writes `docs/wave-<id>/review-party.md`. It is required for every
wave, and it is the artifact rather than a courtesy: a finding that lives
only in a commit message cannot be cited by a later artifact, cannot be read
by /bmad-create-story, and cannot be checked at the epic's closure. That is
the same failure shape as a finding filed only under `docs/wave-<id>/` with
one more step of decay, and it is what register row 51 exists to stop.

Write it in all three cases, so a missing file is always a defect rather than
sometimes an expected absence:
- the review ran and found things: the full record below;
- the review ran and found nothing: say so, and still record the reviewers,
  their domains, and what each attacked. Wave 5B's clean result is exactly
  what got lost by leaving it in a commit message;
- the review did not run (the wave is not load-bearing, or --no-party): a
  short record naming which case applies and why. Under --no-party the record
  from the prior session must already exist on disk; if it does not, refuse
  the flag rather than skipping the step.

Contents:
- the reviewers dispatched and their disjoint domains;
- every finding, with its severity, and how it was proved -- by execution or
  by mutation, never by reading (the standing party-mode brief);
- for each finding, how it was closed and how the close was verified.
  Re-applying the original defect and watching a named test redden is the
  standard; re-reading the fix is not;
- every deferred finding with its destination wave, and any finding with no
  destination wave marked as going to the founder. Both file to waves.md as
  dated amendments as well; this record does not replace that filing.

## Error Handling
Every refusal below that halts a wave mid-flight also writes
`--status blocked --reason "<one line>"` before halting, so the next dispatch
refuses at step 1 instead of re-discovering the same failure. The two
preflight refusals are the exception: they fire before the wave opens, so
there is nothing to block.
- Wave blocked at preflight: refuse; quote the script's stderr. Not clearable
  by this skill or by any flag.
- Wave record present with an unreadable status: refuse (exit 3). Repair the
  record or delete it.
- Dirty working tree at preflight: refuse; name the dirty paths.
- Earlier epic closure-pending at preflight: refuse; name the epic and its
  merged waves, and point at /bmad-close-epic. Not overridable by a flag;
  a deliberate deferral is a dated waves.md amendment.
- --no-party with no review record on disk from the prior session: refuse
  the flag. The flag skips a step that already ran, not the artifact.
- Wave ID not in waves.md: refuse; suggest /bmad-create-wave.
- Open question surfaced by a subagent that the gate should have caught:
  halt the wave and block it; record the resolution to auto-memory, then clear
  the block by hand before re-dispatch. Step 4.5's own halt is not a block: it
  is a pause inside the plan stage waiting on an answer in the same session.
- Verify FAIL: offer edit (re-dispatch with failing-test context), demote
  (drop the story to a new wave), or abort (leave worktree for inspection).
  Abort blocks the wave.
- Never trust a subagent completion summary: read the diff, run the claimed
  tests, before step 8's preview.
- review-party.md absent at step 11: refuse to open the pull request until it
  is written. This is the one step-11 refusal, because a wave that lands
  without its review record cannot be reviewed again later.

## Version history
- 1.2.0 (2026-09-11, Phase 2 of docs/harness-conversion-plan.md): the wave
  lifecycle status moves into `.bmad/wave-<id>/wave.md` and this skill gains
  `scripts/wave_status.py`, the one place the vocabulary is defined. Step 1
  routes on the record's status rather than inferring the re-entry step from
  the conversation, and steps 5, 6 and 10 write the status forward. Blocked is
  sticky: it halts every later dispatch after its cause is fixed, and the
  script refuses to let any skill write over it, so only a human editing or
  deleting the record clears it. No stage was added -- every status re-enters
  at a step this skill already had.
- 1.1.0 (2026-09-10, founder ruling, settled-decisions register row 51):
  step 1 refuses while an earlier epic is closure-pending, and step 10 must
  write docs/wave-<id>/review-party.md for every wave. Both halves were
  earned by the same defect: waves 4A, 4B, 5A and 5B produced no review
  record, Epic 4's closure gate was skipped with nothing recording a
  decision, and a correctness defect in wave 4B code then survived four
  later waves before another epic's review found it. In both Epic 4 and
  Epic 5 the waves without a review record are the waves carrying the
  acceptance clauses nothing asserts.
