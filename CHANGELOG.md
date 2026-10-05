# Changelog
All notable changes to Keelswell. Format: Keep a Changelog; versioning: semver.

## [Unreleased] - 2026-09-12
### Fixed
- The [IR] menu item of Rod and Archie opens a skill that exists
  (2026-10-05). Both `customize.toml` files pointed it at
  `bmad-check-implementation-readiness`, which bmad-method 6.12.0 removed:
  upstream folded the readiness gate into `bmad-sprint-planning` and
  re-pointed its own two menus there. The fork's copies of the bmm agents win
  over upstream's, so they kept the old target; the item has been dead in
  the fork since the 2026-09-11 refresh and in both instances since theirs
  on 2026-10-05. The two items now carry upstream's target and description.
  **What was measured.** Every `skill` named by a menu item in the 16
  `customize.toml` files resolves to an installed skill; before, these two
  did not.
  **The check.** `.github/workflows/ci.yml` gains a fifth step, "Every agent
  menu item opens a skill that exists": each `skill` in a
  `skills/*/customize.toml` menu must be a directory under `.claude/skills`.
  Run against the commit before this fix it fails on exactly these two
  items; run after, it passes. It is what will catch the same thing at the
  next upstream refresh.
  **Not touched.** The other menu items, which still route through v6 shim
  names that upstream removes at v7. No skill version: neither skill carries
  `metadata.version`.
- The secret scan scans again (2026-10-05). `.gitleaks.toml` had an
  allowlist and no `[extend] useDefault = true`, and a gitleaks config
  without that block replaces the default rules with none. Every commit in
  this repository since the first, 2026-07-09, passed a pre-commit scan that
  could not fail. Found when ffbapp, which has no config file and so runs
  the default rules, refused the 6.12 refresh commit on five checksum rows.
  **What changed.** `.gitleaks.toml`: the `[extend]` block, and two
  allowlists by pattern in place of five by path. The hook pipes the staged
  diff to `gitleaks stdin`, which carries no file paths, so a path allowlist
  never applied there. One pattern is an installer manifest row (a quoted
  path, then a quoted sha256); the other is the truncated public JWT header
  in upstream's TEA doc fixture. The runbook's refresh section gains step
  4a.
  **What was measured.** With the old file a line shaped like a GitHub
  token passes; with the new one it is caught, and so is a complete test
  JWT. Under the new file every tracked line of this repository, scanned as
  one diff, is clean. Full history under the default rules: 145 findings in
  three commits, all `generic-api-key`, all in three places: manifest rows,
  that one doc fixture, and `gitleaks-report.json`, an old scan report that
  quoted the same rows and was untracked on 2026-09-28. No provider-specific
  rule fired. The same scan of ffbapp and green-ledger found only the first
  two kinds.
  **Not done.** The 42 findings in the deleted report file stay in history.
  green-ledger carries a copy of the same no-rule config and needs the same
  fix by hand. A fresh instance gets no config from the installer.
  **At risk.** (1) The default rules are what they are: a secret that
  matches no rule was never going to be caught and still is not. (2) The
  eval harness copies this file into each trial; a trial fixture that trips
  a default rule will now refuse its commit.

### Changed
- The instance helper can put the catalog rows back after an upstream
  refresh, and the runbook says how to refresh an instance (2026-10-05).
  **Why.** Both instances are on bmad-method 6.10.0; the fork has run
  6.12.0 since 2026-09-11. RQ ruled: refresh them to 6.12.0, the version the
  fork was built against, not upstream's newer 6.12.1.
  **What changed.** `tools/theme_removal_instance_step.py` gains
  `--catalogs-only`, which skips the skill files, the agents tables and the
  pins and writes the Keelswell rows of the two catalogs alone. It now
  writes the menu codes of the 23 other persona rows as well as the 15
  custom ones: the 6.12 installer regenerates the catalog with codes that
  repeat (architect `A` beside analyst `A`, integration architect `AIA`
  beside infrastructure analyst `AIA`; 31 unique codes in 39 rows), where
  6.10 made them unique. `docs/upstream-refresh-runbook.md` gains
  "Instances: refreshing upstream": the command and why each flag, five
  steps after it, and what the rehearsal measured.
  **What was measured.** The refresh was run on scratch copies of both
  instances. The installer exits 0; each skill tree comes out byte-identical
  to the fork's `.claude/skills`; `_bmad/custom/config.toml` is preserved and
  the resolver shows the 38 names; after `--catalogs-only` all 39 Keelswell
  rows equal the instance's current rows; validation exits 0; 257 and 12
  unit tests pass in the refreshed tree.
  **Not touched.** The instances: the refresh is RQ's to run. `install.sh`.
  **Prediction.** On the real instances the staging list is 306 paths in
  ffbapp and 569 in green-ledger, validation exits 0, and `/bmad-help` in
  ffbapp reports no config failure with the `--no-project` edit gone.
  **At risk.** (1) The pins move tea from v1.19.1 to v1.19.0 in both
  instances and bmad-loop from v0.9.0 to v0.8.1 in ffbapp. (2) Three
  upstream skills are removed, and the fork's pm and architect menus still
  name one of them, `bmad-check-implementation-readiness`: that item is
  already dead in the fork. (3) ffbapp is mid-epic; wave 6B will be the
  first wave run on 6.12 upstream skills.
- The master and QA launchers carry their own principles and stay quiet
  about what an instance never has (2026-10-05). Found on the first run of
  a rewritten voice: `/bmad-master` in ffbapp greeted as Max, then reported
  a missing persona file and an empty menu.
  **What changed.** `skills/bmad-master/SKILL.md` and
  `skills/bmad-agent-qa/SKILL.md`. (1) The Overview of each now holds the
  core principles of its carried persona, with the master's boundaries and
  Quinn's story-file permissions, word for word from
  `_bmad/agents/core/bmad-master.md` and `_bmad/agents/bmm/qa.md`. No
  instance has `_bmad/agents/`: the installer never copies it, so those
  lines had never reached one. (2) Step 3 says a missing persona file is the
  normal case in an installed project and is not mentioned. (3) Step 8 says
  an empty `{agent.menu}` renders nothing and is not mentioned: the master
  asks for the need in one line, Quinn asks what is to be reviewed. Neither
  `customize.toml` has ever had a menu item.
  **Not touched.** The two carried persona files, both `customize.toml`
  files, the voices, every other launcher. No skill version: neither skill
  carries `metadata.version`.
  **Prediction.** After the two files reach ffbapp, `/bmad-master` greets
  as Max with no caveat about a file or a menu.
  **At risk.** The principles now live in two places in the fork, the
  launcher and the carried file; an edit to one must reach the other.
- Theme removal, follow-ups RQ ruled on 2026-10-03 after PR 5 (PR 6).
  bmad-dev-wave 1.12.1 -> 1.12.2.
  **What changed.** (1) No agent is gendered in the files PR 5 left as
  found: `skills/bmad-dev-wave/SKILL.md` (11 lines), the notes of
  `scripts/reviewer-triggers.yaml` (6 values and one comment), one docstring
  in `scripts/select_reviewers.py`, one in its test, and 38 lines of
  `docs/agent-inventory.md`. Each pronoun became the name, the role id or
  "it". RQ lifted ruling (e) for these words; no key, role, skill, display,
  path, glob, pattern, code token or assertion changed, and the 257 tests
  pass with no edit to what they assert. (2) `skills/bmad-master/SKILL.md`
  says Max: heading, overview, the fallback identity, the greeting, the
  stays-active line, and "talk to Max, the BMad Master" in the description,
  in step in `module.yaml` and `_bmad/config.toml`. (3) `agents/` is deleted
  in this PR's second commit: 38 carried-persona files the installer never
  read, that reached no instance, and that after PRs 2 to 5 differed from
  every surface that is read. `install.sh` still names the directory in
  phase 3 and in one phase-6 grep; both skip a directory that is not there.
  `docs/agent-inventory.md` still cites `agents/` paths for the pass it
  records.
  **How.** One subagent did the pronoun pass; the diff of the two Python
  files is two docstrings. A sentence that was more than a one-word swap is
  quoted in the PR body.
  **Grade of PR 5's prediction.** Not gradable yet: the instance hand step
  has not been run. On scratch copies of both instances the helper's result
  validated with exit 0 and `resolve_config.py --key agents` showed the 38
  new names; in ffbapp that needed 13 name pins the instance never had, a
  fourth surface the prediction did not name.
  **Not touched.** `install.sh`; the graders; trigger patterns and selector
  logic; CHANGELOG history, which still quotes the old inert text of the
  bizops row; `_bmad/config.toml` descriptions of the 11 upstream-declared
  seats, which keep upstream's similes; "Tess / Murat (TEA)".
  **Prediction.** After the hand step, a `/bmad-help` listing in either
  instance shows no old name, and a wave run in ffbapp dispatches reviewers
  by the same role ids as before.
  **At risk.** (1) The eval pairs were not re-run after words changed in
  `bmad-dev-wave/SKILL.md`; the changed lines are in notes and rationale,
  not in a step's instruction. (2) The instance helper was applied to
  scratch copies and dry-run against the instances; it has not yet been run
  for real on either.
  **The instance helper.** `tools/theme_removal_instance_step.py`, with a
  runbook section, "Instances: the theme removal is a hand step". It names
  an instance's four surfaces (skill files, `[agents.*]` lines, name pins,
  catalog rows), aborts before writing on any drift from fork commit
  0493ff6, and never stages or commits.
- The 15 custom agents speak in a voice derived from the role (theme
  removal, PR 5 of 5, 2026-10-03). No skill version changes: no persona
  skill carries `metadata.version`.
  **What changed.** Two layouts, two forms. Eight skills with an Overview
  paragraph (agent-sre Reese, -growth Grover, -accessibility Cici, -analytics
  Lytta, -legal Lex, -ml Mel, -web-designer Webb, -design-critic Critt) gain
  a `## Voice` section as the arch seats did. Seven with an Identity block
  (agent-appsec Seth, -billing Bill, -performance Perry, -bizops Bizzy, -llm
  Elle, -mobile Moby, -marketing Mark) have their `Identity:` and `Style:`
  lines rewritten, and every principle, scope line and greeting that used
  the old image now states the same rule in plain words: the inn (Bizzy),
  the fireworks (Mark), the ship and its empire (Moby), the deadpan aside
  (Elle), the roads travelled (Perry), and "remade your own presentation"
  (Webb). One capability name changed, its code did not: `[RP] Release
  Passage Plan` is `[RP] Release Plan`. Four descriptions changed, in step
  in the SKILL.md, `module.yaml` and `_bmad/config.toml`: legal, bizops and
  design-critic lose a gendered pronoun, marketing loses "every display
  prepared to the second and priced to the shot". Every "Use when" trigger
  is intact. `docs/agent-inventory.md` quotes the new design-critic line.
  **How.** The brief with the lessons of PRs 2 to 4; two author subagents,
  one per layout; one reviewer that wrote neither; one sweep subagent over
  the whole tree. Review findings, all applied: Moby cited guideline numbers
  one store does not have and a review status no stateless skill knows; Seth
  disagreed exactly as Seku does, and now argues from the file and line of
  the shipped diff; Bizzy's habit covered two of six capabilities; Elle
  reported an eval score nothing in the skill produces; Reese, Perry, Lytta
  and Lex each fixed one unit or one capability's method onto every output;
  Mark kept a trait of the old character.
  **Grade of PR 4's prediction.** Holds: seven custom agents carried a
  book-derived image (six predicted) and five a gendered pronoun (four
  predicted), and the batch rewrote Identity lines, Style lines, principles
  and greetings.
  **The sweep, whole tree.** Old names: none outside the nine pre-0.5.0
  skill ids kept in the inventory. Book words: none. All 38 names agree
  across the mapping, its default, module.yaml, both config files, the 16
  `customize.toml` files and the trigger table; 15 descriptions agree across
  three files; 21 carried copies are byte copies of their skill;
  `install.sh --validate-only --skip-mcp-check` exits 0.
  **Not touched.** `agents/*.md` (ruling d): nine files there still hold
  images, about 22 by the sweep's count. Capability codes, operating rules,
  artifact locations, provenance paragraphs. Everything R1 to R5 built.
  **Left as found, for RQ to rule on.** (1) Gendered pronouns for agents
  remain in `skills/bmad-dev-wave/SKILL.md` (11 lines), in the notes of
  `reviewer-triggers.yaml` (6 lines), in two comments of
  `select_reviewers.py` and one of its test, all R5 work under ruling (e),
  and in 38 lines of `docs/agent-inventory.md`. (2) `skills/bmad-master/
  SKILL.md` never says Max: it calls itself "the BMad Master", as its
  description always did. (3) `_bmad/config.toml` descriptions for 11
  upstream-declared agents still carry upstream's similes ("a bard weaving
  an epic"); the overlay pins only their names. (4) "Tess / Murat (TEA)" in
  the QA skill and its carried persona. (5) Whether `agents/` should be
  deleted: the installer never reads it, it reaches no instance, and it now
  differs from every surface that is read.
  **Prediction.** After the instance hand step, `install.sh --validate-only
  --skip-mcp-check --target-project` exits 0 on ffbapp and green-ledger,
  `resolve_config.py --key agents` shows the 38 new names, and no code in
  either `bmad-help.csv` repeats.
  **At risk.** (1) No agent was run in any of the five PRs: the voices are
  reviewed text, not measured behavior. (2) Four voices run 2 to 10 words
  over the brief's 110. (3) Many voices open on "distrusts"; they read as
  one hand. (4) The eval pairs were not re-run; pair C's graders match
  reviewers by role and skill id, which did not change.
- The six cis seats speak in a voice stated plainly, not as a simile (theme
  removal, PR 4 of 5, 2026-10-03). No skill version changes: no persona
  skill carries `metadata.version`.
  **What changed.** `communication_style` in the `customize.toml` of
  bmad-cis-agent-brainstorming-coach (Brayden), -design-thinking-coach (Dez),
  -innovation-strategist (Inna), -creative-problem-solver (Olive),
  -storyteller (Ori) and -presentation-master (Preston). Upstream's strings
  were each one simile (improv coach, jazz musician, chess grandmaster,
  Sherlock Holmes, bard, creative director). Each now states the temperament
  the simile pointed at, how the agent opens a task, how it disagrees (a
  question or a reframing, from the seat's own method) and one habit of
  wording. Six SKILL.md files and their byte copies under `_bmad/agents/cis/`
  change one word: "dismisses her" or "him" is now "them". Seven carried
  copies under `_bmad/agents/bmm/` and `_bmad/agents/tea/` get the same word,
  which PR 2 changed in the skills only; they are byte copies again.
  **How.** The brief with the lessons of PRs 2 and 3; one author subagent,
  one reviewer that had not written them, which read each method skill's
  facilitator stance. Its findings, all applied: Brayden's 'yes, and' read as
  the coach adding ideas, which the facilitator stance forbids, and the
  running count of ideas is something no script tracks; Dez answered every
  doubt with a prototype, one step of seven, and "describes users in scenes"
  invited invented users; Olive labelled every statement, solution steps
  included, and reasoned for the user where the skill says to help the user
  reason; Preston's three-second test was asked of a whole piece; Inna had
  no warmth.
  **Grade of PR 3's prediction.** Holds: the six voices are in
  `customize.toml`, with no book word and no old name, and the work was the
  form and the pronoun.
  **Not touched.** `identity` in the six files, which is upstream text and
  still carries backstory ("Twenty years", "Former McKinsey strategist");
  titles ("Oracle", "Maestro"); principles and menus; SKILL.md bodies beyond
  the pronoun; `agents/cis-*.md` (ruling d); the method skills; the custom
  seats; everything R1 to R5 built.
  **Prediction.** PR 5 finds book-derived images in at least six of the 15
  custom agents (bizops, marketing, mobile, llm, performance, web-designer)
  and gendered pronouns in at least four, in SKILL.md bodies that the fork
  owns outright, so that batch rewrites Identity and Style lines and
  activation greetings, not one string.
  **At risk.** (1) No agent was run. (2) The identity strings and the new
  voices now disagree in register: a plain voice under a "Disruptive
  Innovation Oracle" title. (3) These six `customize.toml` files say "DO NOT
  EDIT -- overwritten on every update"; the fork's copies win over upstream
  through marketplace.json, as the renames already rely on.
- The eight arch seats gain a voice derived from the role (theme removal, PR
  3 of 5, 2026-10-03). No skill version changes: no persona skill carries
  `metadata.version`.
  **What changed.** A `## Voice` section, one second-person paragraph, in the
  SKILL.md of bmad-agent-arch-infrastructure-analyst (Ingrid),
  -cloud-architect (Skye), -data-architect (Jason), -integration-architect
  (Inez), -platform-engineer (Platt), -cost-optimizer (Costa),
  -security-reviewer (Seku) and -architecture-governor (Gov), placed after
  the Overview and before the resolution rules. Each says what the job makes
  the agent distrust, how it opens a task, how it disagrees, and the unit or
  artifact it speaks in. These seats never had a themed voice, so nothing was
  removed: the section is an addition and the Overview is not edited. The
  byte copies under `_bmad/agents/arch/` carry the same section.
  **How.** The PR 2 brief plus the lessons of its review; one author
  subagent, one reviewer that had not written them. Its findings, all
  applied: Seku put a STRIDE category on every finding, compliance gaps
  included; Skye and Gov disagreed the same way, and Gov's way only fitted
  an ADR; Ingrid cited requirement IDs the skill never assigns; Skye's one
  example was AWS only; Jason, Inez and Costa spoke in relational, REST and
  monthly terms on seats that also cover graph stores, gRPC and three-year
  TCO.
  **Grade of PR 2's prediction.** Holds: the arch voice lives in SKILL.md
  (there is no `customize.toml`), and the review found no "Opens by" and no
  narrowed duty of the kind PR 2 met. It did find the neighbouring mistake,
  a habit of wording narrower than the seat's range, in five of eight.
  **Not touched.** Frontmatter, Overview, activation steps, capabilities,
  operating rules and assets of the eight skills; `agents/arch-*.md` (ruling
  d), which now differ from their `_bmad/agents/arch/` copies by the new
  section; the roster descriptions in module.yaml and the config files; the
  cis and custom seats; everything R1 to R5 built.
  **Prediction.** PR 4 finds the six cis voices in `customize.toml`, already
  free of book words (they were upstream's own), and its work is the pronoun
  line and the four-part form, not theme removal.
  **At risk.** (1) No agent was run. (2) The opener restates the intake the
  skill limits to its design-heavy capabilities, so a research or checklist
  request may get one extra question. (3) The skill listing budget: each
  SKILL.md grew by about 100 words of body, none of description.
- The core nine speak in a voice derived from the role (theme removal, PR 2
  of 5, 2026-10-03). No skill version changes: no persona skill carries
  `metadata.version`.
  **What changed.** `communication_style` in the `customize.toml` of
  bmad-master (Max), bmad-agent-analyst (Analisa), -pm (Rod), -architect
  (Archie), -dev (Devon), -ux-designer (Yuki), -tech-writer (Ryder), -qa
  (Quinn) and bmad-tea (Tess): each now states two or three traits the job
  breeds, how the agent opens a task, how it disagrees, and one habit of
  wording, in 84 to 106 words with no gendered pronoun. The `Style:`
  paragraph of the two carried personas the launchers read
  (`_bmad/agents/core/bmad-master.md`, `_bmad/agents/bmm/qa.md`) says the
  same as its seat's string. Seven SKILL.md files change one word: "until the
  user dismisses her" or "him" is now "them".
  **How.** One style brief; one subagent wrote the nine; a second that had
  not written them reviewed each against the brief and the seat's unchanged
  duties. Its findings, all applied: Quinn's "files nothing that cannot be
  reproduced" would have barred traceability and risk findings, now "files
  nothing Quinn cannot back up", with the Given-When-Then and gate-verdict
  habit added; "Opens by" read as an instruction to act before the menu, now
  "Opens a task by"; Ryder's sentence contradicted itself; Tess led with
  traits kept from the old character; Max's "lets the user choose" met the
  "never free-hand the orchestration" principle and now excepts wave work.
  **Grade of PR 1's prediction.** Holds for names (0 in the core nine) and
  for the tests (257 and 12 pass in both trees with no edit). One miss: the
  sweep counted "viewings" in Yuki's string as a book word; this PR removes
  it.
  **Not touched.** `role`, `identity`, `principles` and menus in every
  `customize.toml`; every SKILL.md body beyond the one pronoun; `agents/*.md`
  (ruling d), so `agents/core-bmad-master.md` and `agents/bmm-qa.md` now
  differ from their `_bmad/agents/` copies in the Style paragraph;
  the arch, cis and custom seats; everything R1 to R5 built.
  **The default names.** `config/agent-names.yaml.default` now equals the
  mapping (RQ's ruling, 2026-10-03; RQ ran the copy). `--use-defaults` no
  longer puts the old names back. The old names are no longer the "from"
  side of phase 3: a later rename starts from the 38 new names.
  **Prediction.** PR 3 finds the eight arch seats carry their voice in
  SKILL.md, not in a `customize.toml`, and no review finding there repeats
  the "Opens by" or the narrowed-duty mistake, because the brief now rules
  both out.
  **At risk.** (1) No agent was run: whether a model follows the new voice,
  or still greets and shows the menu first, is unmeasured. (2) "them" for a
  named agent is new in these files. (3) Quinn and Tess both speak of
  probability and impact; the reviewer found them the hardest pair to tell
  apart. (4) With the new names as the default, a later whole-word rename away from Mark, Bill or
  Max would rewrite ordinary prose in the asset files.
- The Wheel of Time theme is gone from the roster: 38 names RQ chose replace
  it (theme removal, PR 1 of 5, 2026-10-03). bmad-dev-wave 1.12.0 -> 1.12.1,
  for the `display:` column of `scripts/reviewer-triggers.yaml` and one name
  in SKILL.md. No persona skill carries `metadata.version`, so none is bumped.
  **What changed.** `config/agent-names.yaml` holds the 38 new display names.
  The installer's phase-3 substitution (default name -> chosen name, whole
  word) was run as its own Python, not through `--rename`, which reads
  `/dev/tty`: 363 substitutions in `skills/`, 363 in the mirror, 140 in
  `agents/`. The same rule was then run over what phase 3 does not walk: the
  16 `customize.toml` files, `module.yaml`, `_bmad/config.toml`,
  `_bmad/custom/config.toml`, `_bmad/agents/` (23 carried personas),
  `_bmad/_config/skill-manifest.csv`, `_bmad/bmm/module-help.csv`,
  `docs/agent-inventory.md` and the runbook: 325 more. Short forms and names
  split across a line wrap (15 first names, 4 wrapped pairs) were renamed in
  23 files, `templates/TODO.md.template` and the QA row of
  `_bmad/_config/bmad-help.csv` among them. Words that need the books were
  cut from six voice strings (analyst, pm, dev, qa, tech-writer, tea), from
  the marketing agent and from the two QA persona files; README, module.yaml,
  marketplace.json and the runbook say "role-derived" or "the fork's display
  names" where they said Wheel of Time.
  **Rulings by RQ, 2026-10-03.** (a) the 38 names by role, with
  arch-data-architect changed from Dana to Jason the same day; (b) a fuller
  voice derived from the role, in PRs 2 to 5; (c) menu codes in the
  instances; (d) history keeps the old names; (e) nothing R1 to R5 built
  changes. The grader's display leg in `evals/graders.py` is left as it is
  (option 1).
  **What was measured.** Lines naming an old character in tracked files
  outside the mirror, CHANGELOG and docs/reviews: 856 in 132 files before,
  0 after outside the four files this entry leaves alone. Theme words: 0,
  bar one false match ("otherwise one" in upstream party-mode text). 257 and
  12 unit tests pass in both trees; `install.sh --validate-only
  --skip-mcp-check` exits 0; `diff -rq -x __pycache__` is empty per skill.
  **Not touched.** `config/agent-names.yaml.default` (still the old names: it
  is the "from" side of the rename, see at risk), `_bmad-output/session-wrap/`,
  `docs/harness-conversion-plan.md`, `docs/harness-conversion-prompts.md`,
  CHANGELOG history, `docs/reviews/`, every hook, gate rule, settings key,
  trigger pattern, the selector, the graders, `_bmad/scripts/`,
  `.claude/skills/bmad-eval-runner/`. Role ids and skill ids are unchanged.
  **Prediction.** PR 2 finds no old name and no theme word in the core eight
  when it opens them, and the roster test (coverage by role id) and
  `test_evals.py` pass with no edit.
  **At risk.** (1) Several names are short or ordinary words: Gov, Ori, Mark,
  Bill, Max. The grader's display leg is a substring test, so for those names
  it proves nothing; the role id and skill id legs still do. A later
  whole-word rename away from Mark, Bill or Max would rewrite prose in the
  asset files. (2) `./install.sh --use-defaults` copies the `.default` file
  over the mapping and would put the old names back into
  `config/agent-names.yaml` while the skills keep the new ones. (3) Pronouns
  and gendered turns of phrase written for the old characters remain in the
  persona text until PRs 2 to 5. (4) Four voice strings (architect, dev, ux,
  master) still carry images from the books with no book word in them. (5)
  Both instances still show the old names until the hand step. (6)
  `docs/agent-inventory.md` still lists nine pre-0.5.0 skill ids built from
  the old names (`agent-tam-althor` and eight more): they are the literal ids
  an instance carried and are left as the record. (7) Gov is now a name and
  `[GOV]` is a menu code in the data architect's skill.

### Added
- The first evals of a wave step: three balanced pairs, 18 headless trials,
  graded on end state (R5b of docs/reviews/harness-engineering-review-v1.md,
  2026-10-02). bmad-dev-wave 1.11.0 -> 1.12.0. The review found no step of
  the wave loop had earned its place by any outcome measure. This is the
  second of R5's two pull requests and it ends the review's do-now list.
  **What was built.** `skills/bmad-dev-wave/evals/`: `run_evals.py`, the
  harness; `graders.py`, six code graders; six tasks under `tasks/`, each
  with its prompt, its fixture named in `task.json` and a reference end
  state; the fixture project, three wave variants and two auto-memory
  variants; `README.md`. A trial is a copy of an installed instance with the
  fixture project over it, its own `git init`, a worktree holding the wave's
  work uncommitted, the status written through `wave_status.py`, the
  `step-N.done` markers that make `route` re-enter at the step under test, a
  real `verify` stamp, a `gh` first on PATH that logs and reaches nothing,
  and one `claude -p` session: Sonnet 5.5 parent, `--setting-sources
  project,local`, `--strict-mcp-config`, acceptEdits, four Bash allow rules,
  a turn cap and a dollar cap. Every flag is quoted from the docs in the
  README. The prompt is `/bmad-dev-wave 1A`, the step-9 answer given in
  advance, and where the session ends; the two tasks of a pair get the same
  bytes, asserted by test. No fixture carries an evaluation record, so pair C
  enters at step 8 and the real evaluator writes the PASS it needs.
  Auto-memory is the trial's own directory, through `autoMemoryDirectory` in
  the trial's `settings.local.json`; nothing under `~/.claude` is written.
  `scripts/tests/test_evals.py`, 11 tests with no model call: every reference
  end state passes its own grader, fails the other half of its pair, the
  starting state passes neither, the router re-enters where the task says,
  and each pair C wave fires what its task says. Those run in CI. The trials
  never do.
  **Ruling by RQ, 2026-10-02 (k).** A small stdlib harness, no container. A
  trial has no remote, a stub `gh`, bypass locked off and the deny and ask
  rules in force, so it cannot merge or push. The network and the rest of
  the filesystem are not fenced: an allowed `python3` or `git` command can
  read or write outside the trial directory.
  **The numbers. CLI 2.1.287, 2026-10-02, k=3.**

  | Task | Step | Passed | pass^3 | Cost a trial | Wall time a trial |
  |---|---|---|---|---|---|
  | `a_fire`, stubbed acceptance test | 8 | 2 of 3 | no | $0.55 to $0.98 | 86 to 134 s |
  | `a_pass`, the same wave without it | 8 | 3 of 3 | yes | $0.70 to $0.80 | 82 to 125 s |
  | `b_fire`, open question in memory | 4.5 | 3 of 3 | yes | $0.21 to $0.30 | 23 to 42 s |
  | `b_none`, no such question | 4.5 | 3 of 3 | yes | $0.30 to $0.41 | 36 to 61 s |
  | `c_specialist`, a specialist row fires | 8 to 10 | 2 of 3 | no | $0.75 to $2.50 | 109 to 404 s |
  | `c_generalist`, the fallback | 8 to 10 | 3 of 3 | yes | $3.23 to $4.33 | 492 to 681 s |

  16 of 18 trials passed and four of six tasks hold at pass^3. $22.81 for the
  18 at list price as the CLI estimates it, and $3.38 more for six pilot
  trials on an earlier fixture. These are the fork's first per-step cost
  figures: the open-questions gate costs about a quarter, one evaluation
  about 75 cents, and a review of a ten-line wave $2.50 with two reviewers
  and $3.60 with the fallback's four.
  **What the trials showed, read from both failing transcripts, three
  passing ones in full and every trial's Agent calls and records.** (1) The open-questions gate held six of six. In all three
  `b_fire` trials the session read the question from memory, wrote
  `step-4.5.pending`, dispatched nothing, and the SessionEnd hook then set
  the wave `blocked` with its reason: Phase 4's hook runs in `-p`. (2) The
  evaluator's record was hook-written in 13 of 13 dispatches, and no session
  tried to write one. (3) Dispatch by name held: 13 evaluator and 18 reviewer
  dispatches, every one by `subagent_type`, none with a `model` parameter,
  none general-purpose. Personas named in the prompts equalled the selector's
  `selected` in all five trials that reached step 10, and the fallback ran as
  two reviewers and a held-back third pass in all three of its trials. (4)
  `a_fire` trial 3 failed, and the gate was never tested in it: the session
  saw the stubbed test before dispatching, wrote the missing check and the
  real test itself ("step 7 is where I close coverage gaps"), re-ran verify,
  and the evaluator passed the repaired wave. The defect did not ship. The
  builder edited production code at re-entry with no coder dispatch, and
  nothing in the harness refuses that. (5) `c_specialist` trial 2 failed at
  step 8: the evaluator returned NEEDS_WORK on the clean wave. It rated one
  gap HIGH that the other two trials' evaluators rated LOW, on the same
  files. Over the nine evaluations of a clean wave, eight said PASS. The gap
  is real: the fixture's train rows are in date order, so its order test
  cannot fail for train. (6) Step 10's selector command, `git diff
  --name-only main...HEAD`, prints nothing while the wave's work is
  uncommitted, and step 11 is where it is committed. All five sessions that
  reached step 10 noticed and added the working-tree files themselves, so
  the selector's input was each session's improvisation. (7) Ten of the 13
  evaluations filed, as LOW, that the verify stamp names a commit that does
  not hold the wave's code, for the same reason. (8) In the one trial where a reviewer's
  HIGH was fixed at step 10 (`c_generalist` trial 2), the session went back
  through verify and a second evaluation unprompted, R3's rule. (9)
  Reviewers were denied 5 to 14 Bash calls in each of the five trials that
  reached step 10 (`shasum`, `cp -R`, loops, commands opening with an
  assignment), and two sessions re-dispatched a reviewer whose first attempt
  proved nothing because of it. No reviewer left a mutation in a worktree.
  (10) No trial re-dispatched an unchanged wave. `c_generalist` trial 2's
  second dispatch was at the same HEAD with its fix uncommitted, which is the
  case a refusal keyed on HEAD would get wrong. (11) The wave gate denied
  nothing in 18 trials. Where a control held, it was the session following
  the skill, the hook writing the record, or the SessionEnd hook. (12) Found
  by the workflow's first run on this branch, not by a trial: an untracked
  `__pycache__/` path fires `custom-performance` through its `**/*cache*`
  glob. The machine that built this sets `PYTHONDONTWRITEBYTECODE`, so it
  never showed locally; an installed instance ignores `__pycache__/`, so no
  trial met it. The harness now excludes the directory in a bare trial. The
  glob is left as it is and named here.
  **Prediction, to be checked by the next session that touches the fork.**
  Run again on this CLI and these models: pair B holds six of six; `a_pass`
  and `c_generalist` hold; `a_fire` and `c_specialist` each lose about one
  trial in three, for the two reasons above, until a rule stops the builder
  editing the wave at re-entry and until the evaluator's severity for one gap
  stops moving. Cost a trial stays inside the table's ranges. A change to a
  grader or a fixture that breaks a reference end state fails
  `test_evals.py` in CI. A change to step 4.5, 8 or 10 can now state its
  pass^3 before and after.
  **At risk.** (1) The prompts are the builder's. They say where the session
  ends and answer step 9 in advance; a pair whose prompt is changed to make
  it pass has stopped measuring the skill. (2) One ten-line project, one
  story, one wave: nothing here says how a step behaves on a real wave. (3)
  k=3 is small. Two of three and three of three are not far apart, and a
  pass^3 is three runs. (4) The fixture leaves the wave's work uncommitted,
  which is the skill's own order of steps and is what produced (6) and (7);
  an instance whose coders commit as they go would not see either. (5) The
  window fixture is not clean, as (5) above says; it is left as it ran. (6)
  A trial's reviewers work under headless acceptEdits and four allow rules,
  not under a person or auto mode, so (9) is the trial's own artifact. (7)
  No container. (8) Pair C grades the dispatch against what the selector
  told the session, not against what it should have been told. (9) The
  provenance check on an evaluation record is its header and the Agent call
  in the transcript. (10) `--setting-sources project,local` still carries
  the machine's login, and cost is the CLI's estimate at list price. (11) A
  trial borrows the fork's `.gitleaks.toml` so its first commit passes a
  machine's secret scanner; a fresh instance still has no allowlist of its
  own. (12) The 35 files under `evals/` ship to every instance with the
  skill. (13) These numbers are one CLI and two models on one day.
  **Named, not built.** A gate rule that refuses the session's own edits to
  the worktree while a wave is `in-progress` (the review's Batch 3 item,
  confirmed and unbuilt) is what (4) asks for. Step 10's changed-file
  command and the verify stamp both assume committed work. The evaluator's
  severity scale leaves one gap rateable as LOW or HIGH. The reviewer
  definition's shell needs are not in any allow list. None of these is
  changed here: R5 measures.
  **R4's at-risk items (1) and (2), graded by pair C.** Neither bit: no
  `model` parameter on 31 dispatches and no general-purpose subagent in 18
  trials. That is prose holding, not a rule.
  **R5a's prediction, graded the same day.** Holds where it could be
  checked. The workflow ran on the pull request and on the push to main,
  both green, and RQ made `checks` a required status check on main by a
  ruleset. A scratch pull request with the trees out of step failed naming
  the skill. The table has not changed and the replay is green on this
  machine at mean 4.33. Not graded: what an instance's waves get, because no
  instance carries 1.11.0.
- The reviewer-selection replay is committed, three table defects it surfaced
  are fixed, and a CI workflow runs the tests (R5a of
  docs/reviews/harness-engineering-review-v1.md, 2026-10-02). bmad-dev-wave
  1.10.0 -> 1.11.0. R5 ships as two pull requests; this is the first, and the
  three eval pairs are the second (R5b). The review found zero evals, zero
  CI, and a trigger table tuned on eighteen waves with nothing committed to
  re-run. Three parts, in the review's order.
  (1) The replay. `scripts/tests/replay_fixture.py build --repo <instance>`
  writes the fixture from a local checkout of the instance, using `git log`,
  `git diff` and `git show` and nothing else: per wave, the changed-file list
  of its merge and its test design at that merge.
  `scripts/tests/fixtures/replay-golden.json` records what
  `select_reviewers.py select` returns for each wave: the role ids, whether
  the fallback fired, the file counts, and the mean beside them.
  `test_replay.py` compares the two and reports every difference by wave and
  role; a fixture that no longer matches the golden's counts is reported as a
  stale fixture, not as a table change. `replay_fixture.py golden --write`
  replaces the golden, for a human who has read the difference.
  (2) The table. The golden was committed at the table as it stood, then each
  fix moved it in its own commit:

  | Change | Selections | Mean | Fallback on | Cells moved |
  |---|---|---|---|---|
  | The table on main | 74 | 4.11 | 3A, 3D, 6A | -- |
  | Planning artifacts are seen | 75 | 4.17 | 3A, 3D, 6A | 1C gains `bmm-pm` |
  | `tea-murat` reaches `tests/*/support/` | 77 | 4.28 | 3A, 6A | 3B and 3D gain `tea-murat`; 3D loses the fallback |
  | Cost row: "compute cap", "machine hours" | 78 | 4.33 | 3A, 6A | 1C gains `arch-cost-optimizer` |

  `IGNORED_PATHS` dropped all of `_bmad-output/`, where an instance keeps its
  PRD, epics and architecture spine, so `bmm-pm` (no spec phrases) could never
  fire in an instance and neither could the path half of `bmm-architect`.
  `_bmad-output/planning-artifacts/` is carved back out; the wave map there
  (`waves.md`, changed by 10 of the 18 waves) and the rest of `_bmad-output/`
  stay bookkeeping. `tea-murat` gains `**/tests/*/support/**`. 3D is one of
  the two waves the fallback was built from, and it no longer gets the
  fallback: `tea-murat` is now its only specialist and one specialist retires
  the fallback. That is the table's existing rule, not a judgment that 3D's
  mutation sweep was unnecessary, and nothing replaces the sweep there. The
  cost row fired on 0 of 18 waves and three are about cost (1C, 4B, 5C). It
  now fires on 1C. **4B and 5C stay missed.** Every candidate that reaches
  them was counted over all eighteen specs with the selector's own matcher
  and refused: "cost record" fires on 4B and also on 5A and 5B, where it is
  the provenance line every compute wave carries; "dollars" reaches 4B as a
  field name and any priced product says it; "ledger" is a billing word in
  another project; bare "cost" fires on 8 of 18. 5C's cost defect was a
  constant in the diff, and its spec names cost only in the amendment written
  after the review found it, which a step-10 selector would not have seen.
  The Phase 6.3 entry below carries a dated correction of its two figures
  (4.2 and "exactly two").
  (3) The workflow, `.github/workflows/ci.yml`, on `pull_request` and on push
  to main, with no secret and no model call: `diff -rq -x __pycache__`
  between `skills/<name>` and `.claude/skills/<name>` for every directory
  under `skills/` (46), failing by name; the unit tests of bmad-dev-wave and
  bmad-close-epic in both trees; `./install.sh --validate-only
  --skip-mcp-check` on Node 22 and Python 3.12 with PyYAML; and, on a pull
  request, a `skills/*/SKILL.md` whose `metadata.version` changed needs
  `CHANGELOG.md` in the same pull request. `.github/workflows/` is outside
  the plan's three seams; the R5 kickoff's build list is the grant. Both
  `.gitignore` files name `.replay-fixture/`.
  **Rulings by RQ, 2026-10-02.** (i) Nothing of the instance's text or paths
  is committed: this fork is public and the instance is private. The builder
  and the golden are committed, the fixture is rebuilt locally into a
  git-ignored directory, and the replay test skips with the reason where it
  is absent. (j) All the table defects are fixed, one at a time, golden
  first. (k) The eval pairs run under a small stdlib harness with no
  container (R5b). (l) Two pull requests. (m) One workflow, the four checks
  above; making it a required check is a branch protection setting and RQ's
  hand step.
  **What was measured, 2026-10-02.** E1's own directory had been pruned (its
  `selector/`, its file lists and its builder were gone), so the fixture was
  rebuilt from the instance and the proof target is Appendix F's per-wave
  record: at the table on main the selector reproduced it wave for wave (74
  selections, mean 4.11, `bmm-dev` on 17, cost on 0, fallback on 3A, 3D,
  6A). A deliberately broken row -- `tea-murat`'s `**/fixtures/**` deleted --
  failed the replay naming 2B, 2C, 3C, 3E and 4A losing `tea-murat` and 3C
  and 4A gaining the fallback. Deleting `arch-data-architect`'s
  `**/migrations/**` did not fail it: another pattern of the same row fires
  on every wave that one did. Measured over the whole table: of 504 pattern
  lines, deleting any one moves a golden cell for 18 and is invisible for
  486. 246 tests in bmad-dev-wave (231 before) and 12 in bmad-close-epic,
  both trees; one of them skips without the fixture. `--validate-only`
  exits 0. The workflow's first run, on this pull request, passed in 73
  seconds on ubuntu-latest: 246 tests with one skipped and 12, in each tree,
  about 33 seconds a tree; validation ok; the version check read 1.10.0 ->
  1.11.0 and found `CHANGELOG.md`. Python, Node and PyYAML took 4 seconds. A
  scratch pull request with one file of `.claude/skills/bmad-status-wave`
  out of step failed at the mirror step, "bmad-status-wave: skills/ and
  .claude/skills/ are out of step", and ran nothing after it. Before the
  entry was committed the version check failed this branch locally, for the
  bump with no `CHANGELOG.md`.
  **Prediction, to be checked by the next session that touches the fork.**
  On this machine, any change to the table or the selector that starts or
  stops a row on one of the eighteen waves fails `test_replay.py` naming the
  wave and the role, before it is committed. On every pull request and every
  push to main the workflow runs; a pull request that leaves `skills/` and
  `.claude/skills/` out of step fails naming the skill, and one that changes
  a skill's `metadata.version` without `CHANGELOG.md` fails. In an instance
  that carries dev-wave 1.11.0: a wave that changes the PRD or the epics
  under `_bmad-output/planning-artifacts/` gets `bmm-pm`, one that changes
  the spine there gets `bmm-architect`, one that changes `tests/<x>/support/`
  gets `tea-murat`, and one whose test design says "compute cap" or "machine
  hours" twice gets the cost reviewer. The mean on the eighteen is 4.33; the
  next change that moves it says which cells. Nothing changes in a live
  instance until 1.11.0 is copied in.
  **At risk.** (1) The replay is scored on its training set: the eighteen
  waves are the ones the table was tuned on, so it catches regressions, not
  generalization. (2) A golden reduced to role ids cannot show why a row
  fired, and it sees little: 486 of 504 single-pattern deletions leave it
  unchanged. (3) With the fixture out of the fork the replay is a local
  habit, not a gate. CI skips it, and a table change made on a machine
  without the instance passes CI unchecked. (4) `golden --write` accepts any
  difference in one command; reading the difference first is prose. (5) 3D
  loses the fallback, and its record shows the fallback's method is what
  reviewed it. (6) The mean rose from 4.11 to 4.33, and the plan reads a rise
  as triggers too loose; here each of the four added cells is named above.
  (7) Two cost phrases from one wave's spec can overfit a second time, and
  the row still misses two of the three cost waves. (8) Un-ignoring planning
  artifacts opens them to every row's globs, not only the two rows intended;
  an instance whose waves routinely amend `epics.md` gets `bmm-pm` on each.
  (9) The builder puts eighteen wave ids and pull request numbers of a
  private repository in a public file. (10) The workflow installs Node and
  PyYAML on every run for a suite that takes about two minutes. (11) A
  required check on a repository whose owner merges by hand can block the
  owner; it is not required until RQ sets it. (12) The version check reads
  `metadata.version` by pattern at two spaces of indent; a SKILL.md written
  another way is not seen. (13) The unit tests had only ever run on macOS
  before the workflow's first run.
  **Named, not built.** E1's selector findings 4 to 7: the table and its own
  docstring disagree about whether 4A should pull the ML reviewer; 6A, a
  pre-registered evaluation gate, selects only `bmm-dev`; `pyproject.toml`
  stands in for a dependency change on the appsec row and the governor row
  misses lint and boundary rules kept there; `custom-growth` cannot see a
  tier presentation. `docs/harness-conversion-plan.md` line 488 still says
  "exactly two"; it is outside R5's grant.
  **R4's prediction, graded.** Holds where it could be checked, with one
  miss and one part ungraded. (1) R4's live check again, CLI 2.1.287, in R4's
  instance. Sonnet parent, acceptEdits: the main thread's messages came from
  claude-sonnet-5-5, the coder's from claude-sonnet-5-5 and the reviewer's
  from claude-opus-5-5, neither Agent call carried a `model` parameter,
  `agent_type` on the hook events was the definition's name and
  `effort.level` high on every event, the main thread's included; $0.49. No
  `--model`, auto, `--effort low`: the session started on claude-opus-5-5 at
  effort low, the coder ran on claude-sonnet-5-5 and the reviewer on
  claude-opus-5-5, both at effort high on PreToolUse, on both
  SubagentHandback events and on SubagentStop; $0.61. The reviewer loaded
  `agent-appsec` and named its persona in both, with no prompt and no denial.
  (2) The instances: ffbapp and green-ledger are still at dev-wave 1.8.2 with
  the evaluator's definition only. The hand step for R3 and R4 is not
  applied, no wave has run under either, and no review record has been
  written, so "every review record written from here on" is ungraded and R1
  to R4 still have no grade from a real wave. (3) Validation: exit 0 on main
  and in a copy of R4's instance; exit 7 with the reviewer's `model:` edited
  to `opus`, naming the file and what it declares. (4) The listing: a miss.
  In the session that built this, five of the seven wave skills list as
  "description - when_to_use"; bmad-resume-wave and bmad-status-wave list by
  name only, as do about 50 other project skills. The docs: "if you have
  many skills, Claude Code drops some descriptions to fit the listing's
  character budget". `when_to_use` reaches the listing only while the budget
  allows. (5) This session's own
  Bash, Write and Edit calls replayed through the gate: 0 refused of 76 at
  the time of writing (R4: 0 of 77). Of R4's at-risk list: (4) held again,
  once per mode; (1) and (2), the `model` parameter and dispatch by name
  being prose, wait for R5b's reviewer-dispatch pair. New, for R5b:
  `--setting-sources project,local` did not keep the account's claude.ai
  connectors out of the trial -- the coder's report listed six that need
  authorization.
- The configuration that configured nothing is deleted, and a subagent's
  model and effort bind where Claude Code reads them: its definition's
  frontmatter (R4 of docs/reviews/harness-engineering-review-v1.md,
  2026-10-01). bmad-dev-wave 1.9.0 -> 1.10.0, bmad-resume-wave 1.3.0 ->
  1.4.0, bmad-create-wave 1.1.0 -> 1.1.1, bmad-merge-wave 1.2.0 -> 1.2.1,
  bmad-status-wave 1.2.0 -> 1.2.1, bmad-close-epic 1.4.0 -> 1.4.1, bmad-wrap
  1.9.0 -> 1.9.1. The review found 7 of the settings template's 13 keys were
  not Claude Code settings, 8 SKILL.md keys nothing read, no effort setting
  that took effect anywhere, and reviewers following the session's model in
  7 of ffbapp's 18 waves. Five parts, in the review's order. (1) The
  template loses `contextWindow`, `subagentModels`, `subagentReasoning`,
  `skillsPaths`, `agentNamesFile` and `mcpServers`, and `reasoningEffort`
  becomes `effortLevel`, the key it was meant to be. The `permissions` and
  `hooks` blocks are untouched. The resolver fills `model` and `effortLevel`
  from one row of the tier table and substitutes nothing else. (2) Skill
  frontmatter, all seven wave skills: `when-to-use` is `when_to_use`, the
  one field name with an underscore, so it reaches the skill listing
  (resume-wave's was a list and is now one string). The skill version now
  lives at `metadata.version`. The other keys nothing reads moved under
  `metadata:` too, not into the body: `output-locations`, `inputs`,
  `outputs`, `exit-codes`, `when-not-to-use`. resume-wave's `tools:`, a
  subagent field, is `allowed-tools: Read Glob Grep Bash Skill(bmad-dev-wave
  *)`; that pre-approves those tools for the turn that invokes the skill and
  restricts nothing, and drops `SlashCommand`, not a current tool. (3)
  install.sh no longer creates `~/.claude/projects/<basename>/memory`. The
  step is deleted, not fixed: the real directory is named from the project's
  absolute path and Claude Code creates it. (4) `.agents/skills`: see
  Removed, below. (5) The binding. Two definitions,
  `.claude/agents/keelswell-wave-coder.md` (claude-sonnet-5-5, effort high)
  and `.claude/agents/keelswell-wave-reviewer.md` (claude-opus-5-5, effort
  high), and the evaluator moves from the `opus` alias to claude-opus-5-5.
  Dev-wave dispatches coders at step 6 and reviewers at step 10 by
  `subagent_type`, persona and fallback reviewers alike, under a new
  section, The Routing; The Review Record copies its `model` and `effort`
  from the reviewer's definition. `core/config.yaml` is the tier table: two
  tiers, three roles (`orchestrator`, `coding`, `adversarial`), each role's
  `effort`, and the definitions each role binds under `agents:`. Its
  permissions, parallelism and context blocks are gone; the parallel cap (4)
  is written into step 6. A new phase-6 check, `routing_check`, reads the
  table and each named definition and exits 7 naming the one whose `name`,
  `model` or `effort` differs. It repairs nothing and generates nothing.
  `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` is documented in
  docs/upstream-refresh-runbook.md as the override that ignores every
  definition's model, with the re-pin procedure.
  **Rulings by RQ, 2026-10-01.** (f) Delete six keys, rename one;
  `effortLevel` is filled from the orchestrator row. (g) Two definitions,
  checked and not generated; neither carries a `tools:` line, so both
  inherit every tool, the reviewer included, because it proves a finding by
  mutation and execution; step 3's test-design subagent is left alone. (h)
  Full model ids, re-pinned per release with a line here; the `fast` tier
  and the `research` and `fallback` roles are deleted because nothing bound
  to them. (i) The fork's `.agents/skills` is deleted in its own commit.
  **"Do not add agents".** R4 touches that rule by its letter, not its
  rationale. The two files are role definitions for dispatches dev-wave
  already made, not domain personas: no roster entry, no `module.yaml` line,
  nothing under `agents/`, no row in the trigger table. A reviewer's persona
  is still the skill `select_reviewers.py` returned.
  **What was measured, CLI 2.1.287, 2026-10-01.** A fresh `--target-project`
  install from this branch: settings.json parses, its top-level keys are
  `$schema`, two `$comment_` keys, `model`, `effortLevel`, `permissions` and
  `hooks`, and against R3's it differs in the seven keys removed,
  `effortLevel` added, and `model` (claude-opus-4-8 to claude-opus-5-5, from
  ruling h); `hooks` and `permissions` are equal. Two headless sessions in
  that instance, each dispatching both definitions by name with no `model`
  parameter. Sonnet parent, acceptEdits: the coder's messages came from
  claude-sonnet-5-5 and the reviewer's from claude-opus-5-5; `agent_type` on
  their hook events was the definition's name and `effort.level` high; the
  main thread's effort was high, from `effortLevel` (Sonnet 5.5 defaults to
  medium). No `--model`, auto, `--effort low`: the session ran on
  claude-opus-5-5 from the settings' `model` at effort low, the coder on
  claude-sonnet-5-5 and the reviewer on claude-opus-5-5, both at effort high
  on PreToolUse, on both SubagentHandback events and on SubagentStop. So a
  definition's model holds under a parent of either family and its effort
  holds against the session's. The reviewer loaded `agent-appsec` with the
  Skill tool and named its persona in both modes, with no prompt and no
  denial. `--validate-only` exits 0 in the fork and in the instance; with
  the reviewer's `model:` edited to `opus` it exits 7 naming the file and
  what it declares, and the same with the coder's file missing.
  `when_to_use`: the session that built this reloaded its skill listing
  after the mirror step and each of the seven now reads "description -
  when_to_use"; 1,713 characters across the seven, the longest entry 964 of
  the 1,536 cap. The upstream installer (6.12.0) reads `name` and
  `description` from a SKILL.md and nothing else, and the fresh install's
  phase 4 exited 0. 231 tests in bmad-dev-wave (227 before) and 12 in
  bmad-close-epic, both trees.
  **Prediction, to be checked by R5's session.** In a fresh instance, and in
  any instance that carries the three definitions and dev-wave 1.10.0: every
  step-6 coder runs on claude-sonnet-5-5 and every step-10 reviewer and the
  evaluator on claude-opus-5-5, all at effort high, whatever the session's
  model and effort; every review record written from here on says `model:
  claude-opus-5-5` and `effort: high`; a definition edited away from the
  table fails validation by name. A fresh instance's sessions start on
  claude-opus-5-5 at effort high. The seven wave skills' listing entries
  carry their `when_to_use`. Nothing changes in a live instance until the
  hand step, and nothing there changes in settings.json at all.
  **At risk.** (1) The Agent tool's per-invocation `model` parameter
  outranks a definition. The Routing says not to pass one; nothing refuses
  it, and an `Agent(model:...)` deny rule would apply to every Agent call.
  (2) Dispatch by name is prose. A session can still send a general-purpose
  subagent, which follows the session's model; R5's reviewer-dispatch eval
  is the first grader. (3) Neither definition restricts tools. A reviewer
  can edit, and one that does not restore a mutation leaves it in the
  worktree; the gate and the permission rules apply to it as to the session.
  (4) The reviewer's persona depends on the Skill tool. It loaded unprompted
  in acceptEdits and in auto, once each, one skill; a Skill ask or deny
  rule, or default mode, was not measured. (5) In auto mode every
  subagent's hand-back runs R3's hook, 37 ms, which exits at once for any
  agent but the evaluator; a parallel wave now makes one per coder. (6)
  `effortLevel` in a project file sets every session's effort in a fresh
  instance, which costs more than the medium default; `--effort` and
  `CLAUDE_CODE_EFFORT_LEVEL` still outrank it. (7) A full model id goes
  stale without an error when its model retires, is not the id other
  providers use, and Sonnet 5.5 needs CLI 2.1.284 or later. (8) An instance
  that takes dev-wave 1.10.0 without the definitions has nothing to dispatch
  by name; validation exits 7 until they are copied. (9) resume-wave's
  `allowed-tools` now pre-approves Bash for the turn that invokes it, where
  `tools:` approved nothing; deny and ask rules still come first. (10)
  Reviewers now cost Opus at effort high in a session that ran them cheaper.
  (11) Step 3's test-design subagent, and any other dispatch, still follows
  the session.
  **R3's prediction, graded.** Holds. R3's live check again, five of five,
  Sonnet parent: both real runs were written by the hook (pass 6 from
  SubagentStop in acceptEdits, pass 7 from PostToolUse on SubagentHandback
  in auto), header naming hook, session and subagent, no `record` call in
  either transcript; a two-word reply with no verdict was blocked and the
  second report recorded; a PASS under a `[HIGH]` heading was denied before
  the hand-over and the second recorded; a forged event piped to `record`
  from Bash was denied by the gate. `effort.level` read high on all ten
  evaluator events, both modes. `dispatch` ran only after `verify` stamped
  HEAD in every run. Cost: one evaluator run each, one sent-back round in
  each synthetic run, none in the real ones; hook time not re-measured. Its
  at-risk list: (1) stands, the synthetic runs again recorded what the
  prompt asked for; (5) this session's 63 Bash, Write and Edit calls,
  replayed, 0 refused, against R3's 4 and 2 of 66; (9) the evaluator ran in
  the background in all four runs and the parent waited; (10) one denied
  hand-over in auto, no pause; (7) green-ledger still has no
  `tests/verify-fast.sh`; (2), (3), (4), (6) and (8) not exercised. One
  thing the prediction did not cover, found by the evaluator itself: with
  five NEEDS_WORK records on disk both real passes returned UPSTREAM_CAUSE
  (exit 4, as designed) and both named the pass count as the cause.
  `dispatch` re-dispatches a HEAD that has not changed since the newest
  record, and re-dispatches after an UPSTREAM_CAUSE with no fix on record,
  and each round advances the count. Not built here. The instance grade is
  not gradable: the R3 hand step is not applied to either instance (RQ,
  2026-10-01), so no wave has run under the hooks.
  **Instances.** ffbapp and green-ledger need the runbook's hand step, now
  one pass for R3 and R4: the seven wave skills, the two wrappers, the three
  definitions (`cp .claude/agents/*.md`), the R3 registrations, and a
  `tests/verify-fast.sh`. R4 itself asks nothing of an instance's
  settings.json. Until then `--validate-only --target-project` exits 7 and
  names the missing definitions beside what R3 needs.
  **Named, not built.** The hook rule for the `git -C` and `bash -c` forms
  the permission rules miss is still the unscheduled sixth do-now item
  (RQ, 2026-10-01). Left as found, outside R4's list: `Task` in dev-wave's
  `allowed-tools` (an alias of Agent, which needs no permission), "extra"
  in bmad-wrap's description (the level is xhigh), the `fork:` block of
  `core/config.yaml` (read by nothing), and docs/harness-conversion-plan.md
  and `.gitleaks.toml`, which still mention `.agents/skills`.
- The evaluator's evidence and its record are written by scripts and a hook,
  not by the builder (R3 of docs/reviews/harness-engineering-review-v1.md,
  2026-10-01). bmad-dev-wave 1.8.2 -> 1.9.0. The review found three prose
  links at the evaluation step: the evidence the evaluator is shown was
  written by the builder, `record` parsed whatever text the builder piped
  in, and nothing checked a verdict against the severities listed under it.
  Five parts, in the review's order. (a) The record is hook-written.
  `.claude/hooks/wave-evaluator-record.sh` runs `evaluate_wave.py record` on
  the `keelswell-wave-evaluator` subagent's own report and writes
  `docs/wave-<id>/evaluation-<n>.md` with a header naming the hook, the
  session and the subagent. The pass count, the third-pass rule and the exit
  codes are as before; the exit code now comes from a read-only `verdict`
  verb. (b) `evaluate_wave.py verify` runs `tests/verify-fast.sh` from the
  worktree root and stamps the first line of `verify-output.txt` with the
  command, the exit code, HEAD and the time. `dispatch` writes
  `wave-diff.patch` itself, from the branch's merge-base with main, read
  from git: everything changed since, committed or not, untracked files
  included. It exits 3 when the verify output is missing, unstamped or
  stamped at another HEAD, where it printed a notice. (c) A parser, not a
  model, refuses a report with no `VERDICT:` line, with two, with a verdict
  outside the list, or a PASS under which any `### [SEVERITY]` heading is
  not trivial. The ladder is read from the evaluator definition (its `-
  **NAME** --` bullets and the sentence naming the trivial one), never
  retyped, and `check` refuses a definition it can no longer read it from.
  (d) The definition sets `effort: high`, asserted by `check`, which also
  refuses `memory:` (it grants Write and Edit whatever the tool list says).
  (e) The three loop defects. Dev-wave's steps 7 to 9 are reordered, none
  added: 7 is test expansion and verify, 8 the evaluation, 9 the checkpoint
  preview. The pass count restarts after an UPSTREAM_CAUSE whose fix is on
  record, as a lifecycle history line written by `wave_status.py set
  --status in-progress --reason "upstream fix: <artifact>"` after that
  record; `dispatch` reports `rule_pass` beside `pass_number`. A fix made at
  step 10 routes back through steps 7 and 8, where the stale stamp is
  refused and a `review-party.md` dated on or after the latest evaluation
  joins the evidence.
  **Rulings by RQ, 2026-10-01.** (e) `dispatch` leaves
  `.bmad/wave-<id>/evaluation-pending` holding the session id (from
  `CLAUDE_CODE_SESSION_ID`), the pass number and the worktree path; the hook
  records to the one marker its session left and deletes it. No marker, or
  two, and it writes nothing. (f) The Bash route to `record` is retired.
  `record` now takes the hook event on stdin, and a sixth gate rule, record,
  denies any Bash or Monitor call of it, in the shapes the gate reads and
  the ones it cannot, as the review rule does for `set`. The hook writes the
  `evaluation-session` marker the in-place rule reads, which the gate used
  to note when it saw `record` go by. (g) The verify command is
  `tests/verify-fast.sh` and nothing else; no config key. (h) A third
  registration, asked for mid-session on a measurement: the kickoff allowed
  SubagentStop and PostToolUse on SubagentHandback, and in auto mode neither
  can send a bad report back (below), so PreToolUse on SubagentHandback was
  added. R1's PreToolUse entry is unchanged and first; its test now says so
  instead of pinning the whole list.
  **What was measured, CLI 2.1.287, 2026-10-01.** Where the report travels.
  Outside auto mode it is `last_assistant_message` on SubagentStop, and a
  block decision there starts a second round. In auto mode the subagent
  reports through SubagentHandback, SubagentStop then carries no
  `last_assistant_message` key at all, and neither a block on PostToolUse
  nor a block on SubagentStop does anything: the hand-over has happened. An
  exit 2 on PreToolUse for that tool does: the evaluator sent a second
  report. All three events carry the parent's session id, equal to
  `CLAUDE_CODE_SESSION_ID` in its Bash calls. The live check, in a fresh
  `--target-project` instance with a one-story wave on its own branch, six
  headless sessions with a Sonnet parent (Haiku cannot run auto mode).
  acceptEdits: verify, dispatch, the evaluator, verdict; the hook wrote
  `evaluation-1.md` from SubagentStop, header naming it, marker gone, no
  `record` call in the transcript, no denial. auto: the same, written by
  PostToolUse on SubagentHandback as `evaluation-2.md`, once. Both real
  verdicts were NEEDS_WORK on a defect in the fixture nobody planted: AC-2
  says either argument and the test covers one. A first reply of two words
  with no verdict was blocked and the second attempt recorded. A PASS
  carrying a `[HIGH]` heading was denied before the hand-over and the second
  report recorded. `echo <forged event> | evaluate_wave.py record` from Bash
  was denied by the gate. Report size: 3,714 to 18,072 characters on
  SubagentStop and 4,643 to 10,732 on the hand-back, every record identical
  to the event's text, so the 10,000-character cap documented for
  `additionalContext` applies to neither field. Effort: the evaluator's
  events said `medium` under the definition on main and `high` under this
  one, in both modes. The hook costs 37 ms p50 for another subagent's
  hand-back and 44 ms for the evaluator's (n=20). 227 tests across
  bmad-dev-wave's scripts (176 before) and 12 in bmad-close-epic, both
  trees; three replay hook events recorded from the live run, paths
  shortened.
  **Prediction, to be checked by R4's session.** In an instance that carries
  the three registrations: every evaluation record written from here on has
  the hook's header, and none is written by a session; `evaluate_wave.py
  record` from Bash or Monitor is refused; a report with no verdict, two, or
  a PASS above LOW never reaches disk; the evaluator runs at effort high
  whatever the session's is; `dispatch` refuses evidence that `verify` did
  not stamp at the worktree's HEAD. One evaluation costs one evaluator run
  plus at most two sent-back rounds, and about 40 ms of hook time per event.
  **At risk.** (1) The dispatch prompt is still the builder's. The synthetic
  runs prove it: told to, the evaluator returned NEEDS_WORK with a finding
  titled "wiring test". The hook settles who wrote the text, not what the
  evaluator was asked. (2) The marker is writable by a session (the
  2026-10-01 ruling keeps `.bmad` markers writable). A forged one still
  needs a real evaluator subagent in the same session and a wave in the map.
  (3) Where the gate is not registered, `record` can be fed a forged event
  from Bash; the header then lies. That is every tree R1's rules do not
  reach either. (4) The stamp reads HEAD, so an uncommitted edit after
  verify is not seen. (5) False refusals. A report that starts a line with
  another record's `VERDICT:` is sent back. The record rule refuses a
  command that names evaluate_wave and holds the bare word record where the
  gate cannot place it: of this session's 66 Bash, Write and Edit calls,
  replayed, 4 would have been refused by it, all here-documents editing
  these files, and 2 more by the review rule for the same reason. (6) It
  fails toward no record: a missing wrapper, script or python3, or a
  worktree cut before the registration, records nothing, `verdict` exits 3
  and the wave cannot enter review. (7) A project with no
  `tests/verify-fast.sh` cannot pass step 7; green-ledger has none. (8)
  Waves in flight: an unstamped `verify-output.txt` is refused by name and
  `verify` repairs it. A wave paused between the old steps 7 and 10
  re-enters by markers that meant another step; neither instance has one
  (ffbapp 20 waves, green-ledger 0, 2026-10-01). (9) The evaluator ran in
  the background in both real runs and the parent waited for it; a parent
  that does not wait reads `verdict` exit 3. (10) In auto mode a sent-back
  hand-over is a denied tool call. Auto mode pauses after 3 consecutive
  classifier blocks, and whether a hook's denial counts toward that is not
  documented; the cap here is two.
  **R2's prediction, graded.** Holds, with two corrections. R2's live check
  again on 2.1.287: five of five. In a session that really started in auto
  (Sonnet), `gh pr merge` was denied and `git push`, `git branch -D` and
  `git worktree remove` were denied as unanswered prompts, as in
  acceptEdits; the probe branch survived. A redirect, `tee` and `sed -i`
  onto `.bmad/probe/wave.md`, a path the hook does not match, were each
  denied by the Edit rule alone and the file kept its content. The prompt as
  a prompt, seen by RQ in an interactive session: "Permission rule Bash(git
  push *) requires confirmation" for `git push 2>&1`. Correction one: bypass
  is not rejected. `--dangerously-skip-permissions` and `--permission-mode
  bypassPermissions` both start the session in acceptEdits with no error, so
  "cannot be entered" holds and at-risk (3) should read "is ignored": the
  eval-runner adapter (R5) will not fail fast, it will run with every
  unanswered prompt a denial. Correction two: `--permission-mode auto` on
  Haiku starts in `default`, so R2's `live-check.sh`, which uses Haiku,
  cannot exercise auto. Not re-measured: `gh auth token` (a failed rule
  would have put a token in a transcript), the forms text rules miss, and
  the Edit rules beyond the project root. This session met no prompt or
  denial of its own, because the fork registers no hooks; of its child
  sessions' calls the only denials were the intended ones.
  **1.8.2's prediction, graded.** Holds. TestNewline and TestE2bReplay pass
  on merged main in both trees. Of this session's 66 replayed calls none was
  refused for a newline, two-line and here-document commands included.
  **Instances.** ffbapp and green-ledger carry R1 and R2 at 1.8.2,
  byte-identical to fork 3436373. `./install.sh --validate-only
  --target-project` now exits 7 on both and names what R3 needs: the
  wrapper, its registration, and the three events. The hand step in
  docs/upstream-refresh-runbook.md is extended: copy the skill, both
  wrappers and the evaluator definition, paste the template's three entries,
  and give green-ledger a `tests/verify-fast.sh`. Not built, by the
  2026-10-01 ruling: a hook rule on R1's parser for the `git -C` and `bash
  -c` forms the permission rules miss. It is a sixth do-now item for RQ to
  schedule.
- The merge halt, the verdict rule and the lifecycle record get a
  permission-layer backing (R2 of
  docs/reviews/harness-engineering-review-v1.md, 2026-10-01).
  bmad-dev-wave 1.8.0 -> 1.8.1, a test only. The review found nothing
  guarding a merge, a force push or a hard reset in any mode: the instance
  template set `acceptEdits` and no rule, ffbapp's personal allow list
  pre-approves `gh pr *`, and five `git reset --hard` in ffbapp's record
  followed no human instruction. `templates/settings.json.template` now
  carries rules Claude Code enforces itself, whatever the model does and
  whether or not a hook runs. Deny: `Bash(gh pr merge *)`,
  `Bash(git push --force *)`, `Bash(git push -f *)`,
  `Bash(git reset --hard *)`, `Bash(git clean -f*)`,
  `Edit(/**/docs/wave-*/evaluation-*.md)`, `Edit(/.bmad/**/wave.md)`. Ask:
  `Bash(git push *)`, `Bash(git branch -D *)`,
  `Bash(git worktree remove *)`, `Bash(gh auth token*)`. And
  `permissions.disableBypassPermissionsMode: "disable"`. Every
  `wave_gate.py` rule stays: an Edit rule stops the Write and Edit tools,
  `sed`, `tee` and a redirect, and not a script's own file I/O, which is
  how `evaluate_wave.py record` and `wave_status.py set` still write.
  Four rulings by RQ shape it. The whole template file is a fork-owned
  seam (2026-09-28). Bypass stays banned, now mechanically; the auto ban
  is dropped, with no `disableAutoMode`, and deny and ask rules are the
  hard layer in acceptEdits and auto alike (2026-09-28; see Changed). The
  lifecycle rule locks `wave.md` only, not `.bmad/**` as the review wrote
  it: an Edit deny also stops the Write tool and a redirect, and dev-wave
  writes `checkpoint.json`, `step-N.done` and `step-4.5.pending` there
  with whichever tool it picks (2026-10-01). Both Edit rules carry a
  leading slash, which the review's did not: a pattern without one is
  matched from the session's current directory, which a `cd` moves, and
  one with it from the project root (2026-10-01; the permissions page
  says so, and the 2.1.252 CLI resolves an unanchored pattern against the
  live cwd). `install.sh` phase 6 gains a check that reads and never
  repairs: an instance's settings.json must carry every deny and ask rule
  the template declares, and the bypass lock, or validation exits 7
  naming what is missing. Six new tests pin the block (172 across
  bmad-dev-wave's scripts and 12 in bmad-close-epic, both trees).
  **What was checked, and what was not.** A `--target-project` install
  resolves a settings.json that parses, carries the seven deny and four
  ask rules and the lock, and differs from R1's in `permissions` only;
  the template's hooks lines are untouched. The two Edit patterns were
  run through node-ignore 7.0.11, the gitignore matcher the 2.1.252 CLI
  calls: 16 of 16 paths as intended, `wave.md` and evaluation records
  denied (an upper-case `EVALUATION-3.md` included), the three markers
  not. `evaluate_wave.py record` writes in the scratch instance. The live
  check ran on 2026-10-01 under CLI 2.1.287: five headless `claude -p`
  calls in the scratch instance, each passing an allow rule for its own
  command so that only the block could stop it. `gh pr merge 1` was
  denied; `git push` was denied, a prompt nobody answers being a denial
  in `-p`; a Write to `.bmad/probe/wave.md`, a path the hook does not
  match, was denied by the rule alone, and one to `.bmad/wave-1/wave.md`
  left no file; a Write to `.bmad/wave-1A/step-3.done` went through;
  `record` wrote `evaluation-2.md`. Five of five as wanted. Still
  unobserved: the prompt as a prompt, which only an interactive session
  shows.
  **Prediction, to be checked by R3's session.** In an instance that
  carries the block, `gh pr merge` is refused in every mode; a plain
  `git push`, `git branch -D`, `git worktree remove` and `gh auth token`
  prompt in every mode, auto included; the Write and Edit tools,
  `sed -i`, `tee` and a redirect cannot change a lifecycle or evaluation
  record under the project root with every hook off; bypassPermissions
  cannot be entered. Two sets of numbers, both from an emulation of the
  documented matching rules and not from the runtime. On the review's E2a
  fixture the rules deny 5 and prompt on 4 of the 14 destructive strings
  that are git or gh shapes, miss the other 5 (a here-document script, a
  quoted flag, a printf substitution, an alias, base64 into sh), and
  leave the 13 that are not (`rm -rf`, DROP TABLE, `dd`) alone by design;
  of 13 safe look-alikes they deny 2 (`gh pr merge --help`,
  `git clean -fdn`) and prompt on 1, an ordinary push. On ffbapp's 10,451
  recorded Bash calls they deny 8 (5 `gh pr merge`, 3 of the 5 resets)
  and prompt on 231, 212 of them pushes, across 71 of 91 main sessions:
  a median of 3 prompts in such a session, at most 12. That is the cost,
  and it is the intended one.
  **At risk.** (1) Forms a text rule does not match: `git -C <path>`,
  `git -c key=value`, `bash -c`, a binary by absolute path, a quoted
  word, a force flag after the remote or `--force-with-lease` (both
  prompt instead), a script written and then run. In ffbapp's record
  `git -C` hides 2 of the 5 resets, 53 of some 300 pushes, 27 of 41
  worktree removals and 13 of 16 `branch -D`, and `git -c` hides 35 more
  pushes. bmad-merge-wave writes its steps 3 and 4 as
  `git -C MAIN_REPO ...`, so its worktree removal and branch deletion do
  not prompt because of these rules; they fall to the session's mode. A
  model that is refused can reach for the same forms. Reading them takes
  a hook rule on R1's parser, which R2 was told not to add. (2) In
  `claude -p` a prompt nobody answers is a denial, so the four ask rules
  stop an unattended wave at its push. (3) With bypass locked,
  `--dangerously-skip-permissions` is rejected inside an instance; the
  bmad-eval-runner adapter uses it (R5). (4) The Edit rules stop at the
  project root: a sibling worktree's evaluation record, and a
  worktree-rooted session writing the main checkout's `.bmad/`, are
  outside them, and `rm`, `mv` and `cp` are not among the file commands
  the docs say an Edit rule sees. The hook's verdict and lifecycle rules
  cover those, within the limit graded below. (5) No rule covers
  `rm -rf`, and acceptEdits approves `rm` inside the project. (6)
  `./install.sh --validate-only --target-project` exits 7 on ffbapp and
  green-ledger until the hand step is done (measured 2026-10-01).
  **R1's prediction, graded.** "Every path that let a guarded call
  through without a decision now returns one": true of the five paths R1
  named (the E2b replay on merged main dd1e531 denies all 11 in-review
  shapes and allows the other 4, in both trees) and false of one it did
  not test. `_prepass` marks a newline as an operator with the newline
  inside the mark, shlex splits the mark there, and the halves are read
  as words, so a newline never ends a command. A guarded action on a
  second line passes whenever the first line is a command whose operands
  are not writes: 8 of 10 two-line shapes tried exit 0 (`echo x`, then
  the in-review `set`, a `sed -i` on `wave.md`, an `rm` of it, a `cp`
  over an evaluation record). The same defect refuses ordinary work: a
  `mkdir`, `rm` or `touch` followed by a second line crashes the gate
  (`ValueError: embedded null character`), denied as FAILED CLOSED, and
  a direct literal `wave_status.py set` on a second line is refused as
  unreadable. Replayed from a scratch cwd, ffbapp's 10,451 recorded
  calls hit that crash 61 times. Marking the newline as `;` in a scratch
  copy denies 10 of 10, allows 7 of 7 ordinary two-line commands, clears
  the 61 and keeps the suite green; it is not applied here, being R1's
  file and not R2's subject. "74 ms p50 against 48": measured 48 ms
  against 39 (n=20, twice, 2026-10-01, the wrapper in exec form against
  the 9caab2e gate), so the direction holds and the added cost is 9 ms,
  not 26. At risk, checked by replaying this session's own 64 Bash,
  Write and Edit calls through the gate: 5 would have been refused, none
  of them a guarded action. Two were predicted (a `for` loop that puts
  the verb in a variable; a here-document whose text names
  `.bmad/wave-<id>/wave.md`), one is the verdict rule's twin of a
  predicted case (`node -e` naming an evaluation path), and two are the
  newline defect. Not hit: a broken gate needing a human, and `record`
  fed by a here-document. Not covered then or now: a script written
  earlier and run later, and a renamed `wave_status.py`.
  **Instances.** ffbapp and green-ledger hold a hooks-only settings.json
  that names the wrapper by bare relative path, and bmad-dev-wave 1.7.1
  (byte-identical to fork 9caab2e on 2026-10-01). Reaching them is a
  hand step, written out in docs/upstream-refresh-runbook.md: copy the
  skill and the wrapper, take the template's PreToolUse entry, add the
  permission block without `defaultMode`, then run `--validate-only
  --target-project`. Apply it once the newline defect is fixed, or the
  instances inherit it.
- The wave gate fails closed and parses Bash instead of searching it (R1 of
  docs/reviews/harness-engineering-review-v1.md, 2026-09-29). bmad-dev-wave
  1.7.1 -> 1.8.0. The review found five ways the Phase 4 hook let a guarded
  call through with no decision: any exit but 2 (a missing script, an
  exception, a bare relative path gone bad after a `cd`), a timeout, a tool
  it did not match (Monitor; NotebookEdit, read by the wrong field), a
  filename in another case, and a Bash shape its regexes did not see -- 8 of
  the 11 in-review shapes in the review's E2b fixture passed, and one `echo`
  was denied. Now `.claude/hooks/wave-gate.sh` turns a missing script, a
  missing python3 and any exit but 0 or 2 into exit 2 with the fix on
  stderr, and `wave_gate.py` exits 2 on any exception, on an event it cannot
  read, and past a 20-second deadline. The template registers the hook as
  `${CLAUDE_PROJECT_DIR}/.claude/hooks/wave-gate.sh` in exec form with a
  30-second timeout, and matches Monitor. NotebookEdit is read by
  `notebook_path`; guarded paths match without regard to case; the project
  root is the checkout holding `.bmad/`, found from the session's cwd through
  git's common directory, and a wave's evaluation records are read from its
  worktree first, so the rules see the tree the skill writes from either
  side. Bash and Monitor commands are parsed: here-documents split off,
  comments dropped, words unquoted with shlex, assignments and wrappers
  stripped, git's `-C` read, `cd` followed, and substitutions, `bash -c` and
  `eval` parsed as commands of their own. What the parse cannot read it
  refuses: a `wave_status.py set` reached through
  `python3 -c`, a here-document, a variable holding the command or a pipe
  into a shell, and a `$` or backtick in its verb, `--status` or `--wave`.
  One new rule, *lifecycle*: only `wave_status.py` writes, moves or deletes
  `.bmad/wave-<id>/wave.md` (E2b's b15 was a `sed -i` on it). Both additions
  sit inside R1 by RQ's ruling of 2026-09-28, which also admitted
  `templates/settings.json.template` as a fork-owned seam.
  `wave_status.py` and `evaluate_wave.py` set `allow_abbrev=False`, so
  `--stat` and `--wav` no longer bind. Replaying E2b's 15 commands: all 11
  in-review shapes denied; the echo, show, route and blocked calls allowed.
  24 new tests (50 for the gate, 166 across bmad-dev-wave's scripts),
  including the `.sh` wrapper itself run from a sibling worktree and from a
  `.claude/worktrees/` checkout; the 154 that existed still pass, in both
  trees. **Prediction, to be checked by R2's session.** Every path that let
  a guarded call through without a decision now returns one. A matched call
  costs 74 ms p50 against 48 before (n=20, one `git rev-parse` more). At
  risk: a broken gate blocks every Write, Edit and Bash call until a human
  repairs it outside the session, the intended direction; the refusal of
  unreadable shapes also refuses a legitimate `wave_status.py set` written
  through eval or `python3 -c` (the fix is the direct call), and an
  `evaluate_wave.py record` fed by a here-document whose text names
  `wave_status` and `set` (the documented `< file` form is untouched, and R3
  retires the Bash route to `record`); a command naming
  `.bmad/wave-<id>/wave.md` in anything but a plain read (`sed -n`, a `cp`
  out) is refused. Not covered: a script file written earlier and run later,
  and a renamed copy of `wave_status.py`, are not opened; R2's permission
  rules and the review record are the backstops. Instances: ffbapp and
  green-ledger register the hook by bare relative path in their own
  `.claude/settings.json`, so reaching them is a hand step (copy the
  wrapper and the three scripts, change the registration to the template's),
  not part of this change.
- Two tests were looking in the wrong place (2026-09-14): both located a
  fork-only file at a fixed `parents[N]`, which is right for exactly one of
  the three trees these tests ship to -- the fork's `skills/`, the fork's
  `.claude/skills/` mirror, and every instance's `.claude/skills/`. Phase 3's
  `test_shipped_definition_is_safe` built `.claude/.claude/agents/` in the
  other two and had been failing in the fork's own mirror, not just in
  instances, since it was written; the invariant it asserts was being held in
  the meantime by install.sh's own `evaluate_wave.py check`, which is why
  nothing caught it. Phase 6.3's roster-coverage test had the same shape and
  was skipping in the mirror where it could have asserted. Both now walk up
  until they find the file, assert wherever it exists, and skip only where it
  genuinely does not. All 142 pass in both fork trees; an instance runs 141
  and skips the roster test, which is the one file an instance really does not
  carry.
- green-ledger refreshed to role codes and given 6.3 (Phase 6.2 of
  docs/harness-conversion-plan.md, 2026-09-14): the second live instance still
  keyed nine custom agents under pre-0.5.0 persona codes, and it carries BOTH
  tool trees, so every rename and file copy is done twice -- four surfaces
  there rather than three. Verified in both trees: 38 `[agents.*]` tables with
  zero stale codes, every registered agent has a directory, all 35 firing
  trigger rows resolve to both a directory and a config entry, the suite
  passes, and `install.sh --validate-only --target-project` is green. Merged
  ff-only (no remote). Both live instances now carry 6.2 and 6.3.
  ffbapp needed no rename: it had been done on 2026-09-12 in
  attacktheseam/ffbapp#98, which a later session missed by working from a
  branch seven commits behind `main` and redid to a byte-identical result. The
  lesson is recorded in the plan: check a branch for being *behind* main, not
  only ahead, and read the plan's own Done markers first.
- Three Keelswell help rows given unique menu codes in the instances:
  `bmad-agent-architect` (was colliding with `bmad-agent-analyst` on `A`),
  `bmad-agent-arch-integration-architect` (with `arch-infrastructure-analyst`
  on `AIA`) and `agent-growth` (with TEA's ATDD on `AT`) move to `ARC`, `AIT`
  and `ATU`. These rows are instance-local and appear in no fork catalog.
  `SP`, `ST` and `TR` are cross-module upstream collisions present in the fork
  too and regenerated by the installer; left alone.
- A test portability fix rides along: the roster-coverage test reads
  `config/agent-names.yaml`, which is fork-only, and now skips in an instance
  rather than failing there.
- `bmm-dev` becomes a second opinion on the diff (2026-09-14, founder
  instruction): bmad-dev-wave 1.7.0 -> 1.7.1. An earlier draft left him inert
  on the grounds that a builder cannot review its own build; that was a
  misreading and is corrected here. Phase 3's ruling is about the *same*
  context grading itself and about an evaluator that can write, and a step-10
  dispatch is a fresh subagent with neither property. He fires on any
  implementation source outside a test tree -- 17 of ffbapp's 18 waves -- and
  is marked `generalist` for exactly that reason: a selection holding only
  generalist rows is treated as an empty one, so such a wave gets him *and*
  the fallback. Without that rule his row alone retires the fallback on 3A and
  3D, the two waves it was built for, and "somebody read it" is not the same
  answer as "somebody attacked it". Rows gain an optional `not_paths`, applied
  before `paths` so a row can say "production source, but not its tests";
  only his row needs it. Mean dispatches per wave 3.2 -> 4.2 with the fallback
  still firing on exactly two. 41 tests for this script, 142 across the wave
  scripts.
  **Corrected 2026-10-02 (R5).** Two figures in the sentence above do not
  reproduce. The E1 replay of 2026-09-27 and the replay now committed both
  measure a mean of 4.11, not 4.2 (74 selections over 18 waves), and the
  fallback on three waves, not two: 3A, 3D and 6A, whose only selection is
  `bmm-dev`. The 3.2 and the 17 of 18 reproduce. The fixture behind the
  original figures was not kept, which is what R5's replay is for.
- The trigger table becomes the whole roster, and gains a fallback (Phase 6.3
  second pass, 2026-09-14): bmad-dev-wave 1.6.0 -> 1.7.0. A sweep of all 38
  seats in `config/agent-names.yaml` against the four ffbapp waves that
  selected nobody found three with a real trigger and no row: `tea-murat`
  (fixtures, conftest, verify scripts, CI lanes), `arch-data-architect`
  (migrations, models, schema) and `arch-integration-architect` (routes,
  OpenAPI, protobuf). The data architect had been absent from ten of eighteen
  waves that changed database schema; under the old fixed three they got a
  cost reviewer instead. The remaining seventeen were given triggers rather
  than left inert, on founder instruction, and all but `bmm-dev` fire on an
  artifact rather than on code; several will never fire in a pure-code repo,
  which is correct behaviour and not a dead row. A test asserts the table and
  the roster are the same set, so a seat can no longer go missing quietly.
  **The fallback.** When no row fires, the table returns a method rather than
  a seat: the wave 3A pattern, two concurrent reviewers with disjoint mutation
  domains and a held-back third pass that writes its own exploits from the
  finding text. It is ffbapp's own, not invented here: waves 3A and 3D both
  ran real reviews under no persona's name ("mutation-based correctness
  review", "specimen expressiveness review", "real-sheet execution review"),
  3D's record says it ran "under the wave 3A pattern", and across all ten
  ffbapp review records not one reviewer heading names an agent. That review
  found the two HIGH findings on 3A -- non-finite Decimals passing every type
  check, and `decimal.InvalidOperation` escaping the degrade posture because it
  is an `ArithmeticError` -- which no seat in the table would have looked for.
  Waves 3C and 4A had no review at all and both are marked load-bearing; that
  is the hole this closes. The fallback is returned beside `selected`, never
  merged into it, so a record can always tell an empty selection from a fired
  trigger.
  **A fifth precision rule, and the measurement that forced it.** Structural
  BMAD vocabulary is never a trigger: a test design quotes its story's
  acceptance criteria and cites the PRD's functional requirements by
  construction, so "acceptance criterion" and "functional requirement" appear
  in every spec and separate nothing. Seated, they fired `bmm-qa` and `bmm-pm`
  on nine of eighteen waves apiece. The same trap catches a word the project
  has redefined -- ffbapp "prices" a touchdown and has a "presentation dial",
  neither about money nor slides. Adding all seventeen rows took mean
  dispatches per wave from 1.9 to 4.4; dropping the structural vocabulary took
  it to 3.2, with the fallback firing on exactly the two waves that need it.
  Also recorded: `arch-cost-optimizer`, one of the old fixed three, now fires
  on none of ffbapp's eighteen waves.
  35 stdlib tests. Still asserted under `--validate-only` in both roots.
- Reviewer selection is a script, not a paragraph (Phase 6.3 of
  docs/harness-conversion-plan.md): bmad-dev-wave 1.5.0 -> 1.6.0, plus
  `scripts/select_reviewers.py` and `scripts/reviewer-triggers.yaml`.
  Step 10 stopped hardcoding "security, cost, and platform" and now asks the
  script which reviewers the wave's own changed files and spec require. The
  same logic as prose in SKILL.md would sit in the layer the transfer evidence
  measures as the one that regresses across model families; a script and a
  table are dispatch, which is the layer that carries. It lives under the
  skill's own scripts/, the convention bmad-party-mode already uses, so it
  travels with the skill and survives an upstream refresh; not _bmad/scripts/,
  which the installer owns and wipes.
  **The rule is necessity, not a budget.** Eight domains genuinely in the diff
  return eight reviewers; one returns one. No cap, no maximum, no "top N",
  because a cap means choosing which real gaps to skip looking for. The fixed
  three lost their exemption in the same change: a wave touching no
  infrastructure now returns no platform reviewer.
  **Eighteen rows, and where each trigger came from.** Six quote
  docs/agent-inventory.md's own Trigger line verbatim -- which is all sixteen
  entries had; Group 2's seven end with a "Keep after an upgrade if" line and
  Group 3's with "How to find out", neither of which is a condition in a diff.
  Nine of those ten were written for this table and are marked
  `derived-2026-09-14` so the next inventory pass can tell them apart, as were
  arch-platform-engineer and arch-cost-optimizer, which are not fork-only
  agents and never had inventory entries. Three rows are inert and say why:
  custom-bizops (the inventory's own trigger says he is invoked directly, not
  by a wave), custom-web-designer (a builder dispatched at step 6, not a
  step-10 reviewer; her step-10 half is custom-design-critic), and
  core-bmad-master (the inventory calls it the only one of the sixteen for
  which no trigger is nameable).
  **Four precision rules, each added because a real ffbapp wave proved it
  necessary**, measured against all eighteen: a leading word boundary, because
  wave 4A's spec contains "train" three times and all three are inside
  "constraint"; front matter dropped, because a test design's
  `inputDocuments:` names what the wave read rather than what it changed;
  negated sentences discarded, because waves 3D, 4B, 5C and 5D each say "No
  rendered surface exists in this wave" and a substring match read that as
  proof one exists; and a two-occurrence floor, because "backtest" appears 39
  times in wave 4B and exactly once in 3D, where it is a quotation of the
  architecture spine's component list. Bookkeeping paths (`_bmad-output/`,
  `docs/wave-*/`, TODO.md, HANDOFF.md) are excluded from the file list; a
  session-wrap triage note was dispatching the security reviewer on five of
  eighteen waves on the strength of the word "session" in a directory name.
  Across the eighteen this took mean dispatches per wave from 3.6 to 1.9.
  **Asserted under `--validate-only`** in both `skills/` and
  `.claude/skills/`: the selector exists and is executable, bmad-dev-wave's
  SKILL.md calls it, and `select_reviewers.py check` validates the table --
  the same self-check shape Phase 3 gave the evaluator, so install.sh never
  learns the table's schema. 26 stdlib tests.
  **Party mode is untouched**: an initiated party is still the whole
  collective, preserved by not setting `default_party`.
  Two things this does not do. It does not decide what a load-bearing wave
  with zero selected reviewers should get instead -- four of ffbapp's eighteen
  return none, and whether those need a domain-less adversarial pass is an
  open founder ruling. And it is inert on ffbapp until Phase 6.2 runs: that
  instance still keys nine custom agents under pre-0.5.0 persona codes.
- Agent inventory (Phase 5 of docs/harness-conversion-plan.md):
  `docs/agent-inventory.md` asks one question of each of the sixteen
  fork-only agents, what specific failure it prevents, and sorts the answers
  into earns-its-place (6), consumable (7), and no-answer (3). Assessed
  against the Claude 5 family and dated, because the grouping is expected to
  go stale on each model release: prose does not survive being moved to
  another model family, so a persona that earned its place has to earn it
  again. No agent is deleted, renamed, or edited, including the three that
  could not answer; each of those gets a way to find out instead. The pass
  also found that no wave skill references any of the sixteen, which is why
  Phase 6 was added to the plan.
- Review records carry the model that produced them (Phase 6.1 of
  docs/harness-conversion-plan.md): bmad-dev-wave 1.4.0 -> 1.5.0.
  `docs/wave-<id>/review-party.md` gains a required front-matter block with
  `title`, `wave`, `created`, `model` and `effort`. `model` is the
  reviewers' model, not the orchestrator's: reviewers are dispatched as
  subagents and can run at a different model than the session that
  dispatched them, and theirs is the one that produced the findings. The
  record had no specified header at all; two of ffbapp's ten wrote one
  anyway, and this codifies the shape they converged on. Three of the ten
  said reviewers ran at "the session model" and none named a model, so no
  finding in any of them can be attributed to a model generation, which is
  what `docs/agent-inventory.md` could not recompute against. Scoped to the
  wave record deliberately: `bmad-party-mode` is upstream, so the
  planning-phase reviews it writes stay unstamped rather than opening a
  conflict surface. Asserted under `--validate-only` in both `skills/` and
  `.claude/skills/`; the spec itself takes effect at the next wave.
- Conformance check and hooks (Phase 4 of docs/harness-conversion-plan.md):
  install.sh phase 6 asserts the enforcement layer Phases 1-3 built, and two
  hooks make the rules those phases stated fail as tool calls.
  bmad-dev-wave 1.3.0 -> 1.4.0, bmad-close-epic 1.3.0 -> 1.4.0,
  bmad-resume-wave 1.2.0 -> 1.3.0.
  **The check.** After every install and under `--validate-only`, phase 6
  asserts, in both `skills/` (the source) and `.claude/skills/` (the snapshot
  an upstream refresh rewrites): the closure gate script exists and is
  executable and `bmad-close-epic/SKILL.md` calls it; `wave_status.py`
  exists and is executable and all five wave skills reference it;
  `wave_gate.py` exists and is executable; and the evaluator's tool list
  passes `evaluate_wave.py check`, which is Phase 3's own refusal reused
  rather than a second parser. Then the two hook wrappers exist, are
  executable, and are registered (in a target's `.claude/settings.json`; in
  the fork, which has none, in the template). A failure names the invariant
  and exits 7 (Table I.13: a runtime file is missing or a skill failed to
  load); nothing is repaired. `--validate-allowlist` gains the scripts and
  wrappers as must-exist files. Demonstrated by breaking four invariants
  under `--validate-only` (evaluator declares Write; close-epic loses the
  gate call; `wave_status.py` deleted from the snapshot; gate script loses
  its exec bit), each failing with exit 7 and passing after repair.
  **The hooks.** `skills/bmad-dev-wave/scripts/wave_gate.py` is the one
  PreToolUse hook the plan asked for, wrapped by `.claude/hooks/wave-gate.sh`
  on Write, Edit, MultiEdit, NotebookEdit and Bash. Four rules, each read off
  disk: *closure* (nothing is written under
  `_bmad-output/epic-closure/epic-<N>/` while `check_review_records.py --epic
  N` exits non-zero); *verdict* (`docs/wave-<id>/evaluation-<n>.md` is written
  by `evaluate_wave.py record` and nothing else); *review* (`wave_status.py
  set --status in-review` is denied unless the wave's latest evaluation is
  PASS); *in-place* (the session that recorded NEEDS_WORK cannot write into
  that wave's worktree afterwards; the hook notes the session id when it sees
  `record`). The SessionEnd half, `.claude/hooks/wave-session-end.sh`, blocks
  any wave whose `.bmad/wave-<id>/step-4.5.pending` marker is present when a
  session ends other than by `resume`; step 4.5 now writes that marker while
  it waits and removes it when the answer is recorded. Bash is matched on the
  command's text, a substring test and not a parse: a redirect through a
  variable, a prior `cd`, or a here-doc is not seen, and that is the named
  gap. 28 stdlib unittest cases in `scripts/tests/test_wave_gate.py`.
  **Prediction, to be checked at the next refresh.** Would catch: the
  installer ceasing to copy a custom skill's subdirectories (scripts/ gone
  from the snapshot); the installer rewriting files through a content writer
  that drops the exec bit; BMAD adopting `.claude/agents/` as an IDE-owned
  target and wiping or regenerating the evaluator (the same class as the
  2026-07-19 `.agents/` incident); upstream shipping a same-id
  `bmad-close-epic` or `bmad-dev-wave` whose precedence over the fork's copy
  flips, so the snapshot's SKILL.md no longer names the gate script; a
  template or copy path change that leaves the hook wrappers unregistered or
  non-executable. Would miss: prose drift inside a wave skill that keeps the
  reference string but stops obeying the exit code; the installer moving
  `_bmad-output/planning-artifacts/waves.md` or the `.bmad/wave-<id>/`
  convention, which leaves every script present, wired and exiting 2 on
  every run; Claude Code changing what a subagent's `tools:` list or a
  PreToolUse exit 2 means, which the check reads but cannot verify the
  harness honours; and any Bash route to a guarded file that does not name
  it. Also found: the fork's own `.claude/skills/` snapshot was two phases
  behind `skills/` (Phases 2 and 3 mirrored source only), so the fork's own
  sessions were loading pre-Phase-2 wave skills. Mirrored by hand, the act
  Phase 1 performed; the check would have caught it. The phase-5 copy loop
  now prunes `__pycache__` (carried in from Phase 1).
- A wave evaluator that cannot edit: `.claude/agents/keelswell-wave-evaluator.md`
  and `skills/bmad-dev-wave/scripts/evaluate_wave.py` (Phase 3 of
  docs/harness-conversion-plan.md). bmad-dev-wave 1.2.0 -> 1.3.0,
  bmad-resume-wave 1.1.0 -> 1.2.0.
  Step 7's review used to happen in the context that did the work, through the
  bmad-agent-qa persona. It now goes to a Claude Code subagent whose declared
  tools are `Read`, `Glob`, `Grep` -- no Write, no Edit, no Bash, no Task --
  dispatched with a context that never saw the build. Both halves are load
  bearing: fresh context because an agent reviewing its own output praises it
  (`[[generator-evaluator-split]]`), and no writing tools because an agent that
  can fix a finding decides which findings are worth having. The shape is
  `[[anthropic-cwc-long-running-agents]]`'s evaluator subagent.
  **The guarantee is checked, not asserted.** `evaluate_wave.py check` reads the
  definition's own tool list and exits 3 on any tool that can write, run or
  delegate; `dispatch` runs that check first and refuses to dispatch a
  definition that fails it. An absent `tools:` key is refused rather than
  treated as empty (a subagent with no list inherits the parent's tools), `*`
  is refused, and an unrecognized tool is refused rather than allowed -- a tool
  the check has never heard of is not evidence that it cannot edit. RQ ruled no
  Bash (2026-09-11): `bash -c 'cat > f'` is an edit, and the wave's step 9
  already ran the suite, so the evaluator reads that output as execution
  evidence instead of producing its own.
  The verdict is the evaluator's own `VERDICT:` line, parsed by `record` into
  an exit code (0 PASS, 1 NEEDS_WORK, 4 UPSTREAM_CAUSE, 3 unparseable), so
  bmad-dev-wave routes on what the evaluator said rather than on its own
  summary of what the evaluator said. Output with no readable verdict is not
  summarized on its behalf.
  **NEEDS_WORK is not fixed in place.** It halts the wave at step 7 with the
  status left at `in-progress` -- not blocked, because an ordinary outcome made
  sticky would teach the founder to clear records by reflex and cheapen
  `blocked` everywhere else. The findings become the *next* session's opening
  prompt, generated by `opening-prompt` from the record on disk rather than
  recalled by a session that may no longer exist; bmad-resume-wave runs it and
  opens with what it prints, verbatim.
  BMAD's stopping rule comes with it. `dispatch` sets `third_pass_rule` from
  the count of `evaluation-*.md` records on disk, not from anyone's memory of
  how many rounds this has been. On pass three the evaluator returns
  `UPSTREAM_CAUSE` and names the weak spec, contradiction or ambiguous rule
  behind the findings instead of producing a fourth round of them.
  **Fork-owned and collision-free.** The definition lives under
  `.claude/agents/`, which no BMAD module declares and the installer never
  reads. It is not a BMAD persona, gets no `module.yaml` row, no `[agents.*]`
  table and no `config/agent-names.yaml` entry, so it cannot reproduce the
  duplicate-declaration corruption module.yaml's header documents. It is also
  the only place a `tools:` list is enforced by the harness rather than being
  prose: upstream's subagent convention (`skills/bmad-prfaq/agents/*.md`) is
  plain prompt files whose subagents inherit the parent's tools.
  `bmad-agent-qa` (Aviendha) is untouched and keeps her seat, her skill and her
  persona file; she is no longer the one who grades the wave.
  No stage and no agent was added beyond the evaluator: step 7 already existed
  and its review changed hands, step 10's party mode is unchanged, and
  `docs/wave-<id>/review-party.md` is still required at step 11 for every wave.
  33 tests in `skills/bmad-dev-wave/scripts/tests/test_evaluate_wave.py`, one
  of which runs `check` against the real shipped definition rather than a
  fixture.
- `.claude/agents/` added to the allowlist in `.gitignore` and
  `templates/.gitignore.template`. `.claude/*` is ignored with a per-directory
  allowlist that had no entry for it, so the evaluator definition -- and any
  future subagent definition, in the fork and in every installed project --
  would have been silently untracked.
- `install.sh` copies `.claude/agents/*.md` into a target project alongside the
  hooks, and `--validate-allowlist` now asserts the evaluator definition is
  present. The full conformance assertion (that its tool list is still safe
  after an install) is Phase 4's job, not this one's.
- Wave lifecycle status, and Keelswell's first *sticky* control:
  `skills/bmad-dev-wave/scripts/wave_status.py` (Phase 2 of
  docs/harness-conversion-plan.md). bmad-create-wave 1.0.0 -> 1.1.0,
  bmad-dev-wave 1.1.0 -> 1.2.0, bmad-merge-wave 1.1.0 -> 1.2.0,
  bmad-resume-wave 1.0.0 -> 1.1.0, bmad-status-wave 1.1.0 -> 1.2.0.
  A wave now carries its stage in `.bmad/wave-<id>/wave.md` and the wave
  skills route on it instead of each inferring state from the conversation and
  the filesystem. The vocabulary is BMAD's own bmad-build-auto
  (`spec-template.md:5` and its step-01 routing table) -- draft,
  ready-for-dev, in-progress, in-review, done, blocked -- defined once in that
  script and read from there by all five skills. No stage was added: every
  status re-enters at a step bmad-dev-wave already had, and `done` re-enters
  at step 10 as a fresh follow-up review pass rather than a resumption.
  Verbs are `route` (the gate, exit code is the verdict), `set` (advance it)
  and `show` (read-only, for the dashboard; it never backfills, so a
  project-wide scan cannot quietly migrate eighteen waves).
  **Blocked is sticky, and that is the Phase 2 deliverable.** A blocked wave
  halts every later dispatch after its cause is fixed, `set` refuses to write
  over a blocked record, and no flag exists to force either -- so no skill can
  clear a block it created. Only a human editing `status:` or deleting the
  record clears it. The asymmetry is the control: a retry loop is not one,
  because the run that blocked the wave is the run that would argue it is safe
  to resume. Copied from bmad-build-auto's note on permanence.
  Two ways a missing status is read, and the split is the mechanism rather
  than bookkeeping. No record at all is a wave that predates the field:
  `route` backfills it once from checkpoint, git and worktree evidence, prints
  an `UNMIGRATED` notice naming the inference, and proceeds -- Phase 1's
  prospective-rule shape, where a pre-field artifact gets a named reported
  exemption and never a silent default. A record that exists with an
  unreadable status is refused (exit 3). Without that second half, deleting
  the `status:` line would be an undocumented override of blocked.
  Forty stdlib unittest cases ship in `scripts/tests/`, and every claim they
  rest on was mutation-checked: six deliberate defects re-applied, six
  reddened. One did not, and it was a finding rather than a gap -- the
  `done`-re-enters-at-10 branch was unreachable given that stage's single
  step, so the branch is gone and a test pins the width instead.
- Keelswell's first executable enforcer:
  `skills/bmad-close-epic/scripts/check_review_records.py` (Phase 1 of
  docs/harness-conversion-plan.md). bmad-close-epic 1.2.0 -> 1.3.0. The
  preflight condition that every wave of an epic carries an adversarial
  review record was prose asking the agent to refuse its own work; it is now
  an exit code the skill obeys. The rule is unchanged. Exit 0 proceeds; 1 is
  a wave that landed on or after the 2026-09-10 rule date with no record; 2
  is structural (no wave map, or no waves in the epic); 3 is a wave with no
  record that cannot be dated. Fail-closed throughout: an undatable wave is
  not assumed pre-rule. The refusal text names the wave, both accepted record
  locations, and the remedy, per the vault's "the enforcer coaches" note.
  A wave is dated by the merge that brought its docs to the closing branch,
  not by the commit that wrote them on the wave's own branch. Measured across
  ffbapp's eighteen waves that lag runs from six minutes to forty-six hours,
  and wave 5D's commit (2026-09-09T03:09Z) and merge (2026-09-10T14:42Z) fall
  on opposite sides of the rule date: dating by the commit would have passed a
  post-rule wave as pre-rule, the one direction this gate must not fail in.
  Caught by checking the shipped prediction against real history rather than
  assuming the lag was negligible. Regression test included, verified to redden
  when the defect is re-applied.
  Skill-local `scripts/` is upstream's own convention
  (bmad-party-mode/scripts/) and survives a refresh, unlike `_bmad/scripts/`
  (runbook class D). Twelve stdlib unittest cases ship beside it in
  `scripts/tests/`. What this does and does not buy against Macedo's T4, the
  harness membership test the plan opens on: the *verdict* is now deterministic
  -- which waves carry records, and which side of the rule date they landed on,
  are computed rather than judged, so the agent can no longer reason its way to
  "this gap is acceptable". The *invocation* is not. Three links in the chain
  are still prose: invoking the skill, running the script inside step 1, and
  obeying a non-zero exit. The fork ships two hooks (PostToolUse em-dash scrub,
  SessionEnd wrap reminder) and no PreToolUse anywhere, so nothing denies a
  tool call. Calling T4 satisfied would overstate it until a hook forces the
  invocation; that is Phase 4's job.
- `__pycache__/` and `*.pyc` ignored in .gitignore and
  templates/.gitignore.template, now that the fork ships runnable Python.

### Removed
- The fork's `.agents/skills` tree: 74 directories, 1,051 files (R4 of
  docs/reviews/harness-engineering-review-v1.md, 2026-10-01; roadmap R2 of
  the 2026-09-10 review, confirmed). Claude Code does not read it: "Not
  read: AGENTS.local.md, AGENTS.override.md, or anything under a .agents/
  directory" (https://code.claude.com/docs/en/memory#when-claude-code-reads-agentsmd),
  and it is not a skills location. No refresh had written it since the
  2026-07-19 incident, so it was a frozen pre-v0.3.0 snapshot, and no file
  in the fork read it. RQ's ruling (i), with an explicit yes before the
  `git rm`, in a commit of its own; the tree is in history before it.
  docs/upstream-refresh-runbook.md's "Current state" section says so. No
  instance is touched: green-ledger tracks its own second skill tree under
  `.agents/skills` and ffbapp has an untracked `.agents/` holding an
  unrelated plugin. At risk: a tool other than Claude Code (Cursor, Codex)
  pointed at the fork finds no skills, which was already true of every
  skill added since v0.3.0; `.gitleaks.toml` keeps two allowlist lines for
  paths that no longer exist, and docs/harness-conversion-plan.md still
  counts the tree.

### Fixed
- A newline ends a command in the wave gate (found while grading R1 of
  docs/reviews/harness-engineering-review-v1.md, 2026-10-01). bmad-dev-wave
  1.8.1 -> 1.8.2. `_prepass` marked every operator as ` \0op\0 `, and a
  newline is an operator, so the mark for a newline held the newline
  itself; shlex splits words at whitespace, cut the mark in two, and the
  halves were read as plain words. A newline therefore never ended a
  simple command. Two effects, both measured on 2026-10-01. Open: a
  guarded action on a second line passed whenever the first line's
  command takes its operands as text -- `echo x`, then the in-review
  `wave_status.py set`, a `sed -i` on `.bmad/wave-7A/wave.md`, an `rm` of
  it or a `cp` over an evaluation record: 8 of 10 such shapes exited 0.
  Closed on ordinary work: a `mkdir`, `rm` or `touch` followed by a second
  line put a NUL into a path and crashed the gate (`ValueError: embedded
  null character`), which the wrapper turned into a FAILED CLOSED denial,
  and a direct, literal `wave_status.py set` on a second line was refused
  as unreadable. ffbapp's 10,451 recorded Bash calls, replayed from a
  scratch cwd, hit the crash 61 times. The fix is one line: the newline's
  mark is `;`, which shlex leaves whole. Four tests cover the two-line
  shapes (176 across bmad-dev-wave's scripts, both trees; the E2b replay
  is unchanged). **Prediction, to be checked by R3's session.** Every
  newline splits a command as `;` does: the 10 guarded two-line shapes
  are denied and the 7 ordinary ones allowed; ffbapp's replay shows 0
  FAILED CLOSED and the same 72 other decisions as before (71 closure
  denials that are an artifact of the scratch cwd, 1 lifecycle); this
  session's own 105 Bash, Write and Edit calls are refused 9 times, all
  in R1's predicted classes (a verb in a variable; here-documents and
  interpreters whose text names `wave_status.py set`,
  `.bmad/wave-<id>/wave.md` or an evaluation record), and the two
  newline-caused refusals seen at 64 calls are gone. At risk: a line that
  ends in an operator and continues on the next now yields an empty
  command between two operators, which the parser drops; here-documents
  are read as before, since the body is consumed at the newline that
  follows `<<WORD`; a backslash-newline is still a continuation, not a
  separator (E2b's b14). The instance hand step in the runbook should
  carry this version, not 1.8.1.
- The Phase 2 backfill read sixteen of ffbapp's eighteen waves as `draft`,
  re-entering at step 1, when all eighteen are merged and done. Caught by
  running the migration against the real instance instead of the fixture:
  those waves have no `.bmad/wave-<id>/` at all, because their worktrees were
  swept by hand before bmad-merge-wave 1.1.0 started archiving checkpoints, so
  there was no marker evidence to infer from and the safe-direction default
  took over. The fix reuses Phase 1's own landing signal -- whether
  `docs/wave-<id>/` has merged into main -- and the ancestry test is the part
  that makes it safe: that directory also exists inside the wave's own
  worktree from step 3 onward, so mere presence would read every in-flight
  wave as finished. Re-run against a clone of the real repository, all twenty
  waves now migrate correctly, wave 5D included, whose stale step-2 checkpoint
  is overridden by its merged docs.
- bmad-close-epic's frontmatter claimed the epic-id argument matches an
  `## Epic <N>` block in waves.md. No such block exists: waves.md carries one
  flat table for the whole project, ordered by execution rather than by epic
  (in the ffbapp instance wave 6A sits between 4A and 4B). The epic is the
  leading digits of a Wave label. Caught by writing the gate against the real
  artifact; nothing had checked the documented contract against the file.
- The same pass found wave directories are lower-cased (`docs/wave-6a/`)
  while the Wave column spells them `6A`, so a check built on the column's
  own spelling finds no records anywhere. Recorded in the skill.
- Dating a wave via `gh pr view <branch suffix>` does not work and was never
  going to: waves.md's "Branch suffix" column is an intention, not a record.
  Probed against ffbapp, all three test branches returned "no pull requests
  found" -- real head refs carry tool prefixes and hashes
  (`claude/wave-4a-event-registry-825278`) and two waves' refs share no slug
  with the column at all. Substring matching is worse, since a wave's
  merge-cleanup branch matches the same label. The gate walks from the commit
  that added the wave's docs directory to the merge that brought it in, and
  dates the wave by that merge; verified against all eighteen ffbapp waves,
  with the seven pre-rule ones classified pre-rule and wave 5D correctly
  post-rule.

### Changed
- `core/config.yaml` no longer declares `permissions.forbidden_modes` (R2,
  2026-10-01). Nothing read it. The bypass half of the ban is now
  `permissions.disableBypassPermissionsMode: "disable"` in the settings
  template, which Claude Code enforces; the auto half is dropped by RQ's
  ruling of 2026-09-28, since bmad-wrap suggests auto and deny and ask
  rules bind in it as they do in acceptEdits.
- Eight `agents/custom-*.md` files collapsed to persona descriptors (Phase
  6.5 of docs/harness-conversion-plan.md): accessibility, analytics,
  design-critic, growth, legal, ml, sre, web-designer. Each was
  byte-identical to its `skills/agent-*/SKILL.md`; each now carries the H1,
  a provenance paragraph, and the overview paragraph verbatim, the shape the
  other seven custom agents already use, with the procedure living only in
  the skill. No prose edited, no skill changed, nothing bumped, nothing to
  mirror. The plan's premise that the installer reads `agents/` to build the
  roster was wrong: `[agents.*]` tables come from `module.yaml` alone
  (collectAgentsFromModuleYaml) and an install never copies `agents/` into a
  target. Verified anyway: a fresh `--target-project` install before and
  after emits the same 38 `[agents.*]` tables with the same codes
  (count-asserted), `resolve_party.py` on the target returns the same room
  of 38 and the same sixteen fork-only agents, and `--validate-only` passes
  both trees.
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
    regenerated (class C). Installer also creates _bmad/keelswell/ (its
    config.yaml now tracked like the other module config files) and the
    ignored _bmad/render/, _bmad/{core,bmm}/v6-shims/, and
    _bmad/agents/config.yaml (it treats the fork's _bmad/agents/ persona
    archive as a module dir).
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
  25 -> 26. The now-redundant name pin in _bmad/custom/config.toml is
  removed (12 overlay pins remain).
- .gitignore allowlists _bmad/scripts/config_utils.py and
  _bmad/scripts/render_skill.py so the tracked resolvers keep working
  from a fresh clone, and _bmad/keelswell/config.yaml like the other
  module config files; templates/.gitignore.template carries the same
  lines so initialised projects match.

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
