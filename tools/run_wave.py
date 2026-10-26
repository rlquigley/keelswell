#!/usr/bin/env python3
"""Run one wave of a Keelswell instance headless, for a run no one watches.

    python3 tools/run_wave.py <project> <wave> [--through-step N] [--resume]
        [--max-budget-usd X] [--allow RULE ...] [--log-dir DIR]

Starts `claude -p "/bmad-dev-wave <wave> ..."` in <project> (or
/bmad-resume-wave with --resume), told to stop after step N, to halt at
every gate the skill names, and never to merge. The permission setup is the
eval runner's (acceptEdits; python3, git and gh allowed) plus rsync, which
step 10 uses to copy the worktree for each reviewer; --allow adds a rule.
`gh pr merge` and `gh api` are disallowed: no wave skill calls `gh api`, and a
merge is a human's. `bash` is not allowed either, since a Bash rule does not
see inside `bash -c` (V2-14); a step that needs any of the three halts the
run, and a disallowed rule wins over an --allow. The project's own deny and
ask rules, hooks and settings still apply, the gate's merge rule among them.
A call nothing allows is denied, not asked: there is no one to ask.

The session's stream-json goes to <log-dir>/<project>/<wave>-<UTC time>.jsonl
(default log dir ~/Library/Logs/keelswell). When it ends, prints where it
stopped, the cost and every denied call. Exits with the session's code.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ALLOWED = ("Bash(python3 *)", "Bash(git *)", "Bash(gh *)", "Bash(rsync *)")
DISALLOWED = ("Bash(gh pr merge *)", "Bash(gh api *)")


def prompt(wave, through, resume):
    skill = "bmad-resume-wave" if resume else "bmad-dev-wave"
    stop = (f"Carry the wave through step {through} and stop there." if through
            else "Carry the wave as far as the skill goes.")
    return (f"/{skill} {wave}\n\n"
            f"No one is at the keyboard for this run. {stop} Halt at every gate the "
            "skill names, such as a NEEDS_WORK verdict or open questions at step 4.5, "
            "and at any refused call: do not work around it. Do not merge. End with "
            "one paragraph: the step you stopped at, why, and what the next session needs.")


def summary(log):
    """The last result event of a stream-json log, denials gathered from every leg."""
    legs = []
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "result":
            legs.append(event)
    if not legs:
        return None
    last = dict(legs[-1])
    last["permission_denials"] = [d for e in legs for d in e.get("permission_denials") or []]
    return last


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project", type=Path)
    ap.add_argument("wave")
    ap.add_argument("--through-step", type=int)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--max-budget-usd")
    ap.add_argument("--allow", action="append", default=[])
    ap.add_argument("--log-dir", type=Path, default=Path("~/Library/Logs/keelswell"))
    args = ap.parse_args(argv)
    project = args.project.expanduser().resolve()
    if not project.is_dir():
        ap.error(f"{project} is not a directory")

    command = ["claude", "-p", prompt(args.wave, args.through_step, args.resume),
               "--output-format", "stream-json", "--verbose",
               "--permission-mode", "acceptEdits"]
    if args.max_budget_usd:
        command += ["--max-budget-usd", args.max_budget_usd]
    command += ["--disallowedTools", *DISALLOWED]
    command += ["--allowedTools", *ALLOWED, *args.allow]

    log = args.log_dir.expanduser() / project.name / \
        f"{args.wave}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    print(f"wave {args.wave} in {project}, log {log}", flush=True)
    with open(log, "w", encoding="utf-8") as out, open(log.with_suffix(".stderr.txt"), "w") as err:
        code = subprocess.run(command, cwd=project, stdin=subprocess.DEVNULL,
                              stdout=out, stderr=err).returncode

    result = summary(log)
    if result is None:
        print(f"no result event: the session ended early (exit {code}); see {log.with_suffix('.stderr.txt')}")
        return code
    cost = result.get("total_cost_usd")
    print(f"exit {code}, {result.get('subtype')}, "
          f"{'$%.2f' % cost if cost is not None else 'cost unknown'}, {result.get('num_turns')} turns")
    print((result.get("result") or "").strip())
    for d in result["permission_denials"]:
        shown = d.get("tool_input", {}).get("command") or json.dumps(d.get("tool_input", {}))
        print(f"denied {d.get('tool_name')}: {shown[:160]}")
    print(f"log: {log}")
    return code


if __name__ == "__main__":
    sys.exit(main())
