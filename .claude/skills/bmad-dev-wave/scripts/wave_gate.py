#!/usr/bin/env python3
"""The hook half of the harness: the tool calls the wave rules deny.

Phase 4 of docs/harness-conversion-plan.md. Phases 1 to 3 each left the same
gap behind, and wrote it down three times: the verdict became a script's exit
code, but running the script and honouring its exit were still the agent's
choice, because the fork shipped PostToolUse and SessionEnd hooks and no
PreToolUse, so no tool call was ever denied. This is the one PreToolUse hook
the plan asked for, plus the SessionEnd half Phase 2's step 4.5 needed.

  wave_gate.py pre-tool-use  [--project-root P]   stdin: the PreToolUse JSON.
      Exit 0 allows the call. Exit 2 denies it; stderr names the rule and the
      remedy, and Claude Code feeds that back to the agent.
  wave_gate.py session-end   [--project-root P]   stdin: the SessionEnd JSON.
      Blocks every wave paused at step 4.5 with its question unanswered.
      Exit 0: SessionEnd cannot block, so this one only records.

Five rules, each read off disk and none of them a judgement:

  closure   Nothing touches _bmad-output/epic-closure/epic-<N>/ unless
            check_review_records.py --epic N exits 0. Phase 1's gate, run by
            the hook at the moment the closure artifact would be written,
            rather than by the closing agent at a step it may skip.
  verdict   docs/wave-<id>/evaluation-<n>.md is written by evaluate_wave.py
            record and by nothing else. A verdict typed by the agent whose
            work it grades is not a verdict.
  lifecycle .bmad/wave-<id>/wave.md is written by wave_status.py and by
            nothing else. A status edited by hand skips every refusal the
            script makes, and blocked is sticky only if the session it blocks
            cannot edit, move or delete the record.
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

It fails closed (R1 of docs/reviews/harness-engineering-review-v1.md). Claude
Code lets a PreToolUse call through on any exit but 2, so an error in here, an
event it cannot read, and a run past DEADLINE all exit 2 with the reason: a
gate that cannot decide denies.

Where it looks. The project root is the checkout holding .bmad/, found from
the session's cwd through git's common directory, so a session rooted in a
worktree reads the same .bmad/ as one rooted in the main checkout. A wave's
evaluation records are read from its own worktree when it has them, since
that is where step 7 writes them.

How it reads Bash, and Monitor, which runs commands under the Bash rules: as
the shell would, not as a substring. Here-document bodies are split off,
comments dropped, words split and unquoted with shlex, leading VAR=value
assignments and wrappers (env, timeout, nohup ...) stripped, git's -C and
other global options read, `cd` followed, and $(...), backticks, `bash -c`
and `eval` parsed as commands of their own. What it still cannot read, such
as Python in `python3 -c` or a variable holding a command, it does not guess
at: a wave_status.py set it cannot read literally is refused, and so is a
guarded path named where it cannot tell whether it is written. A script file
written earlier and run later is not opened; that is the gap left.

Stdlib only. Imports wave_status.py and evaluate_wave.py from its own
directory, so the vocabulary, the record paths and the verdict parser stay
defined once.
"""

import argparse
import glob
import json
import os
import re
import shlex
import signal
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
SHELL_TOOLS = ("Bash", "Monitor")

# Seconds. A run past this denies. The hook's registered timeout sits above it,
# because a PreToolUse hook that Claude Code times out lets the call through.
DEADLINE = 20
GIT_TIMEOUT = 10

# Case-insensitive throughout: APFS is, and so is the record reader
# (evaluate_wave.EVALUATION_FILE), so a rule that minded case would guard one
# spelling of a file the reader finds under any.
CLOSURE_PATH = re.compile(r"_bmad-output/epic-closure/epic-(\d+)(?=/|$|\s|['\"])", re.I)
EVALUATION_FILE = re.compile(r"(?:^|/)docs/wave-[^/]+/evaluation-\d+\.md$", re.I)
EVALUATION_NAMED = re.compile(r"docs/wave-[^/\s'\"]+/evaluation-\d+\.md", re.I)
LIFECYCLE_FILE = re.compile(r"(?:^|/)\.bmad/wave-[^/]+/wave\.md$", re.I)
LIFECYCLE_NAMED = re.compile(r"\.bmad/wave-[^/\s'\"]+/wave\.md", re.I)
# .bmad/ itself, or one wave's directory: removing either removes the record.
LIFECYCLE_DIR = re.compile(r"(?:^|/)\.bmad(?:/wave-[^/]+)?$", re.I)

WAVE_STATUS_NAMED = re.compile(r"wave_status", re.I)
# The verb as a word, or the function behind it.
SET_WORD = re.compile(r"(?<![\w-])set(?:_status)?(?![\w-])")

PENDING_MARKER = "step-4.5.pending"
SESSION_FILE = "evaluation-session"


class Deny(Exception):
    def __init__(self, rule, lines):
        super().__init__(rule)
        self.rule = rule
        self.lines = lines


# --------------------------------------------------------------- the parser
#
# Enough of the shell's grammar to say what a command runs and what it writes,
# and no more. Where the grammar runs out the rules fail closed, so the parser
# may be conservative but must never be optimistic.

OPERATORS = sorted(["&&", "||", ";;", "|&", ">>", "<<<", "<<", "&>>", "&>", ">|", ">&",
                    "<&", "<>", "\n", ";", "&", "|", "(", ")", "<", ">", "`"],
                   key=len, reverse=True)
OP = "\x00"  # marks an operator found outside quotes, so a quoted `;` stays a word
OUTPUT_REDIRECTS = {">", ">>", ">|", "&>", "&>>", "<>", ">&"}
REDIRECTS = OUTPUT_REDIRECTS | {"<", "<&", "<<", "<<<"}
ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.S)
VARIABLE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")
PYTHON = re.compile(r"^python[0-9.]*$")
SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
INTERPRETERS = {"perl", "ruby", "node", "php", "osascript"}
# Anything that runs text it is handed as a program.
EXECUTORS = SHELLS | INTERPRETERS | {"eval", "source", ".", "xargs", "parallel"}
WRAPPERS = {"env", "command", "builtin", "exec", "nohup", "nice", "time", "timeout",
            "sudo", "doas", "stdbuf", "caffeinate"}
# Reserved words that can open a simple command: `then rm x` runs rm.
KEYWORDS = {"!", "{", "}", "if", "then", "elif", "else", "fi", "do", "done", "while",
            "until"}
WRAPPER_VALUE_OPTS = {"-u", "-n", "-s", "-k", "-g", "-p", "-C", "-D", "-S"}
UV_VALUE_OPTS = {"--with", "--project", "--python", "-p", "--directory", "--env-file",
                 "--extra", "--group", "--package", "--index", "--from"}
PRINTS = {"echo", "printf", "cat", "grep", "egrep", "fgrep", "rg", "ag", "ack"}
# Commands whose every operand is a path they write, move away or delete.
WRITES_ALL = {"tee", "rm", "unlink", "rmdir", "shred", "truncate", "touch", "mkdir", "mv",
              "ed", "ex"}
# Commands whose last operand is the path they write.
WRITES_LAST = {"cp", "install", "ln", "rsync", "scp", "ditto"}
REMOVERS = {"rm", "rmdir", "unlink", "shred", "mv"}
GIT_WRITES = {"add", "am", "apply", "checkout", "cherry-pick", "clean", "commit", "merge",
              "mv", "pull", "rebase", "reset", "restore", "revert", "rm", "stash", "switch"}
GIT_PATH_WRITES = {"checkout", "restore", "rm", "mv"}
NESTING = 4


def _prepass(text):
    """One quote-aware pass over a command, the way the shell reads it.

    Returns the text with every operator outside quotes marked by OP, comments
    and line continuations gone, plus the here-document bodies in operator
    order. Without the marks, shlex would hand back a quoted `;` and a real one
    as the same string.
    """
    out, bodies, pending = [], [], []
    i, n, quote = 0, len(text), None
    while i < n:
        c = text[i]
        if quote == "'":
            out.append(c)
            quote = None if c == "'" else quote
            i += 1
        elif c == "\\" and i + 1 < n:
            if text[i + 1] != "\n":
                out.append(text[i:i + 2])
            i += 2
        elif quote == '"':
            out.append(c)
            quote = None if c == '"' else quote
            i += 1
        elif c in "'\"":
            quote = c
            out.append(c)
            i += 1
        elif c == "#" and (not out or out[-1][-1] in " \t"):
            while i < n and text[i] != "\n":
                i += 1
        elif c in ";&|()<>`\n":
            op = next(o for o in OPERATORS if text.startswith(o, i))
            i += len(op)
            out.append(f" {OP}{op}{OP} ")
            if op == "<<":
                strip = text.startswith("-", i)
                i += strip
                while i < n and text[i] in " \t":
                    i += 1
                j = i
                while j < n and text[j] not in " \t\n;&|()<>":
                    j += 1
                out.append(text[i:j] + " ")
                pending.append((re.sub(r"['\"\\]", "", text[i:j]), strip))
                i = j
            elif op == "\n" and pending:
                i = _read_bodies(text, i, pending, bodies)
                pending = []
        else:
            out.append(c)
            i += 1
    return "".join(out), bodies


def _read_bodies(text, i, pending, bodies):
    n = len(text)
    for delim, strip in pending:
        lines = []
        while i < n:
            j = text.find("\n", i)
            line = text[i:] if j < 0 else text[i:j]
            i = n if j < 0 else j + 1
            if (line.lstrip("\t") if strip else line) == delim:
                break
            lines.append(line)
        bodies.append("\n".join(lines))
    return i


def _operator(word):
    if len(word) > 2 and word[0] == OP and word[-1] == OP:
        return word[1:-1]
    return None


def _base(word):
    return word.rsplit("/", 1)[-1].lower()


def _expand(word, env):
    return VARIABLE.sub(lambda m: env.get(m.group(1) or m.group(2), m.group(0)), word)


def _paths(token, cwd):
    """The absolute paths a word names from `cwd`, globs expanded as the shell would."""
    p = os.path.expanduser(token)
    p = p if os.path.isabs(p) else os.path.join(cwd, p)
    found = glob.glob(p) if any(ch in p for ch in "*?[") else []
    return [os.path.realpath(q) for q in (found or [p])]


def _inside(path, directory):
    return path == directory or path.startswith(directory.rstrip(os.sep) + os.sep)


def _substitutions(word):
    """(the command text inside each $(...) and `...` of a word, the word
    without them). The inside is parsed as commands of its own."""
    found, rest, i = [], [], 0
    while True:
        j = word.find("$(", i)
        if j < 0:
            break
        depth, k = 1, j + 2
        while k < len(word) and depth:
            depth += {"(": 1, ")": -1}.get(word[k], 0)
            k += 1
        found.append(word[j + 2:k - 1] if depth == 0 else word[j + 2:])
        rest.append(word[i:j])
        i = k
    parts = "".join(rest + [word[i:]]).split("`")
    return found + parts[1::2], "".join(parts[0::2])


def _unwrap(words):
    """argv with wrappers stripped: `env X=1 timeout 30 python3 ...` is `python3 ...`."""
    argv = list(words)
    while argv:
        name = _base(argv[0])
        if argv[0] in KEYWORDS:
            argv = argv[1:]
            continue
        if name == "uv" and argv[1:2] == ["run"]:
            argv = argv[2:]
            while argv and argv[0].startswith("-"):
                opt = argv.pop(0)
                if opt in UV_VALUE_OPTS and argv:
                    argv.pop(0)
            continue
        if name not in WRAPPERS:
            break
        argv = argv[1:]
        while argv and (argv[0].startswith("-") or ASSIGNMENT.match(argv[0])):
            if argv.pop(0) in WRAPPER_VALUE_OPTS and argv:
                argv.pop(0)
        if name == "timeout" and argv:
            argv = argv[1:]  # the duration
    return argv


class Simple:
    """One simple command: what it runs, from where, fed by what."""

    def __init__(self, cwd):
        self.cwd = cwd
        self.words = []       # as written, assignments excluded
        self.assigns = []     # values of leading NAME=value words
        self.redirects = []   # (operator, target)
        self.stdin = None     # here-document or here-string text
        self.piped_to = None  # the command its stdout feeds
        self.nested = set()   # indexes of words parsed as commands of their own
        self.stdin_nested = False
        self.argv = []

    @property
    def name(self):
        return _base(self.argv[0]) if self.argv else ""


class Shell:
    """A Bash or Monitor command, parsed. `error` is set when it cannot be."""

    def __init__(self, command, cwd):
        self.raw = command
        self.cmds, self.stray, self.error = [], [], None
        self.env = {}  # NAME=value words seen anywhere in the command
        try:
            self.cmds, stray = self._parse(command, cwd, self.env, 0)
            self.stray += stray
        except ValueError as e:
            self.error = str(e)

    def names(self, pattern):
        """Does `pattern` appear in the command as written, or in any word once
        unquoted and its variables expanded? `wave_st''atus.py` is the file."""
        if pattern.search(self.raw):
            return True
        texts = list(self.stray)
        for sc in self.cmds:
            texts += sc.words + sc.assigns + [t for _, t in sc.redirects]
            texts += [sc.stdin] if sc.stdin is not None else []
        return any(pattern.search(_expand(t, self.env)) for t in texts)

    def _parse(self, command, cwd, env, depth):
        if depth > NESTING:
            raise ValueError("nested too deep to read")
        marked, bodies = _prepass(command)
        lx = shlex.shlex(marked, posix=True)
        lx.whitespace_split = True
        lx.commenters = ""
        words = list(lx)
        cmds, stray, body, pipe_from = [], [], 0, None
        cur = Simple(cwd)

        def close(sc, piped):
            nonlocal pipe_from
            if not (sc.words or sc.assigns or sc.redirects or sc.stdin is not None):
                return
            if pipe_from is not None:
                pipe_from.piped_to = sc
            cmds.append(sc)
            pipe_from = sc if piped else None

        k = 0
        while k < len(words):
            w = words[k]
            op = _operator(w)
            nxt = _operator(words[k + 1]) if k + 1 < len(words) else None
            if op in REDIRECTS:
                target = words[k + 1] if k + 1 < len(words) else ""
                k += 2
                if op == "<<":
                    if body < len(bodies):
                        cur.stdin = bodies[body]
                        body += 1
                elif op == "<<<":
                    cur.stdin = target
                else:
                    cur.redirects.append((op, target))
                continue
            if op is not None:
                close(cur, op in ("|", "|&"))
                cur = Simple(cwd)
            elif w.isdigit() and nxt in REDIRECTS:
                pass  # a file descriptor number: 2>&1
            elif not cur.words and ASSIGNMENT.match(w):
                name, value = ASSIGNMENT.match(w).groups()
                env[name] = _expand(value, env)
                cur.assigns.append(value)
            else:
                cur.words.append(w)
            k += 1
        close(cur, False)
        stray += bodies[body:]

        out = []
        for sc in cmds:
            sc.cwd = cwd
            sc.argv = _unwrap(sc.words)
            out.append(sc)
            out += self._nested(sc, env, depth)
            if sc.name in ("cd", "pushd") and len(sc.argv) > 1:
                target = _expand(sc.argv[1], env)
                if "$" not in target and target != "-":
                    cwd = _paths(target, cwd)[0]
            elif sc.name in ("cd", "pushd"):
                cwd = os.path.expanduser("~")
        return out, stray

    def _nested(self, sc, env, depth):
        """Commands `sc` runs that its own words do not show: substitutions,
        `bash -c`, `eval`, here-documents fed to a shell, xargs, find -exec."""
        found = []

        def run(text):
            cmds, stray = self._parse(text, sc.cwd, env, depth + 1)
            found.extend(cmds)
            self.stray.extend(stray)

        for word in sc.words + sc.assigns + [t for _, t in sc.redirects]:
            for text in _substitutions(word)[0]:
                run(text)
        argv, name = sc.argv, sc.name
        start = len(sc.words) - len(argv)
        args = argv[1:]
        if name in SHELLS:
            for j, a in enumerate(args):
                if a.startswith("-") and not a.startswith("--") and "c" in a[1:]:
                    if j + 1 < len(args):
                        sc.nested.add(start + 2 + j)
                        run(_expand(args[j + 1], env))
                    break
                if not a.startswith("-"):
                    break  # a script file: not opened
            else:
                if sc.stdin is not None:
                    sc.stdin_nested = True
                    run(sc.stdin)
        elif name == "eval":
            sc.nested.update(range(start + 1, len(sc.words)))
            run(_expand(" ".join(args), env))
        elif name == "xargs":
            j = 0
            while j < len(args) and args[j].startswith("-"):
                j += 2 if args[j] in ("-n", "-I", "-L", "-P", "-d", "-s", "-E") else 1
            sc.nested.update(range(start + 1, len(sc.words)))
            if args[j:]:
                run(shlex.join(args[j:]))
        elif name == "find":
            for j, a in enumerate(args):
                if a in ("-exec", "-execdir", "-ok", "-okdir"):
                    end = next((e for e in range(j + 1, len(args)) if args[e] in (";", "+")),
                               len(args))
                    sc.nested.update(range(start + 2 + j, start + 1 + end))
                    run(shlex.join(args[j + 1:end]))
        return found

    # ---- what the command does

    def code(self, sc):
        """Program text `sc` hands an interpreter this parser cannot read."""
        if not (PYTHON.match(sc.name) or sc.name in INTERPRETERS):
            return []
        texts, script, args, j = [], None, sc.argv[1:], 0
        while j < len(args):
            a = args[j]
            if a in ("-c", "-e", "-E", "--eval", "-r") and j + 1 < len(args):
                texts.append(args[j + 1])
                j += 2
                continue
            if a == "-" or not a.startswith("-"):
                script = a
                break
            j += 1
        if script in (None, "-") and not texts and sc.stdin is not None:
            texts.append(sc.stdin)
        return texts

    def write_paths(self, sc):
        """Every path `sc` writes, truncates, moves away or deletes."""
        env = self.env
        tokens = [t for op, t in sc.redirects
                  if op in OUTPUT_REDIRECTS
                  and not (t in ("/dev/null", "/dev/stdout", "/dev/stderr")
                           or (op == ">&" and (t.isdigit() or t == "-")))]
        name, args = sc.name, sc.argv[1:]
        operands = [a for a in args if not a.startswith("-")]
        if name in WRITES_ALL:
            tokens += operands
        elif name in WRITES_LAST:
            tokens += operands[-1:]
        elif name in ("sed", "gsed", "perl") and any(
                a.startswith("--in-place") or (a.startswith("-") and not a.startswith("--")
                                               and "i" in a[1:]) for a in args):
            tokens += operands
        elif name == "dd":
            tokens += [a[3:] for a in args if a.startswith("of=")]
        elif name in ("curl", "wget"):
            for j, a in enumerate(args[:-1]):
                if a in ("-o", "--output", "-O", "--output-document"):
                    tokens.append(args[j + 1])
            tokens += [a.split("=", 1)[1] for a in args
                       if a.startswith(("--output=", "--output-document="))]
        paths = [p for t in tokens for p in _paths(_expand(t, env), sc.cwd)]
        git = self.git(sc)
        if git and git[0] in GIT_PATH_WRITES:
            paths += [p for t in git[2] for p in _paths(t, git[1])]
        return paths

    def git(self, sc):
        """(subcommand, directory, operands) of a git command, globals read."""
        if sc.name != "git":
            return None
        argv, d, j = sc.argv, sc.cwd, 1
        while j < len(argv):
            a = argv[j]
            if a in ("-C", "--work-tree") and j + 1 < len(argv):
                d = _paths(argv[j + 1], d)[0]
                j += 2
            elif a.startswith("--work-tree="):
                d = _paths(a.split("=", 1)[1], d)[0]
                j += 1
            elif a in ("-c", "--git-dir", "--namespace", "--config-env") and j + 1 < len(argv):
                j += 2
            elif a.startswith("-"):
                j += 1
            else:
                return a, d, [x for x in argv[j + 1:] if not x.startswith("-")]
        return None

    def writes(self, file_re, named_re, removed_re=None):
        """Does the command write a path `file_re` matches, or name one
        (`named_re`) somewhere the parse cannot tell whether it is written?"""
        if self.error is not None:
            return bool(named_re.search(self.raw))
        for sc in self.cmds:
            for p in self.write_paths(sc):
                if file_re.search(p):
                    return True
                if removed_re is not None and sc.name in REMOVERS and removed_re.search(p):
                    return True
            if any(named_re.search(t) for t in self.code(sc)):
                return True
        return any(named_re.search(t) for t in self.stray)

    def writes_into(self, directory):
        if self.error is not None:
            return directory in self.raw
        for sc in self.cmds:
            if any(_inside(p, directory) for p in self.write_paths(sc)):
                return True
            git = self.git(sc)
            if git and git[0] in GIT_WRITES and _inside(git[1], directory):
                return True
            if sc.name == "patch" and _inside(sc.cwd, directory):
                return True
            texts = self.code(sc)
            if texts and (_inside(sc.cwd, directory) or any(directory in t for t in texts)):
                return True
        return False

    def prints_only(self, sc):
        """echo, printf or a search, into nothing that runs or keeps its output."""
        if sc.name not in PRINTS:
            return False
        for op, t in sc.redirects:
            if op in OUTPUT_REDIRECTS and t not in ("/dev/null", "/dev/stderr", "/dev/stdout") \
                    and not (op == ">&" and t.isdigit()):
                return False
        nxt = sc.piped_to
        while nxt is not None:
            if nxt.name in EXECUTORS or PYTHON.match(nxt.name):
                return False
            nxt = nxt.piped_to
        return True

    def call(self, sc, stem):
        """(verb, options) when `sc` runs <stem>.py so the parse can name it:
        `python3 path/<stem>.py ...`, `path/<stem>.py ...` or `python3 -m <stem>`.
        Options read the way argparse reads these scripts' own: `--name value`
        or `--name=value`, the last one winning; the verb is the first bare
        word."""
        argv, target = sc.argv, stem + ".py"
        if not argv:
            return None
        if _base(argv[0]) == target:
            rest = argv[1:]
        elif PYTHON.match(sc.name):
            rest, j = None, 1
            while j < len(argv):
                a = argv[j]
                if a == "-m" and j + 1 < len(argv):
                    if argv[j + 1].rsplit(".", 1)[-1].lower() != stem:
                        return None
                    rest = argv[j + 2:]
                    break
                if a in ("-c", "-") or not a.startswith("-"):
                    if _base(a) != target:
                        return None
                    rest = argv[j + 1:]
                    break
                j += 2 if a in ("-W", "-X") else 1
            if rest is None:
                return None
        else:
            return None
        verb, opts, j = None, {}, 0
        while j < len(rest):
            a = rest[j]
            if a.startswith("--") and len(a) > 2:
                key, eq, value = a.partition("=")
                if not eq and j + 1 < len(rest) and not rest[j + 1].startswith("--"):
                    value = rest[j + 1]
                    j += 1
                opts[key] = value
            elif verb is None:
                verb = a
            j += 1
        return verb, opts

    def unaccounted(self, stem):
        """Text the parse cannot account for as a direct call of <stem>.py or as
        output that only prints: where a hidden call would have to be."""
        texts = list(self.stray)
        for sc in self.cmds:
            texts += sc.assigns
            if self.call(sc, stem) is not None or self.prints_only(sc):
                continue
            if sc.argv[:1] == ["set"]:
                continue  # the shell's own set builtin
            # A substitution's inside was parsed as commands of its own and is
            # accounted for there; `git commit -m "$(cat <<'EOF' ...)"` is fine.
            texts += [_substitutions(w)[1] for j, w in enumerate(sc.words) if j not in sc.nested]
            texts += [t for _, t in sc.redirects]
            if sc.stdin is not None and not sc.stdin_nested:
                texts.append(sc.stdin)
        return texts


# ------------------------------------------------------------------ helpers

def run_git(start, *args):
    try:
        p = subprocess.run(["git", "-C", str(start), *args], capture_output=True, text=True,
                           timeout=GIT_TIMEOUT)
    except OSError:
        return None
    return p.stdout if p.returncode == 0 else None


def main_checkout(start):
    """The main working tree of the repository `start` is in, or None."""
    out = run_git(start, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not out:
        return None
    common = Path(out.strip())
    return common.parent if common.name == ".git" else None


def project_root(candidates):
    """The checkout holding .bmad/, found from where the session is.

    dev-wave keeps .bmad/ in the main checkout and builds in a worktree, so
    the hook's own location and the session's cwd are both the wrong answer
    half the time. git's common directory names the main checkout from any
    worktree of it.
    """
    starts = [Path(c) for c in candidates if c and Path(c).is_dir()]
    for s in starts:
        main = main_checkout(s)
        for d in ([main] if main else []) + [s, *s.parents]:
            if (d / ".bmad").is_dir():
                return Path(os.path.realpath(d))
    for s in starts:
        return Path(os.path.realpath(main_checkout(s) or s))
    return Path(os.path.realpath(os.getcwd()))


def wave_worktree(root, label):
    """The checkout whose branch is this wave's, from `git worktree list`.

    Real branch names carry tool prefixes and hashes
    (claude/wave-5d-categories-exposure-ddd660), so the match is the wave
    label as a path segment prefix, case-insensitively. The main checkout is
    an entry too, so a wave built on the main checkout resolves to the root.
    """
    out = run_git(root, "worktree", "list", "--porcelain")
    if out is None:
        return None
    needle = re.compile(rf"(?:^|/)wave-{re.escape(label.lower())}(?:-|$)")
    path = None
    for line in out.splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):]
        elif line.startswith("branch ") and path and needle.search(line[len("branch "):].lower()):
            return Path(os.path.realpath(path))
    return None


def latest_verdict(root, label):
    """(verdict, path) of the newest evaluation record, or (None, None).

    Step 7 records in the wave's worktree, so that is read first; the root is
    where the records sit once the wave has merged.
    """
    wt = wave_worktree(root, label)
    for base in ([wt] if wt and wt != root else []) + [root]:
        priors = evaluate_wave.prior_evaluations(base, label)
        if priors:
            latest = priors[-1]
            return evaluate_wave.read_verdict(latest.read_text(encoding="utf-8", errors="ignore")), latest
    return None, None


def shown(path, root):
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def session_file(root, label):
    return wave_status.wave_dir(root, label) / SESSION_FILE


# -------------------------------------------------------------------- rules

def closure_rule(root, text):
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


def verdict_rule(target, shell):
    why = ["  Only `evaluate_wave.py record` writes those, from the evaluator's own",
           "  output. A verdict written by the agent whose work it grades is not one."]
    if target is not None and EVALUATION_FILE.search(target):
        raise Deny("verdict", [f"{target} is an evaluation record."] + why)
    if shell is not None and shell.writes(EVALUATION_FILE, EVALUATION_NAMED):
        raise Deny("verdict", [
            "This command writes into a docs/wave-<id>/evaluation-<n>.md record, or names",
            "  one where the gate cannot tell whether it is written."] + why)


def lifecycle_rule(target, shell):
    why = ["  Only wave_status.py writes it: change a status with `wave_status.py set`.",
           "  A blocked wave is cleared by a human, editing or deleting the record",
           "  outside this session; the session it blocks may not."]
    if target is not None and LIFECYCLE_FILE.search(target):
        raise Deny("lifecycle", [f"{target} is a wave's lifecycle record."] + why)
    if shell is not None and shell.writes(LIFECYCLE_FILE, LIFECYCLE_NAMED, LIFECYCLE_DIR):
        raise Deny("lifecycle", [
            "This command writes, moves or deletes a .bmad/wave-<id>/wave.md record, or",
            "  names one where the gate cannot tell whether it is written."] + why)


def review_rule(root, shell):
    if shell is None or not shell.names(WAVE_STATUS_NAMED):
        return
    direct = [
        "  Call it directly, with literal values:",
        "    python3 <skill-root>/scripts/wave_status.py set --project-root <root> \\",
        "        --wave <id> --status <status>"]
    if shell.error is not None:
        if SET_WORD.search(shell.raw):
            raise Deny("review", [
                f"this command names wave_status.py but cannot be parsed ({shell.error}),",
                "  so a set inside it cannot be read."] + direct)
        return
    if any(SET_WORD.search(t) for t in shell.unaccounted("wave_status")):
        raise Deny("review", [
            "this command reaches wave_status.py set through a shape the gate cannot read",
            "  (a variable, eval, python3 -c, a here-document, a pipe into a shell), so",
            "  it is refused rather than guessed at."] + direct)
    for sc in shell.cmds:
        call = shell.call(sc, "wave_status")
        if call is None:
            continue
        verb, opts = call
        status, wave = opts.get("--status"), opts.get("--wave")
        if any(v and ("$" in v or "`" in v) for v in (verb, status, wave)):
            raise Deny("review", [
                "wave_status.py's verb, --status and --wave must be literal values; this",
                "  command builds one from a variable or a substitution."] + direct)
        if verb != "set" or status != wave_status.IN_REVIEW or not wave:
            continue
        labels = wave_status.wave_map_labels(root)
        label = wave_status.resolve_label(labels, wave) if labels else None
        if label is None:
            continue  # wave_status.py refuses this itself, exit 2
        verdict, path = latest_verdict(root, label)
        if verdict == evaluate_wave.PASS:
            continue
        if path is None:
            raise Deny("review", [
                f"wave {label} has no evaluation on disk, so it cannot enter review.",
                "  Step 7 dispatches the fresh-context evaluator and records its verdict",
                "  with `evaluate_wave.py record`; the review stage opens on PASS and on",
                "  nothing else. Reviewing the wave in this context is not a substitute."])
        raise Deny("review", [
            f"wave {label}'s latest evaluation ({shown(path, root)}) is "
            f"{verdict or 'unreadable'}, not PASS, so it cannot enter review.",
            "  NEEDS_WORK: halt; the findings open the next session (bmad-resume-wave).",
            "  UPSTREAM_CAUSE: fix the artifact the record names, not the code.",
            "  Unreadable: repair or delete the record; do not guess what it said."])


def note_recording_session(root, shell, session_id):
    """Bookkeeping, not a denial: remember which session is recording a verdict."""
    if shell is None or shell.error is not None or not session_id:
        return
    for sc in shell.cmds:
        call = shell.call(sc, "evaluate_wave")
        if call is None or call[0] != "record" or not call[1].get("--wave"):
            continue
        labels = wave_status.wave_map_labels(root)
        label = wave_status.resolve_label(labels, call[1]["--wave"]) if labels else None
        if label is None:
            continue
        path = session_file(root, label)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(session_id + "\n", encoding="utf-8")


def in_place_rule(root, tool, target, shell, session_id):
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
        why = [
            f"this session recorded NEEDS_WORK for wave {label} ({shown(path, root)}) and may not",
            "  edit that wave's worktree afterwards. The context that built the wave",
            "  is the context least able to judge whether a fix answered a finding.",
            f"  Halt. The findings open the next session: /bmad-resume-wave {label}."]
        if target is not None and _inside(target, str(wt)):
            raise Deny("in-place", [f"{tool} to {target}:"] + why)
        if shell is not None and shell.writes_into(str(wt)):
            raise Deny("in-place", ["this command writes into the wave's worktree:"] + why)


# ------------------------------------------------------------------- events

def pre_tool_use(root, cwd, event):
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    session_id = event.get("session_id", "")
    target = shell = None
    if tool in FILE_TOOLS:
        # NotebookEdit names its file notebook_path; every other file tool file_path.
        raw = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        target = os.path.realpath(os.path.join(cwd, os.path.expanduser(raw))) if raw else None
        text = target
    elif tool in SHELL_TOOLS:
        text = tool_input.get("command") or ""
        shell = Shell(text, str(cwd))
    else:
        return 0
    try:
        closure_rule(root, text)
        verdict_rule(target, shell)
        lifecycle_rule(target, shell)
        review_rule(root, shell)
        in_place_rule(root, tool, target, shell, session_id)
        note_recording_session(root, shell, session_id)
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


def _deadline(signum, frame):
    raise TimeoutError(f"the gate ran past its {DEADLINE}s deadline")


def main():
    ap = argparse.ArgumentParser(description="PreToolUse and SessionEnd hook for the wave rules.")
    ap.add_argument("event", choices=["pre-tool-use", "session-end"])
    ap.add_argument("--project-root", default=None,
                    help="where to look for .bmad/ (default: the event's cwd, then "
                         "$CLAUDE_PROJECT_DIR)")
    args = ap.parse_args()
    try:
        if args.event == "pre-tool-use" and hasattr(signal, "SIGALRM"):
            signal.signal(signal.SIGALRM, _deadline)
            signal.alarm(DEADLINE)
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            raise ValueError("the hook event is not a JSON object")
        cwd = Path(os.path.realpath(event.get("cwd") or args.project_root or os.getcwd()))
        root = project_root([args.project_root] if args.project_root else
                            [event.get("cwd"), os.environ.get("CLAUDE_PROJECT_DIR"), os.getcwd()])
        code = pre_tool_use(root, cwd, event) if args.event == "pre-tool-use" else session_end(root, event)
    except Exception as e:  # noqa: BLE001 -- any failure is a denial, never a pass
        sys.stderr.write(
            f"wave-gate FAILED CLOSED ({type(e).__name__}: {e}): the wave rules could not be\n"
            "  checked, so this call is denied. A human must repair the gate outside this\n"
            f"  session: `python3 {Path(__file__).resolve()} --help` shows an import or syntax\n"
            "  error, and ./install.sh --validate-only --skip-mcp-check --target-project\n"
            "  <this project>, run from the Keelswell fork, names a missing file.\n")
        sys.exit(2)
    sys.exit(code)


if __name__ == "__main__":
    main()
