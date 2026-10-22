#!/usr/bin/env python3
"""Report how far each Keelswell instance's harness files are from the fork's.

    python3 tools/instance_drift.py [--list] [--root DIR] [--fork DIR] [instance ...]

With no instance named, every project under --root (default ~/Projects) whose
_bmad/_config/manifest.yaml lists the keelswell module is checked; worktrees,
_archive and every checkout of the fork are skipped. --list prints those projects and
stops.

Checked: every skill under the fork's skills/, in each Keelswell skill tree an
instance has (.claude/skills, .agents/skills: a tree holding bmad-dev-wave),
and every subagent definition under the fork's .claude/agents/. Each file is
matched by its git blob hash against every version the fork has had:

  behind   every difference is a file from an older fork version, a file the
           fork has since deleted, or a file the instance lacks: a pending sync
  drift    at least one file holds content the fork never had: hand edits,
           to be read before any sync overwrites them
  missing  the skill or definition is not in the instance at all

Reads only. Exits 0 when every instance matches, 1 otherwise.
"""
import argparse
import hashlib
import re
import subprocess
import sys
from collections import namedtuple
from pathlib import Path

Row = namedtuple("Row", "status tree unit files")
TREES = (".claude/skills", ".agents/skills")
AGENTS = ".claude/agents"
KEELSWELL = re.compile(r"^\s*-\s*name:\s*keelswell\s*$", re.M)


def blob(path):
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def ignored(rel):
    return "__pycache__" in rel.parts or rel.name == ".DS_Store" or rel.suffix == ".pyc"


def files(root):
    if not root.is_dir():
        return {}
    return {p.relative_to(root).as_posix(): p for p in root.rglob("*")
            if p.is_file() and not ignored(p.relative_to(root))}


def history(fork):
    """{fork path: every blob it has held} for skills/ and .claude/agents/."""
    out = subprocess.run(["git", "-C", str(fork), "log", "--format=", "--raw", "--no-abbrev",
                          "--no-renames", "--", "skills", AGENTS],
                         capture_output=True, text=True, check=True).stdout
    seen = {}
    for line in out.splitlines():
        if not line.startswith(":"):
            continue
        meta, path = line.split("\t", 1)
        for h in meta.split()[2:4]:
            if set(h) != {"0"}:
                seen.setdefault(path, set()).add(h)
    return seen


def compare(unit_files, inst_dir, prefix, seen):
    """(status, files) for one skill or definition; status None when it matches."""
    ours = {rel: blob(p) for rel, p in unit_files.items()}
    theirs = files(inst_dir) if inst_dir.is_dir() else {}
    foreign, stale = [], []
    for rel in sorted(set(ours) | set(theirs)):
        if rel not in theirs:
            stale.append(rel)
            continue
        h = blob(theirs[rel])
        if h == ours.get(rel):
            continue
        (stale if h in seen.get(f"{prefix}{rel}", ()) else foreign).append(rel)
    if foreign:
        return "drift", foreign
    return ("behind", stale) if stale else (None, [])


def check(fork, inst):
    fork, inst = Path(fork), Path(inst)
    seen = history(fork)
    rows = []
    for tree in (t for t in TREES if (inst / t / "bmad-dev-wave").is_dir()):
        for skill in sorted(p.name for p in (fork / "skills").iterdir() if p.is_dir()):
            target = inst / tree / skill
            if not target.is_dir():
                rows.append(Row("missing", tree, skill, []))
                continue
            status, changed = compare(files(fork / "skills" / skill), target, f"skills/{skill}/", seen)
            if status:
                rows.append(Row(status, tree, skill, changed))
    for agent in sorted((fork / AGENTS).glob("*.md")):
        target = inst / AGENTS / agent.name
        if not target.is_file():
            rows.append(Row("missing", AGENTS, agent.name, []))
            continue
        h = blob(target)
        if h != blob(agent):
            status = "behind" if h in seen.get(f"{AGENTS}/{agent.name}", ()) else "drift"
            rows.append(Row(status, AGENTS, agent.name, [agent.name]))
    return rows


def common_dir(path):
    r = subprocess.run(["git", "-C", str(path), "rev-parse", "--path-format=absolute",
                        "--git-common-dir"], capture_output=True, text=True)
    return Path(r.stdout.strip()).resolve() if r.returncode == 0 else None


def discover(root, fork):
    fork, found = Path(fork).resolve(), set()
    ours = common_dir(fork)
    for pattern in ("*/*/_bmad/_config/manifest.yaml", "*/*/*/_bmad/_config/manifest.yaml"):
        for manifest in Path(root).expanduser().glob(pattern):
            parts = manifest.relative_to(Path(root).expanduser()).parts
            if "_archive" in parts or "worktrees" in parts:
                continue
            project = manifest.parents[2].resolve()
            if project == fork or (ours and common_dir(project) == ours):
                continue  # the fork itself, or another checkout of it
            if KEELSWELL.search(manifest.read_text(errors="replace")):
                found.add(project)
    return sorted(found)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("instances", nargs="*")
    ap.add_argument("--fork", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--root", default="~/Projects")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)
    targets = [Path(i).expanduser().resolve() for i in args.instances] or discover(args.root, args.fork)
    if args.list:
        print("\n".join(map(str, targets)))
        return 0
    if not targets:
        print(f"no Keelswell instance under {args.root}")
        return 0
    bad = 0
    for inst in targets:
        rows = check(args.fork, inst)
        bad += bool(rows)
        print(inst)
        for r in rows:
            shown = ", ".join(r.files[:6]) + (f" (+{len(r.files) - 6} more)" if len(r.files) > 6 else "")
            print(f"  {r.status:8} {r.tree}/{r.unit}" + (f": {shown}" if shown and r.tree != AGENTS else ""))
        print(f"  {'matches the fork' if not rows else f'{len(rows)} to look at'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
