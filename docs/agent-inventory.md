# Agent inventory: the 16 fork-only agents

Phase 5 of `harness-conversion-plan.md`. One question per agent: what
specific failure does it prevent? Not what it does.

**Assessed 2026-09-12 against the Claude 5 family** (opus-5, fable-5,
sonnet-5), which is the generation that produced every piece of
evidence cited here. This inventory goes stale on the next model
release by design. `[[structure-transfers-prose-does-not]]` is why: a
prompt's value does not survive being moved to another model family,
so a persona that earned its place against Claude 5 has to earn it
again against Claude 6. Re-run this pass then; do not inherit its
verdicts.

Applies only to the 16 fork-only agents the plan identifies:
`agents/core-bmad-master.md` and the fifteen `agents/custom-*.md`
files. The other 22 of the 38 files in `agents/` arrive from BMM, CIS,
TEA, or the architecture pack and are not ours to assess.

## What this is not

Not a deletion list. No entry recommends removing an agent, including
the three that could not answer the question. The reason is in the
wiring finding below: for twelve of the sixteen, the absence of
evidence is an absence of dispatch, and you cannot ablate something
that was never installed.

## The test

An agent earns its place if it named a failure that either reached
shipped code or a real-world irreversible act, or reached a ruled
document as a requirement, **and** a reviewer dispatched by bare
domain would plausibly have missed it.

That last clause does the work. Of ffbapp's eighteen waves, fifteen
dispatched reviewers by bare domain with no persona at all ("security
review", "cost review", "platform review") and still produced
findings; two named a persona (1B and 5D); one (3C) dispatched no
reviewer at all. Where a nameless domain prompt would have caught it,
the domain prompt is what prevented the failure, not the persona. This
matches `[[scaffold-vs-weights]]`: the scaffold buys search behaviour
and dispatch, and the domain intuition comes from weights either way.

## What counts as evidence

ffbapp is the only instance with real usage. green-ledger and
learn-bmad have zero custom-agent hits; isi predates the slate.

Party-review findings count, and they are the strongest evidence
available because they carry per-seat attribution:

- `_bmad-output/planning-artifacts/review-party-epics-waves-2026-08-20.md`,
  67 findings, all ruled and folded, each attributed inline
  (`(Damer Flinn.)`).
- `ux-designs/ux-ffbapp-2026-08-08/party-review-findings-2026-08-08.md`,
  attributed in a summary table.
- `architecture/architecture-ffbapp-2026-08-10/reviews/review-party.md`,
  same table form.
- `prd.md` and `addendum.md`, which cite the filing seat inline where a
  finding became a requirement.

Where a finding can be traced from attribution through an acceptance
criterion to a landed test, that is said explicitly. Where it stops at
a document because the epic has not been built, that is said too.

## Group 1: Earns its place (6)

### agent-ml (Damer Flinn)

**Failure prevented:** temporal leakage in a model backtest. Selecting
or validating on the same weeks the verdict is evaluated on, which
produces a number that looks like evidence and is not.

**Evidence:** the strongest chain in the slate, finding to constraint.
He filed EW-1, EW-2 and EW-9 on 2026-08-20, the only High-severity
findings any custom agent filed in that review. EW-2 ("nothing bounds
the data that computes an archetype assignment, so future weeks can
leak into the with-archetype twin") became AC-5.1-1e and five tests in
`test_archetype_data_through_bound.py`. EW-9 became AC-5.2-1e, a
database check constraint on `ArchetypeValidationRecord` refusing
`evaluated_through_season` plus an engine-layer refusal; Epic 5's code
review records it as "closed at the database, not by Python
politeness" and its traceability pass calls it "the epic's best
example of a defence built in both layers on purpose". EW-1 is cited
as a source in
`implementation-artifacts/6-1-pre-registered-gate-spec-registry.md`.
He also set the PRD's calibrated-confidence meaning (`prd.md:451`).

**Trigger:** the wave trains, scores, selects, or validates a model, or
touches a train/test split, a backtest window, or a feature table.

### agent-sre (Tam al'Thor)

**Failure prevented:** a run that cannot be reproduced or accounted
for. Interrupted work disappearing from the ledger, and a failing
pipeline nobody is paged about.

**Evidence:** EW-12 (the execution-substrate field on every run
manifest) became a required field validated in `launcher.launch`
against `EXECUTION_SUBSTRATES` before the transaction opens, proved by
test, and it is part of what makes Epic 4's reproducibility cap
provable at all (`epic-closure/epic-4/testarch-nfr.md`,
`code-review.md`). EW-11 ("interrupted runs vanish from the ledger")
landed as `launcher.abort()` with spend retained. At the architecture
layer he filed PA-7: "a dead pipeline pages nobody; the uptime probe
watches the web process only."

**Trigger:** the wave adds or changes a long-running job, a run
manifest, a scheduled task, a health probe, or anything that writes a
ledger or spend record.

### agent-appsec (Juilin Sandar)

**Failure prevented:** attacker-controlled bytes reaching a place that
trusts them. A composition prompt, a raw storage bucket, an access
artifact whose powers were never separated.

**Evidence:** the only custom agent with a wave-level code trace and a
standing spec. EW-19 drove raw-column-only writes and back-projection
across three Epic 2 stories (`project_display_names()` sweeping 11,824
player rows). PA-4 and PA-5 at the architecture layer: object storage
carrying no classification, and the web credential reaching raw
quarantine. His security verdict on the injection exposure map
(`llm-surfaces/.../reviews/review-security-verdict.md`) found SV-1,
attacker-controlled display names reaching the composition prompt, and
produced the IX-R1 delimiting spec whose Level A was adopted by
founder ruling 2026-08-16. `prd.md:164` and `prd.md:226` cite him for
splitting view links from claim invites into separate, rotatable,
revocable powers.

**Caveat, recorded because it is the honest half:** he was named in
the review dispatch of two waves (1B and 5D) and no wave-level
`review-party.md` attributes a single finding to him, there or
anywhere; the fifteen waves that dispatched a bare "security review"
produced findings anyway. His
value shows at the architecture and planning layer, not inside the
wave loop. That is an argument for changing where he is called, not
for keeping him out of it.

**Trigger:** the wave handles user-supplied text that reaches a prompt,
a query, or a filename; adds or changes an authorization boundary, an
access token, a share link, or a webhook receiver; or adds a
dependency.

### agent-bizops (Basel Gill)

**Failure prevented:** signing in a name that does not exist yet, and
missing a dated filing obligation. Both are irreversible in a way code
defects are not.

**Evidence:** the only agent whose output left the repository. Five
sessions across PRs #3, #11, #17, #18, #19, #35, #50. The LLC was
formed 2026-08-13; the license was filed 2026-08-25 and the trademark
2026-08-27, both after it, which is his own "entity before signatures"
principle holding in the right order. `planning-artifacts/entity/`
holds fifteen artifacts an attorney actually consumed, including a
counsel-intake memo, an asset schedule, and a route comparison. He
also filed EW-47: Epic 20's done definition omitted Stripe merchant
onboarding.

**Note:** zero code effect, by design. His value is a dated calendar
and a packet on disk, which is closer to the memory layer than to
prose, and that is part of why it held.

**Trigger:** invoked directly, not by a wave. Any act that names an
owner (a filing, a payment account, a contract, a license), or a dated
obligation coming due.

### agent-accessibility (Setalle Anan)

**Failure prevented:** shipping a screen that a keyboard or
screen-reader user cannot operate, against a conformance floor the
product had already ruled for itself (WCAG 2.2 AA, `prd.md:633`).

**Evidence:** the most precise findings in the slate. In the UX review
she filed PR-1 through PR-5, two of them High: dark-mode primary
buttons failing AA contrast with no on-accent token defined, and no
visible-focus law anywhere plus a mock that strips the focus outline
on the ask input. PR-3 (inline links color-only, below 3:1 in both
themes) and PR-4 (WCAG 2.2-specific criteria unenumerated) followed.
In the epics review she filed EW-54 (the public accuracy page, the
trigger surface for NFR-7, carries zero accessibility text), EW-55
(the Playwright floor the coverage rests on is not an accessibility
instrument) and EW-61. `addendum.md:94` credits her for the strategy
line that the casual tier's audience makes accessibility a
build-it-from-the-start decision.

**Thin spot, stated plainly:** none of it has reached code, because
Phase 1 shipped no user interface. Her findings are measurable and
specialist, and the conformance floor is ruled, so the failure is
named and real; the prevention is not yet demonstrated.

**Trigger:** the wave ships or changes a rendered surface: a template,
a component, a stylesheet, a color token, a focus behaviour, or a form.

### agent-billing (Bayle Domon)

**Failure prevented:** double-charging or double-granting on a
redelivered provider event, and entitlements welded to billing shape
so a pricing change requires a schema change.

**Evidence:** PA-9, "billing-event ingestion needs idempotency on the
provider event id", which is the classic Stripe webhook failure and
was filed before any billing code existed. `prd.md:506` cites him for
the structural decision that capabilities are granted through
entitlements independent of billing shape, with tiers as entitlement
bundles. He filed EW-42, EW-43 and EW-44 on unsourced and unowned
subscription mechanics (a season-pass end date with no defined source,
monthly's offer window unowned, the founding-rate mark consumed one
epic before anything creates it). In the UX review he and Tuon filed
PR-17: the league pass has no UX surface anywhere in the spec.

**Thin spot:** Epic 20 onward is unbuilt, so nothing has reached code.
The entitlements decision is the load-bearing one and it is already in
the ruled PRD.

**Trigger:** the wave adds or changes a payment provider call, a
webhook receiver, a subscription state transition, an entitlement
grant, an invoice, or a tax mapping.

## Group 2: Consumable (7)

Useful, and the value is prompt-level. Re-earn after each model
release rather than assuming it carried over.
`[[anthropic-cwc-long-running-agents]]` gives the same advice from
practice: re-evaluate how much of your instruction text you still need
after each release.

For each, the condition to re-test after a model upgrade is the same
shape: dispatch a bare domain reviewer at the same wave, then dispatch
the persona, and compare what each filed. Keep the persona only if it
files something the bare domain prompt did not. The per-agent lines
below say what to look for.

### agent-analytics (Hurin)

**Failure named:** a success metric that reads zero because no story
emits the event it counts. EW-34 (the decision-made and
artifact-shared events have no emitting story, so Gate 2's engagement
and wedge legs read zero), EW-35 (no story sources the consensus
baseline two acceptance criteria presuppose), EW-36 (SM-10's
per-league weekly cost has no recorded source), and PA-3 (install-
through and iOS rates with no denominator event).

**Why consumable, not earning:** these are traceability failures, and
`bmad-close-epic` already runs `testarch-trace` against the epics'
acceptance clauses. The harness has a second mechanism for this class.
Nothing of his reached code.

**Keep after an upgrade if:** the bare traceability pass still misses
uninstrumented metrics. If a Claude 6 traceability pass catches them,
he is redundant, not wrong.

### agent-performance (Jain Farstrider)

**Failure named:** a capacity requirement with nothing that verifies
it. EW-37 (nothing produces the beta latency evidence the Ask-budget
deferral resolves on), EW-38 (FR-31's peak-capacity consequence has no
verifying story), PA-10 (batch-API turnaround can consume the 24-hour
artifact floor). `prd.md:398` and SM-10 (`prd.md:618`) both cite him.

**Why consumable:** same overlap as analytics, against
`testarch-nfr` at closure rather than `testarch-trace`.

**Keep after an upgrade if:** the closure NFR pass still accepts an
unverified capacity claim.

### agent-legal (Gareth Bryne)

**Failure named:** a consent or attribution obligation carried by no
story. EW-49 (the member-imports consent question is carried by no
story, and the coverage bookkeeping is wrong twice), EW-50 (a
counsel-not-delivered disposition missing), EW-62, PA-12 (CC-BY-4.0
attribution has no named render home), and PR-13 with Lan (the
world-variant rule silent on league display names).

**Why consumable:** his own operating rule is that he produces a risk
assessment and names the professional who signs off, so the decision
leaves the harness either way. Real findings, low severity, none in
code.

**Keep after an upgrade if:** a bare compliance review still misses
obligations that exist in the PRD but appear in no story.

### agent-growth (Tuon)

**Failure named:** thinnest with any evidence at all. Two findings,
both co-filed: EW-34 with Hurin, EW-67 with three others (a wave-map
cycle-check sentence that is false for its intra-serial edges), plus
PR-17 with Bayle Domon and PA-3 with Hurin.

**Why consumable:** no finding is his alone. Co-filing is real signal
about the room, not about the seat.

**Keep after an upgrade if:** he files something first, on his own, in
one review.

### agent-llm (Talmanes Delovinde)

**Failure named:** generated text inventing facts, and an unmapped
prompt-injection path.

**Evidence, and its limit:** he produced five substantial artifacts
(`grounding-design.md`, `injection-exposure-map.md`,
`calibrated-confidence-review.md`, `eval-harness-plan.md`,
`inference-cost-budget.md`), all inputs to `epics.md`. But the
injection map's actual verdict came from Juilin, and Talmanes' only
party finding is EW-65, a Low about blurb ownership. Phase 1 builds no
LLM surface, so the failure he exists for has had no chance to occur.

**Keep after an upgrade if:** the first wave that builds an answer path
runs with him and produces a grounding or confidence finding the
generic reviewers missed. Until such a wave exists, this entry cannot
be settled either way.

### agent-mobile (Egeanin Tamarath)

**Failure named:** store-rejection risk, and store material pulled
ahead of a ruled deferral. EW-53 (story 23.1's "store strings" clause
is unimplementable or pulls store material ahead of the ruled
deferral), EW-64 (the notification-prompt-shown event asserted only in
the iOS-scoped story), EW-67.

**Why consumable, with a twist:** his content is external fact (store
guidelines, commission programs, anti-steering state) and those change
on rulings and settlements, not on model releases. So he goes stale on
a second clock, and the right move at an upgrade is to re-check the
rules rather than the persona.

**Keep after an upgrade if:** a store submission is actually on the
roadmap. One party appearance and one memlog is the whole record.

### agent-marketing (Aludra)

**Failure named:** activating a share surface whose contents are still
barred, and routing installability to a story that cannot render its
own identity strings. EW-51 and EW-52.

**Why consumable:** two findings in one review, three files total,
nothing downstream.

**Keep after an upgrade if:** a launch or a public surface is in the
next epic and she files against it.

## Group 3: No answer (3)

Nobody can name a failure these prevent. Not a recommendation to
delete; a recommendation for how to find out.

### agent-web-designer (Leane Sharif)

**Why no answer:** zero hits in artifacts, git log, and 87
transcripts. Added in PR #49 on 2026-08-25 and never activated. Phase
1 shipped no user interface, so the trigger never fired.

**The irony worth recording:** her skill carries the only real
*structure* in the slate, a five-step verification loop (open the app
in the browser, check at 375/768/1280, check each in light and dark,
screenshot and read what changed rather than assuming the CSS worked,
report what was verified at which sizes). That is the layer
`[[structure-transfers-prose-does-not]]` says transfers. It has never
run.

**How to find out:** the first wave that ships a rendered surface,
dispatch her and let her do the build-and-verify pass. Compare the
result against a wave built without the loop. The question is whether
the verification loop catches things, which is answerable in one wave;
the persona around it is a separate question.

### agent-design-critic (Tarna Feir)

**Why no answer:** zero hits, same PR, same reason. Never activated.

**How to find out:** she is the natural pair to the entry above, and
her independence claim (she never edits, so her verdict stays
independent) is testable in one wave: run her against a surface Leane
built and see whether the defect list contains anything the builder's
own verification pass missed. If it does not, the independence buys
nothing and one of the two is enough.

### core-bmad-master (Rand al'Thor)

**Why no answer:** zero hits in artifacts, git log, and 87
transcripts. `Skill(bmad-master)` was never called; the customization
resolver was never run against it. The effectiveness review reached
the same verdict independently (deviation D4). It is also the only one
of the sixteen for which no trigger is nameable: the router role it
would fill is filled by the harness's own skill routing and by
`bmad-help`.

**How to find out:** unlike the two above, this one does not need a
wave. Ask a narrower question first: name one request that should
route to it and does not already route somewhere else. If that
sentence cannot be written, the entry stays unanswered and nothing is
lost by leaving it seated in party mode, where it costs one roster
line.

## The wiring finding: nothing calls them

`bmad-dev-wave` step 10 hardcodes three domains: "dispatch security,
cost, and platform reviewers" (`skills/bmad-dev-wave/SKILL.md:93`).
There is no rule anywhere that selects a reviewer from what the wave
actually touches, and **no wave skill references any of the sixteen
agents.** Grepped for all fifteen role codes and all sixteen persona
names across `bmad-dev-wave`, `bmad-close-epic`, `bmad-create-wave`,
`bmad-merge-wave`, `bmad-status-wave`, `bmad-resume-wave`,
`bmad-wrap` and `bmad-retrospective`: zero hits.

So, as shipped:

- a wave landing a payment surface gets no Bayle Domon;
- a wave shipping a screen gets no Setalle Anan and no Tarna Feir;
- waves 4A and 4B, which landed the model work, got no Damer Flinn,
  and 4B is where the defect that 5D's reviewer eventually caught
  originated.

The intended design is that a wave calls the agents its own diff
requires. The rule is **necessity, not a budget**: if eight domains
are genuinely in the diff, call eight; if one is, call one. There is
no cap, because a cap would mean choosing which real gaps to skip
looking for.

What makes that affordable is trigger precision, not a headcount
limit. Each trigger above is written so it can be answered yes or no
from the wave's file list and spec, without judgment. "The wave adds
or changes a webhook receiver" fires rarely and correctly. "The wave
has monetization implications" fires always and means nothing.

Two consequences follow and are recorded rather than acted on here:

1. **The fixed three lose their exemption.** If necessity decides, then
   dispatching security, cost and platform on every load-bearing wave
   is wrong in the same direction as never dispatching the specialists.
   A wave with no infrastructure change does not need a platform
   reviewer because step 10 says so. Wave 5B's clean result is already
   on record as a review that found nothing.
2. **Reviewer selection is middleware, not prose.** Wiring it is
   therefore the durable kind of change, not the consumable kind, and
   it does not violate the plan's "do not add agents": it adds no
   agent, it routes to the ones already declared.

This is Phase 5 output, so it stays a finding. Wiring it is separate
work needing separate approval.

## Party mode: all sixteen are seated, verified

Standing rule: when `bmad-party-mode` is initiated, every agent is in
the room. Selection by trigger is for the wave loop only; an explicitly
convened party is the full collective.

Verified rather than assumed, on 2026-09-12 against ffbapp:

```
uv run .claude/skills/bmad-party-mode/scripts/resolve_party.py \
  --project-root . --skill .claude/skills/bmad-party-mode
```

returns `"active": "installed"`, a room of 38, with all 16 fork-only
agents seated. `default_party` is `""` in `customize.toml`, and the
resolver's default room is the whole collective when no group is
configured, so the behaviour is already correct and the rule is
preserved by **not** setting `default_party`. Anything that sets it
(the Beta League, the Code Review Crew, the Anti-Consensus Club are all
configured groups) shrinks the default room and breaks this rule. Those
groups stay opt-in per invocation.

One defect found while verifying: ffbapp's installed roster keys nine
of the fifteen custom agents under their pre-0.5.0 persona codes
(`agent-setalle-anan`, `agent-tam-althor`, `agent-hurin`,
`agent-gareth-bryne`, `agent-damer-flinn`, `agent-bayle-domon`,
`agent-juilin-sandar`, `agent-jain-farstrider`, `agent-tuon`) rather
than the role codes the fork renamed to on 2026-07-20. Its
`config.toml` and its skill directories agree with each other, so party
mode works and the skills are invocable there; the instance is simply
two months behind the fork. Any trigger table written against role
codes will miss those nine on ffbapp until it refreshes. Named here,
not fixed here.

## What this inventory could not establish

- **The party reviews do not record which model they ran on.** The wave
  program's models are recoverable per session from transcripts; the
  planning-phase reviews are not. An inventory indexed on model
  generation cannot be recomputed exactly against its own evidence.
  Plan item 6.1 fixes this for wave records, which is the fork-owned
  half; the planning-phase reviews stay unstamped because
  `bmad-party-mode` is upstream.
- **Six of the sixteen have no possible code trace yet** (accessibility,
  billing, mobile, marketing, web-designer, design-critic) because the
  epics they speak to are Phase 2 or need a user interface that does
  not exist. Their entries are honest about stopping at a document.
- **No counterfactual exists for any of them.** No wave has ever run
  twice, with and without a seat. Every "would a bare domain reviewer
  have caught this" judgment here is inference from the fifteen waves
  that used bare domain prompts, not a controlled comparison.

## Predicted impact and at-risk regressions

Per the plan's standing requirement, what this pass predicts and what
to check next time:

- **Predicted:** wiring triggers into step 10 raises the finding count
  on model-touching and payment-touching waves, and lowers reviewer
  count on waves that touch neither. If total reviewer dispatches per
  wave rise on average, the triggers are too loose and should be
  tightened before anything else is concluded.
- **At risk:** review cost per wave. The failure mode is not an
  expensive review, it is a review that gets skipped because it became
  expensive. Wave 3C already ran with no adversarial review at all.
  Watch for `--no-party` usage rising after any wiring change.
- **At risk:** two of the six Group 1 verdicts. Accessibility and
  billing rest entirely on planning artifacts, with no code trace
  possible yet. When Phase 2 builds those epics, check whether the
  findings that looked load-bearing on paper actually prevented
  anything. If they did not, both move to Consumable.
- **Falsifiable claim:** Damer Flinn's entry predicts that a wave
  touching a train/test split without him produces a leakage defect
  that a bare reviewer misses. Wave 4B is weak evidence for this
  already. The next such wave settles it.
