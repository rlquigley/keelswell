# Keelswell fork

This file is for sessions working on the fork itself. Instances get their
CLAUDE.md from `templates/CLAUDE.md.template`, not from this file.

## Harness Change Propagation

- A change to the fork's skills ships to every Keelswell instance. Find the
  instances at run time, never from a remembered list:

  ```bash
  find ~/Projects -maxdepth 5 -path '*/_bmad/_config/manifest.yaml' -not -path '*/worktrees/*' -not -path '*/_archive/*' | xargs grep -l -i keelswell
  ```

  Skip the fork's own entry. This repo is public: do not write instance or
  client names into it.
- Mirror `skills/` to `.claude/skills/`, then copy the changed skills into
  each instance and run
  `./install.sh --validate-only --target-project <instance> --skip-mcp-check`.
  Confirm each instance's skill trees match the fork before reporting done.
- Do not start a step that depends on a PR until
  `gh pr view <n> --json state` shows MERGED.
