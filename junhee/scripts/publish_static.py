# -*- coding: utf-8 -*-
"""junhee/data/processed/ 의 JSON 과 샘플 엑셀을 static/ 으로 복사한다 (app.py 수정 없이 Flask 기본 /static 경로로 서빙).

- dashboard_summary.json → static/data/dashboard_summary.json (스키마 필수 키 검증)
- companies/*.json + index.json (schema handoff-v1) → static/data/companies/
- data/samples/*.xlsx, data/templates/*.xlsx(업로드 양식) → static/samples/
복사 전 검증 (실패하면 아무것도 복사하지 않는다):
  · 모든 item 의 status 가 허용 값(확인됨 / 자료 부족 / 미확인 / 검색 결과 없음 / 검색 불가)인지
  · 실제 기업명 문자열(삼성·하이닉스·samsung·hynix)이 JSON 에 없는지
  · index.json 의 file_sha256 이 회사 JSON 및 실제 엑셀 파일과 같은지

실행: python junhee/scripts/publish_static.py
"""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]           # junhee/
PROJECT = ROOT.parent                                 # test1/
SRC = ROOT / "data" / "processed" / "dashboard_summary.json"
DST_DIR = PROJECT / "static" / "data"
DST = DST_DIR / "dashboard_summary.json"
COMPANIES_SRC = ROOT / "data" / "processed" / "companies"
COMPANIES_DST = DST_DIR / "companies"
SAMPLES_SRC = ROOT / "data" / "samples"
SAMPLES_DST = PROJECT / "static" / "samples"
TEMPLATES_SRC = ROOT / "data" / "templates"   # 업로드 양식 엑셀 (make_upload_template.py) → static/samples/

REQUIRED = {"key", "headline", "note", "state", "source", "as_of", "data_class"}
KEYS = ["regulation", "market", "price", "logistics", "stability"]
ITEM_STATUS = ("확인됨", "자료 부족", "미확인", "검색 결과 없음", "검색 불가")
ITEM_KEYS = {"key", "label", "status", "value", "unit", "period", "as_of", "source", "basis", "note"}
REAL_NAME_PATTERNS = ("삼성", "하이닉스", "samsung", "hynix")
AREAS = ("regulation", "market", "price", "logistics", "stability")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_summary(doc):
    items = doc.get("items")
    assert isinstance(items, list) and len(items) == 5, "items 5개가 아님"
    assert [it["key"] for it in items] == KEYS, "항목 순서/키 불일치"
    for it in items:
        missing = REQUIRED - set(it)
        assert not missing, f"{it.get('key')}: 누락 키 {missing}"
        assert it["state"] in ("ok", "insufficient"), f"{it['key']}: state 값 오류"
        assert it["data_class"] in ("실제자료", "가상데이터", "가정값"), f"{it['key']}: data_class 값 오류"
        if it["state"] == "insufficient":
            assert not any(ch.isdigit() for ch in it["headline"]), f"{it['key']}: 자료 부족인데 headline 에 숫자"
            assert "자료 부족" in it["headline"], f"{it['key']}: 자료 부족 문구 없음"


def validate_companies():
    """handoff-v1 회사 JSON 검증. 반환: (index doc, 검증한 회사 파일 목록)"""
    idx_path = COMPANIES_SRC / "index.json"
    if not idx_path.exists():
        print("skip: companies/index.json 없음")
        return None, []
    index = json.loads(idx_path.read_text(encoding="utf-8"))
    assert index.get("schema") == "handoff-v1", "index.json schema 가 handoff-v1 이 아님"
    files = []
    for c in index["companies"]:
        f = COMPANIES_SRC / f"{c['company_id']}.json"
        assert f.exists(), f"{f.name} 없음"
        text = f.read_text(encoding="utf-8")
        low = text.lower()
        for pat in REAL_NAME_PATTERNS:
            assert pat.lower() not in low, f"{f.name}: 실제 기업명 문자열 '{pat}' 포함 — 복사 중단"
        d = json.loads(text)
        assert d["schema"] == "handoff-v1", f"{f.name}: schema 불일치"
        assert d["data_class"] == "가상 데이터 · 시연용", f"{f.name}: data_class 값 오류"
        assert d["file_sha256"] == c["file_sha256"], f"{c['company_id']}: index 와 회사 JSON 의 sha 불일치"
        sample = SAMPLES_SRC / c["file_name"]
        assert sample.exists(), f"{c['file_name']}: 샘플 엑셀 없음"
        assert sha256(sample) == c["file_sha256"], f"{c['file_name']}: 엑셀이 바뀌었는데 JSON 이 갱신되지 않음 (build_company_items.py 재실행)"
        sc = d.get("score") or {}
        assert sc.get("mode") in ("demo", "hidden") or sc.get("status") == "미확인", f"{f.name}: score 블록 형식 오류"
        for country, block in (sc.get("per_country") or {}).items():
            for fct in block.get("factors", []):
                assert fct["state"] in ("ok", "insufficient"), f"{f.name}/{country}/{fct['key']}: 점수 state 오류"
                if fct["state"] == "insufficient":
                    assert fct["score"] is None, f"{f.name}/{country}/{fct['key']}: 자료 부족인데 점수가 있음"
            assert block["overall"]["state"] in ("ok", "insufficient"), f"{f.name}/{country}: 종합 state 오류"
        n_items = 0
        for country, areas in d["per_country"].items():
            for area in AREAS:
                assert area in areas, f"{f.name}/{country}: 영역 {area} 없음"
                for it in areas[area]:
                    missing = ITEM_KEYS - set(it)
                    assert not missing, f"{f.name}/{country}/{area}/{it.get('key')}: 누락 키 {missing}"
                    assert it["status"] in ITEM_STATUS, f"{f.name}/{country}/{area}/{it['key']}: status 값 오류 '{it['status']}'"
                    if it["status"] != "확인됨":
                        assert it["value"] in (None, 0) or it["key"] in ("export_control_candidates", "csl_search", "import_regulation_records"), \
                            f"{f.name}/{country}/{area}/{it['key']}: status 가 {it['status']} 인데 value 가 있음"
                    n_items += 1
        files.append((f, n_items))
    for pat in REAL_NAME_PATTERNS:
        assert pat.lower() not in idx_path.read_text(encoding="utf-8").lower(), f"index.json: 실제 기업명 문자열 '{pat}' 포함"
    return index, files


def copy_tree(src, dst, pattern, keep_only=None):
    """src 의 pattern 파일을 dst 로 복사한다. keep_only 가 있으면 dst 에서 그 목록에 없는 같은 패턴 파일은 지운다."""
    if not src.exists():
        print(f"skip: {src.relative_to(PROJECT)} 없음")
        return 0
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    names = set()
    for p in sorted(src.glob(pattern)):
        if p.is_file():
            shutil.copyfile(p, dst / p.name)
            names.add(p.name)
            n += 1
    if keep_only is not None:
        for p in dst.glob(pattern):
            if p.name not in keep_only:
                p.unlink()
                print(f"removed stale: {p.relative_to(PROJECT)}")
    print(f"copied {n} files {src.relative_to(PROJECT)} -> {dst.relative_to(PROJECT)}")
    return n


def main():
    doc = json.loads(SRC.read_text(encoding="utf-8"))
    validate_summary(doc)
    index, files = validate_companies()  # 검증 실패 시 여기서 AssertionError 로 멈추고 아무것도 복사하지 않는다
    DST_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC, DST)
    print(f"copied {SRC.relative_to(PROJECT)} -> {DST.relative_to(PROJECT)} ({DST.stat().st_size} bytes)")
    if index:
        keep = {f.name for f, _ in files} | {"index.json"}
        copy_tree(COMPANIES_SRC, COMPANIES_DST, "*.json", keep_only=keep)
        templates = {p.name for p in TEMPLATES_SRC.glob("*.xlsx")} if TEMPLATES_SRC.exists() else set()
        copy_tree(SAMPLES_SRC, SAMPLES_DST, "*.xlsx", keep_only={c["file_name"] for c in index["companies"]} | templates)
        copy_tree(TEMPLATES_SRC, SAMPLES_DST, "*.xlsx")
        for f, n in files:
            print(f"  validated {f.name}: {n} items")


if __name__ == "__main__":
    main()
