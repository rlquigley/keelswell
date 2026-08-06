---
name: bmad-wrap
description: >
  Session-end triage. Triages session learnings into auto-memory (CLAUDE.md
  edits are rare and hard-capped), checks active plans, reconciles TODO.md
  and HANDOFF.md, checks for unpushed commits, opens the working
  branch's missing PR (on confirmation) or halts until an existing
  open PR is merged and validated, confirms the wrap, proposes
  next-session options with one tagged recommended, generating a
  copy-pasteable kickoff prompt and suggested run mode (auto, accept
  edits, plan, manual) from the user's selection, and ends by naming
  the session (32 characters max) from a session summary. Run at the
  end of every working session, whether or not a wave was active.
when-to-use: |
  At the end of every working session. A finished wave needs its learnings
  captured; an unfinished wave needs a handoff the next session can resume
  from; the same discipline covers both.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash          # read-only allow-list: git status, git log, git diff,
                  # git branch, date, gh pr list / view. Sole exception,
                  # gated on the user's step-6 confirmation: git push of
                  # the working branch + gh pr create (step 5). No other
                  # mutating git commands, ever.
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
version: 1.5.0
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
3. Reconcile TODO.md: remove items whose PRs merged, so TODO.md holds
   open items only; list each removal in the triage report under a
   Closed heading; refresh the Last updated line. Closure history
   lives in the triage reports and TODO.md's git history, never as a
   growing section of TODO.md itself.
4. Reconcile HANDOFF.md: rewrite the Current State table (Stage, Wave, Step,
   Status traffic light), Key Design Decisions Since Last Handoff,
   Blocked-On, and the forward-looking Next Session Proposal -- an
   options list with one recommended, the user's selection, and the
   kickoff prompt and run-mode suggestion generated from it (see The
   Next Session Proposal).
5. Check for unpushed commits (`git log @{u}..` per branch); report
   them. Then check the working branch's PR state (`gh pr list
   --head <branch> --state all`):
   - No PR at all, and the branch has commits main lacks: propose
     creating one; on the user's confirmation at step 6, push the
     branch and open the PR. Never push or open a PR without that
     confirmation.
   - PR open, not merged: halt and ask the user to merge it. When
     the user reports it merged, validate with gh (state MERGED); on
     a failed validation, say so and ask again -- never proceed on
     an unvalidated claim. Once validated, re-apply step 3 to items
     the merge closed, then resume the wrap.
   - PR merged: nothing to open; note it in the report.
6. Confirm the wrap is complete; write the triage report; restate the
   selected option with its kickoff prompt block and run-mode line;
   end by naming the session (see The Session Name).

## The Contradiction Scan (step 1 support)
Before proposing any CLAUDE.md edit, scan existing CLAUDE.md for any rule the
edit would supersede or undermine, over the --scope window; on any hit,
resolve the contradiction first or route the learning to auto-memory. Cap
the surfaced list at the top 20 contradictions.

## The Next Session Proposal (step 4 support)
The proposal is a selection dialogue, not a single suggestion:
1. Draft two to four candidate options for the next session's work,
   drawn from step 2's findings (in-flight waves, closure-pending
   epics, blocked items) and open TODO.md entries. Each option is one
   or two lines: the work, and why it is a candidate now.
2. Tag exactly one option "(recommended)", with a one-line reason.
3. Present the list and wait for the user to select an option.
4. Generate the kickoff prompt from the selected option: exactly one
   fenced code block, a copy-pasteable first message for the next
   session. It must be self-contained -- name the skill or command to
   invoke, the target (wave, story, epic, or standalone task), and the
   key file paths -- and must not depend on the wrapped session's
   context to make sense. The prompt always instructs the session to
   create a new branch (named for the work) and work in it, never
   directly on main.
5. With the prompt, suggest the mode to run it in -- auto, accept
   edits, plan, or manual -- matched to the selected work: plan for
   unscoped or design-heavy work, accept edits for well-specified
   implementation, auto for mechanical low-risk work, manual when the
   work is risky or destructive. One line directly below the prompt
   block: the mode, and why.
Step 4 then writes the full options list, the selection, the kickoff
prompt block, and the run-mode line into HANDOFF.md's Next Session
Proposal; step 6 repeats the block and mode line verbatim in the
triage report and in the wrap confirmation, so the prompt is at hand
both at wrap time and when the next session opens HANDOFF.md.

## The Session Name (step 6 support)
The wrap's final act is naming the session. Write a one-or-two-sentence
summary of what the session actually did, then derive the session name
from that summary: at most 32 characters, ASCII. The cap is hard --
count before emitting. The summary and name close the triage report,
and the name is the last line of the wrap confirmation, ready to use
as the session title.

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
- User does not select an option: the recommended option is treated as
  selected; the report notes the default was taken.
- No remote or gh unavailable at step 5: report the PR gap and print
  the would-be commands; never fail the wrap over it.
- User declines to merge at step 5: proceed; record the open PR under
  HANDOFF.md's Blocked-On and in the report.
- Disk full or output directory unwritable: exit 1 (the only error exit).
