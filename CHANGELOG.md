# Changelog
All notable changes to Keelswell. Format: Keep a Changelog; versioning: semver.

## [Unreleased] - 2026-09-11
### Changed
- Upstream refresh: bmad-method 6.10.0 -> 6.12.0 (Phase 0 of
  docs/harness-conversion-plan.md; runbook docs/upstream-refresh-runbook.md,
  invocation pinned to `npx bmad-method@6.12.0`, no `--modules`). What
  changed upstream and landed here:
  - BMM is skills-first: five agents (analyst, pm, ux-designer, architect,
    dev); bmad-agent-tech-writer retired (upstream removals.txt). Eight
    new skills in .claude/skills (bmad-build, bmad-build-auto,
    bmad-deep-recon, bmad-review, bmad-walkthrough, bmad-project-context,
    bmad-editorial-review, bmad-review-verification-gap); three removed
    (bmad-check-implementation-readiness, bmad-index-docs, bmad-shard-doc);
    21 old names retained as v6 compatibility shims that forward to their
    replacements (installShims: true recorded in manifest.yaml; upstream
    removes shims at v7). 106 -> 111 skill dirs.
  - _bmad/scripts/ re-synced from upstream: resolve_config.py and
    resolve_customization.py now import a new config_utils.py (same
    four-layer and three-layer merge, same CLI); render_skill.py added
    (bmad-build and bmad-build-auto shell out to it via `uv run`, so uv is
    now an upstream expectation). memlog.py unchanged. Finding: the
    installer wipes and re-copies _bmad/scripts/ on every install, so the
    directory is installer-owned, not a fork seam. Phase 1 must put its
    gate script elsewhere.
  - _bmad/config.toml regenerated: 38 agent blocks (bmm 5, cis 6, tea 1,
    keelswell 26), no duplicates; the _bmad/custom/config.toml overlay
    pins re-win at resolution (all 13 Wheel of Time names verified).
    manifest.yaml now records keelswell as an installed module (v0.8.0,
    localPath = the checkout the refresh ran from) and bumps core/bmm to
    6.12.0. Per-module config.yaml timestamps and files-manifest.csv
    regenerated (class C). Installer also creates ignored _bmad/keelswell/,
    _bmad/render/, _bmad/{core,bmm}/v6-shims/, and _bmad/agents/config.yaml
    (it treats the fork's _bmad/agents/ persona archive as a module dir).
  - Class B catalogs restored per the runbook (bmad-help.csv,
    skill-manifest.csv, core and bmm module-help.csv), then bmad-help.csv
    re-curated by hand: rows for the three removed skills dropped, rows for
    the five new real skills added from the 6.12 module-help sources, the
    Core and BMad Method _meta docs URLs updated. Rows for the 21 shim
    names were left in place (they still resolve, through forwarders).
- Not adopted, and why:
  - External module upgrades: tea v1.19.0 (v1.26.0 available), cis v0.2.1
    (v0.3.2), bmb v2.1.0 (v2.2.2), bmad-loop v0.8.1 (v0.11.1). All four are
    `channel: pinned` in manifest.yaml and the installer re-asserts pins
    under --yes; unpinning is a separate decision (`--pin code=tag`).
    tea v1.26.0 still declares only bmad-tea, so bmad-agent-qa remains
    keelswell-declared either way.
  - Upstream's 6.12 edits to the five vanilla bmm agent skills (menus
    re-pointed at bmad-deep-recon and bmad-project-context) and the
    bmad-retrospective rewrite: the fork's marketplace copies win over the
    upstream package for the same skill id, so these did not land. The
    mirrors still route through shim names (bmad-market-research,
    bmad-document-project, ...), which work until upstream drops shims at
    v7. Re-basing the mirrors on 6.12 is a follow-up, not part of this
    refresh.
  - The retirement of bmad-agent-tech-writer: the fork keeps Loial (see
    Added).
  - install.sh phase 4's `--modules bmm,cis,tea,bmb`: on an existing
    install it deselects and deletes bmad-loop, so the refresh used the
    runbook's line without it. The runbook text saying the two invocations
    are identical is stale.
  - skill-manifest.csv and the core/bmm module-help.csv were restored to
    their 6.10 content as the runbook prescribes; they now describe the
    pre-refresh layout (nothing fork-side reads them; the installer
    regenerates them on the next run).
- Post-refresh agent roster (38), by declaring module:
  - bmm (upstream module.yaml, names pinned by the overlay): Moiraine
    Damodred (analyst), Egwene al'Vere (pm), Perrin Aybara (architect),
    Mat Cauthon (dev), Min Farshaw (ux-designer).
  - cis (upstream, overlay-pinned): Siuan Sanche, Nynaeve al'Meara,
    Logain Ablar, Birgitte Silverbow, Thom Merrilin, Morgase Trakand.
  - tea (upstream, overlay-pinned): Galad Damodred (bmad-tea).
  - keelswell module.yaml (26): Rand al'Thor (bmad-master), Aviendha
    (bmad-agent-qa), Loial (bmad-agent-tech-writer); the eight
    architecture-pack agents Verin Mathwin, Elayne Trakand, Cadsuane
    Melaidhrin, Androl Genhald, Rhuarc, Berelain sur Paendrag, Lan
    Mandragoran, Sorilea (module label "arch" via the overlay); the fifteen
    custom agents Tam al'Thor, Tuon, Setalle Anan, Hurin, Gareth Bryne,
    Damer Flinn, Bayle Domon, Juilin Sandar, Jain Farstrider, Basel Gill,
    Talmanes Delovinde, Egeanin Tamarath, Aludra, Leane Sharif, Tarna Feir.
  - No agent is declared by more than one module. bmad-loop declares none;
    it is BMAD's outer orchestrator (uv-installed Python tool, module half
    only installed here) that invokes upstream bmad-build-auto per story.

### Added
- module.yaml declares bmad-agent-tech-writer (Loial, Technical Writer).
  Upstream bmm 6.12 no longer declares the code, so without this the
  overlay's name pin resolved to a name-only descriptor. Fork-only count
  25 -> 26. The overlay pin in _bmad/custom/config.toml is now redundant
  and left in place.
- .gitignore allowlists _bmad/scripts/config_utils.py and
  _bmad/scripts/render_skill.py so the tracked resolvers keep working
  from a fresh clone. templates/.gitignore.template still carries the old
  allowlist (follow-up).

### Fixed
- Nine tracked .claude/skills copies of customize.toml (the seven bmm
  agents, bmad-master, bmad-tea) still carried the pre-0.6.0 voice fields;
  the refresh re-copied them from the skills/ sources, which win. Every
  fork mirror in .claude/skills now matches its skills/ source exactly.
- config/agent-names.yaml.default had 32 agents against the 38-agent
  roster of record (stale since 0.7.0), which made `install.sh
  --validate-only` fail before this refresh. Synced; validation exits 0.

## [0.8.0] - 2026-08-24
### Added
- Two custom agents forming a design maker/critic pair, deliberately
  split so neither grades its own work: agent-web-designer (Leane
  Sharif, web design -- visual system lock as a hard gate, design
  canvases via the `design` skill, published page artifacts via
  `artifact-design`, chart and dashboard work via `dataviz`, real
  front-end implementation, and a browser verification loop at 375,
  768, and 1280 in both light and dark) and agent-design-critic
  (Tarna Feir, design critique -- adversarial responsive and theme
  sweeps, design-system conformance measured value against expected,
  craft review of states and typographic detail, hierarchy and
  first-impression read, and a single go/no-go ship verdict with a
  blocking list). Custom roster 13 -> 15, full roster 36 -> 38.
- Leane is the first custom agent with source-edit authority; every
  other custom agent is advisory under folder dominion. The deviation
  is deliberate and stated in her operating rules: visual craft is a
  pixel-level loop that dies if each two-line change has to be handed
  off as a diff. Her authority is bounded to the presentation layer
  (styles, tokens, markup and class names, static assets,
  presentational components), never data fetching, state, routing, or
  business rules, and never a new dependency without asking. Tarna
  holds the opposite constraint -- she cannot edit anything, which is
  what keeps her verdict worth having.
- Pipeline the pair is built for: Leane locks the visual system and
  stops for approval, Leane builds, Tarna sweeps and ranks defects,
  Leane burns the list down, Setalle Anan gates WCAG conformance.
  Both agents route accessibility to Setalle and page performance to
  Jain Farstrider rather than issuing parallel verdicts.
- Touched the `skills/` and `.claude/skills/` trees, the `agents/`
  sources, module.yaml (roster plus the fork-only count in its header
  comment, 23 -> 25), marketplace.json, config/agent-names.yaml,
  _bmad/custom/module-help.csv, and the README roster line.
  marketplace.json plugin version and the README install pin bumped
  0.7.0 -> 0.8.0. The `.agents/skills/` tree carries only bmad-*
  skills and was left alone, matching the existing custom agents.

## [0.7.1] - 2026-08-07
### Fixed
- Min Farshaw's voice did not come through on activation: hers was the
  only core-agent communication_style with no character anchor (no
  world-role, no lore vocabulary; "viewing" read as a generic research
  term), so the agent played a generic terse persona -- reproduced by
  activation probe. Voice amended keeping the original's three beats
  (anti-court plainness, observed-vs-inferred discipline, tease then
  truth) and adding anchors: tavern-corner people-watcher, coat and
  breeches among silk gowns, viewings reported images-first with
  meaning labeled unknown. Probe re-verified in character. skills/
  and .agents/skills/ copies updated; isi and ffbapp instance trees
  updated in place.

## [0.7.0] - 2026-08-07
### Added
- Four custom agents (slate v3), from the 2026-08-07 bench-gap review
  of the ffbapp PRD: agent-bizops (Basel Gill, business operations --
  entity formation prep, bookkeeping, tax calendar and nexus,
  insurance worksheets, compliance calendar; preparation only, never
  professional advice, every artifact closes by naming the CPA,
  attorney, or broker who signs off), agent-llm (Talmanes Delovinde,
  LLM surface engineering -- grounding pipelines, eval harnesses,
  calibrated language, per-answer inference cost, injection exposure),
  agent-mobile (Egeanin Tamarath, mobile and app-store distribution --
  guideline review, IAP vs direct billing, release passage plans,
  push and disclosure policy, terms watch), and agent-marketing
  (Aludra, marketing and SEO -- technical SEO readiness, content
  engines, launch sequencing, listing and landing craft, measurement
  hooks). Custom roster 9 -> 13, full roster 32 -> 36. Touched both
  skill trees, the agents/ sources, module.yaml, marketplace.json,
  config/agent-names.yaml, _bmad/custom/module-help.csv, and the
  README roster line. marketplace.json plugin version and the README
  install pin bumped 0.4.1 -> 0.7.0 (both had gone stale at 0.4.1
  through the 0.5.0 and 0.6.0 releases).

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
