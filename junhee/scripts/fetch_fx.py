# -*- coding: utf-8 -*-
"""안정성 지표용 환율 시계열을 내려받아 junhee/data/raw/external/ 에 저장한다.

출처: 미 연준 H.10 (FRED). API 키가 필요 없다.
- EXKOUS : 원/달러 월평균 (검산용)
- DEX*   : 일별 환율. 원/외화 교차환율은 extract_summary.py 가 일별로 계산한 뒤 월평균을 낸다.
- 한국은행 ECOS 로 바꾸려면 ECOS API 키가 필요하다. 조원의 키 파일은 사용·복사하지 않는다.
- 내려받은 파일은 원본으로 취급하고 수정하지 않는다. 다시 받으면 덮어쓰되
  fetch_meta.json 에 내려받은 시각·URL·행수·기간을 남긴다.

실행: python junhee/scripts/fetch_fx.py
"""
import csv
import io
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "raw" / "external"
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="
SERIES = {
    "EXKOUS": {"file": "fred_EXKOUS_krw_per_usd_monthly.csv", "desc": "원/달러 월평균 (H.10)", "freq": "monthly"},
    "DEXKOUS": {"file": "fred_DEXKOUS_daily.csv", "desc": "KRW per USD 일별", "freq": "daily"},
    "DEXCHUS": {"file": "fred_DEXCHUS_daily.csv", "desc": "CNY per USD 일별", "freq": "daily"},
    "DEXJPUS": {"file": "fred_DEXJPUS_daily.csv", "desc": "JPY per USD 일별", "freq": "daily"},
    "DEXUSUK": {"file": "fred_DEXUSUK_daily.csv", "desc": "USD per GBP 일별", "freq": "daily"},
    "DEXUSEU": {"file": "fred_DEXUSEU_daily.csv", "desc": "USD per EUR 일별", "freq": "daily"},
    "DEXCAUS": {"file": "fred_DEXCAUS_daily.csv", "desc": "CAD per USD 일별", "freq": "daily"},
    "DEXMXUS": {"file": "fred_DEXMXUS_daily.csv", "desc": "MXN per USD 일별", "freq": "daily"},
    "DEXINUS": {"file": "fred_DEXINUS_daily.csv", "desc": "INR per USD 일별", "freq": "daily"},
    "DEXSZUS": {"file": "fred_DEXSZUS_daily.csv", "desc": "CHF per USD 일별", "freq": "daily"},
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (AXPORT junhee fetch_fx)"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = {"fetched_at": datetime.now().isoformat(timespec="seconds"), "series": {}}
    for sid, s in SERIES.items():
        url = FRED + sid
        try:
            text = fetch(url)
        except Exception as e:  # noqa: BLE001
            print(f"{sid}: FAIL {e!r}")
            meta["series"][sid] = {"ok": False, "error": repr(e), "url": url}
            continue
        rows = list(csv.reader(io.StringIO(text)))
        if not rows or rows[0][:2] != ["observation_date", sid]:
            print(f"{sid}: unexpected header {rows[:1]}")
            meta["series"][sid] = {"ok": False, "error": "unexpected header", "url": url}
            continue
        data = [r for r in rows[1:] if len(r) >= 2 and r[1] not in ("", ".")]
        out = OUT_DIR / s["file"]
        out.write_text(text, encoding="utf-8")
        meta["series"][sid] = {
            "ok": True, "url": url, "file": s["file"], "desc": s["desc"], "freq": s["freq"],
            "rows": len(data), "first": data[0][0], "last": data[-1][0],
        }
        print(f"{sid}: {len(data)} rows, {data[0][0]} ~ {data[-1][0]} -> {out.name}")
    (OUT_DIR / "fetch_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all(v.get("ok") for v in meta["series"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
