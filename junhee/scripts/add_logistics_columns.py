# -*- coding: utf-8 -*-
"""가상 기업 샘플의 '물류' 시트에 예정도착일·실제도착일·운임(USD) 열을 추가해 새 버전 파일을 만든다 (2026-09-26 밤).

- 입력: junhee/data/samples/{한빛 v0.2, 대성 v0.2, 새벽 v0.1}.xlsx → 출력: 같은 폴더의 v0.3 / v0.3 / v0.2 (이전 파일은 ../_merge_backup 으로 이동)
- 값은 파일명+물류ID 를 시드로 한 고정 난수라 다시 돌려도 같다. 리드타임은 운송수단·도착지코드(권역)별 가정, 지연 확률은 회사·월별로 흔들리게 해
  납기 준수율 추세가 생기도록 했다. 운임은 순중량(kg) × 권역별 kg 단가 + 고정비(가정). 모두 가상 데이터.
- 새벽반도체는 검증용 결측을 일부러 넣고 '결측목록' 시트에 적는다 (예정도착일 빈칸 3, 실제도착일 빈칸 6, 운임 빈칸 4, 날짜 역전 1).
- '근거' 시트는 읽지도 출력하지도 않는다 (통째로 그대로 저장만 된다).
"""
import hashlib
import random
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]          # junhee/
PROJECT = ROOT.parent
SAMPLES = ROOT / "data" / "samples"
BACKUP = PROJECT.parent / "_merge_backup" / "2026-09-26" / "samples_before_logistics"
VERSIONS = {
    "한빛반도체_수출데이터_v0.2.xlsx": ("한빛반도체_수출데이터_v0.3.xlsx", "0.3"),
    "대성일렉트로닉스_수출데이터_v0.2.xlsx": ("대성일렉트로닉스_수출데이터_v0.3.xlsx", "0.3"),
    "새벽반도체_수출데이터_v0.1.xlsx": ("새벽반도체_수출데이터_v0.2.xlsx", "0.2"),
}
NEW_COLS = ["예정도착일", "실제도착일", "운임(USD)"]
# 도착지코드 → (권역, 항공 계획 리드타임 기본일, 해상 계획 리드타임 기본일, 항공 kg 단가 중심, 해상 kg 단가 중심)
REGION = {
    "FRA": ("유럽", 3, 34, 6.2, 0.85), "MUC": ("유럽", 3, 34, 6.2, 0.85), "AMS": ("유럽", 3, 33, 6.0, 0.85), "DEHAM": ("유럽", 3, 34, 6.2, 0.85), "NLRTM": ("유럽", 3, 33, 6.0, 0.85),
    "LAX": ("북미서부", 2, 15, 5.4, 0.6), "SEA": ("북미서부", 2, 14, 5.4, 0.6), "SFO": ("북미서부", 2, 15, 5.4, 0.6), "USLAX": ("북미서부", 2, 15, 5.4, 0.6), "USSEA": ("북미서부", 2, 14, 5.4, 0.6),
    "JFK": ("북미동부", 3, 30, 5.9, 0.75), "ORD": ("북미동부", 3, 30, 5.9, 0.75), "DFW": ("북미동부", 3, 28, 5.8, 0.7), "ATL": ("북미동부", 3, 30, 5.9, 0.75), "USNYC": ("북미동부", 3, 30, 5.9, 0.75),
    "YYZ": ("북미동부", 3, 31, 6.0, 0.75), "YVR": ("북미서부", 2, 15, 5.5, 0.6), "CAVAN": ("북미서부", 2, 15, 5.5, 0.6),
    "GDL": ("중남미", 3, 22, 6.4, 0.8), "MEX": ("중남미", 3, 22, 6.4, 0.8), "MXZLO": ("중남미", 3, 22, 6.4, 0.8), "MXMZO": ("중남미", 3, 22, 6.4, 0.8),
    "DEL": ("남아시아", 2, 22, 4.6, 0.55), "BOM": ("남아시아", 2, 21, 4.6, 0.55), "BLR": ("남아시아", 2, 23, 4.7, 0.55), "INNSA": ("남아시아", 2, 21, 4.6, 0.55),
    "HAN": ("동남아", 1, 8, 3.8, 0.4), "SGN": ("동남아", 1, 9, 3.8, 0.4), "VNHPH": ("동남아", 1, 8, 3.8, 0.4), "VNSGN": ("동남아", 1, 9, 3.8, 0.4),
    "CKG": ("중국", 1, 6, 3.6, 0.35), "SZX": ("중국", 1, 5, 3.6, 0.35), "PVG": ("중국", 1, 4, 3.6, 0.35), "CNSHA": ("중국", 1, 4, 3.6, 0.35), "CNSHK": ("중국", 1, 5, 3.6, 0.35),
}
DEFAULT_REGION = ("기타", 3, 20, 5.5, 0.7)


def rng_for(*parts):
    h = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return random.Random(int(h[:16], 16))


def month_late_prob(file_key, ym):
    """회사·월별 지연 확률 (0.04~0.24). 고정 시드의 완만한 흔들림 + 연말·여름 성수기 가산."""
    r = rng_for("late", file_key, ym[:4])          # 연 단위 기준값
    base = 0.07 + r.random() * 0.08
    m = int(ym[5:7])
    season = 0.06 if m in (11, 12) else 0.03 if m in (7, 8) else 0.0
    wobble = (rng_for("wobble", file_key, ym).random() - 0.5) * 0.08
    return max(0.04, min(0.24, base + season + wobble))


def find_header(ws, first):
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=10, values_only=True), start=1):
        if row and row[0] == first:
            return i
    raise RuntimeError(f"{ws.title}: 헤더 '{first}' 없음")


def main():
    BACKUP.mkdir(parents=True, exist_ok=True)
    for old_name, (new_name, tv) in VERSIONS.items():
        src = SAMPLES / old_name
        if not src.exists():
            print("건너뜀(없음):", old_name)
            continue
        file_key = new_name.split("_")[0]
        wb = openpyxl.load_workbook(src)          # 수식·서식 유지 (data_only=False)
        ws_l, ws_e = wb["물류"], wb["수출실적"]
        hl, he = find_header(ws_l, "물류ID"), find_header(ws_e, "실적ID")
        ehdr = [c.value for c in ws_e[he]]
        ei = {name: ehdr.index(name) for name in ("실적ID", "목적국", "순중량(kg)", "금액", "취소반품", "거래월")}
        actual = {}
        for row in ws_e.iter_rows(min_row=he + 1, values_only=True):
            if row and row[ei["실적ID"]]:
                actual[str(row[ei["실적ID"]]).strip()] = row
        lhdr = [c.value for c in ws_l[hl]]
        if "예정도착일" in lhdr:
            print("이미 추가됨:", old_name)
            continue
        li = {name: lhdr.index(name) for name in ("물류ID", "실적ID", "운송수단", "도착지코드", "선적일")}
        base_col = len(lhdr) + 1
        head_font, head_fill = ws_l.cell(hl, 1).font, ws_l.cell(hl, 1).fill
        for k, name in enumerate(NEW_COLS):
            c = ws_l.cell(hl, base_col + k, name)
            c.font = Font(name=head_font.name, bold=head_font.bold, size=head_font.size, color=head_font.color)
            c.fill = PatternFill(fill_type=head_fill.fill_type, fgColor=head_fill.fgColor, bgColor=head_fill.bgColor) if head_fill and head_fill.fill_type else PatternFill()
            ws_l.column_dimensions[get_column_letter(base_col + k)].width = 14
        # 새벽반도체 검증용 결측 (물류ID 기준)
        gaps = {}
        if file_key == "새벽반도체":
            gaps = {"L-SB-0021": "eta", "L-SB-0022": "eta", "L-SB-0023": "eta",
                    "L-SB-0060": "ata", "L-SB-0101": "ata", "L-SB-0150": "ata", "L-SB-0202": "ata", "L-SB-0260": "ata", "L-SB-0310": "ata",
                    "L-SB-0075": "fr", "L-SB-0130": "fr", "L-SB-0240": "fr", "L-SB-0333": "fr",
                    "L-SB-0180": "err"}
        stats = {"rows": 0, "tracked": 0, "ontime": 0, "fr": 0.0, "fa": 0.0, "blank": 0}
        gap_rows = []
        for ridx in range(hl + 1, ws_l.max_row + 1):
            row = [ws_l.cell(ridx, c).value for c in range(1, len(lhdr) + 1)]
            if not row[li["물류ID"]]:
                continue
            lid, rid = str(row[li["물류ID"]]).strip(), str(row[li["실적ID"]] or "").strip()
            mode, dcode, ship = str(row[li["운송수단"]] or "").strip(), str(row[li["도착지코드"]] or "").strip(), row[li["선적일"]]
            ex = actual.get(rid)
            r = rng_for(new_name, lid)
            region, air_d, sea_d, air_rate, sea_rate = REGION.get(dcode, DEFAULT_REGION)
            is_sea = mode == "해상" or (not mode and len(dcode) == 5)
            planned = (sea_d + r.choice([0, 1, 1, 2, 3])) if is_sea else (air_d + r.choice([0, 0, 1, 1, 2]))
            eta = ata = freight = None
            stats["rows"] += 1
            if isinstance(ship, datetime):
                eta = ship + timedelta(days=planned)
                ym = ship.strftime("%Y-%m")
                p_late = month_late_prob(file_key, ym) * (1.35 if is_sea else 1.0)
                if r.random() < p_late:
                    delay = r.choice([2, 3, 4, 5, 7, 9]) if is_sea else r.choice([1, 1, 2, 2, 3, 4])
                else:
                    delay = r.choice([-1, 0, 0, 0, 0, 0]) if not is_sea else r.choice([-2, -1, 0, 0, 0])
                ata = eta + timedelta(days=delay)
            cancelled = ex is not None and str(ex[ei["취소반품"]] or "").strip().upper() == "Y"
            weight = ex[ei["순중량(kg)"]] if ex is not None else None
            if cancelled:
                ata, freight = None, None                        # 취소 건: 실제 도착·운임 없음 (계획만 있었음)
            elif isinstance(weight, (int, float)) and weight > 0:
                noise = 0.9 + r.random() * 0.2
                if is_sea:
                    freight = round(max(280.0, weight * sea_rate * noise) + 250.0, 2)
                else:
                    freight = round(max(90.0, weight * air_rate * noise) + 45.0, 2)
            g = gaps.get(lid)
            if g == "eta":
                eta = None
            elif g == "ata":
                ata = None
            elif g == "fr":
                freight = None
            elif g == "err" and isinstance(ship, datetime):
                ata = ship - timedelta(days=3)                   # 날짜 역전 오류 (검증용)
            if g:
                gap_rows.append((ridx, lid, g))
            for k, v in enumerate((eta, ata, freight)):
                c = ws_l.cell(ridx, base_col + k, v)
                if isinstance(v, datetime):
                    c.number_format = "yyyy-mm-dd"
                elif isinstance(v, float):
                    c.number_format = "#,##0.00"
            if eta is not None and ata is not None and g != "err":
                stats["tracked"] += 1
                stats["ontime"] += ata <= eta
            if freight is not None and ex is not None and isinstance(ex[ei["금액"]], (int, float)) and ex[ei["금액"]] > 0:
                stats["fr"] += freight
                stats["fa"] += ex[ei["금액"]]
            stats["blank"] += (eta is None) + (ata is None) + (freight is None)
        # 기업정보: 버전·작성일·물류 설명 갱신
        ws_i = wb["기업정보"]
        for row in ws_i.iter_rows(min_row=1, max_row=ws_i.max_row):
            key = row[0].value
            if key == "template_version":
                row[1].value = tv
            elif key == "작성일":
                row[1].value = "2026-09-26"
            elif key == "4. 물류":
                row[1].value = "물류 시트의 출발지·도착지 코드(공항 IATA·항만 UN/LOCODE)와 선적일 → 운항·입출항 조회 조건 / 예정·실제 도착일 → 납기 준수율·리드타임 / 운임(USD) → 운송비 비중 (v0.3 추가, 가정값)"
            elif key == "제외":
                row[1].value = "원가·이익률, 허가·인증 충족 여부 — 이 파일에 넣지 않음 (납기·운임은 시연용 가정값으로 물류 시트에 추가)"
        # 새벽반도체: 결측목록 시트에 추가
        if gap_rows and "결측목록" in wb.sheetnames:
            ws_m = wb["결측목록"]
            eff = {"eta": ("예정도착일", "납기 준수율 계산에서 제외 (지연 판정 불가)"), "ata": ("실제도착일", "납기 준수율·리드타임 계산에서 제외 (미도착 또는 미기재)"),
                   "fr": ("운임(USD)", "운송비 비중 계산에서 제외"), "err": ("실제도착일 < 선적일 (날짜 역전)", "오류 행으로 표시하고 납기·리드타임 계산에서 제외")}
            col = {"eta": get_column_letter(base_col), "ata": get_column_letter(base_col + 1), "fr": get_column_letter(base_col + 2), "err": get_column_letter(base_col + 1)}
            start = ws_m.max_row + 1
            for k, (ridx, lid, g) in enumerate(gap_rows):
                vals = ("물류", "물류", f"{col[g]}{ridx}", lid, eff[g][0], eff[g][1], "행은 보존, 해당 계산만 제외하고 제외 건수 표시")
                for j, v in enumerate(vals, start=1):
                    ws_m.cell(start + k, j, v)
        dst = SAMPLES / new_name
        wb.save(dst)
        shutil.move(str(src), str(BACKUP / old_name))
        rate = stats["ontime"] / stats["tracked"] * 100 if stats["tracked"] else None
        fr = stats["fr"] / stats["fa"] * 100 if stats["fa"] else None
        print(f"{new_name}: 물류 {stats['rows']}행 · 추적 {stats['tracked']} · 정시 {rate:.1f}% · 운송비 비중 {fr:.2f}% · 빈칸 {stats['blank']} · 검증용 결측 {len(gap_rows)} → 이전 파일은 {BACKUP}")


if __name__ == "__main__":
    main()
