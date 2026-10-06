# -*- coding: utf-8 -*-
"""instance/contact_messages.jsonl (Contact Us 접수, 한 줄 = JSON 1건) → CSV.

로컬 서버에 모인 의견을 엑셀로 보기 위한 변환 스크립트. 개인정보(이메일)가 들어 있으므로 결과 CSV 는 저장소에 넣지 않는다
(기본 출력 위치 instance/ 는 .gitignore 대상).

실행: python junhee/scripts/export_contact.py [입력 jsonl] [출력 csv]
  기본 입력  instance/contact_messages.jsonl
  기본 출력  instance/contact_messages.csv (UTF-8 BOM, 엑셀에서 바로 열림)
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # test1/
FIELDS = ["ts", "type", "field", "name", "email", "message"]


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "instance" / "contact_messages.jsonl"
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".csv")
    if not src.exists():
        raise SystemExit(f"입력 파일 없음: {src}")
    rows, skipped = [], 0
    with open(src, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            rows.append({k: rec.get(k, "") for k in FIELDS})
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)}건 변환 (건너뜀 {skipped}) → {dst}")


if __name__ == "__main__":
    main()
