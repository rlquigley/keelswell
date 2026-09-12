#!/usr/bin/env bash
# install.sh - Keelswell fork installer (reconstructed per Manual Ch 34, App I.10/I.12/I.13)
# Phases: 1 preflight, 2 agent-name mapping, 3 templating, 4 upstream install,
#         5 template-resolution wiring, 6 validation.
set -e
set -o pipefail

# -------- Flag defaults --------
USE_DEFAULTS=0; RENAME=0; USER_NAME=""; TARGET_PROJECT=""; CUSTOM_SOURCE=""
YES=0; DRY_RUN=0; VALIDATE_ALLOWLIST=0; VALIDATE_ONLY=0; SKIP_MCP_CHECK=0
LOG_LEVEL="info"
FORK_ROOT="$(cd "$(dirname "$0")" && pwd)"

usage() { echo "usage: ./install.sh [--use-defaults] [--rename] [--user-name NAME] [--target-project DIR] [--custom-source URL] [--yes] [--dry-run] [--validate-allowlist] [--validate-only] [--skip-mcp-check] [--log-level LVL]"; }

# -------- Helper: version_at_least (sort -V -C trick, 34.3.6) --------
version_at_least() { printf "%s\n%s\n" "$2" "$1" | sort -V -C; }

run() { if [ "$DRY_RUN" -eq 1 ]; then echo "DRY-RUN: $*"; else eval "$@"; fi; }

# -------- Flag parsing (exit 2 on bad args, 3 on conflicts) --------
while [ $# -gt 0 ]; do
  case "$1" in
    --use-defaults) USE_DEFAULTS=1 ;;
    --rename) RENAME=1 ;;
    --user-name) USER_NAME="$2"; shift ;;
    --target-project) TARGET_PROJECT="$2"; shift ;;
    --custom-source) CUSTOM_SOURCE="$2"; shift ;;
    --yes) YES=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --validate-allowlist) VALIDATE_ALLOWLIST=1 ;;
    --validate-only) VALIDATE_ONLY=1 ;;
    --skip-mcp-check) SKIP_MCP_CHECK=1 ;;
    --log-level) LOG_LEVEL="$2"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown flag: $1"; usage; exit 2 ;;
  esac
  shift
done
# Conflict matrix (Table I.12) -> exit 3
[ "$USE_DEFAULTS" -eq 1 ] && [ "$RENAME" -eq 1 ] && { echo "conflict: --use-defaults vs --rename"; exit 3; }
[ "$DRY_RUN" -eq 1 ] && [ "$VALIDATE_ONLY" -eq 1 ] && { echo "conflict: --dry-run vs --validate-only"; exit 3; }
if [ "$VALIDATE_ALLOWLIST" -eq 1 ]; then
  { [ "$RENAME" -eq 1 ] || [ "$VALIDATE_ONLY" -eq 1 ] || [ "$DRY_RUN" -eq 1 ]; } && { echo "conflict: --validate-allowlist composes with none of --rename/--validate-only/--dry-run"; exit 3; }
fi
[ "$VALIDATE_ONLY" -eq 1 ] && [ "$RENAME" -eq 1 ] && { echo "conflict: --validate-only vs --rename"; exit 3; }
# --yes implies --use-defaults unless --rename; non-interactive needs --user-name
if [ "$YES" -eq 1 ] && [ "$RENAME" -eq 0 ]; then USE_DEFAULTS=1; fi
if [ "$YES" -eq 1 ] && [ -z "$USER_NAME" ] && [ "$VALIDATE_ONLY" -eq 0 ] && [ "$VALIDATE_ALLOWLIST" -eq 0 ]; then
  echo "--yes (non-interactive) requires --user-name"; exit 2
fi
if [ -n "$TARGET_PROJECT" ]; then
  mkdir -p "$TARGET_PROJECT" 2>/dev/null || true
  [ -d "$TARGET_PROJECT" ] && [ -w "$TARGET_PROJECT" ] || { echo "ERROR: target directory $TARGET_PROJECT is not writable"; exit 4; }
fi
if [ -n "$CUSTOM_SOURCE" ] && [ ! -d "$CUSTOM_SOURCE" ]; then
  git ls-remote "$CUSTOM_SOURCE" >/dev/null 2>&1 || { echo "custom source unreachable: $CUSTOM_SOURCE"; exit 5; }
fi

echo "Keelswell fork installer v0.4.1"
cd "$FORK_ROOT"

phase1_preflight() {
  echo "[1/6] Preflight checks ..."
  command -v node >/dev/null 2>&1 || { echo "  Node.js: NOT FOUND (install v20.12+)"; exit 1; }
  nv=$(node --version | sed 's/^v//')
  version_at_least "$nv" "20.12.0" || { echo "  Node.js v$nv ... FAIL (>= 20.12 required)"; exit 1; }
  echo "  Node.js v$nv ... ok (>= 20.12 required)"
  command -v python3 >/dev/null 2>&1 || { echo "  Python 3: NOT FOUND (install python3 >= 3.11)"; exit 1; }
  pv=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
  version_at_least "$pv" "3.11.0" || { echo "  Python $pv ... FAIL (>= 3.11 required)"; exit 1; }
  python3 -c "import yaml" 2>/dev/null || { echo "  PyYAML: NOT FOUND (pip3 install pyyaml)"; exit 1; }
  echo "  Python $pv ... ok (>= 3.11 required)"
  command -v git >/dev/null 2>&1 || { echo "  git: NOT FOUND"; exit 1; }
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "  git: not inside a work tree"; exit 1; }
  gd=$(git rev-parse --git-dir)
  { [ -f "$gd/MERGE_HEAD" ] || [ -d "$gd/rebase-apply" ] || [ -d "$gd/rebase-merge" ]; } && { echo "  git: merge/rebase in progress; resolve first"; exit 1; }
  echo "  git $(git --version | awk '{print $3}') ... ok"
  command -v npx >/dev/null 2>&1 || { echo "  npx: NOT FOUND (ships with npm 9+)"; exit 1; }
  echo "  npx (npm $(npm --version)) ... ok"
  echo "Preflight: ok"
}

validate_agent_names() {
  python3 - "$1" "config/agent-names.yaml.default" <<'PY'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
exp = len(yaml.safe_load(open(sys.argv[2]))["agents"])
assert d.get("version") == 1, "schema version must be 1"
names = [a["display_name"] for a in d["agents"]]
roles = [a["role"] for a in d["agents"]]
dupes = sorted({n for n in names if names.count(n) > 1})
assert len(names) == exp, f"expected {exp} agents, found {len(names)}"
assert not dupes, f"display_name collision: {dupes}"
assert len(set(roles)) == exp, "duplicate role identifiers"
PY
}

phase2_mapping() {
  echo "[2/6] Agent-name mapping ..."
  local mapping="config/agent-names.yaml" defaults="config/agent-names.yaml.default"
  [ -f "$defaults" ] || { echo "  missing $defaults"; exit 1; }
  if [ "$USE_DEFAULTS" -eq 1 ]; then
    echo "  --use-defaults set; skipping interactive prompt."
    run "cp '$defaults' '$mapping'"
    echo "  Copying $defaults to $mapping ... done"
  elif [ "$RENAME" -eq 1 ] && [ -f "$mapping" ]; then
    echo "  --rename set; walking $(grep -c '^  - role:' "$mapping") agents against the existing mapping."
    interactive_prompt "$mapping"
  else
    read -r -p "  Use default names (Y/n): " reply; reply=${reply:-Y}
    case "$reply" in
      [Yy]*) run "cp '$defaults' '$mapping'"; echo "  Defaults accepted; $mapping written." ;;
      *) interactive_prompt "$defaults" ;;
    esac
  fi
  [ "$DRY_RUN" -eq 1 ] && { echo "  DRY-RUN: skipping mapping validation"; return; }
  validate_agent_names "$mapping"
  echo "  $(grep -c '^  - role:' "$mapping") agents loaded; all display_name values unique."
}

interactive_prompt() {
  local source_file="$1" target="config/agent-names.yaml" tmp; tmp=$(mktemp)
  echo "  Walking $(grep -c '^  - role:' "$source_file") agents. Press Enter to keep the current name, or type a new one."
  python3 - "$source_file" <<'PY' > "$tmp.in"
import sys, yaml
for a in yaml.safe_load(open(sys.argv[1]))["agents"]:
    print(a["role"], a["bmad_default"], a["display_name"], sep="\t")
PY
  { echo "version: 1"; echo "agents:"; } > "$tmp"
  while IFS=$'\t' read -r role bdef cur; do
    echo "  Role: $role  (BMAD default: $bdef)"
    read -r -p "  Display name [$cur]: " nn </dev/tty; nn=${nn:-$cur}
    printf "  - role: %s\n    bmad_default: %s\n    display_name: %s\n" "$role" "$bdef" "$nn" >> "$tmp"
  done < "$tmp.in"
  mv "$tmp" "$target"; rm -f "$tmp.in"
  echo "  $target written."
}

phase3_templating() {
  echo "[3/6] Templating skill files and agent persona prompts ..."
  [ "$DRY_RUN" -eq 1 ] && { echo "  DRY-RUN: would rewrite display names under skills/ and agents/"; return; }
  python3 - <<'PY'
import yaml, re, pathlib
defaults = {a["role"]: a["display_name"] for a in yaml.safe_load(open("config/agent-names.yaml.default"))["agents"]}
chosen   = {a["role"]: a["display_name"] for a in yaml.safe_load(open("config/agent-names.yaml"))["agents"]}
renames = {defaults[r]: chosen[r] for r in defaults if defaults[r] != chosen.get(r, defaults[r])}
for tree in ("skills", "agents", ".claude/skills"):
    p = pathlib.Path(tree)
    if not p.exists(): continue
    files = [f for f in p.rglob("*") if f.is_file() and f.suffix in (".md", ".csv", ".yaml", ".json", ".txt")]
    subs = 0
    for f in sorted(files):
        text = orig = f.read_text(encoding="utf-8", errors="ignore")
        for old, new in renames.items():
            text, n = re.subn(r"\b" + re.escape(old) + r"\b", new, text)
            subs += n
        if text != orig: f.write_text(text, encoding="utf-8")
    print(f"  {tree}/ : {len(files)} files scanned, {subs} substitutions" + (" (defaults already in place)" if not renames else ""))
PY
  echo "Templating: ok"
}

phase4_upstream() {
  echo "[4/6] Running upstream BMAD plugin install ..."
  local dir="${TARGET_PROJECT:-.}" src="${CUSTOM_SOURCE:-$FORK_ROOT}"
  echo "  npx bmad-method install --directory $dir --custom-source $src --tools claude-code --modules bmm,cis,tea,bmb --yes"
  if [ "$DRY_RUN" -eq 1 ]; then echo "  DRY-RUN: skipped"; return; fi
  if npx bmad-method install --directory "$dir" --custom-source "$src" --tools claude-code --modules bmm,cis,tea,bmb --yes; then
    echo "Upstream install: ok (exit code 0)"
  else
    echo "  WARNING: upstream install exited non-zero (non-fatal pre-publish; see Phase 7 of the quickstart)"
  fi
}

resolve_templates_into() {
  # The unified template-resolution routine keelswell init invokes (34.3.5).
  local T="$1"
  local ts; ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local pname; pname=$(basename "$T")
  # settings.json: resolve MODEL_*/REASONING_* from core/config.yaml tiers.
  python3 - "$T" "$pname" <<'PY'
import sys, yaml, pathlib
target, pname = sys.argv[1], sys.argv[2]
cfg = yaml.safe_load(open("core/config.yaml"))
tiers = {k: v["model"] for k, v in cfg["model_tiers"].items()}
rm = cfg["role_models"]
def model(role): return tiers[rm[role]["tier"]]
def reas(role): return rm[role]["reasoning"]
t = open("templates/settings.json.template").read()
subs = {
  "PROJECT_NAME_PLACEHOLDER": pname,
  "MODEL_ORCHESTRATOR": model("orchestrator"), "REASONING_ORCHESTRATOR": reas("orchestrator"),
  "MODEL_RESEARCH": model("research"), "REASONING_RESEARCH": reas("research"),
  "MODEL_CODING": model("coding"), "REASONING_CODING": reas("coding"),
  "MODEL_ADVERSARIAL": model("adversarial"), "REASONING_ADVERSARIAL": reas("adversarial"),
  "MODEL_FALLBACK": model("fallback"),
}
for k, v in subs.items(): t = t.replace(k, v)
p = pathlib.Path(target) / ".claude"; p.mkdir(parents=True, exist_ok=True)
(p / "settings.json").write_text(t)
(p / "settings.local.json").write_text('{\n  "$comment": "PERSONAL OVERRIDES. Gitignored. Do not commit."\n}\n')
print("  Resolved .claude/settings.json ... done")
PY
  sed "s/{user_name}/${USER_NAME:-you}/g" templates/CLAUDE.md.template > "$T/CLAUDE.md"
  echo "  Resolved CLAUDE.md written to $T/CLAUDE.md (user name: ${USER_NAME:-you})"
  sed "s/{init_timestamp}/$ts/g" templates/TODO.md.template    > "$T/TODO.md"
  sed "s/{init_timestamp}/$ts/g" templates/HANDOFF.md.template > "$T/HANDOFF.md"
  echo "  Computing {init_timestamp} ... $ts ; TODO.md and HANDOFF.md written"
  cp templates/.gitignore.template "$T/.gitignore"
  cp -r templates/_bmad-output "$T/_bmad-output" 2>/dev/null || true
  echo "  Scaffolding $T/_bmad-output/ ... done (7 subdirectories)"
  mkdir -p "$T/.claude/skills" "$T/.claude/hooks" "$T/.claude/rules" "$T/.claude/agents"
  for s in skills/*; do rm -rf "$T/.claude/skills/$(basename "$s")"; cp -r "$s" "$T/.claude/skills/$(basename "$s")"; done
  find "$T/.claude/skills" -name __pycache__ -type d -prune -exec rm -rf {} +
  cp .claude/hooks/*.sh "$T/.claude/hooks/" && chmod +x "$T/.claude/hooks/"*.sh
  # Fork-owned Claude Code subagent definitions (Phase 3). Not BMAD personas:
  # the installer never reads .claude/agents/, which is why the evaluator can
  # live here without colliding with an upstream module.yaml declaration.
  cp .claude/agents/*.md "$T/.claude/agents/"
  echo "  Subagent definitions: $(ls -1 .claude/agents/*.md | wc -l | tr -d ' ') copied to $T/.claude/agents/"
  local slug; slug=$(basename "$T")
  mkdir -p "$HOME/.claude/projects/$slug/memory"
  echo "  Auto-memory directory: ~/.claude/projects/$slug/memory/ ... done"
  # Leftover-token exhaustiveness check
  if grep -l "{user_name}\|{init_timestamp}" "$T/CLAUDE.md" "$T/TODO.md" "$T/HANDOFF.md" >/dev/null 2>&1; then
    echo "  ERROR: unresolved template tokens remain"; exit 7
  fi
}

phase5_wiring() {
  echo "[5/6] Wiring template-resolution path ..."
  if [ -n "$TARGET_PROJECT" ]; then
    [ "$DRY_RUN" -eq 1 ] && { echo "  DRY-RUN: would resolve templates into $TARGET_PROJECT"; return; }
    resolve_templates_into "$TARGET_PROJECT"
  else
    echo "  Registered resolve_template routine (invoked by keelswell init or --target-project)."
    echo "  Three templates known: CLAUDE.md, memory (TODO, HANDOFF), .gitignore."
  fi
  echo "Template wiring: ok"
}

allowlist_check() {
  local base="${TARGET_PROJECT:-.}" gaps=0
  for f in _bmad/scripts/resolve_config.py _bmad/scripts/resolve_customization.py \
           _bmad/config.toml _bmad/_config/bmad-help.csv \
           _bmad/bmb/config.yaml _bmad/bmm/config.yaml _bmad/cis/config.yaml \
           _bmad/core/config.yaml _bmad/tea/config.yaml _bmad/custom/config.toml \
           .claude/settings.json .claude/agents/keelswell-wave-evaluator.md \
           .claude/skills/bmad-close-epic/scripts/check_review_records.py \
           .claude/skills/bmad-dev-wave/scripts/wave_status.py \
           .claude/skills/bmad-dev-wave/scripts/evaluate_wave.py \
           .claude/skills/bmad-dev-wave/scripts/wave_gate.py \
           .claude/hooks/wave-gate.sh .claude/hooks/wave-session-end.sh; do
    [ -e "$base/$f" ] || { echo "  allowlist gap: $base/$f missing"; gaps=1; }
  done
  [ "$gaps" -eq 0 ] || exit 6
  echo "  Allowlist: ok"
}

# Phase 4 of docs/harness-conversion-plan.md: the enforcement layer Phases 1-3
# built is asserted after every install and under --validate-only. These checks
# read; they never repair. A failure names the invariant and phase 6 exits 7
# (Table I.13: a runtime file is missing or a skill failed to load).
WAVE_SKILLS="bmad-create-wave bmad-dev-wave bmad-merge-wave bmad-resume-wave bmad-status-wave"

harness_check() {
  # $1: the skills root to assert. skills/ is the fork's source; .claude/skills
  #     is the snapshot an upstream refresh rewrites, so both are checked.
  # $2: the project root whose .claude/agents/ the evaluator check reads.
  local root="$1" base="$2" bad=0 s missing err
  local gate="$root/bmad-close-epic/scripts/check_review_records.py"
  local vocab="$root/bmad-dev-wave/scripts/wave_status.py"
  local evaluate="$root/bmad-dev-wave/scripts/evaluate_wave.py"
  echo "  Harness invariants under $root/:"
  if [ -x "$gate" ]; then echo "    gate script present and executable ... ok"
  else echo "    gate script present and executable ... FAIL ($gate)"; bad=1; fi
  if grep -q 'scripts/check_review_records.py' "$root/bmad-close-epic/SKILL.md" 2>/dev/null; then
    echo "    gate wired into bmad-close-epic ... ok"
  else echo "    gate wired into bmad-close-epic ... FAIL ($root/bmad-close-epic/SKILL.md does not call scripts/check_review_records.py)"; bad=1; fi
  if [ -x "$vocab" ]; then echo "    status vocabulary present and executable ... ok"
  else echo "    status vocabulary present and executable ... FAIL ($vocab)"; bad=1; fi
  missing=""
  for s in $WAVE_SKILLS; do
    grep -q 'wave_status.py' "$root/$s/SKILL.md" 2>/dev/null || missing="$missing $s"
  done
  if [ -z "$missing" ]; then echo "    every wave skill references wave_status.py ... ok"
  else echo "    every wave skill references wave_status.py ... FAIL (missing in:$missing)"; bad=1; fi
  if [ -x "$root/bmad-dev-wave/scripts/wave_gate.py" ]; then echo "    hook script wave_gate.py present and executable ... ok"
  else echo "    hook script wave_gate.py present and executable ... FAIL ($root/bmad-dev-wave/scripts/wave_gate.py)"; bad=1; fi
  if [ -f "$evaluate" ] && err=$(python3 "$evaluate" check --project-root "$base" 2>&1 >/dev/null); then
    echo "    evaluator subagent declares no writing tool ... ok"
  else
    echo "    evaluator subagent declares no writing tool ... FAIL"
    [ -f "$evaluate" ] && printf '%s\n' "$err" | sed 's/^/      /' || echo "      ($evaluate missing)"
    bad=1
  fi
  return "$bad"
}

hooks_check() {
  # $1: the project root. The two hook wrappers must exist, be executable, and
  # be registered. The fork has no .claude/settings.json of its own (hooks are
  # resolved into a target project from the template), so there the template
  # is the registration that is checked.
  local base="$1" bad=0 h settings="$1/.claude/settings.json"
  [ -f "$settings" ] || settings="templates/settings.json.template"
  echo "  Harness hooks under $base/.claude/hooks/ (registration: $settings):"
  for h in wave-gate.sh wave-session-end.sh; do
    if [ -x "$base/.claude/hooks/$h" ]; then echo "    $h present and executable ... ok"
    else echo "    $h present and executable ... FAIL ($base/.claude/hooks/$h)"; bad=1; fi
    if grep -q "\.claude/hooks/$h" "$settings" 2>/dev/null; then echo "    $h registered ... ok"
    else echo "    $h registered ... FAIL (not named in $settings)"; bad=1; fi
  done
  return "$bad"
}

phase6_validation() {
  echo "[6/6] Validation ..."
  [ "$DRY_RUN" -eq 1 ] && { echo "  DRY-RUN: skipped"; return; }
  validate_agent_names config/agent-names.yaml
  echo "  agent-names.yaml: valid YAML, $(grep -c '^  - role:' config/agent-names.yaml) unique display_names ... ok"
  if grep -rl '\${AGENT:[a-z-]*}' skills agents 2>/dev/null; then
    echo "  ERROR: leftover agent tokens in skills/ or agents/"; exit 7
  fi
  echo "  skills/ and agents/: no leftover tokens ... ok"
  local base="${TARGET_PROJECT:-.}" harness_bad=0
  harness_check skills "$FORK_ROOT" || harness_bad=1
  harness_check "$base/.claude/skills" "$base" || harness_bad=1
  hooks_check "$base" || harness_bad=1
  if [ "$harness_bad" -ne 0 ]; then
    echo "  ERROR: harness invariant failed (named above). Nothing was repaired; restore the file and re-run --validate-only."; exit 7
  fi
  echo "  Harness invariants: ok"
  if command -v keelswell >/dev/null 2>&1; then
    echo "  keelswell command on PATH ... ok ($(command -v keelswell))"
  else
    echo "  keelswell command on PATH ... NOT FOUND (use ./install.sh --target-project as the init fallback)"
  fi
  if [ "$SKIP_MCP_CHECK" -eq 1 ]; then
    echo "  keelswell-mcp check ... skipped (--skip-mcp-check)"
  elif command -v keelswell-mcp >/dev/null 2>&1; then
    echo "  keelswell-mcp on PATH ... ok"
  else
    echo "  keelswell-mcp on PATH ... FAIL (re-run with --skip-mcp-check if registered elsewhere)"; exit 8
  fi
  echo "Validation: ok"
}

# -------- Dispatch --------
if [ "$VALIDATE_ALLOWLIST" -eq 1 ]; then phase1_preflight; allowlist_check; exit 0; fi
if [ "$VALIDATE_ONLY" -eq 1 ]; then phase1_preflight; phase6_validation; exit 0; fi
phase1_preflight
phase2_mapping
phase3_templating
phase4_upstream
phase5_wiring
phase6_validation
echo "Install complete. Next steps:"
echo "1. cd into a project directory and run: keelswell init --user-name <you> --yes"
echo "   (fallback: $FORK_ROOT/install.sh --use-defaults --yes --user-name <you> --target-project <dir> --skip-mcp-check)"
echo "2. Run the end-to-end verification protocol (quickstart Phase 8)."
echo "3. Publish the fork (quickstart Phase 7) if not yet published."
exit 0
