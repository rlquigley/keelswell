# Upstream refresh runbook (closes F-6)

How to safely run `npx bmad-method install` against this repo, based on
the 2026-07-19 investigation (installer source analysis at
bmad-method@6.10.0 plus scratch-clone experiments; full record in the
keelswell-manual repo, quickstart/trackF6-findings-v1.md).

## What actually happened in the original incident

The installer records installed IDE targets in
`_bmad/_config/manifest.yaml` (`ides:`). `.agents/skills` is the
cross-tool shared directory owned by ~24 platforms (codex, cursor,
copilot, windsurf, ...). The original substrate install had recorded one
of those tools; the Track A refresh passed `--tools claude-code` alone,
so the installer treated the `.agents/`-owning tool as deliberately
removed and wiped its target directory. By design, no confirmation:
"the user's IDE selection is the decision."

## Current state: the fork carries no `.agents/` tree

`manifest.yaml` records `ides: [claude-code]` only, so a refresh with
`--tools claude-code` computes nothing-to-remove and writes
`.claude/skills` alone. The fork's `.agents/skills` (74 directories,
1051 files) was deleted on 2026-10-01, R4 of
docs/reviews/harness-engineering-review-v1.md. No refresh had managed
it since the incident, so it was a frozen pre-v0.3.0 snapshot whose
vanilla personas still carried upstream names, and Claude Code never
read it: "Not read: AGENTS.local.md, AGENTS.override.md, or anything
under a .agents/ directory"
(https://code.claude.com/docs/en/memory#when-claude-code-reads-agentsmd).
It is in git history before that commit. Never pass a `--tools` list
that names an `.agents/`-owning platform unless you intend the
installer to create and own that tree. An instance's `.agents/` is the
instance's own: green-ledger tracks a second skill tree there, ffbapp
has an untracked one holding an unrelated plugin, and nothing in the
fork touches either.

## What a refresh DOES clobber, and what protects you

Class A -- fork edits to upstream-owned skills: overwritten from the
upstream package. As of v0.4.0 the only such edit (the
bmad-retrospective Devon recast) ships via marketplace.json, and
custom-module skills WIN over the upstream package for the same skill
id (scratch-verified for the 13 vanilla renames). Keep it that way: any
future fork edit to an upstream-owned skill must either be added to
marketplace.json + skills/ mirror, or it will silently revert on
refresh.

Class B -- generated catalogs: `_bmad/_config/bmad-help.csv`,
`skill-manifest.csv`, `files-manifest.csv`, and the module-help.csv
files are regenerated. The fork's curation is lost: the two
hand-authored DF-1 rows are dropped, ~34 auto-generated
"Keelswell,<skill>" rows are added (violating the sparse-catalog rule),
and skill-manifest gains duplicate rows (upstream + custom copies of the
same skill). The installer leaves `.bak` copies of module-help files.
Restore after refresh:

    git checkout -- _bmad/_config/bmad-help.csv \
                    _bmad/_config/skill-manifest.csv \
                    _bmad/core/module-help.csv _bmad/bmm/module-help.csv
    # then re-run any catalog additions the refresh legitimately needs
    # (bmad-help.csv: drop rows for removed skills, add rows for new real
    # skills from the package's module-help.csv files, refresh _meta URLs)

The restored skill-manifest.csv and module-help.csv files then describe
the layout BEFORE the refresh (skill ids that no longer exist, none of
the new ones). Nothing fork-side reads them and the installer
regenerates them on its next run, so this is accepted staleness, not a
defect to fix by hand.

Class C -- installer-owned regeneration, absorbed by design:
`_bmad/config.toml` comes back with upstream names, but the
`_bmad/custom/config.toml` overlay pins re-win at resolution
(scratch-verified: resolver yields all the fork's display names after a
refresh). `config.yaml` files reset `user_name`/timestamps and derive
`project_name` from the directory name -- cosmetic, restorable with git.

Class D -- `_bmad/scripts/`: the installer deletes the directory and
re-copies its own src/scripts/* on every run (6.10 and 6.12 both do
this). The fork's copies are vanilla, so it is invisible until upstream
changes a script; 6.12.0 did (resolve_config.py and
resolve_customization.py now import config_utils.py, render_skill.py
added). Two consequences: any file the fork places there is gone after
the next refresh, so fork scripts live under skills/ or _bmad/custom/;
and every tracked script's imports must be allowlisted in .gitignore
and templates/.gitignore.template or a fresh clone gets broken
resolvers.

## The procedure

1. Work on a branch; confirm a clean tree.
2. Confirm which version npx will resolve (`npm view bmad-method
   dist-tags`; `latest`, never a -next prerelease) and pin it:
       npx bmad-method@X.Y.Z install --directory . --custom-source <this-repo> --tools claude-code --yes
   Deliberately no --modules. install.sh phase4_upstream passes
   --modules bmm,cis,tea,bmb, which is right for a fresh target but on an
   existing install makes the installer deselect and delete every
   installed module not in that list (bmad-loop; verified at 6.12.0).
   With --yes and no --modules the installer selects installed plus
   defaults and keeps everything. The two invocations are not
   equivalent for a refresh.
3. Review `git status`. Expect: catalog regeneration (class B),
   config churn (class C), plus whatever the new upstream version
   legitimately changed. Anything unexpected: stop.
4. Restore class B via the git checkout above; re-apply intended
   catalog deltas if the upstream version added real skills.
5. Verify: `python3 _bmad/scripts/resolve_config.py --project-root .
   --key agents` shows the fork's display names; `./install.sh
   --validate-only --skip-mcp-check` exits 0; spot-activate one vanilla
   agent (expects its fork display name). Precondition for the validate step:
   config/agent-names.yaml.default must carry the same agents as
   config/agent-names.yaml (the validator asserts equal counts). Sync
   the .default whenever an agent is added, or this step fails for a
   reason unrelated to the refresh (it did at 0.8.0: 32 vs 38).
5a. Run the post-pull check from docs/harness-conversion-prompts.md
   ("Standing item"): confirms the harness enforcement layer survived
   the refresh, diffs upstream's changes against the fork-owned seams,
   and drafts the CHANGELOG entry (what changed, what we chose not to
   adopt). Its step 1 is Phase 4's conformance check: the harness
   invariants, hook checks and permission rules step 5's --validate-only
   already ran, read as a pass/fail per invariant. Run all three steps.
6. Diff-review, commit, merge.

## Instances: the hook registration and the permission block are a hand step

Nothing rewrites an existing instance's `.claude/settings.json`: a
refresh never touches it and `install.sh --target-project` writes one
only into a fresh target. So what `templates/settings.json.template`
carries for the harness reaches a live instance by hand: the gate's
registration (R1 of docs/reviews/harness-engineering-review-v1.md), the
permission block (R2) and the evaluator hook's three registrations (R3).
R4 adds nothing to an instance's settings: what it changed in the
template (seven dead keys gone, `effortLevel` in place of
`reasoningEffort`) sits outside the `hooks` and `permissions` blocks,
which are all a live instance carries. R4 reaches an instance as files:
the seven wave skills and the three subagent definitions.
As of 2026-10-01 both live instances (ffbapp, green-ledger) carry R1 and
R2 and neither R3 nor R4: the template's first PreToolUse entry and its
permission block, the wrappers wave-gate.sh and wave-session-end.sh, and
bmad-dev-wave 1.8.2. Both were byte-identical to fork commit 3436373 on
that date, so the copy below overwrites nothing local; re-check that
before copying (`git show <commit>:<path> | diff - <instance copy>`) and
stop on drift. One pass of the steps below covers R3 and R4 together.

From the fork on main, per instance:

1. Skills, wrappers and the subagent definitions. The skills go into
   every tool tree the instance has (green-ledger also carries `.agents/skills`):
       for s in bmad-create-wave bmad-dev-wave bmad-merge-wave bmad-resume-wave \
                bmad-status-wave bmad-close-epic bmad-wrap; do
         cp -R skills/$s/. <instance>/.claude/skills/$s/
       done
       cp .claude/hooks/wave-gate.sh .claude/hooks/wave-evaluator-record.sh \
          <instance>/.claude/hooks/
       cp .claude/agents/*.md <instance>/.claude/agents/
   Three definitions travel: keelswell-wave-evaluator.md (`effort: high`
   since R3, which the new skill's `dispatch` refuses to go without, and
   a full model id since R4), and R4's keelswell-wave-coder.md and
   keelswell-wave-reviewer.md, which dev-wave 1.10.0 dispatches by name at
   steps 6 and 10. All seven wave skills changed in R4 (frontmatter; see
   the CHANGELOG), so all seven are copied.
2. Settings. In `<instance>/.claude/settings.json`, make the `hooks`
   block carry the template's entries for the harness: the two
   PreToolUse entries (wave-gate.sh on the file and shell tools, exec
   form on `${CLAUDE_PROJECT_DIR}`, `"args": []`, `"timeout": 30`,
   Monitor in the matcher; wave-evaluator-record.sh on
   `SubagentHandback`), the PostToolUse entry on `SubagentHandback`, and
   the SubagentStop entry on `keelswell-wave-evaluator`. The three R3
   entries are one line each in the template; paste them as they stand.
   Add a `permissions` object holding the template's `deny` list, `ask`
   list and `"disableBypassPermissionsMode": "disable"`. Leave out
   `defaultMode`, `model` and the template's other keys: an instance
   keeps its own mode and model. The instance may add rules and hooks of
   its own; it may not drop one of the template's.
3. The verify script. Step 7 runs `tests/verify-fast.sh` from the
   worktree root and nothing else, and `evaluate_wave.py verify` exits 3
   without it. ffbapp has one; green-ledger had none on 2026-10-01. A
   project whose suite lives elsewhere gives the file one line that
   calls it.
4. Check. `./install.sh --validate-only --skip-mcp-check
   --target-project <instance>` exits 0. Until steps 1 and 2 are done it
   exits 7 and names every missing wrapper, registration and rule, which
   is the list to paste (measured on both instances, 2026-10-01: the
   wrapper, its registration, and the three events). Since R4 it also
   names any definition that is missing or whose `model:` or `effort:`
   differs from the fork's `core/config.yaml`. Then
   `diff -rq -x __pycache__ skills/<skill>
   <instance>/.claude/skills/<skill>` prints nothing for each of the
   seven, and the instance's own unit tests pass.
5. Commit in the instance: ffbapp by pull request, green-ledger on a
   branch merged ff-only (it has no remote).

What to expect afterwards:

- Claude Code reads rules in the order deny, ask, allow, whichever file
  a rule sits in, and a deny cannot be lifted by an allow anywhere. So a
  personal allow such as ffbapp's `Bash(gh pr *)` no longer reaches
  `gh pr merge`, and `gh auth token` and a plain `git worktree remove`
  prompt despite `Bash(gh auth *)` and `Bash(git worktree *)`.
- A worktree reads the settings.json of its own checkout. One cut before
  the instance's commit has neither the rules nor the new registrations
  until it takes the instance's main. A session rooted there gets no
  evaluator record at all: nothing writes one, `evaluate_wave.py verdict`
  exits 3, and the review rule keeps the wave out of review.
- No session records a verdict. Step 8 runs `evaluate_wave.py dispatch`,
  dispatches the evaluator, and reads `evaluate_wave.py verdict`; the
  hook writes `evaluation-<n>.md` in between. `evaluate_wave.py record`
  from Bash is denied by the gate. In auto mode a report the hook sends
  back shows up as a denied SubagentHandback call, twice at most.
- A wave whose `verify-output.txt` was written by hand, or before R3,
  carries no stamp, and `dispatch` exits 3 until `verify` has run. Dev-wave's
  steps 7 to 9 changed order (7 verify, 8 evaluation, 9 preview), so a
  wave paused between the old steps 7 and 10 re-enters by markers that
  meant something else; neither instance had one on 2026-10-01.
- The Bash rules match the command as written. They do not match
  `git -C <path> ...`, `git -c key=value ...`, `bash -c '...'`, a binary
  named by absolute path or a quoted subcommand. bmad-merge-wave writes
  its cleanup as `git -C MAIN_REPO ...`, so those calls are decided by
  the session's permission mode, not by these rules.
- The two Edit rules are anchored at the project root. A session rooted
  in the main checkout is not stopped by them from writing a sibling
  worktree's `docs/wave-<id>/evaluation-<n>.md`; the hook's verdict rule
  is what covers that path.
- Since R4 a wave's coders run at claude-sonnet-5-5 and its reviewers
  and evaluator at claude-opus-5-5, all at effort high, whatever model
  the session is on. A session on a cheaper model now pays for Opus
  reviewers; a session on a newer one no longer lends them its model.
- The session's own effort is unchanged in a live instance. A fresh
  `--target-project` install gets `"effortLevel": "high"`, which in a
  project file "applies to every model"
  (https://code.claude.com/docs/en/settings-reference#effortlevel); an
  instance that wants it adds that line by hand.

## Subagent routing: the tier table, the re-pin and the override

`core/config.yaml` is the tier table and nothing else: two tiers
(`frontier`, `workhorse`), each a full model id, and three roles, each a
tier and an effort. The `orchestrator` row fills `model` and
`effortLevel` in a fresh instance's settings.json. The `coding` and
`adversarial` rows name the definitions under `.claude/agents/` that
must carry them: keelswell-wave-coder, and keelswell-wave-reviewer and
keelswell-wave-evaluator. `install.sh` phase 6 reads both sides and
exits 7 naming the definition that differs. Nothing generates the
definitions and nothing repairs them.

Re-pin at each model release, in one commit: the tier's `model:` in
`core/config.yaml`, the `model:` line of every definition on that tier,
the model string in dev-wave's The Review Record, and a CHANGELOG line.
`./install.sh --validate-only --skip-mcp-check` exits 0 only when the
table and the definitions agree. A full id does not follow a release
and does not warn when its model retires; the retirement dates are at
https://platform.claude.com/docs/en/about-claude/models/overview
(on 2026-10-01: Opus 5.5 "Not sooner than September 22, 2027", Sonnet
5.5 "Not sooner than September 28, 2027").

What outranks a definition's `model:`
(https://code.claude.com/docs/en/sub-agents#choose-a-model):

- The Agent tool's per-invocation `model` parameter. Dev-wave's The
  Routing tells the session not to pass one; nothing enforces that. An
  `Agent(model:...)` deny rule would, and would apply to every Agent
  call in the instance, so none is shipped.
- `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`, the deliberate override. While
  it is on, "Claude Code ignores the `model` field of every subagent
  definition" and the session cannot pass one either. Set it with
  `CLAUDE_CODE_SUBAGENT_MODEL=<alias or id>` and every subagent runs on
  that model; set it alone and they run on the session's. Use it to run
  a whole wave on one model on purpose (a cost cap, a model under
  test), in the shell or the `env` block of `.claude/settings.local.json`,
  and write the model that ran into the wave's review record. Requires
  Claude Code v2.1.257 or later.

`CLAUDE_CODE_SUBAGENT_MODEL` by itself is only a default: a definition's
`model:` outranks it. `effort:` has no such override; frontmatter effort
yields only to the `CLAUDE_CODE_EFFORT_LEVEL` environment variable and
to a `maxEffortLevel` cap.

## Known limitation (F-10, closed for documented installs)

A minimal fresh install (`--tools claude-code`, no `--modules`) installs
only core + keelswell: the bmm/cis/tea/bmb module config.yaml files do
not exist, so vanilla agents' Step 5 config loads degrade. The
documented install command (README) therefore carries
`--modules bmm,cis,tea,bmb` -- scratch-verified to produce all four
module config.yaml files, 97 skills, and a valid config.toml.
module.yaml cannot provide those configs itself (they belong to modules
the user did or did not install).

Residual nuance for fresh installs into OTHER projects: the vanilla 13
agents' descriptor blocks come from the upstream module.yaml files
(upstream names), because the fork's _bmad/custom/config.toml overlay
pins do not travel with a marketplace install and the upstream
duplicate-emission bug (filed: bmad-method#2606) blocks redeclaring
those agents in keelswell's module.yaml. The skills themselves still
greet under the fork's display names (the fork's marketplace copies win);
only registry consumers (party-mode rosters, help displays) see the
upstream name. Cosmetic; fix by copying the fork's roster-pin blocks
into the target project's _bmad/custom/config.toml.

## Git-URL installs: pin the release tag

Use `--custom-source https://github.com/rlquigley/keelswell@vX.Y.Z`.
The pin makes installs deterministic (clone-cache channel "pinned" plus
the resolved SHA). The persisted manifest.yaml still records
"version: main" for git-URL sources regardless -- a field mismatch in
the installer's getModuleVersionInfo (reads cloneRef, parser stores the
ref in version; filed: bmad-method#2607). Local-path sources record the
real version correctly. Cosmetic either way; the install-time display
line is always right.
