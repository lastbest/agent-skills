#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structural checks for this repo. No network.

  - every skills/<dir> has SKILL.md with name + description frontmatter
  - frontmatter name matches the directory name, kebab-case
  - every script compiles
  - the three harness manifests agree on name/description/version
  - README lists every skill

Run: python scripts/validate.py
"""

from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
MANIFESTS = [
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    ".cursor-plugin/plugin.json",
]
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

problems: list[str] = []


def bad(msg: str) -> None:
    problems.append(msg)


def frontmatter(path: str) -> dict:
    """Minimal YAML front-matter reader: top-level `key: value` only."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    out, key = {}, None
    for line in text[3:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            out[key] = m.group(2).strip().strip("\"'")
        elif key and line.startswith((" ", "\t")):
            out[key] = (out[key] + " " + line.strip()).strip()
    return out


def check_skills() -> list[str]:
    names = []
    if not os.path.isdir(SKILLS):
        bad("skills/ is missing")
        return names
    for d in sorted(os.listdir(SKILLS)):
        sdir = os.path.join(SKILLS, d)
        if not os.path.isdir(sdir):
            continue
        names.append(d)
        md = os.path.join(sdir, "SKILL.md")
        if not os.path.isfile(md):
            bad(f"{d}: no SKILL.md")
            continue
        fm = frontmatter(md)
        if not fm.get("name"):
            bad(f"{d}: frontmatter has no name")
        elif fm["name"] != d:
            bad(f"{d}: frontmatter name {fm['name']!r} != directory name")
        if not NAME_RE.match(d):
            bad(f"{d}: directory name is not kebab-case")
        desc = fm.get("description", "")
        if len(desc) < 40:
            bad(f"{d}: description is too short to route on ({len(desc)} chars)")
        for dp, _, fns in os.walk(sdir):
            if "__pycache__" in dp:
                continue
            for fn in fns:
                if fn.endswith(".py"):
                    p = os.path.join(dp, fn)
                    try:
                        with open(p, encoding="utf-8") as fh:
                            compile(fh.read(), p, "exec")
                    except SyntaxError as e:
                        bad(f"{d}: {fn} does not compile: line {e.lineno}: {e.msg}")
    if not names:
        bad("no skills found")
    return names


def read_json(rel: str):
    """Load a manifest, naming a BOM explicitly.

    PowerShell's `Set-Content -Encoding utf8` prepends one, and the resulting
    JSONDecodeError is cryptic enough to waste real time.
    """
    p = os.path.join(ROOT, rel)
    if not os.path.isfile(p):
        bad(f"{rel} is missing")
        return None
    raw = open(p, "rb").read()
    if raw.startswith(b"\xef\xbb\xbf"):
        bad(f"{rel} starts with a UTF-8 BOM — rewrite it without one "
            f"(PowerShell's Set-Content -Encoding utf8 adds it)")
        raw = raw[3:]
    try:
        return json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        bad(f"{rel} is not valid JSON: {e}")
        return None


def check_manifests() -> None:
    loaded = {}
    for rel in MANIFESTS:
        m = read_json(rel)
        if m is not None:
            loaded[rel] = m
    for field in ("name", "description", "version"):
        vals = {rel: m.get(field) for rel, m in loaded.items()}
        if len(set(vals.values())) > 1:
            bad(f"manifests disagree on {field}: {vals}")

    market = read_json(".claude-plugin/marketplace.json")
    if market is None:
        return
    plugins = market.get("plugins") or []
    if not plugins:
        bad("marketplace.json lists no plugins")
        return
    plugin = loaded.get(".claude-plugin/plugin.json", {})
    entry = plugins[0]
    for field in ("name", "version"):
        if plugin.get(field) and entry.get(field) != plugin.get(field):
            bad(f"marketplace.json {field} {entry.get(field)!r} "
                f"!= plugin.json {plugin.get(field)!r}")


def check_readme(names: list[str]) -> None:
    p = os.path.join(ROOT, "README.md")
    if not os.path.isfile(p):
        bad("README.md is missing")
        return
    text = open(p, encoding="utf-8").read()
    for n in names:
        if n not in text:
            bad(f"{n}: not listed in README.md")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    names = check_skills()
    check_manifests()
    check_readme(names)

    if problems:
        print(f"FAIL — {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"OK — {len(names)} skill(s): {', '.join(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
