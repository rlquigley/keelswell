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
  - <worktree>/docs/wave-<id>/wave-diff.patch     # evaluator evidence, step 7
  - <worktree>/docs/wave-<id>/verify-output.txt   # evaluator evidence, step 7
  - <worktree>/docs/wave-<id>/evaluation-<n>.md   # one per evaluator pass
  - <worktree>/docs/wave-<id>/review-party.md   # required, every wave (register row 51)
  - <worktree>/.bmad-changed.txt            # reviewer-selection input, step 10
  - <worktree>/docs/stories/                # JIT story files
  - pull request against main via gh pr create
version: 1.6.0
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
    this wave's stories. On any hit, write the questions to
    .bmad/wave-<id>/step-4.5.pending and HALT for user input; when the
    answers are recorded, delete that marker and write step-4.5.done. A
    session that ends with the marker present has its wave blocked by the
    SessionEnd hook (see The Hooks). Never dispatch parallel subagents past
    an unfired gate.
5.  ATDD scaffolding: failing test stubs per the test design. On completion
    set the status to ready-for-dev.
6.  Implementation dispatch: set the status to in-progress before dispatching.
    Serial for spine waves; parallel (one coding
    subagent per story, capped by core/config.yaml
    parallelism.max_parallel_subagents) for parallel waves. Every subagent
    receives the Project Conventions Block verbatim (below).
7.  Test expansion, then evaluation: close coverage gaps, then dispatch the
    fresh-context evaluator (see The Evaluator). You do not review this wave
    yourself and neither does any persona in this context.
8.  Checkpoint preview: show the exact commits about to land; accept
    "approved", "edit: <instruction>", or "abort". A failing story may be
    demoted out of the wave (waves.md is updated and a follow-up wave queued).
9.  Verify: run tests/verify-fast.sh in the worktree; on FAIL offer
    edit / demote / abort.
10. Party-mode adversarial review -- load-bearing waves only (skipped by
    --no-party): set the status to in-review, ask scripts/select_reviewers.py
    which reviewers this wave's own changes require (see The Reviewer
    Selection) and dispatch exactly those; block on
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

## The Evaluator

Step 7's review is not yours. It belongs to a subagent defined at
`.claude/agents/keelswell-wave-evaluator.md`, dispatched with a context that
never saw this wave get built, whose tool list is `Read`, `Glob`, `Grep` --
no `Write`, no `Edit`, no `Bash`, no `Task`. Phase 3 of
docs/harness-conversion-plan.md.

Both halves matter and neither works alone. Fresh context, because an agent
asked to review what it just produced praises it. No writing tools, because an
agent that can fix a finding is the agent that decides which findings are
worth having. The evaluator is structurally unable to edit: that is a tool
list the harness enforces, not an instruction it is asked to honour.

The definition is fork-owned and deliberately not a BMAD persona.
`bmad-agent-qa` (Aviendha) is untouched and still holds her seat; she is no
longer the one who grades this wave. `.claude/agents/` is invisible to the
installer's agent registry, so nothing here can collide with an upstream
module the way a `module.yaml` declaration would.

Ask the script before dispatching. It decides three things you do not:

    python3 {skill-root}/scripts/evaluate_wave.py dispatch \
        --project-root {project-root} --wave <id>

  0  proceed; the JSON carries `pass_number`, `third_pass_rule`, the
     evidence paths, and `record_to`
  2  structural: no wave map, or the wave is not in it
  3  refuse: the definition is missing, declares no tools, or declares a tool
     that can write, run or delegate

Exit 3 is not a warning. Do not dispatch an evaluator whose tool list this
check refused, and do not repair it by adding a rule telling it not to use the
tool. Remove the tool.

Write the evidence bundle to `docs/wave-<id>/` before dispatching -- the diff
as `wave-diff.patch`, step 9's output as `verify-output.txt`, alongside the
test design already there. `dispatch` names anything missing. The evaluator has
no `Bash` and cannot produce this for itself, which is the trade: it reviews
execution evidence rather than running the suite again. It can still `Read`,
`Glob` and `Grep` the whole worktree, so the bundle is its starting point and
not the limit of what it may look at.

Then dispatch one subagent against that definition, hand it the evidence paths
and the pass number, and pipe what it returns straight back:

    python3 {skill-root}/scripts/evaluate_wave.py record \
        --project-root {project-root} --wave <id> < <its output>

  0  PASS -- continue at step 8
  1  NEEDS_WORK -- halt (below)
  3  the output carried no readable VERDICT line; re-dispatch
  4  UPSTREAM_CAUSE -- the third-pass rule fired (below)

The verdict is whatever the evaluator's own `VERDICT:` line says, parsed by
the script. Do not summarize its output and route on your summary, and do not
record a verdict it did not write.

### NEEDS_WORK halts; it does not get fixed here

On exit 1 the wave halts at step 7 with its status left at `in-progress`. It
is not blocked: `NEEDS_WORK` is an ordinary outcome, and making it sticky would
teach the founder to clear records by reflex, which is what keeps `blocked`
worth something everywhere else.

Do not fix the findings in this session. The context that built the wave is the
context least able to judge whether a fix answered the finding, and fixing in
place is how a finding quietly becomes a rationalization. The findings are the
*next* session's opening prompt, produced from the record rather than from
anyone's memory of it:

    python3 {skill-root}/scripts/evaluate_wave.py opening-prompt \
        --project-root {project-root} --wave <id>

/bmad-resume-wave runs that and opens with what it prints. It works when this
session no longer exists, which is the case it is for.

### The third-pass rule

`dispatch` sets `third_pass_rule` from the number of `evaluation-*.md` records
on disk, not from anyone's count of how many times this has come around. On
pass three or later, tell the evaluator the rule is armed: if it still has
non-trivial findings it returns `UPSTREAM_CAUSE` and names the weak spec, the
contradiction, or the ambiguous rule behind them, instead of producing a
fourth round of findings.

Taken from BMAD: non-trivial findings on a third pass "usually mean something
is wrong upstream of this change: a weak spec, a contradiction, or ambiguity in
the rules. Fix that instead of running another pass."

Exit 4 means stop working the code. Fix the artifact the record names -- the
story file, waves.md, the architecture doc, the Project Conventions Block --
and re-enter the wave against a corrected spec. A fourth pass over the same
spec is the loop this rule exists to break.

### The evaluator and party mode are different things

Step 7's evaluator is one generalist, every wave, PASS or NEEDS_WORK on this
wave's own work. Step 10's party mode is several domain specialists,
load-bearing waves only, hunting security, cost and platform findings. Neither
replaces the other, and `docs/wave-<id>/review-party.md` is still required at
step 11 for every wave. The evaluation records sit beside it.

## The Hooks

Phase 4 of docs/harness-conversion-plan.md. Every rule above was a script's
exit code that this skill was asked to obey; two hooks now make the tool
calls that would cross a rule fail on their own. The rules live in
`scripts/wave_gate.py`, the wrappers in `.claude/hooks/wave-gate.sh`
(PreToolUse on Write, Edit, MultiEdit, NotebookEdit and Bash) and
`.claude/hooks/wave-session-end.sh` (SessionEnd), and install.sh registers
both in a target project's `.claude/settings.json` and asserts all of it under
`--validate-only`.

What the PreToolUse hook denies, reading only what is on disk:

- **closure**: any write under `_bmad-output/epic-closure/epic-<N>/` while
  `check_review_records.py --epic N` exits non-zero. /bmad-close-epic's gate,
  run by the hook at the moment the artifact would be written.
- **verdict**: any write to `docs/wave-<id>/evaluation-<n>.md` that is not
  `evaluate_wave.py record`. A verdict typed by the agent it grades is not one.
- **review**: `wave_status.py set --status in-review` for a wave whose latest
  evaluation is not PASS. There is no way into the review stage except through
  step 7's evaluator.
- **in-place**: after this session records NEEDS_WORK for a wave, any write
  into that wave's worktree by this session. The findings open the next
  session; the hook remembers which session recorded the verdict.

A denial arrives as the hook's stderr, naming the rule and the remedy. Do not
route around it through another tool: Bash is matched on the command's text,
so a redirect through a variable or a here-doc is not seen, and taking that
route is the exact obedience failure the hook exists to remove.

What the SessionEnd hook does: a wave whose `.bmad/wave-<id>/step-4.5.pending`
marker is present when the session ends is set to `blocked`, reason recorded,
because the question it was waiting on has no answer on disk and the next
dispatch would walk past it. Ending by `resume` does not count. Sticky as
always: a human records the answer, deletes the marker, and clears the block.

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

## The Reviewer Selection

Step 10 used to dispatch security, cost and platform on every load-bearing
wave. Phase 6.3 of docs/harness-conversion-plan.md removed that exemption:
those three are now ordinary rows in a table, and which reviewers a wave gets
is decided from what the wave actually changed. Waves 4A and 4B landed
ffbapp's model work with no ML reviewer under the old rule, and 4B is where
the defect 5D eventually caught originated.

The answer is not yours to derive. Ask the script:

    git -C {worktree} diff --name-only main...HEAD > {worktree}/.bmad-changed.txt
    python3 {skill-root}/scripts/select_reviewers.py select \
        --wave <id> \
        --changed-files {worktree}/.bmad-changed.txt \
        --spec {worktree}/docs/wave-<id>/test-design.md \
        --json

Dispatch the `skill` of every entry in `selected`, and nothing else. Do not
add a reviewer the script did not return, and do not drop one it did. Exit 2
means the trigger table is malformed; quote its stderr and halt rather than
choosing reviewers by hand, which is the behaviour 6.3 replaced.

**Necessity, not a budget.** If eight rows fire, dispatch eight. If one fires,
dispatch one. There is no cap in the script, none in the table, and none here,
because a cap means choosing which real gaps to skip looking for. What keeps
this affordable is trigger precision: every pattern in
`scripts/reviewer-triggers.yaml` is answerable yes or no from the file list
and the spec, with no judgment. A trigger needing interpretation is a wrong
trigger, not a wrong rule -- fix the table, do not overrule its output.

**Zero reviewers is a possible answer.** Measured over ffbapp's eighteen
waves, four return none: their diffs are grammar ASTs, test fixtures and
contract registries that touch no reviewer's domain. Exit code 0, empty
`selected`. The wave still writes its review record naming that case; see The
Review Record. Whether a zero-selection load-bearing wave should also get a
domain-less adversarial pass is an open founder ruling, not this script's
call.

**Party mode is unaffected.** Trigger selection is for this step only. When
bmad-party-mode is initiated, every agent is in the room; that rule is
preserved by not setting `default_party`, and nothing here changes it.

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
- the selector returned no reviewers: say so, and record the changed-file
  count and the spec files it read, so the empty answer can be re-derived.
  Four of ffbapp's eighteen waves return none;
- the review did not run (the wave is not load-bearing, or --no-party): a
  short record naming which case applies and why. Under --no-party the record
  from the prior session must already exist on disk; if it does not, refuse
  the flag rather than skipping the step.

Front matter, required in all three cases:

```yaml
---
title: "Wave <id> party-mode adversarial review"
wave: <id>
created: <YYYY-MM-DD>
model: <the model the reviewers were dispatched at>
effort: <low|medium|high|xhigh|max>
---
```

`model` is the reviewers' model, not the orchestrator's. Reviewers are
dispatched as subagents and can run at a different model than the
session that dispatched them; the reviewers' is the one that produced
the findings. Write the model string itself (`claude-opus-5`), never
the policy that chose it: three of ffbapp's ten records said "the
session model" and none named a model, which left every finding in
them unattributable to any generation. Where reviewers ran at
different models, list each. `status` and `stories` are optional and
two records already carry them.

This block is the reason the record can be read back by a later pass.
Agent value is re-earned after each model release rather than assumed
(`docs/agent-inventory.md`), and an unstamped finding cannot take part
in that: it proves something about a model nobody can name.

Contents:
- the reviewers dispatched and their disjoint domains, and the trigger that
  selected each one (paste `select_reviewers.py --json`'s `selected` block, or
  its `role`/`trigger`/`source` fields). A record that names reviewers without
  naming what put them there cannot be checked against the table later;
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
- Evaluator definition missing or declaring a writing tool at step 7: refuse
  to dispatch (exit 3); quote the script's stderr. Remove the tool from the
  definition. Do not dispatch it anyway with an instruction not to use the
  tool, and do not fall back to reviewing the wave in this context -- that
  fallback is the thing this step replaced.
- Evaluator returns NEEDS_WORK: halt at step 7, status stays `in-progress`.
  Not a block, and not fixed here; the findings open the next session.
- Evaluator returns UPSTREAM_CAUSE: halt. Fix the artifact it names, not the
  code, and do not run a fourth pass over the same spec.
- Evaluator output with no readable VERDICT line: re-dispatch. Do not decide
  what it meant on its behalf.
- Never trust a subagent completion summary: read the diff, run the claimed
  tests, before step 8's preview.
- review-party.md absent at step 11: refuse to open the pull request until it
  is written. This is the one step-11 refusal, because a wave that lands
  without its review record cannot be reviewed again later.
- Tool call denied by the wave-gate hook: quote its stderr and do what it
  names. Do not retry the same write through a different tool.

## Version history
- 1.6.0 (2026-09-14, Phase 6.3 of docs/harness-conversion-plan.md): step 10
  stops hardcoding "security, cost, and platform" and asks
  `scripts/select_reviewers.py` which reviewers the wave's own changed files
  and spec require, against `scripts/reviewer-triggers.yaml`. The fixed three
  become ordinary rows: a wave touching no infrastructure now returns no
  platform reviewer. The rule is necessity, not a budget -- no cap anywhere,
  because a cap means choosing which real gaps to skip looking for; what keeps
  it affordable is that every trigger is answerable yes or no from the file
  list without judgment. Six of the eighteen rows quote their trigger verbatim
  from docs/agent-inventory.md, which is all the inventory wrote; eleven were
  derived for this table and say so, and three are inert and say why. Nothing
  about party mode changes: an initiated party is still the whole collective.
  No stage and no step was added -- step 10 already existed and its reviewer
  list changed hands, the same move Phase 3 made with step 7's review.
- 1.5.0 (2026-09-12, Phase 6.1 of docs/harness-conversion-plan.md): the
  review record gains a required front-matter block carrying `model` and
  `effort`, the reviewers' rather than the orchestrator's. The record had
  no specified header at all; two of ffbapp's ten wrote one anyway and
  this codifies what they converged on. Three said reviewers ran at "the
  session model" and none named a model, so no finding in any of the ten
  can be attributed to a model generation, which is what
  docs/agent-inventory.md could not recompute against.
- 1.4.0 (2026-09-11, Phase 4 of docs/harness-conversion-plan.md): the rules
  become hooks. `scripts/wave_gate.py` is the one PreToolUse hook (closure,
  verdict, review, in-place) and the SessionEnd hook that blocks a wave left
  paused at step 4.5, which now writes a `step-4.5.pending` marker while it
  waits. No stage added; every denial is a rule this skill already stated,
  now failing as a tool call instead of depending on the agent to refuse.
- 1.3.0 (2026-09-11, Phase 3 of docs/harness-conversion-plan.md): step 7's
  review moves out of this context. It is dispatched to a subagent defined at
  `.claude/agents/keelswell-wave-evaluator.md` whose tool list carries no
  Write, Edit, Bash or Task, so it is structurally unable to fix what it
  finds, and whose context never saw the build. `scripts/evaluate_wave.py`
  refuses to dispatch a definition that declares a writing tool, counts the
  passes, and parses the evaluator's own VERDICT line into an exit code.
  NEEDS_WORK halts the wave at `in-progress` rather than being fixed in place;
  the findings become the next session's opening prompt, generated from the
  record. On a third pass the evaluator names the upstream cause instead of
  listing a fourth round. No step and no stage was added -- step 7 already
  existed and its review changed hands. `bmad-agent-qa` is untouched: the
  evaluator lives where no BMAD module declares agents, so it cannot collide
  with her or with any upstream persona.
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
