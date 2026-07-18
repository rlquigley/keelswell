---
name: bmad-wrap
description: >
  Session-end triage. Triages session learnings into auto-memory (CLAUDE.md
  edits are rare and hard-capped), checks active plans, reconciles TODO.md
  and HANDOFF.md, checks for unpushed commits, confirms the wrap, and
  proposes the next session's work. Run at the end of every working session,
  whether or not a wave was active.
when-to-use: |
  At the end of every working session. A finished wave needs its learnings
  captured; an unfinished wave needs a handoff the next session can resume
  from; the same discipline covers both.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash          # read-only allow-list: git status, git log, git diff,
                  # git branch, date -- no mutating git commands, ever
  - Write         # writable surface: _bmad-output/session-wrap/** ONLY;
                  # CLAUDE.md is readable but NOT on any writable path
inputs:
  - --scope=session|day|since=<git-ref>   # contradiction-scan window;
                                          # default session
output-locations:
  - _bmad-output/session-wrap/<UTC-timestamp>/triage.md
exit-codes:
  - 0: wrap complete (findings or no findings -- findings are the product)
  - 1: the triage report itself could not be written (disk full, permission)
version: 1.0.0
---

# bmad-wrap

## The Six-Step Workflow
1. Triage session learnings. Default destination is auto-memory
   (~/.claude/projects/<project-slug>/memory/). CLAUDE.md additions are
   hard-capped at ZERO per session by default; a candidate edit must pass all
   four checks to even be proposed: durable (applies indefinitely),
   project-wide (not one module or feature), not already covered, and not
   contradicting any existing CLAUDE.md rule. Edits failing any check route
   to auto-memory.
2. Check active plans and in-flight waves (via /bmad-status-wave's probe
   set); surface closure-pending epics.
3. Reconcile TODO.md: move items whose PRs merged from Open to Closed under
   today's date heading; refresh the Last updated line.
4. Reconcile HANDOFF.md: rewrite the Current State table (Stage, Wave, Step,
   Status traffic light), Key Design Decisions Since Last Handoff,
   Blocked-On, and the forward-looking Next Session Proposal.
5. Check for unpushed commits (`git log @{u}..` per branch); report them.
6. Confirm the wrap is complete; write the triage report; propose the next
   session's work.

## The Contradiction Scan (step 1 support)
Before proposing any CLAUDE.md edit, scan existing CLAUDE.md for any rule the
edit would supersede or undermine, over the --scope window; on any hit,
resolve the contradiction first or route the learning to auto-memory. Cap
the surfaced list at the top 20 contradictions.

## Report
Exactly one file per invocation: _bmad-output/session-wrap/<ts>/triage.md,
where <ts> is the invocation's UTC minute (colons replaced by hyphens, e.g.
2026-07-01T22-30-00Z). A second run in the same minute overwrites; a later
run creates a new directory. No locking; a lost report is regenerated from
fresh inputs.

## Error Handling
- CLAUDE.md does not exist: warn; steps 3-6 still run; step 1 routes
  everything to auto-memory.
- No active waves: steps 2's wave portion is a clean no-op.
- /bmad-status-wave output malformed: degrade to direct probes; note it.
- Disk full or output directory unwritable: exit 1 (the only error exit).
