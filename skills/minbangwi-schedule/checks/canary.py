#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""safekorea.go.kr가 아직 이 스킬이 기대하는 모양인지 확인한다.

이 스킬은 공개 API가 아니라 HTML을 긁는다. 사이트가 개편되면 예외가 나는 게
아니라 **빈 결과**가 돌아오고, 그건 '정말 일정이 없음'과 구분이 안 된다.
그래서 여기서는 "있는 게 확실한 것"을 물어보고 비면 실패로 친다.

확인하는 세 가지:
  1. 일정 조회 — 여러 시군구 중 한 곳이라도 결과가 나오고, 필드가 파싱되는가
  2. 지역 코드표 — 페이지에 박힌 data.push({...})를 아직 긁을 수 있는가
  3. 담당부서 연락처 JSON 엔드포인트가 살아 있는가

한 시군구만 보면 그 지역이 그 분기에 일정을 안 올렸을 때 오탐이 난다
(실제로 동작구는 한 달 내내 0건인 적이 있다). 그래서 여러 곳을 돌려보고
하나라도 나오면 통과시킨다.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(HERE, "..", "scripts", "minbangwi.py")
spec = importlib.util.spec_from_file_location("minbangwi", SKILL)
mb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mb)

PROBES = ["서울특별시 강남구", "서울특별시 송파구", "부산광역시 해운대구", "대구광역시 달서구"]
MIN_AREAS = 3000          # 전국 시군구+읍면동. 현재 4072건
problems: list[str] = []


def check_schedule() -> None:
    today = dt.date.today()
    start, end = today.isoformat(), (today + dt.timedelta(days=89)).isoformat()
    regions = mb.load_regions()
    tried = []

    for probe in PROBES:
        codes, _ = mb.resolve(regions, probe.split())
        if not codes:
            problems.append(f"지역 해석 실패: {probe!r} — regions.json이 낡았을 수 있다")
            continue
        sido, sgg, emd = codes
        rows = mb.query_schedule(sido, sgg, emd, start, end)
        tried.append(f"{probe} {len(rows)}건")
        if not rows:
            continue

        print(f"일정 조회 OK — {probe} {len(rows)}건 ({start}~{end})")
        r = rows[0]
        if not re.search(r"\d{4}-\d{2}-\d{2}", r.get("교육일시", "")):
            problems.append(f"교육일시 파싱 실패: {r.get('교육일시')!r}")
        for field in ("지역", "교육대상", "교육장소"):
            if not r.get(field):
                problems.append(f"{field}가 비어 있다 — viewDetale 인자 순서가 바뀌었을 수 있다")
        return

    problems.append(
        "일정 0건 — 3개월 범위에서 어느 시군구도 결과가 없다. "
        f"pageIndex 파라미터나 표 마크업이 바뀌었을 가능성이 높다. 시도: {', '.join(tried)}"
    )


def check_region_table() -> None:
    """regions.json을 덮어쓰지 않고, 페이지에서 코드표를 아직 긁을 수 있는지만 본다."""
    page = mb.fetch_schedule_page({"menuSn": "58"})
    blocks = re.findall(r"data\.push\(\{(.*?)\}\)", page, re.S)
    if len(blocks) < MIN_AREAS:
        problems.append(
            f"지역 코드표 {len(blocks)}건 (기대 {MIN_AREAS}+) — "
            "data.push({...}) 형태가 바뀌면 refresh-regions가 깨진다"
        )
        return
    sample = dict(re.findall(r"(\w+)\s*:\s*'([^']*)'", blocks[0]))
    missing = [k for k in ("orgCd", "orgNm", "upperOrgCd", "fllOrgNm") if k not in sample]
    if missing:
        problems.append(f"코드표 필드 누락: {missing}")
    else:
        print(f"지역 코드표 OK — {len(blocks)}건")


def check_contacts() -> None:
    rows = mb.fetch_contacts("6110000", "3000000")     # 서울 종로구
    if not rows:
        problems.append("담당부서 연락처 JSON 0건 — 엔드포인트나 파라미터가 바뀌었다")
    elif "telno" not in rows[0] or "arcd3Nm" not in rows[0]:
        problems.append(f"연락처 JSON 필드가 바뀌었다: {sorted(rows[0])}")
    else:
        print(f"연락처 JSON OK — {len(rows)}건")


def main() -> int:
    for fn in (check_schedule, check_region_table, check_contacts):
        try:
            fn()
        except Exception as e:
            problems.append(f"{fn.__name__} 예외: {type(e).__name__}: {e}")

    if problems:
        print("\nFAIL — safekorea.go.kr가 바뀐 것 같다:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
