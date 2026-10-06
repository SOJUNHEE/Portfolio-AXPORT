# -*- coding: utf-8 -*-
"""한국은행 ECOS 에서 H.10 에 없는 통화의 원화 환율(일별)을 내려받는다.

키 취급
- 키는 환경변수 ECOS_API_KEY 에서만 읽는다. 파일에 저장하지 않고, 로그·메타에도 남기지 않는다.
- 실행 예 (PowerShell):  $env:ECOS_API_KEY = "<키>"; python junhee/scripts/fetch_fx_ecos.py
- 실행 예 (bash):        ECOS_API_KEY=<키> python junhee/scripts/fetch_fx_ecos.py

동작
1. 통계표 731Y001(주요국 통화의 대원화환율, 일별) 항목 목록을 받아 external/ecos_731Y001_items.json 에 저장한다.
2. TARGETS 의 키워드로 항목 코드를 찾고, 일별 값을 받아 external/ecos_<CCY>_daily.csv 로 저장한다
   (열: observation_date, <CCY>  — FRED 파일과 같은 형태. 값은 '원/통화단위', 단위(예: 100단위)는 메타에 기록).
3. fetch_meta.json 의 series 에 병합한다.

실행: python junhee/scripts/fetch_fx_ecos.py
"""
import csv
import json
import os
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "raw" / "external"
TABLE = "731Y001"
START = "20130101"
TARGETS = {  # CCY: 항목명에 들어갈 키워드 후보
    "COP": ["콜롬비아"],
    "KHR": ["캄보디아"],
    "VND": ["베트남"],
    "ZiG": ["짐바브웨"],
    "USD": ["미국달러", "미 달러", "미국 달러"],  # FRED 와 검산용
}


def get_key():
    key = os.environ.get("ECOS_API_KEY", "").strip()
    if not key:
        sys.exit("ECOS_API_KEY 환경변수가 비어 있습니다. 키는 파일에 넣지 말고 환경변수로만 넘기세요.")
    return key


def api(key, path):
    url = f"https://ecos.bok.or.kr/api/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (AXPORT junhee fetch_fx_ecos)"})
    raw = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
    doc = json.loads(raw)
    if "RESULT" in doc:  # 오류 응답
        raise RuntimeError(f"ECOS {doc['RESULT'].get('CODE')}: {doc['RESULT'].get('MESSAGE')}")
    return doc


def safe(s, key):
    return str(s).replace(key, "***")


def main():
    key = get_key()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta_path = OUT_DIR / "fetch_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {"series": {}}
    meta["ecos_fetched_at"] = datetime.now().isoformat(timespec="seconds")

    # 1) 항목 목록
    try:
        doc = api(key, f"StatisticItemList/{key}/json/kr/1/1000/{TABLE}")
        items = doc["StatisticItemList"]["row"]
    except Exception as e:  # noqa: BLE001
        sys.exit("항목 목록 조회 실패: " + safe(repr(e), key))
    (OUT_DIR / f"ecos_{TABLE}_items.json").write_text(
        json.dumps([{k: v for k, v in it.items()} for it in items], ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"{TABLE} items: {len(items)}")

    # 2) 통화별 수집
    end = date.today().strftime("%Y%m%d")
    ok_all = True
    for ccy, kws in TARGETS.items():
        hit = [it for it in items if any(k in it.get("ITEM_NAME", "") for k in kws)]
        sid = f"ECOS_{ccy}"
        if not hit:
            print(f"{ccy}: 항목 없음 ({'/'.join(kws)})")
            meta["series"][sid] = {"ok": False, "error": "item not found in " + TABLE, "keywords": kws}
            ok_all = False
            continue
        it = hit[0]
        code = it["ITEM_CODE"]
        rows_all = []
        page, size = 1, 10000
        try:
            while True:
                d = api(key, f"StatisticSearch/{key}/json/kr/{(page - 1) * size + 1}/{page * size}/{TABLE}/D/{START}/{end}/{code}")
                block = d["StatisticSearch"]
                rows_all.extend(block["row"])
                if len(rows_all) >= int(block["list_total_count"]) or not block["row"]:
                    break
                page += 1
        except Exception as e:  # noqa: BLE001
            print(f"{ccy}: 조회 실패 " + safe(repr(e), key))
            meta["series"][sid] = {"ok": False, "error": safe(repr(e), key), "item_code": code}
            ok_all = False
            continue
        data = []
        for r in rows_all:
            t, v = r.get("TIME", ""), r.get("DATA_VALUE", "")
            if len(t) == 8 and v not in ("", None):
                data.append((f"{t[:4]}-{t[4:6]}-{t[6:]}", float(v)))
        data.sort()
        out = OUT_DIR / f"ecos_{ccy}_daily.csv"
        with open(out, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["observation_date", ccy])
            w.writerows(data)
        meta["series"][sid] = {
            "ok": True, "source": "한국은행 ECOS", "table": TABLE, "item_code": code, "item_name": it.get("ITEM_NAME"),
            "unit": it.get("UNIT_NAME"), "file": out.name, "freq": "daily", "rows": len(data),
            "first": data[0][0] if data else None, "last": data[-1][0] if data else None,
        }
        print(f"{ccy}: {it.get('ITEM_NAME')} [{code}] unit={it.get('UNIT_NAME')} rows={len(data)} {data[0][0] if data else ''}~{data[-1][0] if data else ''} -> {out.name}")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
