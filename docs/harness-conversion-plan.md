# Harness conversion plan

How to turn Keelswell from a set of instructions into a harness, without
breaking the four upstreams it tracks. Written 2026-09-10 from the
evidence assembled in `../harness-wiki` (36 source pages; the specific
claims behind each phase are cited inline as `[[wiki-page]]`).

## The finding this plan exists for

Keelswell ships 46 skills and **zero executable resources**. No `.sh`,
`.py`, or `.js` anywhere under `skills/`. The two hooks in
`.claude/hooks/` are an em-dash scrubber and a wrap reminder; neither
enforces a workflow invariant.

The gates the recent wave work added are prose. `bmad-close-epic`
instructs the agent to refuse a wave with no review record. The rule is
right and the agent usually follows it, but nothing stops it from not
following it.

The definitional test from `[[macedo-what-makes-a-harness]]` asks four
questions; the fourth is whether the system includes at least one
control mechanism "that does not depend on the mere obedience of the
model." Keelswell fails that one. It passes T1 through T3.

This is not a fork-specific failing. `[[galster-config-mechanisms-study]]`
measured 2,853 repositories and found 85.5% of skills carry no
executable resources at all. The whole field ships prose. That is why
this plan is short: one class of change, applied at four points.

## Where the evidence says to invest

`[[lin-agentic-harness-engineering]]` evolved a harness, froze it, and
moved it to another benchmark and three other model families. A
component ablation found tools, middleware and long-term memory each
carried the improvement on their own, while **the evolved system prompt
alone regressed**. Factual harness structure transfers; prose-level
strategy does not.

`[[sia-self-improving-harness-weights]]` bounds what to expect: harness
updates "make the model agentic, shaping how it searches and acts,"
while domain intuition comes from weights, not scaffold. Fifteen of the
sixteen fork-only agents are domain personas. They are working the
lever the evidence says does not move.

Neither finding says delete the prose. Both say stop treating it as the
durable asset.

## What tracking upstream constrains

Keelswell tracks four upstreams: BMM, CIS, TEA, and the third-party
architecture pack (`Ricoledan/bmad-architecture-agent`). Of the 38
files in `agents/`, 22 arrive from those modules and 16 are fork-only.

So `agents/` is the worst place to invest, and not only for the
transfer reason. `module.yaml` already records what happens when the
fork and an upstream both declare a persona: "the installer emit[s]
duplicate `[agents.*]` tables and corrupt[s] config.toml."

Three seams are fork-only and merge-safe:

1. **The seven wave skills** (`bmad-create-wave`, `bmad-dev-wave`,
   `bmad-merge-wave`, `bmad-resume-wave`, `bmad-status-wave`,
   `bmad-close-epic`, `bmad-wrap`, plus `bmad-retrospective`). No
   upstream conflict surface at all.
2. **Skill-local `scripts/` directories inside the wave skills**, the
   convention upstream itself uses (`bmad-party-mode/scripts/`,
   `bmad-sprint-planning/scripts/`, invoked as
   `uv run {skill-root}/scripts/<name>.py`). The installer copies a
   skill directory whole, so the scripts travel with the skill. Not
   `_bmad/scripts/`: the 6.12.0 refresh showed the installer deletes
   and re-copies that directory from its own package on every install
   (`upstream-refresh-runbook.md`, class D), so anything the fork puts
   there is gone at the next refresh.
3. **`install.sh` phase 6 (validation)**, a gate upstream never sees.

The capability is already here. What is missing is that none of it
enforces a workflow invariant.

## Phase 1: one real gate

Move the `bmad-close-epic` refusal from prose into a script under
`skills/bmad-close-epic/scripts/` that the skill calls and that exits
non-zero when a wave has no review record.

Pick this gate because the recent wave work already invested in it
(`bmad-dev-wave` 1.1.0, `bmad-close-epic` 1.2.0, `bmad-status-wave`
1.1.0), so the rule is settled and only its enforcement changes.

The pattern is `[[default-fail-contract]]` from
`[[anthropic-cwc-long-running-agents]]`: the criterion starts false and
the agent cannot mark it true without the evidence existing. Its own
framing is the point — "asking nicely in the prompt doesn't reliably
stop this. The harness makes 'done' structural."

**Verify:** close a wave with no review record. The failure comes from
the script's exit code, not the agent's judgment. That single test
moves Keelswell across T4.

**Estimate:** half a day.

## Phase 2: status as a state machine, with a sticky blocked

Wave records carry lifecycle status in frontmatter; `bmad-resume-wave`
routes on it rather than inferring state; `blocked` stays blocked until
a human deletes the record.

The shape is BMAD's own `bmad-build-auto` (`[[bmad-official-docs]]`):
`draft` enters at plan, `ready-for-dev` and `in-progress` at implement,
`in-review` at review, `done` runs a fresh follow-up pass, `blocked`
halts. Their note on permanence is the part worth copying: a blocked
record halts every later dispatch "even after the cause is fixed. To
retry, delete the story file."

A sticky failure state that only a human act can clear is a control
mechanism in the T4 sense. A retry loop is not.

**Verify:** each status resumes at the correct stage, and a blocked
wave halts on every subsequent dispatch after its cause is fixed.

**Estimate:** one to two days.

## Phase 3: an evaluator that cannot edit

`bmad-agent-qa` is a persona loaded into the same context that did the
work. `[[generator-evaluator-split]]` is the vault's best-evidenced
concept: agents "respond by confidently praising the work" they
produced.

`[[anthropic-cwc-long-running-agents]]` adds the structural move beyond
prompt-tuning: its evaluator subagent has **no Write/Edit tools**, and
reviews from a context window that never saw the build, returning
PASS/NEEDS_WORK. On NEEDS_WORK the findings become the next session's
opening prompt.

Take BMAD's stopping rule with it: non-trivial findings on a third
review pass "usually mean something is wrong upstream of this change: a
weak spec, a contradiction, or ambiguity in the rules. Fix that instead
of running another pass."

**Verify:** the evaluator is structurally incapable of fixing what it
finds.

**Estimate:** one day.

## Phase 4: conformance check in install.sh

`install.sh` already ends in a validation phase. Extend it to assert the
invariants from phases 1 to 3 still hold after an install: scripts
present and executable, wave records well-formed, the gate wired.

This is the phase that protects the other three. An upstream refresh
that silently breaks the enforcement layer should fail the install, not
surface three waves later.

**Verify:** deliberately break one invariant; the install fails loudly
and names it.

**Carried in from Phase 1**, found while checking that phase's predictions
and deliberately left here rather than fixed in passing (RQ, 2026-09-11):

- `install.sh:214` (`for s in skills/*; do ... cp -r ...`) copies the working
  tree verbatim, so stale `__pycache__/` from a test run ships into every new
  project. Ignored at both ends since Phase 1 added the lines to `.gitignore`
  and `templates/.gitignore.template`, so nothing is committed and nothing
  breaks; it just ships junk. One line in the copy loop prunes it.
- The gate's invocation is still prose. Phase 1 made the review-record
  *verdict* deterministic, but three links in the chain remain obedience:
  invoking `/bmad-close-epic`, running the script inside step 1, and honouring
  a non-zero exit. The fork ships two hooks (`PostToolUse`, `SessionEnd`) and
  no `PreToolUse`, so nothing denies a tool call. Until one does, Macedo's T4
  is not satisfied -- the conformance phase is where that claim gets earned,
  not Phase 1.

**Carried in from Phase 2**, same rule: found while checking that phase's
predictions, left here rather than fixed in passing (RQ, 2026-09-11):

- `bmad-dev-wave` step 4.5, the open-questions gate, halts for user input and
  that halt is a pause rather than a `blocked` status. It was left that way
  deliberately: 4.5 asks a question it expects answered in the same session,
  and blocking on every open question would make `blocked` routine, which
  teaches the founder to clear the record by reflex and cheapens the control
  everywhere else. The cost is that the pause lives entirely in the
  conversation, which is the exact failure mode Phase 2 exists to remove for
  every other piece of wave state. A session that dies while waiting for the
  answer (crash, timeout, `/clear`, the reasons `bmad-resume-wave` exists)
  leaves nothing on disk recording that the question went unanswered, and the
  next dispatch walks past it.
  The resolution is neither option on its own: a question answered in the same
  session stays a pause, a question abandoned by a dead session becomes a
  block. Nothing detects the second case today, but the fork's existing
  `SessionEnd` hook is the place to hang it -- on session end, a wave paused at
  4.5 with no recorded answer gets `--status blocked`. That makes it Phase 4
  work, since it is a hook enforcing an invariant rather than a skill obeying
  one, and it is the same missing `PreToolUse`/hook-level gap the Phase 1 item
  above names.
- `done` spans two skills: a wave is done once `bmad-merge-wave` sweeps it,
  while its epic stays open until `bmad-close-epic` runs. Phase 2 mapped `done`
  to a fresh follow-up review pass at step 10 rather than inventing a `closed`
  status, per this plan's "do not add stages". Whether that follow-up pass is
  genuinely wanted on a merged wave, or is ceremony inherited from
  `bmad-build-auto`, is worth deciding before Phase 3 builds the evaluator that
  would run it.

**Carried in from Phase 3**, same rule: found while checking that phase's
predictions, left here rather than fixed in passing (RQ, 2026-09-11):

- Phase 2 asked whether `done`'s follow-up pass is wanted "before Phase 3
  builds the evaluator that would run it". Phase 3 did not resolve it, and did
  not need to: `done` re-enters at step 10, party mode, while the evaluator
  went to step 7, so a merged wave's follow-up pass runs the domain reviewers
  and not the evaluator. The question is unchanged and still open, just no
  longer blocking.

- The evaluator's *inability to edit* is structural, but its *being dispatched
  at all* is still prose, and this is the third time the same gap has been
  written down (Phase 1's gate invocation, Phase 2's step-4.5 pause, now this).
  Nothing stops a step-7 agent from reviewing the wave in its own context and
  never running `evaluate_wave.py dispatch`, and nothing stops it from reading
  exit 1 and fixing the findings in place anyway. The three items now share one
  root: the fork ships `PostToolUse` and `SessionEnd` hooks and no `PreToolUse`,
  so no tool call is ever denied. Phase 4 should treat them as one piece of work
  rather than three, since one `PreToolUse` hook covers all three and three
  separate ones would not.
- `templates/settings.json.template` carries `subagentModels` and
  `subagentReasoning` keys that do not appear in Claude Code's settings schema.
  If that is right, they have configured nothing since they were written, and
  `core/config.yaml`'s `role_models` table has been feeding a dead end. Phase 3
  routed around it by putting `model: opus` in the evaluator's own frontmatter,
  which is the mechanism that does work, but the config table is still the
  documented source of truth and the two now disagree. Worth confirming against
  the schema before Phase 5 prunes anything on the strength of that table.
- `core/config.yaml`'s `model_tiers` pin `claude-opus-4-8`, `claude-sonnet-4-6`
  and `claude-haiku-4-5`, a generation behind the current Claude 5 family. This
  is exactly the "re-earn after each model release" case Phase 5 names, so it
  belongs there rather than in a phase that happened to notice it.

**Estimate:** half a day.

## Phase 5: decide what is consumable

Applies only to the 16 fork-only agents. The 22 from upstream modules
are not ours to prune.

The test per agent: name a specific failure it prevents. Agents that
cannot answer are consumable — re-earned after a model release, not
accumulated. `[[anthropic-cwc-long-running-agents]]` gives the same
advice from practice: "re-evaluate how much of CLAUDE.md you still need
after each model release."

This is deliberately last. It is the lowest-value phase and the easiest
to argue about; the first four change what Keelswell is.

**Estimate:** ongoing, one pass per model release.

## Standing item: upstream drift

BMM has moved skills-first and now ships five agents against the seven
carried here; its config lives at `_bmad/config.toml` with team and
user override layers (`[[bmad-official-docs]]`). That drift arrives
whether or not we act on it.

Record in `CHANGELOG.md` on each upstream pull: what changed upstream,
and what we chose not to adopt. The second half is the one that gets
lost.

## Three things not to do

**Do not add stages.** `[[wang-inference-time-alignment]]` names
over-decomposition as a failure mode and finds partial harnesses
outperforming full workflows. Decomposition granularity is set by the
agent's controllable progress per step, so the right number of wave
stages should *fall* as models improve. Treat "the agent skipped our
stage" as possible evidence the stage is too fine.

**Do not add agents.** See the transfer evidence above.

**Do not build a self-improving loop yet.**
`[[lin-agentic-harness-engineering]]` reports that such a loop's
"self-attribution is reliable for fixes but blind to regressions." It
notices what it fixed and misses what it broke. Phases 1 to 4 first.

## Throughout: predict what you might break

Adopt AHE's decision observability by hand. Every change ships a note
naming the failure evidence, the root cause, the fix, and a **predicted
impact including at-risk regressions**, checked on the next pass.

> "Each edit thereby becomes falsifiable by the next evaluation, which
> replaces rationale-driven self-justification with a measurable
> contract between rounds."

Cheap to do, and it is what keeps a ratchet from becoming accretion.
