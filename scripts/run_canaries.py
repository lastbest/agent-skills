#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run every skills/<name>/checks/canary.py. Hits the network.

A canary proves the skill still works against the outside world. It must exit 0
on success and non-zero with an explanation on failure.

Run: python scripts/run_canaries.py [skill-name ...]
"""

from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    wanted = set(argv)
    found, failed = 0, []

    for d in sorted(os.listdir(SKILLS)):
        if wanted and d not in wanted:
            continue
        canary = os.path.join(SKILLS, d, "checks", "canary.py")
        if not os.path.isfile(canary):
            continue
        found += 1
        print(f"--- {d}", flush=True)
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, "-I", canary], cwd=os.path.join(SKILLS, d),
                           env=env, text=True, encoding="utf-8", errors="replace",
                           capture_output=True)
        print((r.stdout or "").rstrip())
        if r.returncode != 0:
            print((r.stderr or "").rstrip())
            failed.append(d)

    if not found:
        print("no canaries found")
        return 0
    if failed:
        print(f"\nFAIL — {len(failed)}/{found}: {', '.join(failed)}")
        return 1
    print(f"\nOK — {found} canary/canaries passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
