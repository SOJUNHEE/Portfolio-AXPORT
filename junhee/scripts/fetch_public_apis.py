"""공개 API 수집 (junhee, 2026-09-26) → junhee/data/raw/api/*.json

handoff 의 '미확인' 항목을 채우는 원자료를 받는다. 키는 api_keys.py 가 실행 시점에만 읽고, 저장 파일·로그에 남기지 않는다.
  comtrade_imports.json      UN Comtrade  목적국의 HS6 수입액(세계 합계·한국산) 월별(가능하면 48개월) + 연간
  customs_country.json       관세청 품목별 국가별 수출입실적(GW) 한국 → 목적국 수출액·중량 (월별, HS10 → HS6 합산)
  customs_world.json         관세청 품목별 국가별 수출입실적(GW) 국가 코드 없이 = 한국 전체 수출 (기준 대비 단가: 통계 단가와 같은 출처)
  comtrade_korea_exports.json UN Comtrade 한국 보고 수출(세계·목적국) 월별 — 기준 대비 단가(같은 출처)
  incheon_cargo_weekly.json  인천국제공항공사 화물편 주간 운항 현황 (출발·도착, 조회일 기준 약 +6일)
  incheon_country_cargo.json 인천국제공항공사 국가별 항공 통계 (화물기 pax_cargo=N, 월별 출발·도착편)
  airports_iata.json         공항 IATA → 국가 ISO2 (OurAirports 공개 CSV, 키 불필요) — 화물편을 목적국별로 묶는 데 사용
  vessel_calls.json          해양수산부 선박운항정보(VsslEtrynd5) 부산항 최근 7일 입출항 신고
  koreaexim_fx.json          한국수출입은행 현재환율 (최근 영업일 매매기준율)
사용: python junhee/scripts/fetch_public_apis.py [--only comtrade,customs,...]
"""
import argparse
import csv
import io
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode, unquote
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
from api_keys import get_key, scrub  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "junhee" / "data" / "raw" / "api"
COMPANIES = ROOT / "static" / "data" / "companies"
# ISO2 → UN M49 (Comtrade reporter 코드). 대만은 Comtrade 에 별도 보고국이 없다(Other Asia nes).
M49 = {"CN": 156, "US": 842, "DE": 276, "VN": 704, "IN": 699, "MX": 484, "CA": 124, "JP": 392, "GB": 826, "FR": 251, "SG": 702,
       "MY": 458, "TH": 764, "PH": 608, "ID": 360, "HK": 344, "NL": 528, "IT": 381, "AU": 36, "BR": 76, "TR": 792, "PL": 616, "CH": 757}
TODAY = date.today()


def now():
    return datetime.now().isoformat(timespec="seconds")


def save(name, payload):
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {"fetched_at": now(), **payload}
    (OUT / name).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  저장 {name}")


def http(url, params=None, headers=None, secrets=(), timeout=60, tries=3):
    q = ("?" + urlencode(params)) if params else ""
    last = None
    for i in range(tries):
        try:
            with urlopen(Request(url + q, headers=headers or {}), timeout=timeout) as r:
                return r.read()
        except Exception as e:  # 오류 문자열에 키가 섞일 수 있어 가린다
            last = scrub(f"{type(e).__name__} {getattr(e, 'code', '')}", *secrets)
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"요청 실패 ({last})")


def targets():
    """회사 JSON 들의 목적국(이름·ISO2)과 분석 HS6 합집합."""
    countries, hs6 = {}, set()
    for p in sorted(COMPANIES.glob("*.json")):
        if p.name == "index.json":
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        for c in d["common"]["countries"]:
            if c.get("iso2"):
                countries[c["iso2"]] = c["name"]
        hs6.update(d["common"].get("analysis_hs6") or [])
    return countries, sorted(hs6)


def ym_back(n, end=None):
    y, m = (end or (TODAY.year, TODAY.month))
    out = []
    for k in range(n):
        mm = m - k
        yy = y + (mm - 1) // 12
        mm = (mm - 1) % 12 + 1
        out.append(f"{yy}{mm:02d}")
    return sorted(out)


# ---------------------------------------------------------------- UN Comtrade
def fetch_comtrade(countries, hs6):
    key = get_key("UN_COMTRADE_API_KEY")
    months = ym_back(52)  # 3년 CAGR(48개월) + 발표 지연 여유
    out = {}
    base = dict(cmdCode=",".join(hs6), flowCode="M", partnerCode="0,410", partner2Code="0", customsCode="C00", motCode="0")
    for iso, name in countries.items():
        rep = M49.get(iso)
        if not rep:
            out[iso] = {"name": name, "error": "Comtrade 보고국 코드 없음"}
            continue
        monthly, annual = [], []
        for i in range(0, len(months), 12):
            chunk = months[i:i + 12]
            raw = http("https://comtradeapi.un.org/data/v1/get/C/M/HS", dict(reporterCode=rep, period=",".join(chunk), **base),
                       headers={"Ocp-Apim-Subscription-Key": key}, secrets=(key,))
            for x in json.loads(raw).get("data", []):
                monthly.append({"period": x["period"], "hs6": x["cmdCode"], "partner": "KR" if x["partnerCode"] == 410 else "WORLD",
                                "value_usd": x.get("primaryValue"), "net_wgt_kg": x.get("netWgt")})
            time.sleep(1.1)
        years = [str(TODAY.year - k) for k in range(1, 6)]
        raw = http("https://comtradeapi.un.org/data/v1/get/C/A/HS", dict(reporterCode=rep, period=",".join(years), **base),
                   headers={"Ocp-Apim-Subscription-Key": key}, secrets=(key,))
        for x in json.loads(raw).get("data", []):
            annual.append({"period": x["period"], "hs6": x["cmdCode"], "partner": "KR" if x["partnerCode"] == 410 else "WORLD",
                           "value_usd": x.get("primaryValue"), "net_wgt_kg": x.get("netWgt")})
        time.sleep(1.1)
        mp = sorted({r["period"] for r in monthly})
        print(f"  Comtrade {iso} {name}: 월별 {len(mp)}개월 ({mp[0] if mp else '-'}~{mp[-1] if mp else '-'}) · 연간 {sorted({r['period'] for r in annual})}")
        out[iso] = {"name": name, "reporter_m49": rep, "monthly": monthly, "annual": annual}
    save("comtrade_imports.json", {"source": "UN Comtrade API (comtradeapi.un.org, C/M·C/A/HS, flow M, partner 0=세계·410=한국, customsCode C00·motCode 0·partner2Code 0 합계 행)",
                                   "hs6": hs6, "countries": out})


def fetch_comtrade_korea(countries, hs6):
    """기준 대비 단가용: 한국(410) 보고 수출 — 세계(0)와 각 목적국. 같은 출처(Comtrade)·같은 품목·같은 기간으로 단가를 비교한다."""
    key = get_key("UN_COMTRADE_API_KEY")
    months = ym_back(26)
    partners = ["0"] + [str(M49[i]) for i in countries if i in M49]
    inv = {str(v): k for k, v in M49.items()}
    rows = []
    for i in range(0, len(months), 12):
        raw = http("https://comtradeapi.un.org/data/v1/get/C/M/HS", dict(reporterCode=410, period=",".join(months[i:i + 12]), cmdCode=",".join(hs6), flowCode="X",
                   partnerCode=",".join(partners), partner2Code="0", customsCode="C00", motCode="0"), headers={"Ocp-Apim-Subscription-Key": key}, secrets=(key,))
        for x in json.loads(raw).get("data", []):
            rows.append({"period": x["period"], "hs6": x["cmdCode"], "partner": "WORLD" if x["partnerCode"] == 0 else inv.get(str(x["partnerCode"]), str(x["partnerCode"])),
                         "value_usd": x.get("primaryValue"), "net_wgt_kg": x.get("netWgt")})
        time.sleep(1.1)
    mp = sorted({r["period"] for r in rows})
    print(f"  Comtrade 한국 수출: {len(rows)}행 ({mp[0] if mp else '-'}~{mp[-1] if mp else '-'})")
    save("comtrade_korea_exports.json", {"source": "UN Comtrade API (reporter 410 한국, flow X 수출, partner 0=세계·목적국, 합계 행)", "hs6": hs6, "rows": rows})


# ---------------------------------------------------------------- 관세청
def _customs_rows(url, params, key):
    import xml.etree.ElementTree as ET
    rows, page = [], 1
    while True:
        raw = http(url, dict(serviceKey=unquote(key), numOfRows=500, pageNo=page, **params), secrets=(key, unquote(key)))
        text = raw.decode("utf-8-sig", "replace")
        root = ET.fromstring(text)
        code = root.findtext(".//resultCode")
        if code not in ("00", "0"):
            raise RuntimeError(f"관세청 응답 코드 {code} {root.findtext('.//resultMsg')}")
        items = [{c.tag: (c.text or "") for c in it} for it in root.findall(".//items/item")]
        rows.extend(items)
        total = root.findtext(".//totalCount")
        # totalCount 가 없는 응답(국가 코드 없는 GW 조회)은 pageNo 를 무시하고 전체를 한 번에 준다 → 500 이 아니면 끝, 같은 쪽이 다시 오면 끝
        if not items or (total and len(rows) >= int(total)) or (not total and len(items) != 500) or (page > 1 and items == rows[-2 * len(items):-len(items)]):
            if page > 1 and items == rows[-2 * len(items):-len(items)]:
                del rows[-len(items):]
            break
        page += 1
        time.sleep(0.3)
    return rows


def _agg_hs6(rows, hs6):
    """HS10 행을 HS6·월로 합산 (총계 행 제외). 수출액 USD, 중량 kg."""
    out = {}
    for r in rows:
        y = r.get("year", "")
        if len(y) != 7 or "." not in y:
            continue
        hs = (r.get("hsCode") or r.get("hsCd") or "")[:6]
        if hs not in hs6:
            continue
        k = (y.replace(".", "-"), hs)
        o = out.setdefault(k, {"month": k[0], "hs6": hs, "exp_usd": 0, "exp_kg": 0, "imp_usd": 0, "imp_kg": 0})
        for f, t in (("expDlr", "exp_usd"), ("expWgt", "exp_kg"), ("impDlr", "imp_usd"), ("impWgt", "imp_kg")):
            try:
                o[t] += int(float(r.get(f) or 0))
            except ValueError:
                pass
    return sorted(out.values(), key=lambda x: (x["month"], x["hs6"]))


def fetch_customs(countries, hs6):
    key = get_key("DATA_GO_KR")
    last = (TODAY.replace(day=1) - timedelta(days=1))  # 지난달까지 (당월 미집계)
    years = list(range(last.year - 3, last.year + 1))
    per_country = {}
    for iso, name in countries.items():
        rows = []
        for y in years:
            end = f"{y}12" if y < last.year else f"{y}{last.month:02d}"
            for h in hs6:
                try:
                    rows += _customs_rows("https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList", dict(strtYymm=f"{y}01", endYymm=end, cntyCd=iso, hsSgn=h), key)
                except RuntimeError as e:
                    print(f"  관세청 {iso} {y} {h}: {e}")
        agg = _agg_hs6(rows, hs6)
        print(f"  관세청 국가별 {iso} {name}: {len(agg)}행 ({agg[0]['month'] if agg else '-'}~{agg[-1]['month'] if agg else '-'})")
        per_country[iso] = {"name": name, "monthly": agg}
    save("customs_country.json", {"source": "관세청_품목별 국가별 수출입실적(GW) apis.data.go.kr/1220000/nitemtrade/getNitemtradeList (HS10 → HS6 월별 합산, 중량 kg)",
                                  "hs6": hs6, "countries": per_country})
    world = []
    for y in years:
        end = f"{y}12" if y < last.year else f"{y}{last.month:02d}"
        for h in hs6:
            try:
                # 국가 코드 없이 부르면 한국 전체(모든 국가) 수출. Itemtrade 서비스는 이 키로 미승인(403)이라 같은 GW 서비스를 쓴다
                world += _customs_rows("https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList", dict(strtYymm=f"{y}01", endYymm=end, hsSgn=h), key)
            except RuntimeError as e:
                print(f"  관세청 품목별 {y} {h}: {e}")
    agg = _agg_hs6(world, hs6)
    print(f"  관세청 품목별(전 세계) {len(agg)}행")
    save("customs_world.json", {"source": "관세청 품목별 국가별 수출입실적(GW) 국가 코드 없이 = 한국 전체 (HS10 → HS6 월별 합산)", "hs6": hs6, "monthly": agg})


# ---------------------------------------------------------------- 인천국제공항공사
def _incheon(path, params, key, page_size=1000):
    items, page = [], 1
    while True:
        raw = http("https://apis.data.go.kr/B551177/" + path, dict(serviceKey=unquote(key), type="json", numOfRows=page_size, pageNo=page, **params), secrets=(key, unquote(key)))
        body = json.loads(raw)["response"]["body"]
        got = body.get("items") or []
        if isinstance(got, dict):
            got = got.get("item") or []
        items += got
        total = int(body.get("totalCount") or len(items))
        if not got or len(items) >= total:
            break
        page += 1
    return items


def fetch_incheon():
    key = get_key("DATA_GO_KR")
    dep = _incheon("StatusOfCargoFlightsDSOdp/getCargoDeparturesDSOdp", {}, key)
    arr = _incheon("StatusOfCargoFlightsDSOdp/getCargoArrivalsDSOdp", {}, key)
    print(f"  인천 화물편 주간: 출발 {len(dep)} · 도착 {len(arr)}")
    save("incheon_cargo_weekly.json", {"source": "인천국제공항공사_화물편 주간 운항 현황 B551177/StatusOfCargoFlightsDSOdp (getCargoDeparturesDSOdp · getCargoArrivalsDSOdp)",
                                       "departures": dep, "arrivals": arr})
    months = ym_back(25, ((TODAY.replace(day=1) - timedelta(days=1)).year, (TODAY.replace(day=1) - timedelta(days=1)).month))
    stats = {}
    for m in months:
        try:
            items = _incheon("AviationStatsByCountry/getTotalNumberOfFlight", dict(from_month=m, to_month=m, pax_cargo="N"), key, page_size=300)
        except RuntimeError as e:
            print(f"  국가별 통계 {m}: {e}")
            continue
        stats[m] = [{"country": i.get("country"), "region": i.get("region"), "arr": i.get("arrFlight"), "dep": i.get("depFlight"), "total": i.get("flights")} for i in items]
        time.sleep(0.2)
    print(f"  인천 국가별 화물기 통계: {len(stats)}개월")
    save("incheon_country_cargo.json", {"source": "인천국제공항공사_국가별 항공 통계 서비스 B551177/AviationStatsByCountry/getTotalNumberOfFlight (pax_cargo=N 화물기, 월별)", "months": stats})


def fetch_airports():
    raw = http("https://davidmegginson.github.io/ourairports-data/airports.csv", timeout=120)
    rd = csv.DictReader(io.StringIO(raw.decode("utf-8", "replace")))
    m = {}
    for r in rd:
        code = (r.get("iata_code") or "").strip()
        if len(code) == 3 and r.get("type") in ("large_airport", "medium_airport", "small_airport"):
            if code not in m or r.get("type") == "large_airport":
                m[code] = r.get("iso_country")
    print(f"  공항 IATA→국가 {len(m)}개")
    save("airports_iata.json", {"source": "OurAirports airports.csv (공개 데이터, 키 불필요)", "iata_to_iso2": m})


# ---------------------------------------------------------------- 해양수산부
def fetch_vessels(port="020", days=7):
    import xml.etree.ElementTree as ET
    key = get_key("DATA_GO_KR")
    end, start = TODAY, TODAY - timedelta(days=days - 1)
    calls, page = [], 1
    while page <= 200:
        raw = http("https://apis.data.go.kr/1192000/VsslEtrynd5/Info5", dict(serviceKey=unquote(key), prtAgCd=port, sde=start.strftime("%Y%m%d"), ede=end.strftime("%Y%m%d"),
                                                                             numOfRows=50, pageNo=page), secrets=(key, unquote(key)))
        root = ET.fromstring(raw.decode("utf-8-sig", "replace"))
        if root.findtext(".//resultCode") not in ("00", "0"):
            raise RuntimeError(f"해수부 응답 코드 {root.findtext('.//resultCode')}")
        items = root.findall(".//items/item")
        for it in items:
            g = lambda t: (it.findtext(t) or "").strip()
            det = [{"type": (d.findtext("etryndNm") or "").strip(), "at": (d.findtext("etryptDt") or d.findtext("tkoffDt") or "").strip(),
                    "berth": (d.findtext("laidupFcltyNm") or "").strip()} for d in it.findall(".//details/detail")]
            calls.append({"port": g("prtAgNm"), "vessel": g("vsslNm"), "flag": g("vsslNltyCd"), "kind": g("vsslKndNm"), "grt": g("grtg"),
                          "prev_port": g("prvsDpmprtNatPrtCd"), "prev_name": g("prvsDpmprtPrtNm"), "next_port": g("nxlnptNatPrtCd"), "next_name": g("nxlnptPrtNm"),
                          "call": f"{g('etryptYear')}-{g('etryptCo')}", "details": det})
        total = int(root.findtext(".//totalCount") or 0)
        if not items or len(calls) >= total:
            break
        page += 1
        time.sleep(0.2)
    print(f"  해수부 부산항 {start}~{end}: {len(calls)}건")
    save("vessel_calls.json", {"source": "해양수산부_선박운항정보 apis.data.go.kr/1192000/VsslEtrynd5/Info5 (선박입출항신고, 부산항 prtAgCd 020)",
                               "port": "부산", "period": f"{start}~{end}", "calls": calls})


# ---------------------------------------------------------------- 한국수출입은행
def fetch_exim():
    key = get_key("KOREAEXIM_API_KEY")
    for back in range(0, 15):
        d = TODAY - timedelta(days=back)
        rows = json.loads(http("https://oapi.koreaexim.go.kr/site/program/financial/exchangeJSON", dict(authkey=key, searchdate=d.strftime("%Y%m%d"), data="AP01"), secrets=(key,)))
        rows = [r for r in rows if r.get("result") == 1 and r.get("cur_unit")]
        if rows:
            print(f"  수출입은행 환율 {d}: {len(rows)}개 통화")
            save("koreaexim_fx.json", {"source": "한국수출입은행 현재환율 API (매매기준율 deal_bas_r)", "date": d.isoformat(),
                                       "rates": {r["cur_unit"]: r.get("deal_bas_r") for r in rows}})
            return
    print("  수출입은행 환율: 최근 15일 자료 없음")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", default="comtrade,comtrade_kr,customs,incheon,airports,vessels,exim")
    args = ap.parse_args()
    todo = set(args.only.split(","))
    countries, hs6 = targets()
    print(f"목적국 {len(countries)}개 {sorted(countries)} · HS6 {hs6}")
    steps = [("comtrade", lambda: fetch_comtrade(countries, hs6)), ("comtrade_kr", lambda: fetch_comtrade_korea(countries, hs6)), ("customs", lambda: fetch_customs(countries, hs6)), ("incheon", fetch_incheon),
             ("airports", fetch_airports), ("vessels", fetch_vessels), ("exim", fetch_exim)]
    ok = True
    for name, fn in steps:
        if name not in todo:
            continue
        print(f"[{name}]")
        try:
            fn()
        except Exception as e:
            ok = False
            print(f"  실패: {type(e).__name__} {str(e)[:200]}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
