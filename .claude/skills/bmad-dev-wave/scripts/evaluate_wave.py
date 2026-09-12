#!/usr/bin/env python3
"""Dispatch, record and route on a wave's fresh-context evaluation.

Phase 3 of docs/harness-conversion-plan.md. The review bmad-dev-wave ran at
step 7 happened in the context that did the work, through the bmad-agent-qa
persona. It is replaced by a subagent defined at
`.claude/agents/keelswell-wave-evaluator.md` whose tool list excludes every
tool that can write, run or delegate, dispatched with a context that never saw
the build.

This script is the mechanical half. Three things the agent no longer decides:

  * whether the evaluator is safe to dispatch. `check` reads the definition's
    declared tools and refuses if any of them could edit. The claim "the
    evaluator cannot edit" is then a file the script read, not a sentence in a
    skill anyone can drift away from.
  * which pass this is. `dispatch` counts the evaluation records already on
    disk. BMAD's stopping rule fires on the third pass, and a rule whose
    trigger the reviewed party counts is not a rule.
  * what the verdict was. `record` parses the evaluator's own VERDICT line and
    returns it as an exit code, so bmad-dev-wave routes on what the evaluator
    said rather than on its own summary of what the evaluator said.

  evaluate_wave.py check       --project-root P
  evaluate_wave.py dispatch    --project-root P --wave 5D
  evaluate_wave.py record      --project-root P --wave 5D  [< verdict.txt]
  evaluate_wave.py opening-prompt --project-root P --wave 5D

Exit codes:
  0  safe / proceed / PASS
  1  NEEDS_WORK -- the wave halts and the next session opens with the findings
  2  structural: no wave map, or the wave is not in it
  3  refuse: the evaluator definition is missing, declares no tools, or
     declares a tool that can write, run or delegate; or a verdict that
     cannot be parsed
  4  UPSTREAM_CAUSE -- the third-pass rule fired; fix the named artifact, not
     the code

Stdout is JSON for the caller to quote. Stderr is the refusal or the notice,
written to be acted on. Stdlib only.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WAVE_MAP = Path("_bmad-output") / "planning-artifacts" / "waves.md"

# The evaluator lives under `.claude/agents/`, which no BMAD module declares
# and the installer never reads. That is the whole reason it is there rather
# than beside bmad-agent-qa: module.yaml's agent registry is the collision
# surface (its own header documents duplicate [agents.*] tables corrupting
# config.toml), and `.claude/agents/` is the only place a `tools:` list is
# enforced by the harness instead of being prose the model may ignore.
EVALUATOR = Path(".claude") / "agents" / "keelswell-wave-evaluator.md"

# "6A" -> epic 6, letter A. Epic numbers are not capped at one digit.
WAVE_LABEL = re.compile(r"^(\d+)([A-Za-z]+)$")

# docs/wave-5d/evaluation-2.md -> pass 2.
EVALUATION_FILE = re.compile(r"^evaluation-(\d+)\.md$", re.IGNORECASE)

VERDICT_LINE = re.compile(r"^\s*VERDICT\s*:\s*([A-Z_]+)\s*$", re.MULTILINE)

PASS = "PASS"
NEEDS_WORK = "NEEDS_WORK"
UPSTREAM_CAUSE = "UPSTREAM_CAUSE"
VERDICTS = (PASS, NEEDS_WORK, UPSTREAM_CAUSE)

VERDICT_EXIT = {PASS: 0, NEEDS_WORK: 1, UPSTREAM_CAUSE: 4}

# BMAD's stopping rule: non-trivial findings on a third pass mean the problem
# is upstream of the change. The evaluator is told to diagnose instead of
# producing a fourth round of findings, and this is where that number lives.
THIRD_PASS = 3

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
            "  Step 7 cannot dispatch. Restore the file or re-run install.sh.",
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


def dispatch(project_root, label_wanted):
    """What step 7 needs to know before it dispatches the evaluator."""
    label, why = resolve_label(project_root, label_wanted)
    if label is None:
        return 2, {"wave": label_wanted}, [f"Cannot evaluate: {why}."]

    code, check, lines = check_evaluator(project_root)
    if code != 0:
        check["wave"] = label
        return code, check, lines

    priors = prior_evaluations(project_root, label)
    pass_number = len(priors) + 1
    d = docs_dir(project_root, label)
    result = {
        "wave": label,
        "definition": str(EVALUATOR),
        "declared_tools": check["declared_tools"],
        "pass_number": pass_number,
        "third_pass_rule": pass_number >= THIRD_PASS,
        "prior_evaluations": [str(p.relative_to(project_root)) for p in priors],
        "prior_verdicts": [
            read_verdict(p.read_text(encoding="utf-8", errors="ignore"))
            for p in priors
        ],
        "evidence": {
            "test_design": str((d / "test-design.md").relative_to(project_root)),
            "diff": str((d / "wave-diff.patch").relative_to(project_root)),
            "verify_output": str((d / "verify-output.txt").relative_to(project_root)),
        },
        "record_to": str((d / f"evaluation-{pass_number}.md").relative_to(project_root)),
    }
    missing = [k for k, v in result["evidence"].items()
               if not (project_root / v).is_file()]
    result["evidence_missing"] = missing

    notice = [f"Wave {label}: evaluation pass {pass_number}."]
    if result["third_pass_rule"]:
        notice += [
            f"  THIRD-PASS RULE ARMED. This is pass {pass_number} on the same wave.",
            "  Dispatch the evaluator with the third-pass instruction: if it",
            "  still has non-trivial findings it must return UPSTREAM_CAUSE and",
            "  name the weak spec, contradiction or ambiguous rule behind them,",
            "  not a fourth round of findings.",
        ]
    if missing:
        notice += [
            "  Evidence not yet written: " + ", ".join(missing) + ".",
            "  Write it before dispatching. The evaluator has no Bash and",
            "  cannot produce it for itself.",
        ]
    return 0, result, notice


def record(project_root, label_wanted, text):
    """Write the evaluator's verdict where the next session will find it."""
    label, why = resolve_label(project_root, label_wanted)
    if label is None:
        return 2, {"wave": label_wanted}, [f"Cannot record: {why}."]

    verdict = read_verdict(text)
    if verdict is None:
        return 3, {"wave": label}, [
            "The evaluator's output carries no readable VERDICT line.",
            "  Expected exactly one of: VERDICT: "
            + " | ".join(VERDICTS) + ".",
            "  Not recorded, and not summarized on its behalf. Re-dispatch.",
        ]

    priors = prior_evaluations(project_root, label)
    pass_number = len(priors) + 1
    d = docs_dir(project_root, label)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"evaluation-{pass_number}.md"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    header = (
        f"<!-- Written by bmad-dev-wave/scripts/evaluate_wave.py at {now}.\n"
        f"     Wave {label}, evaluation pass {pass_number}. The body below is\n"
        "     the evaluator subagent's own output, unedited. -->\n\n"
    )
    path.write_text(header + text.rstrip() + "\n", encoding="utf-8")

    rel = str(path.relative_to(project_root))
    result = {"wave": label, "verdict": verdict, "pass_number": pass_number,
              "recorded_to": rel,
              "third_pass_rule": pass_number >= THIRD_PASS}

    if verdict == PASS:
        lines = [f"Wave {label} evaluation pass {pass_number}: PASS. "
                 f"Recorded at {rel}.",
                 "  Step 7 is satisfied. Continue at step 8."]
    elif verdict == NEEDS_WORK:
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
            "  The third-pass rule fired. Three passes on one wave means the",
            "  defect is upstream of the code. Fix the artifact the record",
            "  names -- the story, waves.md, the architecture doc, the Project",
            "  Conventions Block -- and do not run a fourth pass over the same",
            "  spec.",
        ]
    return VERDICT_EXIT[verdict], result, lines


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
    verdict = read_verdict(body)
    rel = str(latest.relative_to(project_root))
    pass_number = len(priors)

    if verdict == PASS:
        return 0, {"wave": label, "open": False, "verdict": verdict,
                   "latest": rel}, [
            f"Wave {label}'s latest evaluation ({rel}) is PASS. Nothing is "
            "owed; open the session normally."]
    if verdict is None:
        return 3, {"wave": label, "latest": rel}, [
            f"{rel} carries no readable VERDICT line. Repair or delete it; do "
            "not guess what it said."]

    prompt = (
        f"You are resuming wave {label}. You did not build it and the session "
        f"that did is gone.\n\n"
        f"A fresh-context evaluator reviewed the wave's landed work and "
        f"returned {verdict} on pass {pass_number}. Its findings are below, "
        f"verbatim, from {rel}. The evaluator has no Write, Edit or Bash, so "
        f"nothing here has been fixed.\n\n"
        f"Close every finding it raised before you do anything else with this "
        f"wave. Do not re-argue a finding you cannot reproduce -- record that "
        f"you could not reproduce it, and say so in the next pass rather than "
        f"deleting it. When the findings are closed, step 7 dispatches the "
        f"evaluator again as pass {pass_number + 1}"
        + (", and the third-pass rule is armed: if it still has non-trivial "
           "findings it will name the spec or rule behind them instead of "
           "listing a fourth round.\n\n"
           if pass_number + 1 >= THIRD_PASS else ".\n\n")
        + "--- begin evaluator output ---\n"
        + body.strip()
        + "\n--- end evaluator output ---\n"
    )
    return 1, {"wave": label, "open": True, "verdict": verdict,
               "pass_number": pass_number, "latest": rel,
               "prompt": prompt}, [prompt]


def main():
    ap = argparse.ArgumentParser(
        description="Dispatch, record and route on a wave's fresh-context evaluation.")
    ap.add_argument("verb", choices=["check", "dispatch", "record", "opening-prompt"])
    ap.add_argument("--project-root", default=".", help="project root (default: cwd)")
    ap.add_argument("--wave", help="wave label as it appears in waves.md (e.g. 5D)")
    ap.add_argument("--verdict-file",
                    help="for record: the evaluator's output (default: stdin)")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    if args.verb == "check":
        code, result, lines = check_evaluator(root)
    elif args.verb == "dispatch":
        if not args.wave:
            ap.error("dispatch needs --wave")
        code, result, lines = dispatch(root, args.wave)
    elif args.verb == "record":
        if not args.wave:
            ap.error("record needs --wave")
        text = (Path(args.verdict_file).read_text(encoding="utf-8")
                if args.verdict_file else sys.stdin.read())
        code, result, lines = record(root, args.wave, text)
    else:
        if not args.wave:
            ap.error("opening-prompt needs --wave")
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
