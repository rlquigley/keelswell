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

Class C -- installer-owned regeneration, absorbed by design:
`_bmad/config.toml` comes back with upstream names, but the
`_bmad/custom/config.toml` overlay pins re-win at resolution
(scratch-verified: resolver yields all Wheel of Time names after a
refresh). `config.yaml` files reset `user_name`/timestamps and derive
`project_name` from the directory name -- cosmetic, restorable with git.

## The procedure

1. Work on a branch; confirm a clean tree.
2. Run the standard invocation (unchanged from install.sh
   phase4_upstream):
       npx bmad-method install --directory . --custom-source <this-repo> --tools claude-code --yes
3. Review `git status`. Expect: catalog regeneration (class B),
   config churn (class C), plus whatever the new upstream version
   legitimately changed. Anything unexpected: stop.
4. Restore class B via the git checkout above; re-apply intended
   catalog deltas if the upstream version added real skills.
5. Verify: `python3 _bmad/scripts/resolve_config.py --project-root .
   --key agents` shows Wheel of Time names; `./install.sh
   --validate-only --skip-mcp-check` exits 0; spot-activate one vanilla
   agent (expects its WoT persona).
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
duplicate-emission bug blocks redeclaring those agents in keelswell's
module.yaml. The skills themselves still greet under Wheel of Time
names (the fork's marketplace copies win); only registry consumers
(party-mode rosters, help displays) see the upstream name. Cosmetic;
fix by copying the fork's roster-pin blocks into the target project's
_bmad/custom/config.toml.
