# Harnesses

`SKILL.md` is a shared format — the Agent Skills spec, originally from Anthropic
and now under neutral stewardship. The skills here are plain Markdown plus
standard-library Python, so what differs between agents is **where the files go**,
not what's in them.

## Install paths

| Agent | Project | User |
|---|---|---|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` |
| Codex | `.codex/skills/` or `.agents/skills/` | `~/.codex/skills/` |
| Cursor | `.cursor/skills/` | — |

Cursor's docs state it also reads Claude's and Codex's skill directories, so one
install can cover more than one agent.

> The Codex and Cursor paths come from vendor docs and community repos that do
> not fully agree. Verify against your installed version before relying on them.

## Installing

**Claude Code** — the marketplace route, which also keeps it updated:

```bash
/plugin marketplace add lastbest/agent-skills
/plugin install agent-skills
```

**Anything else** — copy the directory:

```bash
git clone https://github.com/lastbest/agent-skills
cp -r agent-skills/skills/<name> ~/.codex/skills/
```

**claude.ai / Cowork** — upload a zip of one skill directory:

```bash
cd skills && zip -r ../<name>.zip <name>
```

Build the zip with `zip` or `python -m zipfile`, not PowerShell's
`Compress-Archive` — its archives have been rejected by the uploader.

**No agent at all.** The scripts are ordinary CLIs:

```bash
python skills/minbangwi-schedule/scripts/minbangwi.py schedule 종로구
```

## Manifests

Each harness reads its own manifest; all three point at the same `./skills/`.

- `.claude-plugin/plugin.json` — the plugin itself
- `.claude-plugin/marketplace.json` — the marketplace listing it, `source: "./"`
- `.codex-plugin/plugin.json`
- `.cursor-plugin/plugin.json`

They duplicate `name`, `description` and `version` by design — each harness wants
its own file. `scripts/validate.py` checks they agree, because hand-editing one
and forgetting the others is the obvious failure.
