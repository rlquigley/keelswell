#!/usr/bin/env python3
"""Run the dev-wave eval pairs: one headless session per trial, graded on end state.

R5 of docs/reviews/harness-engineering-review-v1.md. Three balanced pairs, six
tasks, each entered at the step under test from checkpoint markers:

    A  the evaluator gate, step 8        a_fire / a_pass
    B  the open-questions gate, step 4.5 b_fire / b_none
    C  the reviewer dispatch, step 10    c_specialist / c_generalist

The two tasks of a pair get the same prompt, byte for byte. Only the fixture
differs, so a pair cannot pass by being told which half it is.

A trial is a fresh copy of an installed instance with the fixture project laid
over it, its own `git init`, a worktree for the wave, a `gh` on PATH that logs
its arguments and reaches nothing, and one `claude -p` session under the
machine's own login. Graders (graders.py) read what is left on disk and the
Agent calls in the transcript. k trials per task, reported as pass^k: every
trial passed, or the task did not.

    python3 run_evals.py run --template <installed instance> --out <dir> \\
        [--task a_fire ...] [--trials 3]
    python3 run_evals.py scaffold --task a_fire --out <dir> [--template <dir>]
    python3 run_evals.py grade --task a_fire --trial <dir>
    python3 run_evals.py report --out <dir>

`--template` is a directory `install.sh --target-project` has written. Without
it `scaffold` builds a bare trial holding only what the wave scripts read,
which is what the unit tests use; a session cannot run in one.

THIS MEASURES AND NOTHING ELSE. It edits no skill, no table and no definition.
A human reads every failing transcript before a number is written down.

NOT A CONTAINER. A trial has no git remote and a stub `gh`, bypass mode is
locked off by the instance's settings and its deny and ask rules are in force,
so it cannot merge or push. The network and the rest of the filesystem are
not fenced.

Stdlib only.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))
import evaluate_wave  # noqa: E402
import graders  # noqa: E402
import wave_status  # noqa: E402
from graders import PROJECT, WAVE, WORKTREE  # noqa: E402

TASKS = HERE / "tasks"
BRANCH = "wave-1a-story"
MODEL = "claude-sonnet-5-5"   # the parent. Never Haiku: it cannot run auto mode.
ALLOWED = ("Bash(python3 *)", "Bash(git *)", "Bash(gh *)", "Bash(bash *)")

GH_STUB = """#!/usr/bin/env bash
# Eval stub: logs its arguments and reaches nothing.
echo "$*" >> "$(dirname "$0")/../gh.log"
case "$1 $2" in
  "auth status") echo "github.com: logged in as eval-stub" ;;
  "pr create") echo "https://example.invalid/eval/pull/1" ;;
esac
exit 0
"""


class EvalError(Exception):
    pass


def load_task(name):
    path = TASKS / name / "task.json"
    if not path.is_file():
        raise EvalError(f"no task {name!r}; known: {', '.join(task_names())}")
    task = json.loads(path.read_text(encoding="utf-8"))
    task["name"] = name
    task["prompt"] = (TASKS / name / "prompt.md").read_text(encoding="utf-8")
    return task


def task_names():
    return sorted(p.parent.name for p in TASKS.glob("*/task.json"))


def _git(cwd, *args):
    proc = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise EvalError(f"git {' '.join(args)} failed in {cwd}: {proc.stderr.strip()}")
    return proc.stdout


def _overlay(source, target):
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)


def _bare_template(target):
    """The least a trial needs for the wave scripts to run: the evaluator's
    definition, found by walking up to the checkout that ships it."""
    for parent in HERE.parents:
        agents = parent / ".claude" / "agents"
        if (agents / "keelswell-wave-evaluator.md").is_file():
            shutil.copytree(agents, target / ".claude" / "agents")
            return
    raise EvalError("no .claude/agents/keelswell-wave-evaluator.md above this file")


def _set_status(proj, status):
    code, _, lines = wave_status.set_status(proj, WAVE, status)
    if code != 0:
        raise EvalError("wave_status.set_status refused: " + " ".join(lines))


# --------------------------------------------------------------- the trial

def scaffold(task, trial, template=None):
    """Build one trial directory at the state the task starts from."""
    trial = Path(trial)
    if trial.exists():
        raise EvalError(f"{trial} exists; a trial starts from nothing")
    proj, worktree = trial / PROJECT, trial / WORKTREE
    if template:
        shutil.copytree(template, proj, ignore=shutil.ignore_patterns(".git"))
    else:
        proj.mkdir(parents=True)
        _bare_template(proj)
    _overlay(HERE / "project", proj)
    _overlay(HERE / "stories" / task["story"], proj)
    # Where a secret scanner runs on commit, a fresh instance's first commit
    # trips on vendored test-pattern docs. The fork's own allowlist names
    # them; an instance has none yet, so the trial borrows the fork's. The
    # scanner still runs.
    for parent in HERE.parents:
        if (parent / ".gitleaks.toml").is_file() and not (proj / ".gitleaks.toml").exists():
            shutil.copy(parent / ".gitleaks.toml", proj / ".gitleaks.toml")
            break

    memory = trial / "memory"
    shutil.copytree(HERE / "memory" / task["memory"], memory)
    local = proj / ".claude" / "settings.local.json"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(json.dumps({"autoMemoryDirectory": str(memory)}, indent=2) + "\n",
                     encoding="utf-8")

    _git(proj, "init", "-q", "-b", "main")
    _git(proj, "config", "user.email", "eval@example.invalid")
    _git(proj, "config", "user.name", "eval")
    _git(proj, "config", "commit.gpgsign", "false")
    # .bmad/ is the wave's state and is in no instance's history; the local
    # settings file is per-trial. Neither may make the tree look dirty. An
    # installed instance ignores __pycache__/ already; a bare trial has no
    # .gitignore, and an untracked __pycache__ path fires the performance
    # row's `**/*cache*` glob.
    (proj / ".git" / "info").mkdir(exist_ok=True)
    with open(proj / ".git" / "info" / "exclude", "a", encoding="utf-8") as f:
        f.write(".bmad/\n.claude/settings.local.json\n__pycache__/\n")
    _git(proj, "add", "-A")
    _git(proj, "commit", "-q", "-m", "fixture: the project on main")
    _git(proj, "worktree", "add", "-q", "-b", BRANCH, str(worktree))
    # Uncommitted, as the wave leaves it: step 11 is where the commits are made.
    _overlay(HERE / "waves" / task["wave"], worktree)

    for status in task["status"]:
        _set_status(proj, status)
    state = wave_status.wave_dir(proj, WAVE)
    state.mkdir(parents=True, exist_ok=True)
    for step in task["markers"]:
        (state / f"step-{step}.done").touch()
    if task.get("verify"):
        code, _, lines = evaluate_wave.verify(worktree, WAVE)
        if code != 0:
            raise EvalError("the fixture's own verify run failed: " + " ".join(lines))

    stub = trial / "bin" / "gh"
    stub.parent.mkdir()
    stub.write_text(GH_STUB, encoding="utf-8")
    stub.chmod(0o755)
    (trial / "gh.log").touch()
    return trial


def apply_reference(task, trial):
    """Turn a scaffolded trial into the task's reference end state.

    No model is called. The evaluation record is written by the hook's own
    entry point from a report in the evaluator's format, the status by
    wave_status, and the Agent calls into a transcript in the shape the CLI
    prints. A grader that fails this is a broken grader, not a broken skill.
    """
    trial = Path(trial)
    ref = task["reference"]
    proj, worktree = trial / PROJECT, trial / WORKTREE
    state = wave_status.wave_dir(proj, WAVE)
    events = []

    def agent(subagent_type, prompt):
        events.append({"type": "assistant", "parent_tool_use_id": None, "message": {
            "content": [{"type": "tool_use", "id": f"toolu_{len(events)}", "name": "Agent",
                         "input": {"subagent_type": subagent_type, "prompt": prompt}}]}})

    if ref.get("pending"):
        (state / graders.PENDING).write_text(ref["pending"] + "\n", encoding="utf-8")
    if ref.get("verdict"):
        session = "reference-session"
        code, _, lines = evaluate_wave.dispatch(worktree, WAVE, session)
        if code != 0:
            raise EvalError("dispatch refused the reference: " + " ".join(lines))
        agent(graders.EVALUATOR, f"Evaluate wave {WAVE}.")
        finding = "### [HIGH] AC-2's test asserts nothing\n" \
            if ref["verdict"] == evaluate_wave.NEEDS_WORK else ""
        evaluate_wave.record({
            "hook_event_name": "SubagentStop", "agent_type": graders.EVALUATOR,
            "agent_id": "reference", "session_id": session, "cwd": str(proj),
            "last_assistant_message":
                f"VERDICT: {ref['verdict']}\nWAVE: {WAVE}\nPASS: 1\n\n## Findings\n{finding}"})
    for status in ref.get("status", []):
        _set_status(proj, status)
    if ref.get("selector"):
        tool_id = f"toolu_{len(events)}"
        events.append({"type": "assistant", "parent_tool_use_id": None, "message": {
            "content": [{"type": "tool_use", "id": tool_id, "name": "Bash", "input": {
                "command": "python3 scripts/select_reviewers.py select --json"}}]}})
        events.append({"type": "user", "message": {"content": [{
            "type": "tool_result", "tool_use_id": tool_id,
            "content": json.dumps(ref["selector"])}]}})
    for prompt in ref.get("reviewers", []):
        agent(graders.REVIEWER, prompt)
    if ref.get("review_record"):
        (worktree / "docs" / f"wave-{WAVE.lower()}" / "review-party.md").write_text(
            ref["review_record"], encoding="utf-8")
    events.append({"type": "result", "subtype": "success", "is_error": False,
                   "total_cost_usd": 0.0, "duration_ms": 0, "num_turns": 0})
    (trial / "transcript.jsonl").write_text(
        "".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return trial


def run_trial(task, trial, template):
    """One headless session in a fresh trial. Returns the trial's result row."""
    scaffold(task, trial, template)
    trial = Path(trial).resolve()
    env = dict(os.environ, PATH=f"{trial / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}")
    argv = [
        "claude", "-p", task["prompt"],
        "--model", MODEL,
        "--output-format", "stream-json", "--verbose",
        "--setting-sources", "project,local",
        "--strict-mcp-config",
        "--permission-mode", "acceptEdits",
        "--add-dir", str(trial / WORKTREE),
        "--max-turns", str(task["max_turns"]),
        "--max-budget-usd", str(task["max_budget_usd"]),
        "--allowedTools", *ALLOWED,
    ]
    started = time.time()
    with open(trial / "transcript.jsonl", "w", encoding="utf-8") as out, \
            open(trial / "stderr.txt", "w", encoding="utf-8") as err:
        proc = subprocess.run(argv, cwd=trial / PROJECT, env=env, stdin=subprocess.DEVNULL,
                              stdout=out, stderr=err)
    return grade(task, trial, exit_code=proc.returncode, wall=time.time() - started)


def grade(task, trial, exit_code=None, wall=None):
    t = graders.Trial(trial)
    failures = graders.GRADERS[task["name"]](t)
    result = t.result()
    row = {
        "task": task["name"], "trial": Path(trial).name, "passed": not failures,
        "failures": failures,
        "status": t.status(),
        "cost_usd": result.get("total_cost_usd"),
        "duration_s": round(result["duration_ms"] / 1000, 1) if result.get("duration_ms") else None,
        "wall_s": round(wall, 1) if wall is not None else None,
        "turns": result.get("num_turns"),
        "stop": result.get("subtype"),
        "denials": [d.get("tool_name") for d in result.get("permission_denials") or []],
        "agents": [c.get("subagent_type") for c in t.agent_calls()],
        "exit_code": exit_code,
    }
    (Path(trial) / "result.json").write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    return row


def report(out):
    rows = [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(Path(out).glob("*/*/result.json"))]
    lines = ["task           trials  passed  pass^k  cost_usd  mean_s"]
    for name in sorted({r["task"] for r in rows}):
        mine = [r for r in rows if r["task"] == name]
        passed = sum(r["passed"] for r in mine)
        cost = sum(r["cost_usd"] or 0 for r in mine)
        secs = [r["duration_s"] for r in mine if r["duration_s"]]
        lines.append(f"{name:<14} {len(mine):>6}  {passed:>6}  "
                     f"{'yes' if passed == len(mine) else 'no':>6}  {cost:>8.2f}  "
                     f"{sum(secs) / len(secs) if secs else 0:>6.0f}")
        for r in mine:
            for failure in r["failures"]:
                lines.append(f"    {r['trial']}: {failure}")
    total = sum(r["cost_usd"] or 0 for r in rows)
    lines.append(f"{len(rows)} trials, ${total:.2f} at list price as the CLI estimates it")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run", help="run trials: one headless session each")
    r.add_argument("--template", required=True, help="an installed instance to copy")
    r.add_argument("--out", required=True)
    r.add_argument("--task", action="append", help="repeatable; default every task")
    r.add_argument("--trials", type=int, default=3)
    s = sub.add_parser("scaffold", help="build one trial directory and stop")
    s.add_argument("--task", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--template")
    s.add_argument("--reference", action="store_true", help="then apply the reference end state")
    g = sub.add_parser("grade", help="grade a trial directory")
    g.add_argument("--task", required=True)
    g.add_argument("--trial", required=True)
    p = sub.add_parser("report", help="pass^k, cost and time per task")
    p.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        if args.command == "run":
            for name in args.task or task_names():
                task = load_task(name)
                for n in range(1, args.trials + 1):
                    trial = Path(args.out) / name / f"trial-{n}"
                    if (trial / "result.json").is_file():
                        continue  # a finished trial is never re-run over
                    row = run_trial(task, trial, args.template)
                    print(f"{name} trial {n}: {'pass' if row['passed'] else 'FAIL'} "
                          f"${row['cost_usd'] or 0:.2f} {row['duration_s']}s "
                          + "; ".join(row["failures"]), flush=True)
            print(report(args.out))
        elif args.command == "scaffold":
            task = load_task(args.task)
            scaffold(task, args.out, args.template)
            if args.reference:
                apply_reference(task, args.out)
            print(args.out)
        elif args.command == "grade":
            row = grade(load_task(args.task), args.trial)
            print(json.dumps(row, indent=2))
            return 0 if row["passed"] else 1
        else:
            print(report(args.out))
        return 0
    except EvalError as exc:
        print(f"run_evals: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
