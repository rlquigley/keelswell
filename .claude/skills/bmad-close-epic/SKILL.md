---
name: bmad-close-epic
description: >
  Per-epic closure gate. Wraps four Stage F sub-skills -- code-review,
  testarch-trace (requirements traceability), testarch-nfr (non-functional
  requirements), and the retrospective -- into a single gate. Operates on a
  docs-only branch (no production code changes), writes a consolidated
  SUMMARY plus four detail reports, feeds retrospective lessons into
  project-context.md, opens a pull request, and halts before merge.
when-to-use: |
  After every wave of the epic has been through /bmad-dev-wave and
  /bmad-merge-wave, and before starting the next epic -- including when
  /bmad-status-wave shows the epic as closure-pending.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
inputs:
  - >-
    epic-id (positional, required; integer matching an "## Epic <N>" block in
    waves.md). No flags: closure is not tunable, there is no --dry-run, no
    --skip-subskill, no --force.
output-locations:
  - _bmad-output/epic-closure/epic-<N>/SUMMARY.md
  - _bmad-output/epic-closure/epic-<N>/code-review.md
  - _bmad-output/epic-closure/epic-<N>/testarch-trace.md
  - _bmad-output/epic-closure/epic-<N>/testarch-nfr.md
  - _bmad-output/epic-closure/epic-<N>/retrospective.md
  - a docs-only branch pushed to origin, and a pull request against main
version: 1.0.0
---

# bmad-close-epic

## The Six-Step Closure Workflow
1. Preflight: the epic block exists in waves.md and lists at least one wave;
   every wave of the epic is merged AND cleaned up (archived checkpoint
   present, no open PR); every story of the epic is in done status. Any
   failure: refuse -- partial closures produce misleading records.
2. Create the docs-only closure branch off main. No production code changes
   are permitted on it.
3. Run the four sub-skills in order -- code-review, testarch-trace,
   testarch-nfr, retrospective -- each returning a structured verdict
   (PASS / CONCERNS / FAIL) plus a report. A sub-skill that produces
   unparseable output is recorded as ERROR with a stub report embedding the
   raw response; the run continues.
4. Write the five Markdown files: the four detail reports plus SUMMARY.md,
   which carries the top-level status (GREEN if all PASS; YELLOW on any
   CONCERNS, FAIL, or ERROR), the four verdicts, and an epic-to-waves table
   so the closure reads standalone.
5. Feed the retrospective lessons into project-context.md so the next epic
   starts with them in context.
6. Commit the docs, push the branch, open the pull request -- ready-for-review
   when GREEN, draft when YELLOW -- and halt. Human review is the final gate;
   this skill never merges.

## Idempotency
Re-invocation against the same epic and git state reproduces the same
verdicts (modulo bounded sub-skill non-determinism) and overwrites the same
five files on the same branch.

## Refusals
- Some wave not cleaned up: name it; run /bmad-merge-wave first.
- Epic has zero waves: refuse (planning error or typo).
- Closure branch already exists: refuse; delete or rename it explicitly.
- Main diverged since the waves merged: refuse; reconcile main first.
