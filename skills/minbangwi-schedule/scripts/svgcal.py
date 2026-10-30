#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""조회 결과를 달력 SVG로 그린다.

한 칸에 그날의 교육을 `강남오전` `성북야간` 식으로 늘어놓는다. 같은 구·같은
시간대는 한 번만 적는다(교육장이 여러 곳이어도 한 줄). 색은 시간대를 나타내는
보조 표시일 뿐이고, 글자 자체가 이미 시간대를 말하므로 색만으로 구분하게 두지
않는다.

색은 dataviz 스킬의 기본 카테고리 팔레트 1~3번 슬롯이다. 전 조합(all-pairs)
기준으로 명/암 양쪽에서 검증된 조합이라 세 개까지만 쓰고, 온라인(사이버교육)은
성격이 다르므로 중립 회색으로 뺐다.
"""

from __future__ import annotations

import calendar
import datetime as dt
import re
from xml.sax.saxutils import escape

DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")

# 시간대 -> (라벨, 밝은 배경용, 어두운 배경용)
BUCKETS = [
    ("오전", "#2a78d6", "#3987e5"),
    ("오후", "#eb6834", "#d95926"),
    ("야간", "#1baf7a", "#199e70"),
    ("온라인", "#87867f", "#9c9b93"),
]
ORDER = {b[0]: i for i, b in enumerate(BUCKETS)}

COL_W, GAP, PAD = 158, 6, 24
HDR_H, ROW_H, CELL_TOP = 26, 15, 26
MONTH_TITLE_H = 38


def bucket_of(row: dict) -> str:
    """교육일시와 교육구분으로 오전/오후/야간/온라인을 정한다."""
    when = row.get("교육일시", "")
    if "사이버" in row.get("교육구분", "") or "사이버" in row.get("교육장소", ""):
        return "온라인"
    times = TIME_RE.findall(when.split(")", 1)[-1])
    if not times:
        return "온라인"
    h, m = int(times[0][0]), int(times[0][1])
    if (h, m) == (0, 0) and len(times) > 1 and times[1][0] == "23":
        return "온라인"          # 00:00 ~ 23:59 = 종일 = 온라인 과정
    if h < 12:
        return "오전"
    if h < 18:
        return "오후"
    return "야간"


def short(name: str) -> str:
    """'강남구' -> '강남', '사직동' -> '사직', '조치원읍' -> '조치원'."""
    name = name.strip()
    if len(name) > 2 and name[-1] in "구시군동읍면":
        return name[:-1]
    return name


def collect(rows: list[dict], label_key: str) -> dict:
    """날짜 -> [(시간대, 라벨)] (중복 제거, 시간대 -> 이름 순 정렬)"""
    days: dict[str, set] = {}
    for r in rows:
        m = DATE_RE.search(r.get("교육일시", ""))
        if not m:
            continue
        days.setdefault(m.group(0), set()).add(
            (bucket_of(r), short(r.get(label_key) or r.get("지역", "")))
        )
    return {
        d: sorted(v, key=lambda x: (ORDER[x[0]], x[1]))
        for d, v in days.items()
    }


def months_between(start: dt.date, end: dt.date) -> list[tuple[int, int]]:
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def render(rows: list[dict], heading: str, start: str, end: str,
           label_key: str, path: str) -> dict:
    d0, d1 = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    days = collect(rows, label_key)
    n_chips = sum(len(v) for v in days.values())

    cal = calendar.Calendar(firstweekday=6)          # 일요일 시작
    width = PAD * 2 + COL_W * 7 + GAP * 6

    body: list[str] = []
    y = PAD

    # ── 제목과 범례 ────────────────────────────────────────────────
    body.append(f'<text class="h1" x="{PAD}" y="{y + 18}">{escape(heading)}</text>')
    body.append(f'<text class="sub" x="{PAD}" y="{y + 38}">'
                f'{start} ~ {end} · 교육 {len(rows)}건 · 표기 {n_chips}개</text>')
    lx = width - PAD
    for name, _, _ in reversed(BUCKETS):
        lx -= 58
        body.append(f'<rect class="sw b{ORDER[name]}" x="{lx}" y="{y + 28}" '
                    f'width="9" height="9" rx="2"/>')
        body.append(f'<text class="legend" x="{lx + 14}" y="{y + 36}">{name}</text>')
    y += 58

    for (yr, mo) in months_between(d0, d1):
        body.append(f'<text class="h2" x="{PAD}" y="{y + 20}">{yr}년 {mo}월</text>')
        y += MONTH_TITLE_H

        for i, wd in enumerate("일월화수목금토"):
            x = PAD + i * (COL_W + GAP)
            cls = "wd sun" if i == 0 else ("wd sat" if i == 6 else "wd")
            body.append(f'<text class="{cls}" x="{x + COL_W / 2}" y="{y + 17}">{wd}</text>')
        y += HDR_H

        for week in cal.monthdatescalendar(yr, mo):
            if all(d.month != mo for d in week):
                continue
            tallest = max((len(days.get(d.isoformat(), [])) for d in week), default=0)
            h = CELL_TOP + max(tallest, 1) * ROW_H + 8

            for i, d in enumerate(week):
                x = PAD + i * (COL_W + GAP)
                inside = d.month == mo and d0 <= d <= d1
                body.append(f'<rect class="cell{"" if inside else " off"}" x="{x}" '
                            f'y="{y}" width="{COL_W}" height="{h}" rx="6"/>')
                dcls = "dnum" if inside else "dnum off"
                if inside and i == 0:
                    dcls = "dnum sun"
                body.append(f'<text class="{dcls}" x="{x + 9}" y="{y + 17}">{d.day}</text>')

                if not inside:
                    continue
                for j, (bk, name) in enumerate(days.get(d.isoformat(), [])):
                    cy = y + CELL_TOP + j * ROW_H
                    body.append(f'<rect class="bar b{ORDER[bk]}" x="{x + 9}" y="{cy}" '
                                f'width="3" height="11" rx="1.5"/>')
                    body.append(f'<text class="chip" x="{x + 17}" y="{cy + 9.5}">'
                                f'{escape(name + bk)}</text>')
            y += h + GAP
        y += 10

    height = y + PAD - GAP
    svg = SVG_TEMPLATE.format(w=width, h=height, body="\n".join(body))
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return {"days": len(days), "chips": n_chips, "width": width, "height": height}


SVG_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" \
viewBox="0 0 {w} {h}" font-family="'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif">
<style>
  svg {{
    --surface-0:#f4f3f0; --surface-1:#fcfcfb; --surface-off:#eceae5;
    --line:#dedcd6; --text-primary:#0b0b0b; --text-secondary:#52514e;
    --text-muted:#8b8a84; --sun:#b4453f;
    --b0:#2a78d6; --b1:#eb6834; --b2:#1baf7a; --b3:#87867f;
  }}
  @media (prefers-color-scheme: dark) {{
    svg:where(:not([data-theme="light"])) {{
      --surface-0:#121211; --surface-1:#1a1a19; --surface-off:#161615;
      --line:#33332f; --text-primary:#f0efec; --text-secondary:#c3c2b7;
      --text-muted:#76756e; --sun:#e07b74;
      --b0:#3987e5; --b1:#d95926; --b2:#199e70; --b3:#9c9b93;
    }}
  }}
  .bg {{ fill: var(--surface-0); }}
  .cell {{ fill: var(--surface-1); stroke: var(--line); stroke-width: 1; }}
  .cell.off {{ fill: var(--surface-off); stroke: none; }}
  .h1 {{ fill: var(--text-primary); font-size: 17px; font-weight: 700; }}
  .h2 {{ fill: var(--text-primary); font-size: 14px; font-weight: 700; }}
  .sub, .legend {{ fill: var(--text-secondary); font-size: 11px; }}
  .wd {{ fill: var(--text-secondary); font-size: 11px; font-weight: 600;
         text-anchor: middle; }}
  .wd.sun {{ fill: var(--sun); }}
  .dnum {{ fill: var(--text-primary); font-size: 12px; font-weight: 700; }}
  .dnum.sun {{ fill: var(--sun); }}
  .dnum.off {{ fill: var(--text-muted); font-weight: 400; }}
  .chip {{ fill: var(--text-primary); font-size: 10.5px; }}
  .b0 {{ fill: var(--b0); }} .b1 {{ fill: var(--b1); }}
  .b2 {{ fill: var(--b2); }} .b3 {{ fill: var(--b3); }}
</style>
<rect class="bg" x="0" y="0" width="{w}" height="{h}"/>
{body}
</svg>
"""
