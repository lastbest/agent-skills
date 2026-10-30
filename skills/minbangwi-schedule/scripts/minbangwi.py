#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""민방위 교육일정 조회 (국민안전24 safekorea.go.kr).

표준 라이브러리만 사용한다. 외부 패키지 설치 불필요.

사용 예:
    python minbangwi.py regions 사직
    python minbangwi.py regions --sido 서울특별시 --sgg 종로구
    python minbangwi.py schedule 서울특별시 종로구 사직동 --from 2026-11-01 --to 2027-01-31
    python minbangwi.py schedule 종로구 --target 31 --json
    python minbangwi.py refresh-regions
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request

BASE = "https://safekorea.go.kr"
CTX = "/safekorea-kor"
SCHEDULE_URL = BASE + CTX + "/edtr/clns/escd/educationSchedule.do"
CONTACT_URL = BASE + CTX + "/edtr/clns/dcif/departmentContactInformationJson.do"

HERE = os.path.dirname(os.path.abspath(__file__))
REGIONS_PATH = os.path.join(HERE, "..", "assets", "regions.json")
if HERE not in sys.path:          # 다른 스크립트가 import 해 쓸 때도 svgcal을 찾게
    sys.path.insert(0, HERE)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

EDU_TARGETS = {
    "10": "민방위대",
    "20": "신편대원",
    "31": "민방위대 편입 1~2년차대원",
    "32": "민방위대 편입 3~4년차대원",
    "33": "민방위대편입 2년차대원",
    "50": "자체교육인정자",
    "60": "민방위대 편입 5년차 이상",
}

EDU_TIMES = {"0": "평일교육", "1": "야간교육", "2": "주말교육"}

MAX_PAGES = 60


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
def _request(url: str, data: bytes | None = None, timeout: int = 30) -> str:
    headers = {"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"}
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_schedule_page(params: dict) -> str:
    return _request(SCHEDULE_URL + "?" + urllib.parse.urlencode(params))


def fetch_contacts(sido_cd: str, sgg_cd: str, emd_cd: str = "") -> list[dict]:
    body = urllib.parse.urlencode(
        {"sbLawArea1": sido_cd, "sbLawArea2": sgg_cd, "sbLawArea3": emd_cd}
    ).encode()
    try:
        return json.loads(_request(CONTACT_URL, data=body))
    except Exception:
        return []


# --------------------------------------------------------------------------
# 지역 코드 (행정동) 데이터
# --------------------------------------------------------------------------
def load_regions() -> dict:
    """번들된 regions.json을 읽는다. 없으면 사이트에서 새로 받아 저장한다."""
    if os.path.exists(REGIONS_PATH):
        with open(REGIONS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return refresh_regions()


def refresh_regions() -> dict:
    """교육일정 페이지에 인라인으로 박혀 있는 전체 행정구역 코드표를 긁어온다."""
    page = fetch_schedule_page({"menuSn": "58"})

    sido = []
    m = re.search(r'<select[^>]*id="sbLawArea1".*?</select>', page, re.S)
    if m:
        for code, name in re.findall(
            r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)</option>', m.group(0)
        ):
            name = html.unescape(name).strip()
            if code and name:
                sido.append({"orgCd": code, "orgNm": name})

    areas = []
    for block in re.findall(r"data\.push\(\{(.*?)\}\)", page, re.S):
        rec = dict(re.findall(r"(\w+)\s*:\s*'([^']*)'", block))
        if rec.get("orgCd"):
            areas.append(
                {
                    "orgCd": rec.get("orgCd", ""),
                    "orgNm": rec.get("orgNm", ""),
                    "upperOrgCd": rec.get("upperOrgCd", ""),
                    "fllOrgNm": rec.get("fllOrgNm", ""),
                    "arcd": rec.get("arcd", ""),
                    "step": rec.get("orgAcctoStepSeCd", ""),
                }
            )

    if not sido or not areas:
        raise SystemExit("지역 코드표를 추출하지 못했습니다. 사이트 구조가 바뀐 것 같습니다.")

    regions = {
        "updated": dt.date.today().isoformat(),
        "sido": sido,
        "areas": areas,
    }
    os.makedirs(os.path.dirname(REGIONS_PATH), exist_ok=True)
    with open(REGIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(regions, f, ensure_ascii=False, indent=1)
    return regions


def _sido_by_code(regions: dict) -> dict:
    return {s["orgCd"]: s["orgNm"] for s in regions["sido"]}


def sgg_list(regions: dict, sido_cd: str) -> list[dict]:
    """해당 시도에 속한 시군구 목록. 세종처럼 시군구 단계가 없으면 빈 목록."""
    return [
        a for a in regions["areas"]
        if a["step"] == "2" and a["upperOrgCd"] == sido_cd
    ]


def full_name(regions: dict, area: dict) -> str:
    if area.get("fllOrgNm"):
        return area["fllOrgNm"]
    return _sido_by_code(regions).get(area["upperOrgCd"], "") + " " + area["orgNm"]


def search_regions(regions: dict, query: str = "", sido: str = "", sgg: str = "",
                   level: str = "") -> list[dict]:
    """행정구역을 이름 조각으로 찾는다. 반환값은 시군구(step=2)/읍면동(step=3) 목록."""
    sido_names = _sido_by_code(regions)
    sido_codes = {name: code for code, name in sido_names.items()}
    sgg_by_code = {a["orgCd"]: a for a in regions["areas"] if a["step"] == "2"}

    results = []
    for a in regions["areas"]:
        if level and a["step"] != level:
            continue
        name = full_name(regions, a)
        if query and query not in name:
            continue
        if sido:
            top = a["upperOrgCd"] if a["step"] == "2" else (
                sgg_by_code.get(a["upperOrgCd"], {}).get("upperOrgCd", "")
            )
            if not (sido in sido_names.get(top, "") or sido_codes.get(sido) == top):
                continue
        if sgg:
            if a["step"] == "2":
                if sgg not in a["orgNm"]:
                    continue
            else:
                parent = sgg_by_code.get(a["upperOrgCd"], {})
                if sgg not in parent.get("orgNm", ""):
                    continue
        results.append({**a, "name": name})
    return results


def resolve(regions: dict, tokens: list[str]):
    """'서울특별시 종로구 사직동' 같은 입력을 (시도코드, 시군구코드, 읍면동코드)로 바꾼다.

    실패하면 (None, 후보목록)을 돌려준다.
    """
    text = " ".join(t for t in tokens if t).strip()
    if not text:
        return None, []

    sido_names = _sido_by_code(regions)
    sgg_by_code = {a["orgCd"]: a for a in regions["areas"] if a["step"] == "2"}

    def top_code(a):
        if a["step"] == "2":
            return a["upperOrgCd"]
        parent = a["upperOrgCd"]
        if parent in sgg_by_code:            # 보통의 읍면동 -> 시군구 -> 시도
            return sgg_by_code[parent]["upperOrgCd"]
        return parent if parent in sido_names else ""   # 세종: 시군구 단계가 없다

    parts = text.split()

    # 시도 이름만 들어온 경우. 사이트는 시군구가 필수라서 시군구 코드를 비워 두고,
    # 호출하는 쪽에서 그 시도의 시군구를 전부 돌게 한다. (시군구가 없는 세종은 시도 코드를 그대로 쓴다)
    sido_hits = [(c, n) for c, n in sido_names.items() if all(p in n for p in parts)]
    if len(sido_hits) == 1:
        code = sido_hits[0][0]
        return (code, "" if sgg_list(regions, code) else code, ""), []

    cands = []
    for a in regions["areas"]:
        name = full_name(regions, a)
        if all(p in name for p in parts):
            cands.append({**a, "name": name})

    if not cands:
        return None, []

    exact = [c for c in cands if c["orgNm"] == parts[-1]]
    pool = exact or cands

    # 가장 하위 레벨(읍면동)을 우선하되, 후보가 여러 개면 사용자에게 되묻는다
    dongs = [c for c in pool if c["step"] == "3"]
    sggs = [c for c in pool if c["step"] == "2"]
    chosen_pool = dongs if dongs else sggs
    if len(chosen_pool) != 1:
        return None, chosen_pool[:40]

    a = chosen_pool[0]
    if a["step"] == "2":
        return (top_code(a), a["orgCd"], ""), []
    sgg_cd = a["upperOrgCd"] if a["upperOrgCd"] in sgg_by_code else top_code(a)
    return (top_code(a), sgg_cd, a["orgCd"]), []


# --------------------------------------------------------------------------
# 일정 조회
# --------------------------------------------------------------------------
ROW_RE = re.compile(r'class="area"\s+href="javascript:viewDetale\((.*?)\);"', re.S)
FIELDS = ("지역", "교육대상", "교육구분", "교육일시", "교육장소", "지번주소", "도로명주소")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse_rows(page: str) -> list[dict]:
    rows = []
    for raw in ROW_RE.findall(page):
        raw = raw.strip()
        if raw.startswith("'"):
            raw = raw[1:]
        if raw.endswith("'"):
            raw = raw[:-1]
        vals = [html.unescape(v.strip()) for v in raw.split("','")]
        vals += [""] * (len(FIELDS) - len(vals))
        row = dict(zip(FIELDS, vals[: len(FIELDS)]))
        # 원본 DB에 지역/일자가 비어 있는 빈 레코드가 간혹 섞여 나온다 (교육일시가 ': ~ :')
        if not row["지역"] or not DATE_RE.match(row["교육일시"]):
            continue
        rows.append(row)
    return rows


def query_schedule(sido_cd: str, sgg_cd: str, emd_cd: str, start: str, end: str,
                   edu_target: str = "", edu_time: str = "",
                   max_pages: int = MAX_PAGES) -> list[dict]:
    """start/end는 YYYY-MM-DD. 전 페이지를 순회해서 모든 행을 모은다."""
    all_rows: list[dict] = []
    seen = set()
    for page_no in range(1, max_pages + 1):
        params = {
            "menuSn": "58",
            "q_area_cd_1": sido_cd,
            "q_area_cd_2": sgg_cd,
            "q_area_cd_3": emd_cd,
            "q_strdate": start.replace("-", ""),
            "q_enddate": end.replace("-", ""),
            "currentPage": str(page_no),
            "pageIndex": str(page_no),   # 이 파라미터가 없으면 결과가 비어서 나온다
            "edcTgtSeCd": edu_target,
            "hdaySe": edu_time,
            "eduTarget": edu_target,
            "eduTime": edu_time,
        }
        rows = parse_rows(fetch_schedule_page(params))
        if not rows:
            break
        fresh = []
        for r in rows:
            key = tuple(r.values())
            if key in seen:
                continue
            seen.add(key)
            fresh.append(r)
        all_rows.extend(fresh)
        if not fresh:          # 마지막 페이지를 계속 되돌려주는 경우 방어
            break
        if len(rows) < 10:     # 페이지당 10건
            break
    return all_rows


def query_sido(regions: dict, sido_cd: str, start: str, end: str,
               edu_target: str = "", edu_time: str = "",
               with_contact: bool = True, progress=None) -> list[dict]:
    """시도 전체 조회.

    사이트는 시군구가 필수 조건이라 시도 단위 조회가 없다. 그래서 그 시도의
    시군구를 하나씩 query_schedule로 돌린 뒤 합친다. 각 행에는 어느 시군구인지
    `시군구` 키를 붙인다.
    """
    rows: list[dict] = []
    sggs = sgg_list(regions, sido_cd)
    for i, sgg in enumerate(sggs, 1):
        got = query_schedule(sido_cd, sgg["orgCd"], "", start, end, edu_target, edu_time)
        if with_contact and got:
            attach_contacts(got, sido_cd, sgg["orgCd"])
        for r in got:
            r["시군구"] = sgg["orgNm"]
        rows.extend(got)
        if progress:
            progress(i, len(sggs), sgg["orgNm"], len(got))
    return sort_rows(rows)


def sort_rows(rows: list[dict]) -> list[dict]:
    """교육일시(날짜 -> 시작시각) 순으로 정렬한다."""
    def key(r):
        d = r.get("교육일시", "")
        m = DATE_RE.search(d)
        date = m.group(0) if m else "9999-99-99"
        tail = d.split(")", 1)[-1].strip() if ")" in d else ""
        return (date, tail[:5], r.get("시군구", ""), r.get("지역", ""))
    return sorted(rows, key=key)


def attach_contacts(rows: list[dict], sido_cd: str, sgg_cd: str, emd_cd: str = "") -> None:
    contacts = fetch_contacts(sido_cd, sgg_cd, emd_cd)
    by_dong = {c.get("arcd3Nm"): c for c in contacts}
    for r in rows:
        c = by_dong.get(r["지역"])
        r["담당부서"] = (c or {}).get("deptNm", "").strip()
        r["연락처"] = (c or {}).get("telno", "-")


# --------------------------------------------------------------------------
# 출력
# --------------------------------------------------------------------------
def print_table(rows: list[dict], cols: list[str]) -> None:
    if not rows:
        print("조회 결과가 없습니다.")
        return
    widths = [max(_w(c), max(_w(str(r.get(c, ""))) for r in rows)) for c in cols]
    line = "  ".join(c + " " * (w - _w(c)) for c, w in zip(cols, widths))
    print(line)
    print("-" * _w(line))
    for r in rows:
        v = [str(r.get(c, "")) for c in cols]
        print("  ".join(x + " " * (w - _w(x)) for x, w in zip(v, widths)))
    print(f"\n총 {len(rows)}건")


def _w(s: str) -> int:
    """한글은 2칸으로 센다."""
    return sum(2 if ord(ch) > 0x2E7F else 1 for ch in s)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def cmd_regions(args) -> int:
    regions = load_regions()
    level = {"sgg": "2", "dong": "3", "": ""}[args.level or ""]
    res = search_regions(regions, args.query or "", args.sido or "", args.sgg or "", level)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0
    rows = [
        {
            "행정구역": r["name"],
            "구분": "시군구" if r["step"] == "2" else "읍면동",
            "코드": r["orgCd"],
            "법정동코드": r["arcd"],
        }
        for r in res[: args.limit]
    ]
    print_table(rows, ["행정구역", "구분", "코드", "법정동코드"])
    if len(res) > args.limit:
        print(f"({len(res)}건 중 {args.limit}건만 표시 — --limit 으로 늘릴 수 있습니다)")
    return 0


def cmd_schedule(args) -> int:
    regions = load_regions()
    tokens = list(args.region)
    for extra in (args.sido, args.sgg, args.dong):
        if extra:
            tokens.append(extra)
    codes, cands = resolve(regions, tokens)
    if not codes:
        if cands:
            print("행정구역이 하나로 좁혀지지 않았습니다. 아래 중 하나를 더 구체적으로 지정하세요:\n")
            print_table(
                [{"행정구역": c["name"], "코드": c["orgCd"]} for c in cands],
                ["행정구역", "코드"],
            )
        else:
            print(f"'{' '.join(tokens)}' 에 해당하는 행정구역을 찾지 못했습니다. "
                  f"`regions` 명령으로 먼저 검색해 보세요.")
        return 1

    sido_cd, sgg_cd, emd_cd = codes
    today = dt.date.today()
    start = args.start or today.isoformat()
    end = args.end or (today + dt.timedelta(days=30)).isoformat()
    if dt.date.fromisoformat(end) < dt.date.fromisoformat(start):
        print("종료일이 시작일보다 빠릅니다.")
        return 1
    if (dt.date.fromisoformat(end) - dt.date.fromisoformat(start)).days > 95:
        print("※ 사이트는 최대 3개월 범위만 지원합니다. 결과가 잘릴 수 있습니다.\n", file=sys.stderr)

    sweep = sgg_cd == ""          # 시도만 지정된 경우
    if sweep:
        def progress(i, n, nm, cnt):
            print(f"[{i:2}/{n}] {nm} {cnt}건", file=sys.stderr, flush=True)
        rows = query_sido(regions, sido_cd, start, end,
                          args.target or "", args.time or "",
                          with_contact=not args.no_contact,
                          progress=None if args.quiet else progress)
    else:
        rows = query_schedule(sido_cd, sgg_cd, emd_cd, start, end,
                              args.target or "", args.time or "")
        if not args.no_contact:
            attach_contacts(rows, sido_cd, sgg_cd, emd_cd)
        rows = sort_rows(rows)

    if args.calendar:
        import svgcal
        label_key = "시군구" if sweep else "지역"
        info = svgcal.render(rows, " ".join(tokens), start, end, label_key, args.calendar)
        print(f"달력 SVG 저장: {os.path.abspath(args.calendar)}")
        print(f"  {len(rows)}건 / {info['days']}일 / 표기 {info['chips']}개 "
              f"({info['width']}x{info['height']})")
        return 0

    if args.summary:
        return print_summary(rows, tokens, start, end, sweep)

    if args.json:
        print(json.dumps(
            {
                "조회조건": {
                    "행정구역": " ".join(tokens),
                    "코드": {"시도": sido_cd, "시군구": sgg_cd, "읍면동": emd_cd},
                    "기간": [start, end],
                    "교육대상": EDU_TARGETS.get(args.target or "", ""),
                    "교육시간": EDU_TIMES.get(args.time or "", ""),
                },
                "건수": len(rows),
                "일정": rows,
            },
            ensure_ascii=False, indent=1))
        return 0

    head = " ".join(tokens)
    print(f"[{head}] {start} ~ {end} 민방위 교육일정")
    if args.target:
        print(f"교육대상: {EDU_TARGETS.get(args.target, args.target)}")
    if args.time:
        print(f"교육시간: {EDU_TIMES.get(args.time, args.time)}")
    print()
    cols = ["교육일시"] + (["시군구"] if sweep else []) + \
           ["지역", "교육대상", "교육구분", "교육장소"]
    if not args.no_contact:
        cols += ["연락처"]
    print_table(rows, cols)
    return 0


def print_summary(rows: list[dict], tokens: list[str], start: str, end: str,
                  sweep: bool) -> int:
    """같은 날·같은 시군구·같은 시간의 같은 교육을 한 줄로 접어 날짜별로 출력한다.

    시도 전체를 조회하면 수백 건이 나오는데, 대부분은 한 교육회차에 여러 행정동이
    묶인 것이라 그대로 늘어놓으면 읽을 수가 없다.
    """
    groups = {}
    for r in rows:
        d = r["교육일시"]
        m = DATE_RE.search(d)
        date = m.group(0) if m else ""
        when = d.split(")", 1)[-1].strip() if ")" in d else ""
        key = (date, when, r.get("시군구", ""), r["교육대상"], r["교육구분"], r["교육장소"])
        groups.setdefault(key, []).append(r["지역"])

    print(f"[{' '.join(tokens)}] {start} ~ {end} 민방위 교육일정")
    print(f"{len(rows)}건 / {len(groups)}개 교육회차\n")
    cur = None
    for (date, when, sgg, tgt, kind, place), dongs in sorted(groups.items()):
        if date != cur:
            cur = date
            print(f"\n## {date}")
        head = f"  {when}  " + (f"{sgg}  " if sweep else "")
        print(f"{head}{kind} / {tgt}")
        print(f"      {place}")
        print(f"      대상 {len(dongs)}개동: {' '.join(dongs)}")
    return 0


def cmd_refresh(args) -> int:
    regions = refresh_regions()
    print(f"지역 코드 {len(regions['areas'])}건 / 시도 {len(regions['sido'])}건 저장: "
          f"{os.path.normpath(REGIONS_PATH)}")
    return 0


def cmd_codes(args) -> int:
    print("교육대상 (--target)")
    for k, v in EDU_TARGETS.items():
        print(f"  {k:<4} {v}")
    print("\n교육시간 (--time)")
    for k, v in EDU_TIMES.items():
        print(f"  {k:<4} {v}")
    return 0


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    p = argparse.ArgumentParser(description="민방위 교육일정 조회 (국민안전24)")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("regions", help="행정동/시군구 코드 검색")
    r.add_argument("query", nargs="?", default="", help="이름 조각 (예: 사직, 종로)")
    r.add_argument("--sido", help="시도 이름으로 범위 제한")
    r.add_argument("--sgg", help="시군구 이름으로 범위 제한")
    r.add_argument("--level", choices=["sgg", "dong"], help="시군구만/읍면동만")
    r.add_argument("--limit", type=int, default=60)
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=cmd_regions)

    s = sub.add_parser("schedule", help="교육일정 조회")
    s.add_argument("region", nargs="*", help="행정구역 (예: 서울특별시 종로구 사직동)")
    s.add_argument("--sido")
    s.add_argument("--sgg")
    s.add_argument("--dong")
    s.add_argument("--from", dest="start", help="시작일 YYYY-MM-DD (기본: 오늘)")
    s.add_argument("--to", dest="end", help="종료일 YYYY-MM-DD (기본: 한 달 뒤)")
    s.add_argument("--target", choices=sorted(EDU_TARGETS), help="교육대상 코드")
    s.add_argument("--time", choices=sorted(EDU_TIMES), help="교육시간 코드")
    s.add_argument("--no-contact", action="store_true", help="담당부서 연락처 조회 생략")
    s.add_argument("--summary", action="store_true",
                   help="같은 교육회차에 묶인 행정동을 한 줄로 접어서 날짜별로 출력")
    s.add_argument("--calendar", metavar="OUT.svg",
                   help="결과를 달력 SVG로 저장 (날짜 칸에 '강남오전' 식으로 표기)")
    s.add_argument("--quiet", action="store_true", help="시도 전체 조회 진행상황 숨김")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_schedule)

    c = sub.add_parser("codes", help="교육대상/교육시간 코드표")
    c.set_defaults(func=cmd_codes)

    f = sub.add_parser("refresh-regions", help="행정구역 코드표 갱신")
    f.set_defaults(func=cmd_refresh)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
