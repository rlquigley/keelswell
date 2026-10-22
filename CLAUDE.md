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
