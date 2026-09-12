#!/usr/bin/env python3
"""Read, write and route on a wave's lifecycle status.

Phase 2 of docs/harness-conversion-plan.md. This file is the single place the
wave-status vocabulary is defined; bmad-create-wave, bmad-dev-wave,
bmad-merge-wave, bmad-resume-wave and bmad-status-wave all read it from here
rather than each carrying their own copy of the names.

The shape is BMAD's own bmad-build-auto (spec-template.md line 5, and the
step-01 routing table): draft enters at plan, ready-for-dev and in-progress at
implement, in-review at review, done runs a fresh follow-up review pass, and
blocked halts. The names are unchanged; what each one means is keelswell's
twelve-step wave rather than build-auto's four steps.

  status          meaning                                     re-entry
  draft           dev-wave has not run past step 5            first incomplete of 1-5
  ready-for-dev   steps 1-5 done, implementation not sent     step 6
  in-progress     implementation dispatched                   first incomplete of 6-9
  in-review       party review, commits, PR, awaiting merge   first incomplete of 10-12
  done            PR merged and merge-wave cleanup complete   step 10, follow-up pass
  blocked         sticky halt                                 none

No stage is added. Every re-entry point above is a step bmad-dev-wave already
has, which is the plan's "do not add stages" constraint: a status names which
stage the wave is in, and the checkpoint markers beside this record name the
step within it.

BLOCKED IS STICKY. A blocked wave halts every later dispatch, including after
the cause is fixed, and no skill and no flag can clear it -- `set` refuses to
write over a blocked record just as `route` refuses to proceed past one. Only a
human editing `status:` in the record or deleting the record file clears it.
That asymmetry is the control mechanism: a retry loop is not one, because the
agent that caused the block is the agent that would clear it.

MISSING STATUS. Two cases, ruled differently, and the split is the mechanism
rather than bookkeeping (RQ, 2026-09-11):

  * No record file at all -- a wave that predates this field. Lawful. `route`
    backfills it once: it infers the stage from the checkpoint, git and
    worktree evidence bmad-resume-wave's probes already used -- for a wave
    swept before checkpoints were archived, that evidence is whether its
    `docs/wave-<id>/` has merged into main -- says so on stderr, writes the
    record, and proceeds. Inference happens exactly once per wave and its
    result is written down; every dispatch after that routes on the record.
    Same shape as Phase 1's prospective rule -- the pre-field artifact gets a
    named, reported exemption, never a silent default.
  * Record present with `status:` missing or unrecognized -- corrupt. Refuse.
    Once a wave has a record, a garbled status is a refusal and not a guess.
    Without this half, deleting the status line would be an undocumented
    override of blocked; with it, clearing a block means writing a valid
    status or deleting the whole file. Both are deliberate human acts.

The record lives at `.bmad/wave-<ID>/wave.md`, beside the checkpoint that
directory already holds. Local and untracked, like every other piece of wave
state (worktrees are per-machine, so wave state is too; RQ ruled local
2026-09-11). checkpoint.json keeps its job -- which of the twelve steps are
done -- and this record owns the stage.

  wave_status.py route --project-root P --wave 5D
  wave_status.py set   --project-root P --wave 5D --status in-progress
  wave_status.py show  --project-root P [--wave 5D]

Exit codes (route and set):
  0  proceed; route prints the stage and re-entry step
  1  blocked -- route refused to dispatch, or set refused to overwrite
  2  structural: no wave map, or the wave is not in it
  3  corrupt: the record exists and its status is missing or unrecognized

`show` is read-only: it never writes, never backfills, and exits 0 whenever it
could read the wave map, so a dashboard can render a corrupt or blocked wave
as a row instead of dying on it.

Stdout is JSON for the caller to quote. Stderr is the refusal or the notice,
written to be acted on. Stdlib only.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WAVE_MAP = Path("_bmad-output") / "planning-artifacts" / "waves.md"

# The vocabulary. Every wave skill reads these names from here.
DRAFT = "draft"
READY_FOR_DEV = "ready-for-dev"
IN_PROGRESS = "in-progress"
IN_REVIEW = "in-review"
DONE = "done"
BLOCKED = "blocked"

# status -> (stage, the dev-wave steps that stage covers, in order).
# Steps are strings because bmad-dev-wave has a step 4.5 (the open-questions
# gate) and float keys would not round-trip its marker filenames.
STAGES = {
    DRAFT:         ("plan",      ["1", "2", "3", "4", "4.5", "5"]),
    READY_FOR_DEV: ("implement", ["6"]),
    IN_PROGRESS:   ("implement", ["6", "7", "8", "9"]),
    IN_REVIEW:     ("review",    ["10", "11", "12"]),
    DONE:          ("review",    ["10"]),
    BLOCKED:       ("halt",      []),
}

STATUSES = tuple(STAGES)

# "6A" -> epic 6, letter A. Epic numbers are not capped at one digit.
WAVE_LABEL = re.compile(r"^(\d+)([A-Za-z]+)$")

# "step-4.5.done" -> 4.5; "step-3.pin.done" -> 3. Both shapes are in the real
# data (ffbapp .bmad/wave-2B/archive/), and a sub-marker belongs to its step.
MARKER_FILE = re.compile(r"^step-(\d+(?:\.\d+)?)(?:\.[A-Za-z0-9_-]+)?\.done$")

# checkpoint.json's other convention: {"steps": {"1_preflight": "done", ...}}.
# ffbapp .bmad/wave-5D/checkpoint.json uses this while wave-2B uses marker
# files. Both are real; a parser that knows only one misreads half the waves.
MARKER_KEY = re.compile(r"^(\d+(?:_\d+)?)[_-]")

RECORD_NAME = "wave.md"


# ---------------------------------------------------------------- wave map

def parse_wave_labels(text):
    """Every Wave label in the map's pipe table, in table order.

    waves.md carries one flat table for the whole project, ordered by
    execution rather than by epic (Phase 1 correction), so there is nothing
    per-epic to seek to. Any pipe table with a "Wave" column is read; rows
    whose first cell is not a wave label are skipped.
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
            lowered = [c.lower() for c in cells]
            if "wave" in lowered:
                wave_col = lowered.index("wave")
            continue
        if wave_col >= len(cells):
            continue
        if WAVE_LABEL.match(cells[wave_col]):
            labels.append(cells[wave_col])
    return labels


def wave_map_labels(project_root):
    path = project_root / WAVE_MAP
    if not path.is_file():
        return None
    return parse_wave_labels(path.read_text(encoding="utf-8", errors="ignore"))


def resolve_label(labels, wanted):
    """The map's own spelling of `wanted`, matched case-insensitively."""
    for label in labels:
        if label.lower() == wanted.lower():
            return label
    return None


# ------------------------------------------------------------ the record

def wave_dir(project_root, label):
    """`.bmad/wave-<ID>/`, resolved case-insensitively.

    The real instance spells this directory with the map's casing
    (`.bmad/wave-5D/`) while `docs/wave-5d/` is lower-cased, so neither
    spelling can be assumed. An existing directory wins; otherwise the map's
    spelling is what a new one gets.
    """
    bmad = project_root / ".bmad"
    wanted = f"wave-{label}".lower()
    if bmad.is_dir():
        for child in sorted(bmad.iterdir()):
            if child.is_dir() and child.name.lower() == wanted:
                return child
    return bmad / f"wave-{label}"


def record_path(project_root, label):
    return wave_dir(project_root, label) / RECORD_NAME


def parse_record(text):
    """Frontmatter as a dict, plus the body. `None` if there is no frontmatter.

    A deliberately small parser: `key: value` scalars between the leading
    `---` fences, quotes stripped. The record is meant to be hand-edited, so
    it stays in the subset a human types correctly without a YAML reference.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            front = {}
            for line in lines[1:i]:
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                key, sep, value = line.partition(":")
                if not sep:
                    continue
                front[key.strip()] = value.strip().strip("'\"")
            return front, "\n".join(lines[i + 1:])
    return None, text


def read_record(project_root, label):
    path = record_path(project_root, label)
    if not path.is_file():
        return None
    try:
        front, body = parse_record(path.read_text(encoding="utf-8", errors="ignore"))
    except OSError:
        return None
    if front is None:
        return {"status": None, "_body": body, "_malformed": True}
    front["_body"] = body
    return front


def history_lines(body):
    """The record's existing history entries, so a write appends rather than
    replaces. The history is why the record is Markdown and not JSON."""
    out = []
    seen_heading = False
    for line in body.splitlines():
        if line.strip().lower().startswith("## history"):
            seen_heading = True
            continue
        if seen_heading and line.strip().startswith("- "):
            out.append(line.rstrip())
    return out


def render_record(label, status, now, reason=None, blocked_at=None, history=()):
    front = [f"wave: {label}", f"status: {status}", f"updated: {now}"]
    if blocked_at:
        front.append(f"blocked_at: {blocked_at}")
    if reason:
        front.append(f"reason: {reason}")
    return (
        "---\n" + "\n".join(front) + "\n---\n"
        f"\n# Wave {label} lifecycle record\n"
        "\nWritten and read by the wave skills through\n"
        "`bmad-dev-wave/scripts/wave_status.py`. `status:` is the wave's stage;\n"
        "the step within that stage comes from the checkpoint markers beside\n"
        "this file.\n"
        "\nValid statuses: " + ", ".join(STATUSES) + ".\n"
        "\nA `blocked` record halts every later dispatch, including after the\n"
        "cause is fixed. No skill and no flag can clear it. To retry, edit\n"
        "`status:` above to another valid status, or delete this file. Deleting\n"
        "the `status:` line does not clear it -- that is a corrupt record and\n"
        "refuses just as loudly.\n"
        "\n## History\n" + ("\n".join(history) + "\n" if history else "")
    )


def write_record(project_root, label, status, reason=None, note=None,
                 blocked_at=None, existing=None):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    history = list(history_lines(existing.get("_body", ""))) if existing else []
    was = (existing or {}).get("status") or "(none)"
    entry = f"- {now}  {was} -> {status}"
    if note or reason:
        entry += f"  ({note or reason})"
    history.append(entry)
    path = record_path(project_root, label)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_record(label, status, now, reason=reason,
                      blocked_at=blocked_at, history=history),
        encoding="utf-8")
    return now


# ------------------------------------------------------------- the probes

def completed_steps(project_root, label):
    """Which dev-wave steps have a completion marker, from both conventions.

    Marker files (`step-12.done`) and checkpoint.json's `steps` object
    (`{"1_preflight": "done"}`) are both in use in the real instance, and the
    archive directory carries the markers of a swept wave.
    """
    done = set()
    d = wave_dir(project_root, label)
    for base in (d, d / "archive"):
        if not base.is_dir():
            continue
        for child in base.iterdir():
            m = MARKER_FILE.match(child.name)
            if m:
                done.add(m.group(1))
        checkpoint = base / "checkpoint.json"
        if checkpoint.is_file():
            try:
                data = json.loads(checkpoint.read_text(encoding="utf-8", errors="ignore"))
            except (OSError, ValueError):
                continue
            steps = data.get("steps") if isinstance(data, dict) else None
            if isinstance(steps, dict):
                for key, value in steps.items():
                    m = MARKER_KEY.match(str(key))
                    if m and str(value).strip().lower().startswith("done"):
                        done.add(m.group(1).replace("_", "."))
    return done


def _git(project_root, *args):
    """Run git; stdout on success, None on any failure."""
    try:
        out = subprocess.run(
            ["git", "-C", str(project_root), *args],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def _git_ok(project_root, *args):
    """Whether git exited 0. Separate from _git because the ancestry test
    answers with its exit code and writes nothing to stdout."""
    try:
        out = subprocess.run(
            ["git", "-C", str(project_root), *args],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return out.returncode == 0


def docs_landed(project_root, label):
    """Whether `docs/wave-<id>/` has merged into this project's main line.

    The strongest evidence a wave finished, and the only evidence that exists
    for a wave cleaned up before bmad-merge-wave 1.1.0 started archiving
    checkpoints: sixteen of ffbapp's eighteen waves have no `.bmad/wave-<id>/`
    at all, because their worktrees were swept by hand. Their docs directories
    are all on main.

    Phase 1's gate already walks this path, and the ancestry test is the part
    that makes it safe to reuse here: `docs/wave-<id>/` also exists inside the
    wave's own worktree from step 3 onward, so mere presence would read every
    wave as finished from the moment its test design is written. Asking
    whether the commit that added it is an ancestor of main separates a merged
    wave from one still being built.
    """
    path = f"docs/wave-{label.lower()}/"
    out = _git(project_root, "log", "--diff-filter=A", "--format=%H", "--reverse",
               "--", path)
    if not out:
        return False
    added = next((line.strip() for line in out.splitlines() if line.strip()), None)
    if added is None:
        return False
    for ref in ("origin/main", "main"):
        if _git_ok(project_root, "merge-base", "--is-ancestor", added, ref):
            return True
    return False


def has_branch_or_worktree(project_root, label):
    """Whether anything on disk says this wave was ever dispatched.

    Suffix-matched, never reconstructed from a path convention -- the same
    correction bmad-merge-wave 1.1.0 made after a harness-created worktree
    went unseen by a convention-built lookup.
    """
    needle = f"wave-{label}".lower()
    for args in (("branch", "--format=%(refname:short)"),
                 ("worktree", "list", "--porcelain")):
        out = _git(project_root, *args)
        if out and needle in out.lower():
            return True
    return False


def infer_status(project_root, label):
    """The one-time backfill for a wave with no record. Returns (status, why).

    This is the evidence bmad-resume-wave's probes already used, run once and
    then written down. Ambiguity resolves toward `draft`, which re-enters at
    the earliest incomplete step: re-running an idempotent preflight and
    worktree check costs a few minutes, whereas guessing a wave forward past
    steps that never ran skips its test design and its ATDD scaffolding.
    """
    d = wave_dir(project_root, label)
    if (d / "archive").is_dir() and any((d / "archive").glob("cleanup.done")):
        return DONE, "merge-wave archive carries cleanup.done"

    if docs_landed(project_root, label):
        return DONE, f"docs/wave-{label.lower()}/ has merged into main"

    done = completed_steps(project_root, label)
    if done:
        highest = max(done, key=lambda s: float(s))
        top = float(highest)
        if top >= 10:
            return IN_REVIEW, f"highest checkpoint marker is step {highest}"
        if top >= 6:
            return IN_PROGRESS, f"highest checkpoint marker is step {highest}"
        if top >= 5:
            return READY_FOR_DEV, f"highest checkpoint marker is step {highest}"
        return DRAFT, f"highest checkpoint marker is step {highest}"

    if has_branch_or_worktree(project_root, label):
        return DRAFT, "a branch or worktree exists but no checkpoint marker does"
    return DRAFT, "no branch, worktree or checkpoint marker exists"


def reentry_step(project_root, label, status):
    """The step to re-enter at: the first in the stage with no marker.

    `done` re-enters at step 10 whatever its markers say, because a done wave
    is a completed run and the dispatch is a fresh follow-up review rather
    than a resumption -- build-auto's own handling of a `done` spec. That
    needs no branch here: DONE's stage is the single step 10, so first-with-no
    -marker and last-in-stage are the same answer. Widening that list would
    turn the follow-up pass back into a resumption, which is why it is one
    step and not the review stage's three.
    """
    stage, steps = STAGES[status]
    if not steps:
        return None
    done = completed_steps(project_root, label)
    for step in steps:
        if step not in done:
            return step
    return steps[-1]


# ------------------------------------------------------------- the verbs

def _structural(project_root, label):
    """(code, result, lines) when the wave map cannot place this wave."""
    labels = wave_map_labels(project_root)
    if labels is None:
        return 2, {"wave": label, "error": "no_wave_map", "expected": str(WAVE_MAP)}, [
            f"REFUSE: no wave map at {WAVE_MAP}.",
            "  Run /bmad-create-wave before dispatching anything.",
        ], None
    resolved = resolve_label(labels, label)
    if resolved is None:
        return 2, {"wave": label, "error": "wave_not_in_map",
                   "known": labels}, [
            f"REFUSE: wave {label} is not in {WAVE_MAP}.",
            f"  The map lists: {', '.join(labels) if labels else '(none)'}.",
            "  Either the wave id is a typo or the decomposition is wrong.",
        ], None
    return 0, None, [], resolved


def route(project_root, label):
    code, result, lines, resolved = _structural(project_root, label)
    if resolved is None:
        return code, result, lines
    label = resolved

    record = read_record(project_root, label)
    backfilled = None

    if record is None:
        status, why = infer_status(project_root, label)
        write_record(project_root, label, status, note=f"backfilled: {why}")
        backfilled = why
        record = read_record(project_root, label)
    elif record.get("status") not in STATUSES:
        found = record.get("status")
        shown = "(missing)" if found in (None, "") else repr(found)
        return 3, {"wave": label, "error": "unrecognized_status", "found": found,
                   "valid": list(STATUSES),
                   "record": str(record_path(project_root, label))}, [
            f"REFUSE: wave {label}'s record exists and its status is {shown}.",
            f"  {record_path(project_root, label)}",
            f"  Valid statuses: {', '.join(STATUSES)}.",
            "  A record that exists is authoritative, so an unreadable status is",
            "  refused rather than guessed. This is also what stops deleting the",
            "  status line from working as a quiet override of blocked: write a",
            "  valid status, or delete the whole file to start the wave over.",
        ]

    status = record["status"]

    if status == BLOCKED:
        reason = record.get("reason") or "(no reason recorded)"
        blocked_at = record.get("blocked_at") or record.get("updated") or "(unknown)"
        return 1, {"wave": label, "status": BLOCKED, "reason": reason,
                   "blocked_at": blocked_at,
                   "record": str(record_path(project_root, label))}, [
            f"REFUSE: wave {label} is blocked.",
            f"  blocked at: {blocked_at}",
            f"  reason:     {reason}",
            f"  record:     {record_path(project_root, label)}",
            "  This halts every dispatch, including this one, and including after",
            "  the cause has been fixed. Fixing the cause does not clear it and no",
            "  flag exists to skip it -- that is the point, since the run that",
            "  blocked the wave is the run that would argue it is safe to resume.",
            "  A human clears it: edit `status:` in the record to another valid",
            "  status, or delete the record file to start the wave over.",
        ]

    stage, _ = STAGES[status]
    step = reentry_step(project_root, label, status)
    result = {
        "wave": label,
        "status": status,
        "stage": stage,
        "reentry_step": step,
        "followup_pass": status == DONE,
        "completed_steps": sorted(completed_steps(project_root, label),
                                  key=lambda s: float(s)),
        "record": str(record_path(project_root, label)),
    }
    lines = []
    if backfilled:
        result["backfilled"] = backfilled
        lines += [
            f"UNMIGRATED wave {label}: no lifecycle record existed, so one was",
            f"  written now with status {status}, inferred because {backfilled}.",
            "  This wave predates the status field. The inference runs once; every",
            "  later dispatch routes on the record, which is now on disk at",
            f"  {record_path(project_root, label)}.",
            "  Check it before dispatching if the inferred stage looks wrong.",
        ]
    if status == DONE:
        lines.append(f"Wave {label} is done; dispatching a fresh follow-up review "
                     f"pass at step {step}, not resuming.")
    else:
        lines.append(f"Wave {label}: status {status} ({stage}); re-enter at step {step}.")
    return 0, result, lines


def set_status(project_root, label, status, reason=None):
    code, result, lines, resolved = _structural(project_root, label)
    if resolved is None:
        return code, result, lines
    label = resolved

    if status not in STATUSES:
        return 3, {"wave": label, "error": "unrecognized_status", "found": status,
                   "valid": list(STATUSES)}, [
            f"REFUSE: {status!r} is not a wave status.",
            f"  Valid statuses: {', '.join(STATUSES)}.",
        ]

    existing = read_record(project_root, label)
    if existing is not None and existing.get("status") == BLOCKED:
        return 1, {"wave": label, "error": "already_blocked", "requested": status,
                   "reason": existing.get("reason"),
                   "record": str(record_path(project_root, label))}, [
            f"REFUSE: wave {label} is blocked and no skill may write over that.",
            f"  reason: {existing.get('reason') or '(no reason recorded)'}",
            f"  record: {record_path(project_root, label)}",
            f"  The requested status was {status}. Blocked is cleared by a human",
            "  editing the record or deleting it, and by nothing else -- a skill",
            "  that could write its way out of blocked is a retry loop, not a gate.",
        ]

    if reason:
        reason = " ".join(str(reason).split())
    now_blocked = status == BLOCKED
    written = write_record(
        project_root, label, status, reason=reason if now_blocked else None,
        note=reason,
        blocked_at=datetime.now(timezone.utc).isoformat(timespec="seconds")
        if now_blocked else None,
        existing=existing)
    result = {"wave": label, "status": status, "updated": written,
              "record": str(record_path(project_root, label))}
    if now_blocked:
        result["reason"] = reason
        lines = [
            f"Wave {label} is now blocked: {reason or '(no reason recorded)'}.",
            f"  {record_path(project_root, label)}",
            "  Every later dispatch halts on this until a human edits or deletes",
            "  the record. Fixing the cause is not enough.",
        ]
    else:
        lines = [f"Wave {label}: status set to {status}."]
    return 0, result, lines


def show(project_root, label=None):
    """Read-only. Never writes, never backfills, never refuses a readable map."""
    labels = wave_map_labels(project_root)
    if labels is None:
        return 2, {"error": "no_wave_map", "expected": str(WAVE_MAP)}, [
            f"No wave map at {WAVE_MAP}.",
        ]
    if label is not None:
        resolved = resolve_label(labels, label)
        if resolved is None:
            return 2, {"wave": label, "error": "wave_not_in_map", "known": labels}, [
                f"Wave {label} is not in {WAVE_MAP}.",
            ]
        labels = [resolved]

    waves = []
    for one in labels:
        record = read_record(project_root, one)
        if record is None:
            waves.append({"wave": one, "status": None, "state": "unmigrated",
                          "reentry_step": None})
            continue
        status = record.get("status")
        if status not in STATUSES:
            waves.append({"wave": one, "status": status, "state": "corrupt",
                          "reentry_step": None})
            continue
        waves.append({
            "wave": one,
            "status": status,
            "state": "ok",
            "reentry_step": reentry_step(project_root, one, status),
            "reason": record.get("reason"),
            "updated": record.get("updated"),
        })
    return 0, {"waves": waves, "valid": list(STATUSES)}, [
        f"{w['wave']}: {w['status'] or w['state']}" for w in waves
    ]


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(description="Wave lifecycle status: read, write, route.")
    ap.add_argument("verb", choices=["route", "set", "show"])
    ap.add_argument("--project-root", default=".", help="project root (default: cwd)")
    ap.add_argument("--wave", help="wave label as it appears in waves.md (e.g. 5D)")
    ap.add_argument("--status", help="for set: one of " + ", ".join(STATUSES))
    ap.add_argument("--reason", help="for set --status blocked: why, on one line")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    if args.verb == "show":
        code, result, lines = show(root, args.wave)
    elif args.verb == "route":
        if not args.wave:
            ap.error("route needs --wave")
        code, result, lines = route(root, args.wave)
    else:
        if not args.wave or not args.status:
            ap.error("set needs --wave and --status")
        code, result, lines = set_status(root, args.wave, args.status, args.reason)

    result["exit_code"] = code
    _write(sys.stdout, json.dumps(result, indent=2) + "\n")
    if lines:
        _write(sys.stderr, "\n".join(lines) + "\n")
    sys.exit(code)


def _write(stream, text):
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")
    stream.write(text)


if __name__ == "__main__":
    main()
