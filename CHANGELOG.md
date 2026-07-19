# Changelog
All notable changes to Keelswell. Format: Keep a Changelog; versioning: semver.

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
