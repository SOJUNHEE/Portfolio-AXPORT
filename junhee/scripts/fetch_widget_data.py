"""바탕화면 위젯용 공식 자료 수집 (junhee, 2026-09-26) → static/data/widgets/widgets.json

minjung 위젯(widgets.js)은 ExchangeRate-API·TheNewsAPI 키가 없으면 예시 데이터를 보여 준다. 그 파일은 고치지 않고,
이 스크립트가 받은 공식 자료를 junhee-widgets-bridge.js 가 위젯 칸에 넣는다.
  fx       한국은행 ECOS 731Y001 (주요국 통화의 대원화환율, 매매기준율, 일별) → USD/KRW · USD/CNY(=원/달러÷원/위안) · EUR/KRW, 전 영업일 대비
           (ECOS 가 안 되면 한국수출입은행 현재환율)
  weather  관세청 품목별 국가별 수출입실적(GW) 국가 코드 없이 = 한국 전체 수출 → 반도체 품목군별 올해 누계와 전년 같은 기간 대비
  news     Google 뉴스 RSS (키 불필요, 언어별 검색) · 없으면 WTO 최신 뉴스 RSS
키는 api_keys.py 가 실행 시점에만 읽는다(환경변수 우선: ECOS_API_KEY 등). 저장 파일에 키는 들어가지 않는다.
사용: python junhee/scripts/fetch_widget_data.py [--only fx,weather,news]
"""
import argparse
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlencode, unquote
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
from api_keys import MissingKey, get_key, scrub  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "static" / "data" / "widgets" / "widgets.json"
TODAY = date.today()
# minjung 위젯의 수출기상도 품목군 (sx_widgets/weather.py GROUPS 와 같은 구분)
GROUPS = {"memory": ["854232"], "processor": ["854231"], "other": ["854233", "854239", "854290"], "device": ["8541"]}
NEWS_QUERY = {"ko": ("반도체 수출 OR 수출통제 OR CBAM", "ko", "KR", "KR:ko"), "en": ("semiconductor export controls OR CBAM", "en-US", "US", "US:en"),
              "ja": ("半導体 輸出規制 OR CBAM", "ja", "JP", "JP:ja"), "zh": ("半导体 出口管制 OR CBAM", "zh-CN", "CN", "CN:zh-Hans")}


def http(url, secrets=(), timeout=40, headers=None):
    last = None
    for i in range(3):
        try:
            with urlopen(Request(url, headers=headers or {"User-Agent": "AXPORT-Dashboard/1.0"}), timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last = scrub(f"{type(e).__name__} {getattr(e, 'code', '')}", *secrets)
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"요청 실패 ({last})")


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- 환율
def fx_ecos():
    key = get_key("ECOS_API_KEY")
    start, end = (TODAY - timedelta(days=20)).strftime("%Y%m%d"), TODAY.strftime("%Y%m%d")
    series = {}
    for code, cur in (("0000001", "USD"), ("0000053", "CNY"), ("0000003", "EUR")):
        raw = http(f"https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/40/731Y001/D/{start}/{end}/{code}", secrets=(key,))
        rows = (json.loads(raw).get("StatisticSearch") or {}).get("row") or []
        series[cur] = {r["TIME"]: float(r["DATA_VALUE"]) for r in rows if r.get("DATA_VALUE")}
    days = sorted(set(series["USD"]) & set(series["CNY"]) & set(series["EUR"]))
    if len(days) < 2:
        raise RuntimeError("ECOS 환율 영업일 자료 부족")
    d1, d0 = days[-1], days[-2]
    pair = lambda d: {"USD/KRW": series["USD"][d], "USD/CNY": series["USD"][d] / series["CNY"][d], "EUR/KRW": series["EUR"][d]}
    now_, prev = pair(d1), pair(d0)
    rows = [{"pair": k, "value": round(v, 4 if k.endswith("CNY") else 2), "change": round((v / prev[k] - 1) * 100, 2)} for k, v in now_.items()]
    return {"rows": rows, "as_of": f"{d1[:4]}-{d1[4:6]}-{d1[6:]}", "previous": f"{d0[:4]}-{d0[4:6]}-{d0[6:]}",
            "source": "한국은행 ECOS 매매기준율", "source_en": "Bank of Korea ECOS (base rate)", "frequency": "daily"}


def fx_exim():
    key = get_key("KOREAEXIM_API_KEY")
    got = []
    for back in range(0, 20):
        d = TODAY - timedelta(days=back)
        rows = json.loads(http("https://oapi.koreaexim.go.kr/site/program/financial/exchangeJSON?" + urlencode(dict(authkey=key, searchdate=d.strftime("%Y%m%d"), data="AP01")), secrets=(key,)))
        rates = {r["cur_unit"]: float(str(r["deal_bas_r"]).replace(",", "")) for r in rows if r.get("result") == 1 and r.get("cur_unit")}
        if {"USD", "CNH", "EUR"} <= set(rates):
            got.append((d, rates))
        if len(got) == 2:
            break
    if len(got) < 2:
        raise RuntimeError("수출입은행 환율 영업일 자료 부족")
    (d1, a), (d0, b) = got
    pair = lambda r: {"USD/KRW": r["USD"], "USD/CNY": r["USD"] / r["CNH"], "EUR/KRW": r["EUR"]}
    now_, prev = pair(a), pair(b)
    return {"rows": [{"pair": k, "value": round(v, 4 if k.endswith("CNY") else 2), "change": round((v / prev[k] - 1) * 100, 2)} for k, v in now_.items()],
            "as_of": d1.isoformat(), "previous": d0.isoformat(), "source": "한국수출입은행 매매기준율 (CNY 는 역외 CNH)", "source_en": "Korea Eximbank base rate", "frequency": "daily"}


# ---------------------------------------------------------------- 수출기상도 (한국 전체 반도체 수출, 관세청)
def _customs_total(key, prefix, start, end):
    raw = http("https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList?" + urlencode(dict(serviceKey=unquote(key), strtYymm=start, endYymm=end, hsSgn=prefix, numOfRows=10, pageNo=1)),
               secrets=(key, unquote(key)))
    root = ET.fromstring(raw.decode("utf-8-sig", "replace"))
    if root.findtext(".//resultCode") not in ("00", "0"):
        raise RuntimeError(f"관세청 응답 코드 {root.findtext('.//resultCode')}")
    for it in root.findall(".//items/item"):
        if (it.findtext("year") or "") == "총계":
            return int(float(it.findtext("expDlr") or 0))
    raise RuntimeError("총계 행 없음")


def weather():
    key = get_key("DATA_GO_KR")
    last = TODAY.replace(day=1) - timedelta(days=1)  # 지난달까지(당월 미집계)
    y, m = last.year, last.month
    rows = []
    for gid, prefixes in GROUPS.items():
        cur = prev = 0
        for p in prefixes:
            cur += _customs_total(key, p, f"{y}01", f"{y}{m:02d}")
            prev += _customs_total(key, p, f"{y - 1}01", f"{y - 1}{m:02d}")
            time.sleep(0.2)
        rows.append({"id": gid, "hs": prefixes, "exports_million_usd": round(cur / 1e6), "yoy": round((cur / prev - 1) * 100, 1) if prev else None,
                     "previous_million_usd": round(prev / 1e6)})
    return {"rows": rows, "period": f"{y}.01~{y}.{m:02d}", "compare": f"{y - 1}.01~{y - 1}.{m:02d}", "as_of": f"{y}-{m:02d}",
            "source": "관세청 품목별 국가별 수출입실적(전체 국가 합계)", "source_en": "Korea Customs Service trade statistics"}


# ---------------------------------------------------------------- 뉴스
def _rss(url, limit=3):
    root = ET.fromstring(http(url, headers={"User-Agent": "Mozilla/5.0 (AXPORT dashboard)"}))
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        src_el = it.find("source")
        source = (src_el.text or "").strip() if src_el is not None else ""
        if source and title.endswith(" - " + source):
            title = title[: -len(" - " + source)]
        pub = it.findtext("pubDate")
        try:
            pub = parsedate_to_datetime(pub).astimezone(timezone.utc).isoformat(timespec="minutes") if pub else None
        except Exception:
            pub = None
        link = (it.findtext("link") or "").strip()
        if not title or not re.match(r"^https?://", link):
            continue
        items.append({"title": title, "source": source, "url": link, "published_at": pub})
    items.sort(key=lambda x: x["published_at"] or "", reverse=True)
    return items[:limit]


def news():
    out = {}
    for lang, (q, hl, gl, ceid) in NEWS_QUERY.items():
        try:
            out[lang] = {"rows": _rss("https://news.google.com/rss/search?" + urlencode(dict(q=q + " when:7d", hl=hl, gl=gl, ceid=ceid))), "source": "Google 뉴스 RSS"}
        except RuntimeError as e:
            out[lang] = {"rows": [], "error": str(e)}
        if not out[lang]["rows"]:
            try:
                out[lang] = {"rows": _rss("https://www.wto.org/library/rss/latest_news_e.xml"), "source": "WTO news RSS"}
            except RuntimeError as e:
                out[lang] = {"rows": [], "error": str(e)}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", default="fx,weather,news")
    todo = set(ap.parse_args().only.split(","))
    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.is_file() else {}
    ok = True
    if "fx" in todo:
        try:
            data["fx"] = {**fx_ecos(), "fetched_at": now_iso()}
        except (RuntimeError, MissingKey) as e:
            print(f"  ECOS 실패 → 수출입은행 사용 ({e})")
            try:
                data["fx"] = {**fx_exim(), "fetched_at": now_iso()}
            except (RuntimeError, MissingKey) as e2:
                ok = False
                print(f"  환율 실패: {e2}")
        if data.get("fx"):
            print(f"  환율 {data['fx']['as_of']} ({data['fx']['source']}): " + ", ".join(f"{r['pair']} {r['value']} ({r['change']:+.2f}%)" for r in data["fx"]["rows"]))
    if "weather" in todo:
        try:
            data["weather"] = {**weather(), "fetched_at": now_iso()}
            print(f"  수출기상도 {data['weather']['period']}: " + ", ".join(f"{r['id']} {r['exports_million_usd']:,}M ({r['yoy']:+.1f}%)" for r in data["weather"]["rows"]))
        except (RuntimeError, MissingKey) as e:
            ok = False
            print(f"  수출기상도 실패: {e}")
    if "news" in todo:
        data["news"] = {**news(), "fetched_at": now_iso()}
        print("  뉴스: " + ", ".join(f"{k} {len(v['rows'])}건" for k, v in data["news"].items() if isinstance(v, dict)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")  # (2026-09-27) 임시 파일에 쓴 뒤 바꿔치기 → 서버가 반쯤 쓴 파일을 내보내지 않음
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, OUT)
    print(f"저장 {OUT.relative_to(ROOT)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
