# Changelog
All notable changes to Keelswell. Format: Keep a Changelog; versioning: semver.

## [Unreleased] - 2026-09-12
### Added
- Two tests were looking in the wrong place (2026-09-14): both located a
  fork-only file at a fixed `parents[N]`, which is right for exactly one of
  the three trees these tests ship to -- the fork's `skills/`, the fork's
  `.claude/skills/` mirror, and every instance's `.claude/skills/`. Phase 3's
  `test_shipped_definition_is_safe` built `.claude/.claude/agents/` in the
  other two and had been failing in the fork's own mirror, not just in
  instances, since it was written; the invariant it asserts was being held in
  the meantime by install.sh's own `evaluate_wave.py check`, which is why
  nothing caught it. Phase 6.3's roster-coverage test had the same shape and
  was skipping in the mirror where it could have asserted. Both now walk up
  until they find the file, assert wherever it exists, and skip only where it
  genuinely does not. All 142 pass in both fork trees; an instance runs 141
  and skips the roster test, which is the one file an instance really does not
  carry.
- ffbapp refreshed to role codes, and given 6.3 (Phase 6.2 of
  docs/harness-conversion-plan.md, 2026-09-14): the nine custom agents still
  keyed under pre-0.5.0 persona codes (`agent-damer-flinn`,
  `agent-juilin-sandar`, `agent-tam-althor`, `agent-setalle-anan`,
  `agent-hurin`, `agent-gareth-bryne`, `agent-bayle-domon`,
  `agent-jain-farstrider`, `agent-tuon`) move to role codes on the only
  instance that runs waves, across three surfaces: skill directories,
  `[agents.*]` tables, and the two help catalogs. Nothing was broken before --
  config and directories agreed -- but 6.3 is written against role codes and
  would have missed those nine. 6.3 shipped in the same commit for the same
  reason. Verified by `resolve_party.py` (38 seats, all sixteen under role
  codes), by every firing table row resolving to both a skill directory and a
  config entry, and by a live run against ffbapp's real wave 4B diff returning
  `agent-ml`. The new harness assertion caught ffbapp missing 6.3 before
  anything else did, which is it earning its place on first use. A test
  portability fix rides along: the roster-coverage test reads
  `config/agent-names.yaml`, which is fork-only, and now skips in an instance
  rather than failing there.
- `bmm-dev` becomes a second opinion on the diff (2026-09-14, founder
  instruction): bmad-dev-wave 1.7.0 -> 1.7.1. An earlier draft left him inert
  on the grounds that a builder cannot review its own build; that was a
  misreading and is corrected here. Phase 3's ruling is about the *same*
  context grading itself and about an evaluator that can write, and a step-10
  dispatch is a fresh subagent with neither property. He fires on any
  implementation source outside a test tree -- 17 of ffbapp's 18 waves -- and
  is marked `generalist` for exactly that reason: a selection holding only
  generalist rows is treated as an empty one, so such a wave gets him *and*
  the fallback. Without that rule his row alone retires the fallback on 3A and
  3D, the two waves it was built for, and "somebody read it" is not the same
  answer as "somebody attacked it". Rows gain an optional `not_paths`, applied
  before `paths` so a row can say "production source, but not its tests";
  only his row needs it. Mean dispatches per wave 3.2 -> 4.2 with the fallback
  still firing on exactly two. 41 tests for this script, 142 across the wave
  scripts.
- The trigger table becomes the whole roster, and gains a fallback (Phase 6.3
  second pass, 2026-09-14): bmad-dev-wave 1.6.0 -> 1.7.0. A sweep of all 38
  seats in `config/agent-names.yaml` against the four ffbapp waves that
  selected nobody found three with a real trigger and no row: `tea-murat`
  (fixtures, conftest, verify scripts, CI lanes), `arch-data-architect`
  (migrations, models, schema) and `arch-integration-architect` (routes,
  OpenAPI, protobuf). The data architect had been absent from ten of eighteen
  waves that changed database schema; under the old fixed three they got a
  cost reviewer instead. The remaining seventeen were given triggers rather
  than left inert, on founder instruction, and all but `bmm-dev` fire on an
  artifact rather than on code; several will never fire in a pure-code repo,
  which is correct behaviour and not a dead row. A test asserts the table and
  the roster are the same set, so a seat can no longer go missing quietly.
  **The fallback.** When no row fires, the table returns a method rather than
  a seat: the wave 3A pattern, two concurrent reviewers with disjoint mutation
  domains and a held-back third pass that writes its own exploits from the
  finding text. It is ffbapp's own, not invented here: waves 3A and 3D both
  ran real reviews under no persona's name ("mutation-based correctness
  review", "specimen expressiveness review", "real-sheet execution review"),
  3D's record says it ran "under the wave 3A pattern", and across all ten
  ffbapp review records not one reviewer heading names an agent. That review
  found the two HIGH findings on 3A -- non-finite Decimals passing every type
  check, and `decimal.InvalidOperation` escaping the degrade posture because it
  is an `ArithmeticError` -- which no seat in the table would have looked for.
  Waves 3C and 4A had no review at all and both are marked load-bearing; that
  is the hole this closes. The fallback is returned beside `selected`, never
  merged into it, so a record can always tell an empty selection from a fired
  trigger.
  **A fifth precision rule, and the measurement that forced it.** Structural
  BMAD vocabulary is never a trigger: a test design quotes its story's
  acceptance criteria and cites the PRD's functional requirements by
  construction, so "acceptance criterion" and "functional requirement" appear
  in every spec and separate nothing. Seated, they fired `bmm-qa` and `bmm-pm`
  on nine of eighteen waves apiece. The same trap catches a word the project
  has redefined -- ffbapp "prices" a touchdown and has a "presentation dial",
  neither about money nor slides. Adding all seventeen rows took mean
  dispatches per wave from 1.9 to 4.4; dropping the structural vocabulary took
  it to 3.2, with the fallback firing on exactly the two waves that need it.
  Also recorded: `arch-cost-optimizer`, one of the old fixed three, now fires
  on none of ffbapp's eighteen waves.
  35 stdlib tests. Still asserted under `--validate-only` in both roots.
- Reviewer selection is a script, not a paragraph (Phase 6.3 of
  docs/harness-conversion-plan.md): bmad-dev-wave 1.5.0 -> 1.6.0, plus
  `scripts/select_reviewers.py` and `scripts/reviewer-triggers.yaml`.
  Step 10 stopped hardcoding "security, cost, and platform" and now asks the
  script which reviewers the wave's own changed files and spec require. The
  same logic as prose in SKILL.md would sit in the layer the transfer evidence
  measures as the one that regresses across model families; a script and a
  table are dispatch, which is the layer that carries. It lives under the
  skill's own scripts/, the convention bmad-party-mode already uses, so it
  travels with the skill and survives an upstream refresh; not _bmad/scripts/,
  which the installer owns and wipes.
  **The rule is necessity, not a budget.** Eight domains genuinely in the diff
  return eight reviewers; one returns one. No cap, no maximum, no "top N",
  because a cap means choosing which real gaps to skip looking for. The fixed
  three lost their exemption in the same change: a wave touching no
  infrastructure now returns no platform reviewer.
  **Eighteen rows, and where each trigger came from.** Six quote
  docs/agent-inventory.md's own Trigger line verbatim -- which is all sixteen
  entries had; Group 2's seven end with a "Keep after an upgrade if" line and
  Group 3's with "How to find out", neither of which is a condition in a diff.
  Nine of those ten were written for this table and are marked
  `derived-2026-09-14` so the next inventory pass can tell them apart, as were
  arch-platform-engineer and arch-cost-optimizer, which are not fork-only
  agents and never had inventory entries. Three rows are inert and say why:
  custom-bizops (the inventory's own trigger says he is invoked directly, not
  by a wave), custom-web-designer (a builder dispatched at step 6, not a
  step-10 reviewer; her step-10 half is custom-design-critic), and
  core-bmad-master (the inventory calls it the only one of the sixteen for
  which no trigger is nameable).
  **Four precision rules, each added because a real ffbapp wave proved it
  necessary**, measured against all eighteen: a leading word boundary, because
  wave 4A's spec contains "train" three times and all three are inside
  "constraint"; front matter dropped, because a test design's
  `inputDocuments:` names what the wave read rather than what it changed;
  negated sentences discarded, because waves 3D, 4B, 5C and 5D each say "No
  rendered surface exists in this wave" and a substring match read that as
  proof one exists; and a two-occurrence floor, because "backtest" appears 39
  times in wave 4B and exactly once in 3D, where it is a quotation of the
  architecture spine's component list. Bookkeeping paths (`_bmad-output/`,
  `docs/wave-*/`, TODO.md, HANDOFF.md) are excluded from the file list; a
  session-wrap triage note was dispatching the security reviewer on five of
  eighteen waves on the strength of the word "session" in a directory name.
  Across the eighteen this took mean dispatches per wave from 3.6 to 1.9.
  **Asserted under `--validate-only`** in both `skills/` and
  `.claude/skills/`: the selector exists and is executable, bmad-dev-wave's
  SKILL.md calls it, and `select_reviewers.py check` validates the table --
  the same self-check shape Phase 3 gave the evaluator, so install.sh never
  learns the table's schema. 26 stdlib tests.
  **Party mode is untouched**: an initiated party is still the whole
  collective, preserved by not setting `default_party`.
  Two things this does not do. It does not decide what a load-bearing wave
  with zero selected reviewers should get instead -- four of ffbapp's eighteen
  return none, and whether those need a domain-less adversarial pass is an
  open founder ruling. And it is inert on ffbapp until Phase 6.2 runs: that
  instance still keys nine custom agents under pre-0.5.0 persona codes.
- Agent inventory (Phase 5 of docs/harness-conversion-plan.md):
  `docs/agent-inventory.md` asks one question of each of the sixteen
  fork-only agents, what specific failure it prevents, and sorts the answers
  into earns-its-place (6), consumable (7), and no-answer (3). Assessed
  against the Claude 5 family and dated, because the grouping is expected to
  go stale on each model release: prose does not survive being moved to
  another model family, so a persona that earned its place has to earn it
  again. No agent is deleted, renamed, or edited, including the three that
  could not answer; each of those gets a way to find out instead. The pass
  also found that no wave skill references any of the sixteen, which is why
  Phase 6 was added to the plan.
- Review records carry the model that produced them (Phase 6.1 of
  docs/harness-conversion-plan.md): bmad-dev-wave 1.4.0 -> 1.5.0.
  `docs/wave-<id>/review-party.md` gains a required front-matter block with
  `title`, `wave`, `created`, `model` and `effort`. `model` is the
  reviewers' model, not the orchestrator's: reviewers are dispatched as
  subagents and can run at a different model than the session that
  dispatched them, and theirs is the one that produced the findings. The
  record had no specified header at all; two of ffbapp's ten wrote one
  anyway, and this codifies the shape they converged on. Three of the ten
  said reviewers ran at "the session model" and none named a model, so no
  finding in any of them can be attributed to a model generation, which is
  what `docs/agent-inventory.md` could not recompute against. Scoped to the
  wave record deliberately: `bmad-party-mode` is upstream, so the
  planning-phase reviews it writes stay unstamped rather than opening a
  conflict surface. Asserted under `--validate-only` in both `skills/` and
  `.claude/skills/`; the spec itself takes effect at the next wave.
- Conformance check and hooks (Phase 4 of docs/harness-conversion-plan.md):
  install.sh phase 6 asserts the enforcement layer Phases 1-3 built, and two
  hooks make the rules those phases stated fail as tool calls.
  bmad-dev-wave 1.3.0 -> 1.4.0, bmad-close-epic 1.3.0 -> 1.4.0,
  bmad-resume-wave 1.2.0 -> 1.3.0.
  **The check.** After every install and under `--validate-only`, phase 6
  asserts, in both `skills/` (the source) and `.claude/skills/` (the snapshot
  an upstream refresh rewrites): the closure gate script exists and is
  executable and `bmad-close-epic/SKILL.md` calls it; `wave_status.py`
  exists and is executable and all five wave skills reference it;
  `wave_gate.py` exists and is executable; and the evaluator's tool list
  passes `evaluate_wave.py check`, which is Phase 3's own refusal reused
  rather than a second parser. Then the two hook wrappers exist, are
  executable, and are registered (in a target's `.claude/settings.json`; in
  the fork, which has none, in the template). A failure names the invariant
  and exits 7 (Table I.13: a runtime file is missing or a skill failed to
  load); nothing is repaired. `--validate-allowlist` gains the scripts and
  wrappers as must-exist files. Demonstrated by breaking four invariants
  under `--validate-only` (evaluator declares Write; close-epic loses the
  gate call; `wave_status.py` deleted from the snapshot; gate script loses
  its exec bit), each failing with exit 7 and passing after repair.
  **The hooks.** `skills/bmad-dev-wave/scripts/wave_gate.py` is the one
  PreToolUse hook the plan asked for, wrapped by `.claude/hooks/wave-gate.sh`
  on Write, Edit, MultiEdit, NotebookEdit and Bash. Four rules, each read off
  disk: *closure* (nothing is written under
  `_bmad-output/epic-closure/epic-<N>/` while `check_review_records.py --epic
  N` exits non-zero); *verdict* (`docs/wave-<id>/evaluation-<n>.md` is written
  by `evaluate_wave.py record` and nothing else); *review* (`wave_status.py
  set --status in-review` is denied unless the wave's latest evaluation is
  PASS); *in-place* (the session that recorded NEEDS_WORK cannot write into
  that wave's worktree afterwards; the hook notes the session id when it sees
  `record`). The SessionEnd half, `.claude/hooks/wave-session-end.sh`, blocks
  any wave whose `.bmad/wave-<id>/step-4.5.pending` marker is present when a
  session ends other than by `resume`; step 4.5 now writes that marker while
  it waits and removes it when the answer is recorded. Bash is matched on the
  command's text, a substring test and not a parse: a redirect through a
  variable, a prior `cd`, or a here-doc is not seen, and that is the named
  gap. 28 stdlib unittest cases in `scripts/tests/test_wave_gate.py`.
  **Prediction, to be checked at the next refresh.** Would catch: the
  installer ceasing to copy a custom skill's subdirectories (scripts/ gone
  from the snapshot); the installer rewriting files through a content writer
  that drops the exec bit; BMAD adopting `.claude/agents/` as an IDE-owned
  target and wiping or regenerating the evaluator (the same class as the
  2026-07-19 `.agents/` incident); upstream shipping a same-id
  `bmad-close-epic` or `bmad-dev-wave` whose precedence over the fork's copy
  flips, so the snapshot's SKILL.md no longer names the gate script; a
  template or copy path change that leaves the hook wrappers unregistered or
  non-executable. Would miss: prose drift inside a wave skill that keeps the
  reference string but stops obeying the exit code; the installer moving
  `_bmad-output/planning-artifacts/waves.md` or the `.bmad/wave-<id>/`
  convention, which leaves every script present, wired and exiting 2 on
  every run; Claude Code changing what a subagent's `tools:` list or a
  PreToolUse exit 2 means, which the check reads but cannot verify the
  harness honours; and any Bash route to a guarded file that does not name
  it. Also found: the fork's own `.claude/skills/` snapshot was two phases
  behind `skills/` (Phases 2 and 3 mirrored source only), so the fork's own
  sessions were loading pre-Phase-2 wave skills. Mirrored by hand, the act
  Phase 1 performed; the check would have caught it. The phase-5 copy loop
  now prunes `__pycache__` (carried in from Phase 1).
- A wave evaluator that cannot edit: `.claude/agents/keelswell-wave-evaluator.md`
  and `skills/bmad-dev-wave/scripts/evaluate_wave.py` (Phase 3 of
  docs/harness-conversion-plan.md). bmad-dev-wave 1.2.0 -> 1.3.0,
  bmad-resume-wave 1.1.0 -> 1.2.0.
  Step 7's review used to happen in the context that did the work, through the
  bmad-agent-qa persona. It now goes to a Claude Code subagent whose declared
  tools are `Read`, `Glob`, `Grep` -- no Write, no Edit, no Bash, no Task --
  dispatched with a context that never saw the build. Both halves are load
  bearing: fresh context because an agent reviewing its own output praises it
  (`[[generator-evaluator-split]]`), and no writing tools because an agent that
  can fix a finding decides which findings are worth having. The shape is
  `[[anthropic-cwc-long-running-agents]]`'s evaluator subagent.
  **The guarantee is checked, not asserted.** `evaluate_wave.py check` reads the
  definition's own tool list and exits 3 on any tool that can write, run or
  delegate; `dispatch` runs that check first and refuses to dispatch a
  definition that fails it. An absent `tools:` key is refused rather than
  treated as empty (a subagent with no list inherits the parent's tools), `*`
  is refused, and an unrecognized tool is refused rather than allowed -- a tool
  the check has never heard of is not evidence that it cannot edit. RQ ruled no
  Bash (2026-09-11): `bash -c 'cat > f'` is an edit, and the wave's step 9
  already ran the suite, so the evaluator reads that output as execution
  evidence instead of producing its own.
  The verdict is the evaluator's own `VERDICT:` line, parsed by `record` into
  an exit code (0 PASS, 1 NEEDS_WORK, 4 UPSTREAM_CAUSE, 3 unparseable), so
  bmad-dev-wave routes on what the evaluator said rather than on its own
  summary of what the evaluator said. Output with no readable verdict is not
  summarized on its behalf.
  **NEEDS_WORK is not fixed in place.** It halts the wave at step 7 with the
  status left at `in-progress` -- not blocked, because an ordinary outcome made
  sticky would teach the founder to clear records by reflex and cheapen
  `blocked` everywhere else. The findings become the *next* session's opening
  prompt, generated by `opening-prompt` from the record on disk rather than
  recalled by a session that may no longer exist; bmad-resume-wave runs it and
  opens with what it prints, verbatim.
  BMAD's stopping rule comes with it. `dispatch` sets `third_pass_rule` from
  the count of `evaluation-*.md` records on disk, not from anyone's memory of
  how many rounds this has been. On pass three the evaluator returns
  `UPSTREAM_CAUSE` and names the weak spec, contradiction or ambiguous rule
  behind the findings instead of producing a fourth round of them.
  **Fork-owned and collision-free.** The definition lives under
  `.claude/agents/`, which no BMAD module declares and the installer never
  reads. It is not a BMAD persona, gets no `module.yaml` row, no `[agents.*]`
  table and no `config/agent-names.yaml` entry, so it cannot reproduce the
  duplicate-declaration corruption module.yaml's header documents. It is also
  the only place a `tools:` list is enforced by the harness rather than being
  prose: upstream's subagent convention (`skills/bmad-prfaq/agents/*.md`) is
  plain prompt files whose subagents inherit the parent's tools.
  `bmad-agent-qa` (Aviendha) is untouched and keeps her seat, her skill and her
  persona file; she is no longer the one who grades the wave.
  No stage and no agent was added beyond the evaluator: step 7 already existed
  and its review changed hands, step 10's party mode is unchanged, and
  `docs/wave-<id>/review-party.md` is still required at step 11 for every wave.
  33 tests in `skills/bmad-dev-wave/scripts/tests/test_evaluate_wave.py`, one
  of which runs `check` against the real shipped definition rather than a
  fixture.
- `.claude/agents/` added to the allowlist in `.gitignore` and
  `templates/.gitignore.template`. `.claude/*` is ignored with a per-directory
  allowlist that had no entry for it, so the evaluator definition -- and any
  future subagent definition, in the fork and in every installed project --
  would have been silently untracked.
- `install.sh` copies `.claude/agents/*.md` into a target project alongside the
  hooks, and `--validate-allowlist` now asserts the evaluator definition is
  present. The full conformance assertion (that its tool list is still safe
  after an install) is Phase 4's job, not this one's.
- Wave lifecycle status, and Keelswell's first *sticky* control:
  `skills/bmad-dev-wave/scripts/wave_status.py` (Phase 2 of
  docs/harness-conversion-plan.md). bmad-create-wave 1.0.0 -> 1.1.0,
  bmad-dev-wave 1.1.0 -> 1.2.0, bmad-merge-wave 1.1.0 -> 1.2.0,
  bmad-resume-wave 1.0.0 -> 1.1.0, bmad-status-wave 1.1.0 -> 1.2.0.
  A wave now carries its stage in `.bmad/wave-<id>/wave.md` and the wave
  skills route on it instead of each inferring state from the conversation and
  the filesystem. The vocabulary is BMAD's own bmad-build-auto
  (`spec-template.md:5` and its step-01 routing table) -- draft,
  ready-for-dev, in-progress, in-review, done, blocked -- defined once in that
  script and read from there by all five skills. No stage was added: every
  status re-enters at a step bmad-dev-wave already had, and `done` re-enters
  at step 10 as a fresh follow-up review pass rather than a resumption.
  Verbs are `route` (the gate, exit code is the verdict), `set` (advance it)
  and `show` (read-only, for the dashboard; it never backfills, so a
  project-wide scan cannot quietly migrate eighteen waves).
  **Blocked is sticky, and that is the Phase 2 deliverable.** A blocked wave
  halts every later dispatch after its cause is fixed, `set` refuses to write
  over a blocked record, and no flag exists to force either -- so no skill can
  clear a block it created. Only a human editing `status:` or deleting the
  record clears it. The asymmetry is the control: a retry loop is not one,
  because the run that blocked the wave is the run that would argue it is safe
  to resume. Copied from bmad-build-auto's note on permanence.
  Two ways a missing status is read, and the split is the mechanism rather
  than bookkeeping. No record at all is a wave that predates the field:
  `route` backfills it once from checkpoint, git and worktree evidence, prints
  an `UNMIGRATED` notice naming the inference, and proceeds -- Phase 1's
  prospective-rule shape, where a pre-field artifact gets a named reported
  exemption and never a silent default. A record that exists with an
  unreadable status is refused (exit 3). Without that second half, deleting
  the `status:` line would be an undocumented override of blocked.
  Forty stdlib unittest cases ship in `scripts/tests/`, and every claim they
  rest on was mutation-checked: six deliberate defects re-applied, six
  reddened. One did not, and it was a finding rather than a gap -- the
  `done`-re-enters-at-10 branch was unreachable given that stage's single
  step, so the branch is gone and a test pins the width instead.
- Keelswell's first executable enforcer:
  `skills/bmad-close-epic/scripts/check_review_records.py` (Phase 1 of
  docs/harness-conversion-plan.md). bmad-close-epic 1.2.0 -> 1.3.0. The
  preflight condition that every wave of an epic carries an adversarial
  review record was prose asking the agent to refuse its own work; it is now
  an exit code the skill obeys. The rule is unchanged. Exit 0 proceeds; 1 is
  a wave that landed on or after the 2026-09-10 rule date with no record; 2
  is structural (no wave map, or no waves in the epic); 3 is a wave with no
  record that cannot be dated. Fail-closed throughout: an undatable wave is
  not assumed pre-rule. The refusal text names the wave, both accepted record
  locations, and the remedy, per the vault's "the enforcer coaches" note.
  A wave is dated by the merge that brought its docs to the closing branch,
  not by the commit that wrote them on the wave's own branch. Measured across
  ffbapp's eighteen waves that lag runs from six minutes to forty-six hours,
  and wave 5D's commit (2026-09-09T03:09Z) and merge (2026-09-10T14:42Z) fall
  on opposite sides of the rule date: dating by the commit would have passed a
  post-rule wave as pre-rule, the one direction this gate must not fail in.
  Caught by checking the shipped prediction against real history rather than
  assuming the lag was negligible. Regression test included, verified to redden
  when the defect is re-applied.
  Skill-local `scripts/` is upstream's own convention
  (bmad-party-mode/scripts/) and survives a refresh, unlike `_bmad/scripts/`
  (runbook class D). Twelve stdlib unittest cases ship beside it in
  `scripts/tests/`. What this does and does not buy against Macedo's T4, the
  harness membership test the plan opens on: the *verdict* is now deterministic
  -- which waves carry records, and which side of the rule date they landed on,
  are computed rather than judged, so the agent can no longer reason its way to
  "this gap is acceptable". The *invocation* is not. Three links in the chain
  are still prose: invoking the skill, running the script inside step 1, and
  obeying a non-zero exit. The fork ships two hooks (PostToolUse em-dash scrub,
  SessionEnd wrap reminder) and no PreToolUse anywhere, so nothing denies a
  tool call. Calling T4 satisfied would overstate it until a hook forces the
  invocation; that is Phase 4's job.
- `__pycache__/` and `*.pyc` ignored in .gitignore and
  templates/.gitignore.template, now that the fork ships runnable Python.

### Fixed
- The Phase 2 backfill read sixteen of ffbapp's eighteen waves as `draft`,
  re-entering at step 1, when all eighteen are merged and done. Caught by
  running the migration against the real instance instead of the fixture:
  those waves have no `.bmad/wave-<id>/` at all, because their worktrees were
  swept by hand before bmad-merge-wave 1.1.0 started archiving checkpoints, so
  there was no marker evidence to infer from and the safe-direction default
  took over. The fix reuses Phase 1's own landing signal -- whether
  `docs/wave-<id>/` has merged into main -- and the ancestry test is the part
  that makes it safe: that directory also exists inside the wave's own
  worktree from step 3 onward, so mere presence would read every in-flight
  wave as finished. Re-run against a clone of the real repository, all twenty
  waves now migrate correctly, wave 5D included, whose stale step-2 checkpoint
  is overridden by its merged docs.
- bmad-close-epic's frontmatter claimed the epic-id argument matches an
  `## Epic <N>` block in waves.md. No such block exists: waves.md carries one
  flat table for the whole project, ordered by execution rather than by epic
  (in the ffbapp instance wave 6A sits between 4A and 4B). The epic is the
  leading digits of a Wave label. Caught by writing the gate against the real
  artifact; nothing had checked the documented contract against the file.
- The same pass found wave directories are lower-cased (`docs/wave-6a/`)
  while the Wave column spells them `6A`, so a check built on the column's
  own spelling finds no records anywhere. Recorded in the skill.
- Dating a wave via `gh pr view <branch suffix>` does not work and was never
  going to: waves.md's "Branch suffix" column is an intention, not a record.
  Probed against ffbapp, all three test branches returned "no pull requests
  found" -- real head refs carry tool prefixes and hashes
  (`claude/wave-4a-event-registry-825278`) and two waves' refs share no slug
  with the column at all. Substring matching is worse, since a wave's
  merge-cleanup branch matches the same label. The gate walks from the commit
  that added the wave's docs directory to the merge that brought it in, and
  dates the wave by that merge; verified against all eighteen ffbapp waves,
  with the seven pre-rule ones classified pre-rule and wave 5D correctly
  post-rule.

### Changed
- Eight `agents/custom-*.md` files collapsed to persona descriptors (Phase
  6.5 of docs/harness-conversion-plan.md): accessibility, analytics,
  design-critic, growth, legal, ml, sre, web-designer. Each was
  byte-identical to its `skills/agent-*/SKILL.md`; each now carries the H1,
  a provenance paragraph, and the overview paragraph verbatim, the shape the
  other seven custom agents already use, with the procedure living only in
  the skill. No prose edited, no skill changed, nothing bumped, nothing to
  mirror. The plan's premise that the installer reads `agents/` to build the
  roster was wrong: `[agents.*]` tables come from `module.yaml` alone
  (collectAgentsFromModuleYaml) and an install never copies `agents/` into a
  target. Verified anyway: a fresh `--target-project` install before and
  after emits the same 38 `[agents.*]` tables with the same codes
  (count-asserted), `resolve_party.py` on the target returns the same room
  of 38 and the same sixteen fork-only agents, and `--validate-only` passes
  both trees.
- Upstream refresh: bmad-method 6.10.0 -> 6.12.0 (Phase 0 of
  docs/harness-conversion-plan.md; runbook docs/upstream-refresh-runbook.md,
  invocation pinned to `npx bmad-method@6.12.0`, no `--modules`). What
  changed upstream and landed here:
  - BMM is skills-first: five agents (analyst, pm, ux-designer, architect,
    dev); bmad-agent-tech-writer retired (upstream removals.txt). Eight
    new skills in .claude/skills (bmad-build, bmad-build-auto,
    bmad-deep-recon, bmad-review, bmad-walkthrough, bmad-project-context,
    bmad-editorial-review, bmad-review-verification-gap); three removed
    (bmad-check-implementation-readiness, bmad-index-docs, bmad-shard-doc);
    21 old names retained as v6 compatibility shims that forward to their
    replacements (installShims: true recorded in manifest.yaml; upstream
    removes shims at v7). 106 -> 111 skill dirs.
  - _bmad/scripts/ re-synced from upstream: resolve_config.py and
    resolve_customization.py now import a new config_utils.py (same
    four-layer and three-layer merge, same CLI); render_skill.py added
    (bmad-build and bmad-build-auto shell out to it via `uv run`, so uv is
    now an upstream expectation). memlog.py unchanged. Finding: the
    installer wipes and re-copies _bmad/scripts/ on every install, so the
    directory is installer-owned, not a fork seam. Phase 1 must put its
    gate script elsewhere.
  - _bmad/config.toml regenerated: 38 agent blocks (bmm 5, cis 6, tea 1,
    keelswell 26), no duplicates; the _bmad/custom/config.toml overlay
    pins re-win at resolution (all 13 Wheel of Time names verified).
    manifest.yaml now records keelswell as an installed module (v0.8.0,
    localPath = the checkout the refresh ran from) and bumps core/bmm to
    6.12.0. Per-module config.yaml timestamps and files-manifest.csv
    regenerated (class C). Installer also creates _bmad/keelswell/ (its
    config.yaml now tracked like the other module config files) and the
    ignored _bmad/render/, _bmad/{core,bmm}/v6-shims/, and
    _bmad/agents/config.yaml (it treats the fork's _bmad/agents/ persona
    archive as a module dir).
  - Class B catalogs restored per the runbook (bmad-help.csv,
    skill-manifest.csv, core and bmm module-help.csv), then bmad-help.csv
    re-curated by hand: rows for the three removed skills dropped, rows for
    the five new real skills added from the 6.12 module-help sources, the
    Core and BMad Method _meta docs URLs updated. Rows for the 21 shim
    names were left in place (they still resolve, through forwarders).
- Not adopted, and why:
  - External module upgrades: tea v1.19.0 (v1.26.0 available), cis v0.2.1
    (v0.3.2), bmb v2.1.0 (v2.2.2), bmad-loop v0.8.1 (v0.11.1). All four are
    `channel: pinned` in manifest.yaml and the installer re-asserts pins
    under --yes; unpinning is a separate decision (`--pin code=tag`).
    tea v1.26.0 still declares only bmad-tea, so bmad-agent-qa remains
    keelswell-declared either way.
  - Upstream's 6.12 edits to the five vanilla bmm agent skills (menus
    re-pointed at bmad-deep-recon and bmad-project-context) and the
    bmad-retrospective rewrite: the fork's marketplace copies win over the
    upstream package for the same skill id, so these did not land. The
    mirrors still route through shim names (bmad-market-research,
    bmad-document-project, ...), which work until upstream drops shims at
    v7. Re-basing the mirrors on 6.12 is a follow-up, not part of this
    refresh.
  - The retirement of bmad-agent-tech-writer: the fork keeps Loial (see
    Added).
  - install.sh phase 4's `--modules bmm,cis,tea,bmb`: on an existing
    install it deselects and deletes bmad-loop, so the refresh used the
    runbook's line without it. The runbook text saying the two invocations
    are identical is stale.
  - skill-manifest.csv and the core/bmm module-help.csv were restored to
    their 6.10 content as the runbook prescribes; they now describe the
    pre-refresh layout (nothing fork-side reads them; the installer
    regenerates them on the next run).
- Post-refresh agent roster (38), by declaring module:
  - bmm (upstream module.yaml, names pinned by the overlay): Moiraine
    Damodred (analyst), Egwene al'Vere (pm), Perrin Aybara (architect),
    Mat Cauthon (dev), Min Farshaw (ux-designer).
  - cis (upstream, overlay-pinned): Siuan Sanche, Nynaeve al'Meara,
    Logain Ablar, Birgitte Silverbow, Thom Merrilin, Morgase Trakand.
  - tea (upstream, overlay-pinned): Galad Damodred (bmad-tea).
  - keelswell module.yaml (26): Rand al'Thor (bmad-master), Aviendha
    (bmad-agent-qa), Loial (bmad-agent-tech-writer); the eight
    architecture-pack agents Verin Mathwin, Elayne Trakand, Cadsuane
    Melaidhrin, Androl Genhald, Rhuarc, Berelain sur Paendrag, Lan
    Mandragoran, Sorilea (module label "arch" via the overlay); the fifteen
    custom agents Tam al'Thor, Tuon, Setalle Anan, Hurin, Gareth Bryne,
    Damer Flinn, Bayle Domon, Juilin Sandar, Jain Farstrider, Basel Gill,
    Talmanes Delovinde, Egeanin Tamarath, Aludra, Leane Sharif, Tarna Feir.
  - No agent is declared by more than one module. bmad-loop declares none;
    it is BMAD's outer orchestrator (uv-installed Python tool, module half
    only installed here) that invokes upstream bmad-build-auto per story.

### Added
- module.yaml declares bmad-agent-tech-writer (Loial, Technical Writer).
  Upstream bmm 6.12 no longer declares the code, so without this the
  overlay's name pin resolved to a name-only descriptor. Fork-only count
  25 -> 26. The now-redundant name pin in _bmad/custom/config.toml is
  removed (12 overlay pins remain).
- .gitignore allowlists _bmad/scripts/config_utils.py and
  _bmad/scripts/render_skill.py so the tracked resolvers keep working
  from a fresh clone, and _bmad/keelswell/config.yaml like the other
  module config files; templates/.gitignore.template carries the same
  lines so initialised projects match.

### Fixed
- Nine tracked .claude/skills copies of customize.toml (the seven bmm
  agents, bmad-master, bmad-tea) still carried the pre-0.6.0 voice fields;
  the refresh re-copied them from the skills/ sources, which win. Every
  fork mirror in .claude/skills now matches its skills/ source exactly.
- config/agent-names.yaml.default had 32 agents against the 38-agent
  roster of record (stale since 0.7.0), which made `install.sh
  --validate-only` fail before this refresh. Synced; validation exits 0.

## [0.8.0] - 2026-08-24
### Added
- Two custom agents forming a design maker/critic pair, deliberately
  split so neither grades its own work: agent-web-designer (Leane
  Sharif, web design -- visual system lock as a hard gate, design
  canvases via the `design` skill, published page artifacts via
  `artifact-design`, chart and dashboard work via `dataviz`, real
  front-end implementation, and a browser verification loop at 375,
  768, and 1280 in both light and dark) and agent-design-critic
  (Tarna Feir, design critique -- adversarial responsive and theme
  sweeps, design-system conformance measured value against expected,
  craft review of states and typographic detail, hierarchy and
  first-impression read, and a single go/no-go ship verdict with a
  blocking list). Custom roster 13 -> 15, full roster 36 -> 38.
- Leane is the first custom agent with source-edit authority; every
  other custom agent is advisory under folder dominion. The deviation
  is deliberate and stated in her operating rules: visual craft is a
  pixel-level loop that dies if each two-line change has to be handed
  off as a diff. Her authority is bounded to the presentation layer
  (styles, tokens, markup and class names, static assets,
  presentational components), never data fetching, state, routing, or
  business rules, and never a new dependency without asking. Tarna
  holds the opposite constraint -- she cannot edit anything, which is
  what keeps her verdict worth having.
- Pipeline the pair is built for: Leane locks the visual system and
  stops for approval, Leane builds, Tarna sweeps and ranks defects,
  Leane burns the list down, Setalle Anan gates WCAG conformance.
  Both agents route accessibility to Setalle and page performance to
  Jain Farstrider rather than issuing parallel verdicts.
- Touched the `skills/` and `.claude/skills/` trees, the `agents/`
  sources, module.yaml (roster plus the fork-only count in its header
  comment, 23 -> 25), marketplace.json, config/agent-names.yaml,
  _bmad/custom/module-help.csv, and the README roster line.
  marketplace.json plugin version and the README install pin bumped
  0.7.0 -> 0.8.0. The `.agents/skills/` tree carries only bmad-*
  skills and was left alone, matching the existing custom agents.

## [0.7.1] - 2026-08-07
### Fixed
- Min Farshaw's voice did not come through on activation: hers was the
  only core-agent communication_style with no character anchor (no
  world-role, no lore vocabulary; "viewing" read as a generic research
  term), so the agent played a generic terse persona -- reproduced by
  activation probe. Voice amended keeping the original's three beats
  (anti-court plainness, observed-vs-inferred discipline, tease then
  truth) and adding anchors: tavern-corner people-watcher, coat and
  breeches among silk gowns, viewings reported images-first with
  meaning labeled unknown. Probe re-verified in character. skills/
  and .agents/skills/ copies updated; isi and ffbapp instance trees
  updated in place.

## [0.7.0] - 2026-08-07
### Added
- Four custom agents (slate v3), from the 2026-08-07 bench-gap review
  of the ffbapp PRD: agent-bizops (Basel Gill, business operations --
  entity formation prep, bookkeeping, tax calendar and nexus,
  insurance worksheets, compliance calendar; preparation only, never
  professional advice, every artifact closes by naming the CPA,
  attorney, or broker who signs off), agent-llm (Talmanes Delovinde,
  LLM surface engineering -- grounding pipelines, eval harnesses,
  calibrated language, per-answer inference cost, injection exposure),
  agent-mobile (Egeanin Tamarath, mobile and app-store distribution --
  guideline review, IAP vs direct billing, release passage plans,
  push and disclosure policy, terms watch), and agent-marketing
  (Aludra, marketing and SEO -- technical SEO readiness, content
  engines, launch sequencing, listing and landing craft, measurement
  hooks). Custom roster 9 -> 13, full roster 32 -> 36. Touched both
  skill trees, the agents/ sources, module.yaml, marketplace.json,
  config/agent-names.yaml, _bmad/custom/module-help.csv, and the
  README roster line. marketplace.json plugin version and the README
  install pin bumped 0.4.1 -> 0.7.0 (both had gone stale at 0.4.1
  through the 0.5.0 and 0.6.0 releases).

## [0.6.0] - 2026-08-07
### Changed
- The nine core agents now speak in their Wheel of Time character's
  voice: communication_style rewritten in character for Moiraine
  (analyst), Egwene (pm), Perrin (architect), Mat (dev), Aviendha
  (qa), Loial (tech-writer), Min (ux-designer), Galad (tea), and
  Rand (bmad-master). QA and bmad-master gain the field (their
  customize.toml carried no persona fields); the carried personas'
  Style lines (agents/bmm-qa.md, agents/core-bmad-master.md) align
  with the new voices. Each voice keeps the old field's working
  signal: Mat still speaks in file paths and AC IDs, Galad keeps
  strong opinions weakly held as the surrendered sword form, Rand
  keeps route-and-say-why. identity, principles, roles, and menus
  unchanged. Touched both skill trees, the agents/ sources, and the
  _bmad installed copies (21 files including this changelog).
  Verified by resolver runs on every edited skill and activation
  probes on Mat, Aviendha, Galad, and Rand.

## [0.5.0] - 2026-07-20
### Changed
- The nine custom agents' skill ids renamed from persona form to role
  form: agent-tam-althor -> agent-sre, agent-tuon -> agent-growth,
  agent-setalle-anan -> agent-accessibility, agent-hurin ->
  agent-analytics, agent-gareth-bryne -> agent-legal,
  agent-damer-flinn -> agent-ml, agent-bayle-domon -> agent-billing,
  agent-juilin-sandar -> agent-appsec, agent-jain-farstrider ->
  agent-performance. Aligns the custom nine with the
  bmad-agent-<role> convention and the config/agent-names.yaml roster
  keys, so the skill picker reads by role. Personas are unchanged in
  descriptions and activation (talk-to-<persona> routing intact).
  Touched both skill trees, the agents/ sources, module.yaml,
  marketplace.json, and _bmad/custom/module-help.csv (30 files,
  count-asserted). Downstream installs keep the persona-named skill
  dirs until their next refresh -- prune per
  docs/upstream-refresh-runbook.md (verify installer merge behavior
  at refresh time).

### Fixed
- install.sh phase4_upstream now carries --modules bmm,cis,tea,bmb,
  aligning the live installer with the README install command (R1
  follow-up; quickstart v8 Appendix C).

## [0.4.1] - 2026-07-19
### Fixed
- README install command now carries --modules bmm,cis,tea,bmb
  (scratch-verified: all four module config.yaml files created, 97
  skills, valid config.toml -- closes F-10 for documented installs).
- .agents/ tree aligned in place: the 13 vanilla persona skills and
  bmad-retrospective copies (28 files, each verified byte-identical to
  their v0.2.0 baselines first) now carry the v0.3.0/v0.4.0 Wheel of
  Time content. TEA knowledge-base author attributions untouched. The
  tree remains unmanaged by the installer, per the refresh runbook.
- bmad-agent-qa and bmad-master customize.toml fallback identities
  aligned to their carried personas (Aviendha, Rand al'Thor).
- _bmad/custom/module-help.csv backfilled with the 6 pre-existing
  custom agents (now lists all 9).
- Runbook: F-10 section updated; logged the fresh-install descriptor
  nuance (vanilla 13 registry blocks show upstream names in OTHER
  projects because overlay pins do not travel with marketplace
  installs; skills themselves still greet under Wheel of Time names).

## [0.4.0] - 2026-07-19
### Added
- module.yaml: the keelswell custom-module descriptor. Kills the
  installer's "could not locate module.yaml" warnings, records the real
  module version in installed manifests (closes F-9), scopes install
  answers correctly, and writes descriptor blocks for the 19 fork-only
  agents (8 arch, 9 custom, bmad-master, bmad-agent-qa) into
  _bmad/config.toml under their Wheel of Time names -- party-mode and
  the help catalog can now see the full roster. Deliberately does NOT
  redeclare the 13 upstream-declared vanilla agents: the installer
  emits duplicate [agents.*] tables for cross-module redeclarations,
  corrupting config.toml (scratch-verified); their WoT names remain
  pinned by the _bmad/custom/config.toml overlay.
- bmad-retrospective shipped via marketplace.json + skills/ mirror (39
  -> 40 entries), so the fork's Mat Cauthon recast survives upstream
  refreshes (custom-module skills win over the upstream package for the
  same skill id).
- docs/upstream-refresh-runbook.md: closes F-6. Root cause of the
  .agents/ deletion (IDE-list reconciliation wiping a deselected
  platform's shared target_dir), proof the tripwire is disarmed
  (manifest now records claude-code only; scratch refresh left all
  1051 files untouched), the three refresh clobber classes with
  restoration steps, and the documented F-10 limitation
  (--modules bmm,cis,tea,bmb for full-function fresh installs).

## [0.3.0] - 2026-07-19
### Fixed
- F-5 closed: all 13 vanilla persona agents (6 BMM, 6 CIS, TEA) now carry
  their Wheel of Time roster names in every activation surface -- SKILL.md
  (both shipped copies), customize.toml identity, the agents/ and
  _bmad/agents/ persona files, and skill-manifest.csv trigger
  descriptions. Closing-line pronouns follow the new personas.
- bmad-retrospective's scripted dialog recast from Amelia to Mat Cauthon;
  bmad-agent-qa's scope boundary aligned to the dual provenance form
  "Galad Damodred / Murat (TEA)".
- _bmad/custom/config.toml overlay pins the 13 resolved display names,
  overriding the installer-owned _bmad/config.toml descriptor registry
  per its own custom-overlay contract (resolver-verified: 21 blocks, all
  Wheel of Time names).

## [0.2.0] - 2026-07-18
### Added
- Three custom agents: Bayle Domon (Monetization/Billing), Juilin Sandar
  (Application Security), Jain Farstrider (Performance/Capacity). 32 agents
  total.
- Two carried-persona rider launchers: bmad-master (Rand al'Thor) and
  bmad-agent-qa (Aviendha), making both invokable as real skills for the
  first time.
- config/agent-names.yaml and .default extended with the 3 new roster rows.
- bmad-master and bmad-agent-qa registered in _bmad/_config/bmad-help.csv
  (and the matching core/bmm module-help.csv files) as DF-1 carried-persona
  entry points; the 3 new single-persona custom agents intentionally left
  unregistered there per the sparse multi-capability-only rule.
- .claude-plugin/marketplace.json and skills/ mirror expanded to 39 entries.

## [0.1.0] - 2026-07-17
### Added
- 23-agent merged base (vanilla BMAD + Architecture Agent Expansion Pack).
- Six custom agents: SRE, Growth, Accessibility, Analytics, Legal, ML.
- Seven wave-development skills: create/dev/resume/status/merge waves, close-epic, wrap.
- core/config.yaml operational defaults; agent-names.yaml with install-time override.
- Project templates (settings.json, CLAUDE.md, TODO, HANDOFF, .gitignore) and install.sh.
- .claude-plugin/marketplace.json discovery manifest.
