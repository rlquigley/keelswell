---
name: bmad-dev-wave
description: >
  Execute one wave from the wave map. Creates a worktree, designs wave-scoped
  tests, scaffolds stories, dispatches one or more coding subagents, runs
  verify and party-mode gates, lands commits, opens a pull request, and halts
  before merge.
when-to-use: |
  Use at the start of each wave's implementation session, after
  /bmad-create-wave has written the wave map. Do not use for ad-hoc story
  implementation -- this skill is wave-shaped and refuses to run without a
  wave map; small waveless work belongs to Quick Dev.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash
  - Task
output-locations:
  - ../<project>-wave-<id>/                 # sibling worktree, branch wave-<id>-<suffix>
  - .bmad/wave-<id>/checkpoint.json         # plus step-N.done markers (main repo)
  - <worktree>/docs/wave-<id>/test-design.md
  - <worktree>/docs/stories/                # JIT story files
  - pull request against main via gh pr create
version: 1.0.0
---

# bmad-dev-wave
Execute one wave from the wave map. Stage 2 of the four-stage wave cycle: it
consumes the map /bmad-create-wave produced, produces a worktree with
committed story implementations and an opened pull request, and halts before
merge. It never merges.

## Inputs
### Required
- Wave ID (positional). Example: 1A-auth-foundation, or just 1A.
- _bmad-output/planning-artifacts/waves.md (the wave map).
### Optional
- --resume: skip steps with a completed checkpoint; pick up at the first
  incomplete step. /bmad-resume-wave is the canonical entry point; this flag
  is the underlying mechanism.
- --no-party: skip the party-mode step even for a load-bearing wave. Only when
  party-mode ran in a prior session and its artifacts are still valid.
- --dry-run: walk every step and print what would happen without writing
  files, dispatching subagents, or opening a PR.
### Inferred
- Wave pattern (serial or parallel), load-bearing and spine-only flags: from
  the wave map row.
- Repo name and main checkout path: from the current working directory.
- GitHub remote: from `git remote get-url origin`.

## The Twelve-Step Workflow
Each step writes a checkpoint marker under .bmad/wave-<id>/; any step can be
re-entered by /bmad-resume-wave.
1.  Preflight: clean tree, wave exists in waves.md, gh authenticated.
2.  Worktree creation: sibling ../<project>-wave-<id> on branch
    wave-<id>-<suffix>.
3.  Wave-scoped test design (one QA-persona subagent) ->
    docs/wave-<id>/test-design.md.
4.  Just-in-time story creation for stories not yet on disk.
4.5 Open-questions gate: scan auto-memory for unresolved questions tagged to
    this wave's stories; HALT for user input on any hit. Never dispatch
    parallel subagents past an unfired gate.
5.  ATDD scaffolding: failing test stubs per the test design.
6.  Implementation dispatch: serial for spine waves; parallel (one coding
    subagent per story, capped by core/config.yaml
    parallelism.max_parallel_subagents) for parallel waves. Every subagent
    receives the Project Conventions Block verbatim (below).
7.  Test expansion and review: close coverage gaps found in review.
8.  Checkpoint preview: show the exact commits about to land; accept
    "approved", "edit: <instruction>", or "abort". A failing story may be
    demoted out of the wave (waves.md is updated and a follow-up wave queued).
9.  Verify: run tests/verify-fast.sh in the worktree; on FAIL offer
    edit / demote / abort.
10. Party-mode adversarial review -- load-bearing waves only (skipped by
    --no-party): dispatch security, cost, and platform reviewers; block on
    HIGH or CRITICAL findings.
11. Commits and pull request. Parallel waves: exactly one foundation commit
    (every cross-cutting file every subagent edits -- pyproject.toml or the
    lockfile, errors.py, the CLI main, ci-fast.yml, the wave's
    test-design.md) then one commit per story touching only story-exclusive
    files. Serial waves: strict per-story commits. Push branch; gh pr create.
12. Halt before merge. Print the PR URL. Merging is the human's decision;
    cleanup afterward is /bmad-merge-wave's job.

## Project Conventions Block
A single verbatim block defined once here and rendered identically into every
coding-subagent dispatch (subagents inherit neither auto-memory nor
conversation context). It carries: communication rules, git rules
(commit-message format, branch naming), language and tool conventions, the
test framework and verify harness location, CI constraints, standing policy
decisions, and coding discipline (touch only the story's files; no drive-by
improvements). Populate the block for your project before the first dispatch;
an empty block is a preflight warning.

## Error Handling
- Dirty working tree at preflight: refuse; name the dirty paths.
- Wave ID not in waves.md: refuse; suggest /bmad-create-wave.
- Open question surfaced by a subagent that the gate should have caught:
  halt the wave; record the resolution to auto-memory before re-dispatch.
- Verify FAIL: offer edit (re-dispatch with failing-test context), demote
  (drop the story to a new wave), or abort (leave worktree for inspection).
- Never trust a subagent completion summary: read the diff, run the claimed
  tests, before step 8's preview.
