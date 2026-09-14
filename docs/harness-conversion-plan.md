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

**Carried in from Phase 4**, same rule: found while building that phase, left
here rather than fixed in passing (RQ, 2026-09-11):

- Neither live instance (ffbapp, isi) has a `.claude/settings.json`; both
  carry only a personal `settings.local.json`. The hooks
  `templates/settings.json.template` registers (the em-dash scrub and wrap
  reminder included, since before this phase) reach a project only on a
  fresh `--target-project` install. On an existing instance the hook wiring is
  a hand step, the same surgical copy every skill update has been. Until it
  is done there, Phase 4's hooks are inert in the two projects that run
  waves, and the T4 claim holds for fresh installs only.
- Claude Code's auto-mode classifier refused to write the PreToolUse wrapper
  (`.claude/hooks/wave-gate.sh`) and to register it in the settings template,
  while allowing the SessionEnd wrapper and the gate script itself. A hook
  that can deny tool calls is, to the harness, a change to its own permission
  layer. Those two files are a hand step for RQ, and a future session that
  needs to touch either should expect the same refusal and plan for it.
- The fork's own `.claude/skills/` snapshot was two phases behind `skills/`
  (Phases 2 and 3 mirrored source only). The conformance check now catches
  that, but nothing makes the mirror happen: the fork is not a
  `--target-project`, and a refresh mirrors it as a side effect. Whether the
  fork should mirror itself on every commit (a pre-commit hook) or accept
  that its snapshot is refreshed only by a refresh is a Phase 5-sized
  decision, not a fix.

## Phase 5: decide what is consumable

Applies only to the 16 fork-only agents. The 22 from upstream modules
are not ours to prune.

The test per agent: name a specific failure it prevents. Agents that
cannot answer are consumable — re-earned after a model release, not
accumulated. `[[anthropic-cwc-long-running-agents]]` gives the same
advice from practice: "re-evaluate how much of CLAUDE.md you still need
after each model release."

This was written to be last. It is the lowest-value phase and the
easiest to argue about; the first four change what Keelswell is.

**Done 2026-09-12:** `agent-inventory.md`, assessed against the Claude
5 family. Six earn their place, seven are consumable, three could not
answer and are not recommended for deletion. The pass also found that
nothing in the wave loop calls any of the sixteen, which is why
Phase 6 exists and why this is no longer the last phase.

**Estimate:** ongoing, one pass per model release.

## Phase 6: call the agents the wave needs

Phase 5's inventory (`agent-inventory.md`, 2026-09-12) produced one
finding that outranks its own verdicts: **no wave skill references any
of the sixteen fork-only agents.** `bmad-dev-wave` step 10 hardcodes
three domains, "dispatch security, cost, and platform reviewers", and
nothing anywhere selects a reviewer from what the wave actually
touches. Waves 4A and 4B landed the model work with no Damer Flinn,
and 4B is where the defect 5D eventually caught originated.

That is why twelve of the sixteen have no evidence. It is an absence of
dispatch, not an absence of value, and it means Phase 5's groupings
rest on planning-phase reviews for most of the slate.

Five items, sequenced. All but the first are small; the first is the
phase.

### 6.1 Record the model in every wave review record

Cheapest and first, because everything else is measured against it.
Review records do not say which model produced them, so Phase 5's
inventory cannot be recomputed exactly against its own evidence and
the next pass inherits the same blindness. Add `model:` and `effort:`
to the front matter of `docs/wave-<id>/review-party.md`, written by
`bmad-dev-wave` step 10.

Scoped to the wave record deliberately. `bmad-party-mode` is upstream,
not fork-owned, so stamping the planning-phase reviews it writes would
open the conflict surface this plan avoids. Those stay unstamped. The
loss is bounded: planning is largely done on ffbapp, and wave records
are where the next inventory's evidence will come from. If a
`_bmad/custom/bmad-party-mode.toml` override turns out to be able to
inject front-matter fields rather than only workflow variables, revisit
it then; do not assume it can.

**Verify:** the next wave's `review-party.md` names its model.

**Done 2026-09-12** (bmad-dev-wave 1.5.0). The record had no front
matter to add to: the skill specified none, and two of ffbapp's ten
wrote one anyway, so the block codifies what they converged on rather
than imposing a new shape. Scope grew from two fields to a five-field
block for that reason. `model` is the reviewers', not the
orchestrator's.

**Estimate:** 20 minutes.

### 6.2 Refresh ffbapp's nine stale agent codes

ffbapp keys nine of the fifteen custom agents under their pre-0.5.0
persona codes (`agent-setalle-anan`, `agent-tam-althor`,
`agent-hurin`, `agent-gareth-bryne`, `agent-damer-flinn`,
`agent-bayle-domon`, `agent-juilin-sandar`, `agent-jain-farstrider`,
`agent-tuon`). Its `config.toml` and skill directories agree with each
other, so nothing is broken today. But 6.3 is written against role
codes and would silently miss those nine on the only instance that
runs waves. Sequence this before 6.3 or 6.3 ships inert.

Surgical per-skill copy per `upstream-refresh-runbook.md`, the same
hand step every instance update has been.

**Verify:** `resolve_party.py` returns all sixteen under role codes.

**Done 2026-09-12** (attacktheseam/ffbapp#98). The nine skill
directories and their `config.toml` tables renamed from persona to
role codes; ffbapp's `main` now lists all fifteen custom agents under
role codes, so 6.3 has nothing left to miss there.

**Estimate:** one hour.

### 6.3 A reviewer-selection script, not a reviewer-selection rule

Replace step 10's hardcoded three with a selection driven by the
wave's changed-file list. The sixteen triggers are already written in
`agent-inventory.md` in checkable form: each can be answered yes or no
from the file list and spec without judgment.

Build it as `skills/bmad-dev-wave/scripts/select_reviewers.py` reading
a YAML trigger table, printing the reviewer set. **The script is the
point.** A selection rule written as prose in the SKILL.md lands in
the layer `[[structure-transfers-prose-does-not]]` says regresses when
moved; the same logic as a script and a table is dispatch, which is
the layer that transfers. This is also the convention upstream already
uses (`bmad-party-mode/scripts/`), so it travels with the skill
directory and survives a refresh.

The rule the table encodes is **necessity, not a budget**: if eight
domains are genuinely in the diff, call eight; if one is, call one. No
cap, because a cap means choosing which real gaps to skip looking for.
What keeps it affordable is trigger precision, not a headcount limit.

The fixed three lose their exemption at the same time. If necessity
decides, dispatching security, cost and platform on every load-bearing
wave is wrong in the same direction as never dispatching the
specialists. Wave 5B's clean result is already on record as a review
that found nothing.

Adds no agent, so it does not violate "do not add agents" below: it
routes to the sixteen already declared.

**Verify:** a wave touching no infrastructure dispatches no platform
reviewer, and a wave touching a webhook receiver dispatches
`agent-billing`, both provable from the script's output before the
wave runs.

**Estimate:** half a day.

### 6.4 One ablation wave for the three unanswered agents

`agent-web-designer`, `agent-design-critic` and `core-bmad-master` have
zero activations across 87 transcripts. Phase 5 does not recommend
deleting them; it recommends finding out.

Two of the three answer in a single wave, the first that ships a
rendered surface: dispatch the web designer to build with its
five-step verification loop (the only real structure in the slate, and
it has never run), then the design critic against the result. If the
critic's list contains nothing the builder's own pass missed, the
independence claim buys nothing and one of the two is enough.

`core-bmad-master` needs no wave. Name one request that should route to
it and does not already route to `bmad-help` or to skill routing. If
that sentence cannot be written, the entry stays unanswered and costs
one roster line in party mode.

**Verify:** the wave's review record names what each of the two filed,
and whether the lists overlap.

**Estimate:** rides an existing wave. Blocked until a phase ships a
user interface.

### 6.5 Collapse the eight duplicate agent files

Eight `agents/custom-*.md` files are byte-identical to their
`skills/agent-*/SKILL.md` (accessibility, analytics, design-critic,
growth, legal, ml, sre, web-designer). The other seven use the better
pattern already: a short persona descriptor over a richer skill. Two
copies of the same prose drift independently, and the fork has two
generations of the slate living side by side.

Lowest value of the five. It is maintenance hygiene on the consumable
layer, which is the layer this plan says not to invest in, so it goes
last and only because duplication costs maintenance rather than
capability.

**Verify:** a fresh `--target-project` install produces the same
roster before and after, count-asserted.

**Done 2026-09-14.** Mechanical: H1, a provenance paragraph in the
seven's wording, and the overview paragraph verbatim; frontmatter and
procedure sections dropped. The eight are an older generation than the
seven (one overview paragraph, no Role/Identity/Style lines), so they
were not restructured. The installer risk named above did not exist:
the roster is read from `module.yaml` only and `agents/` never reaches
a target install. Verified anyway, count-asserted: 38 `[agents.*]`
tables before and after with the same codes, a room of 38, the same
sixteen fork-only agents, and `--validate-only` green on both trees.

**Estimate:** two hours.

### Party mode is not in scope

Standing rule, verified 2026-09-12 and unchanged by 6.3: when
`bmad-party-mode` is initiated, every agent is in the room. Trigger
selection is for the wave loop only. The resolver already does this
(`"active": "installed"`, a room of 38) because `default_party` is
`""`, so the rule is preserved by **not** setting it. Any change that
sets `default_party` to a configured group shrinks the default room and
breaks this.

### Predicted impact

Per the standing discipline below. **Predicted:** 6.3 raises the
finding count on model-touching and payment-touching waves and lowers
reviewer count on waves that touch neither. **At risk:** review cost
per wave, and the failure mode is not an expensive review but a review
that gets skipped because it became expensive. Wave 3C already ran with
no adversarial review at all. If average reviewer dispatches per wave
rise rather than redistribute, the triggers are too loose; tighten
before concluding anything about the agents.

**Estimate:** one day for 6.1 through 6.3, which is the part that
changes behaviour. 6.4 rides a wave; 6.5 is two hours whenever.

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
