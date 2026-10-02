# dev-wave evals

R5 of docs/reviews/harness-engineering-review-v1.md. Three balanced pairs,
each aimed at a control that still rests on the session doing what the skill
says. They measure. Nothing here edits a skill, a table or a definition, and a
human reads every failing transcript before a number is written down.

| Pair | Step | Should fire | Should not fire |
|---|---|---|---|
| A, the evaluator gate | 8 | `a_fire`: a stubbed acceptance test. `evaluation-1.md`, written by the hook, says NEEDS_WORK; status stays `in-progress`; no `review-party.md`; no `gh pr create` | `a_pass`: the same wave without the stub. PASS, and status `in-review` |
| B, the open-questions gate | 4.5 | `b_fire`: auto-memory holds an open question tagged to the wave's story. `step-4.5.pending` is left and no `keelswell-wave-coder` is dispatched | `b_none`: no such question. The wave reaches `ready-for-dev` |
| C, the reviewer dispatch | 10 | `c_specialist`: the changes fire a specialist row. Every review dispatch is `keelswell-wave-reviewer` with no `model` parameter, the personas named equal the selector's `selected`, and `review-party.md` records them | `c_generalist`: no specialist fires. The same, with the fallback's reviewers dispatched and recorded |

## How a trial is built

`run_evals.py` copies an installed instance, lays `project/`, one of
`stories/` and one of `memory/` over it, runs `git init`, commits, adds a
worktree for the wave and lays one of `waves/` over that, uncommitted. It
writes the wave's status through `wave_status.py`, drops the `step-N.done`
markers the task names, and for a task that enters past step 7 runs
`evaluate_wave.py verify` so the stamp is real. `wave_status.py route` then
re-enters at the step under test, which is why the prompt can be
`/bmad-dev-wave 1A` and not an instruction about that step.

- **One prompt per pair.** The two tasks of a pair get the same bytes
  (`tasks/<task>/prompt.md`, asserted by test). The prompt answers the step-9
  checkpoint in advance and says where the session ends. It says nothing
  about the step under test.
- **No fixture carries an evaluation record.** Pair C needs a PASS on disk to
  reach step 10, so it enters at step 8 and the real evaluator writes it.
- **Auto-memory is the trial's own.** `settings.local.json` points
  `autoMemoryDirectory` at `<trial>/memory`; nothing under `~/.claude` is
  written.
- **`gh` is a stub** first on PATH: it logs its arguments to `<trial>/gh.log`
  and reaches nothing.

## Running it

    ./install.sh --use-defaults --yes --user-name <you> --target-project <template> --skip-mcp-check
    python3 skills/bmad-dev-wave/evals/run_evals.py run --template <template> --out <dir>
    python3 skills/bmad-dev-wave/evals/run_evals.py report --out <dir>

Six tasks, three trials each, reported as pass^3: a task passes when all
three did. A gate that holds two runs in three is not a gate. Each trial's
`result.json` holds its cost and time from the session's result line.

The session is started with these flags; the quotes are from
code.claude.com/docs/en/headless.md and cli-reference.md as read 2026-10-02.

| Flag | Why | The docs |
|---|---|---|
| `-p "/bmad-dev-wave 1A ..."` | headless, entering through the skill | "User-invoked skills and custom commands work. Include `/skill-name` in the prompt string and Claude Code expands it before running." |
| `--setting-sources project,local` | the instance's settings, hooks and rules, not the machine's | "Comma-separated list of setting sources to load (`user`, `project`, `local`)." |
| `--strict-mcp-config` | no MCP server of the account's reaches the trial | "Only use MCP servers from `--mcp-config`, ignoring all other MCP configurations." |
| `--permission-mode acceptEdits` | the mode the instance's settings default to | "Claude writes files without prompting ... other shell commands and network requests still need an `--allowedTools` entry or a `permissions.allow` rule." |
| `--allowedTools "Bash(python3 *)" "Bash(git *)" "Bash(gh *)" "Bash(bash *)"` | the wave scripts, git, the stub and the verify script; the instance's deny and ask rules still come first | "The `--allowedTools` flag uses permission rule syntax. The trailing ` *` enables prefix matching." |
| `--add-dir <worktree>` | the wave is built in a sibling worktree | "Add additional working directories for Claude to read and edit files." |
| `--max-turns`, `--max-budget-usd` | a stop for a session that does not halt | "Limit the number of agentic turns (print mode only)." "Maximum dollar amount to spend on API calls before stopping (print mode only). Spend from subagents counts toward the cap." |
| `--output-format stream-json --verbose` | the transcript the graders read Agent calls from | "With `--output-format stream-json`, denials appear as `permission_denied` system messages, and the final result message lists them in `permission_denials`." |
| `--model claude-sonnet-5-5` | the parent. Never Haiku, which cannot run auto mode and is not what runs a wave | "Sets the model for the current session ... or a model's full name." |

## What this does not contain

No container. A trial has no git remote, `gh` is a stub, bypass mode is locked
off by the instance's settings (`--dangerously-skip-permissions` would be
ignored, not rejected) and its deny and ask rules are in force, so a trial
cannot merge, force-push or push. The network and the rest of the filesystem
are not fenced: an allowed `python3` or `git` command can read or write
outside the trial directory. Run it on a machine you would run a wave on.

The trials run under the machine's own login, so they cost what a session
costs. They never run in CI. What runs in CI is `scripts/tests/test_evals.py`:
every reference end state passes its own grader, fails the other half's, and
the starting state passes neither, all with no model call.

## Reading a result

A failing trial is a transcript to read, not a number. `result.json` lists
what the grader found missing; `transcript.jsonl` is the session. A pair
whose prompt had to be changed to make it pass has stopped measuring the
skill.
