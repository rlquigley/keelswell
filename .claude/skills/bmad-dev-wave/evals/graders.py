#!/usr/bin/env python3
"""Code graders for the dev-wave eval pairs. They read end state, never a model.

R5 of docs/reviews/harness-engineering-review-v1.md. A grader is handed one
trial directory and returns the list of things that are wrong with what the
session left behind; an empty list is a pass. Each reads files the scripts
and the hooks wrote, the `gh` stub's log, and the Agent calls in the
session's own transcript. None reads the session's prose.

    <trial>/proj/                 the main checkout, .bmad/ in it
    <trial>/proj-wave-1a/         the wave's worktree, docs/wave-1a/ in it
    <trial>/gh.log                one line per call the `gh` stub received
    <trial>/transcript.jsonl      the session's stream-json output

Stdlib only.
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import evaluate_wave  # noqa: E402
import select_reviewers  # noqa: E402
import wave_status  # noqa: E402

WAVE = "1A"
PROJECT = "proj"
WORKTREE = "proj-wave-1a"

CODER = "keelswell-wave-coder"
EVALUATOR = "keelswell-wave-evaluator"
REVIEWER = "keelswell-wave-reviewer"
HOOK_HEADER = "<!-- Written by the evaluator hook ("
PENDING = "step-4.5.pending"


class Trial:
    """What one session left behind."""

    def __init__(self, root):
        self.root = Path(root)
        self.proj = self.root / PROJECT
        self.worktree = self.root / WORKTREE
        self.state = wave_status.wave_dir(self.proj, WAVE)
        self.docs = self.worktree / "docs" / f"wave-{WAVE.lower()}"
        self._events = None

    def status(self):
        record = wave_status.read_record(self.proj, WAVE)
        return record.get("status") if record else None

    def history(self):
        path = wave_status.record_path(self.proj, WAVE)
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def gh_calls(self):
        log = self.root / "gh.log"
        return log.read_text(encoding="utf-8").splitlines() if log.is_file() else []

    def evaluations(self):
        return evaluate_wave.prior_evaluations(self.worktree, WAVE)

    def events(self):
        if self._events is None:
            self._events = []
            path = self.root / "transcript.jsonl"
            if path.is_file():
                for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                    try:
                        self._events.append(json.loads(line))
                    except ValueError:
                        continue
        return self._events

    def tool_uses(self):
        """Main-thread tool calls, in order: (id, name, input)."""
        calls = []
        for event in self.events():
            if event.get("type") != "assistant" or event.get("parent_tool_use_id"):
                continue
            for block in (event.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    calls.append((block.get("id"), block.get("name"), block.get("input") or {}))
        return calls

    def agent_calls(self):
        return [i for _, name, i in self.tool_uses() if name in ("Agent", "Task")]

    def tool_result(self, tool_use_id):
        for event in self.events():
            if event.get("type") != "user":
                continue
            content = (event.get("message") or {}).get("content")
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_result" \
                        and block.get("tool_use_id") == tool_use_id:
                    body = block.get("content")
                    if isinstance(body, list):
                        return "".join(b.get("text", "") for b in body if isinstance(b, dict))
                    return body or ""
        return ""

    def result(self):
        """The session's result line. A session that waits on a background
        subagent prints one per leg: cost is cumulative on the last, time and
        turns are per leg and are summed here."""
        legs = [e for e in self.events() if e.get("type") == "result"]
        if not legs:
            return {}
        last = dict(legs[-1])
        last["duration_ms"] = sum(e.get("duration_ms") or 0 for e in legs)
        last["num_turns"] = sum(e.get("num_turns") or 0 for e in legs)
        last["permission_denials"] = [d for e in legs for d in e.get("permission_denials") or []]
        return last

    def selector_output(self):
        """What select_reviewers.py told this session, from the last --json call."""
        found = None
        for tool_id, name, tool_input in self.tool_uses():
            command = tool_input.get("command") or ""
            if name == "Bash" and "select_reviewers.py" in command and "--json" in command:
                text = self.tool_result(tool_id)
                start = text.find("{")
                try:
                    found = json.loads(text[start:]) if start >= 0 else found
                except ValueError:
                    try:
                        found, _ = json.JSONDecoder().raw_decode(text[start:])
                    except ValueError:
                        pass
        return found


def _hook_written(trial, failures):
    """The first evaluation record, if the hook wrote one. Appends what is wrong."""
    records = trial.evaluations()
    if not records:
        failures.append("no evaluation record: the evaluator's hook wrote nothing")
        return None
    text = records[0].read_text(encoding="utf-8", errors="replace")
    if not text.startswith(HOOK_HEADER):
        failures.append(f"{records[0].name} does not open with the hook's header")
    if not any(c.get("subagent_type") == EVALUATOR for c in trial.agent_calls()):
        failures.append(f"no Agent call dispatched {EVALUATOR}")
    return evaluate_wave.read_verdict(text)


# ------------------------------------------------- pair A, the evaluator gate

def a_fire(trial):
    """A planted stubbed acceptance test: the wave halts at step 8."""
    failures = []
    verdict = _hook_written(trial, failures)
    if verdict is not None and verdict != evaluate_wave.NEEDS_WORK:
        failures.append(f"evaluation-1.md says {verdict}, not NEEDS_WORK")
    if trial.status() != wave_status.IN_PROGRESS:
        failures.append(f"status is {trial.status()}, not in-progress")
    if (trial.docs / "review-party.md").exists():
        failures.append("review-party.md exists: the wave went on to review")
    if any(call.startswith("pr create") for call in trial.gh_calls()):
        failures.append("gh pr create was called")
    return failures


def a_pass(trial):
    """The same wave without the defect: PASS, and the review stage opens."""
    failures = []
    verdict = _hook_written(trial, failures)
    if verdict is not None and verdict != evaluate_wave.PASS:
        failures.append(f"evaluation-1.md says {verdict}, not PASS")
    if trial.status() != wave_status.IN_REVIEW:
        failures.append(f"status is {trial.status()}, not in-review")
    return failures


# --------------------------------------------- pair B, the open-questions gate

def _coder_dispatched(trial):
    return any(c.get("subagent_type") == CODER for c in trial.agent_calls())


def b_fire(trial):
    """An open question tagged to the wave's story: the wave halts at 4.5."""
    failures = []
    if not (trial.state / PENDING).is_file():
        failures.append(f"no {PENDING}: the gate did not fire")
    if _coder_dispatched(trial):
        failures.append(f"{CODER} was dispatched past an unfired gate")
    return failures


def b_none(trial):
    """No question tagged to the wave: it reaches ready-for-dev."""
    failures = []
    if (trial.state / PENDING).exists():
        failures.append(f"{PENDING} exists: the gate fired on nothing")
    reached = trial.status() == wave_status.READY_FOR_DEV \
        or f"-> {wave_status.READY_FOR_DEV}" in trial.history()
    if not reached:
        failures.append(f"status is {trial.status()}; the wave never reached ready-for-dev")
    return failures


# --------------------------------------------- pair C, the reviewer dispatch

def _roster():
    rows, _ = select_reviewers.load_table(select_reviewers.DEFAULT_TABLE)
    return rows


def _named(text, rows):
    """The roles whose skill a dispatch prompt names, whole id only."""
    return {row["role"] for row in rows
            if re.search(r"(?<![\w-])" + re.escape(row["skill"]) + r"(?![\w-])", text or "")}


def _dispatch(trial, want_fallback):
    failures = []
    calls = trial.agent_calls()
    reviewers = [c for c in calls if c.get("subagent_type") == REVIEWER]
    if not reviewers:
        return [f"no Agent call dispatched {REVIEWER}"]
    for call in calls:
        kind = call.get("subagent_type")
        if kind not in (EVALUATOR, REVIEWER):
            failures.append(f"an Agent call dispatched {kind or 'no subagent_type'}; "
                            f"steps 8 and 10 dispatch only {EVALUATOR} and {REVIEWER}")
        if "model" in call:
            failures.append(f"an Agent call to {kind} carries model={call['model']!r}")

    selector = trial.selector_output()
    if selector is None:
        return failures + ["select_reviewers.py --json was never run, or printed no JSON"]
    selected = {hit["role"] for hit in selector.get("selected") or []}
    fallback = selector.get("fallback")
    if bool(fallback) != want_fallback:
        failures.append(f"the selector returned {'a' if fallback else 'no'} fallback; "
                        f"this task's wave should {'get' if want_fallback else 'not get'} one")

    rows = _roster()
    named = [_named(c.get("prompt"), rows) for c in reviewers]
    dispatched = set().union(*named)
    for role in sorted(selected - dispatched):
        failures.append(f"{role} was selected and no reviewer's prompt names its skill")
    for role in sorted(dispatched - selected):
        failures.append(f"a reviewer's prompt names {role}'s skill and the selector did not return it")
    unnamed = sum(1 for roles in named if not roles)
    if fallback and unnamed < 2:
        failures.append(f"the fallback is two reviewers with no persona; {unnamed} dispatched")
    if not fallback and unnamed:
        failures.append(f"{unnamed} reviewer(s) dispatched with no persona and no fallback returned")

    record = trial.docs / "review-party.md"
    if not record.is_file():
        return failures + ["no review-party.md"]
    text = record.read_text(encoding="utf-8", errors="replace")
    by_role = {row["role"]: row for row in rows}
    for role in sorted(selected):
        row = by_role.get(role, {})
        if not any(name and name in text for name in (role, row.get("skill"), row.get("display"))):
            failures.append(f"review-party.md does not record {role}")
    if fallback and fallback.get("record_as", "fallback") not in text:
        failures.append("review-party.md does not record the fallback")
    return failures


def c_specialist(trial):
    """A diff that fires a specialist row: that reviewer is dispatched by name."""
    return _dispatch(trial, want_fallback=False)


def c_generalist(trial):
    """A diff that fires no specialist: the fallback is dispatched."""
    return _dispatch(trial, want_fallback=True)


GRADERS = {
    "a_fire": a_fire, "a_pass": a_pass,
    "b_fire": b_fire, "b_none": b_none,
    "c_specialist": c_specialist, "c_generalist": c_generalist,
}
