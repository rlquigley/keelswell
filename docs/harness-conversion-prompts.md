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
