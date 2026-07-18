# Changelog
All notable changes to Keelswell. Format: Keep a Changelog; versioning: semver.

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
