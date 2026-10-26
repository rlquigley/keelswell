# Keelswell
A production-grade fork of the BMAD Method, operated entirely in Claude Code:
23 merged base agents plus 15 custom agents (38 total, role-derived display
names with install-time override), the Architecture Agent Expansion Pack, and
seven wave-based development skills (/bmad-create-wave ... /bmad-wrap).

Install into a project:
    npx bmad-method@6.12.0 install --directory . --custom-source https://github.com/rlquigley/keelswell@v0.9.0 --tools claude-code --modules bmm,cis,tea,bmb --yes --pin bmb=v2.1.0 --pin cis=v0.2.1 --pin tea=v1.19.0

The @tag pin installs the named release (clone cache records channel
"pinned" plus the resolved SHA). Known upstream cosmetic: the persisted
manifest still shows "version: main" for git-URL sources regardless of
the pin (bmad-method#2607); the install-time display line shows the
real version.
Note: this repository is PRIVATE. Installing machines need read access
(collaborator) plus configured git authentication -- SSH key or token.
First-time fork setup: ./install.sh --use-defaults --yes --user-name "<you>"

## How it works

### High-level process map

![High-level process map in four lanes. You share an idea. AI planners plan the product and write the stories. AI builders group the stories into waves and build a wave. AI reviewers test and review it; if it fails, it goes back to be rebuilt. AI builders open a pull request, and you review and merge it. When the epic is done, AI reviewers audit it and the next epic starts; until then, the next wave is built.](docs/process-map-high-level.svg)

### Detailed process map

![Detailed process map in five lanes: you, AI planners, the AI lead, AI coders and AI reviewers. You install Keelswell and share an idea. AI planners research it, write the product brief and the PRD, design the UX if there is a UI, design the architecture, and write the epics and stories, and you approve the plan. The lead maps story dependencies and drafts the wave plan, which you approve. For each wave you start, the lead checks it is ready (if not, it is blocked), opens a workspace, has the tests designed, writes story details, asks you any open questions, and writes failing tests. AI coders code each story until the tests pass. A fresh-eyes reviewer approves the work, or it halts until you resume in a new session. You approve the commits; a critical wave also gets a specialist review, and serious issues go back to the coders. The lead records the review, opens a pull request and wraps up the session; you merge it and the lead cleans up. When the epic is done, reviewers audit it, the lead opens a closure pull request, and you merge it. With more epics, the next wave starts; otherwise you are done.](docs/process-map-detailed.svg)

### Keelswell skills

![Keelswell skills map in three lanes: you, wave skills and session skills. A session starts with /bmad-status-wave. /bmad-create-wave plans the waves. /bmad-dev-wave builds one wave; /bmad-resume-wave picks up a stopped wave. /bmad-wrap ends each session. You merge the pull request, and /bmad-merge-wave cleans up the wave. Until the epic is done, /bmad-dev-wave builds the next wave; then /bmad-close-epic closes the epic, you merge the closure pull request, and the next epic starts.](docs/process-map-skills.svg)
