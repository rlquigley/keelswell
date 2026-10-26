#!/usr/bin/env python3
"""Decide whether every wave of an epic carries an adversarial review record.

This is the mechanical half of /bmad-close-epic's preflight condition four
(settled-decisions register row 51, RQ 2026-09-10). The rule it enforces is
unchanged; what changed is that the verdict is an exit code rather than a
judgement the closing agent makes about its own work.

A wave carries a review record when either of two artifacts is on the main
line, origin/main's tree when that ref exists and main's otherwise:

  * docs/wave-<id>/review-party.md -- canonical, what bmad-dev-wave 1.1.0
    writes for every wave;
  * a "Party-review amendments" section in docs/wave-<id>/api-surface.md --
    the recognized alternative some waves used.

A finding that lives only in a commit message is not a record, which is the
whole point: it cannot be cited by a later artifact and cannot be checked here.

Read from git, not the working tree (V2-12 of docs/reviews/harness-review-v2.md).
A file on disk, untracked or committed only on the closure branch, is not a
record: the closing session could write one, and the gate let it. A record on
main got there through a merge a human made. It must not be empty, and for a
wave that landed on or after 2026-09-12, when bmad-dev-wave 1.5.0 made the
front matter required, it must carry that front matter: title, wave (this
wave's label), created, model and effort. Records from before keep their old
shape, as the rule date keeps waves from before it.

A wave still checked out is not cleaned up: while any checkout is on a wave's
branch (wave_status.locate, the same matcher every wave script uses) the epic
is refused. --preflight adds the checks that need the network, which
/bmad-close-epic runs at step 1 and the wave-gate hook never does: no open
pull request on a wave's branch, and no closure branch for the epic already
(a branch named close-epic-<N> or epic-<N>-closure, other than the one this
runs on).

The rule is prospective from 2026-09-10. A wave that landed before then and
carries no record is a pre-rule gap: reported, argued in the closure's own
code-review pass, never refused. Applying the rule backwards would block
closures over waves that predate it and buys no safety.

Landing dates come from git, not from GitHub: find the commit that added
anything under docs/wave-<id>/, then the merge that brought it to this branch,
and take the merge's date. Not the commit's own -- a wave's docs are written
on its branch and can predate its merge by up to two days, and a wave whose
commit and merge straddle the rule date would otherwise pass as pre-rule when
its merge says refuse. The wave map's "Branch suffix" column
is an intention rather than a record -- real head refs carry tool prefixes and
disambiguating hashes, and some do not share a slug with the column at all --
so it cannot address a pull request, and a substring search over pull requests
matches the wrong one for waves whose cleanup branch shares the wave label.

Every wave starts with no record and nothing but an existing file flips that.
A wave this script cannot date is not assumed pre-rule; it blocks.

  check_review_records.py --project-root P --epic 6 [--preflight]

Exit codes:
  0  every wave of the epic carries a record, or lacks one lawfully (pre-rule)
  1  at least one wave landed on or after the rule date with no record
  2  structural: no wave map, the epic has no waves in it, or wave_status.py
     is missing
  3  at least one wave with no record could not be dated
  4  not cleaned up: a checkout is still on a wave's branch, or (--preflight)
     a wave's pull request is open, a closure branch exists, or gh or git
     could not say

Stdout is JSON for the caller to quote. Stderr is the refusal, written to be
acted on. Stdlib only.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# bmad-dev-wave's status script, for its worktree and branch matcher. Same
# relative layout in skills/ and in .claude/skills/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "bmad-dev-wave" / "scripts"))
try:
    import wave_status  # noqa: E402
except ImportError:
    wave_status = None

# Settled-decisions register row 51. A wave that landed before this instant
# and carries no record is a pre-rule gap, not a refusal.
RULE_DATE = datetime(2026, 9, 10, tzinfo=timezone.utc)

# bmad-dev-wave 1.5.0 made the review record's front matter required.
FRONT_MATTER_DATE = datetime(2026, 9, 12, tzinfo=timezone.utc)
FRONT_MATTER_KEYS = ("title", "wave", "created", "model", "effort")

# The main line records are read from, first that exists.
MAIN_REFS = ("origin/main", "main")

WAVE_MAP = Path("_bmad-output") / "planning-artifacts" / "waves.md"

# "6A" -> epic 6, letter A. Epic numbers are not capped at one digit.
WAVE_LABEL = re.compile(r"^(\d+)([A-Za-z]+)$")

# The alternative record location, as a Markdown heading of any level.
AMENDMENTS = re.compile(r"^#{1,6}\s*Party-review amendments\b", re.IGNORECASE | re.MULTILINE)


def parse_wave_labels(text: str):
    """Every Wave label in the map's pipe table, in table order.

    waves.md carries one flat table for the whole project, ordered by
    execution rather than by epic, so there is nothing per-epic to seek to.
    Any pipe table with a "Wave" column is read; rows whose first cell is not
    a wave label (separators, prose) are skipped.
    """
    labels = []
    wave_col = None
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            wave_col = None
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if wave_col is None:
            if "wave" in [c.lower() for c in cells]:
                wave_col = [c.lower() for c in cells].index("wave")
            continue
        if wave_col >= len(cells):
            continue
        label = cells[wave_col]
        if WAVE_LABEL.match(label):
            labels.append(label)
    return labels


def epic_of(label: str) -> int:
    return int(WAVE_LABEL.match(label).group(1))


def main_line(project_root: Path):
    """The ref records are read from: origin/main when it exists, else main."""
    for ref in MAIN_REFS:
        if _git(project_root, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}"):
            return ref
    return None


def front_matter(text: str):
    """The leading `---` block's keys, or None when there is none."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    keys = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return keys
        key, sep, value = line.partition(":")
        if sep:
            keys[key.strip().lower()] = value.strip().strip("'\"")
    return None


def record_problem(text: str, label: str, landed):
    """Why a record on the main line does not count, or None when it does."""
    if not text.strip():
        return "is empty"
    if landed is not None and landed < FRONT_MATTER_DATE:
        return None
    keys = front_matter(text)
    if keys is None:
        return ("has no front matter, which is required from "
                f"{FRONT_MATTER_DATE.date().isoformat()}: {', '.join(FRONT_MATTER_KEYS)}")
    missing = [k for k in FRONT_MATTER_KEYS if not keys.get(k)]
    if missing:
        return f"has front matter without {', '.join(missing)}"
    if keys["wave"].lower() != label.lower():
        return f"has front matter naming wave: {keys['wave']}, not {label}"
    return None


def find_record(project_root: Path, label: str, ref, landed):
    """(the wave's review record, or None; why a file there does not count, or
    None). Read from `ref`'s tree, never the working tree. Directories are
    lower-cased."""
    wave_dir = f"docs/wave-{label.lower()}"
    canonical = f"{wave_dir}/review-party.md"
    if ref is not None:
        text = _git(project_root, "cat-file", "-p", f"{ref}:{canonical}")
        if text is not None:
            problem = record_problem(text, label, landed)
            if problem is None:
                return canonical, None
            return None, f"{canonical} on {ref} {problem}"
        api = _git(project_root, "cat-file", "-p", f"{ref}:{wave_dir}/api-surface.md")
        if api is not None and AMENDMENTS.search(api):
            return f"{wave_dir}/api-surface.md (Party-review amendments)", None
    if (project_root / canonical).is_file():
        return None, (f"{canonical} exists here but is not on {ref}" if ref else
                      f"{canonical} exists here, and there is no origin/main or main to read")
    return None, None


def _git(project_root: Path, *args):
    """Run git; stdout on success, None on any failure."""
    try:
        out = subprocess.run(
            ["git", "-C", str(project_root), *args],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def _committed_at(project_root: Path, rev: str):
    out = _git(project_root, "log", "-1", "--format=%cI", rev)
    if not out or not out.strip():
        return None
    try:
        return datetime.fromisoformat(out.strip())
    except ValueError:
        return None


def landed_at(project_root: Path, label: str):
    """When docs/wave-<id>/ reached this branch. None if it never has.

    The date that decides pre-rule is when the wave's docs became visible
    here, which is its merge -- not when the commit was written on the wave's
    own branch. The two differ by the length of the wave's review: measured
    across one instance's eighteen waves the lag ranges from six minutes to
    forty-six hours, and one wave's commit and merge fall on opposite sides of
    the rule date. Dating by the branch commit would let that wave pass as
    pre-rule when its merge says otherwise, which is the one direction this
    gate must not fail in.

    So: find the commit that added the directory, then the oldest merge on
    this branch that brought it in, and take that merge's date. A repository
    that squashes or rebases has no such merge commit, and there the commit's
    own date already is the date it landed.
    """
    path = f"docs/wave-{label.lower()}/"
    out = _git(project_root, "log", "--diff-filter=A", "--format=%H", "--reverse", "--", path)
    if not out:
        return None
    added = next((line.strip() for line in out.splitlines() if line.strip()), None)
    if added is None:
        return None

    merges = _git(project_root, "rev-list", "--ancestry-path", "--merges", f"{added}..HEAD")
    if merges and merges.strip():
        first_merge = merges.split()[-1]  # rev-list is newest-first; oldest brought it in
        merged_at = _committed_at(project_root, first_merge)
        if merged_at is not None:
            return merged_at
    return _committed_at(project_root, added)


def held(project_root: Path, labels):
    """(label, checkouts) for every wave a checkout is still on the branch of."""
    out = []
    for label in labels:
        where = wave_status.locate(project_root, label)
        if where.candidates:
            out.append((label, [str(c) for c in where.candidates]))
    return out


def closure_branch(epic: int):
    return re.compile(rf"(?:^|/)(?:close-epic-{epic}|epic-{epic}-closure)(?:-|$)", re.I)


def _here(path):
    out = _git(path, "symbolic-ref", "--short", "-q", "HEAD")
    return out.strip() if out else None


def preflight(project_root: Path, epic: int, labels):
    """Problems the network has to answer: an open pull request on a wave's
    branch, or a closure branch for the epic that already exists. A check
    that cannot run is a problem too."""
    problems = []
    suffixes = {label: wave_status.branch_suffix(project_root, label) for label in labels}
    try:
        p = subprocess.run(["gh", "pr", "list", "--state", "open", "--limit", "500",
                            "--json", "number,headRefName"], cwd=str(project_root),
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        prs = json.loads(p.stdout or "[]") if p.returncode == 0 else None
        why = (p.stderr.strip().splitlines() or [f"exit {p.returncode}"])[0]
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        prs, why = None, str(e)
    if prs is None:
        problems.append(f"gh could not list open pull requests: {why}")
    for pr in prs or []:
        head = pr.get("headRefName") or ""
        for label in labels:
            if wave_status.wave_branch(head, label, suffixes[label]):
                problems.append(f"pull request #{pr.get('number')} is open for wave {label}'s "
                                f"branch {head}")

    names = (_git(project_root, "branch", "--format=%(refname:short)") or "").split()
    if _git(project_root, "remote", "get-url", "origin"):
        remote = _git(project_root, "ls-remote", "--heads", "origin")
        if remote is None:
            problems.append("git could not list origin's branches")
        names += [line.split("refs/heads/", 1)[1] for line in (remote or "").splitlines()
                  if "refs/heads/" in line]
    mine = {_here(project_root), _here(Path.cwd())}
    pattern = closure_branch(epic)
    for name in sorted(set(names)):
        if pattern.search(name) and name not in mine:
            problems.append(f"closure branch already exists: {name}")
    return problems


def check(project_root: Path, epic: int, network=False):
    if wave_status is None:
        return 2, {"epic": epic, "error": "no_wave_status"}, [
            "REFUSE: bmad-dev-wave's scripts/wave_status.py is missing beside this skill,",
            "  so whether a wave is still checked out cannot be read. Restore it",
            "  (./install.sh --validate-only names it).",
        ]
    wave_map = project_root / WAVE_MAP
    if not wave_map.is_file():
        return 2, {"epic": epic, "error": "no_wave_map", "expected": str(WAVE_MAP)}, [
            f"REFUSE: no wave map at {WAVE_MAP}.",
            "  Run /bmad-create-wave before closing anything.",
        ]

    labels = [w for w in parse_wave_labels(wave_map.read_text(encoding="utf-8", errors="ignore"))
              if epic_of(w) == epic]
    if not labels:
        return 2, {"epic": epic, "error": "no_waves_in_epic"}, [
            f"REFUSE: epic {epic} has no waves in {WAVE_MAP}.",
            "  Either the epic id is a typo or the decomposition is wrong.",
        ]

    ref = main_line(project_root)
    waves = []
    for label in labels:
        landed = landed_at(project_root, label)
        record, problem = find_record(project_root, label, ref, landed)
        if record is not None:
            waves.append({"wave": label, "status": "OK", "record": record})
            continue
        entry = {"wave": label, "record": None,
                 "landed": landed.isoformat() if landed else None}
        if problem:
            entry["problem"] = problem
        if landed is None:
            waves.append(dict(entry, status="UNDATABLE"))
        elif landed < RULE_DATE:
            waves.append(dict(entry, status="PRE-RULE-GAP"))
        else:
            waves.append(dict(entry, status="MISSING"))
    checked_out = held(project_root, labels)
    blockers = preflight(project_root, epic, labels) if network else []

    missing = [w for w in waves if w["status"] == "MISSING"]
    undatable = [w for w in waves if w["status"] == "UNDATABLE"]
    gaps = [w for w in waves if w["status"] == "PRE-RULE-GAP"]

    result = {
        "epic": epic,
        "rule_date": RULE_DATE.date().isoformat(),
        "waves": waves,
        "missing": [w["wave"] for w in missing],
        "undatable": [w["wave"] for w in undatable],
        "pre_rule_gaps": [w["wave"] for w in gaps],
        "main_line": ref,
        "checked_out": {label: paths for label, paths in checked_out},
        "preflight": blockers if network else None,
    }

    lines = []
    if missing:
        lines.append(f"REFUSE: epic {epic} has {len(missing)} wave(s) that landed on or after "
                     f"{RULE_DATE.date().isoformat()} with no review record.")
        for w in missing:
            lines += [
                f"  wave {w['wave']} landed {w['landed']} and has neither, on {ref or 'main'}:",
                f"    docs/wave-{w['wave'].lower()}/review-party.md",
                f"    a \"Party-review amendments\" section in "
                f"docs/wave-{w['wave'].lower()}/api-surface.md",
            ]
            if w.get("problem"):
                lines.append(f"    ({w['problem']})")
        lines += [
            "  There is no flag for this. The remedy is to write the record, which",
            "  means the adversarial review has to have happened, and land it on main",
            "  through a pull request. A file only in the working tree or on the",
            "  closure branch does not count, and neither does a finding that lives",
            "  only in a commit message.",
        ]
    if undatable:
        lines.append(f"REFUSE: epic {epic} has {len(undatable)} wave(s) with no review record "
                     "that this gate cannot date.")
        for w in undatable:
            lines += [
                f"  wave {w['wave']}: docs/wave-{w['wave'].lower()}/ has never been added here,",
                "    so the wave has not landed on this branch and the pre-rule",
                "    exemption cannot be proven. An undatable wave is not assumed old.",
            ]
        lines.append("  If the wave has not run, it is not the review record that blocks "
                     "closure; run the wave.")
    if checked_out or blockers:
        lines.append(f"REFUSE: epic {epic} is not cleaned up.")
        for label, paths in checked_out:
            lines += [f"  wave {label}: a checkout is still on its branch:"] + [
                f"    {p}" for p in paths]
        lines += [f"  {b}" for b in blockers]
        lines.append("  Run /bmad-merge-wave for each wave named, or remove a stale worktree or "
                     "branch by hand, then retry.")
    if gaps:
        lines.append(f"Pre-rule gaps (not a refusal): {', '.join(w['wave'] for w in gaps)}.")
        for w in gaps:
            lines.append(f"  wave {w['wave']} landed {w['landed']}, before the rule. Record it in "
                         "the closure's code-review pass and argue its severity there.")

    if missing:
        return 1, result, lines
    if undatable:
        return 3, result, lines
    if checked_out or blockers:
        return 4, result, lines
    if not lines:
        lines.append(f"Epic {epic}: all {len(waves)} wave(s) carry a review record.")
    return 0, result, lines


def main():
    ap = argparse.ArgumentParser(description="Check every wave of an epic for a review record.")
    ap.add_argument("--project-root", default=".", help="project root (default: cwd)")
    ap.add_argument("--epic", required=True, type=int, help="epic number")
    ap.add_argument("--preflight", action="store_true",
                    help="also ask gh and origin: no open pull request, no closure branch")
    args = ap.parse_args()

    code, result, lines = check(Path(args.project_root).resolve(), args.epic, args.preflight)
    result["exit_code"] = code
    _write(sys.stdout, json.dumps(result, indent=2) + "\n")
    _write(sys.stderr, "\n".join(lines) + "\n")
    sys.exit(code)


def _write(stream, text):
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")
    stream.write(text)


if __name__ == "__main__":
    main()
