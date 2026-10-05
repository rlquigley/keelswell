#!/usr/bin/env python3
"""Apply the Keelswell theme removal (fork PRs 34 to 39) to one instance.

Run from the fork root on main:
    python3 tools/theme_removal_instance_step.py <instance-dir> [--check]

Four surfaces: the skill files that changed since BASE, in every Keelswell
skill tree the instance has; name and description lines of the [agents.*]
tables in _bmad/config.toml; name pins in _bmad/custom/config.toml (renamed
where present, added where the instance has none); and the Keelswell rows of
_bmad/_config/bmad-help.csv and _bmad/keelswell/module-help.csv, spliced as
text. Edits in place, never stages or commits. Aborts before writing anything
if an instance file is not what the fork shipped at BASE. --check writes
nothing. Needs PyYAML, as install.sh does. See the runbook section "Instances:
the theme removal is a hand step".
"""
import csv, io, pathlib, re, subprocess, sys, tomllib, yaml

BASE = "0493ff6"                      # fork main before the rename
CODES = dict(zip(
    "agent-sre agent-growth agent-accessibility agent-analytics agent-legal agent-ml agent-billing "
    "agent-appsec agent-performance agent-bizops agent-llm agent-mobile agent-marketing "
    "agent-web-designer agent-design-critic".split(),
    "ARE AGR ACI ALY ALE AME ABI ASE APR ABZ AEL AMO AMA AWE ACR".split()))
fork = pathlib.Path.cwd()
inst = pathlib.Path(sys.argv[1]).expanduser().resolve()
check = "--check" in sys.argv

def git(*a):
    r = subprocess.run(["git", *a], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout
def die(msg): sys.exit("ABORT, nothing written: " + msg)

assert (fork / "install.sh").is_file() and (fork / "module.yaml").is_file(), "run from the fork root"
writes, changed = {}, []          # path -> new text ; instance-relative paths

# ---- surface 1: skill files
files = [f[len("skills/"):] for f in git("diff", "--name-only", BASE, "HEAD", "--", "skills").split()]
trees = [t for t in (".claude/skills", ".agents/skills") if (inst / t / "bmad-dev-wave").is_dir()]
for t in trees:
    for f in files:
        p = inst / t / f
        if not p.is_file(): die(f"{t}/{f} is missing in the instance")
        if p.read_text(encoding="utf-8") != git("show", f"{BASE}:skills/{f}"):
            die(f"{t}/{f} differs from the fork at {BASE} (local drift)")
        writes[p] = (fork / "skills" / f).read_text(encoding="utf-8")

# ---- names and descriptions, old and new
rows = yaml.safe_load((fork / "skills/bmad-dev-wave/scripts/reviewer-triggers.yaml").read_text())
rows = rows["reviewers"] if isinstance(rows, dict) and "reviewers" in rows else rows
def walk(o):
    if isinstance(o, dict):
        if "skill" in o and "display" in o: yield o
        for v in o.values(): yield from walk(v)
    elif isinstance(o, list):
        for v in o: yield from walk(v)
new_name = {r["skill"]: r["display"] for r in walk(rows)}
assert len(new_name) == 38, len(new_name)
old_names = {a["role"]: a["display_name"] for a in yaml.safe_load(git("show", f"{BASE}:config/agent-names.yaml"))["agents"]}
new_names = {a["role"]: a["display_name"] for a in yaml.safe_load((fork / "config/agent-names.yaml").read_text())["agents"]}
rename = {old_names[r]: new_names[r] for r in old_names}
old_mod = {a["code"]: a for a in yaml.safe_load(git("show", f"{BASE}:module.yaml"))["agents"]}
new_mod = {a["code"]: a for a in yaml.safe_load((fork / "module.yaml").read_text())["agents"]}
def desc(skill):
    d = re.search(r"^description: (.*)$", (fork / "skills" / skill / "SKILL.md").read_text(), re.M).group(1).strip()
    return d[1:-1] if d[:1] == d[-1:] == '"' else d

# ---- surface 2: [agents.*] tables in _bmad/config.toml
p = inst / "_bmad/config.toml"; text = p.read_text(encoding="utf-8"); out = []; cur = None; n = 0; skipped = []
for line in text.split("\n"):
    m = re.match(r"\[agents\.([^\]]+)\]", line)
    if m: cur = m.group(1)
    elif line.startswith("["): cur = None
    if cur in new_mod:
        for key in ("name", "description"):
            if line.startswith(f"{key} = "):
                old, new = old_mod[cur][key], new_mod[cur][key]
                assert '"' not in new and "\\" not in new
                if line != f'{key} = "{old}"':
                    if cur not in skipped: skipped.append(cur)
                elif old != new:
                    line = f'{key} = "{new}"'; n += 1
    out.append(line)
if skipped != [] and skipped != ["bmad-agent-tech-writer"]:
    die(f"_bmad/config.toml tables not as the fork shipped them: {skipped}")
new_text = "\n".join(out); tomllib.loads(new_text); writes[p] = new_text
print(f"_bmad/config.toml: {n} lines (name or description) in {len(new_mod) - len(skipped)} tables"
      + (f"; left alone: {skipped} (declared by an upstream module in this instance)" if skipped else ""))

# ---- surface 2b: name pins in _bmad/custom/config.toml, where the instance has them
p = inst / "_bmad/custom/config.toml"
if p.is_file():
    text = p.read_text(encoding="utf-8"); k = 0
    def pin(m):
        global k
        if m.group(1) in rename: k += 1; return f'name = "{rename[m.group(1)]}"'
        return m.group(0)
    new_text = re.sub(r'^name = "([^"]*)"$', pin, text, flags=re.M)
    # Pins the instance lacks (RQ's ruling, 2026-10-03): the fork's name-only pins
    # for the upstream-declared seats, plus the tech writer where the instance's
    # table is upstream's.
    fork_pins = tomllib.loads((fork / "_bmad/custom/config.toml").read_text())["agents"]
    want = {c: v["name"] for c, v in fork_pins.items() if set(v) == {"name"}}
    if skipped: want["bmad-agent-tech-writer"] = new_name["bmad-agent-tech-writer"]
    have = tomllib.loads(new_text).get("agents", {})
    add = {c: nm for c, nm in want.items() if "name" not in have.get(c, {})}
    if any(c in have for c in add): die("_bmad/custom/config.toml has a table for a seat with no name; pin it by hand")
    if add:
        new_text = new_text.rstrip("\n") + "\n\n# --- Keelswell roster pins: display names for the seats upstream declares ---\n"
        new_text += "".join(f'\n[agents.{c}]\nname = "{nm}"\n' for c, nm in add.items())
    tomllib.loads(new_text)
    if k or add: writes[p] = new_text
    print(f"_bmad/custom/config.toml: {k} name pins renamed, {len(add)} added")

# ---- surface 3: Keelswell rows of the help catalogs, spliced as text
def splice(rel):
    p = inst / rel
    if not p.is_file(): return
    lines = p.read_text(encoding="utf-8").split("\n"); k = 0
    for i, line in enumerate(lines):
        m = re.match(r"Keelswell,([^,]+),", line)
        if not m or m.group(1) not in new_name: continue
        skill = m.group(1); row = next(csv.reader([line]))
        if len(row) != 13: die(f"{rel}:{i+1} is not a 13-column row")
        name = new_name[skill]
        if skill in CODES: row[2], row[3] = f"Agent {name}", CODES[skill]
        elif not row[2].startswith(name + ", "): row[2] = f"{name}, {row[2]}"
        row[4] = desc(skill)
        buf = io.StringIO(); csv.writer(buf, lineterminator="").writerow(row)
        if buf.getvalue() != line: lines[i] = buf.getvalue(); k += 1
    text = "\n".join(lines)
    allrows = list(csv.reader(io.StringIO(text)))
    codes = [r[3] for r in allrows[1:] if len(r) > 3 and r[3]]
    for c in CODES.values():
        want = (1,) if rel.endswith("bmad-help.csv") else (0, 1)   # the module catalog may lack later rows
        if codes.count(c) not in want: die(f"{rel}: menu code {c} appears {codes.count(c)} times")
    kee = [r[3] for r in allrows if r and r[0] == "Keelswell"]
    if len(kee) != len(set(kee)): die(f"{rel}: a Keelswell menu code repeats")
    writes[p] = text
    print(f"{rel}: {k} rows; codes repeated elsewhere in the file (not Keelswell's): "
          f"{sorted({c for c in codes if codes.count(c) > 1})}")
splice("_bmad/_config/bmad-help.csv")
splice("_bmad/keelswell/module-help.csv")

# ---- write, then list what changed
for p, t in writes.items():
    if p.read_text(encoding="utf-8") != t:
        changed.append(str(p.relative_to(inst)))
        if not check: p.write_text(t, encoding="utf-8")
lst = inst / ".git" / "keelswell-theme-files.txt"
tracked = set(subprocess.run(["git", "-C", str(inst), "ls-files"], capture_output=True, text=True).stdout.split("\n"))
untracked = [c for c in changed if c not in tracked]
if not check and (inst / ".git").is_dir(): lst.write_text("\n".join(c for c in changed if c in tracked) + "\n")
if untracked: print(f"changed but not tracked by git here, so not in the list: {untracked}")
print(f"skill trees: {trees}; {len(files)} files each")
print(f"{'would change' if check else 'changed'} {len(changed)} files" + ("" if check else f"; list written to {lst}"))
for c in changed: print("  " + c)
