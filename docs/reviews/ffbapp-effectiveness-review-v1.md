# Keelswell Effectiveness Review v1: ffbapp

Reviewed 2026-09-10 against keelswell `205e0dc` (main), ffbapp `ea68bb7` (main), `~/.claude` `b3895b6` plus an uncommitted `CLAUDE.md` edit. Framework read as data; no Keelswell agent, skill, party, or wave workflow was invoked.

Conventions: tokens = chars / 4. "Last commit" = `git log -1 -- <path>`. Evidence counts in 1b and 1c are literal-name hits across: git log subjects and bodies (git), `_bmad-output/session-wrap/*/triage.md` (trg), `.memlog.md` files (mlog), `HANDOFF.md` (hoff), `.claude/settings.local.json` allow list (set), ffbapp auto-memory files (mem). Persona-name hits in 1b are across `_bmad-output/**/*.md`, `docs/**/*.md`, `HANDOFF.md`, `TODO.md`, `CLAUDE.md`. Anything not checkable in the three repos is tagged OPEN VERIFY.

---

## Phase 1: Inventory

### 1a. Instruction files

Load column: auto = injected into every ffbapp session by the harness; mandated = ffbapp `CLAUDE.md` says read it every session; demand = read when a skill or kickoff names it; none = no reader found.

#### Global (`~/.claude`)

| Path | Lines | Chars | ~Tokens | Last commit | Purpose | References | Referenced by | Load |
|---|---|---|---|---|---|---|---|---|
| `~/.claude/CLAUDE.md` | 83 | 6,750 | 1,690 | 2026-07-12 `ebecc07`; working copy adds a Voice section and "Remove all mannered prose" (uncommitted, +11 lines) | Global rules: filesystem split, secrets, communication style, voice bans, clarifying-question discipline, coding simplicity and discipline, verification, self-check | `@~/.claude/filesystem.md`, `~/Projects/utilities/dev-setup`, 1Password `op://` | nothing in any repo (harness loads it) | auto |
| `~/.claude/filesystem.md` | 17 | 918 | 230 | 2026-06-23 `a6b2509` | Folder layout, naming, per-client git identity | none | `~/.claude/CLAUDE.md` (@import) | auto |
| `~/.claude/settings.json` | 32 | 1,537 | n/a (not text-injected) | untracked (`.gitignore` ignores `*`) | outputStyle Concise; allow `Bash(git *)`, ask `Bash(git push *)`; enables plugin `i-have-adhd`; `autoMode.environment` and `soft_deny` text | plugin marketplace `ayghri/i-have-adhd` | none | auto (harness) |
| `~/.claude/plugins/cache/i-have-adhd/i-have-adhd/0.1.0/skills/i-have-adhd/SKILL.md` | 142 | 6,848 | 1,710 | plugin 0.1.0 installed 2026-07-31 (`installed_plugins.json`) | Output-shaping ruleset for an ADHD reader (lead with action, numbered steps, cap lists at 5, no preamble, time estimates) | none | `hooks/hooks.json` SessionStart -> `hooks/always-on.sh` injects the body when `~/.claude/.i-have-adhd-always` exists (file dated 2026-08-14) | auto |
| `~/.claude/projects/-Users-ryanquigley-Projects-personal-ffbapp/memory/MEMORY.md` | 41 | 9,137 | 2,280 | mtime 2026-09-10 | Index of 39 auto-memory entries | 40 topic files, 310,098 chars total (`ffbapp-pipeline-state.md` 141,326; `dev-wave-orchestration-routes.md` 47,988) | bmad-wrap step 1 writes here | auto (index); topics on demand |
| `~/.claude/output-styles/ste100.md` | 81 | 3,314 | 830 | untracked | STE100 output style | none | `settings.json` selects Concise, not STE100 | none |
| `~/.claude/claude-ai-preferences.md` | 8 | 1,080 | 270 | 2026-07-13 `b3895b6` | Mirror of the claude.ai profile field; header says no surface reads it | none | none | none |
| `~/.claude/skills/asd-ste100/SKILL.md` | 138 | 15,346 | 3,840 | git submodule, not in `~/.claude` history | STE100 rewrite skill (user-level) | `references/writing-rules.md` | none in repos | auto (description only) |
| `~/.claude/.pre-commit-config.yaml` | 18 | 718 | n/a | 2026-06-23 `71779f0` | gitleaks pre-commit template for repos | gitleaks v8.30.0 | not installed in ffbapp (ffbapp uses a raw `.git/hooks/pre-commit`) | none |
| `~/.claude/projects/-Users-ryanquigley-Projects-personal-keelswell/memory/MEMORY.md` | 5 | 507 | 130 | mtime 2026-08-07 | Index of 4 keelswell memories | 4 topic files (12,022 chars) | bmad-wrap | auto in keelswell sessions only |

#### ffbapp

| Path | Lines | Chars | ~Tokens | Last commit | Purpose | References | Referenced by | Load |
|---|---|---|---|---|---|---|---|---|
| `CLAUDE.md` | 38 | 4,104 | 1,030 | 2026-09-01 `0423171` (created 2026-08-20 `fdea974`; 6 commits) | Repo map, documents of record, standing rules (register rows 36, 37, 40, 48, 49, 50, abbreviation rule), hands-off paths, "when development starts" | `HANDOFF.md`, `TODO.md`, register, `prd.md`, `ARCHITECTURE-SPINE.md`, `architecture/index.md`, `ux-designs/ux-ffbapp-2026-08-08/`, `epics.md`, `waves.md`, `glossary.md`, `.claude/hooks/diff-composition-gate.sh`, `project-context.md`, `_bmad/` | register rows 48 and 50 text; 29 triage reports; `bmad-wrap` (CLAUDE.md gate); `diff-composition-gate.sh` comment | auto |
| `HANDOFF.md` | 87 | 20,341 | 5,090 | 2026-09-10 `8206f7f` | Current state table, decisions since last handoff, blocked-on, next-session options, kickoff prompt with run mode, model, effort | `epic-closure/epic-4/*`, `waves.md`, `project-context.md`, `projections.py`, `test_assembly_precision.py`, PRs #83 to #91 | `CLAUDE.md` (read first), `bmad-wrap` step 4 (writes), `bmad-status-wave` probe 5 (hint), `bmad-resume-wave` (refuses on Status red), `templates/HANDOFF.md.template` | mandated |
| `TODO.md` | 11 | 9,459 | 2,360 | 2026-09-10 `3c9dbfd` | Open items (4, all founder-side business) | registration log, entity docs, `docs/flag-b/*` | `CLAUDE.md`, `bmad-wrap` step 3 | mandated |
| `_bmad-output/project-context.md` | 142 | 22,178 | 5,540 | 2026-09-10 `97976b0` | Dev-agent coding rules: stack, boundaries, language, framework, testing (17 rules), workflow (13 rules), don't-miss (13 rules); grows by epic retrospective | spine, register, content standard, glossary | `CLAUDE.md`, `bmad-close-epic` step 5 (appends), `bmad-dev-wave` Project Conventions Block (by intent), kickoff prompts | demand |
| `_bmad-output/settled-decisions-register-2026-08-04.md` | 164 | 42,847 | 10,710 | 2026-09-10 `3c9dbfd` | 51 founder rulings, 10 sections plus ratification | brainstorm canon, innovation strategy, narrative, name matrix, pricing register, `TODO.md`, `HANDOFF.md` | `CLAUDE.md`, `project-context.md`, `waves.md`, `epics.md`, `bmad-dev-wave` 1.1.0, `bmad-close-epic` 1.2.0, `bmad-status-wave` 1.1.0 (row 51) | demand |
| `_bmad-output/planning-artifacts/waves.md` | 175 | 72,532 | 18,130 | 2026-09-10 `97976b0` | Phase 1 wave map: 20 wave rows, dependency edges, 14 dated execution amendments citing 27 distinct EW ids | `epics.md`, spine, readiness report, register | `bmad-create-wave` (writes), `bmad-dev-wave`, `bmad-merge-wave`, `bmad-status-wave`, `bmad-close-epic`, `bmad-create-story` | demand |
| `_bmad-output/planning-artifacts/epics.md` | 2,378 | 158,857 | 39,710 | 2026-08-24 `7553a68` | 30 epics, 142 story headings, requirements inventory, founder checkpoints | PRD, addendum, spine, cost model, UX docs, LLM-surface docs, register | `waves.md`, `bmad-create-wave`, `bmad-create-story`, `bmad-close-epic` (traceability source), `CLAUDE.md` | demand |
| `_bmad-output/planning-artifacts/glossary.md` | 176 | 12,780 | 3,200 | 2026-09-08 `a6c33ee` | Abbreviation series of record | none | `CLAUDE.md` abbreviation rule; every "Reference key" block | demand |
| `.claude/settings.local.json` | 373 | 41,051 | n/a | untracked (gitignored) | 354 permission allow entries (250 Bash, 67 WebFetch, 12 Skill, 15 Read, 9 mcp); one Stop hook | `.claude/hooks/diff-composition-gate.sh` | none | auto (harness) |
| `.claude/hooks/diff-composition-gate.sh` | 19 | 1,027 | n/a | 2026-09-01 `0423171` | Stop hook: prints a composition-drift reminder when a diff is pending; never blocks (`exit 0` always) | `CLAUDE.md` row 48 | `settings.local.json` hooks.Stop, `CLAUDE.md` | auto (on Stop) |
| `_bmad/config.toml` | 348 | 20,739 | 5,180 | 2026-08-25 `0908ba3` | Installer-managed agent descriptor registry (38 `[agents.*]` blocks) and module paths | `_bmad/custom/config.toml`, `config.user.toml` | `_bmad/scripts/resolve_customization.py` (agent activation), `resolve_party.py` (party rosters) | demand (agent activation) |
| `_bmad/custom/config.toml` | 7 | 348 | 90 | 2026-08-01 `60f3ced` | Team overlay: comments only, no overrides | none | resolver | demand |
| `_bmad/custom/bmad-party-mode.toml` | 39 | 3,774 | 940 | 2026-08-10 `769c99d` | Beta League panel: 4 user-persona seats, 1 party group | register rows 9, 24, 29 | `bmad-party-mode` (`resolve_party.py`) | demand |
| `_bmad/keelswell/config.yaml` | 13 | 320 | 80 | installer 2026-07-31 (`60f3ced`) | user_name RQ, project_name, output folder | none | keelswell skills' config step | demand |
| `_bmad/_config/manifest.yaml` | 70 | n/a | n/a | 2026-08-01 `60f3ced` | Install record: BMAD 6.10.0, cis v0.2.1, tea v1.19.1, bmb v2.1.0, keelswell "version: main", `ides: [claude-code]` | none | installer | none |
| `.claude/skills/*/SKILL.md` (107 files) | 13,036 | 760,376 | 190,090 (bodies) | tracked (1,125 files under `.claude/skills`; see 1c) | Skill definitions; frontmatter name plus description = 27,903 chars | varies | harness skill loader | auto (frontmatter, ~7,000 tokens); body on invocation |
| `.agents/skills/claude-md-doctor/SKILL.md` | 312 | 17,470 | 4,370 | untracked (`git ls-files .agents` = 0) | Byte-identical duplicate of `.claude/skills/claude-md-doctor/SKILL.md`; installed by the `skills` CLI (`skills-lock.json`) | scripts under the same dir | none | OPEN VERIFY whether Claude Code loads `.agents/skills` (if yes, the description is loaded twice) |
| `docs/wave-*/` (44 files, 18 dirs) plus `docs/flag-b/` (4) and `docs/local-dev.md` | n/a | n/a | n/a | various, 2026-08-20 to 2026-09-10 | Per-wave test designs (17), API-surface pins (12), party reviews (10), 3 one-offs | `epics.md`, `waves.md`, register | `bmad-close-epic` 1.2.0 preflight (review record), kickoff prompts | demand |
| `pyproject.toml` (lint and import-linter sections) | 145 | 3,906 | n/a | 2026-09-01 `34ee8a3` | ruff E, F, I, S608, C901 (22); 7 import-linter contracts (AD-2, AD-18) | none | `tests/verify-fast.sh`, CI `fast` | auto (tooling) |

#### Keelswell source (not loaded into ffbapp sessions except through the installed copies above)

| Path | Lines | Chars | ~Tokens | Last commit | Purpose | References | Referenced by | Load |
|---|---|---|---|---|---|---|---|---|
| `README.md` | 17 | 1,012 | 250 | 2026-08-25 `dae5c53` | Install command pinned to `@v0.8.0`; roster line | `install.sh`, upstream issue #2607 | none | none |
| `CHANGELOG.md` | 200 | 11,177 | 2,790 | 2026-08-25 `dae5c53` | Keep-a-Changelog through 0.8.0 (2026-08-24); skill changes of 2026-08-31 (wrap 1.9.0) and 2026-09-10 (dev-wave 1.1.0, close-epic 1.2.0, status-wave 1.1.0) are absent | skills, `module.yaml`, `marketplace.json` | none | none |
| `module.yaml` | 184 | 13,625 | 3,400 | 2026-08-25 `dae5c53` | Custom-module descriptor: 25 fork-only agents for the installer | `config/agent-names.yaml` | installer (`collectAgentsFromModuleYaml`) | install time |
| `.claude-plugin/marketplace.json` | 65 | 2,350 | 590 | 2026-08-25 `dae5c53` | Plugin manifest, version 0.8.0, 46 skill paths | `skills/*` | installer | install time |
| `config/agent-names.yaml` (+ `.default`) | 121 / 103 | n/a | n/a | 2026-08-25 `dae5c53` | Roster of record, 38 rows (`.default` stops at 32) | none | `module.yaml` comment, `install.sh` | install time |
| `core/config.yaml` | 44 | 1,600 | 400 | 2026-07-17 `f999e39` | Model tiers (`claude-opus-4-8`, `claude-sonnet-4-6`, `claude-haiku-4-5`), role_models, permissions (`forbidden_modes: [auto, bypass]`), parallelism (`max_parallel_subagents: 4`, `worktree_root: .worktrees`), context escalation | "Chapter 29", "28.4.3" of a manual not in the repo | `bmad-dev-wave` step 6 text; no consumer in ffbapp (`grep model_tiers` = 0 hits outside the skill text) | none (not installed in ffbapp) |
| `templates/CLAUDE.md.template` | 109 | 6,900 | 1,720 | 2026-07-17 `f999e39` | Project CLAUDE.md template (BMAD workflow routing, em-dash scrub, bulk-edit triage, skip-skill heuristic, LSP-first, self-check) | `.claude/hooks/em-dash-scrub.sh` | `install.sh` | not used by ffbapp (`CLAUDE.md` written fresh 2026-08-20) |
| `templates/HANDOFF.md.template` | 33 | 1,500 | 380 | 2026-07-17 | Handoff shape (Stage, Wave, Step, Status table) | none | `install.sh` | shape followed loosely by ffbapp |
| `templates/TODO.md.template` | 28 | 1,100 | 280 | 2026-07-17 | P0 to P3 buckets, Closed section | none | `install.sh` | not followed (ffbapp `TODO.md` has one Open list, no buckets) |
| `templates/settings.json.template` | 49 | 1,300 | 330 | 2026-07-17 | model placeholders, `subagentModels`, `subagentReasoning`, `mcpServers.keelswell` (`keelswell-mcp`), hooks (em-dash PostToolUse, wrap-reminder SessionEnd), `skillsPaths`, `agentNamesFile` | hooks | `install.sh` | not installed (ffbapp has no `.claude/settings.json`); `keelswell-mcp` not on PATH; `subagentModels`, `subagentReasoning`, `skillsPaths`, `agentNamesFile`, `contextWindow` are not documented Claude Code settings keys (OPEN VERIFY) |
| `templates/.gitignore.template` | 72 | n/a | n/a | 2026-07-18 | Project gitignore | none | `install.sh` | ffbapp `.gitignore` is 10 lines, not this |
| `install.sh` | 288 | 14,186 | n/a | 2026-07-19 `a7b6760` | Six-phase installer | templates, upstream installer | README | OPEN VERIFY whether it ran on ffbapp (installer manifest present; `install.sh` phases leave no marker) |
| `docs/upstream-refresh-runbook.md` | 111 | 5,600 | 1,400 | 2026-07-19 `76fdcb9` | Refresh procedure, clobber classes, F-6/F-10 record | `_bmad/_config/*.csv`, `resolve_config.py` | none | none |
| `.claude/hooks/em-dash-scrub.sh`, `wrap-reminder.sh` | 8 / 4 | 284 / 177 | n/a | 2026-07-17 `f999e39` | PostToolUse em-dash check (exit 1 on hit); SessionEnd wrap reminder | none | `templates/settings.json.template` only; keelswell's own `.claude/settings.local.json` wires no hooks | none (unwired in both repos) |
| `.claude/settings.local.json` (keelswell) | 60 | 3,400 | n/a | untracked | 54 allow entries, no hooks | none | none | auto in keelswell sessions |
| `agents/*.md` (38 files) | 1,929 | n/a | n/a | 2026-08-25 `dae5c53` | Persona sources mirrored into skill SKILL.md files | none | `skills/*` (by copy) | none directly |
| `skills/` (46 dirs, 159 files) | n/a | n/a | n/a | 2026-09-10 `1899f35` | Fork-owned skills: 7 wave, 25 agent launchers (15 custom, 8 arch, qa, master), 13 renamed vanilla personas, `bmad-retrospective` recast | none | `marketplace.json`; mirrored to `.claude/skills` (106 dirs, 1,125 files) and `.agents/skills` (74 dirs, 1,051 files, frozen pre-v0.3.0 per runbook) | install time |
| `_bmad-output/session-wrap/2026-08-08T00-35-00Z/triage.md` | n/a | n/a | n/a | 2026-08-08 | One bmad-wrap run on keelswell itself | none | none | none |

### 1b. Agents

38 roster agents (`config/agent-names.yaml`) plus 4 non-roster Beta League seats. "Invoked by" lists the skills whose text dispatches or resolves the agent; "Artifacts on ffbapp" is persona-name evidence plus the pull request that landed the work. Zero persona names appear in any `docs/wave-*` file (44 files) or any `_bmad-output/epic-closure` report (25 files), so wave-phase and closure-phase attribution is OPEN VERIFY pending transcripts (Phase 2).

| Agent (display name) | Role | ffbapp skill id | Source file (keelswell) | SKILL lines | Invoked by | Artifacts on ffbapp (files / hits / git-log hits; PRs) |
|---|---|---|---|---|---|---|
| Rand al'Thor | Master orchestrator | `bmad-master` | `agents/core-bmad-master.md` (39) | 85 | own command; `bmad-help` | 0 / 0 / 0 |
| Moiraine Damodred | Analyst | `bmad-agent-analyst` | `agents/bmm-analyst.md` (76) | 76 | own command; party rosters | 32 / 96 / 10; market research 2026-08-05, brief 2026-08-05, register ratification (allow-list commit message "Moiraine stage checkpoint 1") |
| Egwene al'Vere | PM | `bmad-agent-pm` | `agents/bmm-pm.md` (76) | 76 | own command; party rosters | 22 / 47 / 13; PRD (PR #2), epics cut (PR #20, #21), readiness check (PR #23) |
| Perrin Aybara | Architect | `bmad-agent-architect` | `agents/bmm-architect.md` (76) | 76 | own command; party rosters | 19 / 49 / 7; architecture spine (PR #6), architecture party review (PR #7) |
| Mat Cauthon | Developer | `bmad-agent-dev` | `agents/bmm-dev.md` (76) | 76 | own command; `bmad-retrospective` scripted dialog (recast); `bmad-dev-wave` step 6 names no persona | 1 / 3 / 0; no wave artifact names him |
| Min Farshaw | UX designer | `bmad-agent-ux-designer` | `agents/bmm-ux-designer.md` (76) | 76 | own command; party rosters | 4 / 7 / 3; UX spec (PR #4), UX party review (PR #5) |
| Loial | Tech writer | `bmad-agent-tech-writer` | `agents/bmm-tech-writer.md` (76) | 76 | own command | 3 / 6 / 1; party reviewer only |
| Aviendha | QA / test architect | `bmad-agent-qa` | `agents/bmm-qa.md` (47) | 89 | own command; party rosters; `bmad-dev-wave` step 3 says "one QA-persona subagent" without naming which | 9 / 30 / 0; PRD and LLM-surface reviews; no wave test design names her |
| Galad Damodred | Test architect (TEA) | `bmad-tea` | `agents/tea-murat.md` (80) | 80 | own command; party rosters | 11 / 18 / 0; PRD and LLM-surface reviews; no wave test design names him |
| Verin Mathwin | Infrastructure analyst | `bmad-agent-arch-infrastructure-analyst` | `agents/arch-infrastructure-analyst.md` (43) | 43 | own command; party rosters | 5 / 9 / 0; register credits her party instruction (register header) |
| Elayne Trakand | Cloud architect | `bmad-agent-arch-cloud-architect` | `agents/arch-cloud-architect.md` (53) | 53 | own command; party rosters | 4 / 5 / 0 |
| Cadsuane Melaidhrin | Data architect | `bmad-agent-arch-data-architect` | `agents/arch-data-architect.md` (47) | 47 | own command; party rosters | 8 / 18 / 0 |
| Androl Genhald | Integration architect | `bmad-agent-arch-integration-architect` | `agents/arch-integration-architect.md` (44) | 44 | own command; party rosters | 5 / 10 / 0 |
| Rhuarc | Platform engineer | `bmad-agent-arch-platform-engineer` | `agents/arch-platform-engineer.md` (38) | 38 | own command; party rosters | 5 / 8 / 0 |
| Berelain sur Paendrag | Cost optimizer | `bmad-agent-arch-cost-optimizer` | `agents/arch-cost-optimizer.md` (44) | 44 | own command; party rosters | 6 / 8 / 0 |
| Lan Mandragoran | Security reviewer | `bmad-agent-arch-security-reviewer` | `agents/arch-security-reviewer.md` (42) | 42 | own command; party rosters | 1 / 1 / 0 |
| Sorilea | Architecture governor | `bmad-agent-arch-architecture-governor` | `agents/arch-architecture-governor.md` (44) | 44 | own command; party rosters | 8 / 14 / 0 |
| Siuan Sanche | Brainstorming coach | `bmad-cis-agent-brainstorming-coach` | `agents/cis-brainstorming-coach.md` (72) | 72 | own command; `bmad-brainstorming` | 9 / 14 / 0; brainstorm 2026-07-31 (initial commit `60f3ced`) |
| Nynaeve al'Meara | Design-thinking coach | `bmad-cis-agent-design-thinking-coach` | `agents/cis-design-thinking-coach.md` (72) | 72 | own command | 2 / 3 / 1; Beta League fold (party toml header) |
| Logain Ablar | Innovation strategist | `bmad-cis-agent-innovation-strategist` | `agents/cis-innovation-strategist.md` (72) | 72 | own command; `bmad-cis-innovation-strategy` | 22 / 49 / 3; disruption evaluation (PR #1) |
| Birgitte Silverbow | Creative problem solver | `bmad-cis-agent-creative-problem-solver` | `agents/cis-creative-problem-solver.md` (72) | 72 | own command; party rosters | 8 / 13 / 0 |
| Thom Merrilin | Storyteller | `bmad-cis-agent-storyteller` | `agents/cis-storyteller.md` (72) | 72 | own command; `bmad-cis-storytelling` | 3 / 5 / 0; founding narrative 2026-08-04 (worktree `ffbapp-founding-narrative-618570`) |
| Morgase Trakand | Presentation master | `bmad-cis-agent-presentation-master` | `agents/cis-presentation-master.md` (72) | 72 | own command | 5 / 7 / 0 |
| Tam al'Thor | SRE / DevOps | `agent-tam-althor` (keelswell: `agent-sre`) | `agents/custom-sre.md` (41) | 41 | own command; party rosters | 6 / 9 / 0 |
| Tuon | Growth | `agent-tuon` (keelswell: `agent-growth`) | `agents/custom-growth.md` (34) | 34 | own command; party rosters | 6 / 12 / 0 |
| Setalle Anan | Accessibility | `agent-setalle-anan` (keelswell: `agent-accessibility`) | `agents/custom-accessibility.md` (35) | 35 | own command; party rosters; design pair routes WCAG to her | 12 / 28 / 0 |
| Hurin | Analytics / BI | `agent-hurin` (keelswell: `agent-analytics`) | `agents/custom-analytics.md` (31) | 31 | own command; party rosters | 12 / 19 / 1 |
| Gareth Bryne | Legal | `agent-gareth-bryne` (keelswell: `agent-legal`) | `agents/custom-legal.md` (34) | 34 | own command; party rosters | 11 / 15 / 0; name-counsel briefs OPEN VERIFY as his output |
| Damer Flinn | ML / AI | `agent-damer-flinn` (keelswell: `agent-ml`) | `agents/custom-ml.md` (35) | 35 | own command; party rosters | 14 / 20 / 0 |
| Bayle Domon | Billing | `agent-bayle-domon` (keelswell: `agent-billing`) | `agents/custom-billing.md` (30) | 82 | own command; party rosters | 10 / 13 / 0; register row 19 credits a party finding |
| Juilin Sandar | AppSec | `agent-juilin-sandar` (keelswell: `agent-appsec`) | `agents/custom-appsec.md` (28) | 78 | own command; party rosters | 20 / 50 / 6; security verdict (PR #13) |
| Jain Farstrider | Performance | `agent-jain-farstrider` (keelswell: `agent-performance`) | `agents/custom-performance.md` (29) | 81 | own command; party rosters | 2 / 3 / 0 |
| Basel Gill | Business ops | `agent-bizops` | `agents/custom-bizops.md` (32) | 87 | own command | 19 / 35 / 7; entity formation (PRs #3, #17, #18, #19, #35), name lockdown (PR #11), license (PR #50) |
| Talmanes Delovinde | LLM surfaces | `agent-llm` | `agents/custom-llm.md` (31) | 87 | own command | 16 / 58 / 13; LLM-surface pass (PR #9, #10) |
| Egeanin Tamarath | Mobile | `agent-mobile` | `agents/custom-mobile.md` (30) | 84 | own command | 1 / 3 / 2 |
| Aludra | Marketing | `agent-marketing` | `agents/custom-marketing.md` (30) | 81 | own command | 1 / 3 / 3 |
| Leane Sharif | Web designer | `agent-web-designer` | `agents/custom-web-designer.md` (51) | 51 | own command; pairs with Tarna | 0 / 0 / 2 (the commit adding her, PR #49) |
| Tarna Feir | Design critic | `agent-design-critic` | `agents/custom-design-critic.md` (49) | 49 | own command; pairs with Leane | 0 / 0 / 2 (PR #49) |
| Hal, Dana, Marcus, Jules (Beta League) | User-persona seats | none (party members in `_bmad/custom/bmad-party-mode.toml`) | n/a | 39 total | `bmad-party-mode` group `beta-league` | Beta League convening (PR #8), `party-mode/memories/beta-league/.memlog.md` (12 lines) |

Note on skill ids: ffbapp's install predates Keelswell 0.5.0's rename, so the nine original custom agents live under persona-named directories (`agent-tam-althor`, ...) in ffbapp and role-named directories (`agent-sre`, ...) in keelswell. Same content, different ids.

### 1c. Skills and commands

All 108 skill directories in ffbapp are user-invocable slash commands (`/<name>`). Origin: K = Keelswell-authored, V = vanilla BMAD 6.10.0 or a bundled module (bmm, cis, tea, bmb, loop), X = third party. Evidence columns are name hits (git / trg / mlog / hoff / set / mem); name hits undercount skills run under a persona (for example `bmad-prd` ran as "Egwene"), so the Observed-output column carries the artifact evidence instead.

#### Wave cycle and wrap (Keelswell-authored)

| Skill | Ver | Trigger | Inputs read (per SKILL.md) | Outputs written (per SKILL.md) | Consumed by (per SKILL.md) | Observed on ffbapp | Evidence |
|---|---|---|---|---|---|---|---|
| `bmad-create-wave` | 1.0.0 | `/bmad-create-wave` after readiness PASS | `docs/epics.md`, `docs/stories/**/*.md`, optional `docs/architecture.md`, `docs/risk-register.md` (paths that do not exist in ffbapp; real inputs live under `_bmad-output/planning-artifacts/`) | `_bmad-output/planning-artifacts/waves.md`; `--inline` appends to `docs/epics.md` | `bmad-dev-wave`, `bmad-merge-wave`, `bmad-status-wave`, `bmad-close-epic` | `waves.md` (PR #25, 2026-08-20; 20 rows; 14 amendments since, all by hand or by wrap) | 0/2/0/0/2/2 |
| `bmad-dev-wave` | 1.1.0 (ffbapp copy carries an extra Model Policy section, PR #28, absent from keelswell) | `/bmad-dev-wave <id>`; flags `--resume`, `--no-party`, `--dry-run` | `waves.md`, `core/config.yaml` parallelism (not installed), auto-memory open questions, Project Conventions Block (populated per project; ffbapp's block location OPEN VERIFY) | sibling worktree `../<project>-wave-<id>`, `.bmad/wave-<id>/checkpoint.json` and `step-N.done`, `docs/wave-<id>/test-design.md`, `docs/wave-<id>/review-party.md`, `docs/stories/`, PR | `bmad-resume-wave` (checkpoints), `bmad-merge-wave` (archive), `bmad-close-epic` (review record, stories, test designs) | 18 waves merged (PRs #29, #38, #43, #54, #60, #61, #62, #68, #70, #73, #74, #76, #78, #80, #82, #84, #85, #88); worktrees at `.claude/worktrees/<slug>-<hash>` on `claude/*` branches, never sibling dirs; checkpoint state on disk for 2 of 18 waves (2B archive, 5D steps 1-2) | 6/56/0/1/2/12 |
| `bmad-resume-wave` | 1.0.0 | `/bmad-resume-wave <id>`; `--from-step`, `--dry-run` | worktree at `../<project>-wave-<id>/`, `wave-<id>-*` branches, `.bmad/wave-<id>/`, `HANDOFF.md` Status | `.bmad/wave-<id>/resume-from-step-<N>.json`; re-dispatches `bmad-dev-wave --from-step` (a flag `bmad-dev-wave` does not define) | none reads the JSON | no `resume-from-step-*.json` anywhere; 0 hits in every evidence source | 0/0/0/0/0/0 |
| `bmad-status-wave` | 1.1.0 | `/bmad-status-wave`; `--wave`, `--only-active` | `waves.md`, sibling `<project>-wave-*` dirs, `git branch --list 'wave-*'`, `gh pr list`, `.bmad/wave-<id>/`, `HANDOFF.md`, verify-fast results | printed dashboard only | `bmad-wrap` step 2 (probe set) | 10 triage mentions; probes 2 and 3 match nothing in ffbapp's layout | 3/10/0/0/0/1 |
| `bmad-merge-wave` | 1.1.0 | `/bmad-merge-wave <id>` after PR merge | `git worktree list --porcelain`, `waves.md` suffix, `gh pr view`, `git ls-remote` | worktree and local branch removed, `.bmad/wave-<id>/archive/`, cleanup markers | `bmad-close-epic` reads the archive when present | cleanup PRs #45, #55, #81; `.bmad/wave-2B/archive/` is the only archive; 1.1.0 rewrote resolution after harness worktrees were invisible to 1.0.0 | 11/39/0/0/2/10 |
| `bmad-close-epic` | 1.2.0 | `/bmad-close-epic <N>`, no flags | `waves.md`, `gh pr view` per wave, `git worktree list`, `docs/wave-<id>/review-party.md` or api-surface amendments section, `epics.md`, story files | `_bmad-output/epic-closure/epic-<N>/{SUMMARY,code-review,testarch-trace,testarch-nfr,retrospective}.md`, `project-context.md` append, story `Status: done`, docs-only PR | `bmad-dev-wave` 1.1.0 preflight, `bmad-status-wave` closure-pending check, `bmad-wrap` step 2 | 5 closures (PRs #46, #64, #75, #89, #90); verdicts Epic 1 YELLOW (4 CONCERNS), Epic 2 YELLOW (4 CONCERNS), Epic 3 GREEN, Epic 4 YELLOW (4 CONCERNS), Epic 5 YELLOW (2 CONCERNS) | 11/13/0/2/2/6 |
| `bmad-wrap` | 1.9.0 | `/bmad-wrap` at session end; `--scope` | git state, `CLAUDE.md` (read-only), `TODO.md`, `HANDOFF.md`, `bmad-status-wave` probes, plans | `_bmad-output/session-wrap/<ts>/triage.md`, `TODO.md`, `HANDOFF.md`, auto-memory, commit plus push plus PR | `HANDOFF.md` by the next session (human paste of the kickoff prompt) | 77 triage reports 2026-08-01 to 2026-09-10 (452,186 chars); 12 wrap-only PRs (#10, #24, #27, #40, #44, #48, #50, #55, #69, #77, #79, #92) | 10/8/0/1/2/9 |

#### Agent launchers (Keelswell-authored, 25)

| Skill | Trigger | Inputs | Outputs | Consumed by | Evidence |
|---|---|---|---|---|---|
| `bmad-master` | `/bmad-master` | `_bmad/config.toml`, customize.toml | chat | none | 0/1/0/0/0/1 |
| `bmad-agent-qa` | `/bmad-agent-qa` | same | review artifacts (party) | party reviews | 0/0/0/0/0/0 |
| `bmad-agent-arch-*` (8) | `/bmad-agent-arch-<role>` | same plus per-skill assets (compliance, patterns, services YAML) | review findings in party artifacts | party reviews | all 0/0/0/0/0/0 |
| `agent-tam-althor`, `agent-tuon`, `agent-setalle-anan`, `agent-hurin`, `agent-gareth-bryne`, `agent-damer-flinn`, `agent-bayle-domon`, `agent-jain-farstrider` | `/agent-<persona>` | same | `_bmad-output/planning-artifacts/` (declared default) | party reviews | all 0 except persona hits in 1b |
| `agent-juilin-sandar` | `/agent-juilin-sandar` | same | `llm-surfaces/.../review-security-verdict.md` | epics.md inputDocuments | 0/1/0/0/0/0 |
| `agent-bizops` | `/agent-bizops` | same | `planning-artifacts/entity/*`, `name-lockdown/*`, TODO items | founder | 0/7/0/0/0/2 |
| `agent-llm` | `/agent-llm` | same | `llm-surfaces/llm-ffbapp-2026-08-11/*` (6 files) | epics.md inputDocuments | 1/2/0/0/0/4 |
| `agent-mobile` | `/agent-mobile` | same | none on ffbapp | none | 0/0/0/0/0/2 |
| `agent-marketing` | `/agent-marketing` | same | none on ffbapp | none | 0/0/0/0/0/2 |
| `agent-web-designer` | `/agent-web-designer` | same plus `design`, `artifact-design`, `dataviz` skills | none on ffbapp | `agent-design-critic` | 1/0/0/0/0/0 |
| `agent-design-critic` | `/agent-design-critic` | browser | none on ffbapp | `agent-web-designer` | 1/0/0/0/0/0 |

#### Vanilla BMAD and bundled modules (74) plus third party (1)

Inputs and outputs for rows with zero ffbapp evidence are not extracted; they were never run here.

| Skill | Origin | Observed output on ffbapp | Consumed by | Evidence |
|---|---|---|---|---|
| `bmad-brainstorming` | V (cis) | `_bmad-output/brainstorming/brainstorm-ffbapp-regrounding-2026-07-31/` (10 files) | register sources | 0/7/0/0/0/0 |
| `bmad-cis-innovation-strategy` | V (cis) | `innovation-strategy-2026-08-01.md` (PR #1) | register | 0/0/0/0/0/0 (ran as Logain) |
| `bmad-cis-storytelling` | V (cis) | `founding-narrative-2026-08-04.md` | register | 0/0/0/0/1/0 |
| `bmad-market-research` | V (bmm) | `research/market-ffbapp-exotic-league-beachhead-research-2026-08-05.md` plus 10 sample files | brief, PRD | 0/0/0/0/1/0 |
| `bmad-product-brief` | V (bmm) | `briefs/brief-ffbapp-2026-08-05/` (3 files) | PRD | 0/1/0/0/0/0 |
| `bmad-prd` | V (bmm) | `prds/prd-ffbapp-2026-08-06/` (9 files, PR #2) | epics, architecture, UX | 0/4/0/0/0/1 |
| `bmad-ux` | V (bmm) | `ux-designs/ux-ffbapp-2026-08-08/` (13 files, PR #4) | epics | 0/0/0/0/0/1 |
| `bmad-architecture` | V (bmm) | `architecture/architecture-ffbapp-2026-08-10/` (10 files, PR #6) | epics, waves, project-context | 1/24/0/0/1/1 |
| `bmad-party-mode` | V (core) | 3 keepsakes under `party-mode/`, `review-party.md` in arch reviews, `review-party-epics-waves-2026-08-20.md` (PR #32), `party-review-findings-2026-08-08.md` (PR #5); wave-level `docs/wave-*/review-party.md` (10) OPEN VERIFY whether via this skill or ad hoc dispatch inside `bmad-dev-wave` step 10 | register rows (folded findings), waves.md EW series | 0/7/0/0/1/3 |
| `bmad-create-epics-and-stories` | V (bmm) | `epics.md` (PR #20) | waves, stories, closure | 0/2/2/0/2/3 |
| `bmad-check-implementation-readiness` | V (bmm) | `implementation-readiness-report-2026-08-20.md` (PR #23) | waves.md inputDocuments | 0/4/0/0/1/2 |
| `bmad-generate-project-context` | V (bmm) | `project-context.md` (2026-08-20) | dev dispatch, closures | 2/1/0/0/1/2 |
| `bmad-create-story` | V (bmm) | `implementation-artifacts/*.md` (16 story files) | closure traceability | 5/5/0/0/0/3 |
| `bmad-code-review` | V (bmm) | `epic-closure/epic-*/code-review.md` (5) via close-epic | SUMMARY | 0/2/0/0/0/0 |
| `bmad-testarch-trace` | V (tea) | `epic-closure/epic-*/testarch-trace.md` (5) via close-epic | SUMMARY | 0/0/0/0/0/0 |
| `bmad-testarch-nfr` | V (tea) | `epic-closure/epic-*/testarch-nfr.md` (5) via close-epic | SUMMARY | 0/0/0/0/0/0 |
| `bmad-retrospective` | V (bmm, fork-recast 129 lines) | `epic-closure/epic-*/retrospective.md` (5) via close-epic | `project-context.md` | 0/0/0/0/0/0 |
| `bmad-testarch-test-design` | V (tea) | `docs/wave-*/test-design.md` (17) OPEN VERIFY whether this skill or `bmad-dev-wave` step 3's own subagent | dev dispatch, closure trace | 0/0/0/0/0/0 |
| `bmad-dev-story` | V (bmm) | none found; 2 git hits are close-epic 1.1.0 text explaining that dev-story ends stories at `review` | none | 2/0/0/0/0/1 |
| `bmad-help` | V (core) | none | none | 2/0/0/0/0/0 |
| `bmad-customize` | V (core) | none | none | 0/0/0/0/0/1 |
| `bmad-advanced-elicitation` | V (core) | none | none | 0/1/0/0/0/0 |
| `bmad-agent-analyst`, `-pm`, `-architect`, `-ux-designer`, `-dev`, `-tech-writer` | V (bmm, renamed) | persona launchers for the rows above | n/a | 0/1/0/0/1/1; 0/6/0/0/2/3; 0/4/0/0/2/0; 0/2/1/0/2/1; 0; 0 |
| `bmad-tea` | V (tea, renamed) | party reviewer | n/a | 0/1/0/0/0/1 |
| `bmad-cis-agent-*` (6) | V (cis, renamed) | persona launchers | n/a | brainstorming-coach 0/0/0/0/1/0; innovation-strategist 0/1/0/0/0/1; storyteller 0/3/0/0/1/1; other three 0 |
| `claude-md-doctor` | X (`agent-clinic/claude-md-doctor` via `skills` CLI) | skill-doctor session (branch `claude/skill-doctor-33265a`, PR #67 shipped bmad-wrap 1.9.0) | keelswell | 0/2/0/0/0/3 |
| `bmad-bmb-setup`, `bmad-agent-builder`, `bmad-module-builder`, `bmad-workflow-builder`, `bmad-eval-runner`, `bmad-forge-idea` | V (bmb) | none | none | all 0 |
| `bmad-loop-setup`, `bmad-loop-sweep`, `bmad-loop-resolve` | V (loop) | none | none | all 0 |
| `bmad-cis-design-thinking`, `bmad-cis-problem-solving` | V (cis) | none | none | 0 |
| `bmad-checkpoint-preview`, `bmad-code-review` steps, `bmad-correct-course`, `bmad-create-architecture`, `bmad-create-prd`, `bmad-edit-prd`, `bmad-validate-prd`, `bmad-dev-auto`, `bmad-document-project`, `bmad-domain-research`, `bmad-editorial-review-prose`, `bmad-editorial-review-structure`, `bmad-index-docs`, `bmad-prfaq`, `bmad-qa-generate-e2e-tests`, `bmad-quick-dev`, `bmad-review-adversarial-general`, `bmad-review-edge-case-hunter`, `bmad-shard-doc`, `bmad-spec`, `bmad-sprint-planning`, `bmad-sprint-status`, `bmad-teach-me-testing`, `bmad-technical-research`, `bmad-testarch-atdd`, `bmad-testarch-automate`, `bmad-testarch-ci`, `bmad-testarch-framework`, `bmad-testarch-test-review` | V | none | none | all 0 |

Count check: 7 wave and wrap + 25 launchers + 74 vanilla and modules + 1 third party = 107 directories under `.claude/skills`, plus the `.agents/skills/claude-md-doctor` duplicate = 108 frontmatters.

### 1d. State artifacts

| Artifact | Path | Format | Entries | Last updated | Written by | Read by |
|---|---|---|---|---|---|---|
| Settled-decisions register | `_bmad-output/settled-decisions-register-2026-08-04.md` | Markdown tables, 10 sections | 51 rows (ids 1-51; 44-51 numbered out of sequence) | 2026-09-10 `3c9dbfd` (row 51) | founder pen and stage sessions | `CLAUDE.md`, `project-context.md`, `waves.md`, `epics.md`, three wave skills (row 51 only) |
| Wave map | `_bmad-output/planning-artifacts/waves.md` | Markdown table plus amendment log | 20 wave rows (1A-6C); 14 dated amendment entries; 27 EW ids | 2026-09-10 `97976b0` | `bmad-create-wave` once (PR #25); amendments by sessions and closures | `bmad-dev-wave`, `bmad-merge-wave`, `bmad-status-wave`, `bmad-close-epic`, `bmad-create-story` |
| Epic breakdown | `_bmad-output/planning-artifacts/epics.md` | Markdown, YAML frontmatter | 30 epics, 142 stories | 2026-08-24 `7553a68` | `bmad-create-epics-and-stories` plus founder-pen folds | `waves.md`, story creation, closure traceability |
| Story files | `_bmad-output/implementation-artifacts/*.md` | Markdown, `Status:` line | 16 files (15 `done`, 6.1 `ready-for-dev`); 11 merged Phase 1 stories have no file (1.4-1.6, 3.5, 5.1-5.7) | 2026-09-10 (Epic 4 status flips) | `bmad-create-story` inside waves; `bmad-close-epic` flips status | closure traceability |
| Test designs | `docs/wave-*/test-design.md` | Markdown, YAML frontmatter | 17 (every wave dir except 3C) | 2026-09-08 (5D) | `bmad-dev-wave` step 3 subagent | dev dispatch, closure trace |
| API-surface pins | `docs/wave-*/api-surface.md` | Markdown | 12 | 2026-09-08 | wave sessions (memory: "pin the API surface before dispatch") | dev dispatch; close-epic accepts "Party-review amendments" section as a review record |
| Party review records | `docs/wave-*/review-party.md` | Markdown | 10 (1B, 1C, 2A, 2B, 2C, 3A, 3B, 3D, 3E, 5C); absent for 1A, 3C, 4A, 4B, 5A, 5B, 5D, 6A | 2026-09-05 (5C) | `bmad-dev-wave` step 10 | `bmad-close-epic` 1.2.0 preflight (prospective from 2026-09-10) |
| Epic closure reports | `_bmad-output/epic-closure/epic-{1..5}/` | 5 Markdown files each | 25 files; statuses YELLOW, YELLOW, GREEN, YELLOW, YELLOW | 2026-09-10 | `bmad-close-epic` | `bmad-dev-wave` preflight (directory presence), `bmad-status-wave`, HANDOFF |
| Wave checkpoints | `.bmad/wave-2B/archive/` (checkpoint.json plus 15 markers), `.bmad/wave-5D/checkpoint.json` (steps 1-2 only) | JSON plus empty `.done` files | 2 of 18 executed waves | 2026-09-08 | `bmad-dev-wave`, `bmad-merge-wave` | `bmad-resume-wave` (never run), `bmad-merge-wave` preflight check 6 (warn only) |
| Session wrap reports | `_bmad-output/session-wrap/<ts>/triage.md` | Markdown, YAML frontmatter | 77 (2026-08-01T07:19Z to 2026-09-10T16:59Z), 452,186 chars | 2026-09-10 | `bmad-wrap` step 5 | nothing in the framework (`bmad-wrap` itself says closure history "lives in the triage reports") |
| HANDOFF.md | `HANDOFF.md` | Markdown, state table plus kickoff block | 1 live version; PR titles number handoffs ("thirty-fifth" 2026-08-20, "forty-sixth" 2026-08-24) | 2026-09-10 `8206f7f` | `bmad-wrap` step 4; hand reconciliations (PR #71, #92) | next session (human paste), `bmad-status-wave`, `bmad-resume-wave` |
| TODO.md | `TODO.md` | Markdown list | 4 open items, all founder-side | 2026-09-10 `3c9dbfd` | `bmad-wrap` step 3 | next session |
| project-context.md | `_bmad-output/project-context.md` | Markdown, YAML frontmatter (`epic_retrospectives_folded: [1,2,3,4,5]`) | 43 rules across 7 sections | 2026-09-10 `97976b0` | `bmad-generate-project-context` once; `bmad-close-epic` step 5 appends | dev subagents (per dispatch), closures |
| Glossary | `_bmad-output/planning-artifacts/glossary.md` | Markdown | 176 lines | 2026-09-08 `a6c33ee` | sessions (abbreviation rule) | Reference key blocks |
| Gate-spec registry | `harness/gate-specs/REGISTRY.json` plus `h1-v1.json` | JSON, SHA-256 pinned | 1 spec (h1 v1, signed RQ 2026-09-03) | 2026-09-03 `f2cf9e8` | wave 6A | wave 6B (planned) |
| Memlogs | `_bmad-output/**/.memlog.md` | dated bullet log | 8 files, 586 lines | 2026-08-16 (party memory); none since dev started 2026-08-20 | planning-stage skills (`memlog.py`) | the same skill's finalize step |
| Party-mode memories | `_bmad-output/party-mode/memories/{installed,beta-league}/.memlog.md` | bullet log | 57 plus 12 lines | 2026-08-16 | `bmad-party-mode` | `bmad-party-mode` (memory = true) |
| Auto-memory (ffbapp) | `~/.claude/projects/-Users-ryanquigley-Projects-personal-ffbapp/memory/` | Markdown with frontmatter | 41 files, 39 index entries, 310,098 chars in topics | 2026-09-10 | `bmad-wrap` step 1, sessions | sessions (index auto; topics on demand) |
| Auto-memory (keelswell) | `~/.claude/projects/-Users-ryanquigley-Projects-personal-keelswell/memory/` | same | 5 files | 2026-08-25 | sessions | sessions |
| Plans | `~/.claude/plans/*.md` | Markdown | 5 files (3 ffbapp-named) | 2026-09-10 | plan mode | `bmad-wrap` step 2 |
| Transcripts | `~/.claude/projects/-Users-ryanquigley-Projects-personal-ffbapp*/**/*.jsonl` | JSONL | 87 files, 170.9 MB, 2026-08-04 to 2026-09-10 (25 main-dir, 62 worktree-dir sessions); records `message.model` (sampled: `claude-fable-5`) | 2026-09-10 | harness | nothing in the framework (`claude-md-doctor` and `skill-doctor` read them ad hoc) |
| Pull requests | GitHub `attacktheseam/ffbapp` | n/a | 95 (94 merged, 1 open) 2026-08-01 to 2026-09-10 | 2026-09-10 | sessions via `gh` | `bmad-merge-wave`, `bmad-close-epic`, `bmad-wrap` step 6 |

### 1e. Automation

| Mechanism | Where | What it does | Blocks? | Status |
|---|---|---|---|---|
| Permission allow list | `~/.claude/settings.json` | allow `Bash(git *)`; ask `Bash(git push *)` | asks on push | live |
| Permission allow list | `ffbapp/.claude/settings.local.json` | 354 accumulated allow entries: 250 Bash (many one-off curl and python literals, 6 worktree-path-specific resolver commands), 67 WebFetch domains, 12 Skill, 15 Read paths, 9 MCP tools | no | live, unpruned |
| SessionStart hook | i-have-adhd plugin `hooks.json` -> `always-on.sh` | injects the 6,848-char ADHD ruleset when `~/.claude/.i-have-adhd-always` exists | no | live since 2026-08-14 |
| Stop hook | `ffbapp/.claude/settings.local.json` -> `.claude/hooks/diff-composition-gate.sh` | prints a row-48 reminder as `systemMessage` when a diff is pending | no (`exit 0` on every path) | live since 2026-09-01 (PR #72) |
| PostToolUse em-dash scrub | `keelswell/.claude/hooks/em-dash-scrub.sh` (wired only in `templates/settings.json.template`) | exit 1 when a diff adds U+2014 | would block | unwired in keelswell and absent in ffbapp; `epics.md` carries 63 em dashes |
| SessionEnd wrap reminder | `keelswell/.claude/hooks/wrap-reminder.sh` | prints "run /bmad-wrap" | no | unwired in both repos |
| git pre-commit | `ffbapp/.git/hooks/pre-commit` (local, untracked) | gitleaks on the staged diff; blocks on a hit; `--no-verify` documented | yes | live (memory `gitleaks-test-fixture-route.md` records a real block) |
| CI | `ffbapp/.github/workflows/ci.yml` (2026-08-23 `2023795`) | `fast`: ruff check, ruff format --check, lint-imports, pytest tests/unit; `db`: postgres:18 service, makemigrations --check, migrate, check-tables, apply-roles, pytest tests/db; `smoke`: `tests/smoke/test_one_command.sh` | yes via ruleset | live |
| Branch ruleset `main` | GitHub ruleset 21312772 (active, created 2026-08-24, org `attacktheseam`) | blocks deletion and non-fast-forward; requires a pull request (0 approvals); requires status checks `fast`, `db`, `smoke`, strict; no bypass actors | yes | live (a second ruleset `deletion-and-force-push`, 2026-08-17, is disabled) |
| Local verify lanes | `Makefile` -> `tests/verify-fast.sh`, `verify-db.sh`, `verify-full.sh` | same commands as CI; `test_ci_wires_fast_suite.py` asserts the wiring | local only | live |
| Import-boundary lint | `pyproject.toml` `[tool.importlinter]` | 7 contracts encoding AD-2 and AD-18 | yes (in `fast`) | live |
| Lint rules | `pyproject.toml` `[tool.ruff.lint]` | E, F, I, S608 (string-built SQL), C901 max 22 | yes (in `fast`) | live |
| Model routing (config) | `keelswell/core/config.yaml` | tiers and role bindings | n/a | not installed in ffbapp; no reader |
| Model routing (skill text) | `ffbapp/.claude/skills/bmad-dev-wave/SKILL.md` "Model Policy" (PR #28, 2026-08-20) | dev-work subagent dispatches pass model "sonnet"; orchestrator, test-design subagent, and party reviewers stay on the session model | no (instruction) | live in ffbapp only; not in keelswell |
| Model routing (per session) | `bmad-wrap` 1.7.0 and 1.8.0 kickoff lines | suggests model, effort, run mode per next session (latest: plan, opus, high) | no (advisory) | live |
| `model` settings key | neither `settings.json` | none set | n/a | absent |
| Worktree isolation | harness `.claude/worktrees/` (Claude desktop) | one worktree per session | n/a | live; contradicts `core/config.yaml` `worktree_root: .worktrees` and the skills' sibling-dir convention |
| Wave checkpoints | `.bmad/wave-<id>/` | step markers | no | written for 2 of 18 waves |
| Repo settings | GitHub | `delete_branch_on_merge: false`, `allow_auto_merge: false` | n/a | 12 stale remote branches reported in HANDOFF |

### 1f. Contradictions and overlaps

| # | Kind | A | B | Effect |
|---|---|---|---|---|
| 1 | contradiction | `~/.claude/CLAUDE.md` (working copy) Voice: "Banned words: substrate, ..." | ffbapp ruled vocabulary: register row 10 "event substrate"; `epics.md` "## Epic 4: Event Substrate v0"; PR #80 "Wave 4B: distributional event projections"; `HANDOFF.md` uses "substrate" 20+ times; open PR #95 "Substrate exactness" | a global rule bans the project's technical term; every ffbapp session violates one or the other |
| 2 | contradiction | `~/.claude/CLAUDE.md`: "Never use em dashes in user-facing output"; `templates/CLAUDE.md.template`: "Do not use em-dashes (U+2014) ... ever" | `epics.md` (FINAL, ruled) carries 63 U+2014; `waves.md` 3; `TODO.md` 2; `project-context.md` 1; `_bmad/config.toml` descriptions (upstream) | the mechanical check that would catch this (`em-dash-scrub.sh`) is unwired |
| 3 | stale | `ffbapp/CLAUDE.md` line 3: "No production code exists yet. This repo is the planning record; code lands when wave development starts"; section "When development starts: Generate project-context.md" | `project-context.md` exists since 2026-08-20; 18 waves and 5 epic closures merged; `HANDOFF.md` reports 1,308 unit and 353 db tests | the auto-loaded project file misdescribes the repo in its first sentence, unchanged across 5 later edits |
| 4 | overlap | `ffbapp/CLAUDE.md` Standing rules: rows 36, 37, 48, 49, hands-off paths, branch rule, wrap rule | `project-context.md` Development Workflow Rules: the same seven rules restated | two copies to keep in sync; the wave subagent block carries a third |
| 5 | contradiction | `keelswell/core/config.yaml`: `forbidden_modes: [auto, bypass]` | `bmad-wrap` 1.3.0+: suggests "auto" as a run mode; `~/.claude/settings.json` configures `autoMode`; the ffbapp allow list records `Bash(cd ... memory *)` style grants typical of auto sessions | the fork's own policy file forbids a mode the fork's wrap skill recommends |
| 6 | contradiction | `core/config.yaml` model tiers `claude-opus-4-8`, `claude-sonnet-4-6`, `claude-haiku-4-5`; `role_models.coding: workhorse` | `bmad-dev-wave` (ffbapp) Model Policy "sonnet"; `bmad-wrap` "fable or opus ... name whatever tiers are current"; transcripts record `claude-fable-5` | three routing statements, no config the harness reads; the only binding one is per-session prose |
| 7 | contradiction | `bmad-dev-wave` step 2 "sibling ../<project>-wave-<id> on branch wave-<id>-<suffix>"; `bmad-status-wave` probes "sibling directories matching <project>-wave-*" and `git branch --list 'wave-*'`; `bmad-resume-wave` "worktree at ../<project>-wave-<id>/"; `core/config.yaml` `worktree_root: .worktrees` | every ffbapp wave ran in `.claude/worktrees/<slug>-<hash>` on `claude/<slug>-<hash>` (git branch list; `.bmad/wave-5D/checkpoint.json` `branch_deviation`); `bmad-merge-wave` 1.1.0 rewrote its resolution for exactly this | status-wave's worktree and branch probes match nothing; resume-wave cannot locate a wave |
| 8 | contradiction | `bmad-create-wave` inputs "docs/epics.md, docs/stories/**/*.md"; `--inline` output "docs/epics.md Appendix C"; `bmad-dev-wave` output "<worktree>/docs/stories/" | `_bmad/config.toml`: `planning_artifacts = _bmad-output/planning-artifacts`, `implementation_artifacts = _bmad-output/implementation-artifacts`; files live there | skill paths do not resolve on the install they ship with |
| 9 | contradiction | `bmad-resume-wave`: "re-dispatches /bmad-dev-wave with --from-step set" | `bmad-dev-wave` defines `--resume`, `--no-party`, `--dry-run`; no `--from-step` | the resume interface does not exist on the executor |
| 10 | gap | `bmad-dev-wave` step 9: "run tests/verify-fast.sh in the worktree" | CI requires `fast`, `db`, and `smoke`; `HANDOFF.md` kickoff: "make verify and make verify-db, plus ruff check --no-cache" | the skill's gate is weaker than the merge gate; the difference lives in the kickoff prompt |
| 11 | contradiction | `docs/upstream-refresh-runbook.md`: "_bmad/custom/config.toml overlay pins re-win ... all Wheel of Time names" | ffbapp `_bmad/custom/config.toml` is comments only; `_bmad/config.toml` `[agents.bmad-agent-analyst] name = "Mary"` and 12 more upstream names; memory `party-roster-name-mapping.md` records the mismatch surfacing in party mode | registry consumers (party rosters, help) show upstream names while skills greet as Wheel of Time |
| 12 | contradiction | i-have-adhd rule 6: "Give specific time estimates" (every response) | register row 36 and `CLAUDE.md`: "No time estimates in any recorded artifact" | reconciled only if the model separates chat from artifact text in the same turn |
| 13 | overlap | `~/.claude/CLAUDE.md` Communication Style and Voice; `settings.json` outputStyle Concise; i-have-adhd ruleset (142 lines); `templates/CLAUDE.md.template` Communication Style | four overlapping output-shape instruction sets (roughly 3,700 tokens) per session | none of them is measured; rule 9 "cap lists at 5" conflicts with wrap's 2-to-4 options plus founder action lists |
| 14 | tension | `~/.claude/CLAUDE.md`: "Don't write code until clarifying questions are resolved"; "Ask ... One at a time" | `bmad-dev-wave` step 4.5 halts for open questions; i-have-adhd: "do the work instead of asking 'want me to'"; kickoff prompts run in plan or auto mode | which rule wins is decided per turn by the model |
| 15 | drift | `CHANGELOG.md` last entry 0.8.0 (2026-08-24); `marketplace.json` version 0.8.0; README pin `@v0.8.0` | `skills/bmad-wrap` 1.9.0 (2026-08-31 `f2b86a1`), `bmad-dev-wave` 1.1.0, `bmad-close-epic` 1.2.0, `bmad-status-wave` 1.1.0 (2026-09-10 `d42fc6e`, `1b75454`, `1899f35`) | a fresh install at the documented pin does not carry the row 51 gates |
| 16 | drift | memory `keelswell-skill-sync.md` and `HANDOFF.md`: "skill fixes must also ride back to keelswell in both its skills/ and .claude/skills/ trees" | ffbapp `bmad-dev-wave` Model Policy (PR #28, 2026-08-20) is absent from both keelswell trees; keelswell `.agents/skills` frozen pre-v0.3.0 while `.claude/skills` is current | three copies of each wave skill, two of them behind |
| 17 | stale | `bmad-close-epic` 1.2.0 and `project-context.md`: "Waves 4A and 4B are the only waves since 1B with no review-party.md" | `docs/wave-*/review-party.md` absent for 1A, 3C, 4A, 4B, 5A, 5B, 5D, 6A (8 of 18); close-epic's own list names 1A, 3C, 4A, 4B, 5A, 5B, 6A and accepts 5C and 5D via api-surface sections | two counts of the same gap in two ruled texts |
| 18 | contradiction | `bmad-wrap` step 1: "CLAUDE.md additions are hard-capped at ZERO per session" | `ffbapp/CLAUDE.md` changed in 6 commits between 2026-08-20 and 2026-09-01; every triage report records `claude_md_edits: 0` | the cap governs one write path; founder-pen commits are the other, and nothing scans those for the four checks |
| 19 | unresolved reference | `core/config.yaml` "see Chapter 29", "28.4.3"; `bmad-create-wave` "manual Part 5"; runbook "keelswell-manual repo, quickstart/trackF6-findings-v1.md" | no manual in either repo; `~/Documents/Training/Keelswell` absent on this machine | instructions point at text the model cannot read |
| 20 | unresolved reference | `templates/settings.json.template` `mcpServers.keelswell.command = "keelswell-mcp"` | binary not on PATH; no source in the repo | a fresh install from the template would fail to start the server |

### 1g. Totals loaded into a fresh ffbapp session

| Tier | What | Files | Lines | Chars | ~Tokens |
|---|---|---|---|---|---|
| Auto-injected before the first turn | `~/.claude/CLAUDE.md` + `filesystem.md`; `ffbapp/CLAUDE.md`; i-have-adhd ruleset (hook); ffbapp `MEMORY.md` index; 108 skill frontmatters (name plus description) | 5 + 108 | 83 + 17 + 38 + 142 + 41 | 7,668 + 4,104 + 6,650 + 9,137 + 27,903 = 55,462 | 13,870 |
| Mandated by `ffbapp/CLAUDE.md` ("Read first, every session") | `HANDOFF.md`, `TODO.md` | 2 | 98 | 29,800 | 7,450 |
| Typical kickoff reads (the 2026-09-10 prompt names these) | `project-context.md`, `waves.md`, two closure reports (`epic-4/code-review.md`, `testarch-nfr.md` OPEN VERIFY sizes) | 4 | 317+ | 94,710 + closure files | 23,700 + |
| Register when consulted (CLAUDE.md: "check it before you propose anything") | `settled-decisions-register-2026-08-04.md` | 1 | 164 | 42,847 | 10,710 |
| Subtotal before any work on a wave | | 12 + 108 frontmatters | ~760 | ~222,800 | ~55,700 |
| Not counted: harness system prompt, `settings.local.json` (consumed, not injected), plugin and global skill descriptions outside Keelswell (asd-ste100, skill-doctor, claude-api, engineering and productivity plugins), the kickoff prompt itself (~5,800 chars, ~1,450 tokens) | | | | | |

Skill bodies are loaded on invocation: the seven wave skills total 48,268 chars (~12,070 tokens); all 107 bodies total 760,376 chars (~190,000 tokens).

### Keelswell deviations from vanilla BMAD-METHOD 6.10.0

Baseline: keelswell commit `28d731b` "chore: vanilla BMAD substrate (core, bmm, bmb, cis, tea, loop)", 74 skill directories. HEAD has 106.

| # | Deviation | Kind | Evidence | Status | On ffbapp |
|---|---|---|---|---|---|
| D1 | Seven wave skills: `bmad-create-wave`, `bmad-dev-wave`, `bmad-resume-wave`, `bmad-status-wave`, `bmad-merge-wave`, `bmad-close-epic`, `bmad-wrap` | skills added | absent at `28d731b`; added `1a421d8` (2026-07-17); versions now 1.0.0, 1.1.0, 1.0.0, 1.1.0, 1.1.0, 1.2.0, 1.9.0 | VERIFIED | installed; 5 of 7 have run |
| D2 | Eight Architecture Expansion Pack agents as skills (`bmad-agent-arch-*`) | agents added (ported from a community pack, not vanilla core) | `5207df0` (2026-07-14), PR #1 | VERIFIED | installed; party reviewers only |
| D3 | Fifteen custom agents (`agent-*`) | agents added | `694faad` (6, 2026-07-17), `ccecf77` (3, v0.2.0), `e29dea1` (4, v0.7.0), `dae5c53` (2, v0.8.0) | VERIFIED | installed under pre-0.5.0 persona ids for the first nine |
| D4 | `bmad-master` and `bmad-agent-qa` launcher skills for carried personas | skills added | `ccecf77` v0.2.0 | VERIFIED | installed; 0 evidence of use |
| D5 | Thirteen vanilla personas renamed to Wheel of Time names (SKILL.md, customize.toml, agents/, manifests) | persona edit | `c903f66` v0.3.0; diff `28d731b..HEAD` touches 13 SKILL.md and 9 customize.toml under upstream ids | VERIFIED | installed |
| D6 | Character-voice rewrites of nine core agents' `communication_style` (v0.6.0) and Min's anchor fix (v0.7.1) | persona edit | `c820352`, `310fc0b` | VERIFIED | installed |
| D7 | `bmad-retrospective` scripted dialog recast Amelia to Mat Cauthon | upstream skill edit | 129 lines changed since `28d731b`; shipped via marketplace so it survives refresh | VERIFIED | installed; runs inside close-epic |
| D8 | `core/config.yaml` operational defaults (model tiers, role models, permissions, parallelism, context) | config added | `f999e39` | VERIFIED present | not installed; no reader |
| D9 | `config/agent-names.yaml` roster with install-time override | config added | `ae06d47` | VERIFIED | consumed at install |
| D10 | Project templates (CLAUDE.md, HANDOFF, TODO, settings.json, .gitignore) and `install.sh` six-phase installer | tooling added | `f999e39`, `ae06d47` | VERIFIED present | CLAUDE.md and settings templates unused; HANDOFF shape loosely followed; TODO buckets unused; install.sh run OPEN VERIFY |
| D11 | Hooks `em-dash-scrub.sh`, `wrap-reminder.sh` | hooks added | `f999e39` | VERIFIED present | absent; unwired even in keelswell |
| D12 | `module.yaml` custom-module descriptor and `.claude-plugin/marketplace.json` | packaging | `76fdcb9` v0.4.0, `0a4b920` | VERIFIED | installer consumed them (manifest records keelswell module) |
| D13 | Workflow: wave cycle (create, dev, merge, close) replaces vanilla's `sprint-planning`, `sprint-status`, `dev-story`, `code-review` loop; epic closure gate wraps four upstream skills; wrap protocol writes HANDOFF, TODO, kickoff prompt | workflow change | skill texts; vanilla loop skills still installed with 0 ffbapp evidence | VERIFIED | in use |
| D14 | Register row 51 gates: closure-pending refusal in dev-wave, required review record in close-epic, status-wave alignment | workflow change (2026-09-10) | `d42fc6e`, `1b75454`, `1899f35`; ffbapp PRs #93, #94 | VERIFIED | installed today; untested by any wave yet |
| D15 | Model Policy section in `bmad-dev-wave` (sonnet for dev dispatch) | ffbapp-only skill edit | ffbapp PR #28 `2026-08-20`; 7-line diff against keelswell | VERIFIED | ffbapp only |
| D16 | Beta League party panel (4 user-persona seats) | ffbapp-only config | `769c99d` | VERIFIED | ffbapp only |
| D17 | `.agents/skills` cross-tool tree kept, frozen pre-v0.3.0 | packaging | runbook; 74 dirs at HEAD | VERIFIED present | not present in ffbapp (only `claude-md-doctor`); whether Claude Code reads it OPEN VERIFY |
| D18 | Keelswell manual ("Part 5", "Chapter 29", "28.4.3", keelswell-manual repo) | documentation referenced | cited by `core/config.yaml`, `bmad-create-wave`, runbook | OPEN VERIFY (not in either repo, not on disk) | n/a |
| D19 | `keelswell-mcp` MCP server | tooling referenced | `templates/settings.json.template` | OPEN VERIFY (no binary, no source) | n/a |

---

## Phase 2: Evidence of use

### Conventions found before computing anything

| Unit | How it shows up | Reliable for metrics? | Evidence |
|---|---|---|---|
| Wave | Pull request title `Wave <id>: ...` (18 of 18 waves); `docs/wave-<id>/` directory (18); branch name free-form: harness `claude/<slug>-<hash>` for 14 waves, hand-named (`wave-3d-compiler`, `wave-1c-platform-rails`, `claude/wave-2b-founder-league`, `claude/wave-5c-assembly`) for 4; worktree under `.claude/worktrees/` for 15 waves, the main checkout on a feature branch for 1A, 2C, 5C; `.bmad/wave-<id>/` for 2 | yes, via PR titles; PR #45 "Wave 1C merge cleanup" also matches and is excluded | `gh pr list` (95 PRs); `git worktree list` in session transcripts |
| Epic | Closure PR title `Epic <N> closure: ...` (#46, #64, #75, #89, #90; #91 recovered #90's content); `_bmad-output/epic-closure/epic-<N>/` | yes | PR list; tree |
| Story | `Story n.m` commit subjects on 16 of 331 non-merge commits; 16 story files for 30 stories | no; per-story attribution is not recoverable from git | `git log --no-merges --format=%s` |
| Session | One transcript directory per worktree slug (87 `.jsonl`, 8 of them resumed continuations of another file); `_bmad-output/session-wrap/<UTC>/triage.md` (77); `HANDOFF.md` commits (44); commit subjects prefixed `wrap`/`Wrap` (40) or `Session wrap:` (15) | yes with transcripts (`gitBranch`, `customTitle`, `pr-link` records); not from git alone | `~/.claude/projects/-Users-ryanquigley-Projects-personal-ffbapp*` |
| Commit subjects | free-text 209 of 331; prefixed: wrap 40, Wave 31, docs 22, Story 16, fix 7, feat 7, chore 4 | no fix/rework convention; rework computed by subject regex plus file overlap | same |
| Direct commits to main | 58, all on or before 2026-08-13 (planning phase); PR-only since, ruleset enforced since 2026-08-24 | n/a | `git log --first-parent main` |
| Tags | none | n/a | `git tag` |
| Cost | every assistant turn in every transcript carries `message.usage` (input, output, cache read, cache creation); no artifact, skill, or report reads it; no dollar figure recorded anywhere | computable per session and per wave; never computed by the framework | transcripts |
| Model and effort | every assistant turn carries `message.model`; every record carries `effort` | yes | transcripts |

Wave to session mapping used below: 1A main checkout 2026-08-20; 1B `inspiring-haibt-eb231f`; 1C `wave-1c-execution-c6deb9`; 2A `wave-2a-execution-58496f`; 3A `story-3-1-founder-amendment-c75c49`; 2B `wave-2b-founder-league-3e7aad`; 2C main checkout 2026-08-28; 3D `funny-villani-7c12e4`; 3B `wave-3b-reconciliation-dna-81dd71`; 3E `wave-3e-reconciliation-f40891`; 3C `wave-3c-h2-regression-1ff6fa`; 4A `blissful-hypatia-2792d8`; 6A `fervent-sammet-79504e`; 4B `wave-4b-model-backtest-839325`; 5A `serene-moore-8b1d21`; 5B `wave-5b-discovery-weights-0e0d1a` (2026-09-04 file); 5C main checkout 2026-09-05; 5D `wave-5d-categories-exposure-ddd660`.

### 2a. Component usage

Labels: LOAD-BEARING = output consumed downstream and changed code or a decision; USED = invoked, removal would not change the result; CEREMONY = artifacts nothing consumed; DEAD = never invoked on ffbapp.

#### Agents

| Agent | Class | Evidence |
|---|---|---|
| Egwene (pm) | LOAD-BEARING | PRD (PR #2) and epics (PR #20) are inputs to every wave dispatch prompt (`epics.md` present in 14 of 18 waves' dispatch prompts); readiness check (PR #23); 4 activations in transcripts |
| Perrin (architect) | LOAD-BEARING | spine (PR #6) became `pyproject.toml` import-linter contracts (7, labelled AD-2/AD-18) and 39 AD citations in `project-context.md`; 3 activations |
| Min (ux-designer) | LOAD-BEARING | content standard v1.4 binds copy rules in `project-context.md` (CS-6) and wave 5D's fragment work; 3 activations |
| Moiraine (analyst) | LOAD-BEARING | brief and market research produced register rows 45, 46, 47 (H4 definition, verdict, pricing); row 45 is cited from 5 code files |
| Logain (innovation strategist) | LOAD-BEARING | innovation strategy (PR #1) is the source of register rows 11 to 16; row 14 and 16 are cited from 4 and 13 code files |
| Siuan (brainstorming coach) | LOAD-BEARING | brainstorm canon is the source of register rows 1 to 10; activated in the first session (`60f3ced`) |
| Basel Gill (bizops) | LOAD-BEARING (business, not code) | 5 sessions; LLC formed 2026-08-13, trademark filed 2026-08-27, license filed 2026-08-25 (PRs #3, #11, #17, #18, #19, #35, #50); no code effect |
| Talmanes (llm) | USED | LLM-surface pass (PR #9) is an `epics.md` input document; Phase 1 builds no LLM surface; 2 sessions |
| Juilin (appsec) | USED | security verdict (PR #13) folded as spine r4 (PR #14); named in 1B and 5D review dispatch prompts; no wave finding is attributed to him in any artifact |
| Thom (storyteller) | USED | founding narrative is register rows 25, 26; nothing downstream of the register reads it (row 25 has one build-phase reader, a triage report) |
| Nynaeve (design-thinking coach) | USED | one fold, the Beta League panel (`_bmad/custom/bmad-party-mode.toml` header) |
| Aviendha (qa) | USED | never invoked as a skill; the name appears in 3 test-design dispatch prompts (1A, 5B, 5D) as the persona wrapper on the `bmad-dev-wave` step 3 subagent; the other 14 test designs were dispatched without a persona name |
| Galad (tea) | USED | party reviewer in PRD and LLM-surface reviews (11 files); named in the epics-and-waves review dispatch (2 prompts); never in a wave |
| Verin, Elayne, Cadsuane, Androl, Rhuarc, Berelain, Lan, Sorilea (arch 8) | USED | party reviewers in PRD, architecture, LLM-surface, and epics reviews (67 + 21 + 14 findings folded by founder ruling, PRs #5, #7, #32); in waves, reviewers are dispatched by domain ("security review", "platform review", "cost review") and only 1B (Rhuarc, Berelain, Juilin) and 5D (Lan, Juilin) name a persona; no wave finding is attributed to a persona in any `review-party.md` (0 name hits across 44 files) |
| Setalle, Hurin, Damer Flinn, Gareth Bryne, Bayle Domon, Tuon, Tam al'Thor, Jain Farstrider, Birgitte, Morgase, Loial | USED | party reviewers during planning only (1 to 28 artifact hits each); never activated as skills; never in a wave |
| Mat Cauthon (dev) | USED | named once (epics-and-waves review dispatch); the 39 implementation dispatches carry no persona; his skill was never activated |
| Egeanin (mobile), Aludra (marketing) | USED | one appearance each, the epics-and-waves party review; skills never activated |
| Rand al'Thor (bmad-master) | DEAD | 0 hits in artifacts, git log, transcripts (`Skill(bmad-master)` never called; `resolve_customization --skill bmad-master` never run) |
| Leane Sharif (web-designer), Tarna Feir (design-critic) | DEAD | added PR #49 (2026-08-25); 0 activations; Phase 1 has no UI |
| Hal, Dana, Marcus, Jules (Beta League) | LOAD-BEARING once | one convening (PR #8) folded CAB-14 and CAB-15 into the content standard; not convened since 2026-08-11 |

#### Skills

| Skill | Class | Evidence |
|---|---|---|
| `bmad-dev-wave` | LOAD-BEARING | 18 waves, 18 merged PRs; its step 3 test design and the api-surface pin are present in the implementation dispatch prompt of 17 and 15 waves respectively (dispatch-prompt scan); `project-context.md` in 12 |
| `bmad-close-epic` | LOAD-BEARING | 5 closures; Epic 2 code-review findings 1 and 3 became fix PR #65 (`0a1b5fd`); retrospectives folded 17 testing and workflow rules into `project-context.md` (`epic_retrospectives_folded: [1..5]`); the Epic 4 skip (found 2026-09-10) is the counter-evidence: nothing enforced the gate until row 51 |
| `bmad-wrap` | LOAD-BEARING | 77 runs; the kickoff block it writes into `HANDOFF.md` was the verbatim first prompt of 22 of the 52 sessions since 2026-08-20, including all 18 wave sessions (transcript first-prompt match); its `TODO.md` and `HANDOFF.md` reconciliations are the only cross-session state the framework has |
| `bmad-create-wave` | LOAD-BEARING | one run (PR #25); `waves.md` is read by every wave kickoff and 13 waves' dispatch prompts; 14 dated amendments since, all by hand or by wrap, none by the skill |
| `bmad-merge-wave` | USED | 1.0.0 matched nothing on harness worktrees (found at Epic 1 closure, `4a942ac`); 1.1.0 confirmed on wave 2A (PR #55); cleanup was otherwise manual (PRs #45, #81, the 2026-09-08 sweep session ran `git worktree remove` directly); its archive was written once (`.bmad/wave-2B/archive/`) and no consumer requires it |
| `bmad-status-wave` | USED | 10 triage mentions; prints only; probes 2 and 3 (`../<project>-wave-*`, `wave-*` branches) match nothing in this repo's layout, so its dashboard never reflected a real wave; the closure-pending check it now carries (1.1.0) has not run on a wave yet |
| `bmad-resume-wave` | DEAD | 0 invocations; no `resume-from-step-*.json` ever written; 2 of 18 waves left a checkpoint for it to read |
| `bmad-party-mode` | LOAD-BEARING (planning) | 4 sessions; 102 findings across PRs #5, #7, #32 folded by founder ruling into ruled documents; wave-level party reviews (10 `review-party.md`) were dispatched directly from `bmad-dev-wave` step 10 as domain reviewers, not through this skill (0 `Skill(bmad-party-mode)` calls in wave sessions) |
| `bmad-prd`, `bmad-architecture`, `bmad-ux`, `bmad-create-epics-and-stories`, `bmad-product-brief`, `bmad-market-research`, `bmad-cis-innovation-strategy`, `bmad-brainstorming` | LOAD-BEARING | each produced a ruled document that later dispatch prompts or register rows cite (see the agent rows above) |
| `bmad-generate-project-context` | LOAD-BEARING | one run (2026-08-20); the file rides in 12 waves' dispatch prompts and every closure appends to it |
| `bmad-create-story` | USED | 16 story files; dispatch prompts reference a story file in 13 waves; 11 merged stories have no file and the closure gate accepts that (`bmad-close-epic` 1.1.0) |
| `bmad-code-review`, `bmad-testarch-trace`, `bmad-testarch-nfr`, `bmad-retrospective` | LOAD-BEARING via close-epic | 5 report sets; the code-review pass produced fix PR #65 and the substrate re-measurement that drives open PR #95; retrospectives produced the 17 folded rules |
| `bmad-testarch-test-design` | DEAD as a skill | 17 test designs exist, all written by `bmad-dev-wave` step 3 dispatches ("Wave 5D test design", "Wave 1B test design" in transcripts), never by invoking this skill |
| `bmad-check-implementation-readiness` | USED | one run, verdict READY (PR #23); listed as a `waves.md` input; changed nothing |
| `bmad-cis-storytelling` | USED | narrative is register canon with one downstream reader |
| `bmad-customize` | USED | 2 sessions; produced the Beta League panel toml |
| `bmad-help`, `bmad-advanced-elicitation` | USED | 2 and 1 mentions; no artifact |
| `claude-md-doctor` (third party) | LOAD-BEARING for the framework | one session (`claude/skill-doctor-33265a`) produced bmad-wrap 1.9.0's worktree preflight (PR #67) |
| `agent-bizops`, `agent-llm`, `agent-juilin-sandar` | see agent rows | 5, 2, 1 sessions |
| `bmad-agent-pm`, `-architect`, `-ux-designer`, `-analyst`, `bmad-cis-agent-brainstorming-coach`, `-innovation-strategist`, `-storyteller` | USED (launchers) | activation evidence in transcripts (`resolve_customization.py --key agent`) |
| `bmad-dev-story`, `bmad-sprint-planning`, `bmad-sprint-status`, `bmad-quick-dev`, `bmad-dev-auto`, `bmad-correct-course` (vanilla dev loop) | DEAD | 0 invocations; the wave cycle replaced them; still installed and listed in every session's skill roster |
| `bmad-master`, `bmad-agent-qa`, `bmad-agent-dev`, `bmad-agent-tech-writer`, `bmad-tea`, 8 `bmad-agent-arch-*`, 12 other `agent-*` launchers | DEAD as skills | 0 `Skill(...)` calls and 0 resolver activations in 87 transcripts (persona names reached dispatch prompts by text, not by skill) |
| remaining 44 vanilla and module skills (`bmad-bmb-*`, `bmad-loop-*`, `bmad-testarch-*` except the two above, `bmad-cis-*` workflows except innovation and storytelling, `bmad-editorial-*`, `bmad-document-project`, `bmad-domain-research`, `bmad-prfaq`, `bmad-shard-doc`, `bmad-spec`, `bmad-index-docs`, `bmad-workflow-builder`, `bmad-module-builder`, `bmad-eval-runner`, `bmad-forge-idea`, `bmad-teach-me-testing`, `bmad-technical-research`, `bmad-review-*`, `bmad-checkpoint-preview`, `bmad-create-architecture`, `bmad-create-prd`, `bmad-edit-prd`, `bmad-validate-prd`, `bmad-qa-generate-e2e-tests`, `bmad-cis-agent-*` launchers not listed above) | DEAD | 0 evidence in git, triage, memlog, HANDOFF, settings, memory, transcripts |

Count: LOAD-BEARING 17 skills, USED 15, DEAD 76 of 108 (70%).

#### State artifacts

| Artifact | Class | Evidence |
|---|---|---|
| Settled-decisions register | LOAD-BEARING | 10 rows cited from code (`ffbapp/platform/config.py` rows 14, 15, 44, 47; `launcher.py` row 16; `classification.py` row 45), 38 rows cited by build-phase artifacts, row 51 wired into 3 skills |
| `waves.md` | LOAD-BEARING | in 13 waves' dispatch prompts; 14 dated amendments carry deferred findings to later waves; read by close-epic preflight |
| `epics.md` | LOAD-BEARING | in 14 waves' dispatch prompts; the traceability pass reads its acceptance clauses |
| `HANDOFF.md` kickoff block | LOAD-BEARING | verbatim first prompt of 22 sessions; see 2c for fidelity |
| `HANDOFF.md` state table | USED | read by humans; its epic-closure status was silent when Epic 4 went unclosed (2c, K2) |
| `TODO.md` | USED | 4 founder items; no engineering reader |
| `project-context.md` | LOAD-BEARING | in 12 waves' dispatch prompts; 17 rules folded from closures; the wave 5D reviewer brief ("measure fixture reach") came from it |
| Test designs (`docs/wave-*/test-design.md`) | LOAD-BEARING | in 17 waves' implementation or ATDD dispatch prompts; 5B's and 5D's designs surfaced 8 founder forks before code |
| API-surface pins | LOAD-BEARING | in 15 waves' dispatch prompts; accepted as a review record by close-epic 1.2.0 for 2B, 5C, 5D |
| `review-party.md` (10) | LOAD-BEARING from 2026-09-10, CEREMONY before | findings were remediated in-session (dispatch "Remediate party-review findings" in 2A, 3B, 4B, 5C, 5D) so the file changed code; but 8 waves have none, and until row 51 no reader required it; Epic 5's closure read 5C's record and folded its lesson one epic late |
| Epic closure reports | LOAD-BEARING | fix PR #65; 17 folded rules; open PR #95 |
| Story files | USED | 16 of 30; read by dispatches when present; closure accepts absence |
| `.bmad/wave-*` checkpoints | CEREMONY | 2 of 18 waves; sole reader (`bmad-resume-wave`) never ran; merge-wave check 6 only warns |
| `session-wrap/*/triage.md` (77, 452 KB) | CEREMONY (write-only) | no skill, hook, or kickoff reads one; `bmad-wrap` itself says closure history lives there; the only readers found are `grep` runs in this review |
| Memlogs (8) | CEREMONY | stopped 2026-08-16; read only by the producing skill's own finalize step |
| Party memories | USED | `memory = true` panel; 2 files |
| Auto-memory (41 files) | LOAD-BEARING | `MEMORY.md` auto-loaded; kickoff prompts cite memory-derived routes (`ruff check --no-cache`, verify from the worktree); `bmad-dev-wave` step 4.5 reads it for open questions |
| Glossary | USED | Reference key blocks cite it; no machine reader |
| Gate-spec registry | USED until 6B | hash-pinned by 6A; consumer wave not started |
| Plans (`~/.claude/plans`) | USED | plan-mode approvals in 5D and the closure session (transcript "User has approved your plan") |
| Transcripts | USED once | read by the skill-doctor session; never by the framework |

### 2b. Wave metrics

Source: `git log` on `main` (first-parent merges), PR metadata, `git grep -c 'def test_'` per commit, GitHub check-runs per commit, transcripts for the session columns. "Rework (window)" = commits merged to main after the wave and before the second following wave whose subject matches fix/revert/redo/correct/repair/regression and which touch a code file the wave touched. "Rework (strict)" = the same, counting only commits inside the next two wave PRs. Token columns are output tokens, in thousands; input tokens (99% cache reads) in millions.

| Wave | PR | Merged | Session model / effort | Commits | Files (code) | Test files | Test fns added (total) | Lines +/- | Rework win/strict | CI at merge (fast, db, smoke) | Orch code edits / sub code edits | Subagents | Human turns | Questions to RQ | Orch out k / Sub out k | Input M (orch+sub) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1A | 29 | 08-20 | fable-5 / max | 6 | 50 (39) | 7 | 11 (11) | 1585/16 | 0/0 | pass, n/a (lane added in 1B), pass | 9 / 39 | 6 | 7 | 2 | 481 / 192 | 95 |
| 1B | 38 | 08-24 | opus-5 / max | 4 | 42 (34) | 15 | 93 (104) | 3584/31 | 0/0 | pass, pass, pass | 15 / 33 | 7 | 9 | 1 | 423 / 433 | 145 |
| 1C | 43 | 08-24 | opus-5 / medium | 6 | 45 (40) | 19 | 124 (228) | 3457/30 | 0/0 | pass, pass, pass | 81 / 0 | 3 (reviews only) | 8 | 1 | 325 / 91 | 111 |
| 2A | 54 | 08-26 | opus-5 / medium | 5 | 46 (36) | 18 | 156 (384) | 7137/39 | 0/0 | pass, pass, pass | 5 / 205 | 12 | 11 | 4 | 352 / 651 | 311 |
| 3A | 60 | 08-27 | fable-5 / high | 5 | 17 (9) | 6 | 56 (440) | 2423/46 | 0/0 | pass, pass, pass | 5 / 48 | 7 | 11 | 0 | 236 / 54 | 88 |
| 2B | 61 | 08-28 | fable-5 / high | 3 | 54 (46) | 34 | 126 (566) | 6857/49 | 1/0 (`b396d70` WAIVER fix, PR #63) | pass, pass, pass | 7 / 127 | 6 | 7 | 0 | 427 / 86 | 500 |
| 2C | 62 | 08-28 | fable-5 + opus-4-8 / high | 9 | 799 (790, fixtures) | 48 | 124 (693) | 8121/28 | 2/1 (`0a1b5fd` Epic 2 findings PR #65; `fd5bb02` MFL rate-parse in wave 3B) | pass, pass, pass | 12 / 145 | 8 | 12 | 0 | 664 / 126 | 639 |
| 3D | 68 | 09-01 | sonnet-5 / high | 3 | 18 (13) | 10 | 36 (730) | 1470/1 | 0/0 | pass, pass, pass | 5 / 21 | 6 | 7 | 6 | 292 / 209 | 121 |
| 3B | 70 | 09-01 | opus-5 / high | 4 | 32 (22) | 12 | 96 (826) | 4679/78 | 0/0 | pass, pass, pass | 0 / 102 | 7 | 8 | 13 | 482 / 740 | 427 |
| 3E | 73 | 09-02 | opus-5 / high | 20 | 56 (47) | 31 | 183 (1009) | 8611/98 | 0/0 | pass, pass, pass | 0 / 203 | 9 | 8 | 6 | 748 / 1026 | 763 |
| 3C | 74 | 09-02 | sonnet-5 / medium | 2 | 14 (9) | 9 | 2 (1011) | 1272/41 | 0/0 | pass, pass, pass | 0 / 29 | 3 (no review) | 6 | 4 | 131 / 188 | 105 |
| 4A | 76 | 09-03 | sonnet-5 / medium | 1 | 11 (9) | 6 | 31 (1042) | 1035/28 | 0/0 | pass, pass, pass | 1 / 22 | 4 | 7 | 1 | 190 / 106 | 92 |
| 6A | 78 | 09-03 | sonnet-5 / medium | 1 | 16 (9) | 7 | 52 (1094) | 1733/1 | 0/0 | pass, pass, pass | 4 / 11 | 5 | 8 | 24 | 272 / 67 | 72 |
| 4B | 80 | 09-03 | sonnet-5 / high | 4 | 43 (36) | 25 | 99 (1193) | 4068/106 | 0/0 in window; substrate defect found 2026-09-08 by 5D review, fix in open PR #95 | pass, pass, pass | 0 / 95 | 8 | 8 | 3 | 296 / 524 | 314 |
| 5A | 82 | 09-04 | sonnet-5 / high | 6 | 34 (28) | 10 | 54 (1247) | 4003/41 | 0/0 | pass, pass, pass | 51 / 40 | 8 | 12 | 4 | 452 / 374 | 316 |
| 5B | 84 | 09-05 | sonnet-5 / high | 4 | 29 (25) | 14 | 31 (1298) | 2260/108 | 0/0 | pass, pass, pass | 7 / 57 | 6 | 4 | 5 | 213 / 334 | 218 |
| 5C | 85 | 09-07 | fable-5-1 / high | 4 | 17 (10) | 8 | 53 (1351) | 4159/38 | 0/0 | pass, pass, pass | 0 / 86 | 7 | 8 | 0 | 581 / 399 | 221 |
| 5D | 88 | 09-10 | opus-5 / high | 7 | 18 (11) | 8 | 85 (1440) | 4052/28 | 0/0 | pass, pass, pass | 0 / 58 | 9 | 10 | 15 | 511 / 382 | 316 |
| Total 18 waves | | 08-20 to 09-10 | | 94 | 1341 (1213) | 287 | 1412 (1440 test fns; 1308 unit + 353 db collected at HEAD) | 70,506/827 | 3 window commits over 2 waves (11%); 1 strict (6%); 1 out-of-window defect | 54 of 54 lanes green at merge; 54 of 54 at PR head | 202 / 1270 | 121 | 151 | 89 | 8,076 / 6,082 | 4,854 |

Closures for comparison: Epic 1 (opus-5, 273k out, 0 subagents), Epic 2 (opus-5, 142k), Epic 3 (sonnet-5, 58k + 53k), Epics 4 and 5 together (opus-5, 551k + 4k, 8 human turns, 6 questions). Whole project since 2026-08-01: orchestrator output 28.7M tokens, subagent output 7.7M, input 7.9 billion (7.4 billion cache reads); no session, wrap, or closure ever reported a figure from these logs.

### 2c. Kickoff fidelity

The five most recent wrap-generated kickoff prompts (fenced block in `HANDOFF.md` at the wrap commit), each checked against the repo at that commit and against the transcript of the session that consumed it. The 2026-09-10 hand reconciliation (`8206f7f`, 11 minutes after the wrap) is listed separately because it corrected the wrap's own claim.

| Kickoff (commit, written) | Consumed by | Claims checked | Wrong | Unverifiable | Wrong or unverifiable claims |
|---|---|---|---|---|---|
| K5 `9c4bb95` 2026-09-04T19:03 PDT (wave 5C) | 5C session, 2026-09-05T02:05Z, first prompt verbatim | 11 (dependency edge text, scope-note quote, UJ-2 clause in story 5.5, row 60 attributes x5, 9 read-first paths, 5A worktree and branch state, 5B worktree and PR #84 state) | 0 | 0 | none |
| K4 `6f901cf` 2026-09-06T14:28 PDT (sweep plus first-down) | 2026-09-08T19:38Z session, first prompt verbatim | 22 (PRs #82 to #86 states, 5 worktree paths, 6 branch names, 11 read-first paths, count pin 26, `"1D"` code, 2026-09-05 waves.md entry, `bonus_fd_*` keys) | 1: worktree `.claude/worktrees/wave-5c-assembly` never existed; the 5C session ran in the main checkout on branch `claude/wave-5c-assembly` (transcript dir is the main project; the 2026-09-08 `git worktree list` shows no such path; the sweep deleted the branch without a worktree) | 2: branch `claude/wave-5a-dev-83f99d` existence at write time (its worktree was already detached on 2026-09-08); Sleeper league URL reachable login-free (external) | also unexecutable as written: it told the session to remove `wave-5b-discovery-weights-0e0d1a`, the worktree the harness then started the session inside |
| K3 `7d039be` 2026-09-08T13:02 PDT (wave 5D) | 5D session, 2026-09-08T21:47Z, first prompt verbatim | 17 (PR #87, first-down worktree and branch, 8 read-first paths, section 7 of 5C's test design, `PricedEventTrace` and `TendencyContribution` in 5C's pin, row 61, terminal wave, two carry-forwards, 2026-09-05 entry) | 1: "stories 5.6 and 5.7, parallel"; `waves.md` line 61 rules serial; RQ re-ruled serial in session and `.bmad/wave-5D/checkpoint.json` records "HANDOFF.md and the kickoff prompt said parallel, which was drift" | 1: "survived three sweeps" (count not recoverable) | the session also did not create the worktree the skill and prompt direct; RQ ruled to use the harness worktree (checkpoint `branch_deviation`) |
| K2 `4d546f0` 2026-09-09T22:11 PDT (Epic 5 closure) | closure session, 2026-09-10T14:43Z, first prompt verbatim | 15 (PR #88, 5D worktree and branch, 5B worktree, stale branches 4A and 6A, all Epic 5 waves merged, 8 read-first paths, Party-review amendments sections in 5C and 5D pins, the 2026-09-08 entry and its "five tests", three carry-forwards) | 1 by omission: `HANDOFF.md` at this commit contains no statement about Epic 4's closure status; Epic 4 had been closure-pending since 2026-09-03 and the session discovered it (`epic-closure-gate-skip-detection.md`) | 1: "now five sweeps" | the prompt sent the session to close Epic 5 while Epic 4 was open; the state table has no epic-closure row |
| K1 `3c9dbfd` 2026-09-10T10:00 PDT (substrate fix) | superseded by K0 before any session read it | 14 (PRs #89 and #90 merge state, worktree and two branches, 4 read-first paths, zero `localcontext` in `projections.py`, the one test file calling `historical_frequency_magnitude_distribution`, 1308 unit and 353 db collected, lanes green at the #90 head, main-checkout untracked files, PRs #83, #86, #87 shape) | 2: "#90 retargets to main automatically" (it did not; PR #91 recovered the content 4 minutes later); "expect assembled numbers to move; four merged waves' tests pin them" (open PR #95 changes `projections.py` and adds one new test file; no existing test changed) | 2: the measured figures (1032 tables, 695, 55 support points, -3.569E-26) are recorded only in the closure report; "six three-observation histories" (the file says every value feeds one, count not stated) | |
| K0 `8206f7f` 2026-09-10T10:11 PDT (hand reconciliation, PR #92) | substrate session, 2026-09-10T17:27Z, first prompt verbatim | 8 new (77d1ead ancestry, Epic 5 reports and row 51 and folded list at 77d1ead, both closure branches gone local and remote, 5B worktree detached, exactly four stale local branches) plus K1's remaining claims | 0 new | 2 (as K1) | |
| Totals over K1 to K5 | | 79 | 5 (6%) | 6 (8%) | 3 of the 5 wrong claims are about worktree or branch state, the state `bmad-wrap` writes from memory rather than from `git worktree list`; the other 2 are a GitHub-behaviour assumption and a forecast |

Adoption: 22 of 52 sessions since 2026-08-20 opened with the kickoff prompt verbatim (18 wave sessions, 3 closures, 1 cleanup); the other 30 are founder-side, cleanup, or follow-up sessions started by hand.

### 2d. Rulings register

| Measure | Count | Rows |
|---|---|---|
| Total rulings | 51 | 1 to 51 (44 to 51 numbered out of sequence) |
| Referenced by a later artifact or commit (any reader outside the register) | 51 | all |
| Referenced from code or tests | 10 | 13, 14, 15, 16, 28, 29, 44, 45, 46, 47 (`ffbapp/platform/config.py` alone cites 14, 15, 44, 47) |
| Referenced by a build-phase artifact (epics, waves, story files, test designs, pins, closures, `project-context.md`, `CLAUDE.md`, `HANDOFF.md`, `TODO.md`, triage) | 38 | all except the 13 below |
| Referenced only by planning-phase artifacts (brief, PRD, research, narrative, UX, LLM surfaces) | 13 | 1, 3, 6, 7, 11, 20, 21, 22, 27, 38, 41, 42, 43 |
| Referenced only through triage reports among build-phase readers | 6 | 2, 9, 18, 25, 31, 32 |
| Referenced from skills | 1 | 51 (`bmad-dev-wave` 1.1.0, `bmad-close-epic` 1.2.0, `bmad-status-wave` 1.1.0) |
| Carrying an in-place amendment, reaffirmation, or supersession note | 7 | 2 (DFS and best ball moved to deferred, 2026-08-06), 12, 17, 18, 21, 37 (supersedes the earlier all-plain rule), 48 |
| Contradicted by a later ruling that is not folded into the row | 0 | none found; every later ruling either edited the row or added a new one (44 to 51) |
| Contradicted by later code, machine-checked | 0 | row 36: 0 time-estimate phrases in `_bmad-output/planning-artifacts`, `docs`, `epic-closure`; row 37: 0 icon-prefixed lines in recorded artifacts; row 49: 0 `draftlab` imports under `ffbapp/` or `tests/`; row 16: compute cap present (`ffbapp/platform/compute/launcher.py`, PRs #42, #83); row 14: gate spec hash-pinned (`harness/gate-specs/REGISTRY.json`) |
| Never affected anything | 0 by any-reader count; 13 by build-phase reach | the 13 planning-only rows are product-level rulings the PRD absorbed (three pillars, vision, formats, anti-goals, naming state) |

Not checkable from the repo: rows 30 (attribution tags), 33 (opt-in delivery), 34 (umbrella principle) describe product behaviour Phase 1 does not build yet.

### 2e. Escalations

Source: 87 transcripts. Exact count: `AskUserQuestion` tool calls (each question inside a call counted once). Heuristic count: an assistant text ending in a question mark immediately followed by a human turn; duplicates from resumed transcripts and re-invoked skill echoes removed. Classes: P = product or plan decision only RQ could make; S = ambiguity a ruled document or the framework should have resolved before the session; U = unnecessary (mechanical, verifiable by the agent, or re-asked); C = framework ceremony (`bmad-wrap` option selection and wrap confirmation, checkpoint-preview approval, "merge now?").

| Session (date) | Model | Human turns | Questions | P | S | U | C | Notes |
|---|---|---|---|---|---|---|---|---|
| wave planning, create-wave (08-20) | fable-5 | 5 | 4 | 2 | 0 | 0 | 2 | 6A placement; wave map approval |
| CLAUDE.md and model policy (08-20) | fable-5 | 8 | 3 | 1 | 0 | 1 | 1 | |
| wave 1A (08-20) | fable-5 | 7 | 2 | 0 | 0 | 1 | 1 | "how do you want to handle the merge" |
| epics-and-waves party review (08-20) | fable-5 | 19 | 1 | 1 | 0 | 0 | 0 | rule on 67 findings |
| wave 1B (08-23) | opus-5 | 9 | 1 | 0 | 0 | 0 | 1 | |
| founder pen, wave 1B rulings (08-24) | opus-5 | 3 | 5 | 2 | 1 | 1 | 1 | Member vs Manager naming was a spine gap |
| dev errands (08-24) | sonnet-5 | 22 | 4 | 2 | 0 | 2 | 0 | org choice, $50 cap |
| wave 1C (08-24) | opus-5 | 8 | 1 | 0 | 0 | 0 | 1 | |
| wave 1C merge cleanup (08-24) | sonnet-5 | 4 | 5 | 0 | 0 | 4 | 1 | one question per merged worktree |
| Epic 1 closure (08-24) | opus-5 | 10 | 5 | 0 | 4 | 0 | 1 | all four are framework gaps: findings with no reader, story files absent, nothing writes `done`, merge-wave blind to harness worktrees |
| flag B (08-25 and 08-27, one resumed session) | fable-5 | 18 | 3 | 1 | 0 | 0 | 2 | |
| wave 2A (08-25) | opus-5 | 11 | 4 | 0 | 3 | 0 | 1 | contract columns vs real nflverse columns; duplicate rows on re-import; the fix that did not close it |
| wave 2A post-merge cleanup (08-26) | sonnet-5 | 7 | 1 | 0 | 0 | 1 | 0 | |
| wave 2A cleanup outstanding (08-27) | sonnet-5 | 14 | 7 | 0 | 1 | 6 | 0 | six "proceed / delete / keep?" prompts |
| Epic 2 closure (08-31) | opus-5 | 7 | 1 | 0 | 0 | 0 | 1 | |
| Epic 2 findings fix (08-31) | sonnet-5 | 8 | 4 | 1 | 0 | 2 | 1 | trademark filing details (founder data) |
| wave 3D (08-31) | sonnet-5 | 7 | 6 | 1 | 3 | 0 | 2 | Sleeper translation scope; season rule-sheet version undefined (AD-7 gap); process rule for founder-disposition findings |
| wave 3B (09-01) | opus-5 | 8 | 13 | 8 | 3 | 1 | 1 | story 3.3 had no data on disk; a subagent relaxed an import contract (`allow_indirect_imports`) and the orchestrator escalated it; two destructive re-derivation decisions |
| wave 3E (09-01) | opus-5 | 8 | 6 | 2 | 3 | 0 | 1 | thirteen vs twelve event codes; AC-3.3-3 assumed a fallback that does not exist |
| wave 3C (09-02) | sonnet-5 | 6 | 4 | 2 | 0 | 1 | 1 | |
| Epic 3 closure (09-02) | sonnet-5 | 7 | 1 | 0 | 0 | 0 | 1 | |
| wave 4A (09-02) | sonnet-5 | 7 | 1 | 0 | 0 | 0 | 1 | |
| wave 6A (09-03) | sonnet-5 | 8 | 24 | 23 | 0 | 0 | 1 | the H1 gate-spec content (metric, bars, significance, eval window, features, positions) elicited one question at a time at RQ's request ("hold, and ELI5"); row 14 required these thresholds and no ruled document carried them |
| wave 4B (09-03) | sonnet-5 | 8 | 3 | 0 | 2 | 0 | 1 | first model code with no library chosen until 6C; AC tolerance undefined |
| wave 4B cleanup (09-04) | sonnet-5 | 5 | 0 | 0 | 0 | 0 | 0 | |
| wave 5A (09-04) | sonnet-5 | 12 | 4 | 1 | 2 | 0 | 1 | taxonomy for v0 vs row 29; NAV formula absent |
| wave 5B (09-04) | sonnet-5 | 4 | 5 | 0 | 4 | 0 | 1 | four forks the test design found undetermined |
| wave 5C (09-05) | fable-5-1 | 8 | 0 | 0 | 0 | 0 | 0 | two founder rulings taken before dispatch per waves.md, outside `AskUserQuestion` |
| sweep and first-down (09-08) | opus-5 | 3 | 1 | 0 | 0 | 0 | 1 | |
| wave 5D (09-08) | opus-5 | 10 | 15 | 2 | 10 | 2 | 1 | two framework-state conflicts (serial vs parallel; branch suffix vs harness worktree); four spec forks asked twice (plain-language re-ask); 5 of the 10 S are re-asks |
| Epic 4 and 5 closure (09-10) | opus-5 | 8 | 6 | 3 | 2 | 0 | 1 | "Epic 4 was never closed"; two process questions became row 51 |
| substrate fix (09-10) | opus-5 | 0 | 3 | 0 | 0 | 2 | 1 | disposition of the now-stale waves.md filing, asked twice |
| Sessions with zero questions: 2B, 2C, 3A, repo hygiene, inert-test amendment, fictitious-name | | | 0 | | | | | |
| Totals, 31 sessions with questions | | 251 | 143 | 52 | 38 | 24 | 29 | 4.6 per session; 4.9 per wave session (89 over 18 waves); 23 of the 52 P are the 6A elicitation |

Breakdown of the 38 S questions by root: ruled document gap (an acceptance clause, contract, or formula assumed something that did not exist or was never defined) 25; framework gap (no reader for findings, no `done` writer, merge-wave blind, state files disagreeing) 8; re-asks of an S already asked 5.

### 2f. Model routing

Policy sources: `keelswell/core/config.yaml` (not installed), ffbapp `bmad-dev-wave` Model Policy (dev-work dispatches on sonnet; orchestrator, test design, reviewers on the session model), `bmad-wrap` per-session suggestion in `HANDOFF.md`. Actuals from transcripts (`message.model`, `effort`, `Agent` input `model`, subagent transcript models).

| Wave | Wrap suggested (mode / model / effort) | Session model / effort | Test design | Implementation dispatches | Reviewers | Inversion or deviation |
|---|---|---|---|---|---|---|
| 1A | none (first wave) | fable-5 / max | fable-5 | sonnet (2 of 8 dispatches) | fable-5 | policy adopted in-session (PR #28) |
| 1B | opus / high (`70ff3a3`) | opus-5 / max | opus-5 | sonnet (3) | opus-5 | none |
| 1C | "Model policy" / medium (`2fe4c42`) | opus-5 / medium | none dispatched | none; orchestrator wrote stories 1.4 to 1.6 itself (81 code edits, 0 subagent edits) | opus-5 (3 reviews) | orchestrator drift: implementation on the frontier model by the orchestrator |
| 2A | fable or opus / high (`ed378ec`) | opus-5 / medium | opus-5 | sonnet (8 of 12) | opus-5 | effort below suggestion |
| 3A | fable or opus / high | fable-5 / high | fable-5 | sonnet (3) | fable-5 | none |
| 2B | fable or opus / high | fable-5 / high | fable-5 | sonnet (2) | fable-5 | none |
| 2C | fable or opus / high | fable-5 and opus-4-8 / high | opus-4-8 | sonnet (4) | opus-4-8 | part of the session and all subagent orchestration ran on the previous generation (opus-4-8, 330 turns) |
| 3D | sonnet / high (`767dfae`) | sonnet-5 / high | sonnet-5 | sonnet (4) | sonnet-5 | no tier separation: adversarial review on the workhorse tier (`core/config.yaml` routes adversarial to frontier) |
| 3B | sonnet / high | opus-5 / high | opus-5 | sonnet (4) | opus-5 | RQ upgraded the session above the suggestion |
| 3E | opus / high (`4c2e580`) | opus-5 / high | opus-5 | sonnet (5) | opus-5 | none |
| 3C | sonnet / medium (`514be30`) | sonnet-5 / medium | none | sonnet (2) | none dispatched (no review record) | no adversarial review at all |
| 4A | sonnet / medium (`01c8f14`) | sonnet-5 / medium | sonnet-5 | sonnet (1) | sonnet-5 (1) | no tier separation |
| 6A | sonnet / medium (`01508d5`) | sonnet-5 / medium | sonnet-5 | sonnet (1) | sonnet-5 (2) | the wave carrying 23 founder decisions on the H1 gate ran at the lowest suggested tier and effort of any wave |
| 4B | sonnet / high (`93004b4`) | sonnet-5 / high | sonnet-5 | sonnet (3) | sonnet-5 (3) | no tier separation; the substrate defect originated here and passed three sonnet reviewers; caught by 5D's opus-5 test-integrity reviewer |
| 5A | auto / sonnet / low (`f0ad7a5`) | sonnet-5 / high | sonnet-5 | sonnet (2) | sonnet-5 (3) | suggestion was auto and low for a two-story wave that surfaced 2 spec gaps; orchestrator also made 51 code edits |
| 5B | auto / sonnet / low (`4e5e231`) | sonnet-5 / high | sonnet-5 | sonnet (2) | sonnet-5 (3) | suggestion was auto and low for a wave whose test design found 4 undetermined forks |
| 5C | plan / fable / high (`9c4bb95`) | fable-5-1 / high | fable-5-1 | sonnet (4) | fable-5-1 | none |
| 5D | plan / opus / high (`7d039be`) | opus-5 / high | opus-5 | sonnet (3) | opus-5 (3) | none |

Aggregate: dev-work dispatches carried `model: sonnet` in 18 of 18 waves (policy followed). Test design and adversarial review ran on the session model in every wave, so in the 7 waves whose session was sonnet-5 (3D, 3C, 4A, 6A, 4B, 5A, 5B, merged 2026-09-01 to 09-05) the planning, the implementation, and the review all ran on the workhorse tier; those 7 waves account for the only merged correctness defect found later (4B), the wave with no review (3C), and 30 of the 38 spec-gap escalations. Pre-2026-08-20 planning sessions ran on fable-5 at effort max throughout. The wrap's suggestion was followed for model in 14 of 17 waves with a suggestion (RQ upgraded 3B; 2A and 5A, 5B ran at higher effort than suggested).

---

## Phase 3: Assessment

Severity scale: BLOCKS CORRECTNESS (a wrong number or a skipped check reached main), COSTS ATTENTION (RQ turns, re-briefing, or manual checks that a mechanism could remove), COSMETIC (no measured effect on shipped code or attention).

### Six layers

| Layer | What exists | What is missing | Strongest evidence for | Strongest evidence against | Severity |
|---|---|---|---|---|---|
| 1. Context | Global `CLAUDE.md` plus `filesystem.md` (1,920 tokens); ffbapp `CLAUDE.md` kept thin by design (1,030); `project-context.md` with 43 rules grown by closure (5,540); register with 51 rows, 10 cited from code; glossary; 108 skill frontmatters (~7,000); ADHD ruleset (1,710); `MEMORY.md` (2,280); mandated `HANDOFF.md` and `TODO.md` (7,450) | A single rendered conventions block for implementers (present in 4 of 18 waves' dispatch prompts; `project-context.md` in 12; neither in 3B, 3C, 5A, 5B); pruning of 76 never-run skills from the roster; a check that keeps `CLAUDE.md` current; one owner for rules now duplicated in `CLAUDE.md` and `project-context.md`; the installed `core/config.yaml` the skills cite | Folded rules propagate: "prove by execution and mutation" (Epic 1 retrospective) appears in the dispatch prompts of 15 of 18 waves; register rows reach code (`ffbapp/platform/config.py` cites rows 14, 15, 44, 47) | `ffbapp/CLAUDE.md` opens with "No production code exists yet" through 18 waves and 5 edits; the em-dash rule in three sources with 63 violations in the FINAL `epics.md` and an unwired hook; the global voice ban on "substrate" against the project's ruled term; four waves' implementers received no coding rules | COSTS ATTENTION, one correctness exposure (4 waves without rules) |
| 2. Tools and permissions | 354-entry allow list; `gh` for every merge check; `uv`, `pytest`, `ruff`, `lint-imports`; harness worktrees; `Agent` tool with a `model` parameter (the only routing that actually bound, 18 of 18 waves); MCP connectors for the business sessions | A sweep tool for merged worktrees and branches (done by hand in 4 sessions, 20 of the 24 unnecessary questions are "remove this?"); a live-state read at wrap time (`git worktree list`) so `HANDOFF.md` is not written from memory; a model key in settings; wired hooks (`em-dash-scrub.sh`, `wrap-reminder.sh` exist, neither runs); `delete_branch_on_merge` (off; 12 stale remote branches); allow-list pruning (6 entries point at worktree paths that no longer exist) | The `model: sonnet` parameter on dispatch made the Model Policy real without any prose reminder | `bmad-merge-wave` 1.0.0 exited 0 having done nothing on 4 waves; `bmad-status-wave` probes `../<project>-wave-*` and `wave-*` branches, a layout no wave used; K4 told a session to remove the worktree the harness then started it inside | COSTS ATTENTION |
| 3. Verification | CI with three required lanes, strict, no bypass actors (54 of 54 lanes green at every wave merge and head); 1,308 unit and 353 db tests; 7 import-linter contracts; S608 and C901; local lanes proven identical to CI; ATDD scaffolding step; mutation-proof briefs; closure gate with four passes; row 51 gates since 2026-09-10 | A check that a review record exists (8 of 18 waves have none; 3C has no test design either); a check that closures ran before the next epic opened (Epic 4 skipped 2026-09-03 to 09-10); any consequence for a YELLOW closure (4 of 5 merged as-is); coverage or reach tooling (fixture reach was found by a reviewer reading tests); the db lane in `bmad-dev-wave` step 9 (fast only) | Rework inside two waves: 2 of 18; the 3E review found six derivation defects by execution that 915 green tests had not; the 5D reviewer found five tests that could not fail in a suite whose 22-row mutation table caught every row | The 4B guard is an identity on its producer's output: zero firings across 1,032 tables with 695 carrying a real deficit; it passed three same-tier reviewers, 1,193 tests, and waves 5A to 5D; open PR #95 is the fix. Tests that could not fail were found in 2A, 5C, 5D; each time by a person-shaped reviewer, never by a tool | BLOCKS CORRECTNESS |
| 4. State and continuity | Kickoff prompt in `HANDOFF.md` consumed verbatim by 22 sessions, 94% of 79 checked claims right; `project-context.md` growth; register; `waves.md` amendments carrying deferred findings; auto-memory with 39 index entries | State read live from git at wrap (3 of 5 wrong claims are worktree or branch state); an epic-closure row in the state table (K2 sent the session to close Epic 5 with Epic 4 open); checkpoints (2 of 18 waves; resume never possible); a reader for triage reports; a sync mechanism for three copies of every wave skill (Model Policy never reached keelswell; `CHANGELOG.md` 17 days behind four skill changes) | The closure session recovered Epic 4's true state from three one-command repo signals in minutes, and K5 was right on all 11 claims | K3 said parallel where `waves.md` said serial; K4 named a worktree that never existed; K1 assumed a GitHub retarget that did not happen and needed PR #91; the dashboard skill has never shown a real wave | COSTS ATTENTION |
| 5. Control | Every wave halted before merge (18 of 18); founder rulings by chat into a register; 244 `AskUserQuestion` calls; plan mode on the two riskiest sessions; wrap option selection; checkpoint preview; dev dispatch on sonnet; "never trust a subagent summary" rule; row 51 refusal prose | A budget or stop condition on agent spend or on questions per wave; a routing rule that survives the session's model choice (reviewers ran on sonnet in 7 waves); a rule that the orchestrator does not write code (1C: 81 orchestrator code edits, 0 subagent; 5A: 51 vs 40); a pre-wave open-forks pass so the founder interview happens before dispatch (5B: 4 forks, 5D: 4 forks asked twice, 6A: 23); a threshold separating a real question from a confirmation (24 unnecessary, 29 ceremony of 143) | Product questions were never settled silently: 5B's forks, 5D's exposure dial, 3B's data rewrite, 3E's labelling all reached RQ before code; the 3B subagent's import-contract relaxation was surfaced and ruled | The wrap suggested auto and low effort for 5A and 5B, the two waves that then surfaced 6 spec gaps and ran at high; 6A took 23 founder decisions on sonnet at medium; 51 of 244 ask calls batched more than one question against the global one-at-a-time rule | COSTS ATTENTION |
| 6. Observability and improvement | Five skill versions earned by ffbapp failures (`bmad-merge-wave` 1.1.0, `bmad-close-epic` 1.1.0 and 1.2.0, `bmad-wrap` 1.9.0, `bmad-dev-wave` 1.1.0, `bmad-status-wave` 1.1.0), each with a version-history entry naming the defect; 17 rules folded from retrospectives; `epic_retrospectives_folded` frontmatter; one skill-doctor run | Cost per wave (present in every transcript turn, read by nothing); rework, escalation, and kickoff-accuracy metrics; a working dashboard; a changelog that tracks skill versions; a check that a folded rule changed behaviour (the fixture-reach shape recurred in 2A, 3E, 5D after being written down twice) | The improvement loop closed on process defects within days: harness-blind merge-wave found 2026-08-24 and fixed the same day; the Epic 4 skip found and gated the same day | "What did wave N cost and why did it need rework" is unanswerable from any artifact; this review is the first computation of per-wave tokens (130k to 1.8M output; 72M to 763M input); the Epic 4 skip lasted 7 days because the only signal was a blind dashboard | COSTS ATTENTION; cost invisible |

### Failure modes

| Failure mode | Verdict | Evidence |
|---|---|---|
| Instruction dilution | FOUND | Three instruction sources ban em dashes (`~/.claude/CLAUDE.md`, `templates/CLAUDE.md.template`, the unwired hook); `epics.md` (FINAL, ruled) carries 63, `waves.md` 3, `TODO.md` 2. Global rule "Ask ... one at a time": 51 of 244 `AskUserQuestion` calls carried more than one question (5D asked four forks per call, twice). `ffbapp/CLAUDE.md` line 3 stayed false through 5 edits. The Voice section bans "substrate" while `HANDOFF.md` uses it 20 times and PR #95 is titled with it |
| Persona overhead | FOUND | 25 launcher skills, 890 lines of custom persona text, ~10,000 chars of descriptions loaded every session; 0 launcher activations in the build phase; 0 persona names across 44 wave artifacts and 25 closure files; 3 of 17 test-design dispatches named a persona and produced the same artifact shape as the 14 that did not; wave reviewers were dispatched by domain in 16 of 18 waves; the roster-name mismatch (`_bmad/config.toml` upstream names vs Wheel of Time skills) cost a memory entry and a party-mode workaround. Six of keelswell's 46 commits are name or voice maintenance |
| Verification theater | FOUND for reviews and closures, NOT FOUND for CI | CI gates merges for real (ruleset, no bypass, 54 of 54 green). Reviews: 8 of 18 waves have no record, 3C had no test design and no review; closures: 4 of 5 YELLOW, all merged, none blocked anything; the Epic 4 gate was skipped and nothing noticed; `bmad-status-wave`'s Tests column reads results "if present" and none were ever present. Tests green while wrong: 2A's contract-correspondence test, 5C's 29 exactness tests on halves and quarters, 5D's five unfailable tests, 4B's guard |
| Phantom state | FOUND | 5 of 79 kickoff claims wrong (K1 GitHub retarget, K1 forecast, K2 omission of the closure-pending epic, K3 parallel, K4 non-existent worktree); `project-context.md` and `bmad-close-epic` 1.2.0 give different lists of waves without review records; `ffbapp/CLAUDE.md` misdescribes the repo; the dashboard skill is structurally blind |
| Write-only registers | FOUND | 77 triage reports, 452 KB, no reader in any skill, hook, or kickoff; 8 memlogs, dead since 2026-08-16; `.bmad` checkpoints for 2 waves, read by a skill that never ran; `ffbapp-pipeline-state.md` (141 KB, a chronology duplicating HANDOFF history) is 46% of auto-memory; `.agents/skills` frozen pre-0.3.0; `_bmad/config.toml` descriptors for 22 launchers that never ran; 13 register rows with no reader after the PRD |
| Orchestrator drift | FOUND | Wave 1C: the opus-5 orchestrator made 81 code edits and dispatched 0 implementers (3 review subagents only); 5A: 51 orchestrator code edits against 40 by subagents; 1B 15, 2C 12. Subagent architecture call: the 3B implementer added `allow_indirect_imports = true` to an AD-2 contract (`pyproject.toml` comment records it); escalated after the fact and ruled, not prevented. No silent product call found: 5D's `free=full` exposure dial and 5B's forks were escalated |
| Underspecified handoffs | FOUND in 5 of 18 waves | Implementation dispatches without `project-context.md` or a conventions block: 3B, 3C, 5A, 5B; 3C's two dispatches carried no test design (none exists) and no acceptance clauses beyond the api-surface pin; 5B's implementers received the test design and nothing else (no pin, no story file, no clauses). Elsewhere prompts averaged 4,000 to 12,000 chars and carried test design (17 waves), pin (15), clauses (12). Consequence visible in 2A: two remediation rounds per story |
| Single-project overfit | FOUND | Keelswell's own `skills/` tree now carries ffbapp history: 38 ffbapp-specific strings across `bmad-close-epic` (17: "waves 1A, 3C, 4A, 4B, 5A, 5B and 6A", "Epic 6's closure", "Ruled by RQ in chat, 2026-08-24"), `bmad-dev-wave` (16: "Epic 4 fell through", "wave 4B merged on 2026-09-03", `tests/verify-fast.sh`), `bmad-status-wave` (3), `bmad-merge-wave` (2). The closure-record rule is dated "prospective from 2026-09-10" inside the framework. `core/config.yaml`, the sibling-worktree convention, and `docs/stories/` paths fit no project that runs under the Claude desktop harness |

### Deviation verdicts

| # | Deviation | Earned its keep? | Evidence |
|---|---|---|---|
| D1 | Seven wave skills | Split: `bmad-dev-wave`, `bmad-close-epic`, `bmad-wrap`, `bmad-create-wave` yes; `bmad-merge-wave` marginal; `bmad-status-wave` and `bmad-resume-wave` no | 18 waves merged with 2 of 18 reworked and every lane green; 5 closures produced 17 rules and fix PR #65; 22 verbatim kickoffs at 94% accuracy; one wave map consumed by everything. Merge-wave did the cleanup once (2A) and was bypassed by hand elsewhere. Status-wave never displayed a real wave; resume-wave never ran and had 2 checkpoints to read |
| D2 | Eight architecture agents | No as skills; yes as review domains | 0 activations; their names appear only as planning-phase party reviewers whose 102 folded findings came through `bmad-party-mode` rosters, and wave reviewers were dispatched by domain without them |
| D3 | Fifteen custom agents | Basel Gill yes (business outcomes); Talmanes and Juilin marginal; twelve no | 5 sessions of entity and trademark work landed real filings; two produced planning inputs for surfaces Phase 1 does not build; 12 had 0 activations, two of them added 2026-08-25 for work that has no Phase 1 surface |
| D4 | `bmad-master` and `bmad-agent-qa` launchers | No | 0 activations; the QA persona reached three test-design prompts as text |
| D5 | Wheel of Time renames | No | No behaviour attributable; cost: roster-name mismatch in party mode, 6 maintenance commits, `_bmad/config.toml` still carries upstream names |
| D6 | Character voice rewrites | No | Row 37 keeps voice out of every recorded artifact; the only surface is chat, unmeasured |
| D7 | Retrospective recast to Mat Cauthon | No | 129 changed lines of scripted dialogue; the retrospective's output (17 rules) is plain prose |
| D8 | `core/config.yaml` | No | Never installed; contradicts the run modes the wrap suggests and the worktree layout every wave used |
| D9 | `agent-names.yaml` roster | Neutral | Install-time input only |
| D10 | Templates and `install.sh` | HANDOFF shape yes; the rest no | HANDOFF's state table survives; the CLAUDE.md template was not used; the settings template references keys and a binary that do not exist; TODO buckets unused |
| D11 | Hooks | No | Unwired in both repos; the one mechanical rule they enforce is the one most violated |
| D12 | `module.yaml` and marketplace packaging | Yes | The installer recorded the module and skills mirror; refresh runbook documents the clobber classes |
| D13 | Wave cycle replacing the vanilla story loop | Yes, the core value | The vanilla loop skills have 0 invocations; the wave cycle shipped Phase 1 epics 1 to 5 in 21 days with CI green throughout |
| D14 | Row 51 gates (2026-09-10) | Too new; design risk | Both halves are preflight prose the model must obey; the same shape (a skill saying "refuse") is what let Epic 4's gate be skipped |
| D15 | Model Policy in `bmad-dev-wave` (ffbapp only) | Yes for cost; unsynced | Sonnet on 18 of 18 dev dispatches; never copied to keelswell; its silence on reviewers produced the 7 all-sonnet waves |
| D16 | Beta League panel | Yes once | One convening changed CAB-14 and CAB-15; idle since 2026-08-11 |
| D17 | Frozen `.agents/skills` tree | No | Unread, behind `.claude/skills`, duplicates 1,051 files |

### Ten findings that most affect the definition of effective

| # | Finding | Layer | Ranking item hit | Evidence |
|---|---|---|---|---|
| 1 | Review and closure verdicts do not gate anything. A wave can merge with no review record (8 of 18 did), an epic can close YELLOW (4 of 5 did) or not close at all (Epic 4, 7 days), and the one correctness defect that reached main did so through exactly those gaps | 3 | 1 correctness | `docs/wave-*/review-party.md` absent for 1A, 3C, 4A, 4B, 5A, 5B, 5D, 6A; `epic-closure/*/SUMMARY.md` statuses; `epic-closure-gate-skip-detection.md`; open PR #95 |
| 2 | Adversarial review ran on the same tier as implementation in 7 waves because the reviewer model follows the session model and nothing installed says otherwise. Those 7 waves hold the later-found defect, the unreviewed wave, and 30 of 38 spec-gap escalations | 5 | 1 correctness, 2 attention | 2f table; `core/config.yaml` (uninstalled) `adversarial: frontier`; 5D's opus-5 reviewer caught what 4B's three sonnet-5 reviewers passed |
| 3 | Implementers in 4 waves (3B, 3C, 5A, 5B) received no coding rules: neither `project-context.md` nor the conventions block was in their dispatch prompt; the block `bmad-dev-wave` says is rendered "identically into every coding-subagent dispatch" appears in 4 of 18 waves | 1 | 1 correctness | dispatch-prompt key scan (2a); `bmad-dev-wave` Project Conventions Block section |
| 4 | RQ answered 143 questions across 31 engineering sessions; 53 were mechanical or wrap ceremony and 38 were spec gaps that surfaced only at dispatch time, so most waves opened with a founder interview (5B: 4 forks; 5D: 4 forks twice; 6A: 23) | 5 | 2 attention | 2e table; wave test designs' "Open Questions" sections |
| 5 | The handoff is written from memory: 5 of 79 kickoff claims were wrong, three about worktree or branch state a `git worktree list` would have fixed, one omitted the closure-pending epic, one assumed a GitHub behaviour that cost PR #91; the dashboard that should catch drift probes a layout the project never used | 4 | 2 attention, 3 continuity | 2c table; `bmad-status-wave` probes 2 and 3; `.bmad/wave-5D/checkpoint.json` `pattern_ruling` |
| 6 | Worktree and branch cleanup is a manual loop: 4 sweep sessions, 20 "remove this?" questions, `bmad-merge-wave` silently doing nothing for its first 4 waves, sessions started inside the worktree they were told to remove, 12 stale remote branches with `delete_branch_on_merge` off | 2 | 2 attention | 2e (U class); PRs #45, #55, #81; 2026-09-08 sweep transcript; `gh api repos/attacktheseam/ffbapp` |
| 7 | Every session pays ~14,000 tokens of framework context before reading a file, half of it descriptions of 76 skills and 25 personas that never ran on this project, and a wave session reads ~55,000 tokens before its first tool call; no persona name appears in any wave or closure artifact | 1 | 5 cost, 2 attention | 1g; 2a skill and agent tables |
| 8 | State the framework writes but never reads: 77 triage reports (452 KB), checkpoints for 2 waves, memlogs dead since 08-16, a 141 KB chronology in auto-memory, a frozen `.agents/skills` tree, three copies of each wave skill with the Model Policy in one and the changelog 17 days behind | 6 | 3 continuity, 5 cost | 1d; 2a artifacts table; `CHANGELOG.md` vs `skills/*/SKILL.md` version histories |
| 9 | A third of Phase 1 is not traceable from git: 11 of 30 merged stories have no story file, 16 `Story n.m` commits cover 30 stories, and branch names carry the wave for 14 of 18; traceability lives in test designs and closure trace passes instead | 4 | 4 traceability | 1d story-file row; conventions table; `bmad-close-epic` "a story with no file needs nothing" |
| 10 | Cost is unmeasured and unbudgeted: 36M output and 7.9B input tokens across 87 sessions, per wave 130k to 1.8M output, computed here for the first time; the wrap suggested auto and low effort for waves that ran high; nothing stops a session on spend or on questions | 6 | 5 cost, 2 attention | 2b token columns; 2f suggestion column; transcripts `message.usage` |

---

## Phase 4: Harness roadmap

### Target harness spec (one page)

| Layer | Contains | Enforces | Measured by |
|---|---|---|---|
| 1. Context | Global `CLAUDE.md` under 60 lines (voice and filesystem only; no project-vocabulary bans). Project `CLAUDE.md` under 40 lines: repo map, verify commands, paths of the documents of record, one pointer to the rules file. One rules file (`project-context.md`) as the sole owner of coding and workflow rules. A skill roster of at most 25 skills per project, declared in a project manifest. Register and glossary unchanged. A SessionStart hook that prints live repo facts (branch, last merged wave, test counts, open PRs) so no prose file has to claim them | A dispatch hook refuses an implementation dispatch whose prompt lacks the rules-file marker. A lint fails when a rule appears in both `CLAUDE.md` and `project-context.md`. Skill descriptions are loaded only for the manifest roster | Tokens injected at session start (target under 8,000). Skills listed vs skills invoked per month. Duplicate-rule lint count (0) |
| 2. Tools and permissions | `bin/wave-state` (live JSON: worktrees, branches, PR states, closure dirs, collected test counts). `bin/sweep` (verify merged with `gh`, remove worktree, delete local and remote branch, refuse the session's own worktree, print what it did). Repo setting `delete_branch_on_merge` on. Committed `settings.json` with hooks, a curated allow list under 60 patterns, and the model default. The harness `Agent` model parameter | No git housekeeping question ever reaches RQ; wrap and status read `bin/wave-state`, never memory | Unnecessary-class questions per session (0). Sweep sessions (0). Allow-list entries (under 60) |
| 3. Verification | CI as today (three required lanes, no bypass) plus: a review-record check on every wave PR (fails without `docs/wave-<id>/review-party.md` naming the reviewed commit); a closure-order check on every wave PR (fails while an earlier epic has all waves merged and no `epic-closure/epic-<n>/SUMMARY.md`); `verify-db` in the wave's own verify step; a test-reach lint (`pytest.raises` without `match=`, tests with no assert, asserts against `None` only) run in the fast lane; optional mutation smoke on files the PR touches | A wave cannot merge without its review record; the next epic's first wave cannot open while a closure is pending; a CONCERNS verdict creates owned TODO items or blocks (decision 1) | Waves merged without a record (0). Days between last wave merge and closure (under 2). Post-merge defects per epic. Reach-lint findings per PR |
| 4. State and continuity | `HANDOFF.md` generated: state table from `bin/wave-state`, a human-written "next" section, the kickoff prompt with live fields filled by script. No checkpoints (resume from git and PR state). No triage reports (the wrap prints its summary; TODO history is git history). Auto-memory capped at 25 index entries, no chronologies. Keelswell installed into projects by a sync script with a CI diff check, not by hand copy | Every state claim in a kickoff is generated; skill copies are identical across keelswell trees and instances | Wrong state claims per kickoff (0). Sync diff lines (0). `HANDOFF.md` under 60 lines |
| 5. Control | Routing in the dispatch call, not in prose: implementation `model: sonnet`; test design and every reviewer `model:` frontier, regardless of session model. A pre-wave forks pass: test design runs first, its open questions go to RQ as one pre-read, dispatch waits for rulings. A wave marker file while a wave is open; a PreToolUse hook denies orchestrator edits under `ffbapp/` and `tests/` while it exists. A per-wave spend line printed at wrap with a soft cap. Wrap defaults to its recommended option; merge halts stay | Reviewers never share the implementer's tier; the orchestrator never writes code during a wave; RQ is asked before dispatch, not during it | Questions per wave by class (P, S, U, C; target U and C at 0). Reviewer tier compliance (100%). Orchestrator code edits during a wave (0). Output tokens per wave |
| 6. Observability and improvement | `bin/wave-cost` (transcript usage to per-session and per-wave tokens by role). `metrics.csv` appended by every wrap: wave, PR, tokens by role, questions by class, rework commits, review record present, closure status. `CHANGELOG.md` entries required by a keelswell CI check on any skill version bump. A quarterly skill-doctor pass | Every wrap records cost and questions; every skill change has a changelog line | The metrics file itself: cost per wave, rework rate, kickoff accuracy, escalation mix, trend over epics |

Portability split: Keelswell owns the skills (stripped of project history), `bin/` scripts parameterized by a small config (verify commands, wave-map path, closure dir, tiers), the hooks, the CI job templates, a settings template with only real keys, the metrics schema, and the roster manifest format. The ffbapp layer owns `CLAUDE.md`, `project-context.md`, the register, the glossary, `waves.md`, the verify scripts, the CI wiring, the Beta League panel, the Model Policy values, and a `docs/keelswell-local.md` holding the row 51 narrative and every other dated ffbapp fact now living inside skill text.

### Migration, batch 0: removals and shrinks first

| # | Remove or shrink | Where | Saving | Reversible by |
|---|---|---|---|---|
| R1 | 76 never-run skills and 22 never-activated launchers out of the ffbapp roster (keep them in keelswell behind a manifest) | `ffbapp/.claude/skills` | ~4,000 tokens per session of descriptions; a roster the model can read | `git revert` |
| R2 | `.agents/skills` duplicate in ffbapp and the frozen 1,051-file tree in keelswell | both repos | repo size; a possible double-loaded description (OPEN VERIFY) | `git revert` |
| R3 | `bmad-resume-wave`, `bmad-status-wave` (rebuilt on `bin/wave-state` in batch 1), `core/config.yaml`, `templates/settings.json.template`, the checkpoint-writing steps in `bmad-dev-wave` | keelswell | 3 dead artifacts, ~2,000 chars of skill prose, one config that contradicts practice | `git revert` |
| R4 | Triage reports (`_bmad-output/session-wrap/`): stop writing them; wrap prints the same summary | `bmad-wrap` step 5 | ~1,500 output tokens per wrap (113,000 over 77 wraps); 452 KB nothing reads | version bump back |
| R5 | `HANDOFF.md` "Key Design Decisions" section (duplicates closure reports and memory) | ffbapp | 20,341 to about 6,000 chars: ~3,600 tokens per session that reads it | git history |
| R6 | `ffbapp-pipeline-state.md` (141 KB chronology) and the route memories whose own "delete when" condition has passed (pricing, name screening, entity fees, league sampling) | auto-memory | index from 39 to about 25 entries, ~1,000 tokens per session; stale recall | files are in git-tracked memory dirs (OPEN VERIFY: they are not; copy before deleting) |
| R7 | Contradictions 1, 3, 4 from 1f: drop "substrate" from the global ban or scope voice bans to chat; rewrite `ffbapp/CLAUDE.md` line 3 and the "When development starts" section; replace the duplicated standing rules with one pointer to `project-context.md` | `~/.claude/CLAUDE.md`, `ffbapp/CLAUDE.md` | ~300 tokens; one fewer rule the model demonstrably ignores | git |
| R8 | ffbapp-specific prose out of keelswell skills (38 strings: Epic 4, wave 4B, row 51 dates, RQ, `tests/verify-fast.sh`) into `ffbapp/docs/keelswell-local.md` | keelswell `skills/` | portability; ~3,000 chars per skill copy | git |
| R9 | The three-copy layout in keelswell (`skills/`, `.claude/skills/`, `.agents/skills/`) down to one source plus a build step | keelswell | the Model Policy class of drift | git |

### Migration, batches 1 to 5: additions

Each mechanism lists the finding it fixes (Phase 3 numbering), the metric that shows it worked, the build cost, and the failure mode it could introduce. Prefer the check that runs without a model.

| Batch | Mechanism | Fixes | Metric | Build cost | Failure mode introduced | Owner |
|---|---|---|---|---|---|---|
| 1 | `bin/wave-state`: one script printing worktrees, branches, PR states, closure dirs, collected test counts as JSON; `bmad-wrap` writes the HANDOFF state table and kickoff fields from it; `bmad-status-wave` rebuilt as a thin renderer of the same JSON | 5, 6, 8 | wrong state claims per kickoff: 5 of 79 to 0 | ~150 lines Python plus wrap text; half a day | a script bug misreports state as confidently as prose did; keep the raw `git worktree list` and `gh pr list` output in the HANDOFF appendix | keelswell (script), ffbapp (config) |
| 1 | `bin/sweep` (verify MERGED, remove, delete local and remote, refuse own worktree) and `delete_branch_on_merge: true` on the repo | 6 | unnecessary questions per session: 24 of 143 to 0; stale remote branches: 12 to 0 | ~80 lines; two hours | a merged-but-unswept worktree holding an uncommitted file (the fictitious-name case) is destroyed; sweep must refuse any worktree with untracked files and name them | keelswell |
| 2 | Review-record CI check: a job on PRs whose branch or title marks a wave fails when `docs/wave-<id>/review-party.md` is absent or does not name the reviewed commit SHA | 1 | waves merged without a record: 8 of 18 to 0 | ~40-line script plus workflow job; two hours | a file written to satisfy the check (theater); requiring the reviewed SHA and the reviewer dispatch descriptions makes an empty record visible | keelswell template, ffbapp wiring |
| 2 | Closure-order CI check: on a wave PR, read `waves.md`, find any earlier epic whose waves are all merged and whose closure dir is absent, fail with the epic named | 1 | closure lag: 7 days (Epic 4) to under 2 | needs a machine-readable wave map (a strict table or `waves.yaml`); half a day | a follow-up PR that is not a wave must be exempt, so the wave marker (title prefix or label) has to be reliable; a deliberate deferral needs a dated amendment the script reads | keelswell |
| 2 | `bmad-dev-wave` step 9 runs `verify-db` as well as `verify-fast`; test-reach lint in the fast lane (`pytest.raises` without `match=`, assert-free tests, `is not None`-only asserts) | 1, 3 | reach-lint findings per PR trend to 0; post-merge defects per epic | lint: ~60-line AST script or ruff PT rules; two hours | false positives on legitimate existence checks; allow a per-line opt-out with a reason | keelswell (lint), ffbapp (wiring) |
| 3 | Explicit `model:` on every dispatch in `bmad-dev-wave`: implementation sonnet, test design and reviewers frontier; a PreToolUse hook on `Agent` that denies an implementation dispatch whose prompt lacks the rules marker and the acceptance clauses | 2, 3 | reviewer tier compliance 100%; implementer prompts carrying rules: 14 of 18 to 18 of 18 | hook ~40 lines; prompt template in the skill; one day | frontier reviewers raise per-wave input cost (measure in batch 4); a marker can be present with stale content, so the hook checks the file hash, not the marker alone | keelswell |
| 3 | Wave marker file written by `bmad-dev-wave` step 1 and removed at step 12; PreToolUse hook denies `Edit` and `Write` under `ffbapp/` and `tests/` in the orchestrating session while the marker exists | orchestrator drift (1C, 5A) | orchestrator code edits during a wave: 202 to 0 | hook ~30 lines; two hours | a crashed wave leaves the marker and blocks a quick fix; the hook message names the marker so it can be removed by hand | keelswell |
| 4 | `bin/wave-cost`: sum `message.usage` per session and per subagent from the transcript directory; `bmad-wrap` appends one `metrics.csv` row (wave, PR, tokens by role, questions by class from `AskUserQuestion` calls, rework commits, review record present, closure status) | 10, 8 | a row per wave; cost per wave visible; rework and question trends | ~120 lines; half a day | transcript format drift breaks the parser; fail soft and mark the row incomplete | keelswell |
| 4 | Keelswell CI: changelog line required on any `version:` bump; `diff -r` between the source tree and instance copies | 8 | changelog lag: 17 days to 0; sync drift lines: 7 to 0 | ~20-line workflow; one hour | none material | keelswell |
| 5 | Pre-wave forks pass: test design first, every open question in one founder pre-read with a tagged recommendation, dispatch only after rulings; wrap auto-selects its recommended option unless RQ overrides at the wrap; a soft cap on questions per wave that halts with a pre-read instead of asking inline | 4 | S-class re-asks 0; questions per wave under 4 excluding the pre-read; ceremony questions 29 to 0 | skill text only (model-remembered, the weakest kind); half a day | batching forks conflicts with the global one-at-a-time rule (decision 3); auto-selecting the wrap option removes a decision RQ overrode 3 times in 17 wraps | keelswell |

Sequence: batch 0 in one session (all reverts are `git revert`); batch 1 next, because batches 2 and 4 read `bin/wave-state`; batch 2 before the next wave 6B opens, so 6B is the first wave that cannot merge unreviewed; batch 3 with 6B's dispatch; batch 4 at 6B's wrap; batch 5 after one epic of metrics shows where the questions actually come from.

### Open decisions

1. Gating: should a closure with any CONCERNS verdict block the next epic's first wave until every CONCERNS item has an owner and a destination, or stay informational as it is today (4 of 5 closures YELLOW and merged unchanged)?
2. Roster: do the 25 persona launchers and the Wheel of Time layer stay in Keelswell for future projects' planning phase (pruned only from ffbapp), or go entirely, leaving party-mode domain rosters without names?
3. Forks: for the pre-wave forks pass, will you take a wave's open questions as one batched pre-read, which contradicts your one-at-a-time rule, or one at a time as now, which keeps the per-wave interview?
