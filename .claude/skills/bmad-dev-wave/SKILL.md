---
name: bmad-dev-wave
description: >
  Execute one wave from the wave map. Creates a worktree, designs wave-scoped
  tests, scaffolds stories, dispatches one or more coding subagents, runs
  verify and party-mode gates, lands commits, opens a pull request, and halts
  before merge.
when_to_use: |
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
metadata:
  version: 1.25.0
  output-locations:
    - ../<project>-wave-<id>/                 # sibling worktree, branch wave-<id>-<suffix>
    - .bmad/wave-<id>/checkpoint.json         # plus step-N.done markers
    - .bmad/wave-<id>/wave.md                 # lifecycle status record
      # both: in the directory of the record path route prints, the wave
      # worktree's own .bmad/ when it has one, else the main repo's (a new
      # wave starts where the session is rooted); bmad-merge-wave adopts a
      # worktree's into the main repo before removal
    - <worktree>/docs/wave-<id>/test-design.md
    - <worktree>/docs/wave-<id>/verify-output.txt   # stamped by evaluate_wave.py verify, step 7
    - <worktree>/docs/wave-<id>/wave-diff.patch     # written by evaluate_wave.py dispatch, step 8
    - <worktree>/docs/wave-<id>/evaluation-<n>.md   # one per evaluator pass, written by its hook
    - <worktree>/docs/wave-<id>/review-party.md   # required, every wave (register row 51)
    - <worktree>/.bmad-changed.txt            # reviewer-selection input, step 10
    - <worktree>/docs/stories/                # JIT story files
    - pull request against main via gh pr create
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
Each step ends with its checkpoint marker, made by the status script and
never by hand:

    python3 {skill-root}/scripts/wave_status.py mark \
        --project-root {project-root} --wave <id> --step <N>

The marker, `step-<N>.done`, lands in the wave's state directory, the one
holding the `record` path step 1's `route` prints: `.bmad/wave-<id>/` in the
wave's worktree when it has one, else the main checkout's; a wave with
neither starts in the checkout the session is rooted in. Never both. Do not
use the Write tool or `touch` for one: a desktop session isolated to the
worktree is refused the Write tool in the main checkout and told to use the
worktree's path, and a marker put there splits the wave's state, so route
and set exit 3 until a human merges the copies. Exit 2 from `mark` names a
step this skill does not have; exit 3 is route's split or ambiguous-worktree
refusal. Any step can be re-entered by /bmad-resume-wave.
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
    this wave's stories. On any hit, put the questions in a file outside
    `.bmad/` and run `wave_status.py pend --project-root {project-root}
    --wave <id> --questions-file <file>`, which writes `step-4.5.pending`
    beside the record, then HALT for user input. When the answers are
    recorded, run `wave_status.py pend --project-root {project-root} --wave
    <id> --clear`, then `wave_status.py mark --step 4.5`. Never write or
    delete the pending marker with the Write tool, `touch` or `rm`: the
    same refusal that splits a step marker splits this one, and `pend` exits
    3 where `mark` does. A session that ends with the marker present has its
    wave blocked by the SessionEnd hook (see The Hooks). Never dispatch
    parallel subagents past an unfired gate.
5.  ATDD scaffolding: failing test stubs per the test design. On completion
    set the status to ready-for-dev.
6.  Implementation dispatch: set the status to in-progress before dispatching.
    Serial for spine waves; parallel (one coding subagent per story, at most
    4 at a time) for parallel waves. Every coding subagent is dispatched as
    `keelswell-wave-coder` (see The Routing) and
    receives the Project Conventions Block verbatim (below).
7.  Test expansion, then verify: close coverage gaps, then run
    scripts/evaluate_wave.py verify, which runs tests/verify-fast.sh in the
    worktree and stamps its output (see The Evaluator). On FAIL offer
    edit / demote / abort.
8.  Evaluation: dispatch the fresh-context evaluator (see The Evaluator). You
    do not review this wave yourself and neither does any persona in this
    context, and you do not write its verdict down: its hook does.
9.  Checkpoint preview: show the exact commits about to land; accept
    "approved", "edit: <instruction>", or "abort". A failing story may be
    demoted out of the wave (waves.md is updated and a follow-up wave queued).
    On approval set the status to in-review, for every wave, including one
    whose step 10 will not run: the review stage opens here, on step 8's PASS.
10. Party-mode adversarial review -- load-bearing waves only (skipped by
    --no-party): ask scripts/select_reviewers.py
    which reviewers this wave's own changes require (see The Reviewer
    Selection) and dispatch exactly those, each as `keelswell-wave-reviewer`
    (see The Routing); block on
    HIGH or CRITICAL findings. Write docs/wave-<id>/review-party.md before
    step 11, always, including when the review found nothing and when it did
    not run (see The Review Record). A HIGH or CRITICAL finding fixed here
    sends the wave back through steps 7 and 8 before step 11: a PASS is
    bound to the diff it graded, and the gate denies in-review on the old
    one. Set the status to in-progress before the fix; step 9 sets in-review
    again on the new PASS.
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

## The Routing
Steps 6 and 10 dispatch by name, and the name is the routing. Claude Code
binds a subagent's model and effort in one place, the frontmatter of its
definition, so each role this skill dispatches has one:

| Step | Role | `subagent_type` | Definition |
|---|---|---|---|
| 6 | one story's implementation | `keelswell-wave-coder` | `.claude/agents/keelswell-wave-coder.md` |
| 8 | the wave's evaluation | `keelswell-wave-evaluator` | `.claude/agents/keelswell-wave-evaluator.md` |
| 10 | one reviewer, persona or fallback | `keelswell-wave-reviewer` | `.claude/agents/keelswell-wave-reviewer.md` |

R4 of docs/reviews/harness-engineering-review-v1.md. Reviewers followed the
session's model in 7 of ffbapp's 18 waves, because nothing said what they
should run at; a settings key that claimed to say it never existed.

- Dispatch with the Agent tool and the `subagent_type` above. Do not pass the
  Agent tool's `model` parameter on these dispatches: it outranks the
  definition, and a subagent that follows the session is the defect.
- Do not use a general-purpose subagent for one of these roles. If a
  definition is missing, halt and restore it from the fork
  (`.claude/agents/*.md`); `install.sh --validate-only` names what is wrong.
- The definitions are role files, not personas. A reviewer's persona is still
  the `skill` the selector returned; the dispatch prompt names it and the
  reviewer loads it.
- Each definition's `model:` and `effort:` are a row of the fork's
  `core/config.yaml`, checked by `install.sh --validate-only` and changed
  only together with it.

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
  3  the record exists and cannot be read, names a key twice, or has a
     missing or unrecognized status; or the wave's state cannot be placed:
     two checkouts are on its branch, or the main checkout's copy of its
     directory disagrees with the worktree's

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

Write points are steps 5, 6 and 9 above, step 10 when a fix sends the wave
back to in-progress, and every refusal in Error Handling that halts the wave,
which writes `--status blocked --reason "<one line>"`.

`set` makes only the moves in the script's transition table: draft ->
ready-for-dev -> in-progress -> in-review -> done, in-review back to
in-progress for a step-10 fix, a same-status set (history only), and blocked
from anything. Anything else exits 4 and writes nothing; in particular a wave
reaches done only from in-review, so not past step 8's evaluator. A record
that cannot be read exits 3 and is never written over.

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

Step 8's review is not yours. It belongs to a subagent defined at
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
`bmad-agent-qa` (Quinn) is untouched and still holds its seat; Quinn is no
longer the one who grades this wave. `.claude/agents/` is invisible to the
installer's agent registry, so nothing here can collide with an upstream
module the way a `module.yaml` declaration would.

Three things here used to be yours and are now a script's: the evidence the
evaluator is shown, the count of passes, and the record of what it said. R3 of
docs/reviews/harness-engineering-review-v1.md.

**Step 7, verify.** Run the suite through the script, not by hand:

    python3 {skill-root}/scripts/evaluate_wave.py verify \
        --project-root {worktree} --wave <id>

It runs `tests/verify-fast.sh` from the worktree root and writes
`docs/wave-<id>/verify-output.txt`, whose first line is a stamp: the command,
its exit code, the HEAD it ran at, the time. Beside the wave's `wave.md` it
writes `.bmad/wave-<id>/verify-stamp`: the sha256 of that output and of the
wave's diff as the run left it. The gate guards the stamp as it guards
`wave.md`. There is no other verify command
and no config key for one; a project whose suite lives elsewhere gives
`tests/verify-fast.sh` one line that calls it.

  0  the script exited 0
  1  the script failed; the output is stamped all the same. Offer edit,
     demote or abort
  3  refuse: no `tests/verify-fast.sh`, not a git checkout, or two checkouts
     on the wave's branch

**Step 8, dispatch.** Ask the script before dispatching:

    python3 {skill-root}/scripts/evaluate_wave.py dispatch \
        --project-root {worktree} --wave <id>

  0  proceed; the JSON carries `pass_number`, `rule_pass`, `third_pass_rule`,
     the evidence paths, and `record_to`
  2  structural: no wave map, or the wave is not in it
  3  refuse: the definition is missing, declares a tool that can write, run
     or delegate, or lacks `effort: high`; or `verify-output.txt` is missing,
     carries no stamp, was stamped at a HEAD that is not the worktree's, or
     is not the bytes the verify stamp hashed; or the wave's diff has changed
     since verify ran; or the latest evaluation is NEEDS_WORK or
     UPSTREAM_CAUSE on the same diff, with no upstream fix on record

Exit 3 is not a warning. Do not dispatch an evaluator whose tool list this
check refused, and do not repair it by adding a rule telling it not to use the
tool. Remove the tool. A stale or missing stamp, or a change since verify,
means step 7 has to run again; do not write `verify-output.txt` yourself,
because one that is not verify's bytes is refused. A verdict is not re-rolled:
the same diff after NEEDS_WORK is refused from any session, so the next pass
grades a change.

On exit 0 the script has written `docs/wave-<id>/wave-diff.patch` itself:
everything the wave changed since its merge-base with main, committed or not,
untracked files included, and the harness's own files (`.bmad/`, the verify
output, the patch, the evaluation records) left out. Its sha256 goes in the
marker; the hook refuses to record a report if the patch or the verify output
changed after dispatch, and writes the hash into the record's header. The
gate's review rule recomputes it at step 9: `set --status in-review` is
denied unless the latest PASS names the wave's diff as it is then, so a
commit, an edit or a new file after PASS goes back through steps 7 and 8.
Step 11's commits do not change it: the diff is taken against the working
tree. You do not write the diff. The evaluator has no
`Bash` and cannot produce this evidence for itself, which is the trade: it
reviews execution evidence rather than running the suite again. It can still
`Read`, `Glob` and `Grep` the whole worktree, so the bundle is its starting
point and not the limit of what it may look at.

Then dispatch one `keelswell-wave-evaluator` subagent, hand it the evidence
paths and `rule_pass` as its pass number, and wait for it to return. That is
all you do with its report.
A hook (`.claude/hooks/wave-evaluator-record.sh`) writes the subagent's own
text to `record_to`, matched to this dispatch by a marker the script left at
`.bmad/wave-<id>/evaluation-pending`. A report it cannot record -- no
`VERDICT:` line, two of them, or a `PASS` that lists a finding above `LOW` --
is sent back to the evaluator, twice at most. `evaluate_wave.py record` is that
hook's entry point and the wave gate denies it to you.

When the evaluator has returned, read what the hook wrote:

    python3 {skill-root}/scripts/evaluate_wave.py verdict \
        --project-root {worktree} --wave <id>

  0  PASS -- continue at step 9
  1  NEEDS_WORK -- halt (below)
  3  nothing is recorded for this dispatch; stderr says why. Run `dispatch`
     and dispatch the evaluator again
  4  UPSTREAM_CAUSE -- the third-pass rule fired (below)

The verdict is whatever the evaluator's own `VERDICT:` line says, parsed by
the script from the record the hook wrote. Do not summarize its output and
route on your summary.

### NEEDS_WORK halts; it does not get fixed here

On exit 1 the wave halts at step 8 with its status left at `in-progress`. It
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

`dispatch` sets `third_pass_rule` from the `evaluation-*.md` records on disk,
not from anyone's count of how many times this has come around. On pass three
or later, tell the evaluator the rule is armed: if it still has
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

When the artifact is fixed, put the fix on record. That is what restarts the
count, so the corrected spec gets its own three passes instead of being armed
at once:

    python3 {skill-root}/scripts/wave_status.py set \
        --project-root {project-root} --wave <id> --status in-progress \
        --reason "upstream fix: <the artifact you fixed>"

`dispatch` then reports `rule_pass` 1 while `pass_number`, which names the
record file, keeps counting. The count restarts only for a fix recorded after
the `UPSTREAM_CAUSE` it answers, naming a file the report's `Where:` or `Fix
this instead:` line named, whose bytes have changed since: the hook writes
each such file's sha256 into the record's header. A line written ahead of
the verdict, or naming a file that is missing, unchanged or not in the
report, does nothing. Name the artifact by its path from the project root,
as the report does. A PASS also restarts the count, so step 10's re-check
is pass 1 of its own.

### A fix at step 10 comes back through here

A HIGH or CRITICAL party finding fixed at step 10 changes code the evaluator
passed. Set the status to in-progress, then run step 7 again, then step 8, then
step 9, which sets in-review again only on a PASS: `dispatch` refuses the old
verify stamp
once the wave's diff has moved, the gate denies in-review on the old PASS,
and when `review-party.md` is dated on or after the
latest evaluation it adds the review record to the evidence, so the evaluator
checks the fix against the finding.

### The evaluator and party mode are different things

Step 8's evaluator is one generalist, every wave, PASS or NEEDS_WORK on this
wave's own work. Step 10's party mode is several domain specialists,
load-bearing waves only, hunting security, cost and platform findings. Neither
replaces the other, and `docs/wave-<id>/review-party.md` is still required at
step 11 for every wave. The evaluation records sit beside it.

## The Hooks

Phase 4 of docs/harness-conversion-plan.md. Every rule above was a script's
exit code that this skill was asked to obey; hooks now make the tool calls
that would cross a rule fail on their own, and write the one record a session
must not write for itself. The rules live in `scripts/wave_gate.py` and
`scripts/evaluate_wave.py`, the wrappers in `.claude/hooks/wave-gate.sh`
(PreToolUse on Write, Edit, MultiEdit, NotebookEdit, Bash and Monitor),
`.claude/hooks/wave-session-end.sh` (SessionEnd) and
`.claude/hooks/wave-evaluator-record.sh` (the evaluator's report, below), and
install.sh registers all three in a target project's `.claude/settings.json`
and asserts all of it under `--validate-only`.

What the PreToolUse hook denies, reading only what is on disk:

- **closure**: any write under `_bmad-output/epic-closure/epic-<N>/` while
  `check_review_records.py --epic N` exits non-zero. /bmad-close-epic's gate,
  run by the hook at the moment the artifact would be written.
- **verdict**: any write to `docs/wave-<id>/evaluation-<n>.md`. The evaluator
  hook is the one writer. A verdict typed by the agent it grades is not one,
  and neither is one copied, moved, linked or unpacked into
  `docs/wave-<id>/` (or into `docs/` as a `wave-<id>` directory) from
  elsewhere; a copy into `docs/` is read by looking inside its source. A
  record main does not hold yet stays where it is: a removal that reaches one
  (rm, rmdir, a move away, a find that deletes), and `git clean` or a stash
  with `-u`/`-a` that would sweep one, is denied, because it resets the pass
  count and hides the findings. Once the wave has merged its records are on
  main, and the same cleanup goes through.
- **record**: any Bash or Monitor call of `evaluate_wave.py record`, the
  hook's entry point, in any shape the gate can or cannot read, and any run of
  the hook's wrapper `.claude/hooks/wave-evaluator-record.sh`. The hook hands
  it the subagent's own report; a session calling it would hand it anything.
- **lifecycle**: any write, move or delete of `.bmad/wave-<id>/wave.md`, or of
  the evaluator's markers beside it (`evaluation-session`,
  `evaluation-pending`), or of the directory holding them, that is not the
  script that owns it, and any cp, rsync or install into that directory of a
  source that could carry one: one of those names, a glob that could match
  it, a variable, a directory, or anything under a recursive flag. Blocked is
  sticky only if the session it blocks cannot edit the record, and the
  in-place rule holds only if its session cannot edit `evaluation-session`.
- **review**: `wave_status.py set --status in-review` or `--status done` for
  a wave whose latest evaluation is not PASS. There is no way into the review
  stage except through step 8's evaluator.
- **in-place**: after this session's evaluator returns NEEDS_WORK for a wave,
  any write into that wave's worktree by this session, and any
  `evaluate_wave.py dispatch` or `verify` run for that wave: re-running the
  evaluator on its own fix until it says PASS is the judgement this rule
  keeps from it. The findings open the next session; the evaluator hook notes
  which session's evaluator it recorded.
  One exemption, to the file tools only: `_bmad-output/session-wrap/` in the
  worktree, so /bmad-wrap can still write its triage report.
- **merge**: `gh pr merge` in any shape the gate reads (`bash -c`, `eval`,
  `env`, a substitution), `gh api` with a method other than GET to a
  `/merge` or `/merges` path or with a merge mutation, and a `git push` that
  lands on main or master (`main`, `HEAD:main`, `:main`, `--all`,
  `--mirror`, or a bare push or `HEAD` from a checkout on main). Text that
  names a merge with gh or push where the parse cannot read it is denied
  too. Push the wave's branch, open the pull request and halt: a human
  merges, outside Claude Code. Local `git merge` and `git pull --ff-only`
  are not merges of a pull request and stay open.

Paths match without regard to case, as the filesystem and the record reader
do. The hook finds the wave's state, its worktree and its evaluation records
the way `wave_status.py` does, whichever checkout the session is rooted in.
The worktree is the one on the waves.md branch suffix, never a lookalike;
with two on it, the review rule refuses and the in-place rule guards both.

A denial arrives as the hook's stderr, naming the rule and the remedy. Do not
route around it. Bash is parsed the way the shell reads it, not searched as
text: quotes, variables set in the same command, `cd`, `git -C`, `eval`,
`bash -c` and substitutions are all followed. What the parse cannot read, it
refuses: a `wave_status.py set` reached through `python3 -c`, a here-document,
a variable holding the command, or a pipe into a shell is denied even when the
call would have been allowed. Call `wave_status.py` directly with literal
values; that is the only shape the gate reads.

The hook fails closed. If its script is missing, python3 is missing, or the
script errors or runs past its deadline, every call it matches is denied with
the fix on stderr. That is not something to work around from inside the
session: stop and tell the human, who repairs it outside the session.

What the evaluator hook does: it runs on three events, all from the
`keelswell-wave-evaluator` subagent, because the report travels differently by
permission mode. Outside auto mode the report is the subagent's last message
and arrives on SubagentStop. In auto mode the subagent hands it over with the
SubagentHandback tool, and SubagentStop then carries no message: PreToolUse on
that tool sends back a report that cannot be recorded, before you see it, and
PostToolUse records the one that landed. Either way one pass is recorded once.
With no `dispatch` marker for this session, or with two, it writes nothing.
If its script or python3 is missing it writes nothing and says so to the
human; `verdict` then exits 3 and the review rule keeps the wave out of
review.

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

Dispatch one `keelswell-wave-reviewer` subagent for every entry in `selected`,
naming the entry's `skill` in its prompt as the persona to load, and nothing
else (see The Routing). Do not
add a reviewer the script did not return, and do not drop one it did. Exit 2
means the trigger table is malformed; quote its stderr and halt rather than
choosing reviewers by hand, which is the behaviour 6.3 replaced.

**Each reviewer works alone.** Reviewers run at the same time and every one
of them mutates code, so before dispatching, give each its own place to do
it, and put all of the following in its prompt. `{scratch}` is the
session's scratchpad directory, or a temporary directory outside the
repository when there is none; `<name>` is the reviewer's `skill`, or
`fallback-<n>` for a fallback reviewer.

- **Its own copy of the worktree**, made by you before dispatch:
  `rsync -a --exclude .git --exclude .venv --exclude node_modules
  --exclude __pycache__ {worktree}/ {scratch}/<name>/tree/`. The reviewer
  runs lanes and applies mutations there and nowhere else. The wave's
  worktree is read-only to it.
- **Its own scratch directory**, `{scratch}/<name>/`, for its scripts and
  output. Name no other reviewer's directory or skill in the prompt. Wave
  5E's follow-up shared one directory, and one reviewer overwrote another's
  mutation script.
- **Its own verify database**, when the project's verify lanes take a
  database name from the environment (read `tests/verify-*.sh`): a value
  ending in `<name>`. Two lanes on one database corrupt each other's run.
  A failure on a cluster-wide object, such as a database role, while
  another lane runs is a known collision: rerun once before reporting it.
- **Which tools work there.** The copy has no `.git`: prove each restore
  with a checksum snapshot of every file before and after, not `git status`.
  Apply mutations with a script that writes and restores bytes. Do not use
  `git worktree add --detach` for reviewer copies: a session isolated in a
  worktree by the desktop app is refused git and Edit in any other
  checkout, and its subagents with it. When a call is refused, quote the
  refusal and do not retry it through another tool.
- **Commands that run with no one at the keyboard.** An unattended run
  denies any Bash call its permission rules do not allow, and a proof
  denied is a finding left unproven. Write each probe or mutation script
  into `{scratch}/<name>/` with Write, which creates the directory, and run
  it as `python3 {scratch}/<name>/<script>.py`; read with Read, Grep, Glob
  or a single `git -C <path> ...`. One command per Bash call: no `cd` and
  no variable set in front of the command, no chain with `;`, `&&` or `|`,
  and no `mkdir`, `cp`, `shasum` or `find` (the script copies, hashes and
  walks). In R5b's eval trials 37 of 117 reviewer Bash calls were denied,
  and all but one broke this rule.
- **No commits past the secret scan.** A reviewer that wants a baseline
  takes the checksum snapshot. It never runs `git init` and commits in the
  copy, and never uses `--no-verify` or sets `core.hooksPath`: two wave 6B
  reviewers did both to get past gitleaks.

When every reviewer has returned, check that the wave's worktree is as it
was: `git -C {worktree} status --porcelain` and `git -C {worktree} rev-parse
HEAD` read the same as before dispatch. Say so in the review record. A
difference is a finding against the review, not the wave: name the
reviewer and restore from the evidence before going on.

**Necessity, not a budget.** If eight rows fire, dispatch eight. If one fires,
dispatch one. There is no cap in the script, none in the table, and none here,
because a cap means choosing which real gaps to skip looking for. What keeps
this affordable is trigger precision: every pattern in
`scripts/reviewer-triggers.yaml` is answerable yes or no from the file list
and the spec, with no judgment. A trigger needing interpretation is a wrong
trigger, not a wrong rule -- fix the table, do not overrule its output.

**Zero reviewers is a possible answer, and it is not zero review.** When no
row fires, the JSON carries a `fallback` instead of an empty answer: a method
rather than a seat, dispatched as `keelswell-wave-reviewer` subagents with no
persona, under the brief the table
carries. Dispatch it exactly as written and record the review with
`record_as`, never as though a trigger fired.

The method is ffbapp's own. Waves 3A and 3D both ran real reviews under no
persona's name -- "mutation-based correctness review", "specimen
expressiveness review", "real-sheet execution review" -- and 3D's record says
it ran "under the wave 3A pattern". That review found two HIGH findings on 3A
that no seat in the table would have looked for. Waves 3C and 4A got no review
at all and both are load-bearing. This block is why that cannot happen again.

It is not the step-8 evaluator twice. That one reads: fresh context,
Read/Glob/Grep, no Bash. This one executes, which is the standing party brief:
a finding is proved by execution or by mutation, never by reading.

**The generalist does not stand in for a specialist.** `bmm-dev` fires on any
implementation diff -- 17 of ffbapp's 18 waves -- because it is the second
opinion on code rather than an answer about a domain. A selection holding only
generalists is treated as an empty one: the wave gets `bmm-dev` *and* the
fallback. Without that rule the `bmm-dev` row alone retires the fallback on the
two waves that most need it, and "somebody read it" is not the same answer as
"somebody attacked it".

**The table is the whole roster.** All 38 agents in `config/agent-names.yaml`
have a row, asserted by test, so a missing trigger is visible in one file
rather than needing a count. Three rows are inert and each says why:
custom-bizops and core-bmad-master because the inventory ruled so, and
custom-web-designer because it builds at step 6.

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
- the selector returned no reviewers and the fallback ran: say so, name the
  method, and record the changed-file count and the spec files it read so the
  empty answer can be re-derived. Mark it with the fallback's `record_as`, not
  as a fired trigger: a record that cannot tell the two apart cannot be
  checked against the table later;
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
model: <the `model:` line of .claude/agents/keelswell-wave-reviewer.md>
effort: <its `effort:` line>
---
```

`model` is the reviewers' model, not the orchestrator's. Reviewers are
dispatched as subagents and run at the model and effort their
definition states, whatever the session that dispatched them is on; the
reviewers' is the one that produced the findings. Copy both lines from
`.claude/agents/keelswell-wave-reviewer.md`, the definition that ran, as
they stand there (`claude-opus-5-5`, `high`). Write the model string
itself, never
the policy that chose it: three of ffbapp's ten records said "the
session model" and none named a model, which left every finding in
them unattributable to any generation. Where reviewers ran at
different models, list each, and say why: a reviewer dispatched another
way, or a session with `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` set, did not
run at the definition's. `status` and `stories` are optional and
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
- Wave record present but unreadable, with a key named twice, or with an
  unreadable status: refuse (exit 3). Repair the record or delete it.
- `set` exits 4: the transition table does not allow that move. Quote the
  stderr, which names the moves that are allowed; do not reach the status by
  another route.
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
- Verify output missing, unstamped or stale at step 8: `dispatch` exits 3.
  Run step 7's `verify` again; do not write the file by hand.
- Evaluator definition missing, declaring a writing tool or lacking
  `effort: high` at step 8: refuse to dispatch (exit 3); quote the script's
  stderr. Remove the tool from the definition, or restore the line. Do not dispatch it anyway with an instruction not to use the
  tool, and do not fall back to reviewing the wave in this context -- that
  fallback is the thing this step replaced.
- Evaluator returns NEEDS_WORK: halt at step 8, status stays `in-progress`.
  Not a block, and not fixed here; the findings open the next session.
- Evaluator returns UPSTREAM_CAUSE: halt. Fix the artifact it names, not the
  code, and do not run a fourth pass over the same spec.
- Evaluator report the hook cannot record (no VERDICT line, two of them, a
  PASS listing a finding above LOW): the hook sends it back, twice at most.
  If `verdict` still exits 3, run `dispatch` and dispatch the evaluator
  again. Do not decide what it meant on its behalf, and do not record it.
- Never trust a subagent completion summary: read the diff, run the claimed
  tests, before step 9's preview.
- review-party.md absent at step 11: refuse to open the pull request until it
  is written. This is the one step-11 refusal, because a wave that lands
  without its review record cannot be reviewed again later.
- Tool call denied by the wave-gate hook: quote its stderr and do what it
  names. Do not retry the same write through a different tool.

## Version history
- 1.25.0 (2026-10-25, harness review v2 V2-14): the gate has a merge rule.
  `gh pr merge`, a `gh api` merge and a push to main or master are denied in
  every shape the parse reads, and text naming a merge that it cannot read
  is denied too. The settings template's text rule could not see `bash -c`
  or `gh api`. No step changed; every step already halts before merge.
- 1.24.0 (2026-10-25, follow-up to 1.23.0): step 4.5's `step-4.5.pending`
  is written by `wave_status.py pend --questions-file <file>` and removed by
  `pend --clear`, beside the record `route` printed, exit 3 where route
  would. The agent's own Write tool put it in the worktree in a desktop
  session isolated there, splitting the wave's state. No step's order
  changed.
- 1.23.0 (2026-10-25, follow-up to harness review v2 PR 4): every step's
  marker is made by `wave_status.py mark --step <N>`, which puts it beside
  the record `route` printed and exits 3 where route would. Step 4.5 runs it
  too. A desktop session isolated to the worktree is refused the Write tool
  in the main checkout, and the refusal's advice put the marker in the
  worktree, splitting the wave's state. No step's order changed.
- 1.22.0 (2026-10-25, harness review v2 PR 3: V2-02 in full, V2-05, V2-06,
  V2-22, V2-23): an evaluation is bound to the sha256 of the wave diff it
  graded, committed, uncommitted and untracked work alike. dispatch refuses
  the same diff after NEEDS_WORK or UPSTREAM_CAUSE, a verify output that is
  not verify's bytes, and a tree that changed since verify; the hook refuses
  a report on evidence changed after dispatch; the gate denies in-review on
  a PASS whose diff is not the wave's now. verify writes
  `.bmad/wave-<id>/verify-stamp`, guarded like `wave.md`. A PASS restarts
  the third-pass count, and an upstream fix restarts it only when a file the
  report named has changed. No step's order changed.
- 1.21.0 (2026-10-25, harness review v2 PR 4: V2-07, V2-08, V2-31): one
  answer to where a wave's state lives, `wave_status.locate`, read by every
  script. A session rooted in the worktree and one rooted in main read and
  write the same record, markers beside it; route and set exit 3 when two
  copies disagree or two worktrees match. The worktree is matched on the
  waves.md suffix, whole, with an optional harness hash. SessionEnd blocks a
  pending question in any checkout. route no longer infers done while the
  wave's worktree or an unmerged branch of it exists. Step 1's marker
  location is the record's directory; no step changed otherwise.
- 1.20.0 (2026-10-23, harness review v2 PR 2: V2-03, V2-04, V2-20, V2-09 a
  and b, V2-02's cheap fix): the gate's verdict rule denies a record copied,
  moved, linked or unpacked into a wave's directory, and a removal, `git
  clean` or untracked stash that reaches one on disk. Running the record
  hook's wrapper is `record`. A `--` before the verb no longer hides it. The
  evaluator's markers are guarded like `wave.md`, worktree paths compare
  casefolded, and the session held by the in-place rule may not run
  `dispatch` or `verify` for the wave. Cleanup is blocked only where it
  would take a record main does not hold yet. Gate only; no step changed.
- 1.19.0 (2026-10-23, harness review v2 PR 1: V2-01, V2-10 in part, V2-30,
  V2-34): `wave_status.py set` makes only the moves in a transition table
  and exits 4 on any other, so in-progress -> done is refused. The gate's
  review rule guards done as it guards in-review. A record that cannot be
  read or names a key twice exits 3 instead of reading as absent. A set
  holds a lock across its read and write and writes through os.replace.
  The in-review write moves from step 10 to the end of step 9, for every
  wave; a step-10 fix sets in-progress first.
- 1.18.1 (2026-10-23, harness review v2 PR 5): the settings-template test
  asserts the `${CLAUDE_PROJECT_DIR}` exec form for every hook. Test only;
  no step changed.
- 1.18.0 (2026-10-22, R5b eval trials): step 10's dispatch prompt names
  the command shapes an unattended run allows a reviewer: scripts written
  to its scratch directory and run with `python3`, one command per Bash
  call. Dispatch text only.
- 1.17.0 (2026-10-18, ffbapp's H1 rulings follow-up and wave 6B): step 10
  gives each reviewer its own rsync copy of the worktree, its own scratch
  directory and its own verify database, says which tools work there, and
  forbids a commit past the secret scan; the session checks the worktree is
  unchanged afterwards. Dispatch text only: the reviewer definition, the
  hooks and the selector are unchanged.
- 1.16.0 (2026-10-17, ffbapp wave 6B): the lifecycle rule denies a copy into
  a wave's `.bmad/wave-<id>/` directory (or `.bmad/` itself) whose source
  could carry `wave.md`. A target that is the directory names no record, so
  6B's merge session copied one in by hand. `wave_status.py adopt` is still
  the route. No step changed.
- 1.15.0 (2026-10-17, ffbapp wave 5E): the in-place rule exempts
  `_bmad-output/session-wrap/` inside the wave's worktree, to the file tools
  only. 5E's session, rooted in that worktree and refused the main checkout
  by the desktop app's isolation, had nowhere to write its wrap. Every other
  write into the worktree, and every shell write, is still denied.
- 1.14.0 (2026-10-17, ffbapp wave 6B): `wave_status.py adopt` copies a
  worktree's `.bmad/wave-<id>/` into the main checkout, overwriting nothing
  and refusing on any file that differs. bmad-merge-wave 1.3.0 runs it
  before removing the worktree. Where this skill writes its checkpoint is
  unchanged.
- 1.13.0 (2026-10-17, ffbapp wave 5E): the `custom-ml` row fires on a
  `*_features.py` module, a model's feature builder. 5E changed one and
  selected no ML reviewer. The replay covers twenty waves, adding 6B and 5E,
  the first two merged after the table was tuned. No step changed.
- 1.12.2 (2026-10-03, theme removal, follow-ups): no agent is gendered in
  this skill, the trigger table's notes or the selector's docstrings. Words
  only: no trigger pattern, selector rule, step or test assertion changed.
- 1.12.1 (2026-10-03, theme removal, PR 1): the `display:` column of
  `scripts/reviewer-triggers.yaml` and one name in step 10 carry the 38 new
  display names. No trigger pattern, selector rule or step changed.
- 1.12.0 (2026-10-02, R5 of docs/reviews/harness-engineering-review-v1.md,
  second part): the skill gains `evals/`, three balanced pairs that enter the
  wave at the step under test and grade what the session leaves on disk: the
  evaluator gate (step 8), the open-questions gate (step 4.5) and the reviewer
  dispatch (step 10). `evals/run_evals.py` runs one headless session per
  trial and reports pass^3 with cost and time; `evals/README.md` says how and
  what it does not contain. `scripts/tests/test_evals.py` checks every task's
  reference end state against its grader with no model call. Measurement
  only: no step, no hook and no gate rule changed.
- 1.11.0 (2026-10-02, R5 of docs/reviews/harness-engineering-review-v1.md):
  the reviewer-selection replay is committed. `scripts/tests/replay_fixture.py`
  builds a fixture of the eighteen waves the trigger table was tuned on from
  a local checkout of the instance,
  `scripts/tests/fixtures/replay-golden.json` records what the selector
  returns for each (role ids, the fallback, file counts), and
  `test_replay.py` compares the two by wave and role. The fixture is a
  private instance's and is not committed, so the replay skips where it is
  absent. No step changed. Three table defects the replay surfaced are fixed,
  each as its own change to the golden. (1) The selector no longer ignores
  `_bmad-output/planning-artifacts/`, where an instance keeps its PRD, epics
  and architecture spine, so `bmm-pm` and the path half of `bmm-architect`
  can fire there; the wave map and the rest of `_bmad-output/` stay
  bookkeeping. (2) `tea-murat` reaches a test-support tree one level down
  (`tests/unit/support/`). A wave whose only specialist is `tea-murat` no
  longer gets the fallback, which is the table's existing rule applied to one
  more wave. (3) `arch-cost-optimizer` matches "compute cap" and "machine
  hours". Two further cost waves stay missed and the table says why beside the
  row.
- 1.10.0 (2026-10-01, R4 of docs/reviews/harness-engineering-review-v1.md):
  steps 6 and 10 dispatch by name. Coding subagents run as
  `keelswell-wave-coder` and reviewers, persona or fallback, as
  `keelswell-wave-reviewer`; each definition under `.claude/agents/` states
  its `model:` and `effort:`, and the review record copies its two lines from
  the reviewer's. New section, The Routing; no step added. The parallel cap
  (4) is written into step 6, where it used to cite a `core/config.yaml` key
  nothing read. Frontmatter: `when-to-use` is `when_to_use`, the field Claude
  Code reads, and `version` and `output-locations` sit under `metadata:`.
- 1.9.0 (2026-10-01, R3 of docs/reviews/harness-engineering-review-v1.md):
  the evaluator's evidence and its record stop being the builder's to write.
  Steps 7 to 9 are reordered, not added to: 7 is test expansion and verify, 8
  the evaluation, 9 the checkpoint preview. Verify ran after the evaluation
  whose evidence it produces. `evaluate_wave.py verify` runs
  `tests/verify-fast.sh` and stamps the output with the command, the exit
  code and HEAD; `dispatch` writes the diff from the merge-base itself and
  exits 3 on a missing, unstamped or stale verify output, where it printed a
  notice. The record is written by a hook from the subagent's own report
  (SubagentStop, and SubagentHandback in auto mode), `evaluate_wave.py record`
  is that hook's entry point, and a new gate rule, record, denies it to Bash
  and Monitor. A report with no VERDICT line, with two, or a PASS listing a
  finding above LOW is sent back to the evaluator. New `verdict` verb reads
  the record back as the exit code `record` used to return. The evaluator
  runs at `effort: high`, asserted by `check`. The pass count restarts after
  an UPSTREAM_CAUSE whose fix is on record in the lifecycle history, and a
  step-10 fix routes back through steps 7 and 8.
- 1.8.2 (2026-10-01, found while grading R1 of
  docs/reviews/harness-engineering-review-v1.md): a newline ends a command in
  the gate's parser. 1.8.0 marked a newline with the newline inside the mark,
  shlex split the mark there, and the halves were read as words, so a guarded
  action on a second line passed after `echo` on the first, and a `mkdir`,
  `rm` or `touch` followed by a second line crashed the gate into a denial.
- 1.8.1 (2026-10-01, R2 of docs/reviews/harness-engineering-review-v1.md):
  tests only; no step changes. `scripts/tests/test_settings_template.py` pins
  the permission block the instance settings template gains beside R1's hook
  registration: five Bash and two Edit deny rules, four ask rules and the
  bypassPermissions lock. Where an instance's settings carry the block,
  `gh pr merge` is denied, a plain `git push`, `git branch -D` or
  `git worktree remove` prompts, and the Write and Edit tools cannot touch
  `.bmad/wave-<id>/wave.md` or an evaluation record even with the hook off.
- 1.8.0 (2026-09-29, R1 of docs/reviews/harness-engineering-review-v1.md):
  the hook fails closed and stops matching text. Any error in the gate, a
  missing script or python3, and a run past its deadline now deny instead of
  letting the call through; the hook is registered by
  `${CLAUDE_PROJECT_DIR}` in exec form with a timeout, and also matches
  Monitor. Bash is parsed rather than searched: the 11 in-review shapes of
  the review's E2b fixture are all denied (3 were before) and its echo is no
  longer. NotebookEdit is read by `notebook_path`, paths match without regard
  to case, and `.bmad/` is found from the session's cwd through git, so a
  worktree-rooted session is checked like a main-rooted one. New lifecycle
  rule: only `wave_status.py` writes `.bmad/wave-<id>/wave.md`.
  `wave_status.py` and `evaluate_wave.py` no longer accept `--stat` or
  `--wav` for `--status` and `--wave`.
- 1.7.1 (2026-09-14, founder instruction): `bmm-dev` gains a trigger and
  becomes a second opinion on any implementation diff, which an earlier draft
  had refused on a misreading -- Phase 3's ruling is about the same context
  grading itself and about an evaluator that can write, and a step-10 dispatch
  is neither. `bmm-dev` is marked `generalist`, and a selection holding only
  generalists still returns the fallback: it fires on 17 of 18 ffbapp waves, so
  without that rule its row alone would retire the fallback on 3A and 3D. Rows
  gain an optional `not_paths`, which narrows the candidate set before `paths`
  is tested, so its row can say "production source, but not its tests".
- 1.7.0 (2026-09-14, Phase 6.3 of docs/harness-conversion-plan.md, second
  pass): the trigger table becomes the whole 38-agent roster and gains a
  fallback. A sweep of every seat against the four ffbapp waves that selected
  nobody found three with a real trigger and no row -- tea-murat (fixtures,
  conftest, verify scripts, CI lanes), arch-data-architect (migrations, models,
  schema) and arch-integration-architect (routes, OpenAPI, protobuf) -- of
  which the data architect had been missing from ten of eighteen waves that
  changed database schema. The remaining seventeen were given triggers on
  founder instruction and all but bmm-dev fire on an artifact rather than on
  code. When no row fires at all the table's `fallback` is returned: the wave
  3A pattern, two concurrent reviewers with disjoint mutation domains and a
  held-back verification pass, which is the method ffbapp's own 3A and 3D
  reviews used under no persona's name. A fifth precision rule is recorded:
  structural BMAD vocabulary is never a trigger, because "acceptance criterion"
  and "functional requirement" appear in every test design by construction and
  fired bmm-qa and bmm-pm on nine of eighteen waves apiece before they were
  dropped.
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
  with Quinn or with any upstream persona.
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
