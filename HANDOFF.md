# HANDOFF

Session: v0.7.0: four new bench agents
Last updated: 2026-08-08 (UTC)

## Current State

| Stage | Wave | Step | Status |
|---|---|---|---|
| Fork release v0.7.0 (slate v3) authored; both instances updated | none | Wrap complete; PR open, pending RQ merge | green |

## Key Design Decisions Since Last Handoff

- Four seats ruled in from the 2026-08-07 bench-gap review of the
  ffbapp PRD: business operations, LLM surface engineering,
  mobile/app-store, and marketing/SEO. RQ overrode the deferrals on
  mobile and marketing; all four authored now.
- Personas: Basel Gill (bizops), Talmanes Delovinde (llm), Egeanin
  Tamarath (mobile), Aludra (marketing). The accountant question
  resolved into the bizops seat: preparation only, never professional
  advice, every artifact closes by naming the CPA, attorney, or
  broker who signs off.
- Instance agent-ADDITION recipe established (extends the surgical
  copy recipe): role-form skill dir into every tool tree the instance
  has, plus a matching `[agents.agent-<slug>]` table appended to the
  instance's `_bmad/config.toml`. The old nine stay character-named
  until their next refresh (v0.5.0 note).
- marketplace.json plugin version and the README install pin bumped
  0.4.1 -> 0.7.0; release checklist rule recorded in memory so pins
  move with every release tag.

## Blocked-On

- PR merge (RQ): `claude/session-export-review-bd3069` -> `main`,
  carrying slate v3 and this wrap's bookkeeping.
- isi instance commit (RQ, by hand): four skill dirs in both tool
  trees plus four config tables (TODO item 3).

## Next Session Proposal

Options considered:

- A. ffbapp: Basel Gill entity-formation prep (recommended) -- the
  name package is with the attorney; the entity should exist before
  any filing names an applicant. Time-sensitive.
- B. ffbapp: new-seat party sweep of the final PRD -- the four new
  agents file the review tags their surfaces are missing; feeds
  architecture.
- C. ffbapp: architecture stage kickoff (Perrin) with the expanded
  bench at the table.
- D. keelswell-manual: v0.7.0 findings file + KNOWN-GAPS update
  (fork-arc convention).

Selection: A (RQ, 2026-08-08).

Kickoff prompt for the next session:

```
Talk to Basel Gill: run the [EF] Entity Formation Prep engagement for the ffbapp entity.
Context: the 2026-08-07 bench-gap ruling (Keelswell v0.7.0 slate v3) added this seat. The name package is with the attorney, and the entity should exist before any filing names an applicant. PRD OQ-1 (data licensing) and the future Stripe account are entity-signature moments; PRD at _bmad-output/planning-artifacts/prds/prd-ffbapp-2026-08-06/prd.md.
Working dir: ~/Projects/personal/ffbapp. It has no git repo, so there is no work branch to create; note that and proceed.
Confirm with me before drafting: home state, single- vs multi-member, and formation-state preference.
Output: entity type and state comparison, formation checklist, operating agreement outline, and registered-agent options, packaged for attorney review, to _bmad-output/planning-artifacts/.
```

Run mode: accept edits -- a well-specified, doc-producing single-agent
engagement; it pauses only for the three inputs above, and touches no
code.
