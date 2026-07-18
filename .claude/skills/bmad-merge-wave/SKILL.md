---
name: bmad-merge-wave
description: >
  Post-merge cleanup for a single wave. Verifies the wave's pull request is
  merged on the remote, pulls main fast-forward-only, removes the wave's
  worktree via an absolute git -C path, deletes the local branch, archives
  the wave checkpoint, and verifies the cleanup. Idempotent across
  re-invocation.
when-to-use: |
  After a wave's PR is merged on the remote (any merge style), including when
  /bmad-status-wave shows a merged-with-worktree row. Not for abandoning an
  unmerged wave -- delete that branch and worktree manually.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
inputs:
  - wave-id (positional, required)
  - --verbose (optional; full git output instead of one line per step)
version: 1.0.0
---

# bmad-merge-wave
Five steps, each with a precondition, an action, and a checkpoint marker under
.bmad/wave-<id>/cleanup/. If step N fails, steps N+1..5 do not run; re-invoke
after fixing and the skill picks up at the right step.

Variables, computed once at entry (the skill never uses cd; every git command
takes its repo via `git -C <abs-path>`):
- WAVE_ID: positional arg 1.
- MAIN_REPO: absolute pwd at invocation (readlink -f).
- WORKTREE_PATH: <parent-of-MAIN_REPO>/<project>-wave-<WAVE_ID>.
- BRANCH_NAME: wave-<WAVE_ID>* (the wave's branch from waves.md's suffix).
- CHECKPOINT_DIR: <MAIN_REPO>/.bmad/wave-<WAVE_ID>; CLEANUP_DIR:
  <CHECKPOINT_DIR>/cleanup.

## Step 1: Preflight (six checks, refuse-and-exit-1 on failure)
1. Wave exists in waves.md.
2. Worktree state: if present, it is a git worktree on BRANCH_NAME with a
   clean tree (`git -C <worktree> status --porcelain` empty). Dirty or
   wrong-branch: refuse. Absent: pass (idempotent).
3. Branch state: capture tip SHA; if worktree AND branch are both gone, skip
   to step 5 and report a no-op (exit 0).
4. PR merged: `gh pr view --json number,state,merged,mergeCommit,headRefName`
   for the branch. No PR, or .merged false: refuse with the PR URL. Capture
   the merge commit SHA.
5. Branch ahead of merge: commits past the merged head mean orphan work;
   refuse and name the SHAs to cherry-pick first.
6. Checkpoint: warn (not block) if checkpoint.json is missing or the last
   marker is not step-12.done.

## Step 2: Pull main
`git -C MAIN_REPO pull --ff-only origin main`. Verify local main is the merge
SHA or a descendant; abort on divergence (force-push suspected).

## Step 3: Remove worktree
`git -C MAIN_REPO worktree remove WORKTREE_PATH` -- always from the main
repository path, never from inside the worktree being removed (the documented
git foot-gun this skill exists to prevent). If removal leaves a stale
registry entry: `git -C MAIN_REPO worktree prune` and re-verify. Absent
worktree: skip (idempotent).

## Step 4: Delete local branch
`git -C MAIN_REPO branch -d BRANCH_NAME`. If -d refuses AND step 1 verified
.merged true, the PR was squash- or rebase-merged; escalate to -D. The -D
path is reachable only behind the verified-merged check -- never otherwise.

## Step 5: Verify cleanup
Worktree directory absent; worktree registry clean; branch absent; archive
checkpoint.json, the step-N.done markers, and the cleanup markers under
CHECKPOINT_DIR/archive/ (epic closure reads the archive). Print the five-line
summary and exit 0.

## Merge-Type Acceptance
Merge-commit, squash, and rebase merges are all accepted; the only rejected
value is merged == false.

## Refusals
| Refusal | Trigger | Resolution |
|---|---|---|
| Unknown wave | wave-id not in waves.md | check spelling; /bmad-create-wave first |
| PR not merged | .merged false | merge on GitHub (URL in diagnostic), re-invoke |
| Worktree dirty | porcelain non-empty | commit, stash, or discard; diagnostic prints the dirty paths |
| Branch ahead of merge | commits past the merge SHA | cherry-pick the named SHAs to a new branch |
| Wrong branch | worktree not on wave-<id>* | check out the wave branch or remove the worktree manually |
Idempotent no-op: worktree gone, branch gone, archive present -> "already
cleaned up; nothing to do", exit 0.
