#!/usr/bin/env python3
"""Build the reviewer-selection replay fixture, and replay the selector over it.

R5 of docs/reviews/harness-engineering-review-v1.md. The trigger table was
tuned by running select_reviewers.py against eighteen merged waves of one
instance and reading what came back. No fixture and no script from that work
was committed, so a later edit to the table had nothing to be compared with,
and two numbers in the CHANGELOG could not be reproduced. This file is the
script; fixtures/replay-golden.json is what the selector returned.

THE FIXTURE IS NOT IN THIS REPOSITORY. It is one instance's changed-file lists
and test designs, the instance is private and this fork is public (RQ's
ruling, 2026-10-02). `build` writes it from a local checkout of the instance
into a git-ignored directory, and test_replay.py skips, saying why, when that
directory is absent. So the replay is a local check, run before any change to
the table, and not something CI can run.

WHAT THE GOLDEN CAN AND CANNOT SHOW. Per wave it holds the role ids selected,
whether the fallback fired, and the file counts. It catches a row that starts
or stops firing on a wave. It cannot show why a row fired, and it is scored
on the same eighteen waves the table was tuned on: it catches regressions,
not generalization.

Usage:

    python3 replay_fixture.py build --repo ~/path/to/instance
    python3 replay_fixture.py golden            # print what the table returns
    python3 replay_fixture.py golden --write    # replace the golden file

`build` runs `git log`, `git diff` and `git show` in the instance and nothing
else. `golden --write` is for a human who has read the difference test_replay
reported and decided the table is right; nothing calls it.

Stdlib only, like the scripts beside it.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "select_reviewers.py"
GOLDEN = HERE / "fixtures" / "replay-golden.json"
FIXTURE_ENV = "KEELSWELL_REPLAY_FIXTURE"
FIXTURE_DIRNAME = ".replay-fixture"

# The eighteen merged waves the table was tuned on, each with the pull request
# that merged it. The two lists do not pair by position; the pairing is from
# each merge's branch name and the docs/wave-<id>/ directory its diff touches.
WAVES = (
    ("1A", 29), ("1B", 38), ("1C", 43), ("2A", 54), ("2B", 61), ("2C", 62),
    ("3A", 60), ("3B", 70), ("3C", 74), ("3D", 68), ("3E", 73), ("4A", 76),
    ("4B", 80), ("5A", 82), ("5B", 84), ("5C", 85), ("5D", 88), ("6A", 78),
)


class FixtureError(Exception):
    """The fixture cannot be built or read."""


def default_fixture_dir():
    """<checkout root>/.replay-fixture, or $KEELSWELL_REPLAY_FIXTURE.

    Found by walking up to the checkout root rather than at a fixed depth:
    this file ships to skills/ and to the .claude/skills/ mirror, and both
    copies should read the one fixture.
    """
    override = os.environ.get(FIXTURE_ENV)
    if override:
        return Path(override)
    for parent in HERE.parents:
        if (parent / ".git").exists():
            return parent / FIXTURE_DIRNAME
    return HERE / FIXTURE_DIRNAME


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------

def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "core.quotePath=false", *args],
                          capture_output=True, text=True)


def find_merge(repo, pr):
    proc = _git(repo, "log", "--all", "--merges", "--format=%H", "--fixed-strings",
                "--grep", f"Merge pull request #{pr} from")
    shas = proc.stdout.split()
    if proc.returncode != 0 or len(shas) != 1:
        raise FixtureError(
            f"pull request #{pr}: expected one merge commit in {repo}, found "
            f"{len(shas)}. {proc.stderr.strip()}"
        )
    return shas[0]


def build(repo, out):
    """Write <out>/<wave>/{changed-files.txt,test-design.md,meta.json}."""
    repo = Path(repo).expanduser()
    if not (repo / ".git").exists():
        raise FixtureError(f"not a git checkout: {repo}")
    for wave, pr in WAVES:
        merge = find_merge(repo, pr)
        diff = _git(repo, "diff", "--name-only", f"{merge}^1", merge)
        if diff.returncode != 0:
            raise FixtureError(f"wave {wave}: git diff failed. {diff.stderr.strip()}")
        n_files = len(diff.stdout.splitlines())
        target = Path(out) / wave
        target.mkdir(parents=True, exist_ok=True)
        (target / "changed-files.txt").write_text(diff.stdout, encoding="utf-8")
        # A wave with no test design at its merge is a real case (one of the
        # eighteen has none), so a failed `git show` removes the file, not the wave.
        spec = _git(repo, "show", f"{merge}:docs/wave-{wave.lower()}/test-design.md")
        spec_file = target / "test-design.md"
        if spec.returncode == 0:
            spec_file.write_text(spec.stdout, encoding="utf-8")
        elif spec_file.exists():
            spec_file.unlink()
        (target / "meta.json").write_text(json.dumps({
            "wave": wave, "pr": pr, "merge": merge,
            "files": n_files,
            "spec": spec.returncode == 0,
        }, indent=2) + "\n", encoding="utf-8")
        print(f"  {wave}  #{pr}  {merge[:7]}  {n_files} files"
              f"{'' if spec.returncode == 0 else '  no test design'}")
    return 0


# --------------------------------------------------------------------------
# replay
# --------------------------------------------------------------------------

def fixture_present(fixture):
    return all((Path(fixture) / wave / "changed-files.txt").is_file() for wave, _ in WAVES)


def replay(fixture, table=None):
    """Run `select_reviewers.py select` over every wave; return the golden's shape."""
    waves = {}
    for wave, _ in WAVES:
        source = Path(fixture) / wave
        argv = [sys.executable, str(SCRIPT)]
        if table is not None:
            argv += ["--table", str(table)]
        argv += ["select", "--wave", wave, "--json",
                 "--changed-files", str(source / "changed-files.txt")]
        if (source / "test-design.md").is_file():
            argv += ["--spec", str(source / "test-design.md")]
        proc = subprocess.run(argv, capture_output=True, text=True)
        if proc.returncode != 0:
            raise FixtureError(f"wave {wave}: selector exit {proc.returncode}. "
                               f"{proc.stderr.strip()}")
        out = json.loads(proc.stdout)
        waves[wave] = {
            "files": out["changed_file_count"] + out["ignored_file_count"],
            "ignored": out["ignored_file_count"],
            "specs": out["spec_file_count"],
            "fallback": out["fallback"] is not None,
            "selected": [hit["role"] for hit in out["selected"]],
        }
    return {"summary": summarize(waves), "waves": waves}


def summarize(waves):
    selections = sum(len(w["selected"]) for w in waves.values())
    return {
        "waves": len(waves),
        "selections": selections,
        "mean": round(selections / len(waves), 2),
        "fallback": [wave for wave, w in waves.items() if w["fallback"]],
    }


def compare(golden, actual):
    """Every difference, one line each, naming the wave and the role."""
    lines = []
    for wave, want in golden["waves"].items():
        got = actual["waves"].get(wave)
        if got is None:
            lines.append(f"wave {wave}: missing from the replay")
            continue
        if got["files"] != want["files"] or got["specs"] != want["specs"]:
            lines.append(
                f"wave {wave}: the fixture holds {got['files']} paths and "
                f"{got['specs']} spec file(s), the golden was written from "
                f"{want['files']} and {want['specs']}. Rebuild the fixture; this "
                "is not a table change"
            )
            continue
        for role in want["selected"]:
            if role not in got["selected"]:
                lines.append(f"wave {wave}: {role} no longer selected")
        for role in got["selected"]:
            if role not in want["selected"]:
                lines.append(f"wave {wave}: {role} newly selected")
        if got["selected"] != want["selected"] and sorted(got["selected"]) == sorted(want["selected"]):
            lines.append(f"wave {wave}: same roles, different order")
        if got["fallback"] != want["fallback"]:
            lines.append(f"wave {wave}: fallback {'now fires' if got['fallback'] else 'no longer fires'}")
        if got["ignored"] != want["ignored"]:
            lines.append(f"wave {wave}: {got['ignored']} bookkeeping paths ignored, "
                         f"golden says {want['ignored']}")
    for wave in actual["waves"]:
        if wave not in golden["waves"]:
            lines.append(f"wave {wave}: not in the golden")
    if actual["summary"] != golden["summary"]:
        lines.append(f"summary: {actual['summary']}, golden says {golden['summary']}")
    return lines


def load_golden():
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def dump(result):
    """One wave per line, so a table change reads as a diff of the cells it moved."""
    lines = ["{", f'  "summary": {json.dumps(result["summary"])},', '  "waves": {']
    items = list(result["waves"].items())
    for i, (wave, entry) in enumerate(items):
        comma = "," if i < len(items) - 1 else ""
        lines.append(f'    "{wave}": {json.dumps(entry)}{comma}')
    lines += ["  }", "}"]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fixture", default=str(default_fixture_dir()),
                        help=f"fixture directory (default: <checkout>/{FIXTURE_DIRNAME}, "
                             f"or ${FIXTURE_ENV})")
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="write the fixture from a local checkout of the instance")
    b.add_argument("--repo", required=True, help="the instance's checkout; read, never written")
    g = sub.add_parser("golden", help="print what the selector returns over the fixture")
    g.add_argument("--write", action="store_true", help="replace fixtures/replay-golden.json")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            return build(args.repo, args.fixture)
        if not fixture_present(args.fixture):
            raise FixtureError(f"no fixture at {args.fixture}; run `build --repo <instance>` first")
        text = dump(replay(args.fixture))
        if args.write:
            GOLDEN.write_text(text, encoding="utf-8")
            print(f"wrote {GOLDEN}")
        else:
            sys.stdout.write(text)
        return 0
    except FixtureError as exc:
        print(f"replay_fixture: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
