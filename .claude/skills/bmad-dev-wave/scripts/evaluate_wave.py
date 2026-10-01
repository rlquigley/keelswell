#!/usr/bin/env python3
"""Verify, dispatch, record and route on a wave's fresh-context evaluation.

Phase 3 of docs/harness-conversion-plan.md moved a wave's review out of the
context that built it, into a subagent defined at
`.claude/agents/keelswell-wave-evaluator.md` whose tool list excludes every
tool that can write, run or delegate. R3 of
docs/reviews/harness-engineering-review-v1.md moved what was still the
builder's to do by hand -- the evidence, and writing the verdict down -- into
this script and the hook that runs it.

What the building agent no longer decides:

  * whether the evaluator is safe to dispatch. `check` reads the definition's
    declared tools and refuses if any of them could edit. The claim "the
    evaluator cannot edit" is then a file the script read, not a sentence in a
    skill anyone can drift away from.
  * what the evaluator is shown. `verify` runs tests/verify-fast.sh and stamps
    its output with the command, the exit code and the HEAD it ran at.
    `dispatch` refuses evidence that is missing or was stamped at another
    HEAD, and writes the diff itself, from the wave's merge-base with main.
  * which pass this is. `dispatch` counts the evaluation records already on
    disk. BMAD's stopping rule fires on the third pass, and a rule whose
    trigger the reviewed party counts is not a rule.
  * what the verdict was, and who wrote it down. `record` is run by the
    evaluator hook (.claude/hooks/wave-evaluator-record.sh) on the subagent's
    own report, and by nothing else: the wave gate denies it to Bash. A
    record on disk is therefore the evaluator's text, not the builder's
    account of it. `verdict` reads that record back as an exit code.

  evaluate_wave.py check          --project-root P
  evaluate_wave.py verify         --project-root P --wave 5D
  evaluate_wave.py dispatch       --project-root P --wave 5D
  evaluate_wave.py record                              stdin: the hook event
  evaluate_wave.py verdict        --project-root P --wave 5D
  evaluate_wave.py opening-prompt --project-root P --wave 5D

P is the checkout the wave is built in. `.bmad/` is read from the main
checkout, which git names from any worktree of it.

Exit codes:
  0  safe / proceed / PASS
  1  NEEDS_WORK -- the wave halts and the next session opens with the
     findings; for `verify`, the verify script failed (its output is stamped
     all the same)
  2  structural: no wave map, or the wave is not in it
  3  refuse: the evaluator definition is missing, declares a tool that can
     write, run or delegate, or lacks `effort: high`; the verify output is
     missing, unstamped or stale; or nothing is recorded for the dispatch
  4  UPSTREAM_CAUSE -- the third-pass rule fired; fix the named artifact, not
     the code

Stdout is JSON for the caller to quote. Stderr is the refusal or the notice,
written to be acted on. `record` is the exception, because Claude Code reads
a hook's stdout: it prints a decision or nothing. Stdlib only.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wave_status  # noqa: E402

WAVE_MAP = Path("_bmad-output") / "planning-artifacts" / "waves.md"

# The evaluator lives under `.claude/agents/`, which no BMAD module declares
# and the installer never reads. That is the whole reason it is there rather
# than beside bmad-agent-qa: module.yaml's agent registry is the collision
# surface (its own header documents duplicate [agents.*] tables corrupting
# config.toml), and `.claude/agents/` is the only place a `tools:` list is
# enforced by the harness instead of being prose the model may ignore.
EVALUATOR = Path(".claude") / "agents" / "keelswell-wave-evaluator.md"
EVALUATOR_AGENT = EVALUATOR.stem

# Sessions at different effort levels return verdicts that cannot be compared,
# and a subagent with no `effort:` inherits its session's.
EVALUATOR_EFFORT = "high"

# "6A" -> epic 6, letter A. Epic numbers are not capped at one digit.
WAVE_LABEL = re.compile(r"^(\d+)([A-Za-z]+)$")

# docs/wave-5d/evaluation-2.md -> pass 2.
EVALUATION_FILE = re.compile(r"^evaluation-(\d+)\.md$", re.IGNORECASE)

VERDICT_LINE = re.compile(r"^\s*VERDICT\s*:\s*([A-Z_]+)\s*$", re.MULTILINE)
VERDICT_ANY = re.compile(r"^\s*VERDICT\s*:.*$", re.MULTILINE)
# "### [HIGH] no test for AC-3", the evaluator definition's own heading.
FINDING_HEADING = re.compile(r"^#{3}\s*\[([^\]\n]+)\]", re.MULTILINE)

PASS = "PASS"
NEEDS_WORK = "NEEDS_WORK"
UPSTREAM_CAUSE = "UPSTREAM_CAUSE"
VERDICTS = (PASS, NEEDS_WORK, UPSTREAM_CAUSE)

VERDICT_EXIT = {PASS: 0, NEEDS_WORK: 1, UPSTREAM_CAUSE: 4}

# BMAD's stopping rule: non-trivial findings on a third pass mean the problem
# is upstream of the change. The evaluator is told to diagnose instead of
# producing a fourth round of findings, and this is where that number lives.
THIRD_PASS = 3

# The severity ladder is the definition's own, read from it and never retyped
# here: its bullets (`- **HIGH** -- ...`) name the severities and one sentence
# names the trivial one. `check` refuses a definition these no longer match.
SEVERITY_BULLET = re.compile(r"^- \*\*([A-Z]+)\*\* -- ", re.MULTILINE)
TRIVIAL_LINE = re.compile(r"`([A-Z]+)` findings alone are trivial")

# The one verify command (RQ, 2026-10-01): dev-wave step 7 names it and no
# config key does.
VERIFY_SCRIPT = Path("tests") / "verify-fast.sh"
STAMP = re.compile(r"^# verify-stamp command=(?P<command>.+) exit=(?P<exit>-?\d+) "
                   r"head=(?P<head>[0-9a-f]{7,64}) at=(?P<at>\S+)$")

# .bmad/wave-<id>/evaluation-pending: `dispatch` leaves it, the hook reads it.
# A finished evaluator's event names its session and not the wave it graded.
PENDING_FILE = "evaluation-pending"
# .bmad/wave-<id>/evaluation-session: the session whose evaluator was last
# recorded, which the gate's in-place rule holds to a NEEDS_WORK.
SESSION_FILE = "evaluation-session"
HANDBACK_TOOL = "SubagentHandback"
# A report that cannot be recorded is sent back this many times, then dropped.
HOOK_ROUNDS = 2

# "- 2026-10-02T09:00:00+00:00  in-progress -> in-progress  (upstream fix: docs/stories/5.4.md)",
# the history line `wave_status.py set --status in-progress --reason
# "upstream fix: <artifact>"` writes.
UPSTREAM_FIX = re.compile(r"^- (\S+)\s+\S+ -> " + re.escape(wave_status.IN_PROGRESS)
                          + r"\s+\(upstream fix:\s*\S", re.IGNORECASE)
WRITTEN_AT = re.compile(r"\bat (\d{4}-\d\d-\d\dT[\d:]+(?:[+-][\d:]+)?)")

GIT_TIMEOUT = 60

# Any tool that can write a file, run a command, or hand work to something
# that can. A definition declaring one of these is refused: the guarantee is
# the tool list, so a hole in the tool list is the guarantee gone. Bash is
# here because `bash -c 'cat > f'` is an edit, and Task because a subagent it
# spawns inherits no such restriction (RQ ruled no Bash, 2026-09-11).
DENIED_TOOLS = {
    "write", "edit", "multiedit", "notebookedit", "update",
    "bash", "bashoutput", "killshell", "killbash",
    "task", "agent", "slashcommand", "skill",
    "artifact", "senduserfile", "computer",
}

# Tools whose only power is to look. Anything outside this and DENIED_TOOLS is
# reported as unrecognized rather than silently allowed -- a tool this script
# has never heard of is not evidence that it cannot edit.
READ_ONLY_TOOLS = {"read", "glob", "grep", "webfetch", "websearch",
                   "todowrite", "listmcpresourcestool", "readmcpresourcetool"}


# ---------------------------------------------------------------- wave map

def parse_wave_labels(text):
    """Every Wave label in the map's pipe table, in table order.

    Same reader as wave_status.py and check_review_records.py: waves.md is one
    flat table ordered by execution, any pipe table with a "Wave" column is
    read, and rows whose first cell is not a wave label are skipped.
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


def resolve_label(project_root, wanted):
    """The map's own spelling of `wanted`, or None with a structural reason."""
    path = project_root / WAVE_MAP
    if not path.is_file():
        return None, f"no wave map at {WAVE_MAP}"
    labels = parse_wave_labels(path.read_text(encoding="utf-8", errors="ignore"))
    for label in labels:
        if label.lower() == wanted.lower():
            return label, None
    return None, (f"wave {wanted} is not in {WAVE_MAP} "
                  f"({len(labels)} waves there: {', '.join(labels) or 'none'})")


def docs_dir(project_root, label):
    """`docs/wave-<id>/`, resolved case-insensitively.

    The real instance spells `.bmad/wave-5D/` with the map's casing and
    `docs/wave-5d/` lower-cased, so neither can be assumed. An existing
    directory wins; a new one gets the lower-cased spelling the docs tree uses.
    """
    docs = project_root / "docs"
    wanted = f"wave-{label}".lower()
    if docs.is_dir():
        for child in sorted(docs.iterdir()):
            if child.is_dir() and child.name.lower() == wanted:
                return child
    return docs / wanted


# ----------------------------------------------------------------------- git

def _run_git(root, *args):
    """(exit code, stdout) of a git command; (None, "") when git cannot run."""
    try:
        p = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=GIT_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None, ""
    return p.returncode, p.stdout


def _git(root, *args):
    code, out = _run_git(root, *args)
    return out if code == 0 else None


def state_root(start):
    """The checkout holding `.bmad/`, found from the one the wave is built in.

    dev-wave keeps `.bmad/` in the main checkout and builds in a worktree.
    git's common directory names the main checkout from any worktree of it.
    """
    out = _git(start, "rev-parse", "--path-format=absolute", "--git-common-dir")
    common = Path(out.strip()) if out and out.strip() else None
    main = common.parent if common is not None and common.name == ".git" else None
    for d in ([main] if main else []) + [start, *start.parents]:
        if (d / ".bmad").is_dir():
            return d
    return main or start


def merge_base(project_root):
    """Where the wave's branch left main. Read from git, never from the agent."""
    for ref in ("main", "origin/main"):
        out = _git(project_root, "merge-base", "HEAD", ref)
        if out and out.strip():
            return out.strip()
    return None


def wave_diff(project_root, base, skip):
    """Everything the wave changed since `base`, committed or not, as a patch.

    Untracked files are in it as additions: a diff that left them out would
    hide every file the wave created and has not committed yet. `.bmad/` is
    the harness's own state, not the wave's work, and stays out.
    """
    diff = _git(project_root, "diff", base, "--", ".", *[f":(exclude){s}" for s in skip])
    untracked = _git(project_root, "ls-files", "--others", "--exclude-standard")
    if diff is None or untracked is None:
        return None
    for name in untracked.splitlines():
        if name and name not in skip and not name.startswith(".bmad/"):
            # --no-index exits 1 when the two sides differ, which they always do.
            diff += _run_git(project_root, "diff", "--no-index", "--", "/dev/null", name)[1]
    return diff


# ------------------------------------------------- the evaluator definition

def parse_frontmatter(text):
    """Frontmatter as {key: value}, values kept raw. None if there is none.

    A list value (`tools:` followed by `- Read`) comes back as the joined
    items, so the caller sees the same shape whichever spelling was used.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    front = {}
    key = None
    items = []
    for line in lines[1:]:
        if line.strip() == "---":
            if key is not None and items:
                front[key] = ", ".join(items)
            return front
        stripped = line.strip()
        if stripped.startswith("- ") and key is not None:
            items.append(stripped[2:].strip().strip("'\""))
            continue
        if ":" in line and not line.startswith((" ", "\t")):
            if key is not None and items:
                front[key] = ", ".join(items)
                items = []
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip("'\"")
            if value:
                front[key] = value
                key = None
    return None


def severities(project_root):
    """(the definition's severity ladder, the trivial ones), or None.

    Trivial severities are the ones a PASS may carry. Both come from the
    evaluator definition's own text, so the parser and the evaluator cannot
    disagree about what a finding is called.
    """
    try:
        text = (project_root / EVALUATOR).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    ladder = SEVERITY_BULLET.findall(text)
    trivial = {s for s in TRIVIAL_LINE.findall(text) if s in ladder}
    if len(ladder) < 2 or not trivial or len(trivial) == len(ladder):
        return None
    return ladder, trivial


def check_evaluator(project_root):
    """Is the evaluator definition safe to dispatch?

    Every failure here is exit 3 and names the file. The default is refuse: a
    definition this script cannot read is not assumed harmless, because the
    only thing standing between the evaluator and the codebase is this list.
    """
    path = project_root / EVALUATOR
    result = {"definition": str(EVALUATOR), "safe": False}
    if not path.is_file():
        return 3, result, [
            f"No evaluator definition at {EVALUATOR}.",
            "  Step 8 cannot dispatch. Restore the file or re-run install.sh.",
        ]

    front = parse_frontmatter(path.read_text(encoding="utf-8", errors="ignore"))
    if front is None:
        return 3, result, [
            f"{EVALUATOR} has no frontmatter, so it declares no tool list.",
            "  A subagent with no `tools:` key inherits every tool the parent",
            "  has, Write and Edit included. Refusing to dispatch.",
        ]

    raw = front.get("tools", "")
    declared = [t.strip() for t in raw.replace("\n", ",").split(",") if t.strip()]
    result["declared_tools"] = declared

    if not declared:
        return 3, result, [
            f"{EVALUATOR} declares no tools.",
            "  An absent list is not an empty list: the subagent inherits the",
            "  parent's tools, Write and Edit included. Refusing to dispatch.",
        ]
    if any(t == "*" for t in declared):
        return 3, result, [
            f"{EVALUATOR} declares `*`, which is every tool.",
            "  Refusing to dispatch.",
        ]

    denied = [t for t in declared if t.split("__")[-1].lower() in DENIED_TOOLS]
    unknown = [t for t in declared
               if t.lower() not in READ_ONLY_TOOLS
               and t.split("__")[-1].lower() not in DENIED_TOOLS]
    result["denied_tools"] = denied
    result["unrecognized_tools"] = unknown

    if denied:
        return 3, result, [
            f"{EVALUATOR} declares a tool that can write, run or delegate: "
            + ", ".join(denied) + ".",
            "  The evaluator's whole guarantee is that it cannot fix what it",
            "  finds. Remove the tool; do not add a rule asking it not to use",
            "  the tool. Refusing to dispatch.",
        ]
    if unknown:
        return 3, result, [
            f"{EVALUATOR} declares a tool this check does not recognize: "
            + ", ".join(unknown) + ".",
            "  Unrecognized is refused, not allowed: a tool the check has",
            "  never heard of is not evidence that it cannot edit. Add it to",
            "  READ_ONLY_TOOLS or DENIED_TOOLS in this script, deliberately.",
        ]
    if "memory" in front:
        return 3, result, [
            f"{EVALUATOR} sets `memory:`, which gives a subagent Read, Write and",
            "  Edit whatever its `tools:` list says. Remove the key. Refusing to",
            "  dispatch.",
        ]

    result["effort"] = front.get("effort")
    if result["effort"] != EVALUATOR_EFFORT:
        return 3, result, [
            f"{EVALUATOR} does not set `effort: {EVALUATOR_EFFORT}` "
            f"(found: {result['effort'] or 'nothing'}).",
            "  Without it the evaluator runs at whatever effort its session",
            "  happens to be at, and verdicts from different sessions cannot be",
            "  compared. Restore the line. Refusing to dispatch.",
        ]

    found = severities(project_root)
    if found is None:
        return 3, result, [
            f"{EVALUATOR} no longer states its severity ladder where this script",
            "  reads it: `- **NAME** -- ` bullets, and the sentence naming which",
            "  severity alone is trivial. A PASS is checked against that ladder,",
            "  so it must be readable. Refusing to dispatch.",
        ]
    result["severities"], result["trivial"] = found[0], sorted(found[1])

    result["safe"] = True
    return 0, result, []


# ------------------------------------------------------- evaluation records

def prior_evaluations(project_root, label):
    """Every `docs/wave-<id>/evaluation-<n>.md`, ordered by n."""
    d = docs_dir(project_root, label)
    found = []
    if d.is_dir():
        for child in d.iterdir():
            m = EVALUATION_FILE.match(child.name)
            if m and child.is_file():
                found.append((int(m.group(1)), child))
    return [p for _, p in sorted(found)]


def read_verdict(text):
    """The VERDICT line's value, or None. The evaluator's word, not a guess."""
    m = VERDICT_LINE.search(text)
    if not m:
        return None
    return m.group(1) if m.group(1) in VERDICTS else None


def report_problem(text, trivial):
    """Why this report cannot be recorded, in one clause, or None.

    A parser's job, not a model's: one VERDICT line, a verdict from the list,
    and a PASS that agrees with the severities it lists under itself.
    """
    lines = VERDICT_ANY.findall(text)
    if not lines:
        return "it carries no VERDICT line"
    if len(lines) > 1:
        return f"it carries {len(lines)} VERDICT lines and a report has exactly one"
    verdict = read_verdict(text)
    if verdict is None:
        return (f"its VERDICT line ({lines[0].strip()}) is not one of VERDICT: "
                + ", VERDICT: ".join(VERDICTS))
    if verdict == PASS:
        held = sorted({s.strip() for s in FINDING_HEADING.findall(text)
                       if s.strip().upper() not in trivial})
        if held:
            return ("it says PASS and lists a finding that is not trivial ("
                    + ", ".join(f"[{s}]" for s in held) + "), which is NEEDS_WORK")
    return None


def _when(text):
    try:
        when = datetime.fromisoformat(text)
    except ValueError:
        return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def written_at(path):
    """When a record was written: its header's timestamp, else the file's."""
    try:
        head = path.read_text(encoding="utf-8", errors="ignore")[:400]
    except OSError:
        head = ""
    m = WRITTEN_AT.search(head)
    # Whole seconds, as every timestamp these scripts write is.
    return ((_when(m.group(1)) if m else None)
            or datetime.fromtimestamp(int(path.stat().st_mtime), timezone.utc))


def rule_base(state, label, priors):
    """How many of `priors` the third-pass rule no longer counts.

    The count restarts after an UPSTREAM_CAUSE whose fix is on record: a
    history line in the wave's lifecycle record, written by wave_status.py
    after that evaluation, naming the artifact that was fixed. Without the
    restart a wave re-entered against a corrected spec is armed at once, and
    NEEDS_WORK can never be returned for it again.
    """
    record = wave_status.read_record(state, label) or {}
    fixes = []
    for line in wave_status.history_lines(record.get("_body") or ""):
        m = UPSTREAM_FIX.match(line)
        when = _when(m.group(1)) if m else None
        if when:
            fixes.append(when)
    base = 0
    for n, path in enumerate(priors, 1):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if read_verdict(text) == UPSTREAM_CAUSE and any(f >= written_at(path) for f in fixes):
            base = n
    return base


def read_stamp(path):
    """The stamp `verify` wrote on the first line of its output, or None."""
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            m = STAMP.match(f.readline().strip())
    except OSError:
        return None
    return m.groupdict() if m else None


def read_marker(path):
    """A pending-dispatch marker, or None if there is none this can use."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not (isinstance(data, dict) and isinstance(data.get("wave"), str)
            and isinstance(data.get("project_root"), str)
            and isinstance(data.get("pass_number"), int)):
        return None
    return data


def write_marker(path, marker):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")


# ------------------------------------------------------------- the evidence

def verify(project_root, label_wanted):
    """Run the verify script and stamp what it printed."""
    label, why = resolve_label(project_root, label_wanted)
    if label is None:
        return 2, {"wave": label_wanted}, [f"Cannot verify: {why}."]

    if not (project_root / VERIFY_SCRIPT).is_file():
        return 3, {"wave": label}, [
            f"No {VERIFY_SCRIPT} in {project_root}.",
            "  It is the one verify command this step runs. Add it, or have it",
            "  call the project's own suite. Nothing was run and nothing stamped.",
        ]
    head = (_git(project_root, "rev-parse", "HEAD") or "").strip()
    if not head:
        return 3, {"wave": label}, [
            f"{project_root} is not a git checkout with a commit, so the verify",
            "  output cannot be stamped with the HEAD it ran at. Nothing was run.",
        ]

    command = f"bash {VERIFY_SCRIPT}"
    p = subprocess.run(["bash", str(VERIFY_SCRIPT)], cwd=str(project_root),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, encoding="utf-8", errors="replace")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    d = docs_dir(project_root, label)
    d.mkdir(parents=True, exist_ok=True)
    path = d / "verify-output.txt"
    path.write_text(
        f"# verify-stamp command={command} exit={p.returncode} head={head} at={now}\n"
        + p.stdout, encoding="utf-8")

    rel = str(path.relative_to(project_root))
    result = {"wave": label, "command": command, "verify_exit": p.returncode,
              "head": head, "verify_output": rel}
    if p.returncode == 0:
        return 0, result, [f"Wave {label}: {command} exited 0 at {head[:12]}. "
                           f"Stamped at {rel}."]
    return 1, result, [
        f"Wave {label}: {command} exited {p.returncode} at {head[:12]}. "
        f"Stamped at {rel}.",
        "  Verify FAIL: offer edit, demote or abort before evaluating.",
    ]


def dispatch(project_root, label_wanted, session_id):
    """What step 8 needs before it dispatches the evaluator, and its evidence."""
    label, why = resolve_label(project_root, label_wanted)
    if label is None:
        return 2, {"wave": label_wanted}, [f"Cannot evaluate: {why}."]

    code, check, lines = check_evaluator(project_root)
    if code != 0:
        check["wave"] = label
        return code, check, lines

    d = docs_dir(project_root, label)
    verify_path, diff_path = d / "verify-output.txt", d / "wave-diff.patch"

    def rel(path):
        return str(path.relative_to(project_root))

    def refuse(*lines):
        return 3, {"wave": label}, list(lines)

    rerun = (f"  Run: evaluate_wave.py verify --project-root {project_root} "
             f"--wave {label}")
    head = (_git(project_root, "rev-parse", "HEAD") or "").strip()
    if not head:
        return refuse(f"{project_root} is not a git checkout with a commit, so "
                      "neither the diff nor the verify stamp can be read.")
    stamp = read_stamp(verify_path)
    if not verify_path.is_file():
        return refuse(f"Wave {label} has no verify output at {rel(verify_path)}.",
                      "  Verify runs before the evaluator, which has no Bash and reads",
                      "  that output as its execution evidence.", rerun)
    if stamp is None:
        return refuse(f"{rel(verify_path)} carries no verify stamp: it was written by",
                      "  hand, or before `verify` existed. What ran, and at which commit,",
                      "  cannot be read from it.", rerun)
    if stamp["head"] != head:
        return refuse(f"{rel(verify_path)} is stale: stamped at {stamp['head'][:12]},",
                      f"  and the worktree's HEAD is {head[:12]}.", rerun)
    base = merge_base(project_root)
    if base is None:
        return refuse(f"{project_root} has no merge-base with main or origin/main,",
                      "  so the wave's diff has no base to be taken from.")
    if not session_id:
        return refuse("CLAUDE_CODE_SESSION_ID is not set, so this was not run by a",
                      "  Claude Code session's Bash tool. The evaluator hook matches a",
                      "  report to its dispatch by session, and would record nothing.")
    diff = wave_diff(project_root, base, [rel(diff_path), rel(verify_path)])
    if diff is None:
        return refuse(f"git could not produce the wave's diff from {base[:12]}.")
    diff_path.write_text(diff, encoding="utf-8")

    priors = prior_evaluations(project_root, label)
    pass_number = len(priors) + 1
    state = state_root(project_root)
    rule_pass = pass_number - rule_base(state, label, priors)
    result = {
        "wave": label,
        "definition": str(EVALUATOR),
        "declared_tools": check["declared_tools"],
        "pass_number": pass_number,
        "rule_pass": rule_pass,
        "third_pass_rule": rule_pass >= THIRD_PASS,
        "prior_evaluations": [rel(p) for p in priors],
        "prior_verdicts": [
            read_verdict(p.read_text(encoding="utf-8", errors="ignore"))
            for p in priors
        ],
        "base": base,
        "head": head,
        "verify_exit": int(stamp["exit"]),
        "evidence": {
            "test_design": rel(d / "test-design.md"),
            "diff": rel(diff_path),
            "verify_output": rel(verify_path),
        },
        "record_to": rel(d / f"evaluation-{pass_number}.md"),
    }
    result["evidence_missing"] = [] if (d / "test-design.md").is_file() else ["test_design"]

    notice = [f"Wave {label}: evaluation pass {pass_number}."]
    if rule_pass != pass_number:
        notice.append(f"  Pass {rule_pass} since the upstream fix on record; tell the "
                      "evaluator that number.")
    if result["third_pass_rule"]:
        notice += [
            f"  THIRD-PASS RULE ARMED. This is pass {rule_pass} on the same spec.",
            "  Dispatch the evaluator with the third-pass instruction: if it",
            "  still has non-trivial findings it must return UPSTREAM_CAUSE and",
            "  name the weak spec, contradiction or ambiguous rule behind them,",
            "  not a fourth round of findings.",
        ]
    if result["verify_exit"] != 0:
        notice.append(f"  The stamped verify run exited {result['verify_exit']}.")
    if result["evidence_missing"]:
        notice.append("  No test design at " + result["evidence"]["test_design"] + ".")

    # A fix made at step 10 comes back through here. The review record is then
    # newer than the last evaluation, and the evaluator is shown what was found.
    review = d / "review-party.md"
    if review.is_file() and priors:
        front = parse_frontmatter(review.read_text(encoding="utf-8", errors="ignore")) or {}
        try:
            created = date.fromisoformat(front.get("created", ""))
        except ValueError:
            created = None
        if created is not None and created >= written_at(priors[-1]).date():
            result["evidence"]["review_record"] = rel(review)
            notice += [
                f"  {rel(review)} is dated {created}, on or after the latest",
                "  evaluation: this pass re-checks the wave after step 10's fixes.",
                "  Hand the evaluator the review record with the rest.",
            ]

    write_marker(wave_status.wave_dir(state, label) / PENDING_FILE, {
        "session_id": session_id, "wave": label, "pass_number": pass_number,
        "project_root": str(project_root), "rounds": 0,
        "dispatched": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    notice += [
        f"  Dispatch one `{EVALUATOR_AGENT}` subagent now. Its hook records the",
        f"  report at {result['record_to']}; then run `evaluate_wave.py verdict`.",
    ]
    return 0, result, notice


# --------------------------------------------------------------- the record

def pending(state, session_id):
    """Every (marker path, marker) this session has left by dispatching."""
    found = []
    bmad = state / ".bmad"
    if session_id and bmad.is_dir():
        for d in sorted(bmad.iterdir()):
            marker = read_marker(d / PENDING_FILE)
            if marker and marker.get("session_id") == session_id:
                found.append((d / PENDING_FILE, marker))
    return found


def record(event):
    """The evaluator hook: write the subagent's own report where the next
    session will find it. Returns (exit code, stdout, stderr lines).

    Three events reach this, all from the `keelswell-wave-evaluator` subagent.
    Outside auto mode the report is the subagent's last message, on
    SubagentStop, and a report that cannot be recorded is sent back by a block
    decision. In auto mode the subagent hands its report over with the
    SubagentHandback tool: PreToolUse sends back one that cannot be recorded,
    before the builder sees it, and PostToolUse records the one that landed.
    Nothing can send the subagent back after the hand-over (measured on CLI
    2.1.287), which is why the check sits before it.
    """
    if event.get("agent_type") != EVALUATOR_AGENT:
        return 0, "", []
    name = event.get("hook_event_name")
    if name == "SubagentStop":
        text, source = event.get("last_assistant_message"), name
    elif name in ("PreToolUse", "PostToolUse") and event.get("tool_name") == HANDBACK_TOOL:
        text = (event.get("tool_input") or {}).get("message")
        source = f"{name} on {HANDBACK_TOOL}"
    else:
        return 0, "", []
    if not isinstance(text, str) or not text.strip():
        # SubagentStop after a hand-over carries no message; the report already went.
        return 0, "", []

    session_id = event.get("session_id") or ""
    start = Path(event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    found = pending(state_root(start), session_id)
    if len(found) != 1:
        why = ("no dispatch is pending for this session" if not found else
               "this session has dispatches pending for waves "
               + ", ".join(m["wave"] for _, m in found)
               + ", so the report cannot be told apart")
        return 0, "", [f"evaluator hook ({source}): {why}. Nothing recorded.",
                       "  `evaluate_wave.py dispatch` leaves the marker; run it first."]
    marker_path, marker = found[0]
    root, n = Path(marker["project_root"]), marker["pass_number"]
    label, why = resolve_label(root, marker["wave"])
    if label is None:
        return 0, "", [f"evaluator hook ({source}): {marker_path} names a wave "
                       f"this cannot place ({why}). Nothing recorded."]

    target = docs_dir(root, label) / f"evaluation-{n}.md"
    if target.is_file():
        return 0, "", []  # the other path recorded this pass

    problem = report_problem(text, (severities(root) or ([], set()))[1])
    if problem is not None:
        marker["refused"] = problem
        if name != "PostToolUse" and marker.get("rounds", 0) < HOOK_ROUNDS:
            marker["rounds"] = marker.get("rounds", 0) + 1
            write_marker(marker_path, marker)
            reason = (
                f"Your report for wave {label} was not recorded: {problem}. Send the "
                "whole report again, in your output format, with exactly one VERDICT "
                "line (VERDICT: PASS, VERDICT: NEEDS_WORK or VERDICT: UPSTREAM_CAUSE) "
                "that agrees with the findings under it.")
            if name == "PreToolUse":
                return 2, "", [reason]
            return 0, json.dumps({"decision": "block", "reason": reason}), []
        write_marker(marker_path, marker)
        return 0, "", [f"evaluator hook ({source}): wave {label} pass {n} not "
                       f"recorded: {problem}. Dispatch the evaluator again."]
    if name == "PreToolUse":
        return 0, "", []  # PostToolUse records it once the hand-over has landed

    if len(prior_evaluations(root, label)) + 1 != n:
        return 0, "", [f"evaluator hook ({source}): wave {label} was dispatched as "
                       f"pass {n} and its records have changed since. Nothing "
                       "recorded. Dispatch again."]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    header = (
        f"<!-- Written by the evaluator hook ({source}) through\n"
        f"     bmad-dev-wave/scripts/evaluate_wave.py record at {now}.\n"
        f"     Wave {label}, evaluation pass {n}. Session {session_id},\n"
        f"     subagent {event.get('agent_id') or 'unknown'}.\n"
        "     The body below is the evaluator subagent's own output, unedited. -->\n\n"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(target, "x", encoding="utf-8") as f:
            f.write(header + text.rstrip() + "\n")
    except FileExistsError:
        return 0, "", []
    (marker_path.parent / SESSION_FILE).write_text(session_id + "\n", encoding="utf-8")
    marker_path.unlink()
    return 0, "", [f"evaluator hook ({source}): wave {label} pass {n} recorded at "
                   f"{target}: {read_verdict(text)}."]


def verdict(project_root, label_wanted):
    """The hook-written verdict for the latest dispatch, as an exit code."""
    label, why = resolve_label(project_root, label_wanted)
    if label is None:
        return 2, {"wave": label_wanted}, [f"No verdict: {why}."]

    marker = read_marker(wave_status.wave_dir(state_root(project_root), label) / PENDING_FILE)
    if marker is not None:
        return 3, {"wave": label, "pending_pass": marker["pass_number"],
                   "refused": marker.get("refused")}, [
            f"Wave {label}: pass {marker['pass_number']} was dispatched and nothing "
            "is recorded for it.",
            "  " + (f"The evaluator's report was refused: {marker['refused']}."
                    if marker.get("refused") else
                    "No evaluator report reached the hook: it was not dispatched, it "
                    "has not finished, or the hook is not registered."),
            "  Not recorded, and not summarized on its behalf. Run `dispatch` and",
            "  dispatch the evaluator again.",
        ]

    priors = prior_evaluations(project_root, label)
    if not priors:
        return 3, {"wave": label}, [
            f"Wave {label} has no evaluation on disk. Run `dispatch`, then dispatch",
            "  the evaluator; its hook writes the record."]
    latest = priors[-1]
    rel = str(latest.relative_to(project_root))
    pass_number = len(priors)
    found = read_verdict(latest.read_text(encoding="utf-8", errors="ignore"))
    if found is None:
        return 3, {"wave": label, "latest": rel}, [
            f"{rel} carries no readable VERDICT line. Repair or delete it; do "
            "not guess what it said."]

    result = {"wave": label, "verdict": found, "pass_number": pass_number,
              "recorded_to": rel}
    if found == PASS:
        lines = [f"Wave {label} evaluation pass {pass_number}: PASS. "
                 f"Recorded at {rel}.",
                 "  Step 8 is satisfied. Continue at step 9."]
    elif found == NEEDS_WORK:
        lines = [
            f"Wave {label} evaluation pass {pass_number}: NEEDS_WORK. "
            f"Recorded at {rel}.",
            "  Do not fix these findings in this session. They are the next",
            "  build session's opening prompt, which is the point of the",
            "  split: the context that built the wave is the context least",
            "  able to judge whether a fix answered the finding.",
            f"  Next session: /bmad-resume-wave {label}. Its opening prompt",
            "  comes from `evaluate_wave.py opening-prompt`.",
        ]
    else:
        lines = [
            f"Wave {label} evaluation pass {pass_number}: UPSTREAM_CAUSE. "
            f"Recorded at {rel}.",
            "  The third-pass rule fired. Three passes on one spec means the",
            "  defect is upstream of the code. Fix the artifact the record",
            "  names -- the story, waves.md, the architecture doc, the Project",
            "  Conventions Block -- and do not run a fourth pass over the same",
            "  spec. When it is fixed, put the fix on record, which restarts",
            "  the pass count:",
            f"    wave_status.py set --wave {label} --status in-progress \\",
            '        --reason "upstream fix: <the artifact>"',
        ]
    return VERDICT_EXIT[found], result, lines


def opening_prompt(project_root, label_wanted):
    """The next build session's opening prompt, when one is owed.

    The findings reach the next session as text this script produced from the
    record on disk, not as the previous session's recollection of them. The
    previous session may not exist any more; that is the case this is for.
    """
    label, why = resolve_label(project_root, label_wanted)
    if label is None:
        return 2, {"wave": label_wanted}, [f"No opening prompt: {why}."]

    priors = prior_evaluations(project_root, label)
    if not priors:
        return 0, {"wave": label, "open": False}, [
            f"Wave {label} has no evaluation on disk. Nothing is owed; open "
            "the session normally."]

    latest = priors[-1]
    body = latest.read_text(encoding="utf-8", errors="ignore")
    found = read_verdict(body)
    rel = str(latest.relative_to(project_root))
    pass_number = len(priors)

    if found == PASS:
        return 0, {"wave": label, "open": False, "verdict": found,
                   "latest": rel}, [
            f"Wave {label}'s latest evaluation ({rel}) is PASS. Nothing is "
            "owed; open the session normally."]
    if found is None:
        return 3, {"wave": label, "latest": rel}, [
            f"{rel} carries no readable VERDICT line. Repair or delete it; do "
            "not guess what it said."]

    next_rule_pass = pass_number + 1 - rule_base(state_root(project_root), label, priors)
    prompt = (
        f"You are resuming wave {label}. You did not build it and the session "
        f"that did is gone.\n\n"
        f"A fresh-context evaluator reviewed the wave's landed work and "
        f"returned {found} on pass {pass_number}. Its findings are below, "
        f"verbatim, from {rel}. The evaluator has no Write, Edit or Bash, so "
        f"nothing here has been fixed.\n\n"
        f"Close every finding it raised before you do anything else with this "
        f"wave. Do not re-argue a finding you cannot reproduce -- record that "
        f"you could not reproduce it, and say so in the next pass rather than "
        f"deleting it. When the findings are closed, step 7 verifies and step 8 "
        f"dispatches the evaluator again as pass {pass_number + 1}"
        + (", and the third-pass rule is armed: if it still has non-trivial "
           "findings it will name the spec or rule behind them instead of "
           "listing a fourth round.\n\n"
           if next_rule_pass >= THIRD_PASS else ".\n\n")
        + "--- begin evaluator output ---\n"
        + body.strip()
        + "\n--- end evaluator output ---\n"
    )
    return 1, {"wave": label, "open": True, "verdict": found,
               "pass_number": pass_number, "latest": rel,
               "prompt": prompt}, [prompt]


def main():
    # No prefix forms: wave_gate.py reads --wave by its full name.
    ap = argparse.ArgumentParser(
        description="Verify, dispatch, record and route on a wave's fresh-context evaluation.",
        allow_abbrev=False)
    ap.add_argument("verb", choices=["check", "verify", "dispatch", "record",
                                     "verdict", "opening-prompt"])
    ap.add_argument("--project-root", default=".", help="project root (default: cwd)")
    ap.add_argument("--wave", help="wave label as it appears in waves.md (e.g. 5D)")
    args = ap.parse_args()

    if args.verb == "record":
        # Run by the evaluator hook. Nothing here may exit 2: on SubagentStop
        # that would hand the subagent an error as its next instruction.
        try:
            event = json.load(sys.stdin)
            if not isinstance(event, dict):
                raise ValueError("not a JSON object")
        except ValueError:
            _write(sys.stderr, "evaluate_wave.py record takes a hook event on stdin and "
                               "is run by the evaluator hook, not by hand. Nothing recorded.\n")
            sys.exit(3)
        try:
            code, out, lines = record(event)
        except Exception as e:  # noqa: BLE001 -- a failure records nothing, and says so
            _write(sys.stderr, f"evaluator hook failed ({type(e).__name__}: {e}). "
                               "Nothing recorded.\n")
            sys.exit(1)
        if out:
            _write(sys.stdout, out + "\n")
        if lines:
            _write(sys.stderr, "\n".join(lines) + "\n")
        sys.exit(code)

    root = Path(args.project_root).resolve()
    if args.verb == "check":
        code, result, lines = check_evaluator(root)
    else:
        if not args.wave:
            ap.error(f"{args.verb} needs --wave")
        if args.verb == "verify":
            code, result, lines = verify(root, args.wave)
        elif args.verb == "dispatch":
            code, result, lines = dispatch(root, args.wave,
                                           os.environ.get("CLAUDE_CODE_SESSION_ID", ""))
        elif args.verb == "verdict":
            code, result, lines = verdict(root, args.wave)
        else:
            code, result, lines = opening_prompt(root, args.wave)

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
