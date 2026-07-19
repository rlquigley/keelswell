# Keelswell
A production-grade fork of the BMAD Method, operated entirely in Claude Code:
23 merged base agents plus 9 custom agents (32 total, Wheel of Time display
names with install-time override), the Architecture Agent Expansion Pack, and
seven wave-based development skills (/bmad-create-wave ... /bmad-wrap).

Install into a project:
    npx bmad-method install --directory . --custom-source https://github.com/rlquigley/keelswell@v0.4.1 --tools claude-code --modules bmm,cis,tea,bmb --yes

The @tag pin installs the named release (clone cache records channel
"pinned" plus the resolved SHA). Known upstream cosmetic: the persisted
manifest still shows "version: main" for git-URL sources regardless of
the pin (bmad-method#2607); the install-time display line shows the
real version.
Note: this repository is PRIVATE. Installing machines need read access
(collaborator) plus configured git authentication -- SSH key or token.
First-time fork setup: ./install.sh --use-defaults --yes --user-name "<you>"
