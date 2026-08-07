# Changelog
All notable changes to Keelswell. Format: Keep a Changelog; versioning: semver.

## [0.6.0] - 2026-08-07
### Changed
- The nine core agents now speak in their Wheel of Time character's
  voice: communication_style rewritten in character for Moiraine
  (analyst), Egwene (pm), Perrin (architect), Mat (dev), Aviendha
  (qa), Loial (tech-writer), Min (ux-designer), Galad (tea), and
  Rand (bmad-master). QA and bmad-master gain the field (their
  customize.toml carried no persona fields); the carried personas'
  Style lines (agents/bmm-qa.md, agents/core-bmad-master.md) align
  with the new voices. Each voice keeps the old field's working
  signal: Mat still speaks in file paths and AC IDs, Galad keeps
  strong opinions weakly held as the surrendered sword form, Rand
  keeps route-and-say-why. identity, principles, roles, and menus
  unchanged. Touched both skill trees, the agents/ sources, and the
  _bmad installed copies (21 files including this changelog).
  Verified by resolver runs on every edited skill and activation
  probes on Mat, Aviendha, Galad, and Rand.

## [0.5.0] - 2026-07-20
### Changed
- The nine custom agents' skill ids renamed from persona form to role
  form: agent-tam-althor -> agent-sre, agent-tuon -> agent-growth,
  agent-setalle-anan -> agent-accessibility, agent-hurin ->
  agent-analytics, agent-gareth-bryne -> agent-legal,
  agent-damer-flinn -> agent-ml, agent-bayle-domon -> agent-billing,
  agent-juilin-sandar -> agent-appsec, agent-jain-farstrider ->
  agent-performance. Aligns the custom nine with the
  bmad-agent-<role> convention and the config/agent-names.yaml roster
  keys, so the skill picker reads by role. Personas are unchanged in
  descriptions and activation (talk-to-<persona> routing intact).
  Touched both skill trees, the agents/ sources, module.yaml,
  marketplace.json, and _bmad/custom/module-help.csv (30 files,
  count-asserted). Downstream installs keep the persona-named skill
  dirs until their next refresh -- prune per
  docs/upstream-refresh-runbook.md (verify installer merge behavior
  at refresh time).

### Fixed
- install.sh phase4_upstream now carries --modules bmm,cis,tea,bmb,
  aligning the live installer with the README install command (R1
  follow-up; quickstart v8 Appendix C).

## [0.4.1] - 2026-07-19
### Fixed
- README install command now carries --modules bmm,cis,tea,bmb
  (scratch-verified: all four module config.yaml files created, 97
  skills, valid config.toml -- closes F-10 for documented installs).
- .agents/ tree aligned in place: the 13 vanilla persona skills and
  bmad-retrospective copies (28 files, each verified byte-identical to
  their v0.2.0 baselines first) now carry the v0.3.0/v0.4.0 Wheel of
  Time content. TEA knowledge-base author attributions untouched. The
  tree remains unmanaged by the installer, per the refresh runbook.
- bmad-agent-qa and bmad-master customize.toml fallback identities
  aligned to their carried personas (Aviendha, Rand al'Thor).
- _bmad/custom/module-help.csv backfilled with the 6 pre-existing
  custom agents (now lists all 9).
- Runbook: F-10 section updated; logged the fresh-install descriptor
  nuance (vanilla 13 registry blocks show upstream names in OTHER
  projects because overlay pins do not travel with marketplace
  installs; skills themselves still greet under Wheel of Time names).

## [0.4.0] - 2026-07-19
### Added
- module.yaml: the keelswell custom-module descriptor. Kills the
  installer's "could not locate module.yaml" warnings, records the real
  module version in installed manifests (closes F-9), scopes install
  answers correctly, and writes descriptor blocks for the 19 fork-only
  agents (8 arch, 9 custom, bmad-master, bmad-agent-qa) into
  _bmad/config.toml under their Wheel of Time names -- party-mode and
  the help catalog can now see the full roster. Deliberately does NOT
  redeclare the 13 upstream-declared vanilla agents: the installer
  emits duplicate [agents.*] tables for cross-module redeclarations,
  corrupting config.toml (scratch-verified); their WoT names remain
  pinned by the _bmad/custom/config.toml overlay.
- bmad-retrospective shipped via marketplace.json + skills/ mirror (39
  -> 40 entries), so the fork's Mat Cauthon recast survives upstream
  refreshes (custom-module skills win over the upstream package for the
  same skill id).
- docs/upstream-refresh-runbook.md: closes F-6. Root cause of the
  .agents/ deletion (IDE-list reconciliation wiping a deselected
  platform's shared target_dir), proof the tripwire is disarmed
  (manifest now records claude-code only; scratch refresh left all
  1051 files untouched), the three refresh clobber classes with
  restoration steps, and the documented F-10 limitation
  (--modules bmm,cis,tea,bmb for full-function fresh installs).

## [0.3.0] - 2026-07-19
### Fixed
- F-5 closed: all 13 vanilla persona agents (6 BMM, 6 CIS, TEA) now carry
  their Wheel of Time roster names in every activation surface -- SKILL.md
  (both shipped copies), customize.toml identity, the agents/ and
  _bmad/agents/ persona files, and skill-manifest.csv trigger
  descriptions. Closing-line pronouns follow the new personas.
- bmad-retrospective's scripted dialog recast from Amelia to Mat Cauthon;
  bmad-agent-qa's scope boundary aligned to the dual provenance form
  "Galad Damodred / Murat (TEA)".
- _bmad/custom/config.toml overlay pins the 13 resolved display names,
  overriding the installer-owned _bmad/config.toml descriptor registry
  per its own custom-overlay contract (resolver-verified: 21 blocks, all
  Wheel of Time names).

## [0.2.0] - 2026-07-18
### Added
- Three custom agents: Bayle Domon (Monetization/Billing), Juilin Sandar
  (Application Security), Jain Farstrider (Performance/Capacity). 32 agents
  total.
- Two carried-persona rider launchers: bmad-master (Rand al'Thor) and
  bmad-agent-qa (Aviendha), making both invokable as real skills for the
  first time.
- config/agent-names.yaml and .default extended with the 3 new roster rows.
- bmad-master and bmad-agent-qa registered in _bmad/_config/bmad-help.csv
  (and the matching core/bmm module-help.csv files) as DF-1 carried-persona
  entry points; the 3 new single-persona custom agents intentionally left
  unregistered there per the sparse multi-capability-only rule.
- .claude-plugin/marketplace.json and skills/ mirror expanded to 39 entries.

## [0.1.0] - 2026-07-17
### Added
- 23-agent merged base (vanilla BMAD + Architecture Agent Expansion Pack).
- Six custom agents: SRE, Growth, Accessibility, Analytics, Legal, ML.
- Seven wave-development skills: create/dev/resume/status/merge waves, close-epic, wrap.
- core/config.yaml operational defaults; agent-names.yaml with install-time override.
- Project templates (settings.json, CLAUDE.md, TODO, HANDOFF, .gitignore) and install.sh.
- .claude-plugin/marketplace.json discovery manifest.
