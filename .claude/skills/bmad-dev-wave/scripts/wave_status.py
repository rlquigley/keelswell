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
    status or deleting the whole file. Both are deliberate human acts. A
    record that cannot be read, or that names a key twice, is corrupt too:
    reading it as absent would let `set` write over a blocked record and
    `route` backfill one (V2-10 of the harness review v2).

TRANSITIONS. `set` writes only the moves in TRANSITIONS below, so a wave
cannot jump from in-progress to done past the evaluator and the review stage
(V2-01). Blocked is reachable from anything and leaves to nothing a skill
writes. `route`'s one-time backfill is not a set and is not held to the table.

The record lives at `.bmad/wave-<ID>/wave.md`, beside the checkpoint that
directory already holds. Local and untracked, like every other piece of wave
state (worktrees are per-machine, so wave state is too; RQ ruled local
2026-09-11). checkpoint.json keeps its job -- which of the twelve steps are
done -- and this record owns the stage.

  wave_status.py route --project-root P --wave 5D
  wave_status.py set   --project-root P --wave 5D --status in-progress
  wave_status.py show  --project-root P [--wave 5D]
  wave_status.py adopt --project-root P --wave 5D --from <wave worktree>
  wave_status.py mark  --project-root P --wave 5D --step 4.5
  wave_status.py pend  --project-root P --wave 5D --questions-file F
  wave_status.py pend  --project-root P --wave 5D --clear

Exit codes (route, set, adopt, mark and pend):
  0  proceed; route prints the stage and re-entry step; adopt copied, or
     found nothing to copy; mark wrote the step's marker, or found it there;
     pend wrote the pending marker, or removed it, or found none to remove
  1  blocked -- route refused to dispatch, or set refused to overwrite;
     adopt found a file that differs between the two copies, or runs inside
     the worktree it copies from
  2  structural: no wave map, or the wave is not in it; mark's step is not
     one of bmad-dev-wave's; pend's questions file is missing or empty
  3  corrupt: the record exists and cannot be read, names a key twice, or
     its status is missing or unrecognized; or the wave's state cannot be
     placed (two copies disagree, two worktrees match); nothing is written
  4  set only: TRANSITIONS does not allow this move; nothing is written

WHERE IT LIVES. `locate` answers it once for every script (V2-07 and V2-08
of the harness review v2). The project root is the main checkout, which git's
common directory names from any worktree. The wave's worktree is the one
checkout whose branch is the waves.md "Branch suffix", whole, after any
`<prefix>/` and before any hash a harness adds (claude/wave-5e-qb-archetypes,
claude/wave-4a-event-registry-825278). The wave's directory is the
worktree's `.bmad/wave-<ID>/` when it has one, else the main checkout's, so a
session rooted in either checkout reads and writes the same record. A wave
with neither starts its directory in the checkout the call came from, where
that session writes its markers. `route` and `set` refuse, exit 3,
when two worktrees match, or when both checkouts hold a copy and the main
checkout's has a file the worktree's lacks or holds with other bytes: which
copy is right is a human's call.

`adopt` is bmad-merge-wave's, run before it removes a worktree: a session
rooted in the wave's worktree writes this directory there (2026-10-17). It
refuses when the session runs inside that worktree (V2-15): removing it
removes the wave gate's hook for the rest of the session.

`mark` writes `step-<N>.done` where `route` printed the record, refusing
as `route` does when that place cannot be decided. A desktop session
isolated to the wave's worktree may not use the Write tool on the main
checkout's `.bmad/`, and its refusal says to write in the worktree instead;
a marker written there starts a second copy, and `route` and `set` then
exit 3 until a human merges the two (2026-10-25).

`pend` is the same for step 4.5's `step-4.5.pending`: it copies the
questions file's bytes there, and `--clear` removes it once the answers are
recorded. wave_gate.py's SessionEnd rule blocks a wave whose directory, in
any checkout, still holds it.

`show` is read-only: it never writes, never backfills, and exits 0 whenever it
could read the wave map, so a dashboard can render a corrupt or blocked wave
as a row instead of dying on it.

Stdout is JSON for the caller to quote. Stderr is the refusal or the notice,
written to be acted on. Stdlib only.
"""

import argparse
import collections
import contextlib
import fcntl
import functools
import json
import os
import re
import shutil
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

# current status -> the statuses `set` may write over it, and the skill that
# writes each one. `None` is no record. A same-status set changes nothing but
# the history (step 5 or 6 re-run, the third-pass "upstream fix" line, a
# merge-wave re-run). Blocked has no row: only a human edits it away.
TRANSITIONS = {
    None:          {DRAFT,           # create-wave
                    BLOCKED},        # SessionEnd hook, any halt
    DRAFT:         {DRAFT, READY_FOR_DEV, BLOCKED},    # dev-wave step 5
    READY_FOR_DEV: {READY_FOR_DEV, IN_PROGRESS, BLOCKED},  # dev-wave step 6
    IN_PROGRESS:   {IN_PROGRESS, IN_REVIEW, BLOCKED},  # dev-wave end of step 9
    IN_REVIEW:     {IN_REVIEW,
                    IN_PROGRESS,     # dev-wave step 10, a fix re-checked by 7 and 8
                    DONE,            # merge-wave step 5
                    BLOCKED},
    DONE:          {DONE, BLOCKED},
}

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
# Step 4.5's open questions; wave_gate.py's SessionEnd rule blocks the wave
# of any directory still holding it.
PENDING = "step-4.5.pending"


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
    A key given twice raises ValueError: which of two status lines is meant
    is not something to guess.
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
                if key.strip() in front:
                    raise ValueError(f"it names {key.strip()!r} twice")
                front[key.strip()] = value.strip().strip("'\"")
            return front, "\n".join(lines[i + 1:])
    return None, text


def read_record(project_root, label):
    """The record, or None when there is no file. A file that cannot be read
    or parsed comes back with `_corrupt` set, never as None: absent is what
    lets route backfill and set write, and a corrupt record gets neither."""
    path = record_path(project_root, label)
    if not path.is_file():
        return None
    try:
        front, body = parse_record(path.read_text(encoding="utf-8", errors="ignore"))
    except OSError as e:
        return {"status": None, "_body": "", "_corrupt": f"it cannot be read ({e.strerror})"}
    except ValueError as e:
        return {"status": None, "_body": "", "_corrupt": str(e)}
    if front is None:
        return {"status": None, "_body": body, "_malformed": True}
    front["_body"] = body
    return front


def corrupt_refusal(project_root, label, record):
    """(code 3, result, lines) when an existing record cannot be trusted, else None."""
    path = record_path(project_root, label)
    if record.get("_corrupt"):
        return 3, {"wave": label, "error": "corrupt_record", "why": record["_corrupt"],
                   "record": str(path)}, [
            f"REFUSE: wave {label}'s record exists and {record['_corrupt']}.",
            f"  {path}",
            "  Nothing was written. A record that exists is authoritative, so one",
            "  that cannot be read is refused rather than treated as absent: absent",
            "  would let a set write over a blocked wave. A human repairs the file",
            "  (its permissions, or the duplicated line), or deletes it to start the",
            "  wave over.",
        ]
    if record.get("status") not in STATUSES:
        found = record.get("status")
        shown = "(missing)" if found in (None, "") else repr(found)
        return 3, {"wave": label, "error": "unrecognized_status", "found": found,
                   "valid": list(STATUSES), "record": str(path)}, [
            f"REFUSE: wave {label}'s record exists and its status is {shown}.",
            f"  {path}",
            f"  Valid statuses: {', '.join(STATUSES)}.",
            "  A record that exists is authoritative, so an unreadable status is",
            "  refused rather than guessed. This is also what stops deleting the",
            "  status line from working as a quiet override of blocked: write a",
            "  valid status, or delete the whole file to start the wave over.",
        ]
    return None


@contextlib.contextmanager
def locked(project_root, label):
    """Hold the wave's directory under an exclusive flock for a read, a
    decision and a write, so two sets cannot both read the same history and
    each drop the other's line (V2-34). The directory is locked rather than a
    lock file, which adopt would copy along with the checkpoint."""
    d = wave_dir(project_root, label)
    d.mkdir(parents=True, exist_ok=True)
    fd = os.open(d, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


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
    """Write the record whole through a temp file and os.replace, so a reader
    never sees half of one. Call it inside `locked`, with `existing` read
    there too."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    history = list(history_lines(existing.get("_body", ""))) if existing else []
    was = (existing or {}).get("status") or "(none)"
    entry = f"- {now}  {was} -> {status}"
    if note or reason:
        entry += f"  ({note or reason})"
    history.append(entry)
    path = record_path(project_root, label)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(RECORD_NAME + ".tmp")
    tmp.write_text(
        render_record(label, status, now, reason=reason,
                      blocked_at=blocked_at, history=history),
        encoding="utf-8")
    os.replace(tmp, path)
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


# --------------------------------------------------- where the state lives

Where = collections.namedtuple("Where", "root worktree base candidates split")


@functools.lru_cache(maxsize=None)
def state_root(start):
    """The project's main checkout, from any checkout or directory in it.

    git's common directory names it from any worktree. Outside git, the
    nearest directory up from `start` that holds `.bmad/`, else `start`.
    """
    start = Path(os.path.realpath(start))
    out = _git(start, "rev-parse", "--path-format=absolute", "--git-common-dir")
    common = Path(out.strip()) if out and out.strip() else None
    if common is not None and common.name == ".git":
        return Path(os.path.realpath(common.parent))
    for d in (start, *start.parents):
        if (d / ".bmad").is_dir():
            return d
    return start


def _head_branch(head):
    try:
        text = head.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text[len("ref: refs/heads/"):] if text.startswith("ref: refs/heads/") else None


@functools.lru_cache(maxsize=None)
def checkouts(root):
    """(path, branch or None) of every checkout on disk, main first.

    Read from git's own files under `.git/worktrees/` when the main checkout
    has a `.git` directory: the wave gate asks on every tool call, and a
    `git worktree list` costs it about 10 ms. `git worktree list` otherwise.
    """
    git_dir = Path(root) / ".git"
    if git_dir.is_dir():
        found = [(Path(root), _head_branch(git_dir / "HEAD"))]
        admin = git_dir / "worktrees"
        for d in (sorted(admin.iterdir()) if admin.is_dir() else []):
            try:
                link = Path((d / "gitdir").read_text(encoding="utf-8").strip())
            except OSError:
                continue
            path = Path(os.path.realpath(d / link)).parent  # relative paths are the admin dir's
            found.append((path, _head_branch(d / "HEAD")))
        return [f for f in found if f[0].is_dir()]
    out = _git(root, "worktree", "list", "--porcelain")
    found = []
    for line in (out or "").splitlines():
        if line.startswith("worktree "):
            found.append([Path(os.path.realpath(line[len("worktree "):])), None])
        elif line.startswith("branch ") and found:
            found[-1][1] = line[len("branch "):].removeprefix("refs/heads/")
    return [tuple(f) for f in found if f[0].is_dir()] or [(Path(root), None)]


def branch_suffix(project_root, label):
    """The wave's "Branch suffix" cell in waves.md, or None."""
    path = project_root / WAVE_MAP
    if not path.is_file():
        return None
    wave_col = suffix_col = None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            wave_col = suffix_col = None
            continue
        cells = [c.strip().strip("`") for c in line.strip("|").split("|")]
        if wave_col is None:
            lowered = [c.lower() for c in cells]
            if "wave" in lowered and "branch suffix" in lowered:
                wave_col, suffix_col = lowered.index("wave"), lowered.index("branch suffix")
            continue
        if max(wave_col, suffix_col) < len(cells) and cells[wave_col].lower() == label.lower():
            return cells[suffix_col] or None
    return None


def wave_branch(branch, label, suffix):
    """Whether `branch` is this wave's. With a suffix, the suffix whole, after
    any `<prefix>/` and before any hash of six or more hex digits a harness
    adds, as bmad-merge-wave matches it. With none, the wave label as a path
    segment prefix, the gate's old test, which a stale lookalike also passes."""
    if not branch:
        return False
    if suffix:
        pattern = rf"(?:^|/){re.escape(suffix.lower())}(?:-[0-9a-f]{{6,}})?$"
    else:
        pattern = rf"(?:^|/)wave-{re.escape(label.lower())}(?:-|$)"
    return re.search(pattern, branch.lower()) is not None


def _not_held(copy, other):
    """Files under `copy` that `other` lacks or holds with other bytes."""
    out = []
    for f in sorted(p for p in copy.rglob("*") if p.is_file() and p.suffix != ".tmp"):
        twin = other / f.relative_to(copy)
        if not twin.is_file() or twin.read_bytes() != f.read_bytes():
            out.append(str(f.relative_to(copy)))
    return out


def locate(start, label):
    """Where wave `label`'s state lives, from any checkout of the project.

    root: the main checkout. candidates: every checkout on the wave's branch.
    worktree: the one candidate, or None for none or several. base: the
    checkout whose `.bmad/wave-<ID>/` is the wave's: the worktree's copy, else
    the main checkout's, else, for a wave with neither, the checkout the call
    came from, where that session's markers go. split: the files that make
    the main checkout's copy disagree with the worktree's, when both exist.
    `label` is the map's spelling.
    """
    root = state_root(start)
    suffix = branch_suffix(root, label)
    candidates = [path for path, branch in checkouts(root) if wave_branch(branch, label, suffix)]
    worktree = candidates[0] if len(candidates) == 1 else None
    base, split = root, []
    if worktree is not None and worktree != root:
        own, main_copy = wave_dir(worktree, label), wave_dir(root, label)
        if own.is_dir() or (not main_copy.is_dir() and _within(start, worktree)):
            base = worktree
        if own.is_dir() and main_copy.is_dir():
            split = _not_held(main_copy, own)
    return Where(root, worktree, base, candidates, split)


def where_refusal(where, label):
    """(code 3, result, lines) when the wave's state cannot be placed, else None."""
    if len(where.candidates) > 1:
        return 3, {"wave": label, "error": "ambiguous_worktree",
                   "worktrees": [str(c) for c in where.candidates]}, [
            f"REFUSE: {len(where.candidates)} checkouts are on wave {label}'s branch:",
        ] + [f"  {c}" for c in where.candidates] + [
            "  Nothing was read or written. Which one holds the wave is not guessed:",
            "  remove the stale worktree, or correct the wave's Branch suffix in",
            f"  {WAVE_MAP}.",
        ]
    if where.split:
        main_copy, own = wave_dir(where.root, label), wave_dir(where.worktree, label)
        return 3, {"wave": label, "error": "split_state", "main": str(main_copy),
                   "worktree": str(own), "files": where.split}, [
            f"REFUSE: wave {label}'s state is in two places that disagree:",
            f"  {main_copy}",
            f"  {own}",
            "  The main checkout's copy has files the worktree's lacks or holds",
            "  with other bytes:",
        ] + [f"    {f}" for f in where.split] + [
            "  Nothing was read or written. The worktree's copy is the wave's",
            "  while the worktree exists. Decide which copy is right, move what",
            "  the main checkout's holds that the worktree's should keep, and",
            "  remove the main checkout's copy by hand.",
        ]
    return None


def in_flight(project_root, label, where):
    """Why the wave is still being built, or None: its worktree exists, or a
    branch of it carries commits main does not. A merged branch left behind
    (ffbapp keeps several) is not a wave in flight."""
    if where.candidates:
        return f"its worktree {where.candidates[0]} exists"
    suffix = branch_suffix(where.root, label)
    for branch in (_git(project_root, "branch", "--format=%(refname:short)") or "").split():
        if wave_branch(branch, label, suffix) and not any(
                _git_ok(project_root, "merge-base", "--is-ancestor", branch, ref)
                for ref in ("main", "origin/main")):
            return f"branch {branch} has commits main does not"
    return None


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


def infer_status(project_root, label, where):
    """The one-time backfill for a wave with no record. Returns (status, why).

    This is the evidence bmad-resume-wave's probes already used, run once and
    then written down. Ambiguity resolves toward `draft`, which re-enters at
    the earliest incomplete step: re-running an idempotent preflight and
    worktree check costs a few minutes, whereas guessing a wave forward past
    steps that never ran skips its test design and its ATDD scaffolding.
    Merged docs are not done while the wave is still in flight (V2-31):
    ffbapp 5E merged with its worktree, and its in-review record, still there.
    """
    d = wave_dir(project_root, label)
    if (d / "archive").is_dir() and any((d / "archive").glob("cleanup.done")):
        return DONE, "merge-wave archive carries cleanup.done"

    landed = docs_landed(project_root, label)
    live = in_flight(project_root, label, where) if landed else None
    if landed and live is None:
        return DONE, f"docs/wave-{label.lower()}/ has merged into main"
    status, why = _infer_from_markers(project_root, label)
    if live:
        why += f"; docs/wave-{label.lower()}/ has merged, but {live}, so it is not done"
    return status, why


def _infer_from_markers(project_root, label):
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
    root = state_root(project_root)
    code, result, lines, resolved = _structural(root, label)
    if resolved is None:
        return code, result, lines
    label = resolved
    where = locate(project_root, label)
    refusal = where_refusal(where, label)
    if refusal:
        return refusal
    project_root = where.base

    backfilled = None
    with locked(project_root, label):
        record = read_record(project_root, label)
        if record is None:
            status, why = infer_status(project_root, label, where)
            write_record(project_root, label, status, note=f"backfilled: {why}")
            backfilled = why
            record = read_record(project_root, label)
    refusal = corrupt_refusal(project_root, label, record)
    if refusal:
        return refusal

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


def set_status(project_root, label, status, reason=None, base=None):
    """`base` names the checkout whose `.bmad/` to write and skips `locate`:
    the SessionEnd hook blocks the record beside the marker it found."""
    root = state_root(project_root)
    code, result, lines, resolved = _structural(root, label)
    if resolved is None:
        return code, result, lines
    label = resolved

    if status not in STATUSES:
        return 3, {"wave": label, "error": "unrecognized_status", "found": status,
                   "valid": list(STATUSES)}, [
            f"REFUSE: {status!r} is not a wave status.",
            f"  Valid statuses: {', '.join(STATUSES)}.",
        ]

    if base is None:
        where = locate(project_root, label)
        refusal = where_refusal(where, label)
        if refusal:
            return refusal
        base = where.base
    with locked(base, label):
        return _set_locked(base, label, status, reason)


def _set_locked(project_root, label, status, reason):
    existing = read_record(project_root, label)
    if existing is not None:
        refusal = corrupt_refusal(project_root, label, existing)
        if refusal:
            return refusal
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

    was = existing.get("status") if existing is not None else None
    if status not in TRANSITIONS[was]:
        allowed = sorted(TRANSITIONS[was], key=STATUSES.index)
        return 4, {"wave": label, "error": "illegal_transition", "from": was,
                   "requested": status, "allowed": allowed,
                   "record": str(record_path(project_root, label))}, [
            f"REFUSE: wave {label} cannot move from {was or '(no record)'} to {status}.",
            f"  From {was or '(no record)'} a set may write: {', '.join(allowed)}.",
            "  Nothing was written. Each status is entered by the step that earns it:",
            "  in-review at the end of dev-wave step 9 on a PASS, done by merge-wave",
            "  after an in-review wave's PR merged. A wave with no record gets one",
            "  from route (step 1) or create-wave, not from a later step's set.",
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


def mark(project_root, label, step):
    """Write dev-wave step `step`'s completion marker beside the record.

    Empty, so the same marker in two copies never differs in bytes."""
    root = state_root(project_root)
    code, result, lines, resolved = _structural(root, label)
    if resolved is None:
        return code, result, lines
    label = resolved

    steps = list(dict.fromkeys(s for _, listed in STAGES.values() for s in listed))
    if step not in steps:
        return 2, {"wave": label, "error": "unknown_step", "found": step, "valid": steps}, [
            f"REFUSE: {step!r} is not a bmad-dev-wave step.",
            f"  Valid steps: {', '.join(steps)}.",
        ]

    where = locate(project_root, label)
    refusal = where_refusal(where, label)
    if refusal:
        return refusal
    marker = wave_dir(where.base, label) / f"step-{step}.done"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()
    return 0, {"wave": label, "step": step, "marker": str(marker),
               "record": str(record_path(where.base, label))}, [
        f"Wave {label}: step {step} marked done at {marker}."]


def pend(project_root, label, questions=None):
    """Write step 4.5's pending marker beside the record, holding the bytes
    of the `questions` file; with no file, remove the marker."""
    root = state_root(project_root)
    code, result, lines, resolved = _structural(root, label)
    if resolved is None:
        return code, result, lines
    label = resolved

    body = None
    if questions is not None:
        try:
            body = questions.read_bytes()
        except OSError:
            body = b""
        if not body.strip():
            return 2, {"wave": label, "error": "no_questions", "file": str(questions)}, [
                f"REFUSE: {questions} is missing or empty.",
                "  The pending marker holds step 4.5's open questions; write them",
                "  to that file first.",
            ]

    where = locate(project_root, label)
    refusal = where_refusal(where, label)
    if refusal:
        return refusal
    marker = wave_dir(where.base, label) / PENDING
    result = {"wave": label, "marker": str(marker), "record": str(record_path(where.base, label))}
    if body is None:
        cleared = marker.is_file()
        marker.unlink(missing_ok=True)
        return 0, dict(result, cleared=cleared), [
            f"Wave {label}: {'removed' if cleared else 'no'} pending marker at {marker}."]
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_bytes(body)
    return 0, result, [f"Wave {label}: step 4.5's open questions are pending at {marker}."]


def adopt(project_root, label, source_root):
    """Copy a worktree's `.bmad/wave-<ID>/` into the project root's, before the
    worktree is removed.

    A session rooted in the wave's worktree writes the record and markers
    there, and the directory is ignored, so `git worktree remove` takes it
    with it (ffbapp wave 6B, copied out by hand). This is the copy, and it is
    here because only this script writes `wave.md`.

    Nothing is overwritten. A file the root already holds with the same bytes
    is skipped; one it holds with different bytes is a conflict, and any
    conflict refuses before anything is copied, naming the files. Which copy
    is right is a human's call, as clearing a block is.
    """
    root = state_root(project_root)
    code, result, lines, resolved = _structural(root, label)
    if resolved is None:
        return code, result, lines
    label = resolved

    inside = [w for w in (_cwd(), os.environ.get("CLAUDE_PROJECT_DIR")) if w and _within(w, source_root)]
    if inside:
        return 1, {"wave": label, "error": "inside_worktree", "from": str(source_root),
                   "inside": inside}, [
            f"REFUSE: this session runs inside {source_root}:",
        ] + [f"  {w}" for w in inside] + [
            "  Nothing was copied. Removing that worktree next would remove the",
            "  wave gate's hook with it, and every later call in this session would",
            "  run ungated. Start a session in the main checkout,",
            f"  {root}, and run /bmad-merge-wave {label} there.",
        ]

    src = wave_dir(Path(source_root), label)
    dst = wave_dir(root, label)
    if src.resolve() == dst.resolve():
        src_files = []
    else:
        src_files = sorted(p for p in src.rglob("*") if p.is_file()) if src.is_dir() else []

    copy, identical, conflicts = [], [], []
    for f in src_files:
        rel = f.relative_to(src)
        target = dst / rel
        if not target.exists():
            copy.append(rel)
        elif target.is_file() and target.read_bytes() == f.read_bytes():
            identical.append(rel)
        else:
            conflicts.append(rel)

    result = {"wave": label, "from": str(src), "to": str(dst),
              "adopted": [str(r) for r in copy],
              "identical": [str(r) for r in identical],
              "conflicts": [str(r) for r in conflicts]}
    if conflicts:
        return 1, result, [
            f"REFUSE: wave {label}: {len(conflicts)} file(s) differ between",
            f"  {src}",
            f"  {dst}",
        ] + [f"    {r}" for r in conflicts] + [
            "  Nothing was copied. Decide which copy is right, then remove the",
            "  other by hand and run adopt again. The worktree's wave.md is the",
            "  one its session wrote last.",
        ]
    for rel in copy:
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, target)
    if not src_files:
        return 0, result, [f"Wave {label}: no checkpoint at {src}; nothing to adopt."]
    return 0, result, [f"Wave {label}: adopted {len(copy)} file(s) from {src} "
                       f"({len(identical)} already identical)."]


def _cwd():
    try:
        return os.getcwd()
    except OSError:
        return None


def _within(path, directory):
    path, directory = os.path.realpath(path), os.path.realpath(directory)
    return path == directory or path.startswith(directory.rstrip(os.sep) + os.sep)


def show(project_root, label=None):
    """Read-only. Never writes, never backfills, never refuses a readable map."""
    start, project_root = project_root, state_root(project_root)
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
        where = locate(start, one)
        refusal = where_refusal(where, one)
        if refusal:
            waves.append({"wave": one, "status": None, "state": refusal[1]["error"],
                          "reentry_step": None})
            continue
        record = read_record(where.base, one)
        if record is None:
            waves.append({"wave": one, "status": None, "state": "unmigrated",
                          "reentry_step": None})
            continue
        status = record.get("status")
        if status not in STATUSES or record.get("_corrupt"):
            waves.append({"wave": one, "status": status, "state": "corrupt",
                          "reentry_step": None})
            continue
        waves.append({
            "wave": one,
            "status": status,
            "state": "ok",
            "reentry_step": reentry_step(where.base, one, status),
            "reason": record.get("reason"),
            "updated": record.get("updated"),
        })
    return 0, {"waves": waves, "valid": list(STATUSES)}, [
        f"{w['wave']}: {w['status'] or w['state']}" for w in waves
    ]


# ------------------------------------------------------------------ main

def main():
    # No prefix forms: wave_gate.py reads --status and --wave by their full
    # names, so `--stat` binding to --status would be a spelling it cannot see.
    ap = argparse.ArgumentParser(description="Wave lifecycle status: read, write, route.",
                                 allow_abbrev=False)
    ap.add_argument("verb", choices=["route", "set", "show", "adopt", "mark", "pend"])
    ap.add_argument("--project-root", default=".", help="project root (default: cwd)")
    ap.add_argument("--wave", help="wave label as it appears in waves.md (e.g. 5D)")
    ap.add_argument("--status", help="for set: one of " + ", ".join(STATUSES))
    ap.add_argument("--reason", help="for set --status blocked: why, on one line")
    ap.add_argument("--from", dest="source", help="for adopt: the wave's worktree")
    ap.add_argument("--step", help="for mark: the dev-wave step done (e.g. 4.5)")
    ap.add_argument("--questions-file", help="for pend: the file holding step 4.5's questions")
    ap.add_argument("--clear", action="store_true", help="for pend: remove the pending marker")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    if args.verb == "show":
        code, result, lines = show(root, args.wave)
    elif args.verb == "adopt":
        if not args.wave or not args.source:
            ap.error("adopt needs --wave and --from")
        code, result, lines = adopt(root, args.wave, Path(args.source).resolve())
    elif args.verb == "route":
        if not args.wave:
            ap.error("route needs --wave")
        code, result, lines = route(root, args.wave)
    elif args.verb == "mark":
        if not args.wave or not args.step:
            ap.error("mark needs --wave and --step")
        code, result, lines = mark(root, args.wave, args.step)
    elif args.verb == "pend":
        if not args.wave or bool(args.questions_file) == args.clear:
            ap.error("pend needs --wave and one of --questions-file or --clear")
        questions = None if args.clear else Path(args.questions_file).resolve()
        code, result, lines = pend(root, args.wave, questions)
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
