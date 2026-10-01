# Harness conversion prompts

Session-opening prompts for each phase of `harness-conversion-plan.md`,
plus the standing post-pull check. Written 2026-09-11. Phase 0 runs
first; every later phase assumes the previous one is merged to
`main`. Run every session from
the keelswell root: the paths are relative to it and the project's
`.claude/` settings need to load.

Model and effort per phase are recommendations, not requirements. The
reasoning: Opus 5 at `xhigh` is the default for bounded, fully
specified coding work; Phases 0 and 4 get Fable 5.1 because they touch
the installer that already caused one incident and their failure mode
is silent; Phase 5 drops to `high` because it is reading and judgment,
where a human's priors beat raw effort.

Each prompt ends by making the model state its approach and its
biggest uncertainty before touching anything. That step is where a
misread of the plan gets caught cheaply. Do not skip it.

## Phase 0: upstream refresh, before anything else

Fable 5.1, effort `xhigh`. Opus 5 at `xhigh` is fine if step 3's
`git status` matches what the runbook predicts; escalate if it does
not.

Ran 2026-09-11, merged as PR #11. One assumption in this prompt was
wrong: `_bmad/scripts/` is installer-owned, not a fork seam (the
installer wipes and re-copies it on every run; runbook class D). The
Phase 1 and Phase 2 prompts below were corrected for that.

Why this is first: the fork is pinned at bmad-method 6.10.0 (published
2026-07-03) and upstream is at 6.12.0 (2026-09-04). The delta is
structural: BMM moved skills-first with five agents against the 6.10
roster of seven, and QA moved into the TEA module. Phase 1 does not
care, but Phase 3 routes around `bmad-agent-qa` and Phase 2 borrows
`bmad-build-auto`'s vocabulary, both 6.12-era shapes. Building them
against 6.10 and refreshing afterwards is the worst order.

```text
Run the upstream refresh runbook. This is preparation for Phase 1 of
docs/harness-conversion-plan.md, not part of it: the fork is pinned
at bmad-method 6.10.0 and upstream is at 6.12.0, and Phases 2 and 3
are designed against the 6.12 shape, so the refresh has to land
first.

Read, in this order, before running anything:
1. docs/upstream-refresh-runbook.md, all of it. The incident section
   and the clobber classes (B and C) are the reason the procedure
   looks the way it does.
2. The manual chapters the runbook cites (Ch 34, App I.10/I.12/I.13)
   in ../keelswell-manual.
3. module.yaml, top comment. It documents how a duplicate agent
   declaration corrupts config.toml. The upstream roster changed
   between 6.10 and 6.12, so this is the live risk this time.
4. docs/harness-conversion-prompts.md, the "Standing item" section.
   Step 5a of the runbook runs it. Its step 1 does not apply yet;
   its steps 2 and 3 do.

What changed upstream that you should expect to see: BMM moved to a
skills-first layout with five agents (the 6.10 roster here has
seven), QA moved into the TEA module, and config moved toward
_bmad/config.toml with team and user override layers. Some of that
will collide with the fork's Wheel of Time overlay and with
module.yaml. Expect it; do not be surprised by it; do not resolve it
by hand-editing anything an upstream module declares.

Then follow the runbook's six steps exactly, with these additions:

- Before step 2, confirm which bmad-method version npx will resolve.
  It must be 6.12.0, not a -next prerelease. Tell me the version
  before you run the install.
- At step 3, if git status shows anything outside the classes the
  runbook names, stop and show me. That instruction is in the
  runbook already; I am repeating it because it is the one that
  matters.
- At step 5a, run the standing item's steps 2 and 3: diff upstream's
  changes against the fork-owned seams (wave skills, _bmad/scripts/,
  install.sh, config/agent-names.yaml, module.yaml), then draft the
  CHANGELOG entry with both halves: what changed upstream, and what
  we are choosing not to adopt and why.
- In that CHANGELOG entry, also record the post-refresh agent roster
  (which personas exist, which module declares each). Phases 2 and 3
  need that baseline.
- While you are in the manifest: _bmad/_config/manifest.yaml lists a
  bmad-loop module at v0.8.1. Tell me what it is and whether it is
  the orchestrator that BMAD's bmad-build-auto hands off to. Do not
  change it. Phase 2 may be able to lean on it.

Done means: the runbook's step 5 verification passes, the CHANGELOG
entry is written with both halves and the roster, and the tree is
clean on a branch ready for PR. Open the PR. In its description,
list every file the refresh touched that a Phase 1 through 3 session
will also touch, so those sessions know what moved under them.

Constraints:
- Branch, never main. Clean tree before step 2.
- Do not touch agents/ except through the installer and the class B
  restore the runbook describes.
- If the refresh wants to change the wave skills or _bmad/scripts/,
  that is unexpected and you stop.
- Nothing from the harness conversion plan gets built in this
  session. If you see an obvious Phase 1 opportunity, note it for
  the Phase 1 session and leave it.

Before running the install: tell me the resolved version, your read
of what the roster change will do to the Wheel of Time overlay and
module.yaml, and the one thing you are least sure about. Wait for my
go-ahead.
```

## Phase 1: one real gate

Opus 5, effort `xhigh`.

```text
Start Phase 1 of the keelswell harness conversion.

Read docs/harness-conversion-plan.md first. It has the diagnosis, the
evidence, and the five phases. This session is Phase 1 only: make the
bmad-close-epic gate real. Do not start Phase 2.

What Phase 1 is: bmad-close-epic currently asks the agent to refuse
closing a wave that has no review record. That refusal is prose in
SKILL.md, so it depends on the model choosing to comply. Move the
enforcement into a script under skills/bmad-close-epic/scripts/ that
the skill calls (upstream's own skill-local convention; see
bmad-party-mode/scripts/) and that exits non-zero when the review
record is missing. The rule does not change; only where it is
enforced.

Done means: attempting to close a wave with no review record fails on
the script's exit code, not on the agent's judgment. Show me that
failing case and the passing case before you call it finished.

Constraints that matter here:
- Keelswell tracks four upstreams (BMM, CIS, TEA, the Ricoledan
  architecture pack). Only touch the fork-owned seams the plan names:
  the wave skills (including their scripts/ subdirectories) and
  install.sh. Do not touch agents/. Never put anything in
  _bmad/scripts/: the installer wipes and re-copies it on every
  refresh (docs/upstream-refresh-runbook.md, class D).
- The installer is fragile. module.yaml documents how a duplicate
  declaration corrupts config.toml. Read that comment before changing
  anything the installer reads.
- Match upstream's skill-local script style (Python, stdlib only;
  .claude/skills/bmad-party-mode/scripts/ is the nearest model).
  Upstream 6.12 invokes such scripts as
  `uv run {skill-root}/scripts/<name>.py`; the fork's mirrored skills
  still use `python3`. Pick one and say which in your approach. Keep
  the existing skill conventions, including the version bump and
  CHANGELOG entry the recent wave commits used.
- Do not add stages or agents.

Work on a branch and open a PR, the way the recent wave changes were
merged. In the PR description, include a short prediction: what this
change fixes, and what it might break. That prediction gets checked
on the next pass, so make it specific.

Before writing anything: read the plan, read the files Phase 1
touches, then tell me your approach and the one thing you are least
sure about. Wait for my go-ahead.

The evidence behind the plan is in ../harness-wiki. Start with
concepts/default-fail-contract.md and concepts/mechanical-enforcers.md
if you want the reasoning; you do not need the whole vault.
```

## Phase 2: status as a state machine, with a sticky blocked

Opus 5, effort `xhigh`.

```text
Start Phase 2 of the keelswell harness conversion. Phase 1 is merged;
the bmad-close-epic gate is now script-enforced.

Read docs/harness-conversion-plan.md, Phase 2. This session is Phase
2 only.

What Phase 2 is: wave records carry a lifecycle status in frontmatter,
and the wave skills route on that status instead of inferring state
from the conversation or the filesystem. The vocabulary comes from
BMAD's bmad-build-auto: draft enters at plan, ready-for-dev and
in-progress at implement, in-review at review, done runs a fresh
follow-up review pass, blocked halts. Adapt the names to keelswell's
wave stages if they differ, but define the vocabulary in exactly one
place and have every wave skill read it from there.

The part that makes this a control mechanism rather than a
convention: blocked is sticky. A blocked wave halts on every later
dispatch even after the cause is fixed. The only way to clear it is a
human deleting or editing the record. Enforce that the same way Phase
1 enforced closure: a script the skill calls, not prose asking the
agent to check.

Done means, demonstrated: (1) a wave record at each status resumes at
the correct stage, (2) a wave marked blocked halts on a second
dispatch after its underlying cause is fixed, (3) removing the
blocked status by hand lets it proceed. Show me all three.

Constraints:
- Fork-owned seams only: the wave skills and their scripts/
  subdirectories. The shared vocabulary file lives in one wave skill
  (or _bmad/custom/, which the installer never rewrites), never in
  _bmad/scripts/ (installer-owned; runbook class D). Do not touch
  agents/ or anything an upstream module declares.
- Existing in-flight wave records have no status field. Decide what
  a missing status means and tell me before implementing. Do not
  silently default it.
- Do not add stages. If a status seems to need a new stage, that is
  a finding to report, not a change to make.
- Match the script style from Phase 1 and the skill version-bump and
  CHANGELOG conventions.

Branch and PR as before. In the PR, include the prediction: what this
fixes, what it might break. Be specific about the migration risk for
existing waves.

Before writing anything: read the plan, read the wave skills and
Phase 1's script, then tell me your approach, how you will handle
records with no status, and the one thing you are least sure about.
Wait for my go-ahead.
```

## Phase 3: an evaluator that cannot edit

Opus 5, effort `xhigh`.

```text
Start Phase 3 of the keelswell harness conversion. Phases 1 and 2 are
merged; closure is script-enforced and wave status is a real state
machine.

Read docs/harness-conversion-plan.md, Phase 3. This session is Phase
3 only.

What Phase 3 is: the review that bmad-dev-wave runs today happens in
the same context that did the work, through the bmad-agent-qa persona.
Replace it with a fresh-context evaluator that is structurally unable
to edit. In Claude Code that means a subagent definition whose tools
list excludes Write and Edit, invoked as a separate process so its
context never saw the build. It returns PASS or NEEDS_WORK with
specific findings, and on NEEDS_WORK the findings become the opening
prompt of the next build session rather than being fixed in place.

Also adopt BMAD's stopping rule: if a third review pass on the same
wave still produces non-trivial findings, the evaluator should say so
explicitly and name the likely upstream cause (weak spec,
contradiction, ambiguous rule) instead of producing a fourth round of
findings.

Done means, demonstrated: (1) the evaluator definition contains no
Write or Edit tool and cannot be talked into editing, (2) a wave with
a planted defect gets NEEDS_WORK with the defect named, (3) the next
build session opens with those findings, (4) the third-pass rule
fires when exercised.

Constraints:
- The evaluator is fork-owned. Put it where keelswell owns it, not
  where an upstream module would collide with it. Check how
  bmad-agent-qa is declared before deciding, and tell me.
- Consider running the evaluator on a different model than the
  builder; the plan's evidence includes Cursor finding different
  models suit different roles. Propose one, with reasoning, but do not
  decide it for me.
- Do not remove bmad-agent-qa. It comes from upstream. Route around it.
- Do not add stages or agents beyond the one evaluator subagent.

Branch and PR as before, with the prediction. The regression I most
want named is: what happens to a wave that was mid-review under the
old persona when this lands.

Before writing anything: read the plan, read bmad-dev-wave and how
bmad-agent-qa is wired, then tell me your approach, your model
recommendation for the evaluator, and the one thing you are least
sure about. Wait for my go-ahead.
```

## Phase 4: conformance check in install.sh

Fable 5.1, effort `xhigh`.

```text
Start Phase 4 of the keelswell harness conversion. Phases 1 through 3
are merged.

Read docs/harness-conversion-plan.md, Phase 4. This session is Phase
4 only.

What Phase 4 is: install.sh already ends in a validation phase (phase
6). Extend it so that after an install, the enforcement layer from
Phases 1 to 3 is asserted to still be intact: the gate script exists
and is executable and wired into bmad-close-epic, the status
vocabulary file exists and every wave skill references it, the
evaluator subagent exists and has no Write or Edit tool. This is the
phase that protects the other three from an upstream refresh that
silently breaks them.

Done means, demonstrated: deliberately break one invariant, run the
install, and the install fails loudly naming which invariant failed.
Then repair it and the install passes. Do this for at least two
different invariants.

Constraints, and these matter more than in earlier phases:
- install.sh is reconstructed per the keelswell-manual repo (Manual
  Ch 34, App I.10/I.12/I.13). Read the relevant chapters before
  touching phase 6, and read docs/upstream-refresh-runbook.md for the
  incident that runbook exists because of. Do not repeat it.
- The --dry-run, --validate-only, and --validate-allowlist paths must
  keep working, and the new checks must run under --validate-only
  without requiring a fresh install.
- The installer already has an allowlist-validation concept. Extend
  the existing mechanism if it fits; do not build a parallel one.
- Do not change anything the upstream npx installer writes. Your
  checks read; they do not repair.

Branch and PR as before. The prediction I want is specific: which
upstream change would this catch, and which would it miss.

Before writing anything: read the plan, the runbook, the manual
chapters, and install.sh phases 1 to 6, then tell me your approach and
the one thing you are least sure about. Wait for my go-ahead.
```

## Phase 5: decide what is consumable

Opus 5, effort `high`.

Ran 2026-09-12, merged as PR #17. The prompt worked, but two of its
assumptions did not. It asked for an example "from a real wave", and
for most of the sixteen the usable evidence turned out to be
planning-phase party reviews with per-seat attribution, not waves. And
it framed Group 3 as agents nobody can name a failure for, when the
actual cause was that no wave skill calls any of them. That finding is
now Phase 6.

```text
Start Phase 5 of the keelswell harness conversion. Phases 1 through 4
are merged.

Read docs/harness-conversion-plan.md, Phase 5. This session produces
a document, not code changes. Do not delete, rename, or edit any
agent.

What Phase 5 is: an inventory of the 16 fork-only agents (the ones
module.yaml declares as keelswell's own, not the 22 that arrive from
BMM, CIS, TEA, or the architecture pack). For each one, answer a
single question: what specific failure does this agent prevent? Not
what it does; what goes wrong without it, concretely, with an example
from a real wave if one exists in _bmad-output or the git history.

Sort the result into three groups:
- Earns its place: a named failure it prevents, with evidence.
- Consumable: useful but its value is prompt-level and should be
  re-earned after each model release rather than assumed. Say what
  would need to be true after a model upgrade to keep it.
- No answer: nobody can name a failure it prevents. Do not recommend
  deletion. Recommend a way to find out, such as running one wave
  without it.

Write it to docs/agent-inventory.md, matching the conventions of the
other docs there. Include the date and the model generation it was
assessed against, because this inventory goes stale on every model
release by design.

Constraints:
- Read each agent file and the waves that used it. Do not assess from
  the name or the description alone.
- Where the evidence is thin, say so. A short honest entry beats a
  confident invented one.
- The plan's reasoning for this phase is in ../harness-wiki under
  concepts/scaffold-vs-weights.md and
  concepts/structure-transfers-prose-does-not.md. Read those two so
  the grouping criteria match the evidence.

Before writing the document: tell me which agents you expect to land
in each group and why, so I can correct your priors before you spend
the effort. Wait for my go-ahead.
```

## Phase 6: call the agents the wave needs

Five items. 6.1 ran 2026-09-12 and merged as PR #18; its prompt is not
kept, because it was a twenty-minute edit whose only surprise is
already recorded in the plan (there was no front matter to add to).

Order matters: **6.2 gates 6.3.** 6.3's trigger table is written
against role codes, and ffbapp still keys nine agents under persona
codes, so 6.3 shipped first is inert on the only instance that runs
waves. 6.5 is independent. 6.4 is blocked until something ships a user
interface.

### Phase 6.2: refresh ffbapp's nine stale agent codes

Fable 5.1, effort `xhigh`. Same reasoning as Phases 0 and 4: this
edits an installed tree rather than the fork, and its failure mode is
silent. A dropped roster entry does not error, it just means a seat
stops appearing in party mode and nobody notices for a month.

**Run this session from the ffbapp root, not keelswell.**

```text
Run item 6.2 of the keelswell harness conversion. Read
docs/harness-conversion-plan.md in ../keelswell first (Phase 6), then
docs/agent-inventory.md there, section "Party mode: all sixteen are
seated".

This session edits ffbapp's installed BMAD tree. It does not edit the
keelswell fork. Do not change any skill's behaviour; this is a rename
of nine agent codes and nothing else.

The problem: keelswell renamed nine custom agents from persona form to
role form in v0.5.0 on 2026-07-20 (agent-tam-althor -> agent-sre,
agent-tuon -> agent-growth, agent-setalle-anan -> agent-accessibility,
agent-hurin -> agent-analytics, agent-gareth-bryne -> agent-legal,
agent-damer-flinn -> agent-ml, agent-bayle-domon -> agent-billing,
agent-juilin-sandar -> agent-appsec, agent-jain-farstrider ->
agent-performance). ffbapp never refreshed. Its _bmad/config.toml and
its .claude/skills/ directories both still use the persona codes, so
they agree with each other and nothing is visibly broken today. But
item 6.3 builds a reviewer-selection table against role codes, and it
would silently match nothing here.

Before changing anything, record the baseline so the verification has
something to compare against:

  uv run .claude/skills/bmad-party-mode/scripts/resolve_party.py \
    --project-root . --skill .claude/skills/bmad-party-mode

Note the room size and which of the sixteen fork-only agents are
seated. It should be 38 and all 16.

Then find every place a persona code appears. At minimum:
_bmad/config.toml ([agents.*] table names), the .claude/skills/
directory names, _bmad/custom/module-help.csv, and anything under
_bmad/custom/. Search for all nine, do not assume that list is
complete, and report what you found before editing.

Follow ../keelswell/docs/upstream-refresh-runbook.md. This is the
surgical per-skill copy, not a full installer run. Do not run
`npx bmad-method install`: the runbook's class D says the installer
wipes and re-copies directories it owns, and this instance carries
local state that has not been reconciled with the fork in two months.

Verify, and paste the output:
1. resolve_party.py returns a room of 38 with all 16 fork-only agents
   seated, now under role codes.
2. No persona code survives anywhere: grep for all nine across the
   repo and show a clean result.
3. Activating one renamed skill still works. Pick agent-appsec (it is
   the one with a real activation on record) and confirm it resolves.

Do not touch _bmad-output/. The historical artifacts cite personas by
display name, which is unchanged; only the skill codes move.

Before touching anything: tell me which files you found the nine codes
in, whether any of them surprised you, and what you think is most
likely to break. Wait for my go-ahead.
```

### Phase 6.3: a reviewer-selection script

Opus 5, effort `xhigh`. Bounded and fully specified: the triggers are
already written. The judgment is in the table, not the code.

Run from the keelswell root. Requires 6.2 merged.

```text
Start item 6.3 of the keelswell harness conversion. 6.1 and 6.2 are
merged.

Read docs/harness-conversion-plan.md, Phase 6, item 6.3. Then read
docs/agent-inventory.md in full: every one of the sixteen entries ends
with a Trigger line, and those lines are the input to this work. Do
not re-derive them.

What to build: skills/bmad-dev-wave/scripts/select_reviewers.py plus a
YAML trigger table beside it. Given a wave's changed-file list (and
its spec where a trigger needs it), it prints the set of reviewers to
dispatch. Step 10 of bmad-dev-wave calls it instead of hardcoding
"security, cost, and platform".

The script is the point. A selection rule written as prose in the
SKILL.md sits in the layer that regresses when moved to another model;
the same logic as a script plus a table is dispatch, which transfers.
See ../harness-wiki/wiki/concepts/structure-transfers-prose-does-not.md
if you want the evidence. Put it under the skill's own scripts/
directory, the convention upstream already uses, so it travels with
the skill and survives a refresh. Not _bmad/scripts/: the installer
owns that and wipes it.

The rule the table encodes is necessity, not a budget. If eight
domains are genuinely in the diff, it returns eight. If one is, it
returns one. Do not add a cap, a maximum, or a "top N most relevant".
A cap means choosing which real gaps to skip looking for.

What keeps it affordable is trigger precision. Every trigger must be
answerable yes or no from the file list and spec without judgment. If
you find yourself writing a trigger that needs interpretation, the
trigger is wrong, not the rule.

The fixed three lose their exemption in the same change. Security,
cost and platform become entries in the table like everything else. A
wave touching no infrastructure should return no platform reviewer.

Also decide, and tell me your recommendation before implementing:
whether install.sh's harness_check should assert this script the way
it asserts wave_status.py and wave_gate.py. There is an argument both
ways and I want your read on it.

Housekeeping this repo expects, from the 6.1 commit as the model:
bump the skill version and add a version-history entry; mirror the
edit into .claude/skills/; add a CHANGELOG entry under [Unreleased];
mark 6.3 done in the plan. Run `bash install.sh --validate-only` and
paste the harness-invariant block.

Verify with real data, not invented examples: ffbapp has eighteen
waves under ../ffbapp/docs/wave-*/. Run the selector against several
of their actual changed-file lists and show what it returns. Wave 4A
and 4B landed model work and should pull agent-ml. Waves that touched
no infrastructure should not pull a platform reviewer.

Before writing code: state your approach, show me the trigger table's
shape for three agents, and name your biggest uncertainty. Wait for my
go-ahead.
```

### Phase 6.4: one ablation wave for the three unanswered agents

No separate session. This rides the first wave that ships a rendered
surface, so keep it here until that wave exists and then paste it into
that wave's kickoff.

```text
This wave also runs item 6.4 of the keelswell harness conversion. Read
docs/agent-inventory.md, Group 3, in ../keelswell.

agent-web-designer and agent-design-critic have never been activated.
This is the first wave with a surface they could act on, so it is the
experiment.

At the build step, dispatch agent-web-designer and let it run its own
five-step verification loop (browser at 375, 768 and 1280, each in
light and dark, screenshot and read rather than assume the CSS
worked). That loop is the only real structure in the custom slate and
it has never run once.

Then dispatch agent-design-critic against the result, and record its
defect list separately.

The question this answers: does the critic's list contain anything the
builder's own verification pass already caught? Record the overlap
explicitly in the wave's review record. If the lists are effectively
the same, the independence claim buys nothing and one of the two is
enough. If they diverge, both earn their place and the inventory moves
them out of Group 3.

Do not merge the two dispatches into one agent to save a turn. The
separation is the experiment.
```

### Phase 6.5: collapse the eight duplicate agent files

Opus 5, effort `high`. Mechanical, but the installer reads `agents/`
for the roster, so the verification matters more than the edit.

Run from the keelswell root. Independent of 6.2 and 6.3.

```text
Run item 6.5 of the keelswell harness conversion. Read
docs/harness-conversion-plan.md, Phase 6, item 6.5.

Eight files under agents/ are byte-identical to their
skills/agent-*/SKILL.md: accessibility, analytics, design-critic,
growth, legal, ml, sre, web-designer. Confirm that yourself before
acting; do not take my word for it.

The other seven custom agents use a better pattern already: agents/ carries
a short persona descriptor and the skill carries the procedure.
Compare agents/custom-appsec.md against skills/agent-appsec/SKILL.md
to see the shape. Convert the eight to match it.

This is maintenance on the consumable layer, which this plan says not
to invest in, so keep it strictly mechanical. Do not improve the
prose, do not rewrite a capability menu, do not fix anything you
notice in passing. Mention what you noticed instead.

The risk is the installer. It reads agents/ to build the roster, so
verify the roster is unchanged rather than assuming:
1. Count [agents.*] tables produced by a fresh `--target-project`
   install before and after. They must match, and the count must be
   asserted, not eyeballed.
2. resolve_party.py on the target returns the same room size and the
   same sixteen fork-only agents.
3. `bash install.sh --validate-only` passes both trees.

Housekeeping: bump nothing (no skill behaviour changes), but add a
CHANGELOG entry under [Unreleased], mirror anything that needs
mirroring into .claude/skills/, and mark 6.5 done in the plan.

Before editing: show me the diff you intend for one of the eight and
name what you think the installer will do with it. Wait for my
go-ahead.
```

## Harness review v1: the five do-now items

`docs/reviews/harness-engineering-review-v1.md` (2026-09-27) ranked five
structural items, R1 to R5, one pull request each, every item's session
grading the previous item's prediction. R1 ran on 2026-09-28 from a
five-item kickoff prompt RQ wrote by hand (not reproduced here) and is
rlquigley/keelswell#23. From R2 on, each item gets its own prompt below,
written by the session that finished the item before it, so the rulings
and the prediction to grade travel with it.

### R2: permission-layer backing for the merge halt and the blocked record

Fable 5.1, effort `high`. Two hours of configuration plus a live check;
the failure mode is a rule that looks right and never fires, so the
verify step is the work.

Run from the keelswell root. Requires #23 merged.

```text
You are implementing R2 of the Keelswell harness-engineering review, the
second of five "do now" items, one pull request per item. R1 is open as
rlquigley/keelswell#23 (branch claude/r1-gate-fails-closed); confirm it has
merged before you branch, and branch from that main. The review is
approved; do not re-plan it. Read these first, in order:

1. docs/reviews/harness-engineering-review-v1.md, sections 1, 4 and 5
   (the verdict, R1 to R10, the roadmap rulings). R2 is the item.
2. docs/reviews/harness-review-v1-appendix-b.md: rows 2.6, 4.1 to 4.7, 5.1,
   5.2, 6.1 to 6.3, 3.6 and "Definitive answers" 7 and 9. Every Claude Code
   fact you rely on comes from there or from https://code.claude.com/docs;
   verify against the docs before building on any row marked "not
   runtime-verified". A docs mirror from 2026-09-28 may still sit in the
   previous session's scratchpad; fetch fresh if not.
3. docs/reviews/harness-review-v1-appendix-f.md, section 3 (the ffbapp
   census: five unrequested `git reset --hard`, two via `git -C`) and the
   E2a fixture (40 destructive-command strings, verbatim near the end).
4. docs/harness-conversion-plan.md ("What tracking upstream constrains", the
   three seams) and docs/upstream-refresh-runbook.md.
5. The CHANGELOG [Unreleased] entry R1 wrote (top of the file): it carries
   the prediction you grade first.
6. The Keelswell auto-memory index at
   ~/.claude/projects/-Users-ryanquigley-Projects-personal-keelswell/memory/MEMORY.md,
   then keelswell-hook-writes-blocked, git-stage-explicitly-not-add-all,
   keelswell-push-needs-sandbox-off, keelswell-project-structure.

Your first message: your approach in five lines at most, your biggest
uncertainty, R1's prediction restated with how you will grade it, and the
four rulings below restated as you understand them. Then wait for RQ's go.

Rulings already made (2026-09-28), restate them, do not reopen them:
(a) templates/settings.json.template is a fork-owned seam, the whole file,
    not permission rules only.
(b) Keep bypass banned mechanically: permissions.disableBypassPermissionsMode
    "disable" in the template. Drop the auto ban: no disableAutoMode; remove
    forbidden_modes from core/config.yaml with a CHANGELOG line. Deny and
    ask rules are the hard layer in acceptEdits and auto alike.
(c) (R5's fixture location; not yours.)

One new ruling to confirm before touching anything (proposed default in
brackets; RQ decides):
(d) The review's list has deny Edit(.bmad/**). That form also denies the
    Write tool writing .bmad/wave-<id>/checkpoint.json, step-N.done and
    step-4.5.pending, which dev-wave writes with whichever tool the agent
    picks (SKILL.md names no tool). R1's lifecycle hook rule already guards
    exactly .bmad/wave-<id>/wave.md. [Narrow the rule to
    Edit(.bmad/**/wave.md); keep the markers unguarded at the permission
    layer.]

Grade R1's prediction first, before building. It said: every path that let a
guarded call through without a decision now returns one; a matched call
costs 74 ms p50 against 48; at risk were a broken gate blocking a session
until a human repairs it, legitimate `wave_status.py set` calls written
through eval or python3 -c being refused, `evaluate_wave.py record` fed by
a here-document that names wave_status and set being refused, and any
non-read command naming .bmad/wave-<id>/wave.md being refused; not covered
were a script file written earlier and run later, and a renamed copy of
wave_status.py. Grade it by re-running the E2b replay on merged main
(skills/bmad-dev-wave/scripts/tests/test_wave_gate.py, TestE2bReplay),
timing 20 matched calls, and reporting whether any at-risk case was hit in
your own session's tool calls once the scratch instance runs under the
hooks. Write the grade into the R2 CHANGELOG entry and the PR body.

Standing rules, all from the fork's own record:
- Work only in the fork-owned seams: the wave skills, skill-local scripts/,
  install.sh phase 6, .claude/hooks and .claude/agents, plus
  templates/settings.json.template per (a). R2's own list also names
  core/config.yaml and the runbook; that list is the grant for those two.
  Never _bmad/scripts/, never agents/, never an upstream-declared skill body.
- Every change ships a predicted impact with at-risk regressions, in the
  CHANGELOG [Unreleased] entry and the PR body; R3's session checks it.
- Bump the version of every skill you change; mirror skills/ into
  .claude/skills/ (diff -rq -x __pycache__ per skill must be empty); run the
  unit tests in both trees (baseline after R1: 166 in bmad-dev-wave, 12 in
  bmad-close-epic, both trees) and `./install.sh --validate-only
  --skip-mcp-check` before every commit. Stage files by name, never git add
  -A, and re-check the staged list against the commit message. The
  gitleaks pre-commit hook runs; never bypass it.
- Prose is ASCII with " -- " dashes. No em dashes anywhere.
- Hook and settings files: prepare the exact content, then let the
  permission prompt decide; R1's session was allowed to write both the
  wrapper and the template registration, so try once. If a write is
  refused, print the file contents and the path for RQ to apply by hand,
  and carry on.
- Do not add a stage, do not add a domain persona, do not build anything
  that edits the harness on its own. R2 adds no hook rule: if the check
  needs one (for the `git -C` and `bash -c` forms text rules miss, appendix
  B row 4.3), that is a stop-and-ask, not a workaround.
- Git: `git fetch`/`git push` failing with "signing failed ...
  communication with agent failed" means 1Password is locked, not a
  sandbox block; ask RQ to unlock and retry. The review docs under
  docs/reviews/ may still be untracked; never stage them.
- RQ merges and tags by hand. Halt after the PR is open and report: what
  changed, the prediction, R1's grade, what R3 needs from the merge.

R2. Permission-layer backing for the merge halt and the blocked record
(templates/settings.json.template; core/config.yaml; a hand step for the
two live instances recorded in the CHANGELOG and
docs/upstream-refresh-runbook.md).
Build: deny Bash(gh pr merge *), Bash(git push --force *),
Bash(git push -f *), Bash(git reset --hard *), Bash(git clean -f*),
Edit(**/docs/wave-*/evaluation-*.md), and per (d) the .bmad rule; ask
Bash(git push *), Bash(git branch -D *), Bash(git worktree remove *),
Bash(gh auth token*); permissions.disableBypassPermissionsMode "disable";
per (b) remove forbidden_modes from core/config.yaml with a CHANGELOG line.
Keep every wave_gate.py rule: Edit deny rules cover the tool, sed, tee and
redirect forms, not evaluate_wave.py's own file I/O, which is the one
legitimate writer (row 4.4). Rule order is deny, then ask, then allow;
first match wins (row 4.1). Note row 4.3's limits (`git -C . push`,
`bash -c`, /bin/rm are not matched) in the at-risk list, and that dev-wave
step 11's push and merge-wave's `worktree remove` and `branch -D` now
prompt on every wave, which is the intended cost.
Verify: `./install.sh --target-project <scratch dir> ...` produces a
settings.json that a fresh `claude` session honours: `gh pr merge` is
denied, `git push` prompts, a Write to .bmad/wave-1/wave.md is denied,
`python3 .claude/skills/bmad-dev-wave/scripts/evaluate_wave.py record`
still writes. Caveat for the headless route: in `claude -p` a permission
request that no hook decides is denied, so "prompts" shows as a denial
there; the interactive prompt is RQ's to observe, or use
--permission-prompt-tool if the docs support it on the installed CLI. On
2026-09-28 `claude -p` on this machine failed with "OAuth session expired"
and the CLI was 2.1.252 against docs for 2.1.283; RQ was asked to run
/login and `claude update` before this session. If the session still
cannot authenticate, unit-test the resolved settings.json (valid JSON,
every rule present, hooks block unchanged from R1) and hand RQ the live
check as exact commands. Record the hand step for ffbapp and green-ledger
(their settings.json is hooks-only, registered by bare relative path; they
also need R1's wrapper, the three scripts, and the exec-form registration)
in the CHANGELOG and the runbook.

What R3 will need from your merge: the permission block's final shape,
since R3's SubagentStop hook and its "record only through the hook" gate
rule sit beside it, and the scratch instance you built, which R3 reuses for
its hook-written-record check.
```

### R3: the evaluator's dispatch, evidence and record become script work

Fable 5.1, effort `high`. One day. The failure mode is a record that
looks hook-written and was not, so the live dispatch in the scratch
instance is the check; the unit tests only say the hook would write.

Run from the keelswell root. Requires #24 and #25 merged (both landed
2026-10-01; main 528d344).

```text
You are implementing R3 of the Keelswell harness-engineering review, the
third of five "do now" items, one pull request per item. R2 is merged as
rlquigley/keelswell#24 and the R1 parser fix as #25 (main 528d344,
bmad-dev-wave 1.8.2); confirm both are in main before you branch, and
branch from that main. The review is approved; do not re-plan it. Read
these first, in order:

1. docs/reviews/harness-engineering-review-v1.md, sections 1, 4 and 5. R3 is
   the item; its parts (a) to (e) are the build list below.
2. docs/reviews/harness-review-v1-appendix-b.md: rows 1.13, 1.14, 2.2, 2.5,
   3.5, 3.6, 8.1 to 8.5, 9.3, 19.1, 19.2 and "Definitive answers" 1, 7, 8
   and 9. Then the raw docs, never a summary: `curl -sL
   https://code.claude.com/docs/en/hooks.md` and read "SubagentStop", "Stop
   decision control" and "Common input fields"; sub-agents.md for `effort`
   and SubagentHandback. Row 1.14 predates one fact that changes the
   design: on CLI 2.1.271 and later a subagent that runs with the
   SubagentHandback tool (added in auto mode whatever its tool list says)
   delivers its report through that tool, and `last_assistant_message` then
   holds only its closing text. The report is the tool call's `message`
   input, which a PreToolUse or PostToolUse hook matched on SubagentHandback
   sees. WebFetch summaries of these pages have been wrong before (a
   Boolean where the page says the string "disable"); grep the markdown.
3. skills/bmad-dev-wave/SKILL.md, "The Evaluator" and "The Hooks";
   scripts/evaluate_wave.py (`dispatch`, `record`, `opening-prompt`,
   `read_verdict`); scripts/wave_gate.py (`verdict_rule`,
   `note_recording_session`, `in_place_rule`);
   .claude/agents/keelswell-wave-evaluator.md (its severity ladder and the
   `### [SEVERITY] <title>` and `VERDICT:` formats are what (c) parses).
4. docs/harness-conversion-plan.md ("What tracking upstream constrains")
   and docs/upstream-refresh-runbook.md, whose last section is the instance
   hand step you extend.
5. The CHANGELOG [Unreleased] entries R2 wrote: the Added entry at the top
   carries R2's prediction and the Fixed entry for 1.8.2 the parser's; you
   grade both first.
6. The auto-memory index at
   ~/.claude/projects/-Users-ryanquigley-Projects-personal-keelswell/memory/MEMORY.md,
   then keelswell-harness-review-v1, keelswell-hook-writes-blocked,
   git-stage-explicitly-not-add-all, keelswell-push-needs-sandbox-off,
   claude-docs-raw-markdown, rq-adhd-communication.

Your first message: your approach in five lines at most, your biggest
uncertainty, R2's prediction restated with how you will grade it, and the
rulings below restated as you understand them. Then wait for RQ's go. When
a ruling needs RQ, write the plain story of the choice first, then the
options with the recommended one first; RQ answered R2's two that way
inside a minute.

Rulings already made, restate them, do not reopen them:
(a) 2026-09-28: templates/settings.json.template is a fork-owned seam, the
    whole file. Your hook registrations go there, beside R1's PreToolUse
    entry and R2's permission block. test_settings_template.py pins the
    PreToolUse entry exactly and only requires wave-session-end.sh under
    SessionEnd, so new events beside them break nothing. Do not change the
    PreToolUse entry.
(b) 2026-09-28: deny and ask rules are the hard layer in acceptEdits and
    auto alike; bypass is locked by the template. install.sh phase 6 makes
    every deny and ask rule in the template required in every instance, so
    a rule you add there is one the hand step must carry.
(c) 2026-10-01: the lifecycle Edit rule locks `.bmad/**/wave.md` only, and
    dev-wave's step markers stay writable at the permission layer. Both
    Edit rules carry a leading slash (project-root anchor); any new Edit
    rule is written the same way.
(d) 2026-10-01: a hook rule on R1's parser for the `git -C` and `bash -c`
    forms the text rules miss is not R3's. It is a sixth do-now item for RQ
    to schedule: name it in your report, do not build it.

Three new rulings to confirm before touching anything (proposed default in
brackets; RQ decides):
(e) How the hook knows which wave a finished evaluator graded. SubagentStop
    carries agent_type, agent_id, agent_transcript_path and
    last_assistant_message, not the wave. [`dispatch` writes
    .bmad/wave-<id>/evaluation-pending holding the session id and the pass
    number before the Agent call; the hook reads the one pending marker
    whose session id matches, records to that wave, and deletes the marker.
    No marker: the hook writes nothing and prints why to stderr. This is
    the shape note_recording_session already uses for in-place.]
(f) The Bash route to `record`. [Retired: a new wave_gate rule, "record",
    denies any Bash or Monitor command that calls evaluate_wave.py record,
    naming the hook as the one writer; the hook calls the Python function
    directly, and also writes the evaluation-session marker that
    note_recording_session wrote, or in-place goes blind. The `< file` form
    R1 kept goes with it, and "The Evaluator" in SKILL.md changes to match.]
(g) Where the verify command comes from. dev-wave step 9 names
    tests/verify-fast.sh in the worktree and nothing else does. [Run
    tests/verify-fast.sh from the worktree root when it exists, else exit 3
    naming the missing script. No new config key. verify-output.txt's first
    line is a stamp: command, exit code, HEAD SHA, UTC time.]

Grade R2's prediction first, before building. It said: in an instance that
carries the block, `gh pr merge` is refused in every mode; a plain
`git push`, `git branch -D`, `git worktree remove` and `gh auth token`
prompt in every mode, auto included; the Write and Edit tools, `sed -i`,
`tee` and a redirect cannot change a lifecycle or evaluation record under
the project root with every hook off; bypassPermissions cannot be entered.
At risk were the forms text rules miss (`git -C`, `git -c`, `bash -c`, an
absolute-path binary, a quoted word, a force flag after the remote),
headless prompts becoming denials, `--dangerously-skip-permissions`
rejected inside an instance, the Edit rules stopping at the project root,
no `rm -rf` rule, and validation exiting 7 on the instances until the hand
step. The 1.8.2 entry predicted that every newline now splits a command as
`;` does, the only other parse change being an empty command dropped
between two operators. Grade them by: (1) the scratch instance's live check
again on the current CLI (script and instance paths below; the instance is
a git repo with wave 1A in-progress and two PASS records; rebuild steps are
in the #24 body), plus two calls it lacks: `claude -p --permission-mode
auto` asked to run `git push`, which must appear in permission_denials, and
`claude -p --dangerously-skip-permissions` on anything, which must be
rejected; (2) the interactive prompt, which only RQ can observe: ask once,
with the exact command; (3) your own session: every prompt or denial you
meet while working in the scratch instance under the block, and any guarded
form that went through unmatched, counted and named; (4) for 1.8.2,
TestNewline and TestE2bReplay on merged main, and whether any two-line
command of your own was refused for its newline. Write both grades into the
R3 CHANGELOG entry and the PR body.

Standing rules, all from the fork's own record:
- Work only in the fork-owned seams: the wave skills, skill-local scripts/,
  install.sh phase 6, .claude/hooks and .claude/agents, plus
  templates/settings.json.template per (a) and the runbook's instance
  section. Never _bmad/scripts/, never agents/, never an upstream-declared
  skill body.
- Every change ships a predicted impact with at-risk regressions, in the
  CHANGELOG [Unreleased] entry and the PR body; R4's session checks it.
- Bump the version of every skill you change (bmad-dev-wave is 1.8.2; this
  is a minor bump); mirror skills/ into .claude/skills/ (diff -rq -x
  __pycache__ per skill must be empty); run the unit tests in both trees
  (baseline: 176 in bmad-dev-wave, 12 in bmad-close-epic, both trees) and
  `./install.sh --validate-only --skip-mcp-check` before every commit.
  Stage files by name, never git add -A, and re-check the staged list
  against the commit message. The gitleaks pre-commit hook runs; never
  bypass it. A fresh --target-project instance cannot make its first commit
  without the fork's .gitleaks.toml copied in (a vendored TEA fixture trips
  the hook); that defect is a separate chip, not yours.
- Prose is ASCII with " -- " dashes. No em dashes anywhere.
- Hook and settings files: prepare the exact content, then let the
  permission prompt decide. R1 and R2 were both allowed to write the
  wrapper, the registration and the permission block on the first try, so
  try once; if refused, print the content and the path for RQ and carry on.
- Do not add a stage, do not add a domain persona, do not build anything
  that edits the harness on its own. R3 adds two hook registrations
  (SubagentStop on keelswell-wave-evaluator; PostToolUse on
  SubagentHandback) and one gate rule ("record"); nothing else at the hook
  layer, per (d).
- Git: `git fetch`/`git push` failing with "signing failed ...
  communication with agent failed" means 1Password is locked; ask RQ to
  unlock and retry. The review docs under docs/reviews/ are untracked;
  never stage them.
- RQ merges and tags by hand. Halt after the PR is open and report: what
  changed, the prediction, R2's and 1.8.2's grades, what R4 needs from the
  merge.

R3. Make the evaluator's dispatch, evidence and record provenance script
work, not prose (skills/bmad-dev-wave/{SKILL.md, scripts/evaluate_wave.py,
scripts/wave_gate.py, scripts/tests/}; a new wrapper under .claude/hooks/;
.claude/agents/keelswell-wave-evaluator.md; templates/settings.json.template
for the registrations; install.sh phase 6 for the new wrapper in
hooks_check; the runbook's instance section; CHANGELOG).
Build, in the review's order:
(a) A SubagentStop hook, matcher `keelswell-wave-evaluator`, exec form on
    ${CLAUDE_PROJECT_DIR} with a timeout, whose wrapper calls a new
    evaluate_wave.py entry point with the event JSON on stdin. It takes
    the report from last_assistant_message, resolves the wave per (e), and
    writes evaluation-<n>.md through the function `record` uses today, so
    the header, the pass count, the third-pass rule and the exit semantics
    are unchanged except that the header names the hook as the writer. No
    readable VERDICT line: return `decision: "block"` with a reason telling
    the evaluator to end with exactly one `VERDICT: PASS | NEEDS_WORK |
    UPSTREAM_CAUSE` line; the docs say that keeps the subagent running with
    the reason as its next instruction; cap it at two rounds, then write
    nothing and say so on stderr. Per the 2.1.271 fact above, also register
    a PostToolUse hook on SubagentHandback (same wrapper, same entry point)
    that records the call's `message` input when the agent is the
    evaluator, and make the two paths idempotent on one pass number:
    whichever arrives first records, the other sees the record and exits
    0. Measure the report size each path receives in the scratch instance;
    the 10,000-character cap is documented for additionalContext, not for
    these fields, and "confirm" was the review's word.
(b) A `verify` subcommand per (g). `dispatch` writes wave-diff.patch from
    the recorded base (the wave branch's merge-base with main, read from
    git, never from the agent) and exits 3 when verify-output.txt is
    missing or its stamped HEAD SHA is not the worktree's HEAD, in place of
    today's notice. The two files stay where they are.
(c) A parser over `### [SEVERITY]` headings: a PASS that carries a MEDIUM,
    HIGH or CRITICAL heading is refused through the same block channel as
    a missing VERDICT line, and a record with two `VERDICT:` lines is
    refused. The severities are the definition's own ladder; read them
    from it, do not retype them.
(d) `effort: high` in the evaluator's frontmatter, asserted by `check` so
    an instance whose definition drops it fails validation. Never add
    `memory:` to that file: it auto-enables Write and Edit (B row 8.2).
(e) The three loop defects: `dispatch` refuses (exit 3) without
    verify-output.txt; dev-wave's steps are renumbered so verify precedes
    evaluation (step 9 runs after step 7 today while step 7's evidence
    bundle needs step 9's output; the SKILL.md and evaluator-definition
    text changes describe an order the script now enforces); the pass
    counter resets after an UPSTREAM_CAUSE fix, counted from a
    wave_status.py-written history line in wave.md that names the fixed
    artifact (add a `--reason` for in-progress if `set` lacks one); and a
    step-10 HIGH or CRITICAL fix routes back through verify and the
    evaluator, which is a SKILL.md text change plus `dispatch` comparing
    the review record's date with the latest evaluation's.
The "record" rule per (f) sits in wave_gate.py beside the five existing
rules and is tested as they are (TestVerdict, TestE2bReplay and
TestNewline are the models). Keep every existing rule.
Verify: in the scratch instance, `claude -p` with the project settings
dispatches the evaluator against wave 1A after `verify` and `dispatch`
have written the evidence bundle; afterwards docs/wave-1a/ holds a new
evaluation record written by the hook, its header naming the hook, and no
`record` Bash call appears in the run's permission_denials or transcript.
Then the refusals: a report with no VERDICT line ends in a block reason and
a second attempt; a PASS carrying a HIGH heading is refused;
`evaluate_wave.py record` from Bash is denied by the gate. If `claude -p`
cannot authenticate, unit-test the entry point on recorded event JSON (two
fixtures from a real run, one per path, kept under scripts/tests/) and
hand RQ the live check as exact commands. Extend the runbook's instance
section with the new registrations and the new wrapper, and say in the
CHANGELOG what the instances need: ffbapp and green-ledger carry R1 + R2
as of 2026-10-01 (attacktheseam/ffbapp#101; green-ledger ff-only).

What R4 will need from your merge: the evaluator's final frontmatter (R4
binds model and effort for the other roles beside it), the hooks block's
final shape (R4 deletes the dead template keys around it), and the scratch
instance with its hook-written record.

Paths from R2's session (the scratchpad persists for days, not forever;
rebuild from the #24 body if it is gone):
  instance:   /private/tmp/claude-501/-Users-ryanquigley-Projects-personal-keelswell/b0fc3f65-f667-4532-a7e2-55495a0d0723/scratchpad/keelswell-r2-scratch
  live check: /private/tmp/claude-501/-Users-ryanquigley-Projects-personal-keelswell/b0fc3f65-f667-4532-a7e2-55495a0d0723/scratchpad/live-check.sh
```

### R4: delete the configuration that configures nothing, bind what should

Fable 5.1, effort `high`. Half a day. The failure mode is the one R4 exists
to remove: a setting that looks bound and binds nothing. So every key kept
or added is checked from what the runtime reports (a hook event's
`effort.level`, the run's `modelUsage`), never from the file.

Run from the keelswell root. Requires #27 merged (landed 2026-10-01; main
c068c48).

```text
You are implementing R4 of the Keelswell harness-engineering review, the
fourth of five "do now" items, one pull request per item. R3 is merged as
rlquigley/keelswell#27 (main c068c48, bmad-dev-wave 1.9.0); confirm it is in
main before you branch, and branch from that main. The review is approved;
do not re-plan it. Read these first, in order:

1. docs/reviews/harness-engineering-review-v1.md, sections 1, 4 and 5. R4 is
   the item; its "What" is the build list below. Section 5's rows for
   roadmap R2, R3 and "Batch 3 explicit model:" are the rulings it carries.
2. docs/reviews/harness-review-v1-appendix-b.md: rows 4.1, 7.1 to 7.11, 8.1
   to 8.5, 9.1, 9.2, 10.1, 11.2, 15.1, 16.1, 16.2, 17.1, 17.2 and
   "Definitive answers" 1, 4 and 5. Then the raw docs, never a summary:
   `curl -sL https://code.claude.com/docs/en/<page>.md` for
   settings-reference (effortLevel, model), sub-agents ("Supported
   frontmatter fields", "Choose a model"), skills ("Frontmatter reference")
   and model-config (aliases, effort levels). The appendix is dated
   2026-09-27 and model names have moved since: on 2026-10-01 the `sonnet`
   alias resolved to claude-sonnet-5-5 on CLI 2.1.287, where the appendix
   says Sonnet 5. Quote the page for every value you write into a file.
3. templates/settings.json.template; install.sh lines 176 to 226 (the
   resolver that fills MODEL_* and REASONING_*, and the memory directory it
   creates); core/config.yaml; the frontmatter of the seven wave skills
   (bmad-create-wave, -dev-wave, -merge-wave, -resume-wave, -status-wave,
   bmad-close-epic, bmad-wrap); .claude/agents/keelswell-wave-evaluator.md;
   and in skills/bmad-dev-wave/SKILL.md steps 3, 6 and 10, "The Reviewer
   Selection" and "The Review Record", which are the dispatches R4 binds.
4. docs/harness-conversion-plan.md ("What tracking upstream constrains") and
   docs/upstream-refresh-runbook.md: "Current state" is what the record says
   about `.agents/`, and the last section is the instance hand step you
   extend.
5. The CHANGELOG [Unreleased] entry R3 wrote (top of the file): it carries
   the prediction you grade first.
6. The auto-memory index at
   ~/.claude/projects/-Users-ryanquigley-Projects-personal-keelswell/memory/MEMORY.md,
   then keelswell-harness-review-v1, claude-code-subagent-report-hooks,
   keelswell-instance-updates, keelswell-hook-writes-blocked,
   git-stage-explicitly-not-add-all, keelswell-push-needs-sandbox-off,
   claude-docs-raw-markdown, rq-adhd-communication.

Your first message: your approach in five lines at most, your biggest
uncertainty, R3's prediction restated with how you will grade it, and the
rulings below restated as you understand them. Then wait for RQ's go. When a
ruling needs RQ, write the plain story of the choice first, then the options
with the recommended one first, one question at a time; RQ answered R3's
four that way inside a minute each.

Rulings already made, restate them, do not reopen them:
(a) 2026-09-28: templates/settings.json.template is a fork-owned seam, the
    whole file. R4 deletes keys around the `permissions` and `hooks` blocks
    and changes neither. test_settings_template.py pins R1's PreToolUse
    entry as the first, the evaluator hook's three entries exactly, every
    deny and ask rule, the bypass lock and `defaultMode: acceptEdits`.
(b) 2026-09-28: bypass is locked by the template and there is no auto ban;
    `disableAutoMode` stays out. Deny and ask rules are the hard layer in
    every mode.
(c) 2026-10-01: the evaluator's record is hook-written on three events and
    `evaluate_wave.py record` is denied to Bash. `check` refuses an
    evaluator definition that lacks `effort: high`, sets `memory:`, declares
    a tool that can write, or no longer states its severity ladder. Whatever
    R4 does to agent frontmatter leaves all four true of that file.
(d) 2026-10-01: the hook rule for the `git -C` and `bash -c` forms the
    permission rules miss is a sixth do-now item, still unscheduled. Name it
    in your report, do not build it.
(e) The review, approved 2026-09-28: R4 touches "do not add agents" by the
    letter and not the rationale. The definitions it adds are role files for
    dispatches dev-wave already makes, not domain personas: no roster entry,
    no module.yaml line, nothing under agents/. Say so in the CHANGELOG.

Four new rulings to confirm before touching anything (proposed default in
brackets; RQ decides):
(f) The seven dead template keys. reasoningEffort, contextWindow,
    subagentModels, subagentReasoning, skillsPaths, agentNamesFile and
    mcpServers configure nothing (B rows 7.2 to 7.7). [Delete six. Rename
    reasoningEffort to effortLevel, still filled from the orchestrator role,
    since that is the key it was always meant to be; it sets the session's
    effort in a fresh instance. Delete the resolver's substitutions that no
    longer have a placeholder. Live instances carry `hooks` and
    `permissions` only (measured 2026-10-01), so none of this reaches them.]
(g) Which dispatches get a definition, and how the tier table reaches them.
    Dev-wave dispatches subagents at step 3 (test design, a QA persona),
    step 6 (one coder per story) and step 10 (the reviewers
    select_reviewers.py returns as persona skills, or the fallback's plain
    subagents). [Two files, .claude/agents/keelswell-wave-coder.md and
    keelswell-wave-reviewer.md, each with `model:` and `effort:` written
    literally, dispatched by subagent_type at steps 6 and 10. A reviewer's
    persona stays the `skill` the selector returned, named in its dispatch
    prompt. Step 3 is left alone. No generator: core/config.yaml shrinks to
    the tier table, and install.sh phase 6 asserts that each definition's
    `model:` and `effort:` equal the table's, reading and never repairing,
    as it does for every other invariant. The evaluator's `model:` joins the
    assertion.]
(h) What the table pins. core/config.yaml names claude-opus-4-8 and
    claude-sonnet-4-6, both legacy, and claude-haiku-4-5, whose retirement
    was "not sooner than October 15, 2026" on 2026-09-27. An alias (`opus`,
    `sonnet`) follows releases without an edit, and resolves to the
    session's own model when the session is in the same family. A full id
    makes verdicts comparable and must be re-pinned per release. [Full ids
    for the coder and the reviewer, re-pinned per release with a CHANGELOG
    line, which is what docs/agent-inventory.md already expects of agent
    value; the evaluator moves from `opus` to the same full id as the
    reviewer. Drop the `fast` tier if nothing binds to it.]
(i) `.agents/skills`. Claude Code never reads it (B row 17.1). The fork
    tracks 74 directories there, 1,051 files, a frozen pre-v0.3.0 snapshot.
    green-ledger carries one of its own, tracked, and ffbapp an untracked
    one (measured 2026-10-01). Deleting the fork's is the one destructive
    step in R4. [Delete the fork's tree in its own commit, rewrite the
    runbook's "Current state" section to match, and leave every instance's
    alone. Whatever this ruling says, stop and get RQ's explicit yes
    immediately before the `git rm`, naming the file count.]

Grade R3's prediction first, before building. It said: in an instance that
carries the three registrations, every evaluation record written from then
on has the hook's header and none is written by a session; `evaluate_wave.py
record` from Bash or Monitor is refused; a report with no verdict, two, or a
PASS above LOW never reaches disk; the evaluator runs at effort high
whatever the session's is; `dispatch` refuses evidence that `verify` did not
stamp at the worktree's HEAD; one evaluation costs one evaluator run plus at
most two sent-back rounds, and about 40 ms of hook time per event. At risk
were: the dispatch prompt still being the builder's; a pending marker a
session can write; `record` fed a forged event where the gate is not
registered; a stamp that reads HEAD and misses an uncommitted edit; false
refusals (a quoted `VERDICT:` at the start of a line; a command naming
evaluate_wave with the bare word record, 4 of that session's 66 calls, and 2
more by the review rule); failing toward no record; a project with no
tests/verify-fast.sh; a wave paused between the old steps 7 and 10; a parent
that does not wait for a background evaluator; and a sent-back hand-over
counting toward auto mode's pause. Grade it by: (1) the live check again on
the current CLI (script and instance below; the instance holds five
NEEDS_WORK records for wave 1A, so the next dispatch is pass 6 with the
third-pass rule armed, which the checks do not depend on), with a Sonnet or
Opus parent and never Haiku, which cannot run auto mode; (2) the instances:
on 2026-10-01 ffbapp and green-ledger were at 1.8.2 and validation exited 7
naming the R3 hand step. Ask RQ once whether it has been applied and whether
a wave has run under the hooks. If one has, read its evaluation records'
headers and its transcript for a `record` call: that is the first grade any
of R1 to R3 gets from a real wave; (3) your own session: replay your Bash,
Write and Edit calls through the gate (replay_session.py, below) and count
what the record and review rules would have refused, against R3's 4 and 2 of
66; (4) effort, from the evaluator's hook events in (1): `effort.level` must
read high in both modes. Write the grade into the R4 CHANGELOG entry and the
PR body.

Standing rules, all from the fork's own record:
- Work only where R4's list reaches: templates/settings.json.template,
  install.sh (the resolver, the memory path and phase 6), core/config.yaml,
  the seven wave skills' frontmatter and dev-wave's dispatch text,
  .claude/agents/, the runbook, and `.agents/skills` per (i). That list is
  the grant for what sits outside the plan's three seams. Never
  _bmad/scripts/, never agents/, never an upstream-declared skill body:
  bmad-retrospective's frontmatter is name and description only and stays as
  it is.
- Every change ships a predicted impact with at-risk regressions, in the
  CHANGELOG [Unreleased] entry and the PR body; R5's session checks it.
- Bump the version of every skill you change. `version:` moves under
  `metadata:` in this item, so all seven wave skills change and all seven
  bump. A grep of install.sh, the wave scripts and .claude-plugin on
  2026-10-01 found no reader of the key; check the installer's custom-source
  path before you move it, and say in the CHANGELOG where the version now
  lives. Mirror skills/ into .claude/skills/ (diff -rq -x __pycache__ per
  skill must be empty); run the unit tests in both trees (baseline: 227 in
  bmad-dev-wave, 12 in bmad-close-epic, both trees) and `./install.sh
  --validate-only --skip-mcp-check` before every commit. Stage files by
  name, never git add -A, and re-check the staged list against the commit
  message. The gitleaks pre-commit hook runs; never bypass it.
- Prose is ASCII with " -- " dashes. No em dashes anywhere.
- Settings and agent files: prepare the exact content, then let the
  permission prompt decide. R1, R2 and R3 were each allowed their wrapper,
  registration and permission-block writes on the first try, so try once; if
  refused, print the content and the path for RQ and carry on.
- Do not add a stage, do not add a domain persona, do not build anything
  that edits the harness on its own. R4 adds no hook and no gate rule.
- Git: `git fetch`/`git push` failing with "signing failed ... communication
  with agent failed" means 1Password is locked; ask RQ to unlock and retry.
  The review docs under docs/reviews/ are untracked; never stage them.
- RQ merges and tags by hand. Halt after the PR is open and report: what
  changed, the prediction, R3's grade, what R5 needs from the merge.

R4. Delete the configuration that configures nothing and bind the routing
that should (templates/settings.json.template; install.sh; core/config.yaml;
the seven wave skills' SKILL.md; .claude/agents/; `.agents/skills`;
docs/upstream-refresh-runbook.md; CHANGELOG).
Build, in the review's order:
(1) The template, per (f), and the resolver in step with it. A fresh
    `--target-project` install must resolve a settings.json that parses,
    carries no top-level key the settings index does not list (the two
    `$comment_` keys and `$schema` aside), and differs from R3's in the
    deleted keys and the rename only.
(2) Skill frontmatter, all seven wave skills. `when-to-use` becomes
    `when_to_use`, the one field name with an underscore; description plus
    when_to_use must stay under the 1,536-character cap, and the longest
    today is bmad-wrap at 962. `version:` moves under `metadata:`.
    resume-wave's `tools:` becomes `allowed-tools: Read Glob Grep Bash
    Skill(bmad-dev-wave *)`, which drops SlashCommand, not a current tool.
    The other inert keys (when-not-to-use, output-locations, outputs,
    inputs, exit-codes) are documentation nothing reads: move them under
    `metadata:` or into the body, and say which. `allowed-tools`
    pre-approves and never restricts; do not write as if it did.
(3) install.sh's memory directory (the `mkdir -p
    "$HOME/.claude/projects/$slug/memory"` near line 222). The real
    directory is the target's absolute path with every non-alphanumeric
    character replaced by "-" (B row 10.1), and Claude Code creates it. Fix
    the path or delete the step, and say which.
(4) `.agents/skills`, per (i).
(5) The binding, per (g) and (h): the definitions; dev-wave steps 6 and 10
    dispatching them by name; "The Review Record" taking its `model` and
    `effort` from the definition that ran; core/config.yaml reduced to the
    tier table (its permissions, parallelism and context blocks are read by
    nothing, B rows 4.1, 11.2 and 15.1, but dev-wave step 6 cites
    `parallelism.max_parallel_subagents`, so keep that number where the step
    can cite it or move it into the step); the phase-6 assertion; and
    `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` documented in the runbook as the
    override that ignores frontmatter models.
At risk, to carry into your entry and add to. The Agent tool's
per-invocation `model` parameter outranks frontmatter (B row 8.3), so a
caller can still override a definition, and an `Agent(model:...)` deny rule
would apply to every Agent call. A definition with no `tools:` inherits
every tool, which is right for a coder and has to be a decision for a
reviewer, whose brief is to prove findings by execution. In auto mode every
subagent's hand-back runs R3's hook, 37 ms each, which exits at once for any
agent but the evaluator. `effortLevel` in a project file sets every
session's effort in that instance. A full model id goes stale without an
error when a model retires.
Verify: rebuild the scratch instance from your branch and dispatch each new
definition by name from a `claude -p` session, with a logging hook on
SubagentStop and on SubagentHandback (R3's log-hook.sh, registered in the
git-ignored .claude/settings.local.json and loaded with `--setting-sources
project,local`). The event's `agent_type` is the definition's name and its
`effort.level` the definition's; the run's `modelUsage` in the stream-json
result names the pinned model. The session's own effort, from any
main-thread PreToolUse event, equals `effortLevel`. Say how you checked that
`when_to_use` reaches the skill listing, or that you could not.
`./install.sh --validate-only --skip-mcp-check` exits 0 in the fork, and
exits 7 naming the definition when its `model:` is edited away from the
table. If `claude -p` cannot authenticate, unit-test what parses and hand RQ
the live check as exact commands.
Instances: the R3 hand step may still be outstanding. Extend the runbook so
one pass covers both (the new definitions travel with `cp
.claude/agents/*.md`; the template change reaches no instance), and say in
the CHANGELOG what the instances need.

What R5 will need from your merge: the names of the definitions (R5's
reviewer-dispatch eval grades `tool_used` on Agent by subagent_type), the
tier table's final shape, and one fact from R3's grading of R2: with bypass
locked, `--dangerously-skip-permissions` is ignored, not rejected, so the
eval-runner adapter runs in the instance's default mode with every
unanswered prompt a denial.

Paths from R3's and R2's sessions (a scratchpad persists for days, not
forever; rebuild from the #27 body if it is gone). Usage: `bash
live-check-r3.sh <run-name> <acceptEdits|auto>
<main|noverdict|passhigh|record>`, then `python3 report.py <run-name>`;
`python3 replay_session.py <transcript.jsonl> <fork root>`.
  instance:   /private/tmp/claude-501/-Users-ryanquigley-Projects-personal-keelswell/1fd03231-8d37-4f23-9bc1-cf827c93a385/scratchpad/r3-live/keelswell-r3-scratch
  live check: /private/tmp/claude-501/-Users-ryanquigley-Projects-personal-keelswell/1fd03231-8d37-4f23-9bc1-cf827c93a385/scratchpad/r3-live/live-check-r3.sh
  logger:     /private/tmp/claude-501/-Users-ryanquigley-Projects-personal-keelswell/1fd03231-8d37-4f23-9bc1-cf827c93a385/scratchpad/r3-live/log-hook.sh
  replay:     /private/tmp/claude-501/-Users-ryanquigley-Projects-personal-keelswell/b0fc3f65-f667-4532-a7e2-55495a0d0723/scratchpad/replay_session.py
```

### R5: seed the eval suite from what already exists, then run it in CI

Fable 5.1, effort `high`. One day for the replay and the workflow, two for
the three eval pairs. The failure mode is a number nobody can trust: a task
that passes because it is broken, or a grader that reads the wrong file. So
every task ships a reference end state, and every grader is shown failing
once before its pass is believed.

Run from the keelswell root. Requires #29 merged (landed 2026-10-01; main
3750f45).

```text
You are implementing R5 of the Keelswell harness-engineering review, the
last of five "do now" items. R4 is merged as rlquigley/keelswell#29 (main
3750f45, bmad-dev-wave 1.10.0); confirm it is in main before you branch, and
branch from that main. The review is approved; do not re-plan it. Read these
first, in order:

1. docs/reviews/harness-engineering-review-v1.md, sections 1, 4 and 5. R5 is
   the item; its "What" is the build list below. Section 5's rows for
   roadmap R9, "Batch 2 review-record check at PR time" and "Batch 4
   Keelswell CI" are the rulings it carries.
2. docs/reviews/harness-review-v1-appendix-a.md, A1a sections 3.1 (the
   runner table, the three balanced pairs, "How to run it") and 3.4.
   docs/reviews/harness-review-v1-appendix-f.md, track E1: Summary, 1.1,
   1.2, 6 ("Selector findings the replay surfaced"), 7, 8, 10, 12 and "Open
   items" 3 to 5, and DP2's caveat. Appendix B rows 14.1, 19.1 and 19.3.
   Then the raw docs, never a summary: `curl -sL
   https://code.claude.com/docs/en/<page>.md` for plugin-evals and headless.
   Quote the page for every flag you put in a script.
3. skills/bmad-dev-wave/scripts/select_reviewers.py (IGNORED_PATHS at line
   112 and the five precision rules in its docstring), reviewer-triggers.yaml
   (the header, the fallback block, and the rows tea-murat, bmm-pm,
   bmm-architect and arch-cost-optimizer), tests/test_select_reviewers.py.
   In skills/bmad-dev-wave/SKILL.md: steps 4.5, 8 and 10, The Routing, The
   Reviewer Selection. .claude/skills/bmad-eval-runner/: SKILL.md,
   references/eval-format.md, references/grader.md,
   assets/adapter-claude-code.json, scripts/aggregate_benchmark.py. install.sh
   phase 6, which is what a workflow would call.
4. The CHANGELOG [Unreleased] entry R4 wrote (top of the file): it carries
   the prediction you grade first. Then the Phase 6.3 entry further down,
   which says "3.2 -> 4.2 with the fallback still firing on exactly two":
   E1 measured 4.11 and three (3A, 3D, 6A).
5. The auto-memory index at
   ~/.claude/projects/-Users-ryanquigley-Projects-personal-keelswell/memory/MEMORY.md,
   then keelswell-harness-review-v1, keelswell-trigger-table-precision,
   keelswell-wave-script-testing, claude-code-subagent-report-hooks,
   keelswell-instance-updates, git-stage-explicitly-not-add-all,
   keelswell-push-needs-sandbox-off, claude-docs-raw-markdown,
   rq-adhd-communication.

Your first message: your approach in five lines at most, your biggest
uncertainty, R4's prediction restated with how you will grade it, and the
rulings below restated as you understand them. Then wait for RQ's go. When a
ruling needs RQ, write the plain story of the choice first, then the options
with the recommended one first, one question at a time; RQ answered R4's
five that way inside a minute each.

Rulings already made, restate them, do not reopen them:
(a) 2026-09-28: templates/settings.json.template is a fork-owned seam.
    test_settings_template.py pins its top-level keys (`model`,
    `effortLevel`, `permissions`, `hooks`), R1's PreToolUse entry as the
    first, the evaluator hook's three entries, every deny and ask rule, the
    bypass lock and `defaultMode: acceptEdits`. R5 does not touch the file.
(b) 2026-09-28: bypass is locked and there is no auto ban. Measured
    2026-10-01: with the lock, `--dangerously-skip-permissions` is ignored,
    not rejected, so a session started with it runs in the settings' default
    mode and every unanswered prompt is a denial. Haiku cannot run auto.
(c) 2026-10-01: the evaluator's record is hook-written on three events and
    `evaluate_wave.py record` is denied to Bash. An eval never writes or
    forges an evaluation record; it reads the one the hook wrote.
(d) 2026-10-01: three definitions under .claude/agents/, dispatched by
    `subagent_type`: keelswell-wave-coder (claude-sonnet-5-5, high),
    keelswell-wave-reviewer and keelswell-wave-evaluator (claude-opus-5-5,
    high). core/config.yaml is the tier table and `routing_check` in
    install.sh phase 6 asserts the definitions against it. Not generated;
    re-pinned per release with a CHANGELOG line. A reviewer's persona is the
    `skill` the selector returned, named in its prompt.
(e) 2026-10-01: a skill's version lives at `metadata.version` in its
    SKILL.md frontmatter. A version check reads that key.
(f) 2026-10-01: the hook rule for the `git -C` and `bash -c` forms is a
    sixth do-now item, unscheduled. Name it in your report, do not build it.
(g) Not ruled, so not built: R4's grading of R3 found that `evaluate_wave.py
    dispatch` re-dispatches a HEAD unchanged since the newest record, and
    re-dispatches after an UPSTREAM_CAUSE with no fix on record, and each
    round advances the pass count. RQ has not scheduled it. An eval that
    trips over it reports it; R5 does not fix it.
(h) The review, approved 2026-09-28: "no self-improving loop yet" stands. R5
    builds measurement. A human reads every failing transcript, and nothing
    R5 builds edits a skill, a table or a definition from a result.

Five new rulings to confirm before touching anything (proposed default in
brackets; RQ decides):
(i) What of ffbapp may enter the fork. Measured 2026-10-01 with `gh repo
    view`: rlquigley/keelswell is PUBLIC and attacktheseam/ffbapp is
    PRIVATE. E1's fixture is 1.1 MB of ffbapp: 18 changed-file lists (2C's
    has 799 paths), 17 test designs, 10 review records. The review says
    "commit E1's replay fixture"; it did not weigh that. [Nothing of
    ffbapp's text or paths is committed. Commit the builder (it holds 18
    wave ids and pull request numbers and reads the local ffbapp checkout),
    and one golden file: per wave, the role ids selected, whether the
    fallback fired, and the counts, with the mean beside them. The fixture
    is rebuilt locally into a git-ignored directory, and the replay test
    skips with a named reason when it is absent. The cost: a GitHub-hosted
    runner cannot reach ffbapp, so CI does not run the replay; it runs on
    this machine before any change to the table, and the CHANGELOG says so.]
    The other options, for the question: commit the file lists and not the
    specs (paths disclose the project's layout, and the selector's spec
    half goes untested), or commit all of it.
(j) Which table defects R5 fixes. The review names five (E1 section 6, items
    1 to 3, plus the two wrong CHANGELOG numbers). Every fix moves the
    metric the replay pins, so the order is: commit the golden at today's
    table first (mean 4.11 with bmm-dev seated, fallback on 3A, 3D and 6A),
    then each fix as its own change to the golden, with before and after in
    the CHANGELOG. [Fix `IGNORED_PATHS` so planning artifacts under
    `_bmad-output/planning-artifacts/` are seen while a wave's own
    bookkeeping stays ignored. Fix tea-murat's glob to reach
    `tests/unit/support/`, and say plainly that 3D then gets tea-murat and
    loses the fallback, one of the two waves the fallback was built from.
    Give arch-cost-optimizer the cost vocabulary it misses on 1C, 4B and 5C,
    each new pattern checked against the five precision rules and against
    all 18 waves for a new misfire. Correct 4.2 to 4.11 and "exactly two" to
    three as a dated correction beside the old line, not a rewrite of it.]
    E1's items 4 to 7 (4A and ML, 6A, pyproject.toml as a dependency proxy,
    custom-growth) are not among the five: name them, do not build them.
(k) What runs the three pairs. They need a project's own hooks and
    definitions to load (pair A reads a hook-written record), code graders
    on end state, k=3 reported as pass^3, and a `gh` that reaches nothing.
    bmad-eval-runner's Claude Code adapter passes
    `--dangerously-skip-permissions` (ignored under the lock, ruling b),
    authenticates by `ANTHROPIC_API_KEY`, grades by an LLM grader only and
    reports no pass^k. `claude plugin eval` loads the plugin without the
    project's settings and hooks (B row 14.1), 10 turns and 300 s by
    default. R3's and R4's live checks already do the job at small scale: a
    fresh `--target-project` instance, `claude -p --setting-sources
    project,local --permission-mode <mode> --allowedTools ...`, a Python
    report over the stream-json and the files left behind, under the
    machine's own login. [A small stdlib harness on that pattern under
    skills/bmad-dev-wave/evals/, one directory per task with its prompt, its
    fixture and a reference end state; graders are Python reading files and
    a `gh` stub's log; parent model Sonnet, never Haiku. No container: with
    bypass ignored, the deny and ask rules in force and a fixture with no
    remote, a trial cannot merge, force-push or push at all. Say what that
    does not contain: the network and the rest of the filesystem.] The
    review's at-risk line asks for a container; this default argues it away
    and RQ may not agree.
(l) One pull request or two. The review's estimate is one day for the
    replay and the workflow and two for the pairs, and a suite run is 18
    headless trials. R4's two-dispatch trials cost $0.48 and $0.59 each at
    list price, R3's evaluator trials $0.11 to $0.61. [Two: R5a is the
    replay, the table fixes and the workflow; R5b is the three pairs, opened
    after R5a merges. Each carries its own prediction.] "One pull request
    per item" has held for R1 to R4, so this is RQ's call.
(m) What CI runs and what it gates. `.github/workflows/` is outside the
    plan's three seams; this prompt's list is the grant. [One workflow on
    pull_request and on push to main, no secret and no model call: the unit
    tests in both trees; `diff -rq -x __pycache__` between skills/<name> and
    .claude/skills/<name> for every directory under skills/ (46 on
    2026-10-01), which must print nothing; `./install.sh --validate-only
    --skip-mcp-check`, which needs Node 20.12 or later, Python 3.11 or later
    and PyYAML; and a check that a pull request changing any
    skills/*/SKILL.md `metadata.version` also changes CHANGELOG.md. The
    pairs never run in CI. Making the workflow a required check is a branch
    protection setting, RQ's hand step; say so and do not attempt it.]

Grade R4's prediction first, before building. It said: in a fresh instance,
and in any instance that carries the three definitions and dev-wave 1.10.0,
every step-6 coder runs on claude-sonnet-5-5 and every step-10 reviewer and
the evaluator on claude-opus-5-5, all at effort high, whatever the session's
model and effort; every review record written from then on says `model:
claude-opus-5-5` and `effort: high`; a definition edited away from the table
fails validation by name; a fresh instance's sessions start on
claude-opus-5-5 at effort high; the seven wave skills' listing entries carry
their `when_to_use`; nothing changes in a live instance until the hand step,
and nothing there changes in settings.json at all. At risk were: the Agent
tool's `model` parameter outranking a definition; dispatch by name being
prose, so a general-purpose subagent can still be sent; neither definition
restricting tools, so a reviewer can leave a mutation behind; the persona
depending on the Skill tool (measured once per mode, never in default mode
or under a Skill rule); R3's hook running on every subagent's hand-back in
auto mode; `effortLevel` setting every session's effort in a fresh instance;
a full id going stale without an error; dev-wave 1.10.0 without the
definitions; resume-wave's `allowed-tools` pre-approving Bash; reviewers
costing Opus at high; step 3's subagent still following the session; and a
non-Claude tool finding no `.agents/skills`. Grade it by: (1) the live check
again on the current CLI (script and instance below): a Sonnet parent in
acceptEdits and a settings-model parent in auto with `--effort low`; read
each thread's `message.model` from the stream-json `assistant` lines grouped
by `parent_tool_use_id`, and `effort.level` and `agent_type` from the hook
events; (2) the instances: on 2026-10-01 ffbapp and green-ledger were at
1.8.2 with neither the R3 nor the R4 hand step. Ask RQ once whether it has
been applied and whether a wave has run. If one has, read its
review-party.md front matter, its evaluation records' headers, and its
transcript for every Agent call's `subagent_type` and `model`: that is the
first grade any of R1 to R4 gets from a real wave; (3) validation: exit 0 on
main, exit 7 naming the file in a scratch instance with one definition's
`model:` edited; (4) the listing: say how you checked that `when_to_use`
reaches it (R4 saw its own session's listing reload with "description -
when_to_use"); (5) your own session: replay your Bash, Write and Edit calls
through the gate (replay_session.py, below) and count refusals against R4's
0 of 77. Pair C of the build list is the first grader of "dispatch by name
is prose"; cite its result in the grade if R5b lands in this session. Write
the grade into the R5 CHANGELOG entry and the PR body.

Standing rules, all from the fork's own record:
- Work only where R5's list reaches: skills/bmad-dev-wave/scripts/
  (select_reviewers.py, reviewer-triggers.yaml, tests, fixtures),
  skills/bmad-dev-wave/evals/, .github/workflows/, .gitignore and
  templates/.gitignore.template for a local fixture directory, and the
  CHANGELOG. That list is the grant for what sits outside the plan's three
  seams. Never _bmad/scripts/, never agents/, never an upstream-declared
  skill body, and never .claude/skills/bmad-eval-runner/, which is
  upstream's: read it, do not edit it.
- ffbapp is read-only, always. The builder runs `git show`, `git diff` and
  `git log` there and nothing else.
- Every change ships a predicted impact with at-risk regressions, in the
  CHANGELOG [Unreleased] entry and the PR body. R5 is the last do-now item,
  so say who grades it: the next session that touches the fork.
- Bump `metadata.version` of every skill you change. Mirror skills/ into
  .claude/skills/ (diff -rq -x __pycache__ per skill must be empty); run the
  unit tests in both trees (baseline: 231 in bmad-dev-wave, 12 in
  bmad-close-epic, about 61 s a tree) and `./install.sh --validate-only
  --skip-mcp-check` before every commit. Stage files by name, never git add
  -A, and re-check the staged list against the commit message. The gitleaks
  pre-commit hook runs; never bypass it. It refuses a fresh scratch
  instance's first commit; a scratch instance does not need one.
- Prose is ASCII with " -- " dashes. No em dashes anywhere.
- Do not add a stage, do not add a domain persona, do not build anything
  that edits the harness on its own. R5 adds no hook and no gate rule.
- Scripts are stdlib only. PyYAML is install.sh's dependency, not a wave
  script's.
- Git: `git fetch`/`git push` failing with "signing failed ... communication
  with agent failed" means 1Password is locked; ask RQ to unlock and retry.
  The review docs under docs/reviews/ are untracked; never stage them.
- RQ merges and tags by hand unless RQ says otherwise in the session. Halt
  after the PR is open and report: what changed, the prediction, R4's grade,
  the first outcome numbers, and the open list below.

R5. Seed the eval suite from what already exists, then run it in CI
(skills/bmad-dev-wave/scripts/ and evals/; .github/workflows/; CHANGELOG).
Build, in the review's order:
(a) The replay, per (i) and (j). A test that runs `select_reviewers.py
    select` over each wave of the fixture and compares role ids, the
    fallback flag and the mean against the golden. Prove it against E1's own
    outputs first (selector/<ID>.json, below): at today's table it must
    reproduce 74 selections over 18 waves, mean 4.11, bmm-dev on 17, the
    cost row on 0, the fallback on 3A, 3D and 6A. Then the fixes, one at a
    time, each showing the cells it moved. The fixture is the 18 waves the
    table was tuned on: it catches regressions, not generalization, and the
    entry says so.
(b) The three balanced pairs, per (k), entered at the step under test with
    checkpoint fixtures, never from step 1. A, the evaluator gate at step 8
    (A1a wrote "step 7" before R3 renumbered): a wave with a planted
    stubbed acceptance test against the same wave without it; should-fire
    ends with a hook-written `evaluation-1.md` saying NEEDS_WORK, status
    `in-progress`, no review-party.md and no `gh pr create` in the stub's
    log; should-not ends PASS and `in-review`. B, the open-questions gate at
    step 4.5: an open question tagged to the wave's story against none;
    should-fire leaves `step-4.5.pending` and no Agent dispatch of
    keelswell-wave-coder; should-not reaches `ready-for-dev`. C, reviewer
    dispatch at step 10: a diff that fires a specialist row against one that
    fires only the generalist; the Agent calls' `subagent_type` is
    keelswell-wave-reviewer with no `model` parameter, and the personas
    named in their prompts and recorded in review-party.md equal the
    selector's `selected`, or the fallback. k=3 per task, 18 trials,
    reported as pass^3 per task. A fresh copy of the fixture per trial,
    fresh `.git` included. Record cost and wall time per trial from the
    result line: it is the fork's first per-step cost figure.
(c) The workflow, per (m).
At risk, to carry into your entry and add to. The replay is scored on its
training set. A golden reduced to role ids cannot show why a row fired. With
the fixture out of the fork the replay is a local habit, not a gate. Fixing
tea-murat's glob retires the fallback on 3D. New cost vocabulary can
overfit to ffbapp a second time. An eval's prompt is the builder's: a task
that tells the session what to do at the step under test measures
obedience to the prompt, not the skill. Pair B's memory fixture depends on
the auto-memory path, which is named from the instance's absolute path. A
trial under the machine's own login reads the user's settings and MCP
servers unless `--setting-sources` keeps them out. Auto mode pauses after 3
consecutive or 20 total classifier blocks. A workflow that installs Node
and PyYAML on every push is slow for a suite that takes two minutes. A
required check on a repo whose owner merges by hand can block the owner.
Verify: for (a), the golden reproduces E1's numbers before any fix, and a
deliberately broken row (one glob deleted) fails the test by wave and role.
For (b), every task's reference end state passes its grader with no model
call, every grader fails on the opposite task's reference end state, and
then the 18 trials run; read every failing transcript and two passing ones
before writing a number down. For (c), the workflow passes on the pull
request, and a scratch branch with skills/ and .claude/skills/ out of step
fails it by name. If `claude -p` cannot authenticate, land what runs
without a model and hand RQ the trials as exact commands.

The open list, for your last message, each named and none built: the sixth
do-now item (f); the `dispatch` gap (g); E1's selector findings 4 to 7; the
review's "Later" items R6 to R10; the instance hand step for R3 and R4 if
(2) finds it still outstanding; and what was left as found on 2026-10-01
(`Task` in dev-wave's `allowed-tools`, "extra" in bmad-wrap's description,
the `fork:` block of core/config.yaml, the `.agents/skills` mentions in
docs/harness-conversion-plan.md and `.gitleaks.toml`). The do-now list ends
with R5; write no further kickoff unless RQ asks for one.

Paths from R4's, R3's and the review's sessions (a scratchpad persists for
days, not forever). If E1's directory is gone, rebuild the fixture from
Appendix F section 1.1: per wave, `git diff --name-only <merge>^1 <merge>`
and `git show <merge>:docs/wave-<id>/test-design.md` in the ffbapp checkout,
the merge found by `git log --merges --grep "Merge pull request #<n>\b"`.
If R4's instance is gone, `./install.sh --use-defaults --yes --user-name RQ
--target-project <dir> --skip-mcp-check` builds another. Usage: `bash
live-check-r4.sh <run-name> <acceptEdits|auto> [claude flags]`, then
`python3 report-r4.py <run-name>`; `python3 replay_session.py
<transcript.jsonl> <fork root>`.
  E1:         /private/tmp/claude-501/-Users-ryanquigley-Projects-personal-keelswell/27d71e3a-ea91-4b21-8c3d-e559c67ee01d/scratchpad/jev/e1
              (build_fixture.sh, fixture/<ID>/, selector/<ID>.json, probes/, compare.py)
  instance:   /private/tmp/claude-501/-Users-ryanquigley-Projects-personal-keelswell/fe03d5d2-5442-4e76-993b-bb4bcadf8ab1/scratchpad/r4-live/keelswell-r4-scratch
  live check: /private/tmp/claude-501/-Users-ryanquigley-Projects-personal-keelswell/fe03d5d2-5442-4e76-993b-bb4bcadf8ab1/scratchpad/r4-live/live-check-r4.sh
  report:     /private/tmp/claude-501/-Users-ryanquigley-Projects-personal-keelswell/fe03d5d2-5442-4e76-993b-bb4bcadf8ab1/scratchpad/r4-live/report-r4.py
  logger:     /private/tmp/claude-501/-Users-ryanquigley-Projects-personal-keelswell/fe03d5d2-5442-4e76-993b-bb4bcadf8ab1/scratchpad/r4-live/log-hook.sh
  R3 kit:     /private/tmp/claude-501/-Users-ryanquigley-Projects-personal-keelswell/1fd03231-8d37-4f23-9bc1-cf827c93a385/scratchpad/r3-live
  replay:     /private/tmp/claude-501/-Users-ryanquigley-Projects-personal-keelswell/b0fc3f65-f667-4532-a7e2-55495a0d0723/scratchpad/replay_session.py
```

## Standing item: after every upstream pull

Opus 5, effort `medium`. Event-triggered, not scheduled. Runs at step
5a of `upstream-refresh-runbook.md`, after verification and before the
diff-review commit, so the "what we chose not to adopt" note lands in
the same commit as the pull. Step 1 is Phase 4's conformance check
(merged 2026-09-11); a failure there names the invariant and stops the
refresh before anything is committed.

```text
I just pulled upstream BMAD (or CIS, TEA, or the architecture pack)
into keelswell. Before I do anything else:

1. Run ./install.sh --validate-only and tell me whether the Phase 4
   conformance checks pass. If any fail, stop there and tell me which.
2. Diff what changed upstream against the fork-owned seams: the wave
   skills, _bmad/scripts/, install.sh, config/agent-names.yaml, and
   module.yaml. Tell me what upstream changed that touches or
   overlaps any of them.
3. Draft a CHANGELOG.md entry with two parts: what changed upstream,
   and what we are choosing not to adopt and why. The second part is
   the one that gets lost; write it even if the answer is "nothing".

Do not resolve anything. Report, then wait.
```
