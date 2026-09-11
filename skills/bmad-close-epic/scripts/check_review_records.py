#!/usr/bin/env python3
"""Decide whether every wave of an epic carries an adversarial review record.

This is the mechanical half of /bmad-close-epic's preflight condition four
(settled-decisions register row 51, RQ 2026-09-10). The rule it enforces is
unchanged; what changed is that the verdict is an exit code rather than a
judgement the closing agent makes about its own work.

A wave carries a review record when either of two reachable artifacts exists:

  * docs/wave-<id>/review-party.md -- canonical, what bmad-dev-wave 1.1.0
    writes for every wave;
  * a "Party-review amendments" section in docs/wave-<id>/api-surface.md --
    the recognized alternative some waves used.

A finding that lives only in a commit message is not a record, which is the
whole point: it cannot be cited by a later artifact and cannot be checked here.

The rule is prospective from 2026-09-10. A wave that landed before then and
carries no record is a pre-rule gap: reported, argued in the closure's own
code-review pass, never refused. Applying the rule backwards would block
closures over waves that predate it and buys no safety.

Landing dates come from git, not from GitHub: the first commit that added
anything under docs/wave-<id>/ is when that wave's docs reached this branch,
which for a merged wave is its merge. The wave map's "Branch suffix" column
is an intention rather than a record -- real head refs carry tool prefixes and
disambiguating hashes, and some do not share a slug with the column at all --
so it cannot address a pull request, and a substring search over pull requests
matches the wrong one for waves whose cleanup branch shares the wave label.

Every wave starts with no record and nothing but an existing file flips that.
A wave this script cannot date is not assumed pre-rule; it blocks.

  check_review_records.py --project-root P --epic 6

Exit codes:
  0  every wave of the epic carries a record, or lacks one lawfully (pre-rule)
  1  at least one wave landed on or after the rule date with no record
  2  structural: no wave map, or the epic has no waves in it
  3  at least one wave with no record could not be dated

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

# Settled-decisions register row 51. A wave that landed before this instant
# and carries no record is a pre-rule gap, not a refusal.
RULE_DATE = datetime(2026, 9, 10, tzinfo=timezone.utc)

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


def find_record(project_root: Path, label: str):
    """The wave's review record, or None. Directories are lower-cased."""
    wave_dir = project_root / "docs" / f"wave-{label.lower()}"
    canonical = wave_dir / "review-party.md"
    if canonical.is_file():
        return str(canonical.relative_to(project_root))
    api_surface = wave_dir / "api-surface.md"
    if api_surface.is_file():
        try:
            if AMENDMENTS.search(api_surface.read_text(encoding="utf-8", errors="ignore")):
                return str(api_surface.relative_to(project_root)) + " (Party-review amendments)"
        except OSError:
            pass
    return None


def landed_at(project_root: Path, label: str):
    """When docs/wave-<id>/ first appeared here. None if it never has."""
    path = f"docs/wave-{label.lower()}/"
    try:
        out = subprocess.run(
            ["git", "-C", str(project_root), "log", "--diff-filter=A",
             "--format=%cI", "--reverse", "--", path],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    for line in out.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            return datetime.fromisoformat(line)
        except ValueError:
            return None
    return None


def check(project_root: Path, epic: int):
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

    waves = []
    for label in labels:
        record = find_record(project_root, label)
        if record is not None:
            waves.append({"wave": label, "status": "OK", "record": record})
            continue
        landed = landed_at(project_root, label)
        if landed is None:
            waves.append({"wave": label, "status": "UNDATABLE", "record": None, "landed": None})
        elif landed < RULE_DATE:
            waves.append({"wave": label, "status": "PRE-RULE-GAP", "record": None,
                          "landed": landed.isoformat()})
        else:
            waves.append({"wave": label, "status": "MISSING", "record": None,
                          "landed": landed.isoformat()})

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
    }

    lines = []
    if missing:
        lines.append(f"REFUSE: epic {epic} has {len(missing)} wave(s) that landed on or after "
                     f"{RULE_DATE.date().isoformat()} with no review record.")
        for w in missing:
            lines += [
                f"  wave {w['wave']} landed {w['landed']} and has neither:",
                f"    docs/wave-{w['wave'].lower()}/review-party.md",
                f"    a \"Party-review amendments\" section in "
                f"docs/wave-{w['wave'].lower()}/api-surface.md",
            ]
        lines += [
            "  There is no flag for this. The remedy is to write the record, which",
            "  means the adversarial review has to have happened. A finding that",
            "  lives only in a commit message does not count.",
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
    if gaps:
        lines.append(f"Pre-rule gaps (not a refusal): {', '.join(w['wave'] for w in gaps)}.")
        for w in gaps:
            lines.append(f"  wave {w['wave']} landed {w['landed']}, before the rule. Record it in "
                         "the closure's code-review pass and argue its severity there.")

    if missing:
        return 1, result, lines
    if undatable:
        return 3, result, lines
    if not lines:
        lines.append(f"Epic {epic}: all {len(waves)} wave(s) carry a review record.")
    return 0, result, lines


def main():
    ap = argparse.ArgumentParser(description="Check every wave of an epic for a review record.")
    ap.add_argument("--project-root", default=".", help="project root (default: cwd)")
    ap.add_argument("--epic", required=True, type=int, help="epic number")
    args = ap.parse_args()

    code, result, lines = check(Path(args.project_root).resolve(), args.epic)
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
