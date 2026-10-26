# Keelswell fork

This file is for sessions working on the fork itself. Instances get their
CLAUDE.md from `templates/CLAUDE.md.template`, not from this file.

## Harness Change Propagation

- A change to the fork's skills ships to every Keelswell instance. Find the
  instances at run time, never from a remembered list:

  ```bash
  python3 tools/instance_drift.py --list
  ```

  It lists every project under `~/Projects` whose
  `_bmad/_config/manifest.yaml` names the keelswell module, skipping
  worktrees, `_archive` and the fork's own checkouts. This repo is public:
  do not write instance or client names into it.
- Mirror `skills/` to `.claude/skills/`, then copy the changed skills into
  each instance and run
  `./install.sh --validate-only --target-project <instance> --skip-mcp-check`.
  Before reporting done, `python3 tools/instance_drift.py` exits 0. Read
  any `drift` row before a sync overwrites it: that file holds content the
  fork never had.
- Do not start a step that depends on a PR until
  `gh pr view <n> --json state` shows MERGED.

## Process Diagrams

- README.md shows three swim-lane process maps, `docs/process-map-*.svg`,
  drawn by `tools/process_map.py` from the data at its top: high-level,
  detailed, and Keelswell's own skills. Before every `gh pr create` on
  this repository, compare the branch's diff with all three.
  If the change adds, removes or reorders an activity, a decision or a
  hand-off between lanes, edit the data and run
  `python3 tools/process_map.py` on the branch. A stale map fails
  tools/tests/test_process_map.py.
- The PR body says which, on a line of its own: `Diagrams: updated --
  <what changed>` or `Diagrams: no change -- <why>`.
  `tools/pr_diagram_check.py`, registered in `.claude/settings.json`,
  denies a `gh pr create` for this repository whose body has no such
  line. A PR on any other repository, such as an instance's, passes.
- Write the maps for a reader with no context: short verb phrases, and no
  skill, script, status or file names outside the skills map. GitHub's
  Mermaid cannot draw swim lanes, which is why the maps are generated SVGs.
