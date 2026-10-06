# -*- coding: utf-8 -*-
"""가상 기업 엑셀 3개 + 공개자료 → 회사별 대시보드 항목 JSON (schema "handoff-v1").

기준 문서: junhee/docs/dashboard_items_team_handoff.txt, 규칙: junhee/WORK_RULES_0926.md
- 입력: junhee/data/samples/*.xlsx (기업정보·제품정보·거래처·수출실적·물류 시트만 읽는다. '근거'·'결측목록' 시트는 읽지 않는다.
  물류 시트의 예정도착일·실제도착일·운임(USD) 열(v0.3, add_logistics_columns.py)이 있으면 납기 준수율·리드타임·운송비 비중과 물류 점수를 계산한다),
        junhee/data/raw/** 공개자료, junhee/data/processed/{stability,price}.json (기존 extract_summary.py 결과 재사용)
- 출력: junhee/data/processed/companies/<company_id>.json, index.json
- 점수는 계산하지 않는다 (handoff: 평가 기준 확정 후 추가). 값이 없는 항목은 status 로만 표시하고 만들어 넣지 않는다.
- 결측 원칙: 빈칸은 0 이나 임의 값으로 채우지 않는다. 금액·통화·거래일·목적국 빈칸 행은 합계에서 빼고 건수만 기록한다.
  취소반품 Y(수량·금액 0)는 실제 0 으로 세고 유효 실적에서 제외한다. 완전 중복 행은 1개만 남긴다.
  행이 통째로 없는 달은 0 이 아니라 결측(자료 없음)으로 본다.

실행: python junhee/scripts/build_company_items.py
"""
import csv
import hashlib
import json
import re
import statistics
import sys
import warnings
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import openpyxl

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_summary import F_CSL, F_FREIGHT, F_HSK, F_KOTRA, F_WSTS, hwpx_text_lines  # noqa: E402
import public_api_items as pai  # noqa: E402  (2026-09-26) 공개 API 원자료 → 항목. 원자료가 없으면 기존 '미확인' 유지

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SAMPLES = ROOT / "data" / "samples"
PROCESSED = ROOT / "data" / "processed"
OUT = PROCESSED / "companies"

SCHEMA = "handoff-v1"
DATA_CLASS = "가상 데이터 · 시연용"
COMPANY_IDS = {"한빛반도체": "hanbit", "대성일렉트로닉스": "daesung", "새벽반도체": "saebyeok"}
STATUS = ("확인됨", "자료 부족", "미확인", "검색 결과 없음", "검색 불가")
ISO2 = {"미국": "US", "중국": "CN", "영국": "GB", "인도": "IN", "캐나다": "CA", "멕시코": "MX", "스위스": "CH",
        "콜롬비아": "CO", "에콰도르": "EC", "캄보디아": "KH", "짐바브웨": "ZW", "EU": "EU", "독일": "DE", "일본": "JP", "베트남": "VN"}
# WTO 관세조치 파일(reporter 코드). 독일은 EU(U918) 파일. 파일이 없는 나라(베트남 등)는 '자료 부족'.
TARIFF_FILE = {"미국": "C840", "중국": "C156", "영국": "C826", "EU": "U918", "독일": "U918", "캐나다": "C124",
               "멕시코": "C484", "인도": "C356", "스위스": "C756", "콜롬비아": "C170", "에콰도르": "C218",
               "캄보디아": "C116", "짐바브웨": "C716"}
# 관세청 운송비 보도자료의 항로명 (목적국 → 표에 있는 항로). 표에 없는 나라는 '자료 부족'.
FREIGHT_ROUTES = {"미국": ["미국서부", "미국동부", "미국"], "중국": ["중국"], "일본": ["일본"], "베트남": ["베트남"],
                  "독일": ["유럽연합"], "EU": ["유럽연합"]}
REASON_COLS = [("금액", "금액 빈칸"), ("통화", "통화 빈칸"), ("거래일", "거래일 빈칸"), ("목적국", "목적국 빈칸"),
               ("제품ID", "제품ID 빈칸"), ("거래처ID", "거래처ID 빈칸"), ("순중량(kg)", "순중량 빈칸"), ("수량", "수량 빈칸")]
CRITICAL = ("금액", "통화", "거래일", "목적국")  # 이 값이 없으면 합계에서 뺀다
REAL_NAME_PATTERNS = ("삼성", "하이닉스", "samsung", "hynix")  # JSON 에 들어가면 안 되는 실제 기업명


# ---------------------------------------------------------------- 유틸
def blank(v):
    return v is None or str(v).strip() == ""


def num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def as_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", v.strip())
        if m:
            try:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                return None
    return None


def ym_str(ym):
    return f"{ym[0]}-{ym[1]:02d}"


def ym_add(ym, k):
    n = ym[0] * 12 + (ym[1] - 1) + k
    return (n // 12, n % 12 + 1)


def ym_range(a, b):
    out, cur = [], a
    while cur <= b:
        out.append(cur)
        cur = ym_add(cur, 1)
    return out


def r2(x, d=2):
    return None if x is None else round(x + 1e-9, d)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_name(s):
    return re.sub(r"[^A-Z0-9]", "", str(s or "").upper())


def read_sheet(wb, name, id_col):
    """헤더 행(첫 셀 == id_col)을 찾아 dict 목록으로 읽는다. 값이 하나도 없는 행은 건너뛴다."""
    ws = wb[name]
    rows = list(ws.iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows) if r and r[0] == id_col)
    hdr = list(rows[hi])
    out = []
    for r in rows[hi + 1:]:
        if r and any(v is not None and str(v).strip() != "" for v in r):
            out.append({hdr[i]: r[i] for i in range(min(len(hdr), len(r))) if hdr[i]})
    return out


def item(key, label, status, value=None, unit=None, period=None, as_of=None, source=None, basis=None, note=None, rows=None, **extra):
    assert status in STATUS, status
    d = {"key": key, "label": label, "status": status, "value": value, "unit": unit, "period": period,
         "as_of": as_of, "source": source, "basis": basis, "note": note}
    if rows is not None:
        d["rows"] = rows
    d.update(extra)
    return d


# ---------------------------------------------------------------- 공개자료 로더 (캐시)
_cache = {}


def hsk_table():
    """HSKCD(10자리) → {name, control_numbers[]}"""
    if "hsk" not in _cache:
        wb = openpyxl.load_workbook(F_HSK, read_only=True, data_only=True)
        t = {}
        for r in wb.worksheets[0].iter_rows(min_row=2, values_only=True):
            if r and r[0]:
                ctrl = [c.strip() for c in str(r[3] or "").split(",") if c.strip()]
                t[str(r[0]).strip()] = {"name": str(r[1] or "").strip(), "name_en": str(r[2] or "").strip(), "control_numbers": ctrl}
        _cache["hsk"] = t
    return _cache["hsk"]


def kotra():
    if "kotra" not in _cache:
        with open(F_KOTRA, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        hs_cols = [h for h in rows[0] if "HS_코드" in h]
        _cache["kotra"] = (rows, hs_cols)
    return _cache["kotra"]


def csl():
    """정규화한 name/alt_names → 명단 레코드 목록"""
    if "csl" not in _cache:
        idx = defaultdict(list)
        n = 0
        latest = ""
        with open(F_CSL, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                n += 1
                rec = {"name": r.get("name", ""), "addresses": r.get("addresses", ""), "source": r.get("source", ""),
                       "start_date": r.get("start_date", ""), "end_date": r.get("end_date", "")}
                if rec["start_date"] > latest:
                    latest = rec["start_date"]
                keys = {normalize_name(r.get("name"))}
                for alt in (r.get("alt_names") or "").split(";"):
                    keys.add(normalize_name(alt))
                keys.discard("")
                for k in keys:
                    idx[k].append(rec)
        _cache["csl"] = (idx, n, latest)
    return _cache["csl"]


def wsts_regions():
    """WSTS Monthly Data: region → {(y,m): 1000 US$}"""
    if "wsts" not in _cache:
        wb = openpyxl.load_workbook(F_WSTS, read_only=True, data_only=True)
        ws = wb["Monthly Data"]
        series = defaultdict(dict)
        year = None
        for r in ws.iter_rows(values_only=True):
            if r and isinstance(r[0], int) and 1980 <= r[0] <= 2100:
                year = r[0]
            elif r and r[0] in ("Americas", "Europe", "Japan", "Asia Pacific", "Worldwide") and year:
                for m in range(12):
                    v = r[1 + m]
                    if isinstance(v, (int, float)):
                        series[r[0]][(year, m + 1)] = float(v)
        _cache["wsts"] = dict(series)
    return _cache["wsts"]


def tariff_table(code):
    """WTO 관세조치 파일: hs6 → [(year_dt, best_avlbl, imports)] (조치일 순). 파일 없으면 None."""
    key = ("tariff", code)
    if key not in _cache:
        f = RAW / "test1_prices" / f"{code}_C410.csv"
        if not f.exists():
            _cache[key] = None
        else:
            d = defaultdict(list)
            meta = {}
            with open(f, encoding="utf-8-sig", newline="") as fh:
                for r in csv.DictReader(fh):
                    meta.setdefault("reporter_name", r.get("reporter_name"))
                    meta.setdefault("partner_name", r.get("partner_name"))
                    d[r["hs_code"]].append((r["year_dt"], num(r.get("best_avlbl")), num(r.get("imports"))))
            for k in d:
                d[k].sort()
            _cache[key] = (dict(d), meta, f.name)
    return _cache[key]


def freight_tables():
    """관세청 hwpx: {mode: {"unit":…, "routes": {항로: [(y,m,value)]}}} — 해상수출·해상수입·항공수입을 구분한다."""
    if "freight" not in _cache:
        L = hwpx_text_lines(F_FREIGHT)
        specs = [("해상수출", "해상 수출 운송비용 현황 (", "천원/2TEU"), ("해상수입", "해상 수입 운송비용 현황 (", "천원/2TEU"),
                 ("항공수입", "항공 수입 운송비용 현황 (", "원/kg")]
        starts = []
        for mode, key, unit in specs:
            idx = next((i for i, l in enumerate(L) if key in l), None)
            if idx is not None:
                starts.append((idx, mode, unit))
        starts.sort()
        out = {}
        for k, (start, mode, unit) in enumerate(starts):
            end = starts[k + 1][0] if k + 1 < len(starts) else len(L)
            routes = defaultdict(list)
            route = None
            i = start
            while i < end:
                l = L[i]
                if l in ("미국", "유럽연합", "중동", "중국", "일본", "베트남"):
                    route = l
                    if i + 1 < end and L[i + 1] in ("서부", "동부"):
                        route = l + L[i + 1]
                        i += 1
                elif l == "유럽" and i + 1 < end and L[i + 1] == "연합":  # 월별 표에서는 '유럽'·'연합' 두 문단으로 나뉨
                    route = "유럽연합"
                    i += 1
                elif l in ("서부", "동부"):
                    route = "미국" + l
                elif re.fullmatch(r"\d{4}", l) and i + 1 < end and L[i + 1] == "금액" and route:
                    year, j, month = int(l), i + 2, 1
                    while j < end and month <= 12 and re.fullmatch(r"-?[\d,]+(\.\d+)?", L[j]):
                        routes[route].append((year, month, float(L[j].replace(",", ""))))
                        month += 1
                        j += 1
                    i = j
                    continue
                i += 1
            out[mode] = {"unit": unit, "routes": dict(routes)}
        _cache["freight"] = out
    return _cache["freight"]


def processed_json(name):
    key = ("json", name)
    if key not in _cache:
        f = PROCESSED / f"{name}.json"
        _cache[key] = json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    return _cache[key]


# ---------------------------------------------------------------- 회사 파일
def load_company(path):
    wb = openpyxl.load_workbook(path, data_only=True)  # 수식 값은 캐시된 값을 읽는다
    info = {}
    for r in wb["기업정보"].iter_rows(values_only=True):
        # '생성 근거' 등 실제 기업명이 들어 있는 항목은 읽지 않는다
        if r and r[0] in ("company", "company_en", "data_class", "기준기간", "금액 통화", "template_version", "작성일"):
            info[r[0]] = r[1]
    return {
        "info": info,
        "products": read_sheet(wb, "제품정보", "제품ID"),
        "customers": read_sheet(wb, "거래처", "거래처ID"),
        "actuals": read_sheet(wb, "수출실적", "실적ID"),
        "logistics": read_sheet(wb, "물류", "물류ID"),
    }


def process_actuals(raw_rows):
    """중복 제거 → 취소 건 분리 → 결측 사유 집계 → 유효 행. 빈칸은 채우지 않는다."""
    seen, dedup, dups = set(), [], 0
    for r in raw_rows:
        key = tuple(sorted((k, str(v)) for k, v in r.items()))
        if key in seen:
            dups += 1
            continue
        seen.add(key)
        dedup.append(r)
    cancelled, active = [], []
    for r in dedup:
        (cancelled if str(r.get("취소반품") or "").strip().upper() == "Y" else active).append(r)
    reasons = {label: 0 for _, label in REASON_COLS}
    ids_by = {label: [] for _, label in REASON_COLS}   # 결측 안내 창에 보여줄 실적ID (앞 6개만 저장)
    date_errs = []
    rows = []
    for r in active:
        flags = {col: blank(r.get(col)) for col, _ in REASON_COLS}
        for col, label in REASON_COLS:
            if flags[col]:
                reasons[label] += 1
                ids_by[label].append(str(r.get("실적ID") or "?"))
        d = as_date(r.get("거래일"))
        row = {
            "id": r.get("실적ID"), "date": d, "ym": (d.year, d.month) if d else None,
            "product": None if flags["제품ID"] else str(r.get("제품ID")).strip(),
            "customer": None if flags["거래처ID"] else str(r.get("거래처ID")).strip(),
            "country": None if flags["목적국"] else str(r.get("목적국")).strip(),
            "iso2": None if blank(r.get("목적국코드")) else str(r.get("목적국코드")).strip(),
            "qty": None if flags["수량"] else num(r.get("수량")),
            "weight": None if flags["순중량(kg)"] else num(r.get("순중량(kg)")),
            "amount": None if flags["금액"] else num(r.get("금액")),
            "currency": None if flags["통화"] else str(r.get("통화")).strip(),
            "excluded": [label for col, label in REASON_COLS if col in CRITICAL and flags[col]],
        }
        if d is None and not flags["거래일"]:
            row["excluded"].append("거래일 형식 오류")
            date_errs.append(str(r.get("실적ID") or "?"))
        rows.append(row)
    valid = [r for r in rows if not r["excluded"]]
    quality = {
        "rows_total": len(raw_rows), "rows_after_dedup": len(dedup), "duplicates_removed": dups,
        "cancelled_zero_rows": len(cancelled), "rows_valid": len(valid),
        "rows_excluded_from_totals": len(rows) - len(valid), "excluded_by_reason": reasons,
        "excluded_ids_by_reason": {k: v[:6] for k, v in ids_by.items() if v},
        "date_format_errors": len(date_errs), "date_format_error_ids": date_errs[:6],
    }
    return rows, valid, cancelled, quality


# ---------------------------------------------------------------- 항목 계산
def monthly_sums(rows, months):
    """월별 합계. 행이 하나도 없는 달은 None(결측)."""
    s, has = defaultdict(float), set()
    for r in rows:
        s[r["ym"]] += r["amount"]
        has.add(r["ym"])
    return [{"month": ym_str(m), "value_usd": r2(s[m]) if m in has else None, "rows": sum(1 for r in rows if r["ym"] == m)} for m in months]


def build_regulation(c, country, ctx):
    hsk = hsk_table()
    prod_rows = []
    found = unsearchable = 0
    for p in ctx["products"]:
        if not p["input_hsk"]:
            prod_rows.append({"product_id": p["id"], "product": p["name"], "input_hsk": "", "hsk_name": None, "control_numbers": [],
                              "status": "검색 불가", "note": "HSK 없음"})
            unsearchable += 1
            continue
        hit = hsk.get(p["input_hsk"])
        if hit and hit["control_numbers"]:
            found += 1
            prod_rows.append({"product_id": p["id"], "product": p["name"], "input_hsk": p["input_hsk"], "hsk_name": hit["name"],
                              "control_numbers": hit["control_numbers"], "status": "확인됨", "note": "후보"})
        else:
            prod_rows.append({"product_id": p["id"], "product": p["name"], "input_hsk": p["input_hsk"], "hsk_name": hit["name"] if hit else None,
                              "control_numbers": [], "status": "검색 결과 없음", "note": "연계표에 통제번호 없음" if hit else "연계표에 해당 HSK 없음"})
    status = "확인됨" if found else ("검색 불가" if unsearchable == len(prod_rows) else "검색 결과 없음")
    ctrl = item("export_control_candidates", "수출통제 후보 (통제번호·품목명)", status, value=found, unit="후보 있는 제품 수",
                as_of="2026-09-01", source=F_HSK.name, basis="제품정보의 입력HSK(10자리)를 HSK연계표 HSKCD 와 정확히 대조, CNTRLNO 를 쉼표로 나눠 후보 목록으로",
                note="후보 표시이며 해당 여부 판정 아님", rows=prod_rows)

    rows_all, hs_cols = kotra()
    iso = ISO2.get(country)
    hs6s = ctx["hs6_list"]
    if not iso:
        reg = item("import_regulation_records", "목적국 수입규제 기록", "검색 불가", source=F_KOTRA.name, as_of="2026-06-03",
                   note="목적국 ISO2 코드 미확인")
    elif not hs6s:
        reg = item("import_regulation_records", "목적국 수입규제 기록", "검색 불가", source=F_KOTRA.name, as_of="2026-06-03",
                   basis=f"규제시행국={iso}", note="분석 HS6 가 있는 제품이 없어 품목 검색 불가")
    else:
        by_country = [r for r in rows_all if r["규제시행국"] == iso]
        hits = []
        for r in by_country:
            codes = [str(r[h]).strip() for h in hs_cols if not blank(r[h])]
            matched = sorted({cd for cd in codes for h6 in hs6s if len(cd) >= 4 and (cd.startswith(h6) or h6.startswith(cd))})
            if matched:
                hits.append({"item": (r.get("품목명") or "").strip(), "type_and_status": (r.get("규제형태(진행상황)") or "").strip(),
                             "target_origin": (r.get("규제대상국 ") or r.get("규제대상국") or "").strip(),
                             "period_raw": (r.get("최종 판정결과(부과기간)") or "").strip(), "rate_raw": (r.get("최종 판정결과(관세율)") or "").strip(),
                             "korea_targeted": (r.get("한국대상여부") or "").strip(), "matched_hs": matched})
        basis = f"규제시행국 코드 {iso}({country}) {len(by_country)}건 중 HS 컬럼이 분석 HS6 {'·'.join(hs6s)} 와 앞자리 일치하는 행"
        if country == "독일":
            basis += " · KOTRA 파일은 EU 공동 조치를 회원국 코드(DE 등)마다 수록하며 'EU' 코드는 없음 (확인함)"
        reg = item("import_regulation_records", "목적국 수입규제 기록", "확인됨" if hits else "검색 결과 없음", value=len(hits), unit="건",
                   as_of="2026-06-03", source=F_KOTRA.name, basis=basis,
                   note="규제 유형·대상 원산지·진행상황·기간은 파일 원문 그대로" if hits else "기록 없음이 규제 없음을 뜻하지 않음", rows=hits)

    idx, n_csl, latest = csl()
    iso_c = ISO2.get(country)
    custs = [cu for cu in ctx["customers"] if cu["iso2"] == iso_c or cu["country"] == country]
    crow, any_hit, searched = [], 0, 0
    for cu in custs:
        if not cu["name"]:
            crow.append({"customer_id": cu["id"], "name": "", "alias": cu["alias"], "status": "검색 불가", "note": "법인명 없음(별칭만 있음)", "matches": []})
            continue
        searched += 1
        m = idx.get(normalize_name(cu["name"]), [])
        note = "주소 미기재(명칭만 검색)" if not cu["address"] else None
        if m:
            any_hit += 1
            crow.append({"customer_id": cu["id"], "name": cu["name"], "alias": cu["alias"], "status": "확인됨", "note": note, "matches": m[:20]})
        else:
            crow.append({"customer_id": cu["id"], "name": cu["name"], "alias": cu["alias"], "status": "검색 결과 없음",
                         "note": (note + " · " if note else "") + "거래 가능 판정 아님", "matches": []})
    if not custs:
        cstat, cnote = "검색 불가", "이 목적국의 거래처가 거래처 시트에 없음"
    elif any_hit:
        cstat, cnote = "확인됨", "명단에서 명칭 일치가 발견됐다는 사실만 표시"
    elif searched:
        cstat, cnote = "검색 결과 없음", "검색 결과 없음(거래 가능 판정 아님)"
    else:
        cstat, cnote = "검색 불가", "검색 불가(법인명 없음)"
    csl_item = item("csl_search", "거래처 CSL 검색", cstat, value=any_hit, unit="일치 거래처 수", as_of=latest or None, source=F_CSL.name,
                    basis=f"거래처 시트의 목적국 거래처 법인명을 대문자·영숫자만 남겨 정규화한 뒤 CSL name·alt_names 와 정확 일치 비교 · CSL {n_csl:,}건 (최신 등재 {latest}, 파일 확보 2026-09-22)",
                    note=cnote, rows=crow)
    return [ctrl, reg, csl_item]


def build_market(c, country, ctx, cty_rows):
    items = [
        item("destination_imports", "목적국 수입시장 규모 (연간·월별)", "미확인", note="목적국 수입통계 API 연동 전"),
        item("korea_share", "한국산 수입점유율", "미확인", note="목적국 수입통계 API 연동 전"),
        item("growth_yoy", "성장률 · 전년 동기 대비", "미확인", note="필요한 기간의 수입통계 확보 후 계산"),
        item("growth_3m_yoy", "성장률 · 최근 3개월 전년 동기 대비", "미확인", note="필요한 기간의 수입통계 확보 후 계산"),
        item("cagr_3y", "성장률 · 3년 연평균(CAGR)", "미확인", note="필요한 기간의 수입통계 확보 후 계산"),
    ]
    api = pai.market_items(country, ISO2.get(country), ctx["hs6_list"]) if ctx["hs6_list"] else None
    code = TARIFF_FILE.get(country)
    tt = tariff_table(code) if code else None
    if api:
        items = api
    elif not tt:
        items.append(item("korea_exports_to_destination", "한국의 해당국 수출액 (수입국 통계 기준)", "자료 부족",
                          note=f"{country} 의 WTO 관세조치 파일 없음" + (f"(코드 {code})" if code else "")))
    else:
        table, meta, fname = tt
        rows = []
        for h6 in ctx["hs6_list"]:
            recs = table.get(h6, [])
            vals = {(d[:4], v) for d, _, v in recs if v is not None}
            for year, v in sorted(vals):
                rows.append({"hs6": h6, "year_dt_year": year, "imports_usd": v})
        latest_total = None
        if rows:
            last_year = max(r["year_dt_year"] for r in rows)
            latest_total = r2(sum(r["imports_usd"] for r in rows if r["year_dt_year"] == last_year))
        items.append(item("korea_exports_to_destination", "한국의 해당국 수출액 (수입국 통계 기준)", "확인됨" if rows else "자료 부족",
                          value=latest_total, unit="USD",
                          period=f"조치일 {min(d for h in ctx['hs6_list'] for d, _, _ in table.get(h, []))[:10]}~{max(d for h in ctx['hs6_list'] for d, _, _ in table.get(h, []))[:10]}" if rows else None,
                          as_of=max(d for h in ctx["hs6_list"] for d, _, _ in table.get(h, []))[:10] if rows else None, source=fname,
                          basis=f"{meta.get('reporter_name')} 의 대한국({meta.get('partner_name')}) 수입액 imports 열(USD, 최신 가용치). 조치일마다 같은 값이 반복되므로 연도별 변화는 이 파일로는 알 수 없음",
                          note="목적국 수입통계가 아니라 WTO 관세조치 파일의 참고 수입액 · 변화(추세)는 자료 부족", rows=rows))
    ws = wsts_regions()
    world = ws.get("Worldwide", {})
    last = max(world) if world else None
    wrows = []
    if last:
        months = [ym_add(last, -k) for k in range(12, -1, -1)]
        for region, s in ws.items():
            for m in months:
                v = s.get(m)
                prev = s.get((m[0] - 1, m[1]))
                wrows.append({"region": region, "month": ym_str(m), "value_thousand_usd": v,
                              "yoy_pct": r2((v / prev - 1) * 100, 1) if v is not None and prev else None})
    items.append(item("wsts", "WSTS 반도체 매출 (세계·권역별, 업황 참고)", "확인됨" if last else "자료 부족",
                      value=r2(world[last] / 1e6, 2) if last else None, unit="10억 달러 (세계, 최신 월)",
                      period=f"{ym_str(ym_add(last, -12))}~{ym_str(last)}" if last else None, as_of=f"{last[0]}-{last[1]:02d}" if last else None,
                      source=F_WSTS.name, basis="Monthly Data 시트의 Americas·Europe·Japan·Asia Pacific·Worldwide 행, 단위 1000 US$ → 최근 13개월과 전년동월비",
                      note="산업 매출이며 목적국 수입액·한국 수출액과 다른 정보", rows=wrows))
    yearly = defaultdict(float)
    for r in cty_rows:
        yearly[r["ym"][0]] += r["amount"]
    items.append(item("company_exports", f"회사 자료 · {country} 수출액 (연도별·월별)", "확인됨" if cty_rows else "자료 부족",
                      value=r2(sum(r["amount"] for r in cty_rows)), unit=ctx["currency_label"], period=ctx["period_label"],
                      as_of=ctx["as_of"], source=ctx["file_name"] + " · 수출실적 시트",
                      basis=f"유효 행(중복·취소·금액/통화/거래일/목적국 빈칸 제외) {len(cty_rows)}건의 금액 합 · 행이 없는 달은 결측(자료 없음)",
                      note="가상 데이터 · 회사 자체 수출 흐름 참고용 (목적국 수입액 아님)",
                      rows=monthly_sums(cty_rows, ctx["months"]), yearly=[{"year": y, "value_usd": r2(v)} for y, v in sorted(yearly.items())]))
    return items


def build_price(c, country, ctx, cty_rows):
    items = [item("trade_unit_price", "무역통계 kg당 단가", "미확인", note="무역통계 API 연동 전")]
    prows = []
    excluded_w = 0
    by = defaultdict(lambda: {"amount": 0.0, "weight": 0.0, "n": 0})
    for r in cty_rows:
        if r["product"] is None or ctx["product_map"].get(r["product"]) is None:
            continue
        if r["weight"] is None or r["weight"] <= 0:
            excluded_w += 1
            continue
        k = (r["product"], r["ym"][0])
        by[k]["amount"] += r["amount"]
        by[k]["weight"] += r["weight"]
        by[k]["n"] += 1
    for (pid, year), v in sorted(by.items()):
        p = ctx["product_map"][pid]
        prows.append({"product_id": pid, "product": p["name"], "hs6": p["analysis_hs6"] or None, "year": year,
                      "usd_per_kg": r2(v["amount"] / v["weight"]), "rows_used": v["n"]})
    items.append(item("company_unit_price", "회사 자료 · kg당 단가 (제품별·연도별)", "확인됨" if prows else "자료 부족",
                      value=r2(sum(v["amount"] for v in by.values()) / sum(v["weight"] for v in by.values())) if by else None, unit="USD/kg (전체)",
                      period=ctx["period_label"], as_of=ctx["as_of"], source=ctx["file_name"] + " · 수출실적 시트",
                      basis=f"금액 합 ÷ 순중량(kg) 합 (두 값이 모두 있는 행만) · 순중량 빈칸으로 제외 {excluded_w}행 · 제품ID 빈칸 행 제외",
                      note="가상 데이터 · 통계 단가는 실제 판매가가 아님", rows=prows))
    api = pai.price_items(country, ISO2.get(country), ctx["hs6_list"]) if ctx["hs6_list"] else None
    if api:
        items = [x for x in items if x["key"] != "trade_unit_price"]
        items = [next(a for a in api if a["key"] == "trade_unit_price")] + items + [a for a in api if a["key"] == "baseline_unit_price"]
    else:
        items.append(item("baseline_unit_price", "기준 대비 단가 (한국 전체 수출단가 대비)", "자료 부족", note="같은 품목·기간·출처의 한국 전체 수출단가 자료 미확보"))
    code = TARIFF_FILE.get(country)
    tt = tariff_table(code) if code else None
    if not tt:
        items.append(item("tariff_reference", "관세 참고치 (WTO, HS6·조치일별)", "자료 부족", note=f"{country} 의 WTO 관세조치 파일 없음" + (f"(코드 {code})" if code else "")))
    elif not ctx["hs6_list"]:
        items.append(item("tariff_reference", "관세 참고치 (WTO, HS6·조치일별)", "검색 불가", source=tt[2], note="분석 HS6 가 있는 제품이 없음"))
    else:
        table, meta, fname = tt
        trows, latest = [], {}
        for h6 in ctx["hs6_list"]:
            hist = [(d, b) for d, b, _ in table.get(h6, []) if b is not None]
            for d, b in hist:
                trows.append({"hs6": h6, "year_dt": d[:10], "best_avlbl_pct": b})
            if hist:
                latest[h6] = hist[-1]
        items.append(item("tariff_reference", "관세 참고치 (WTO, HS6·조치일별)", "확인됨" if trows else "자료 부족",
                          value={h: b for h, (_, b) in latest.items()} or None, unit="% (HS6별 최신 조치)",
                          period=f"{min(r['year_dt'] for r in trows)}~{max(r['year_dt'] for r in trows)}" if trows else None,
                          as_of=max(r["year_dt"] for r in trows) if trows else None, source=fname,
                          basis=f"{meta.get('reporter_name')} → 대한국 best_avlbl (조치 후 적용 예상 관세, HS6 단순평균) 를 year_dt 순으로" + (" · 독일은 EU(U918) 파일 사용" if country == "독일" else ""),
                          note="참고치이며 확정 적용세율 아님", rows=trows))
    stab = (processed_json("stability") or {}).get("detail", {})
    ccy = ctx["currency"]
    if ccy == "미확인":
        items.append(item("fx_reference", "참고환율 (결제통화 → 원화, 월평균)", "미확인", note="기업정보의 '금액 통화' 빈칸 → 결제통화 불명"))
    else:
        pc = (stab.get("per_currency") or {}).get(ccy)
        if pc and pc.get("state") == "ok" and pc.get("monthly"):
            m = pc["monthly"]
            lx = pai.fx_latest(ccy)
            items.append(item("fx_reference", f"참고환율 (원/{ccy})", "확인됨", value=lx["value"] if lx else m[-1]["value"], unit=f"KRW/{ccy}",
                              period=f"{m[0]['month']}~{m[-1]['month']}", as_of=lx["date"] if lx else m[-1]["month"],
                              source=(lx["source"] + " · 추세: " if lx else "") + str(pc.get("source")),
                              basis=(f"값: {lx['source']} {lx['date']} · " if lx else "") + f"추세: 연준 H.10 일별 환율 → {pc.get('desc', '')} 교차환율 → 월평균",
                              note="참고환율이며 회사 적용환율과 다를 수 있음", rows=m, monthly_last=m[-1]["value"]))
        else:
            items.append(item("fx_reference", f"참고환율 (원/{ccy})", "자료 부족", note=f"{ccy} 환율 시계열 없음 (H.10 미수록)"))
    pj = (processed_json("price") or {}).get("detail", {})
    epi = pj.get("export_price_index")
    if epi:
        items.append(item("price_index", f"수출입물가지수 · {epi.get('row_label')} (수출, 잠정)", "확인됨", value=epi.get("latest_preliminary"),
                          unit=epi.get("base"), period=" / ".join(epi.get("periods") or []), as_of=epi.get("period"), source=epi.get("file"),
                          basis=f"시트 '{epi.get('sheet')}' 의 실제 수록 분류 행 · 전월비 {epi.get('mom_pct')}% · 전년동월비 {epi.get('yoy_pct')}%",
                          note="반도체 개별 제품 가격 아님 (파일에 반도체 세부 지수 없음)",
                          rows=[{"period": epi.get("periods", ["", ""])[0], "value": epi.get("prev")}, {"period": epi.get("periods", ["", ""])[1], "value": epi.get("latest_preliminary")}],
                          mom_pct=epi.get("mom_pct"), yoy_pct=epi.get("yoy_pct")))
    else:
        items.append(item("price_index", "수출입물가지수", "자료 부족", note="processed/price.json 에 수출물가지수 없음"))
    ft = freight_tables()
    frows = []
    for mode, tab in ft.items():
        for route in FREIGHT_ROUTES.get(country, []):
            s = tab["routes"].get(route)
            if not s:
                continue
            y, m, v = s[-1]
            prev = next((x[2] for x in s if (x[0], x[1]) == ym_add((y, m), -1)), None)
            yoy = next((x[2] for x in s if (x[0], x[1]) == (y - 1, m)), None)
            frows.append({"mode": mode, "route": route, "unit": tab["unit"], "month": f"{y}-{m:02d}", "value": v,
                          "mom_pct": r2((v / prev - 1) * 100, 1) if prev else None, "yoy_pct": r2((v / yoy - 1) * 100, 1) if yoy else None,
                          "series": [{"month": f"{a}-{b:02d}", "value": c_} for a, b, c_ in s]})
    items.append(item("freight_reference", "운송비 참고 (해상수출·해상수입·항공수입 구분)", "확인됨" if frows else "자료 부족",
                      value=len(frows), unit="수록 항로 수", period="2025-01~2026-08", as_of="2026-08-31", source=F_FREIGHT.name,
                      basis="hwpx 본문의 '해상 수출/해상 수입/항공 수입 운송비용 현황' 월별 표에서 목적국 항로 행을 읽음 (2TEU 당 천원, 항공은 원/kg)",
                      note="항공수입 값은 한국발 항공수출 견적이 아님 · 수록 항로의 평균 운송비 참고" if frows else f"{country} 항로는 관세청 자료에 미수록", rows=frows))
    return items


def build_logistics(c, country, ctx, cty_rows):
    """물류 시트(연결된 유효 실적만): 조회 조건 + v0.3 에서 추가된 예정·실제 도착일·운임 기반 항목. 공개자료(항공편·운항·선박)는 API 연동 전 미확인."""
    ids = {r["id"] for r in cty_rows}
    lrows = [l for l in ctx["lparsed"] if l["rid"] in ids]
    has_cols = ctx["logistics_has_cols"]
    grp = defaultdict(int)
    blanks = {"운송수단 빈칸": 0, "도착지코드 빈칸": 0, "선적일 빈칸": 0}
    dates = []
    for l in lrows:
        blanks["운송수단 빈칸"] += (not l["mode"])
        blanks["도착지코드 빈칸"] += (not l["d"])
        blanks["선적일 빈칸"] += (l["ship"] is None)
        if l["ship"]:
            dates.append(l["ship"])
        grp[(l["mode"] or "(빈칸)", l["o"] or "(빈칸)", l["d"] or "(빈칸)")] += 1
    qrows = [{"mode": k[0], "origin_code": k[1], "destination_code": k[2], "shipments": v} for k, v in sorted(grp.items(), key=lambda x: -x[1])]
    period = f"{min(dates).isoformat()}~{max(dates).isoformat()}" if dates else None
    src = ctx["file_name"] + " · 물류 시트"
    months = ctx["months"]
    present = {r["ym"] for r in cty_rows}
    # 월별 선적 건수 (운송수단별). 거래가 없는 달은 자료 없음(None), 거래는 있는데 물류 행이 없으면 실제 0
    mrows = []
    for m in months:
        if m not in present:
            mrows.append({"month": ym_str(m), "air": None, "sea": None, "other": None, "total": None})
            continue
        ml = [l for l in lrows if l["ym"] == m]
        air, sea = sum(1 for l in ml if l["mode"] == "항공"), sum(1 for l in ml if l["mode"] == "해상")
        mrows.append({"month": ym_str(m), "air": air, "sea": sea, "other": len(ml) - air - sea, "total": len(ml)})
    # 납기 준수율: 예정·실제 도착일이 모두 있고 날짜 역전이 아닌 행 중 실제 ≤ 예정
    tracked = [l for l in lrows if l["eta"] and l["ata"] and not l["date_err"]]
    ontime_n = sum(1 for l in tracked if l["ata"] <= l["eta"])
    orows = []
    for m in months:
        mt = [l for l in tracked if l["ym"] == m]
        on = sum(1 for l in mt if l["ata"] <= l["eta"])
        orows.append({"month": ym_str(m), "tracked": len(mt) if m in present else None, "ontime": on if m in present else None,
                      "rate_pct": r2(on / len(mt) * 100, 1) if mt else None})
    oblanks = {"예정도착일 빈칸": sum(1 for l in lrows if l["eta"] is None), "실제도착일 빈칸": sum(1 for l in lrows if l["ata"] is None),
               "날짜 역전 오류": sum(1 for l in lrows if l["date_err"])}
    # 리드타임 (실제 도착일 − 선적일)
    lt_rows = [l for l in lrows if l["ship"] and l["ata"] and not l["date_err"]]

    def lt_stats(sub, mode):
        days = [(l["ata"] - l["ship"]).days for l in sub]
        planned = [(l["eta"] - l["ship"]).days for l in sub if l["eta"]]
        return {"mode": mode, "shipments": len(days), "avg_days": r2(sum(days) / len(days), 1), "min_days": min(days), "max_days": max(days),
                "planned_avg_days": r2(sum(planned) / len(planned), 1) if planned else None}
    ltrows = [lt_stats([l for l in lt_rows if l["mode"] == md], md) for md in ("항공", "해상") if any(l["mode"] == md for l in lt_rows)]
    lt_all = r2(sum((l["ata"] - l["ship"]).days for l in lt_rows) / len(lt_rows), 1) if lt_rows else None
    # 운송비 비중 (운임 합 ÷ 연결된 수출금액 합)
    fr_rows = [l for l in lrows if l["freight"] is not None and l["amount"] and l["amount"] > 0]

    def fr_stats(sub, mode):
        f, a = sum(l["freight"] for l in sub), sum(l["amount"] for l in sub)
        w = sum(l["weight"] for l in sub if l["weight"])
        return {"mode": mode, "shipments": len(sub), "freight_usd": r2(f), "amount_usd": r2(a), "ratio_pct": r2(f / a * 100, 3) if a else None,
                "usd_per_kg": r2(f / w, 2) if w else None}
    frrows = [fr_stats([l for l in fr_rows if l["mode"] == md], md) for md in ("항공", "해상") if any(l["mode"] == md for l in fr_rows)]
    fr_all = r2(sum(l["freight"] for l in fr_rows) / sum(l["amount"] for l in fr_rows) * 100, 3) if fr_rows else None

    def status_of(l):
        if l["date_err"]:
            return "날짜 오류"
        if l["eta"] is None:
            return "예정 미기재"
        if l["ata"] is None:
            return "도착 미기재"
        late = (l["ata"] - l["eta"]).days
        return "정시" if late <= 0 else f"지연 {late}일"
    recent = sorted([l for l in lrows if l["ship"]], key=lambda l: (l["ship"], l["id"]))[-10:][::-1]
    rrows = [{"id": l["id"], "mode": l["mode"] or "(빈칸)", "origin_code": l["o"] or "(빈칸)", "destination_code": l["d"] or "(빈칸)",
              "ship_date": l["ship"].isoformat(), "eta": l["eta"].isoformat() if l["eta"] else None, "ata": l["ata"].isoformat() if l["ata"] else None,
              "status": status_of(l)} for l in recent]
    note_api = "인천공항·항만 API 연동 전 · 조회 조건은 'query_conditions' 항목 참조"
    common = dict(period=period, as_of=ctx["as_of"], source=src)
    items = pai.logistics_items(country, ISO2.get(country)) or [
        item("cargo_flights", "인천공항 화물편 일정", "미확인", note=note_api),
        item("flight_counts", "운항 횟수 (국가별 월간 출발·도착편)", "미확인", note=note_api),
        item("vessel_records", "선박 입출항 기록", "미확인", note=note_api),
    ]
    if not has_cols:
        items += [item("delivery_ontime", "회사 자료 · 납기 준수율 (실제 ≤ 예정 도착)", "자료 부족", note="물류 시트에 예정·실제 도착일 열 없음"),
                  item("lead_time", "회사 자료 · 평균 리드타임 (선적일 → 실제 도착일)", "자료 부족", note="물류 시트에 실제 도착일 열 없음"),
                  item("freight_ratio", "회사 자료 · 운송비 비중 (운임 ÷ 수출금액)", "자료 부족", note="물류 시트에 운임 열 없음")]
    else:
        items += [
            item("delivery_ontime", "회사 자료 · 납기 준수율 (실제 ≤ 예정 도착)", "확인됨" if tracked else "자료 부족",
                 value=r2(ontime_n / len(tracked) * 100, 1) if tracked else None, unit="%", **common,
                 basis=f"예정·실제 도착일이 모두 있는 {len(tracked)}건 중 실제도착일 ≤ 예정도착일 {ontime_n}건 · 날짜 역전 행 제외",
                 note="가상 데이터 · 과거 기록이며 배송시간·운송 가능 여부를 확정하지 않음", rows=orows, blanks=oblanks, tracked=len(tracked), ontime=ontime_n),
            item("lead_time", "회사 자료 · 평균 리드타임 (선적일 → 실제 도착일)", "확인됨" if lt_rows else "자료 부족", value=lt_all, unit="일", **common,
                 basis="실제도착일 − 선적일(일)의 평균·최소·최대를 운송수단별로 · 계획 리드타임 = 예정도착일 − 선적일", note="가상 데이터 · 과거 기록이며 배송시간 예측이 아님", rows=ltrows),
            item("freight_ratio", "회사 자료 · 운송비 비중 (운임 ÷ 수출금액)", "확인됨" if fr_rows else "자료 부족", value=fr_all, unit="%", **common,
                 basis=f"운임이 있는 {len(fr_rows)}건의 운임 합 ÷ 연결된 수출실적 금액 합 × 100 · 운송수단별 kg당 운임은 참고", note="가상 데이터 · 운임은 가정값이며 견적이 아님",
                 rows=frrows, blanks={"운임 빈칸": sum(1 for l in lrows if l["freight"] is None)}),
        ]
    items += [
        item("shipments_monthly", "회사 자료 · 월별 선적 건수 (운송수단별)", "확인됨" if lrows else "자료 부족", value=len(lrows), unit="건", **common,
             basis="유효 수출실적과 실적ID 로 연결된 물류 행을 거래월·운송수단별로 센 것 · 거래가 없는 달은 자료 없음", note="가상 데이터", rows=mrows),
        item("recent_shipments", "회사 자료 · 최근 선적 기록", "확인됨" if rrows else "자료 부족", value=len(rrows), unit="건", **common,
             basis="선적일 기준 최근 10건 · 상태는 실제 도착일과 예정 도착일 비교", note="직항 여부·전체 배송시간·운송 가능 여부를 확정하지 않음", rows=rrows),
        item("query_conditions", "조회 조건(회사 자료)", "확인됨" if qrows else "자료 부족", value=len(lrows), unit="선적 건수", **common,
             basis="유효 수출실적과 실적ID 로 연결된 물류 행을 운송수단·출발지코드·도착지코드별로 센 것 (공항 IATA · 항만 UN/LOCODE)",
             note="직항 여부·전체 배송시간·운송 가능 여부를 확정하지 않음", rows=qrows, blanks=blanks),
    ]
    return items


def build_stability(c, country, ctx, cty_rows):
    items = (pai.stability_items(country, ISO2.get(country), ctx["hs6_list"]) if ctx["hs6_list"] else None) or [
        item("destination_monthly_imports", "목적국 월별 수입금액·전월비", "미확인", note="목적국 수입통계 API 연동 전"),
        item("cv", "변동계수 CV (목적국 수입액)", "미확인", note="목적국 수입통계 API 연동 전"),
        item("sharp_drops", "급감 이력 (전월비 −20% 이하)", "미확인", note="목적국 수입통계 API 연동 전"),
    ]
    ms = monthly_sums(cty_rows, ctx["months"])
    vals = [x["value_usd"] for x in ms]
    present = [v for v in vals if v is not None]
    drops, comparable = [], 0
    for i in range(1, len(ms)):
        a, b = vals[i - 1], vals[i]
        if a is None or b is None:
            ms[i]["mom_pct"] = None
            continue
        comparable += 1
        mom = (b / a - 1) * 100 if a > 0 else None
        ms[i]["mom_pct"] = r2(mom, 1)
        if mom is not None and mom <= -20:
            drops.append({"month": ms[i]["month"], "mom_pct": r2(mom, 1), "value_usd": b})
    ms[0]["mom_pct"] = None
    cv = (statistics.pstdev(present) / statistics.mean(present) * 100) if len(present) >= 2 and statistics.mean(present) > 0 else None
    items.append(item("company_export_volatility", f"회사 자료 · {country} 월별 수출액 변동(보조)", "확인됨" if len(present) >= 2 else "자료 부족",
                      value=r2(cv, 1), unit="CV %", period=ctx["period_label"], as_of=ctx["as_of"], source=ctx["file_name"] + " · 수출실적 시트",
                      basis=f"자료 있는 달 {len(present)}개의 월별 합계 CV(모표준편차÷평균) · 전월비는 두 달 모두 자료가 있을 때만 계산({comparable}회) · 결측 달은 0 이 아니라 제외",
                      note="가상 데이터 · 과거 변동이며 미래 손실·수출 실패 확률이 아님", rows=ms,
                      drops=drops, drop_count=len(drops), comparable_months=comparable,
                      drop_rate_pct=r2(len(drops) / comparable * 100, 1) if comparable else None,
                      missing_months=[x["month"] for x in ms if x["value_usd"] is None]))
    stab = (processed_json("stability") or {}).get("detail", {})
    pc = (stab.get("per_country") or {}).get(country)
    cur = (stab.get("per_currency") or {}).get(pc["ccy"]) if pc and pc.get("ccy") else None
    if pc and pc.get("state") == "ok" and cur:
        items.append(item("fx_volatility", f"결제통화 환율 변동성 (원/{pc['ccy']}, 보조)", "확인됨", value=cur.get("mean_abs_mom_pct"), unit="전월비 절대값 평균 %",
                          period=cur.get("period"), as_of=pc.get("as_of"), source=pc.get("source"),
                          basis=f"stability_method v{stab.get('method_version', '1.0') if isinstance(stab, dict) else '1.0'}: 월평균 환율의 전월비 절대값 평균 · 과거 {stab.get('history_years')}년 롤링 분포 대비 등급 {cur.get('grading', {}).get('grade')} · CV {cur.get('coefficient_of_variation_pct')}%",
                          note=pc.get("headline"), rows=cur.get("monthly"), grade=cur.get("grading", {}).get("grade"), high=cur.get("high"), low=cur.get("low")))
    else:
        items.append(item("fx_volatility", "결제통화 환율 변동성 (보조)", "자료 부족", source=(pc or {}).get("source"),
                          note=(pc or {}).get("headline") or f"{country} 결제통화 환율 시계열 없음"))
    ws = wsts_regions()
    wrows = []
    for region, s in ws.items():
        keys = sorted(s)[-13:]
        moms = []
        for i in range(1, len(keys)):
            a, b = s[keys[i - 1]], s[keys[i]]
            if a:
                moms.append((b / a - 1) * 100)
        wrows.append({"region": region, "period": f"{ym_str(keys[0])}~{ym_str(keys[-1])}" if keys else None,
                      "mean_abs_mom_pct": r2(sum(abs(x) for x in moms) / len(moms), 1) if moms else None,
                      "drops_20pct": sum(1 for x in moms if x <= -20), "comparable_months": len(moms)})
    world = next((w for w in wrows if w["region"] == "Worldwide"), None)
    items.append(item("wsts_volatility", "WSTS 세계·권역별 매출 변동(보조)", "확인됨" if world else "자료 부족", value=world["mean_abs_mom_pct"] if world else None,
                      unit="전월비 절대값 평균 % (세계)", period=world["period"] if world else None, source=F_WSTS.name,
                      basis="최근 13개월 월별 매출의 전월비 절대값 평균과 −20% 이하 급감 횟수 (권역별)", note="산업 매출 변동이며 목적국 수입 변동이 아님", rows=wrows))
    return items




# ---------------------------------------------------------------- 점수 (demo_scoring v0.2 — 시연용, 확정 채점 기준 아님)
# v0.1 산식(junhee/rules/demo_scoring.md)을 handoff-v1 파일에 맞춰 보정한다. 보정 내용은 문서 'v0.2' 절과 같다.
SCORE_RULE = "demo_scoring v0.3 (2026-09-26) — v0.2 + 물류 점수(납기 준수율·운송비 비중, 물류 시트 v0.3 열), 가상 데이터 · 시연용"
WEIGHTS = {"market": 35, "price": 30, "logistics": 20, "stability": 15}  # workspace.js defaults 와 동일
OVERALL_MISSING = "renormalize"  # 자료 부족 요인은 종합에서 빼고 나머지 가중치를 재정규화한다 ("insufficient" 로 바꾸면 v0.1 처럼 종합도 자료 부족)
SERIES_MONTHS = 6
TRAIL = 12


def clip(x):
    return max(0.0, min(100.0, x))


def r1(x):
    return None if x is None else round(x + 1e-9, 1)


def _month_end_iso(ym):
    import calendar
    return date(ym[0], ym[1], calendar.monthrange(ym[0], ym[1])[1]).isoformat()


def _wsts_yoy_at(ym):
    """M 이전(포함) 가장 최근 WSTS Worldwide 월의 전년동월비(%). 3개월 넘게 오래되면 None."""
    s = wsts_regions().get("Worldwide", {})
    cands = [k for k in s if k <= ym]
    if not cands:
        return None, None
    k = max(cands)
    if (ym[0] * 12 + ym[1]) - (k[0] * 12 + k[1]) > 3:
        return None, k
    prev = s.get((k[0] - 1, k[1]))
    if not prev:
        return None, k
    return (s[k] / prev - 1) * 100, k


def _tariff_at(code, hs6, ym):
    tt = tariff_table(code) if code else None
    if not tt:
        return None
    rows = [(d, b) for d, b, _ in tt[0].get(hs6, []) if b is not None and d[:10] <= _month_end_iso(ym)]
    return max(rows)[1] if rows else None


def _insufficient(note):
    return {"score": None, "state": "insufficient", "note": note}


def _score_regulation(win, country, ctx, cands, kotra_hits, csl_hits):
    total = sum(r["amount"] for r in win)
    share = (sum(r["amount"] for r in win if r["product"] in cands) / total) if total else 0.0
    p1, p2, p3 = (30 if kotra_hits else 0), (40 if csl_hits else 0), 20 * share
    return {"score": r1(clip(100 - p1 - p2 - p3)), "state": "ok", "needs_review": (p1 + p2 + p3) > 0,
            "note": f"수입규제 {'해당 ' + str(kotra_hits) + '건' if kotra_hits else '기록 없음'} · CSL {'일치 ' + str(csl_hits) + '곳' if csl_hits else '일치 없음'} · 통제번호 후보 품목 비중 {share * 100:.0f}% (검토 필요, 해당 확정 아님)",
            "inputs": {"P1_kotra": p1, "P2_csl": p2, "P3_hsk": r1(p3), "hsk_candidate_share": round(share, 4)}}


def _score_market(rows, ym):
    yoy, wm = _wsts_yoy_at(ym)
    if yoy is None:
        return _insufficient(f"{ym_str(ym)} 기준 3개월 이내 WSTS 출하액 없음")
    recent = sum(r["amount"] for r in rows if ym_add(ym, -2) <= r["ym"] <= ym)
    prev = sum(r["amount"] for r in rows if ym_add(ym, -5) <= r["ym"] <= ym_add(ym, -3))
    if prev <= 0:
        return _insufficient("직전 3개월 수출실적이 없어 증가율을 계산할 수 없음")
    growth = (recent / prev - 1) * 100
    f, g = clip(50 + yoy / 2), clip(50 + growth)
    return {"score": r1(0.5 * f + 0.5 * g), "state": "ok",
            "note": f"세계 출하 전년동월비 {yoy:+.1f}%({ym_str(wm)}) · 최근 3개월 수출액 {growth:+.1f}%",
            "inputs": {"wsts_yoy_pct": round(yoy, 2), "wsts_month": ym_str(wm), "company_growth_3m_pct": round(growth, 2), "f": r1(f), "g": r1(g)}}


def _score_price(win, country, ctx, ym):
    code = TARIFF_FILE.get(country)
    if not code or not tariff_table(code):
        return _insufficient(f"{country} 의 WTO 관세조치 파일 없음")
    by_hs = defaultdict(float)
    for r in win:
        p = ctx["product_map"].get(r["product"]) if r["product"] else None
        if p and p["analysis_hs6"]:
            by_hs[p["analysis_hs6"]] += r["amount"]
    if not by_hs:
        return _insufficient("HS6 가 있는 제품의 수출실적 없음")
    rates = {h: _tariff_at(code, h, ym) for h in by_hs}
    if any(v is None for v in rates.values()):
        return _insufficient("관세 참고치가 없는 HS6 있음: " + ", ".join(h for h, v in rates.items() if v is None))
    tot = sum(by_hs.values())
    r = sum(rates[h] * by_hs[h] / tot for h in by_hs)
    t = clip(100 - 2 * r)
    # v0.2 보정: handoff-v1 파일에는 원가·비용 시트가 없어 마진 점수(m)를 계산할 수 없다 → 관세 항목(t)만 반영
    return {"score": r1(t), "state": "ok", "note": f"가중 관세 참고율 {r:.2f}% · 마진 자료 없음(원가·비용 시트 미포함) → 관세 항목만 반영",
            "inputs": {"weighted_tariff_pct": round(r, 3), "t": r1(t), "m": None, "tariff_by_hs6": {h: rates[h] for h in by_hs}}}


def _score_logistics(lwin):
    """v0.3: 0.7 × 납기 준수율 + 0.3 × c, c = clip(100 − 10 × 운송비 비중%). 추적 창 = 점수 창(12개월) 안의 연결된 물류 행."""
    tracked = [l for l in lwin if l["eta"] and l["ata"] and not l["date_err"]]
    if len(tracked) < 5:
        return _insufficient(f"추적 창 안에 예정·실제 도착일이 모두 있는 물류 행 {len(tracked)}건 (5건 이상 필요)")
    ontime_n = sum(1 for l in tracked if l["ata"] <= l["eta"])
    ontime = ontime_n / len(tracked) * 100
    fr_rows = [l for l in lwin if l["freight"] is not None and l["amount"] and l["amount"] > 0]
    if not fr_rows:
        return _insufficient("운임과 연결된 수출금액이 있는 물류 행 없음")
    f, a = sum(l["freight"] for l in fr_rows), sum(l["amount"] for l in fr_rows)
    fr = f / a * 100
    c = clip(100 - 10 * fr)
    return {"score": r1(0.7 * ontime + 0.3 * c), "state": "ok",
            "note": f"납기 준수율 {ontime:.1f}% ({ontime_n}/{len(tracked)}건) · 운송비 비중 {fr:.2f}% → c {c:.1f} (가상 데이터, 배송시간 확정 아님)",
            "inputs": {"ontime_pct": round(ontime, 2), "tracked_rows": len(tracked), "ontime_rows": ontime_n, "freight_ratio_pct": round(fr, 3),
                       "freight_usd": round(f, 2), "linked_amount_usd": round(a, 2), "c": r1(c)}}


def _score_stability(win, ym):
    totals = defaultdict(float)
    for r in win:
        totals[r["ym"]] += r["amount"]
    if len(totals) < 6:
        return _insufficient(f"최근 12개월 중 거래가 있는 달이 {len(totals)}개 (6개 이상 필요)")
    rows_c = [r for r in win if r["customer"]]
    tot = sum(r["amount"] for r in rows_c)
    if tot <= 0:
        return _insufficient("거래처가 연결된 수출실적 없음")
    by_c = defaultdict(float)
    for r in rows_c:
        by_c[r["customer"]] += r["amount"]
    hhi = sum((v / tot) ** 2 for v in by_c.values())
    conc = clip((1 - hhi) * 100)
    vals = list(totals.values())
    cv = statistics.pstdev(vals) / statistics.mean(vals) * 100
    cvs = clip(100 - 2 * cv)
    return {"score": r1(0.5 * conc + 0.5 * cvs), "state": "ok",
            "note": f"거래처 집중도 HHI {hhi:.2f} · 월별 수출액 변동계수 {cv:.0f}% (목적국 내 거래처 기준, 국가위험 아님)",
            "inputs": {"hhi_customer": round(hhi, 4), "conc": r1(conc), "cv_pct": round(cv, 2), "cv_score": r1(cvs), "months_with_sales": len(totals)}}


def _overall(factors):
    """가중 평균. OVERALL_MISSING='renormalize' 면 자료 부족 요인을 빼고 가중치를 재정규화한다."""
    ok = {k: factors[k]["score"] for k in WEIGHTS if factors[k]["state"] == "ok"}
    missing = [k for k in WEIGHTS if k not in ok]
    if not ok or (missing and OVERALL_MISSING != "renormalize"):
        return None, missing
    return sum(WEIGHTS[k] * ok[k] for k in ok) / sum(WEIGHTS[k] for k in ok), missing


FACTOR_KO = {"regulation": "규제 관문", "market": "시장성", "price": "가격", "logistics": "물류", "stability": "안정성"}


def score_country(country, cty_rows, ctx, as_of, cands, kotra_hits, csl_hits, cty_log=()):
    months = [ym_add(as_of, -k) for k in range(SERIES_MONTHS, -1, -1)]  # as_of-6 … as_of (전월 대비용 1개 더)
    per = {}
    for m in months:
        win = [r for r in cty_rows if ym_add(m, -(TRAIL - 1)) <= r["ym"] <= m]
        per[m] = {
            "regulation": _score_regulation(win, country, ctx, cands, kotra_hits, csl_hits),
            "market": _score_market(cty_rows, m),
            "price": _score_price(win, country, ctx, m),
            "logistics": _score_logistics([l for l in cty_log if ym_add(m, -(TRAIL - 1)) <= l["ym"] <= m]),
            "stability": _score_stability(win, m),
        }
    factors = []
    for key in ("regulation", "market", "price", "logistics", "stability"):
        cur, prev = per[as_of][key], per[ym_add(as_of, -1)][key]
        f = {"key": key, "label_ko": FACTOR_KO[key], "weight": None if key == "regulation" else WEIGHTS[key],
             "score": cur["score"], "state": cur["state"],
             "delta": r1(cur["score"] - prev["score"]) if cur["state"] == "ok" and prev["state"] == "ok" else None,
             "series": [per[m][key]["score"] for m in months[1:]], "series_months": [ym_str(m) for m in months[1:]],
             "note": cur["note"], "inputs": cur.get("inputs", {})}
        if key == "regulation":
            f["gate"] = True
            f["needs_review"] = bool(cur.get("needs_review"))
        factors.append(f)
    ov, missing = _overall(per[as_of])
    ov_prev, _ = _overall(per[ym_add(as_of, -1)])
    series = [_overall(per[m])[0] for m in months[1:]]
    used = [k for k in WEIGHTS if k not in missing]
    overall = {"score": r1(ov), "state": "ok" if ov is not None else "insufficient",
               "delta_vs_prev_month": r1(ov - ov_prev) if ov is not None and ov_prev is not None else None,
               "series": [r1(v) for v in series], "series_months": [ym_str(m) for m in months[1:]],
               "weights": WEIGHTS, "weights_used": {k: WEIGHTS[k] for k in used}, "excluded": missing,
               "regulation_gate": "excluded", "needs_regulation_review": bool(per[as_of]["regulation"].get("needs_review")),
               "note": ("자료 부족 요인 제외 후 재정규화: " + ", ".join(FACTOR_KO[k] for k in missing)) if missing and ov is not None else ("자료 부족 요인이 있어 종합 없음" if ov is None else "4개 요인 가중 평균")}
    oks = [f for f in factors if f["state"] == "ok" and f["key"] != "regulation"]
    best = max(oks, key=lambda f: f["score"]) if oks else None
    worst = min(oks, key=lambda f: f["score"]) if oks else None
    hl = ""
    if best and worst and best is not worst:
        hl = f"{best['label_ko']}({best['score']:.0f}점)이 가장 강하고 {worst['label_ko']}({worst['score']:.0f}점)이 가장 약합니다. "
    if overall["delta_vs_prev_month"] is not None:
        d = overall["delta_vs_prev_month"]
        hl += f"종합 점수는 전월 대비 {d:+.1f}점 {'상승' if d > 0 else '하락' if d < 0 else '변화 없음'}했습니다. "
    if missing:
        hl += "자료 부족으로 종합에서 제외한 요인: " + "·".join(FACTOR_KO[k] for k in missing) + ". "
    if overall["needs_regulation_review"]:
        hl += "규제 관문은 통제번호 후보 품목이 있어 원문 대조 검토가 필요합니다(해당 확정 아님). "
    hl += "가상 데이터에 시연용 산식을 적용한 결과이며 실제 판정이 아닙니다."
    return {"overall": overall, "factors": factors, "highlights": hl}


# ---------------------------------------------------------------- 회사 평가
def build_company(path):
    data = load_company(path)
    info = data["info"]
    name = str(info.get("company") or "").strip()
    cid = COMPANY_IDS.get(name)
    if not cid:
        raise RuntimeError(f"{path.name}: 등록되지 않은 회사명 '{name}'")
    products = []
    for p in data["products"]:
        hsk = "" if blank(p.get("입력HSK")) else str(p.get("입력HSK")).strip()
        hs6 = "" if blank(p.get("HS코드")) else str(p.get("HS코드")).strip()[:6]
        products.append({"id": str(p.get("제품ID")).strip(), "name": str(p.get("모델명") or "").strip(), "family": str(p.get("제품군") or "").strip(),
                         "input_hsk": hsk, "analysis_hs6": hs6, "hs_status": "확인됨" if hs6 and hsk else "미확인",
                         "note": None if blank(p.get("분류비고")) else str(p.get("분류비고")).strip()})
    product_map = {p["id"]: p for p in products}
    customers = [{"id": str(cu.get("거래처ID")).strip(), "name": "" if blank(cu.get("법인명")) else str(cu.get("법인명")).strip(),
                  "alias": "" if blank(cu.get("별칭")) else str(cu.get("별칭")).strip(), "address": "" if blank(cu.get("주소")) else str(cu.get("주소")).strip(),
                  "country": "" if blank(cu.get("국가")) else str(cu.get("국가")).strip(), "iso2": "" if blank(cu.get("국가코드")) else str(cu.get("국가코드")).strip(),
                  "relation": "" if blank(cu.get("최종사용자관계")) else str(cu.get("최종사용자관계")).strip()} for cu in data["customers"]]
    rows, valid, cancelled, quality = process_actuals(data["actuals"])
    if not valid:
        raise RuntimeError(f"{path.name}: 유효한 수출실적 없음")
    all_yms = {r["ym"] for r in rows if r["ym"]}
    period = (min(all_yms), max(all_yms))
    months = ym_range(*period)
    present_months = {r["ym"] for r in rows if r["ym"]}
    quality["missing_months"] = [ym_str(m) for m in months if m not in present_months]
    cur_raw = str(info.get("금액 통화") or "").strip()
    currency = cur_raw.split()[0] if cur_raw else "미확인"
    by_ctry = defaultdict(float)
    for r in valid:
        by_ctry[r["country"]] += r["amount"]
    total = sum(by_ctry.values())
    iso_of = {}
    for r in valid:
        if r["iso2"]:
            iso_of.setdefault(r["country"], r["iso2"])
    countries = [{"name": k, "iso2": iso_of.get(k) or ISO2.get(k), "export_share": r2(v / total, 4), "amount_usd": r2(v)}
                 for k, v in sorted(by_ctry.items(), key=lambda x: -x[1])]
    by_hs = defaultdict(float)
    for r in valid:
        p = product_map.get(r["product"]) if r["product"] else None
        if p and p["analysis_hs6"]:
            by_hs[p["analysis_hs6"]] += r["amount"]
    hs6_list = sorted({p["analysis_hs6"] for p in products if p["analysis_hs6"]})
    hs_unknown = [p["id"] for p in products if not p["analysis_hs6"]]
    rows_hs_unknown = sum(1 for r in valid if r["product"] and product_map.get(r["product"]) and not product_map[r["product"]]["analysis_hs6"])
    ctx = {
        "file_name": path.name, "products": products, "product_map": product_map, "customers": customers, "logistics": data["logistics"],
        "hs6_list": hs6_list, "months": months, "period_label": f"{ym_str(period[0])}~{ym_str(period[1])}",
        "as_of": date(period[1][0], period[1][1], 1).replace(day=28).isoformat()[:7], "currency": currency,
        "currency_label": "USD" if currency == "USD" else ("USD (기업정보 통화 미확인, 실적 행의 통화 기준)" if currency == "미확인" else currency),
    }
    by_id = {r["id"]: r for r in valid}
    lparsed = []   # 유효 실적과 연결된 물류 행 (v0.3: 예정·실제 도착일·운임 포함)
    for l in data["logistics"]:
        r = by_id.get(l.get("실적ID"))
        if not r:
            continue
        ship, eta, ata = as_date(l.get("선적일")), as_date(l.get("예정도착일")), as_date(l.get("실제도착일"))
        lparsed.append({"id": str(l.get("물류ID") or "").strip(), "rid": r["id"], "ym": r["ym"], "country": r["country"], "product": r["product"] or "",
                        "mode": str(l.get("운송수단") or "").strip(), "o": str(l.get("출발지코드") or "").strip(), "d": str(l.get("도착지코드") or "").strip(),
                        "ship": ship, "eta": eta, "ata": ata, "freight": None if blank(l.get("운임(USD)")) else num(l.get("운임(USD)")),
                        "amount": r["amount"], "weight": r["weight"], "date_err": bool(ship and ata and ata < ship)})
    ctx["lparsed"] = lparsed
    ctx["logistics_has_cols"] = bool(data["logistics"]) and "예정도착일" in data["logistics"][0] and "운임(USD)" in data["logistics"][0]
    per_country = {}
    for ct in countries:
        country = ct["name"]
        cty_rows = [r for r in valid if r["country"] == country and (r["currency"] == "USD")]
        per_country[country] = {
            "regulation": build_regulation(None, country, ctx),
            "market": build_market(None, country, ctx, cty_rows),
            "price": build_price(None, country, ctx, cty_rows),
            "logistics": build_logistics(None, country, ctx, cty_rows),
            "stability": build_stability(None, country, ctx, cty_rows),
        }
    quality["rows_with_hs_unknown_product"] = rows_hs_unknown
    quality["logistics_rows_total"] = len(data["logistics"])
    # 화면에서 기간·HS 필터로 다시 계산할 수 있도록 월별 집계(목적국·제품·거래처)를 넣는다. 개별 거래 행은 넣지 않는다.
    agg = defaultdict(lambda: {"a": 0.0, "w": 0.0, "aw": 0.0, "n": 0, "nw": 0})
    for r in valid:
        if r["currency"] != "USD":
            continue
        g = agg[(ym_str(r["ym"]), r["country"], r["product"] or "", r["customer"] or "")]
        g["a"] += r["amount"]
        g["n"] += 1
        if r["weight"] is not None and r["weight"] > 0:  # kg당 단가는 순중량이 있는 행의 금액(aw)÷순중량(w)
            g["w"] += r["weight"]
            g["aw"] += r["amount"]
            g["nw"] += 1
    rows_agg = [{"m": k[0], "c": k[1], "p": k[2], "cu": k[3], "a": round(v["a"], 2), "w": round(v["w"], 3), "aw": round(v["aw"], 2), "n": v["n"], "nw": v["nw"]} for k, v in sorted(agg.items())]
    lagg = defaultdict(lambda: {"n": 0, "blank_dest": 0, "blank_date": 0, "blank_mode": 0, "tr": 0, "ot": 0, "fr": 0.0, "fa": 0.0, "fw": 0.0, "nf": 0, "lt": 0, "ln": 0,
                                "ltmin": None, "ltmax": None, "pl": 0, "pn": 0, "blank_eta": 0, "blank_ata": 0, "blank_fr": 0, "err": 0})
    for l in lparsed:
        g = lagg[(ym_str(l["ym"]), l["country"], l["mode"] or "(빈칸)", l["o"] or "(빈칸)", l["d"] or "(빈칸)", l["product"])]
        g["n"] += 1
        g["blank_dest"] += (not l["d"])
        g["blank_date"] += (l["ship"] is None)
        g["blank_mode"] += (not l["mode"])
        g["blank_eta"] += (l["eta"] is None)
        g["blank_ata"] += (l["ata"] is None)
        g["blank_fr"] += (l["freight"] is None)
        g["err"] += int(l["date_err"])
        if l["eta"] and l["ata"] and not l["date_err"]:
            g["tr"] += 1
            g["ot"] += int(l["ata"] <= l["eta"])
        if l["freight"] is not None and l["amount"] and l["amount"] > 0:
            g["fr"] += l["freight"]
            g["fa"] += l["amount"]
            g["fw"] += l["weight"] or 0
            g["nf"] += 1
        if l["ship"] and l["ata"] and not l["date_err"]:
            days = (l["ata"] - l["ship"]).days
            g["lt"] += days
            g["ln"] += 1
            g["ltmin"] = days if g["ltmin"] is None else min(g["ltmin"], days)
            g["ltmax"] = days if g["ltmax"] is None else max(g["ltmax"], days)
            if l["eta"]:
                g["pl"] += (l["eta"] - l["ship"]).days
                g["pn"] += 1
    logistics_agg = [{"m": k[0], "c": k[1], "mode": k[2], "o": k[3], "d": k[4], "p": k[5], **{kk: (round(vv, 2) if isinstance(vv, float) else vv) for kk, vv in v.items()}}
                     for k, v in sorted(lagg.items())]
    world = wsts_regions().get("Worldwide", {})
    wsts_long = [{"month": ym_str(k), "value_thousand_usd": world[k], "yoy_pct": r2((world[k] / world[(k[0] - 1, k[1])] - 1) * 100, 4) if world.get((k[0] - 1, k[1])) else None}  # 4자리: 브라우저 재계산이 파이썬 점수와 같아지도록
                 for k in sorted(world) if k >= (2021, 1)]
    hsk_tab = hsk_table()
    for p_ in products:
        p_["has_control_candidates"] = bool(p_["input_hsk"] and hsk_tab.get(p_["input_hsk"], {}).get("control_numbers"))
    # 점수(시연용 산식 v0.2): 목적국별로 계산. 규제 P3 는 통제번호 후보가 있는 제품의 수출액 비중.
    hsk = hsk_table()
    cands = {p["id"] for p in products if p["input_hsk"] and hsk.get(p["input_hsk"], {}).get("control_numbers")}
    score_pc = {}
    for ct in countries:
        country = ct["name"]
        cty_rows = [r for r in valid if r["country"] == country and r["currency"] == "USD"]
        reg_items = per_country[country]["regulation"]
        kotra_hits = next((it["value"] for it in reg_items if it["key"] == "import_regulation_records" and it["status"] == "확인됨"), 0) or 0
        csl_hits = next((it["value"] for it in reg_items if it["key"] == "csl_search" and it["status"] == "확인됨"), 0) or 0
        score_pc[country] = score_country(country, cty_rows, ctx, period[1], cands, kotra_hits, csl_hits, [l for l in lparsed if l["country"] == country])
    # 업로드 확인 창용 결측·오류 목록: 시트 · 항목 · 건수 · 식별자(앞 6개) · 영향. 값을 채우지 않고 알리기만 한다.
    EFFECT = {"금액 빈칸": ("월별 합계·단가·점수 계산에서 제외 (0으로 더하지 않음)", "warn"), "통화 빈칸": ("통화 불명 → 합계에서 제외", "warn"),
              "거래일 빈칸": ("월 배정 불가 → 합계에서 제외", "warn"), "목적국 빈칸": ("목적국 배정 불가 → 합계에서 제외", "warn"),
              "제품ID 빈칸": ("HS별 항목·통제번호 후보·kg 단가에서 제외", "info"), "거래처ID 빈칸": ("거래처 집중도·CSL 검색에서 제외", "info"),
              "순중량 빈칸": ("kg당 단가 계산에서 제외", "info"), "수량 빈칸": ("건수만 유지", "info")}
    issues = []
    for label, n in quality["excluded_by_reason"].items():
        if n:
            issues.append({"sheet": "수출실적", "field": label.replace(" 빈칸", ""), "kind": "결측", "count": n,
                           "ids": quality.get("excluded_ids_by_reason", {}).get(label, []), "effect": EFFECT[label][0], "severity": EFFECT[label][1]})
    if quality.get("date_format_errors"):
        issues.append({"sheet": "수출실적", "field": "거래일 형식", "kind": "오류", "count": quality["date_format_errors"], "ids": quality.get("date_format_error_ids", []),
                       "effect": "날짜로 읽을 수 없어 합계에서 제외", "severity": "error"})
    if quality["missing_months"]:
        issues.append({"sheet": "수출실적", "field": "거래가 없는 달", "kind": "자료 없음", "count": len(quality["missing_months"]), "ids": quality["missing_months"][:6],
                       "effect": "월별 추세·전월비에서 '자료 없음'으로 표시 (0 아님)", "severity": "warn"})
    if quality["duplicates_removed"]:
        issues.append({"sheet": "수출실적", "field": "완전 중복 행", "kind": "중복", "count": quality["duplicates_removed"], "ids": [], "effect": "1개만 남김", "severity": "info"})
    if quality["cancelled_zero_rows"]:
        issues.append({"sheet": "수출실적", "field": "취소반품 Y", "kind": "실제 0", "count": quality["cancelled_zero_rows"], "ids": [], "effect": "실제 0으로 세고 유효 실적에서 제외", "severity": "info"})
    if hs_unknown:
        issues.append({"sheet": "제품정보", "field": "입력HSK·HS코드", "kind": "결측", "count": len(hs_unknown), "ids": hs_unknown[:6],
                       "effect": f"통제번호 후보·관세 참고치 조회 불가 · 해당 제품 {rows_hs_unknown}행은 HS별 항목에서 제외", "severity": "warn"})
    no_name = [cu["id"] for cu in customers if not cu["name"]]
    if no_name:
        issues.append({"sheet": "거래처", "field": "법인명", "kind": "결측", "count": len(no_name), "ids": no_name[:6], "effect": "CSL 제재 명단 검색 불가 (검색 불가로 표시)", "severity": "warn"})
    no_addr = [cu["id"] for cu in customers if cu["name"] and not cu["address"]]
    if no_addr:
        issues.append({"sheet": "거래처", "field": "주소", "kind": "결측", "count": len(no_addr), "ids": no_addr[:6], "effect": "CSL 주소 대조 불가 (명칭만 검색)", "severity": "info"})
    if currency == "미확인":
        issues.append({"sheet": "기업정보", "field": "금액 통화", "kind": "결측", "count": 1, "ids": ["company"], "effect": "결제통화 불명 → 참고환율·환율 변동성 미확인", "severity": "warn"})
    lq = {"운송수단": [l["id"] for l in lparsed if not l["mode"]], "도착지코드": [l["id"] for l in lparsed if not l["d"]], "선적일": [l["id"] for l in lparsed if l["ship"] is None]}
    for field, ids_ in lq.items():
        if ids_:
            issues.append({"sheet": "물류", "field": field, "kind": "결측", "count": len(ids_), "ids": ids_[:6], "effect": "조회 조건·월별 선적 건수에서 '(빈칸)'으로 표시", "severity": "info"})
    if ctx["logistics_has_cols"]:
        lq2 = {"예정도착일": ([l["id"] for l in lparsed if l["eta"] is None], "납기 준수율 계산에서 제외"),
               "실제도착일": ([l["id"] for l in lparsed if l["ata"] is None], "납기 준수율·리드타임 계산에서 제외 (미도착 또는 미기재)"),
               "운임(USD)": ([l["id"] for l in lparsed if l["freight"] is None], "운송비 비중 계산에서 제외")}
        for field, (ids_, eff) in lq2.items():
            if ids_:
                issues.append({"sheet": "물류", "field": field, "kind": "결측", "count": len(ids_), "ids": ids_[:6], "effect": eff, "severity": "warn"})
        errs = [l["id"] for l in lparsed if l["date_err"]]
        if errs:
            issues.append({"sheet": "물류", "field": "실제도착일 < 선적일", "kind": "오류", "count": len(errs), "ids": errs[:6], "effect": "날짜 역전 → 오류 행으로 표시, 납기·리드타임 계산에서 제외", "severity": "error"})
    elif data["logistics"]:
        issues.append({"sheet": "물류", "field": "예정도착일·실제도착일·운임(USD) 열", "kind": "열 없음", "count": len(data["logistics"]), "ids": [],
                       "effect": "납기 준수율·운송비 비중을 계산할 수 없어 물류 점수 자료 부족", "severity": "warn"})
    # 원본 행 번호를 함께 제공한다. 식별자만으로 찾기 어려운 중복 ID도 모두 표시한다.
    location_book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    id_columns = {"수출실적": "실적ID", "제품정보": "제품ID", "거래처": "거래처ID", "물류": "물류ID"}
    location_maps = {}
    for sheet, id_column in id_columns.items():
        positions, active = defaultdict(list), False
        for row_number, row in enumerate(location_book[sheet].iter_rows(values_only=True), 1):
            if row and row[0] == id_column:
                active = True
                continue
            if active and row and row[0] is not None:
                positions[str(row[0])].append(row_number)
        location_maps[sheet] = positions
    location_book.close()
    for issue in issues:
        positions = location_maps.get(issue["sheet"], {})
        issue["row_numbers"] = sorted({n for identifier in issue["ids"] for n in positions.get(str(identifier), [])})
    quality["issues"] = issues
    quality["issue_counts"] = {sev: sum(1 for i in issues if i["severity"] == sev) for sev in ("error", "warn", "info")}
    doc = {
        "company_id": cid, "company_name": name, "company_name_en": str(info.get("company_en") or "").strip(),
        "file_name": path.name, "file_sha256": sha256(path), "schema": SCHEMA, "data_class": DATA_CLASS,
        "template_version": str(info.get("template_version") or ""), "generated_at": datetime.now().isoformat(timespec="seconds"),
        "score": {"mode": "demo", "rule": SCORE_RULE, "weights": WEIGHTS, "overall_missing": OVERALL_MISSING,
                  "note": "가상 데이터 · 시연용 산식 v0.3 — 확정 채점 기준이 아님. 물류는 물류 시트의 예정·실제 도착일(납기 준수율)과 운임(운송비 비중)으로 계산, 가격은 관세 항목만 반영",
                  "per_country": score_pc},
        "common": {
            "period": {"from": ym_str(period[0]), "to": ym_str(period[1])},
            "products": products,
            "hs_unknown_products": hs_unknown,
            "analysis_hs6": hs6_list,
            "countries": countries,
            "main_country": countries[0]["name"] if countries else None,
            "main_hs6": max(by_hs, key=by_hs.get) if by_hs else None,
            "currency": currency,
            "data_quality": quality,
        },
        "per_country": per_country,
        "rows_agg": rows_agg,
        "logistics_agg": logistics_agg,
        "public_series": {"wsts_worldwide": wsts_long, "wsts_source": F_WSTS.name},
    }
    text = json.dumps(doc, ensure_ascii=False)
    low = text.lower()
    for pat in REAL_NAME_PATTERNS:
        assert pat.lower() not in low, f"{path.name}: JSON 에 실제 기업명 문자열 '{pat}' 포함"
    return doc


def status_counts(doc):
    cnt = {s: 0 for s in STATUS}
    for area in doc["per_country"].values():
        for items in area.values():
            for it in items:
                cnt[it["status"]] += 1
    return cnt


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(SAMPLES.glob("*.xlsx"))
    if not files:
        raise SystemExit("junhee/data/samples/*.xlsx 없음")
    index = {"generated_at": datetime.now().isoformat(timespec="seconds"), "schema": SCHEMA, "data_class": DATA_CLASS, "companies": []}
    docs = []
    for f in files:
        doc = build_company(f)
        (OUT / f"{doc['company_id']}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        index["companies"].append({k: doc[k] for k in ("company_id", "company_name", "company_name_en", "file_name", "file_sha256")}
                                  | {"period": doc["common"]["period"], "main_country": doc["common"]["main_country"], "main_hs6": doc["common"]["main_hs6"]})
        docs.append(doc)
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")

    for doc in docs:
        q = doc["common"]["data_quality"]
        print("=" * 78)
        print(f"{doc['company_name']} ({doc['company_id']}) · {doc['file_name']} · 기간 {doc['common']['period']['from']}~{doc['common']['period']['to']} · 통화 {doc['common']['currency']}")
        print(f"  행 {q['rows_total']} → 중복 제거 {q['duplicates_removed']} · 취소(실제 0) {q['cancelled_zero_rows']} · 유효 {q['rows_valid']} · 합계 제외 {q['rows_excluded_from_totals']}")
        print("  결측 사유별:", {k: v for k, v in q["excluded_by_reason"].items()})
        print("  빈 달:", q["missing_months"] or "없음", "· HS 미확인 제품:", doc["common"]["hs_unknown_products"] or "없음", f"(해당 행 {q['rows_with_hs_unknown_product']})")
        print("  목적국:", ", ".join(f"{c['name']} {c['export_share']*100:.1f}%" for c in doc["common"]["countries"]), "· 주요 HS6:", doc["common"]["main_hs6"])
        print("  항목 status (모든 목적국 합산):", status_counts(doc))
        mc = doc["common"]["main_country"]
        sc = doc["score"]["per_country"].get(mc, {})
        print(f"  점수({mc}): 종합 {sc.get('overall', {}).get('score')} (전월 {sc.get('overall', {}).get('delta_vs_prev_month')}) · "
              + " · ".join(f"{f['label_ko']} {f['score'] if f['state'] == 'ok' else '자료 부족'}" for f in sc.get("factors", [])))
    print("written:", OUT)


if __name__ == "__main__":
    main()
