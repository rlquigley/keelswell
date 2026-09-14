#!/usr/bin/env python3
"""Decide which reviewers a wave dispatches, from what the wave actually changed.

Phase 6.3 of docs/harness-conversion-plan.md. Step 10 of bmad-dev-wave used to
hardcode three domains -- "dispatch security, cost, and platform reviewers" --
and no wave skill referenced any of the sixteen fork-only agents at all. Waves
4A and 4B landed ffbapp's model work with no ML reviewer, and 4B is where the
defect 5D eventually caught originated.

WHY A SCRIPT AND NOT A PARAGRAPH. The same logic written as prose in SKILL.md
would sit in the layer [[structure-transfers-prose-does-not]] measured as the
one that regresses when the harness is moved to another model family; the
component ablation found tools and middleware carrying the improvement on
their own while the evolved system prompt alone regressed. A script plus a
table is dispatch, which is the layer that transfers. It lives under the
skill's own scripts/ -- the convention bmad-party-mode already uses -- so it
travels with the skill directory and survives an upstream refresh. Not
_bmad/scripts/: the installer owns that and wipes it.

NECESSITY, NOT A BUDGET. If eight domains are genuinely in the diff, this
prints eight. If one is, it prints one. There is no cap, no maximum and no
"top N most relevant" in this file, because a cap means choosing which real
gaps to skip looking for. What keeps it affordable is trigger precision: every
pattern in the table is answerable yes or no from the changed-file list and
the spec, without judgment. A trigger needing interpretation is a wrong
trigger, not a wrong rule.

AN EMPTY ANSWER IS AN ANSWER. Zero reviewers exits 0. A wave that touches no
infrastructure returns no platform reviewer, and that is the point of removing
the fixed three's exemption rather than a failure to be retried.

WHAT THE SPEC MATCHER REFUSES, AND WHY. Four rules, every one of them added
because a plain substring match got a real ffbapp wave wrong. They are stated
here rather than in the table because they apply to every phrase in it.

  1. Leading word boundary. "train" matches "training" and not "constraint".
     Wave 4A's test design contains "train" three times and all three are
     inside "constraint"; a substring match dispatches the ML reviewer on
     that and calls it precision.

  2. Front matter is not prose. Everything above the spec's second '---' is
     dropped. A test design's `inputDocuments:` list names every document the
     wave READ, so matching it dispatches a reviewer for every subject the
     wave consulted rather than every subject it changed.

  3. A negated sentence is not a hit. Waves 3D, 4B, 5C and 5D each say "No
     rendered surface exists in this wave" -- and a substring match read that
     sentence as proof a rendered surface exists and called the design critic.
     The sentence around each hit is checked for a negator from a fixed list.
     This is the one rule that can be wrong in both directions; it is written
     so that its failures dispatch an extra reviewer rather than skip a real
     one, which is the cheap direction.

  4. One mention is a cross-reference; two is the subject. A phrase must
     appear at least MIN_SPEC_OCCURRENCES times. Measured across all eighteen
     ffbapp waves, this separates cleanly: "backtest" appears 39 times in wave
     4B, 25 in 5B and 10 in 5A, all real backtest work, and exactly once in
     3D, 5C and 5D, every one of them a passing quotation of the architecture
     spine's component list. This is a precision rule inside one trigger. It
     is not a cap on the reviewer count; there is no such cap anywhere.

Usage:

    git diff --name-only main...HEAD > /tmp/changed.txt
    python3 select_reviewers.py select \\
        --wave 4B \\
        --changed-files /tmp/changed.txt \\
        --spec docs/wave-4B/test-design.md

    python3 select_reviewers.py check      # table parses and is well formed

Stdlib only, like wave_status.py and evaluate_wave.py beside it: the table is
read by the restricted parser below rather than by PyYAML, so a target
project's python3 needs nothing installed. The file is still valid YAML.
"""

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

DEFAULT_TABLE = Path(__file__).resolve().parent / "reviewer-triggers.yaml"

REQUIRED_FIELDS = ("role", "skill", "display", "source", "trigger")

# See rule 4 in the module docstring. Two, from the measurement across
# eighteen ffbapp waves, not from taste.
MIN_SPEC_OCCURRENCES = 2

# Bookkeeping the wave writes about itself, not product it changed. A
# session-wrap triage note under _bmad-output/ dispatched the security
# reviewer on five of eighteen ffbapp waves, on the strength of the word
# "session" in a directory name. The wave's own docs/wave-<id>/ artifacts are
# excluded too: they reach this script as --spec, where they belong, and
# counting them as changed files makes every wave look like a documentation
# wave. .github/ is deliberately NOT here -- a CI change is real platform work.
IGNORED_PATHS = (
    "_bmad-output/**",
    "_bmad/**",
    ".bmad/**",
    "docs/wave-*/**",
    "**/session-wrap/**",
    "HANDOFF.md",
    "TODO.md",
)

# Rule 3. A hit whose sentence carries one of these before it is a statement
# that the thing is absent, deferred, or out of scope.
NEGATORS = (
    "no", "not", "none", "never", "without", "absent", "n/a",
    "excluded", "deferred", "omits", "omitted", "unchanged",
)

_FRONT_MATTER = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n", re.DOTALL)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;:])\s+|\r?\n")


class TableError(Exception):
    """The trigger table is missing, unparseable, or malformed."""


# --------------------------------------------------------------------------
# The table
# --------------------------------------------------------------------------

def _unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _split_kv(text, lineno):
    if ":" not in text:
        raise TableError(f"line {lineno}: expected 'key: value', got {text!r}")
    key, _, value = text.partition(":")
    return key.strip(), value.strip()


def load_table(path):
    """Parse the restricted YAML subset the trigger table is written in.

    The shape is fixed and the parser is strict about it, which is deliberate:
    being unable to read anything else means `check` validates the table's
    layout as a side effect of reading it, with no second schema to maintain.

        version: 1                  indent 0, scalar
        reviewers:                  indent 0, the one list
          - role: custom-ml         indent 2, opens a reviewer
            skill: agent-ml         indent 4, scalar field
            paths:                  indent 4, opens a list
              - "**/backtest*"      indent 6, list item

    Comments and blank lines are skipped. A '#' inside a value is a literal.
    """
    if not path.is_file():
        raise TableError(f"trigger table not found: {path}")

    version = None
    reviewers = []
    current = None
    current_list = None

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()

        if indent == 0:
            current_list = None
            if line == "reviewers:":
                continue
            key, value = _split_kv(line, lineno)
            if key != "version":
                raise TableError(f"line {lineno}: unknown top-level key {key!r}")
            try:
                version = int(value)
            except ValueError:
                raise TableError(f"line {lineno}: version must be an integer, got {value!r}")

        elif indent == 2:
            if not line.startswith("- "):
                raise TableError(f"line {lineno}: expected a reviewer entry '- role: ...'")
            current = {}
            current_list = None
            reviewers.append(current)
            key, value = _split_kv(line[2:], lineno)
            current[key] = _unquote(value)

        elif indent == 4:
            if current is None:
                raise TableError(f"line {lineno}: field outside any reviewer entry")
            key, value = _split_kv(line, lineno)
            if value == "":
                current_list = []
                current[key] = current_list
            else:
                current_list = None
                current[key] = _unquote(value)

        elif indent == 6:
            if current_list is None:
                raise TableError(f"line {lineno}: list item under no list key")
            if not line.startswith("- "):
                raise TableError(f"line {lineno}: expected a list item '- ...'")
            current_list.append(_unquote(line[2:]))

        else:
            raise TableError(f"line {lineno}: unexpected indent {indent}")

    if version is None:
        raise TableError("table has no 'version' key")
    if version != 1:
        raise TableError(f"unsupported table version {version}; this script reads version 1")
    if not reviewers:
        raise TableError("table declares no reviewers")
    return reviewers


def validate(reviewers):
    """Every rule the table has to obey. Raises TableError naming the first break."""
    seen = set()
    for entry in reviewers:
        role = entry.get("role", "<no role>")
        for field in REQUIRED_FIELDS:
            if not entry.get(field):
                raise TableError(f"{role}: missing required field '{field}'")
        if role in seen:
            raise TableError(f"{role}: duplicate role code")
        seen.add(role)

        has_patterns = bool(entry.get("paths") or entry.get("spec"))
        if entry.get("inert"):
            if has_patterns:
                raise TableError(
                    f"{role}: an inert row cannot carry 'paths' or 'spec'; "
                    "a row either fires or it does not"
                )
        elif not has_patterns:
            raise TableError(
                f"{role}: no 'paths', no 'spec' and no 'inert'. A row that "
                "cannot fire must say why, so a missing trigger is visible "
                "rather than silent"
            )
        for key in ("paths", "spec"):
            if key in entry and not isinstance(entry[key], list):
                raise TableError(f"{role}: '{key}' must be a list")
    return reviewers


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------

def path_matches(pattern, changed_files):
    """Files matching one glob.

    fnmatch's '*' crosses '/', so a '**/'-prefixed pattern already covers every
    depth at or below one directory. The second test covers depth zero, so
    '**/Dockerfile*' also fires on a Dockerfile at the repository root.
    """
    bare = pattern[3:] if pattern.startswith("**/") else None
    hits = []
    for path in changed_files:
        if fnmatch.fnmatchcase(path, pattern):
            hits.append(path)
        elif bare is not None and fnmatch.fnmatchcase(path, bare):
            hits.append(path)
    return hits


def _is_negated(text, start, end):
    """True when the sentence holding this hit says the thing is absent.

    Rule 3 of the module docstring. The sentence is the span between sentence
    punctuation or line breaks; a negator anywhere in it, as a whole word,
    disqualifies the hit. Crude on purpose: the failure mode is a missed
    negation, which dispatches one extra reviewer, and never a suppressed real
    trigger, which would skip a gap.
    """
    left = max((m.end() for m in _SENTENCE_SPLIT.finditer(text, 0, start)), default=0)
    right_match = _SENTENCE_SPLIT.search(text, end)
    sentence = text[left:right_match.start() if right_match else len(text)]
    words = re.findall(r"[a-z/]+", sentence.lower())
    return any(n in words for n in NEGATORS)


def spec_matches(phrase, spec_text):
    """True when the phrase is genuinely a subject of this spec.

    All four rules from the module docstring apply: leading word boundary,
    front matter already stripped by strip_front_matter, negated sentences
    discarded, and at least MIN_SPEC_OCCURRENCES surviving hits.
    """
    pattern = re.compile(r"(?<!\w)" + re.escape(phrase), re.IGNORECASE)
    kept = 0
    for match in pattern.finditer(spec_text):
        if not _is_negated(spec_text, match.start(), match.end()):
            kept += 1
            if kept >= MIN_SPEC_OCCURRENCES:
                return True
    return False


def select(reviewers, changed_files, spec_text):
    """Every reviewer whose trigger the wave fires. No cap; see the module docstring."""
    selected, skipped, inert = [], [], []

    for entry in reviewers:
        if entry.get("inert"):
            inert.append(entry)
            continue

        path_hits = []
        for pattern in entry.get("paths", []):
            hits = path_matches(pattern, changed_files)
            if hits:
                path_hits.append({"pattern": pattern, "files": hits})

        spec_hits = [p for p in entry.get("spec", []) if spec_matches(p, spec_text)]

        if path_hits or spec_hits:
            selected.append({
                "role": entry["role"],
                "skill": entry["skill"],
                "display": entry["display"],
                "trigger": entry["trigger"],
                "source": entry["source"],
                "matched_paths": path_hits,
                "matched_spec": spec_hits,
            })
        else:
            skipped.append(entry)

    return selected, skipped, inert


# --------------------------------------------------------------------------
# Input
# --------------------------------------------------------------------------

def is_ignored(path):
    """True for bookkeeping the wave wrote about itself. See IGNORED_PATHS."""
    return any(path_matches(pattern, [path]) for pattern in IGNORED_PATHS)


def read_changed_files(spec):
    if spec == "-":
        text = sys.stdin.read()
    else:
        path = Path(spec)
        if not path.is_file():
            raise TableError(f"changed-file list not found: {path}")
        text = path.read_text(encoding="utf-8")
    all_paths = [line.strip() for line in text.splitlines() if line.strip()]
    kept = [p for p in all_paths if not is_ignored(p)]
    return kept, len(all_paths) - len(kept)


def strip_front_matter(text):
    """Drop a leading YAML front-matter block. See rule 2 in the docstring."""
    return _FRONT_MATTER.sub("", text)


def read_spec_text(paths):
    chunks = []
    for raw in paths:
        path = Path(raw)
        if not path.is_file():
            raise TableError(f"spec file not found: {path}")
        chunks.append(strip_front_matter(path.read_text(encoding="utf-8", errors="replace")))
    return "\n".join(chunks)


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

def render(selected, skipped, inert, wave, n_files, n_specs, n_ignored):
    label = f"Wave {wave}" if wave else "Selection"
    ignored = f", {n_ignored} bookkeeping path{'' if n_ignored == 1 else 's'} ignored" if n_ignored else ""
    lines = [
        f"{label}: {len(selected)} reviewer{'' if len(selected) == 1 else 's'} "
        f"({n_files} changed file{'' if n_files == 1 else 's'}, "
        f"{n_specs} spec file{'' if n_specs == 1 else 's'}{ignored})",
        "",
    ]

    if not selected:
        lines.append("  none. No trigger in the table fires on this wave.")
        lines.append("")
    for hit in selected:
        lines.append(f"{hit['role']}  ({hit['skill']}, {hit['display']})  [{hit['source']}]")
        for match in hit["matched_paths"]:
            shown = ", ".join(match["files"][:3])
            extra = len(match["files"]) - 3
            if extra > 0:
                shown += f" (+{extra} more)"
            lines.append(f"    path  {match['pattern']}  ->  {shown}")
        for phrase in hit["matched_spec"]:
            lines.append(f"    spec  \"{phrase}\"")
        lines.append("")

    if skipped:
        lines.append(f"Not selected ({len(skipped)}): " + ", ".join(e["role"] for e in skipped))
    if inert:
        lines.append(f"Inert, never selected ({len(inert)}): " + ", ".join(e["role"] for e in inert))
    return "\n".join(lines)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def cmd_select(args):
    reviewers = validate(load_table(Path(args.table)))
    changed_files, n_ignored = read_changed_files(args.changed_files)
    spec_text = read_spec_text(args.spec)
    selected, skipped, inert = select(reviewers, changed_files, spec_text)

    if args.json:
        print(json.dumps({
            "wave": args.wave,
            "changed_file_count": len(changed_files),
            "ignored_file_count": n_ignored,
            "spec_file_count": len(args.spec),
            "selected": selected,
            "not_selected": [e["role"] for e in skipped],
            "inert": [{"role": e["role"], "reason": e["inert"]} for e in inert],
        }, indent=2))
    else:
        print(render(selected, skipped, inert, args.wave,
                     len(changed_files), len(args.spec), n_ignored))
    return 0


def cmd_check(args):
    reviewers = validate(load_table(Path(args.table)))
    firing = [e for e in reviewers if not e.get("inert")]
    print(
        f"reviewer-triggers.yaml: {len(reviewers)} rows, "
        f"{len(firing)} can fire, {len(reviewers) - len(firing)} inert ... ok"
    )
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--table", default=str(DEFAULT_TABLE),
                        help="trigger table (default: beside this script)")
    sub = parser.add_subparsers(dest="command", required=True)

    sel = sub.add_parser("select", help="print the reviewers this wave's changes require")
    sel.add_argument("--changed-files", required=True,
                     help="file holding one changed path per line, or '-' for stdin")
    sel.add_argument("--spec", action="append", default=[],
                     help="spec file to match spec phrases against; repeatable")
    sel.add_argument("--wave", default="", help="wave id, for the output header")
    sel.add_argument("--json", action="store_true", help="machine-readable output")
    sel.set_defaults(func=cmd_select)

    chk = sub.add_parser("check", help="validate the trigger table")
    chk.set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except TableError as exc:
        print(f"select_reviewers: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
