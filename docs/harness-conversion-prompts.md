# Harness conversion prompts

Session-opening prompts for each phase of `harness-conversion-plan.md`,
plus the standing post-pull check. Written 2026-09-11. Each phase
assumes the previous one is merged to `main`. Run every session from
the keelswell root: the paths are relative to it and the project's
`.claude/` settings need to load.

Model and effort per phase are recommendations, not requirements. The
reasoning: Opus 5 at `xhigh` is the default for bounded, fully
specified coding work; Phase 4 gets Fable 5.1 because it touches the
installer that already caused one incident and its failure mode is
silent; Phase 5 drops to `high` because it is reading and judgment,
where a human's priors beat raw effort.

Each prompt ends by making the model state its approach and its
biggest uncertainty before touching anything. That step is where a
misread of the plan gets caught cheaply. Do not skip it.

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
enforcement into a script under _bmad/scripts/ that the skill calls
and that exits non-zero when the review record is missing. The rule
does not change; only where it is enforced.

Done means: attempting to close a wave with no review record fails on
the script's exit code, not on the agent's judgment. Show me that
failing case and the passing case before you call it finished.

Constraints that matter here:
- Keelswell tracks four upstreams (BMM, CIS, TEA, the Ricoledan
  architecture pack). Only touch the fork-owned seams the plan names:
  the wave skills, _bmad/scripts/, install.sh. Do not touch agents/.
- The installer is fragile. module.yaml documents how a duplicate
  declaration corrupts config.toml. Read that comment before changing
  anything the installer reads.
- Match the existing script style in _bmad/scripts/ (Python already
  lives there) and the existing skill conventions, including the
  version bump and CHANGELOG entry the recent wave commits used.
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
- Fork-owned seams only: the wave skills and _bmad/scripts/. Do not
  touch agents/ or anything an upstream module declares.
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

## Standing item: after every upstream pull

Opus 5, effort `medium`. Event-triggered, not scheduled. Runs at step
5a of `upstream-refresh-runbook.md`, after verification and before the
diff-review commit, so the "what we chose not to adopt" note lands in
the same commit as the pull. Until Phase 4 is merged, step 1 has
nothing to report; run steps 2 and 3.

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
