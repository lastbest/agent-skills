# agent-skills

Portable `SKILL.md` agent skills for **Claude Code, Codex, Cursor** and any other
harness that reads the Agent Skills format. Standard-library Python only — nothing
to install.

## Skills

| Skill | What it does |
|---|---|
| [`minbangwi-schedule`](skills/minbangwi-schedule/) | 민방위 교육일정 조회 — Korean civil-defense education schedules by region and date range, from 국민안전24. Searches administrative regions, sweeps a whole province, renders a month calendar as SVG. |

## Install

**Claude Code**

```bash
/plugin marketplace add lastbest/agent-skills
/plugin install agent-skills
```

**Codex / Cursor / others** — copy the skill directory into the agent's skills
folder:

```bash
git clone https://github.com/lastbest/agent-skills
cp -r agent-skills/skills/minbangwi-schedule ~/.codex/skills/
```

See [docs/harnesses.md](docs/harnesses.md) for each agent's path, and for the
claude.ai upload route.

**Without an agent** — they are ordinary CLIs:

```bash
python skills/minbangwi-schedule/scripts/minbangwi.py schedule 서울특별시 종로구 \
    --from 2026-11-01 --to 2026-11-30
```

## Contributing / adding a skill

[AGENTS.md](AGENTS.md) describes how the repo is laid out and what a new skill
needs. [docs/authoring.md](docs/authoring.md) is the guide to writing one.

```bash
python scripts/validate.py      # structure and manifest checks
python scripts/run_canaries.py  # live checks against external sites
```

## Why canaries

Several of these skills read public websites that offer no API and no versioning.
When such a site is redesigned the skill does not crash — it returns *nothing*,
which looks exactly like a legitimate empty result. A weekly workflow asks each
skill for something that is certain to exist and opens an issue if it comes back
empty. See [AGENTS.md](AGENTS.md#canaries).

## License

MIT.
