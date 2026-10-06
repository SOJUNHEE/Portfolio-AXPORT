# -*- coding: utf-8 -*-
"""junhee/data/raw 의 원본 복사본 목록을 junhee/MANIFEST.csv 로 만든다.

컬럼: path, folder, source, as_of, sha256, md5, size_bytes, file_mtime, license_note, usage_note
- 출처·이용조건은 파일명·파일 내부 메타데이터에서 확인 가능한 범위만 적고, 확인이 안 되면 '확인 필요' 로 둔다.
- 복사하지 않은 API 키 파일은 해시 없이 '복사 제외' 로만 기록한다.

실행: python junhee/scripts/build_manifest.py
"""
import csv
import hashlib
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "MANIFEST.csv"


def hashes(path):
    h1, h2 = hashlib.sha256(), hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h1.update(chunk)
            h2.update(chunk)
    return h1.hexdigest(), h2.hexdigest()


def yyyymmdd(s):
    return f"{s[:4]}-{s[4:6]}-{s[6:]}"


def describe(rel: Path):
    """파일명 패턴별 출처·기준일·이용조건. (source, as_of, license_note, usage_note)"""
    n = rel.name
    folder = rel.parts[0]
    if n == "ITA_consolidated_screening_list.csv":
        return ("미국 상무부 ITA Consolidated Screening List (trade.gov)", "최신 등재 2026-03-26 · 파일 확보 2026-09-22",
                "미국 연방정부 공개자료(퍼블릭 도메인으로 알려짐, 이용 전 재확인)", "규제: CSL 총 건수·기준일")
    if n.startswith("대한무역투자진흥공사_국별 대세계 수입규제 현황"):
        return ("KOTRA 국별 대세계 수입규제 현황 (공공데이터포털)", yyyymmdd(re.search(r"_(\d{8})", n).group(1)),
                "공공데이터포털 이용조건(공공누리 유형) 확인 필요", "규제: 미국의 대한국 수입규제 건수, HS 854231 포함 여부")
    if n.startswith("HSK연계표"):
        return ("전략물자 HSK 연계표 (전략물자관리원 추정)", yyyymmdd(re.search(r"_(\d{8})", n).group(1)),
                "이용조건 확인 필요", "규제: HS 854231 하위 HSK 코드의 통제번호 연계 확인(판정 아님)")
    if n.startswith("[별표") or "전략물자수출입고시" in n:
        return ("산업통상자원부 전략물자수출입고시 일부개정(안) 별표·고시문", "미확인(고시문 내 확인 필요)",
                "정부 고시문(공공저작물). 원문 대조 미완료", "규제: 원문 확보만, 이번 단계 파싱·판정 미적용")
    if n.startswith("WSTS-Historical-Billings-Report"):
        extra = " · test1_marketability 와 동일 파일(MD5 일치)" if folder == "test1_stablity" else ""
        return ("WSTS Historical Billings Report (Jul 2026)", "2026-07 (월간)",
                "© WSTS, Inc. 저작권 자료 — 내부 시연용, 재배포 금지",
                ("시장성: 세계 반도체 월간 출하액·전년동월비" if folder == "test1_marketability" else "안정성: 전용 자료 아님 → 자료 부족 처리") + extra)
    if n.startswith("(통계)") and "수출입물가지수" in n:
        m = re.search(r"(\d{4})년(\d{2})월", n)
        return ("한국은행 수출입물가지수·무역지수(잠정) 통계표", f"{m.group(1)}-{m.group(2)} (잠정)",
                "한국은행 공표자료(공공누리 유형 확인 필요)", "가격: 수출물가지수(컴퓨터·전자·광학기기; 반도체 세부지수 미포함)")
    if n.endswith(".hwpx") and "운송비용 현황" in n:
        return ("관세청 보도자료 '2026년 8월 수출입 운송비용 현황' (2026-09-15 배포)", "2026-08 (신고수리일 기준, 잠정)",
                "보도자료(공공누리 유형 확인 필요)", "물류: 한국→미국 서·동부 해상수출 컨테이너 평균 운송비용(천원/2TEU)")
    if folder == "external" and n.startswith("fred_EXKOUS"):
        return ("미 연준 H.10 원/달러 월평균 환율 (FRED 시리즈 EXKOUS), fetch_fx.py 로 수집",
                "external/fetch_meta.json 의 last 값 참조", "FRED 이용약관(공개 데이터, 출처 표기)", "안정성: 검산용 월평균")
    m = re.fullmatch(r"fred_(DEX[A-Z]+)_daily\.csv", n)
    if folder == "external" and m:
        return (f"미 연준 H.10 일별 환율 (FRED 시리즈 {m.group(1)}), fetch_fx.py 로 수집",
                "external/fetch_meta.json 의 last 값 참조", "FRED 이용약관(공개 데이터, 출처 표기)", "안정성: 원/외화 교차환율 월평균 → 최근 12개월 평균 월간 변동폭·과거 10년 3분위 등급")
    if folder == "external" and n == "fetch_meta.json":
        return ("fetch_fx.py 수집 기록", "-", "-", "수집 시각·URL·기간 기록")
    if n == "tariff-actions-metadata.csv":
        return ("WTO 관세조치(tariff actions) 데이터 메타데이터", "-", "WTO 데이터 이용약관 확인 필요", "가격: 컬럼 정의 참조")
    m = re.fullmatch(r"([CU]\d{3})_C410\.csv", n)
    if m:
        return (f"WTO 관세조치 데이터 — reporter {m.group(1)} → partner C410(한국), HS6", "파일 내 year_dt 최신값 참조",
                "WTO 데이터 이용약관 확인 필요", "가격: HS 854231 best_avlbl(적용관세율)·imports(수입액)" + (" — 대시보드 사용" if m.group(1) == "C840" else " — 예비"))
    return ("확인 필요", "확인 필요", "확인 필요", "")


def main():
    rows = []
    for p in sorted(RAW.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(RAW)
        sha, md = hashes(p)
        source, as_of, lic, usage = describe(rel)
        rows.append({
            "path": str(rel).replace("\\", "/"),
            "folder": rel.parts[0],
            "source": source,
            "as_of": as_of,
            "sha256": sha,
            "md5": md,
            "size_bytes": p.stat().st_size,
            "file_mtime": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
            "license_note": lic,
            "usage_note": usage,
        })
    rows.append({
        "path": "(복사 제외) test1_data/개인 api 키.txt",
        "folder": "-",
        "source": "개인 API 키",
        "as_of": "-",
        "sha256": "",
        "md5": "",
        "size_bytes": "",
        "file_mtime": "",
        "license_note": "비밀정보",
        "usage_note": "복사·커밋 금지 (.gitignore: '*api 키*.txt', '*.env')",
    })
    with open(OUT, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"MANIFEST.csv: {len(rows)} rows -> {OUT}")


if __name__ == "__main__":
    main()
