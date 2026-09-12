#!/usr/bin/env python3
"""The hook half of the harness: the tool calls the wave rules deny.

Phase 4 of docs/harness-conversion-plan.md. Phases 1 to 3 each left the same
gap behind, and wrote it down three times: the verdict became a script's exit
code, but running the script and honouring its exit were still the agent's
choice, because the fork shipped PostToolUse and SessionEnd hooks and no
PreToolUse, so no tool call was ever denied. This is the one PreToolUse hook
the plan asked for, plus the SessionEnd half Phase 2's step 4.5 needed.

  wave_gate.py pre-tool-use  --project-root P   stdin: the PreToolUse JSON.
      Exit 0 allows the call. Exit 2 denies it; stderr names the rule and the
      remedy, and Claude Code feeds that back to the agent.
  wave_gate.py session-end   --project-root P   stdin: the SessionEnd JSON.
      Blocks every wave paused at step 4.5 with its question unanswered.
      Exit 0 always: SessionEnd cannot block, so this one only records.

Four rules, each read off disk and none of them a judgement:

  closure   Nothing touches _bmad-output/epic-closure/epic-<N>/ unless
            check_review_records.py --epic N exits 0. Phase 1's gate, run by
            the hook at the moment the closure artifact would be written,
            rather than by the closing agent at a step it may skip.
  verdict   docs/wave-<id>/evaluation-<n>.md is written by evaluate_wave.py
            record and by nothing else. A verdict typed by the agent whose
            work it grades is not a verdict.
  review    wave_status.py set --status in-review is denied for a wave whose
            latest evaluation on disk is not PASS. There is no way into the
            review stage except through the evaluator, so step 7 cannot be
            walked past.
  in-place  The session that recorded NEEDS_WORK for a wave cannot edit that
            wave's worktree. The findings are the next session's opening
            prompt, and the session that built the wave is the one least able
            to judge whether a fix answered them. The hook notes the session
            id when it sees `evaluate_wave.py record` and holds that session
            to it until a later session records a new verdict.

Write, Edit and MultiEdit are matched exactly, by file_path. Bash is matched
by the command's text naming the guarded path or the guarded script: a
substring test, not a parse. A command that reaches a guarded file through a
variable, a prior cd, or a here-doc is not seen, and that is the known gap.

Stdlib only. Imports wave_status.py and evaluate_wave.py from its own
directory, so the vocabulary, the record paths and the verdict parser stay
defined once.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evaluate_wave  # noqa: E402
import wave_status  # noqa: E402

# Phase 1's gate. Same relative layout in skills/ and in .claude/skills/, which
# is how the wave skills reach each other's scripts too.
CLOSURE_GATE = HERE.parent.parent / "bmad-close-epic" / "scripts" / "check_review_records.py"

FILE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")

CLOSURE_PATH = re.compile(r"_bmad-output/epic-closure/epic-(\d+)(?=/|$|\s|['\"])")
EVALUATION_PATH = re.compile(r"docs/wave-[^/\s'\"]+/evaluation-\d+\.md")
STATUS_SET = re.compile(r"wave_status\.py\b.*\bset\b")
STATUS_ARG = re.compile(r"--status(?:=|\s+)(\S+)")
RECORD_CMD = re.compile(r"evaluate_wave\.py\b.*\brecord\b")
WAVE_ARG = re.compile(r"--wave(?:=|\s+)(\S+)")

# What a redirect, tee, cp or mv is writing into. `2>/dev/null` is a redirect
# of a descriptor, not of content, so a `>` preceded by a digit or `&` is not
# a write.
REDIRECT_TARGET = re.compile(r"(?:(?<![0-9&])>>?|\btee\b(?:\s+-a)?|\b(?:cp|mv)\b\s+\S+)\s*(\S+)")
# Any command shape that changes files. Used only for the in-place rule, where
# the state is "this session halted", so a false positive costs a re-read of
# the reason and a true positive is the whole point.
WRITE_SHAPE = re.compile(
    r"(?<![0-9&])>|\btee\b|\bcp\b|\bmv\b|\brm\b|\bsed\s+-i|\bpatch\b|"
    r"\bgit\b(?:\s+-[-\w]+(?:\s+\S+)?)*\s+(?:add|commit|apply|am|checkout|restore|reset)\b")

PENDING_MARKER = "step-4.5.pending"
SESSION_FILE = "evaluation-session"


class Deny(Exception):
    def __init__(self, rule, lines):
        super().__init__(rule)
        self.rule = rule
        self.lines = lines


# ------------------------------------------------------------------ helpers

def resolve_path(root, file_path):
    p = Path(file_path)
    if not p.is_absolute():
        p = root / p
    try:
        return p.resolve()
    except OSError:
        return p


def bash_writes_to(command, pattern):
    """Does this command redirect, tee, cp, mv or sed -i into a path matching `pattern`?"""
    for m in REDIRECT_TARGET.finditer(command):
        if pattern.search(m.group(1)):
            return True
    return bool(re.search(r"\bsed\s+-i", command)) and bool(pattern.search(command))


def wave_worktree(root, label):
    """The checkout whose branch is this wave's, from `git worktree list`.

    Real branch names carry tool prefixes and hashes
    (claude/wave-5d-categories-exposure-ddd660), so the match is the wave
    label as a path segment prefix, case-insensitively. The main checkout is
    an entry too, so a wave built on the main checkout resolves to the root.
    """
    p = subprocess.run(["git", "-C", str(root), "worktree", "list", "--porcelain"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return None
    needle = re.compile(rf"(?:^|/)wave-{re.escape(label.lower())}(?:-|$)")
    path = None
    for line in p.stdout.splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):]
        elif line.startswith("branch ") and path and needle.search(line[len("branch "):].lower()):
            return Path(path).resolve()
    return None


def latest_verdict(root, label):
    """(verdict, path) of the newest evaluation record, or (None, None)."""
    priors = evaluate_wave.prior_evaluations(root, label)
    if not priors:
        return None, None
    latest = priors[-1]
    return evaluate_wave.read_verdict(latest.read_text(encoding="utf-8", errors="ignore")), latest


def session_file(root, label):
    return wave_status.wave_dir(root, label) / SESSION_FILE


# -------------------------------------------------------------------- rules

def closure_rule(root, tool, tool_input):
    text = tool_input.get("file_path", "") if tool in FILE_TOOLS else tool_input.get("command", "")
    for epic in sorted({int(n) for n in CLOSURE_PATH.findall(text or "")}):
        if not CLOSURE_GATE.is_file():
            raise Deny("closure", [
                f"epic {epic}: the review-record gate is missing at {CLOSURE_GATE}.",
                "  Nothing may be written under _bmad-output/epic-closure/ without it.",
                "  Restore the file (./install.sh --validate-only names it) and retry."])
        p = subprocess.run([sys.executable, str(CLOSURE_GATE), "--project-root", str(root),
                            "--epic", str(epic)], capture_output=True, text=True)
        if p.returncode != 0:
            raise Deny("closure", [
                f"epic {epic}: check_review_records.py exited {p.returncode}, so no closure "
                "artifact may be written for it."]
                + ["  " + line for line in p.stderr.strip().splitlines()]
                + ["  The gate has no flag and no override; the remedy is in its output."])


def verdict_rule(root, tool, tool_input):
    if tool in FILE_TOOLS:
        if EVALUATION_PATH.search(str(resolve_path(root, tool_input.get("file_path", "")))):
            raise Deny("verdict", [
                f"{tool_input.get('file_path')} is an evaluation record.",
                "  Only `evaluate_wave.py record` writes those, from the evaluator's own",
                "  output. A verdict written by the agent whose work it grades is not one."])
    elif tool == "Bash" and bash_writes_to(tool_input.get("command", ""), EVALUATION_PATH):
        raise Deny("verdict", [
            "This command writes into a docs/wave-<id>/evaluation-<n>.md record.",
            "  Only `evaluate_wave.py record` writes those, from the evaluator's own",
            "  output. A verdict written by the agent whose work it grades is not one."])


def review_rule(root, tool, tool_input):
    if tool != "Bash":
        return
    command = tool_input.get("command", "")
    if not STATUS_SET.search(command):
        return
    status = STATUS_ARG.search(command)
    wave = WAVE_ARG.search(command)
    if not status or status.group(1) != wave_status.IN_REVIEW or not wave:
        return
    labels = wave_status.wave_map_labels(root)
    label = wave_status.resolve_label(labels, wave.group(1)) if labels else None
    if label is None:
        return  # wave_status.py refuses this itself, exit 2
    verdict, path = latest_verdict(root, label)
    if verdict == evaluate_wave.PASS:
        return
    if path is None:
        raise Deny("review", [
            f"wave {label} has no evaluation on disk, so it cannot enter review.",
            "  Step 7 dispatches the fresh-context evaluator and records its verdict",
            "  with `evaluate_wave.py record`; the review stage opens on PASS and on",
            "  nothing else. Reviewing the wave in this context is not a substitute."])
    rel = path.relative_to(root)
    raise Deny("review", [
        f"wave {label}'s latest evaluation ({rel}) is "
        f"{verdict or 'unreadable'}, not PASS, so it cannot enter review.",
        "  NEEDS_WORK: halt; the findings open the next session (bmad-resume-wave).",
        "  UPSTREAM_CAUSE: fix the artifact the record names, not the code.",
        "  Unreadable: repair or delete the record; do not guess what it said."])


def note_recording_session(root, tool, tool_input, session_id):
    """Bookkeeping, not a denial: remember which session is recording a verdict."""
    if tool != "Bash" or not session_id:
        return
    command = tool_input.get("command", "")
    wave = WAVE_ARG.search(command)
    if not RECORD_CMD.search(command) or not wave:
        return
    labels = wave_status.wave_map_labels(root)
    label = wave_status.resolve_label(labels, wave.group(1)) if labels else None
    if label is None:
        return
    path = session_file(root, label)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(session_id + "\n", encoding="utf-8")


def in_place_rule(root, tool, tool_input, session_id):
    bmad = root / ".bmad"
    if not session_id or not bmad.is_dir():
        return
    for d in sorted(bmad.iterdir()):
        if not d.is_dir() or not d.name.lower().startswith("wave-"):
            continue
        sf = d / SESSION_FILE
        if not sf.is_file() or sf.read_text(encoding="utf-8").strip() != session_id:
            continue
        label = d.name[len("wave-"):]
        verdict, path = latest_verdict(root, label)
        if verdict != evaluate_wave.NEEDS_WORK:
            continue
        wt = wave_worktree(root, label)
        if wt is None:
            continue
        rel = path.relative_to(root)
        why = [
            f"this session recorded NEEDS_WORK for wave {label} ({rel}) and may not",
            "  edit that wave's worktree afterwards. The context that built the wave",
            "  is the context least able to judge whether a fix answered a finding.",
            f"  Halt. The findings open the next session: /bmad-resume-wave {label}."]
        if tool in FILE_TOOLS:
            target = resolve_path(root, tool_input.get("file_path", ""))
            if target == wt or wt in target.parents:
                raise Deny("in-place", [f"{tool} to {target}:"] + why)
        elif tool == "Bash":
            command = tool_input.get("command", "")
            if WRITE_SHAPE.search(command) and (wt == root.resolve() or str(wt) in command):
                raise Deny("in-place", ["this command writes into the wave's worktree:"] + why)


# ------------------------------------------------------------------- events

def pre_tool_use(root, event):
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    session_id = event.get("session_id", "")
    if tool not in FILE_TOOLS and tool != "Bash":
        return 0
    try:
        closure_rule(root, tool, tool_input)
        verdict_rule(root, tool, tool_input)
        review_rule(root, tool, tool_input)
        in_place_rule(root, tool, tool_input, session_id)
        note_recording_session(root, tool, tool_input, session_id)
    except Deny as d:
        sys.stderr.write(f"wave-gate DENIED ({d.rule}): " + "\n".join(d.lines) + "\n")
        return 2
    return 0


def session_end(root, event):
    """Block every wave whose step 4.5 question this session leaves unanswered.

    A `resume` end is the same conversation continuing elsewhere, so its
    question is still live and is not blocked.
    """
    if event.get("reason") == "resume":
        return 0
    bmad = root / ".bmad"
    if not bmad.is_dir():
        return 0
    session_id = event.get("session_id", "?")
    labels = wave_status.wave_map_labels(root) or []
    for d in sorted(bmad.iterdir()):
        if not d.is_dir() or not (d / PENDING_MARKER).is_file():
            continue
        wanted = d.name[len("wave-"):]
        label = wave_status.resolve_label(labels, wanted) or wanted
        code, result, lines = wave_status.set_status(
            root, label, wave_status.BLOCKED,
            reason=f"session {session_id} ended with step 4.5's open question unanswered "
                   f"({d.name}/{PENDING_MARKER} present)")
        print(f"wave-gate session-end: wave {label}: exit {code}")
        for line in lines:
            print("  " + line)
    return 0


def main():
    ap = argparse.ArgumentParser(description="PreToolUse and SessionEnd hook for the wave rules.")
    ap.add_argument("event", choices=["pre-tool-use", "session-end"])
    ap.add_argument("--project-root", default=None,
                    help="project root (default: the event's cwd, then the process cwd)")
    args = ap.parse_args()
    try:
        event = json.load(sys.stdin)
    except (ValueError, OSError):
        event = {}
    root = Path(args.project_root or event.get("cwd") or os.getcwd()).resolve()
    if args.event == "pre-tool-use":
        sys.exit(pre_tool_use(root, event))
    sys.exit(session_end(root, event))


if __name__ == "__main__":
    main()
