# Writing a skill

A skill is not documentation and not a library. It is **instructions an agent
reads when it decides your skill is relevant**, plus whatever code makes that
cheap. Two things decide whether it works: the description, and whether the
hard-won details survived into the file.

## The description is the product

Everything else in `SKILL.md` is invisible until the agent has already chosen to
load the skill. The frontmatter `description` is the entire basis for that
choice. A perfect skill with a vague description never runs.

Write it in the third person, and cover **what it does and when to use it** —
the second half is the part people skip.

```yaml
---
name: minbangwi-schedule
description: >
  민방위 교육일정을 지역(시도/시군구/행정동)과 검색기간으로 조회한다.
  "민방위 교육", "민방위 일정", "민방위 훈련 언제", 또는 특정 동네의 교육
  날짜·장소를 물어볼 때 사용한다. 네트워크 접속이 필요하다.
---
```

What makes that one work:

- **Real trigger phrases, in the words users actually type.** Not "civil defense
  training information retrieval" — the words someone would say.
- **Says when, not just what.** "…을 물어볼 때 사용한다."
- **States its requirements.** "네트워크 접속이 필요하다" stops an agent from
  reaching for it in a sandbox with no network.

Also worth stating: when **not** to use it, if there is an obvious near-miss
skill it could be confused with.

## Write down what you only learn by trying

The body's value is the things that are not guessable. From the civil-defense
skill, all three of these cost real debugging and all three are now one line in
`SKILL.md`:

- `pageIndex` must be sent or the endpoint returns an empty list with HTTP 200.
- The 시군구 parameter is mandatory; there is no province-wide query, so a
  province query means looping over its districts.
- Sejong has no district level, so its province code doubles as the district code.

If a future reader (you in six months, or an agent) would have to re-derive it,
it belongs in the file. Conversely, do not explain what the code already says.

## Shape

```
SKILL.md          # the instructions. keep it skimmable
scripts/          # the actual work. standard library where possible
assets/           # data the scripts read
references/       # long material SKILL.md links to, loaded only when needed
checks/canary.py  # proof it still works against the outside world
```

Put the work in `scripts/`, not in prose telling the agent how to do it by hand.
A deterministic script is cheaper, repeatable and testable; prose is none of
those. `SKILL.md` should mostly be *how to drive the script* and *how to read
what comes back*.

Keep `SKILL.md` short enough to read in one pass. Long reference material goes
in `references/` with a pointer, so it only enters context when actually needed.

## Tell the agent how to answer, not just how to query

The difference between a skill that returns data and one that is useful is
usually a short section near the end:

- Trim the output — nobody wants 469 rows pasted back.
- What a zero result means, and what to do about it (here: widen the range and
  re-check, because empty and broken look identical).
- Caveats worth passing to the user.

## Checklist

- [ ] `name` matches the directory, kebab-case
- [ ] `description` has trigger phrases, says when to use it, states requirements
- [ ] Non-obvious behaviour of the thing you're wrapping is written down
- [ ] Scripts run standalone, from any working directory
- [ ] Standard library only, or the dependency is stated
- [ ] `checks/canary.py` exists if anything external is involved
- [ ] A "how to answer" section
- [ ] `python scripts/validate.py` passes
- [ ] Added to the table in `README.md`

## Reference skill

[`skills/minbangwi-schedule/`](../skills/minbangwi-schedule/) is the worked
example: a CLI with subcommands, bundled data with a refresh path, an SVG
renderer, and a canary. Copy it and adapt.
