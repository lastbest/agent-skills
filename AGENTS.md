# agent-skills

Portable Agent Skills (`SKILL.md`) that run under Claude Code, Codex, Cursor and
any other harness that reads the format.

**Read this file as a table of contents.** Detail lives in `docs/`. Keep it under
~150 lines — an always-on context file that grows stops being read.

Claude Code reads this through `CLAUDE.md`, which points here. There is one
canonical context file, not two.

## Map

- **[docs/authoring.md](docs/authoring.md)** — how to write a skill. Read before adding one.
- **[docs/harnesses.md](docs/harnesses.md)** — where each agent looks for skills, and how to install.
- **[README.md](README.md)** — the public face: what's here, how to install.

## Layout

```
skills/<skill-name>/
  SKILL.md          # required. frontmatter + instructions
  scripts/          # optional. executables the skill calls
  assets/           # optional. data the scripts read
  references/       # optional. long docs SKILL.md points to
  checks/canary.py  # optional. proves the skill still works (see below)
```

The whole repo is **one plugin** containing every skill. Idle skills cost almost
nothing — only `name` and `description` sit in the agent's context until one
matches — so bundling is cheaper than splitting. Split a skill into its own
repo only when it needs its own issues, license or collaborators.

Manifests, all pointing at `./skills/`:

| File | Read by |
|---|---|
| `.claude-plugin/plugin.json` + `marketplace.json` | Claude Code |
| `.codex-plugin/plugin.json` | Codex |
| `.cursor-plugin/plugin.json` | Cursor |

Bump `version` in **all three** together. `scripts/validate.py` fails if they drift.

## Adding a skill

1. `skills/<name>/SKILL.md` — `name` must equal the directory name, kebab-case.
2. Write the `description` last and carefully. It is the only thing the agent
   sees before deciding to load the skill — see [docs/authoring.md](docs/authoring.md).
3. Standard library only where you can. A skill that needs `pip install` is a
   skill most people won't run.
4. Add `checks/canary.py` if the skill depends on anything outside this repo.
5. `python scripts/validate.py` before committing.
6. Add the skill to the table in `README.md`.

## Canaries

A skill that scrapes a website or calls an undocumented endpoint **fails
silently**: the page changes, the parser matches nothing, and the skill
cheerfully reports "no results" — indistinguishable from a real empty answer.
That is worse than crashing.

So any skill with an external dependency ships `checks/canary.py`: it asks for
something that is *certain* to exist and fails loudly if it gets nothing back.
`.github/workflows/canary.yml` runs them weekly and opens an issue on failure.

Keep canaries cheap and polite — one small request, weekly, never a loop.

Note: GitHub disables scheduled workflows on public repos after 60 days with no
commits. Silence can mean the canary is off, not that everything is fine.

## Quality gates

```bash
python scripts/validate.py      # structure, frontmatter, manifest agreement
python scripts/run_canaries.py  # live checks (hits the network)
```

CI runs `validate.py` on every push and PR; `run_canaries.py` weekly.

## House rules

- Skill and directory names: lowercase, hyphen-separated.
- A skill's own docs go in its directory, not in `docs/` — `docs/` is about the
  repo, not about any one skill.
- Write `SKILL.md` in the language of the skill's users. The Korean civil-defense
  skill is in Korean on purpose; repo-level docs are in English.
- Never commit secrets, API keys or personal contact details. Manifests carry a
  GitHub URL, not an email address.
