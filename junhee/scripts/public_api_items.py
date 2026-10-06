# -*- coding: utf-8 -*-
"""공개 API 원자료(junhee/data/raw/api/*.json, fetch_public_apis.py 결과) → handoff-v1 항목 (junhee, 2026-09-26).

build_company_items.py 가 목적국마다 부른다. 원자료 파일이 없으면 None 을 돌려주고, 호출한 쪽은 기존 '미확인' 항목을 그대로 둔다.
원칙 (handoff):
- 목적국 수입액(Comtrade) · 한국의 해당국 수출액(관세청) · WSTS 산업매출은 서로 다른 정보로 둔다.
- 성장률·변동계수·급감은 필요한 달이 모두 있을 때만 계산한다(빈 달을 0 으로 채우지 않음). 월별이 없고 연간만 있으면 '연간 기준'으로 표시.
- 실제 0 과 자료 없음 구분: 월별 통계에 나라가 없으면 자료 없음(None), 0 으로 온 값은 0.
- 화물편·선박 기록은 공항·항만·국가 기준 정보이며 직항 여부·배송시간·운송 가능 여부를 확정하지 않는다.
행(rows)에는 HS6 를 남겨 화면의 HS 필터로 다시 합칠 수 있게 한다.
"""
import json
import statistics
from functools import lru_cache
from pathlib import Path

API = Path(__file__).resolve().parents[1] / "data" / "raw" / "api"


@lru_cache(maxsize=None)
def load(name):
    p = API / name
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def item(key, label, status, value=None, unit=None, period=None, as_of=None, source=None, basis=None, note=None, rows=None, **extra):
    d = {"key": key, "label": label, "status": status, "value": value, "unit": unit, "period": period, "as_of": as_of,
         "source": source, "basis": basis, "note": note, "rows": rows if rows is not None else []}
    d.update(extra)
    return d


def r2(x, d=2):
    return None if x is None else round(x, d)


def ym(p):  # "202607" → "2026-07"
    p = str(p)
    return f"{p[:4]}-{p[4:6]}" if len(p) == 6 else p


def ym_add(m, k):
    y, mm = int(m[:4]), int(m[5:7])
    n = y * 12 + (mm - 1) + k
    return f"{n // 12}-{n % 12 + 1:02d}"


def window(series, end, n):
    """end 를 포함한 n 개월 합. 한 달이라도 없으면 None."""
    total = 0.0
    for k in range(n):
        v = series.get(ym_add(end, -k))
        if v is None:
            return None
        total += v
    return total


def latest_end(series, need):
    """need(end) 가 값을 돌려주는 가장 최근 end 월."""
    for end in sorted(series, reverse=True):
        v = need(end)
        if v is not None:
            return end, v
    return None, None


def fetched(name):
    d = load(name)
    return (d or {}).get("fetched_at", "")[:10]


# ---------------------------------------------------------------- 시장성 (Comtrade 목적국 수입 · 관세청 한국 수출)
def _comtrade(iso, hs6):
    d = load("comtrade_imports.json")
    if not d:
        return None
    c = (d.get("countries") or {}).get(iso)
    if not c or c.get("error"):
        return {"missing": (c or {}).get("error") or "Comtrade 에 이 나라 자료 없음"}
    hs = set(hs6)
    rows, world, korea = {}, {}, {}
    for r in c.get("monthly", []):
        if r["hs6"] not in hs or r.get("value_usd") is None:
            continue
        m = ym(r["period"])
        row = rows.setdefault((m, r["hs6"]), {"month": m, "hs6": r["hs6"], "world_usd": None, "korea_usd": None})
        row["world_usd" if r["partner"] == "WORLD" else "korea_usd"] = r["value_usd"]
        tgt = world if r["partner"] == "WORLD" else korea
        tgt[m] = tgt.get(m, 0) + r["value_usd"]
    annual_w, annual_k, arows = {}, {}, {}
    for r in c.get("annual", []):
        if r["hs6"] not in hs or r.get("value_usd") is None:
            continue
        row = arows.setdefault((r["period"], r["hs6"]), {"year": r["period"], "hs6": r["hs6"], "world_usd": None, "korea_usd": None})
        row["world_usd" if r["partner"] == "WORLD" else "korea_usd"] = r["value_usd"]
        tgt = annual_w if r["partner"] == "WORLD" else annual_k
        tgt[r["period"]] = tgt.get(r["period"], 0) + r["value_usd"]
    return {"name": c.get("name"), "rows": sorted(rows.values(), key=lambda x: (x["month"], x["hs6"])), "world": world, "korea": korea,
            "arows": sorted(arows.values(), key=lambda x: (x["year"], x["hs6"])), "annual_w": annual_w, "annual_k": annual_k,
            "source": "UN Comtrade (" + (c.get("name") or iso) + " 보고 수입, HS " + "·".join(hs6) + ")"}


def market_items(country, iso, hs6):
    ct = _comtrade(iso, hs6) if iso else None
    if ct is None:
        return None
    src_f = f"UN Comtrade API · 수집 {fetched('comtrade_imports.json')}"
    out = []
    if ct.get("missing"):
        miss = ct["missing"]
        return [item(k, lbl, "자료 부족", source=src_f, note=miss) for k, lbl in (
            ("destination_imports", "목적국 수입시장 규모 (연간·월별)"), ("korea_share", "한국산 수입점유율"), ("growth_yoy", "성장률 · 전년 동기 대비"),
            ("growth_3m_yoy", "성장률 · 최근 3개월 전년 동기 대비"), ("cagr_3y", "성장률 · 3년 연평균(CAGR)"))] + [korea_exports_item(country, iso, hs6)]
    world, korea = ct["world"], ct["korea"]
    monthly = bool(world)
    months = sorted(world)
    last = months[-1] if months else None
    common = dict(source=src_f)
    if monthly:
        end12, v12 = latest_end(world, lambda e: window(world, e, 12))
        partial = end12 is None
        if partial:  # 12개월이 다 차지 않으면 있는 달의 합과 개월 수를 밝힌다
            recent = [m for m in months if m > ym_add(last, -12)]
            v12, end12 = sum(world[m] for m in recent), last
        out.append(item("destination_imports", "목적국 수입시장 규모 (연간·월별)", "확인됨", value=r2(v12), unit="USD (최근 12개월 합)",
                        period=f"{ym_add(end12, -11)}~{end12}", as_of=end12, **common,
                        basis=f"{ct['name']} 의 HS {'·'.join(hs6)} 전 세계 수입액(partner 0) 월별 합계 · 최근 12개월 합" + (" (빈 달이 있어 있는 달만 합산)" if partial else ""),
                        note="목적국 수입통계 (한국 수출액·WSTS 산업매출과 다른 정보) · Comtrade 발표 지연으로 최근 1~2개월 없음",
                        rows=ct["rows"], granularity="monthly", months_available=len(months)))
        k12 = window(korea, end12, 12) if not partial else sum(korea.get(m, 0) for m in months if m > ym_add(last, -12))
        out.append(item("korea_share", "한국산 수입점유율", "확인됨" if k12 is not None and v12 else "자료 부족",
                        value=r2(k12 / v12 * 100, 1) if k12 is not None and v12 else None, unit="%", period=f"{ym_add(end12, -11)}~{end12}", as_of=end12, **common,
                        basis="같은 기간 한국산(partner 410) 수입액 ÷ 전 세계 수입액 × 100"))
        e, g = latest_end(world, lambda e: (lambda a, b: (a / b - 1) * 100 if a is not None and b else None)(window(world, e, 12), window(world, ym_add(e, -12), 12)))
        out.append(item("growth_yoy", "성장률 · 전년 동기 대비", "확인됨" if g is not None else "자료 부족", value=r2(g, 1), unit="%",
                        period=f"{ym_add(e, -23)}~{e}" if e else None, as_of=e, **common,
                        basis="최근 12개월 수입액 ÷ 그 전 12개월 수입액 − 1 (24개월이 모두 있는 가장 최근 구간)", note=None if g is not None else "비교할 24개월이 모두 있는 구간 없음"))
        e3, g3 = latest_end(world, lambda e: (lambda a, b: (a / b - 1) * 100 if a is not None and b else None)(window(world, e, 3), window(world, ym_add(e, -12), 3)))
        out.append(item("growth_3m_yoy", "성장률 · 최근 3개월 전년 동기 대비", "확인됨" if g3 is not None else "자료 부족", value=r2(g3, 1), unit="%",
                        period=f"{ym_add(e3, -2)}~{e3}" if e3 else None, as_of=e3, **common, basis="최근 3개월 수입액 ÷ 전년 같은 3개월 − 1"))
        ec, gc = latest_end(world, lambda e: (lambda a, b: ((a / b) ** (1 / 3) - 1) * 100 if a is not None and b else None)(window(world, e, 12), window(world, ym_add(e, -36), 12)))
        if gc is None and len(ct["annual_w"]) >= 4:
            ys = sorted(ct["annual_w"])
            y1, y0 = ys[-1], str(int(ys[-1]) - 3)
            if y0 in ct["annual_w"] and ct["annual_w"][y0]:
                gc, ec = ((ct["annual_w"][y1] / ct["annual_w"][y0]) ** (1 / 3) - 1) * 100, y1
                out.append(item("cagr_3y", "성장률 · 3년 연평균(CAGR)", "확인됨", value=r2(gc, 1), unit="%", period=f"{y0}~{y1} (연간)", as_of=y1, **common,
                                basis="월별 48개월이 모두 있지 않아 연간 수입액으로 계산: (최근 연도 ÷ 3년 전) ^ (1/3) − 1"))
                gc = "done"
        if gc != "done":
            out.append(item("cagr_3y", "성장률 · 3년 연평균(CAGR)", "확인됨" if gc is not None else "자료 부족", value=r2(gc, 1), unit="%",
                            period=f"{ym_add(ec, -47)}~{ec}" if ec else None, as_of=ec, **common,
                            basis="(최근 12개월 ÷ 36개월 전 12개월) ^ (1/3) − 1", note=None if gc is not None else "48개월 자료 필요"))
    else:
        aw = ct["annual_w"]
        ys = sorted(aw)
        if not ys:
            return [item(k, lbl, "자료 부족", source=src_f, note=f"{country}: Comtrade 수입 자료 없음") for k, lbl in (
                ("destination_imports", "목적국 수입시장 규모 (연간·월별)"), ("korea_share", "한국산 수입점유율"), ("growth_yoy", "성장률 · 전년 동기 대비"),
                ("growth_3m_yoy", "성장률 · 최근 3개월 전년 동기 대비"), ("cagr_3y", "성장률 · 3년 연평균(CAGR)"))] + [korea_exports_item(country, iso, hs6)]
        y = ys[-1]
        note = f"{country} 는 Comtrade 월별 자료가 없어 연간 값(최근 {y}년)으로 표시 · 월별 성장률·최근 3개월 비교는 자료 부족"
        out.append(item("destination_imports", "목적국 수입시장 규모 (연간·월별)", "확인됨", value=r2(aw[y]), unit=f"USD ({y}년 연간)", period=y, as_of=y, **common,
                        basis=f"{ct['name']} 의 HS {'·'.join(hs6)} 전 세계 수입액 연간 합", note=note, rows=ct["arows"], granularity="annual"))
        k = ct["annual_k"].get(y)
        out.append(item("korea_share", "한국산 수입점유율", "확인됨" if k is not None and aw[y] else "자료 부족", value=r2(k / aw[y] * 100, 1) if k is not None and aw[y] else None,
                        unit="%", period=y, as_of=y, **common, basis="연간 한국산 수입액 ÷ 전 세계 수입액 × 100"))
        prev = str(int(y) - 1)
        g = (aw[y] / aw[prev] - 1) * 100 if aw.get(prev) else None
        out.append(item("growth_yoy", "성장률 · 전년 동기 대비", "확인됨" if g is not None else "자료 부족", value=r2(g, 1), unit="%", period=f"{prev}~{y} (연간)", as_of=y, **common,
                        basis="연간 수입액 전년 대비 (월별 자료 없음)"))
        out.append(item("growth_3m_yoy", "성장률 · 최근 3개월 전년 동기 대비", "자료 부족", **common, note=note))
        y0 = str(int(y) - 3)
        gc = ((aw[y] / aw[y0]) ** (1 / 3) - 1) * 100 if aw.get(y0) else None
        out.append(item("cagr_3y", "성장률 · 3년 연평균(CAGR)", "확인됨" if gc is not None else "자료 부족", value=r2(gc, 1), unit="%", period=f"{y0}~{y} (연간)", as_of=y, **common,
                        basis="(최근 연도 ÷ 3년 전) ^ (1/3) − 1", note=None if gc is not None else "3년 전 연간 자료 없음"))
    out.append(korea_exports_item(country, iso, hs6))
    return out


def korea_exports_item(country, iso, hs6):
    d = load("customs_country.json")
    c = ((d or {}).get("countries") or {}).get(iso)
    src = f"관세청 품목별 국가별 수출입실적(GW) · 수집 {fetched('customs_country.json')}"
    if not c or not c.get("monthly"):
        return item("korea_exports_to_destination", "한국의 해당국 수출액 (관세청)", "자료 부족", source=src, note=f"{country}: 관세청 국가별 자료 없음")
    rows = [r for r in c["monthly"] if r["hs6"] in hs6]
    s = {}
    for r in rows:
        s[r["month"]] = s.get(r["month"], 0) + r["exp_usd"]
    last = max(s)
    v12 = window(s, last, 12)
    return item("korea_exports_to_destination", "한국의 해당국 수출액 (관세청)", "확인됨", value=r2(v12), unit="USD (최근 12개월 합)", period=f"{ym_add(last, -11)}~{last}", as_of=last,
                source=src, basis=f"한국 → {country} HS {'·'.join(hs6)} 수출액(HS10 합산) 월별 · 최근 12개월 합",
                note="한국 측 수출 통계 (목적국 수입통계와 집계 기준이 다름)",
                rows=[{"month": r["month"], "hs6": r["hs6"], "exp_usd": r["exp_usd"], "exp_kg": r["exp_kg"]} for r in rows])


# ---------------------------------------------------------------- 가격 (관세청 kg 단가 · Comtrade 한국 전체 대비)
def price_items(country, iso, hs6):
    d = load("customs_country.json")
    c = ((d or {}).get("countries") or {}).get(iso)
    if d is None:
        return None
    out = []
    src = f"관세청 품목별 국가별 수출입실적(GW) · 수집 {fetched('customs_country.json')}"
    rows = [r for r in (c or {}).get("monthly", []) if r["hs6"] in hs6]
    if rows:
        last = max(r["month"] for r in rows)
        win = [r for r in rows if r["month"] > ym_add(last, -12)]
        usd, kg = sum(r["exp_usd"] for r in win), sum(r["exp_kg"] for r in win)
        prow = [{"month": r["month"], "hs6": r["hs6"], "exp_usd": r["exp_usd"], "exp_kg": r["exp_kg"], "usd_per_kg": r2(r["exp_usd"] / r["exp_kg"]) if r["exp_kg"] else None} for r in rows]
        out.append(item("trade_unit_price", "무역통계 kg당 단가 (한국 → 목적국 수출)", "확인됨" if kg else "자료 부족", value=r2(usd / kg) if kg else None, unit="USD/kg (최근 12개월)",
                        period=f"{ym_add(last, -11)}~{last}", as_of=last, source=src, basis="최근 12개월 수출액 합 ÷ 수출 중량(kg) 합 · 월별 단가는 행별 계산",
                        note="통계 단가이며 제품의 실제 판매가가 아님", rows=prow))
    else:
        out.append(item("trade_unit_price", "무역통계 kg당 단가 (한국 → 목적국 수출)", "자료 부족", source=src, note=f"{country}: 관세청 국가별 자료 없음"))
    cw = load("customs_world.json")
    if rows and cw and cw.get("monthly"):
        # 기준 대비 단가: 통계 단가와 같은 출처(관세청)·같은 품목·같은 12개월로 (목적국 kg 단가 ÷ 한국 전체 kg 단가) × 100
        last = max(r["month"] for r in rows)
        wrows = [r for r in cw["monthly"] if r["hs6"] in hs6 and ym_add(last, -12) < r["month"] <= last]
        drows = [r for r in rows if ym_add(last, -12) < r["month"] <= last]
        brow = []
        for h in hs6:
            du, dk = sum(r["exp_usd"] for r in drows if r["hs6"] == h), sum(r["exp_kg"] for r in drows if r["hs6"] == h)
            wu, wk = sum(r["exp_usd"] for r in wrows if r["hs6"] == h), sum(r["exp_kg"] for r in wrows if r["hs6"] == h)
            if dk and wk:
                brow.append({"hs6": h, "dest_usd_per_kg": r2(du / dk), "world_usd_per_kg": r2(wu / wk), "ratio_pct": r2((du / dk) / (wu / wk) * 100, 1), "dest_usd": du, "dest_kg": dk, "world_usd": wu, "world_kg": wk})
        du = sum(b["dest_usd"] for b in brow); dk = sum(b["dest_kg"] for b in brow); wu = sum(b["world_usd"] for b in brow); wk = sum(b["world_kg"] for b in brow)
        out.append(item("baseline_unit_price", "기준 대비 단가 (한국 전체 수출단가 대비)", "확인됨" if brow else "자료 부족",
                        value=r2((du / dk) / (wu / wk) * 100, 1) if brow else None, unit="% (한국 전체 = 100)", period=f"{ym_add(last, -11)}~{last}", as_of=last,
                        source=f"관세청 품목별 국가별 수출입실적(GW) · 수집 {fetched('customs_world.json')}",
                        basis="같은 출처(관세청)·같은 품목·같은 12개월에서 (목적국 수출 kg 단가 ÷ 한국 전체 수출 kg 단가) × 100",
                        note="통계 단가 비교이며 실제 판매가 비교가 아님", rows=brow))
        return out
    k = load("comtrade_korea_exports.json")
    if k:
        dest = {}
        world = {}
        for r in k["rows"]:
            if r["hs6"] not in hs6 or r.get("value_usd") is None or not r.get("net_wgt_kg"):
                continue
            tgt = world if r["partner"] == "WORLD" else (dest if r["partner"] == iso else None)
            if tgt is None:
                continue
            m = ym(r["period"])
            g = tgt.setdefault((m, r["hs6"]), [0.0, 0.0])
            g[0] += r["value_usd"]
            g[1] += r["net_wgt_kg"]
        common = sorted({m for m, _ in dest} & {m for m, _ in world})
        if common:
            last = common[-1]
            use = [m for m in common if m > ym_add(last, -12)]
            brow = []
            for h in hs6:
                du = sum(dest.get((m, h), [0, 0])[0] for m in use)
                dk = sum(dest.get((m, h), [0, 0])[1] for m in use)
                wu = sum(world.get((m, h), [0, 0])[0] for m in use)
                wk = sum(world.get((m, h), [0, 0])[1] for m in use)
                if dk and wk:
                    brow.append({"hs6": h, "dest_usd_per_kg": r2(du / dk), "world_usd_per_kg": r2(wu / wk), "ratio_pct": r2((du / dk) / (wu / wk) * 100, 1),
                                 "dest_usd": du, "dest_kg": dk, "world_usd": wu, "world_kg": wk})
            du = sum(b["dest_usd"] for b in brow); dk = sum(b["dest_kg"] for b in brow); wu = sum(b["world_usd"] for b in brow); wk = sum(b["world_kg"] for b in brow)
            out.append(item("baseline_unit_price", "기준 대비 단가 (한국 전체 수출단가 대비)", "확인됨" if brow else "자료 부족",
                            value=r2((du / dk) / (wu / wk) * 100, 1) if brow else None, unit="% (한국 전체 = 100)", period=f"{use[0]}~{last}", as_of=last,
                            source=f"UN Comtrade (한국 보고 수출) · 수집 {fetched('comtrade_korea_exports.json')}",
                            basis="같은 출처(Comtrade 한국 보고 수출)·같은 품목·같은 기간에서 (목적국 수출 kg 단가 ÷ 전 세계 수출 kg 단가) × 100",
                            note="통계 단가 비교이며 실제 판매가 비교가 아님", rows=brow))
        else:
            out.append(item("baseline_unit_price", "기준 대비 단가 (한국 전체 수출단가 대비)", "자료 부족", note="Comtrade 한국 수출 자료에서 겹치는 달 없음"))
    return out


def fx_latest(ccy):
    d = load("koreaexim_fx.json")
    if not d or not ccy:
        return None
    rates = d.get("rates") or {}
    for key in (ccy, "CNH" if ccy == "CNY" else None, f"{ccy}(100)"):
        if key and key in rates:
            v = float(str(rates[key]).replace(",", ""))
            per = 100 if key.endswith("(100)") else 1
            return {"date": d.get("date"), "value": r2(v / per, 4), "unit": f"KRW/{ccy}", "source": "한국수출입은행 현재환율 (매매기준율)" + (" · CNY 는 역외 CNH" if key == "CNH" else "")}
    return None


# ---------------------------------------------------------------- 물류 (인천공항 · 해양수산부)
def logistics_items(country, iso):
    wk = load("incheon_cargo_weekly.json")
    if not wk:
        return None
    amap = (load("airports_iata.json") or {}).get("iata_to_iso2") or {}
    rows, seen = [], set()
    for direction, lst in (("출발", wk.get("departures", [])), ("도착", wk.get("arrivals", []))):
        for f in lst:
            if amap.get(f.get("airportCode")) != iso:
                continue
            k = (direction, f.get("flightId"), f.get("scheduleDateTime"))
            if k in seen:
                continue
            seen.add(k)
            rows.append({"direction": direction, "airline": f.get("airline"), "flight": f.get("flightId"), "airport": f.get("airport"), "airport_code": f.get("airportCode"),
                         "scheduled": f.get("scheduleDateTime"), "estimated": f.get("estimatedDateTime"), "status": f.get("remark") or "예정"})
    rows.sort(key=lambda r: r["scheduled"] or "")
    allt = [f.get("scheduleDateTime") or "" for lst in (wk.get("departures", []), wk.get("arrivals", [])) for f in lst]
    per = f"{min(allt)[:4]}-{min(allt)[4:6]}-{min(allt)[6:8]}~{max(allt)[:4]}-{max(allt)[4:6]}-{max(allt)[6:8]}" if allt else None
    src_w = f"인천국제공항공사 화물편 주간 운항 현황 · 수집 {fetched('incheon_cargo_weekly.json')}"
    out = [item("cargo_flights", "인천공항 화물편 일정", "확인됨", value=len(rows), unit="편 (중복 제거)", period=per, as_of=fetched("incheon_cargo_weekly.json"), source=src_w,
                basis=f"조회 시점 기준 주간(약 +6일) 화물편 중 상대공항(IATA)이 {country}({iso})인 편 · 공항→국가는 OurAirports 공개 목록",
                note="공항 기준 운항 정보이며 HS별 반도체 운송실적·직항 여부·배송시간을 뜻하지 않음", rows=rows,
                departures=sum(1 for r in rows if r["direction"] == "출발"), arrivals=sum(1 for r in rows if r["direction"] == "도착"))]
    st = load("incheon_country_cargo.json") or {}
    months = sorted((st.get("months") or {}))
    mrows = []
    for m in months:
        hit = next((x for x in st["months"][m] if x.get("country") == country), None)
        num = lambda v: None if v in (None, "") else int(str(v).replace(",", ""))
        mrows.append({"month": ym(m), "dep": num(hit["dep"]) if hit else None, "arr": num(hit["arr"]) if hit else None, "total": num(hit["total"]) if hit else None})
    have = [r for r in mrows if r["total"] is not None]
    last = have[-1] if have else None
    out.append(item("flight_counts", "운항 횟수 (국가별 월간 출발·도착편, 화물기)", "확인됨" if have else "자료 부족", value=last["total"] if last else None, unit="편 (최근 월)",
                    period=f"{mrows[0]['month']}~{mrows[-1]['month']}" if mrows else None, as_of=last["month"] if last else None,
                    source=f"인천국제공항공사 국가별 항공 통계 · 수집 {fetched('incheon_country_cargo.json')}",
                    basis="화물기(pax_cargo=N) 국가별 월간 출발·도착편 · 통계에 나라가 없는 달은 자료 없음(0 으로 채우지 않음)",
                    note="인천공항 기준 국가별 운항 통계", rows=mrows, departures=last["dep"] if last else None, arrivals=last["arr"] if last else None))
    vs = load("vessel_calls.json")
    if vs:
        vrows = []
        for c in vs.get("calls", []):
            prev, nxt = (c.get("prev_port") or ""), (c.get("next_port") or "")
            if not (prev.startswith(iso) or nxt.startswith(iso)):
                continue
            ent = next((d["at"] for d in c.get("details", []) if d.get("type") == "입항"), None)
            dep = next((d["at"] for d in c.get("details", []) if d.get("type") == "출항"), None)
            vrows.append({"vessel": c.get("vessel"), "flag": c.get("flag"), "kind": c.get("kind"), "prev": f"{c.get('prev_name') or ''}({prev})" if prev else "",
                          "next": f"{c.get('next_name') or ''}({nxt})" if nxt else "", "arrival": (ent or "")[:16].replace("T", " "), "departure": (dep or "")[:16].replace("T", " ")})
        out.append(item("vessel_records", f"선박 입출항 기록 ({vs.get('port')}항 · {country} 전후 항로)", "확인됨", value=len(vrows), unit="건", period=vs.get("period"),
                        as_of=fetched("vessel_calls.json"), source=f"해양수산부 선박운항정보(선박입출항신고) · 수집 {fetched('vessel_calls.json')}",
                        basis=f"{vs.get('port')}항 입출항 신고 중 이전 출항지 또는 다음 입항지가 {country}({iso}) 항만(UN/LOCODE)인 기록",
                        note="항만 기준 기록이며 화물 품목·운송 가능 여부를 뜻하지 않음 · 0 건은 조회 기간에 해당 기록이 없다는 실제 0", rows=vrows[:60]))
    return out


# ---------------------------------------------------------------- 안정성 (목적국 월별 수입)
def stability_items(country, iso, hs6):
    ct = _comtrade(iso, hs6) if iso else None
    if ct is None:
        return None
    src = f"UN Comtrade API · 수집 {fetched('comtrade_imports.json')}"
    labels = (("destination_monthly_imports", "목적국 월별 수입금액·전월비"), ("cv", "변동계수 CV (목적국 수입액)"), ("sharp_drops", "급감 이력 (전월비 −20% 이하)"))
    world = (ct or {}).get("world") or {}
    if ct.get("missing") or not world:
        why = ct.get("missing") or f"{country} 는 Comtrade 월별 수입 자료가 없음(연간만 제공)"
        return [item(k, l, "자료 부족", source=src, note=why) for k, l in labels]
    months = sorted(world)
    last = months[-1]
    first = months[0]
    span = [m for m in (ym_add(last, -k) for k in range(23, -1, -1)) if m >= first]  # 최근 24개월 (수집 범위 밖의 달은 결측으로 세지 않음)
    rows, drops, comparable = [], [], 0
    prev = None
    for m in span:
        v = world.get(m)
        mom = None
        if v is not None and prev is not None and prev > 0:
            comparable += 1
            mom = (v / prev - 1) * 100
            if mom <= -20:
                drops.append({"month": m, "mom_pct": r2(mom, 1), "value_usd": v})
        rows.append({"month": m, "value_usd": v, "mom_pct": r2(mom, 1)})
        prev = v
    present = [r["value_usd"] for r in rows if r["value_usd"] is not None]
    cv = statistics.pstdev(present) / statistics.mean(present) * 100 if len(present) >= 6 and statistics.mean(present) > 0 else None
    miss = [r["month"] for r in rows if r["value_usd"] is None]
    common = dict(period=f"{span[0]}~{last}", as_of=last, source=src)
    return [
        item("destination_monthly_imports", "목적국 월별 수입금액·전월비", "확인됨", value=r2(world[last]), unit="USD (최근 월)", **common,
             basis=f"{ct['name']} 의 HS {'·'.join(hs6)} 전 세계 수입액 월별 · 전월비는 두 달 모두 있을 때만", note="자료 없는 달: " + ", ".join(miss) if miss else None,
             rows=rows, missing_months=miss),
        item("cv", "변동계수 CV (목적국 수입액)", "확인됨" if cv is not None else "자료 부족", value=r2(cv, 1), unit="%", **common,
             basis=f"최근 24개월 중 자료 있는 {len(present)}개월의 모표준편차 ÷ 평균", note="과거 변동이며 미래 손실·수출 실패 확률이 아님"),
        item("sharp_drops", "급감 이력 (전월비 −20% 이하)", "확인됨" if comparable else "자료 부족", value=len(drops), unit="회", **common,
             basis=f"최근 24개월 중 비교 가능한 {comparable}회에서 전월 대비 −20% 이하인 달", rows=drops, drop_count=len(drops), comparable_months=comparable,
             drop_rate_pct=r2(len(drops) / comparable * 100, 1) if comparable else None),
    ]
