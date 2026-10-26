#!/usr/bin/env python3
"""PreToolUse hook for sessions on the fork: a pull request on this repository
says what it did about README.md's process maps.

    stdin: the PreToolUse JSON of a Bash call

Exit 0 lets the call through. Exit 2 denies it, and stderr says what to check:
a `gh pr create` or `gh pr new` for this repository whose body has no line
starting `Diagrams:`. A pull request for any other repository passes, such as
an instance's opened while a fork change is propagated. This repository is
the owner/name of $CLAUDE_PROJECT_DIR's origin; the pull request's is its
--repo, or the origin of the directory gh runs in.

The command is read with the wave gate's shell parser, so a commit message
that mentions gh pr create is text and not a call, and a `cd` before gh is
followed. Fails open: a crash lets the call through, and the fork's CLAUDE.md
still asks for the line.

Registered in the fork's .claude/settings.json and nowhere else. It lives in
tools/ because install.sh copies .claude/hooks/ into every instance.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "bmad-dev-wave" / "scripts"))
from wave_gate import Shell  # noqa: E402

LINE = re.compile(r"^\W*diagrams:[ \t]*\S", re.I | re.M)
DENIAL = """\
pr-diagram-check: this pull request is for {repo}, and its body has no
`Diagrams:` line. Compare the branch's diff with the process maps in
README.md. If the change adds, removes or reorders an activity, a decision or
a hand-off between lanes, edit the map data in tools/process_map.py and run it
on this branch first. Then put one line in the body, `Diagrams: updated --
<what changed>` or `Diagrams: no change -- <why>`, through --body or
--body-file, and run gh pr create again.
"""


def repo(text):
    """owner/name, lower-cased, from a remote URL or a --repo value."""
    parts = re.sub(r"\.git$", "", text.strip().rstrip("/")).replace(":", "/").split("/")
    return "/".join(parts[-2:]).lower() if len(parts) > 1 and all(parts[-2:]) else None


def origin(directory):
    out = subprocess.run(["git", "-C", str(directory), "remote", "get-url", "origin"],
                         capture_output=True, text=True)
    return repo(out.stdout) if out.returncode == 0 else None


def value(argv, *names):
    """The value of the first of `names` in argv: --name v, --name=v or -n v."""
    for i, a in enumerate(argv):
        for name in names:
            if a == name and i + 1 < len(argv):
                return argv[i + 1]
            if name.startswith("--") and a.startswith(name + "="):
                return a.split("=", 1)[1]
    return None


def body(sc):
    """Everything the body could come from: the words, a here-document, and a
    --body-file that is not stdin."""
    text = "\n".join(sc.words + [sc.stdin or ""])
    path = value(sc.argv, "--body-file", "-F")
    if path and path != "-":
        p = Path(sc.cwd, os.path.expanduser(path))
        if p.is_file():
            text += "\n" + p.read_text(errors="replace")
    return text


def main():
    event = json.load(sys.stdin)
    ours = origin(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    shell = Shell((event.get("tool_input") or {}).get("command") or "", event.get("cwd") or os.getcwd())
    for sc in shell.cmds:
        if sc.name != "gh" or sc.argv[1:3] not in (["pr", "create"], ["pr", "new"]):
            continue
        flag = value(sc.argv, "--repo", "-R")
        target = repo(flag) if flag else origin(sc.cwd)
        if ours and target == ours and not LINE.search(body(sc)):
            sys.stderr.write(DENIAL.format(repo=ours))
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
