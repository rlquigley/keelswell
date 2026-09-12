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

## Current state: the deletion cannot recur

`manifest.yaml` now records `ides: [claude-code]` only. A refresh with
`--tools claude-code` computes nothing-to-remove; scratch-clone
experiment confirmed `.agents/` (1051 files) survives untouched. The
tree is simply UNMANAGED: refreshes update `.claude/skills` and leave
`.agents/skills` a frozen pre-v0.3.0 snapshot (its vanilla personas
still carry upstream names). Never pass a `--tools` list that names an
`.agents/`-owning platform unless you intend the installer to take
ownership of (and regenerate) that tree.

## What a refresh DOES clobber, and what protects you

Class A -- fork edits to upstream-owned skills: overwritten from the
upstream package. As of v0.4.0 the only such edit (the
bmad-retrospective Mat Cauthon recast) ships via marketplace.json, and
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
(scratch-verified: resolver yields all Wheel of Time names after a
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
   --key agents` shows Wheel of Time names; `./install.sh
   --validate-only --skip-mcp-check` exits 0; spot-activate one vanilla
   agent (expects its WoT persona). Precondition for the validate step:
   config/agent-names.yaml.default must carry the same agents as
   config/agent-names.yaml (the validator asserts equal counts). Sync
   the .default whenever an agent is added, or this step fails for a
   reason unrelated to the refresh (it did at 0.8.0: 32 vs 38).
5a. Run the post-pull check from docs/harness-conversion-prompts.md
   ("Standing item"): confirms the harness enforcement layer survived
   the refresh, diffs upstream's changes against the fork-owned seams,
   and drafts the CHANGELOG entry (what changed, what we chose not to
   adopt). Its step 1 is Phase 4's conformance check: the harness
   invariants and hook checks step 5's --validate-only already ran, read
   as a pass/fail per invariant. Run all three steps.
6. Diff-review, commit, merge.

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
greet under Wheel of Time names (the fork's marketplace copies win);
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
