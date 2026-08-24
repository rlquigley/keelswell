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
  - every existing story file of the epic set to Status: done
version: 1.1.0
---

# bmad-close-epic

## The Six-Step Closure Workflow
1. Preflight: the epic block exists in waves.md and lists at least one wave;
   every wave of the epic is merged AND cleaned up; every story of the epic
   has landed. Any failure: refuse -- partial closures produce misleading
   records. What counts as proof for the second and third conditions is below.
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

## What preflight accepts as proof

**A wave is merged and cleaned up** when its pull request reads merged, no pull
request against the repository is open for its branch, and no worktree in
`git worktree list` carries its branch. Live state, checked at invocation.

Not an archived checkpoint file. An archive is a proxy for those facts and a
weaker one, since it is a file on disk that says cleanup happened rather than
evidence that it did; the live checks are the facts themselves. Read the
archive when it exists, for the step record it carries, and never refuse for
its absence.

Merged is `state == "MERGED"` from
`gh pr view <branch> --json number,state,mergedAt,mergeCommit`. There is no
`merged` field; naming it makes `gh` reject the whole call.

**A story has landed** when the wave carrying it is merged by the rule above.
A story file is read when it exists and is not required: a wave scaffolds its
stories inside its own worktree, and a wave may land without one. The ruled
acceptance criteria live in the epics document, which is the source the
traceability pass reads in either case. Refuse for a story whose wave never
merged, never for a story whose file was never written.

## Story status is this skill's to set

`bmad-dev-story` ends a story at `review` and no other skill writes `done`, so
before this rule every story sat at `review` after merging and a preflight
demanding `done` could never pass. Passing this gate is the acceptance event,
so the closure owns the transition.

At step 6, with all four verdicts written, set every story file of the epic
that exists to `Status: done` and record the ruling in the file. Do this on the
docs-only branch with the reports, so the status moves in the same pull request
that justifies it. A story with no file needs nothing. Never set `done` before
the four passes have run: the gate is what the status attests to.

Ruled by RQ in chat, 2026-08-24, at the Epic 1 closure.

## Idempotency
Re-invocation against the same epic and git state reproduces the same
verdicts (modulo bounded sub-skill non-determinism) and overwrites the same
five files on the same branch.

## Refusals
- Some wave not cleaned up: name it, and name which check failed (pull request
  unmerged, pull request open, or worktree still carrying the branch); run
  /bmad-merge-wave first.
- Epic has zero waves: refuse (planning error or typo).
- Closure branch already exists: refuse; delete or rename it explicitly.
- Main diverged since the waves merged: refuse; reconcile main first. Local
  main merely behind origin is not divergence: fast-forward and continue.

## Version history
- 1.1.0 (2026-08-24, founder ruling at the Epic 1 closure): preflight proves
  cleanup from live pull-request and worktree state instead of an archived
  checkpoint file, which /bmad-merge-wave never wrote here; a story with no
  story file no longer blocks, since a wave may land without one; the skill
  now owns the `review` to `done` transition, which nothing previously wrote;
  the `gh --json merged` field corrected to `state`/`mergedAt`; local main
  behind origin named explicitly as not divergence.
