# -*- coding: utf-8 -*-
# v0.1 샘플 전용 — 2026-09-26 이후 사용하지 않음 (build_company_items.py 로 대체)
"""더미 엑셀 2개의 '수출실적'·'물류' 시트 맨 뒤에 2025-10 ~ 2026-09 월별 거래를 추가한다.

- 기존 행은 지우거나 옮기지 않는다 → '검증케이스' 시트의 엑셀 행 번호가 그대로 유지된다.
- '물류' 시트에는 '실제도착일' 열을 마지막에 추가한다 (기존 행은 빈칸).
- 두 회사의 흐름을 다르게 만든다.
    한빛반도체      : 규모 큼, 거래처 6곳 분산, 월 2% 완만한 성장, 납기 대부분 준수
    대성일렉트로닉스: 규모 작음, 중국 거래처 1곳 65% 집중, 월별 ±35% 변동, 단가 하락, 납기 지연 잦음
- 고정 시드라 다시 실행해도 같은 값. 이미 보강된 파일(ID 101 이상 존재)은 건너뛴다.
- 모든 수치는 시연용 가상값이다.

실행: python junhee/scripts/augment_samples.py
"""
import random
from datetime import date, timedelta
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "data" / "samples"
MONTHS = [(2025, 10), (2025, 11), (2025, 12)] + [(2026, m) for m in range(1, 10)]
ACTUAL_ARRIVAL_COL = "실제도착일"

PLANS = {
    "한빛반도체_수출데이터_v0.1.xlsx": {
        "prefix": "HB",
        "seed": 7,
        "base_month_usd": 40_000_000,
        "growth": 0.02,      # 월 성장률
        "noise": 0.03,       # 월 총액 잡음
        "price_drift": 0.0,  # 월별 단가 변화율
        "freight_ratio": 0.015,
        # (거래처ID, 국가, 제품ID, 단가USD, 비중, (출발지, 도착지, 수단, 운송일수))
        "lanes": [
            ("C-HB-01", "미국", "P-HB-001", 6.20, 0.30, ("부산항", "롱비치항", "해상", 16)),
            ("C-HB-02", "중국", "P-HB-004", 4.10, 0.22, ("부산항", "상하이항", "해상", 4)),
            ("C-HB-03", "영국", "P-HB-002", 9.30, 0.15, ("부산항", "사우샘프턴항", "해상", 35)),
            ("C-HB-04", "인도", "P-HB-005", 105.00, 0.12, ("인천공항", "뭄바이공항", "항공", 1)),
            ("C-HB-05", "캐나다", "P-HB-001", 6.35, 0.11, ("부산항", "밴쿠버항", "해상", 18)),
            ("C-HB-06", "멕시코", "P-HB-006", 1.85, 0.10, ("부산항", "만사니요항", "해상", 22)),
        ],
        "late": {((2026, 3), "C-HB-03"): 3},   # (연월, 거래처) → 지연 일수
        "skip": {},
        "spikes": {},
    },
    "대성일렉트로닉스_수출데이터_v0.1.xlsx": {
        "prefix": "DS",
        "seed": 11,
        "base_month_usd": 2_500_000,
        "growth": 0.0,
        "noise": 0.35,
        "price_drift": -0.012,
        "freight_ratio": 0.045,
        "lanes": [
            ("C-DS-01", "중국", "P-DS-001", 1.95, 0.65, ("부산항", "광저우항", "해상", 5)),
            ("C-DS-02", "미국", "P-DS-002", 3.60, 0.25, ("부산항", "롱비치항", "해상", 16)),
            ("C-DS-03", "인도", "P-DS-004", 2.40, 0.10, ("인천공항", "뭄바이공항", "항공", 1)),
        ],
        "late": {((2025, 11), "C-DS-01"): 5, ((2025, 12), "C-DS-01"): 6, ((2026, 2), "C-DS-01"): 9, ((2026, 3), "C-DS-02"): 3, ((2026, 5), "C-DS-02"): 4, ((2026, 6), "C-DS-01"): 8, ((2026, 8), "C-DS-01"): 7, ((2026, 9), "C-DS-01"): 4},
        "skip": {(2026, 4): {"C-DS-03"}, (2026, 7): {"C-DS-02", "C-DS-03"}},   # 그 달에 거래 없음
        "spikes": {(2026, 1): 0.55, (2026, 6): 1.9, (2026, 9): 0.7},           # 월 총액 배수
    },
}


def already_augmented(ws, prefix):
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row and isinstance(row[0], str) and row[0].startswith(f"R-{prefix}-1"):
            return True
    return False


def set_date(cell, d):
    cell.value = d
    cell.number_format = "YYYY-MM-DD"


def augment(path, plan):
    wb = load_workbook(path)
    ws_act, ws_log = wb["수출실적"], wb["물류"]
    if already_augmented(ws_act, plan["prefix"]):
        print(f"{path.name}: 이미 보강됨 — 건너뜀")
        return
    header = [c.value for c in ws_log[1]]
    if ACTUAL_ARRIVAL_COL not in header:
        from copy import copy

        ws_log.cell(1, len(header) + 1, ACTUAL_ARRIVAL_COL).font = copy(ws_log.cell(1, 1).font)
    rng = random.Random(plan["seed"])
    n_act, n_log = 100, 100
    for k, (y, m) in enumerate(MONTHS):
        total = plan["base_month_usd"] * (1 + plan["growth"]) ** k
        total *= 1 + plan["noise"] * rng.uniform(-1, 1)
        total *= plan["spikes"].get((y, m), 1.0)
        for cust, country, pid, price0, share, (src, dst, mode, days) in plan["lanes"]:
            if cust in plan["skip"].get((y, m), set()):
                continue
            price = round(price0 * (1 + plan["price_drift"]) ** k * rng.uniform(0.98, 1.02), 2)
            amount = total * share * rng.uniform(0.9, 1.1)
            qty = max(100, int(round(amount / price, -2)))
            amount = round(qty * price, 2)
            n_act += 1
            rid = f"R-{plan['prefix']}-{n_act:03d}"
            deal = date(y, m, rng.randint(3, 24))
            ws_act.append([rid, deal, pid, cust, country, qty, "EA", amount, "USD", "N"])
            set_date(ws_act.cell(ws_act.max_row, 2), deal)
            # 물류: 같은 거래의 출하 1건
            n_log += 1
            plan_dep = deal + timedelta(days=3)
            act_dep = plan_dep + timedelta(days=rng.choice([0, 0, 0, 1]))
            plan_arr = plan_dep + timedelta(days=days)
            late = plan["late"].get(((y, m), cust), 0)
            # 지연은 계획표(late)로만 정한다. 지연이 없는 달은 예정일 당일 또는 하루 일찍 도착.
            act_arr = plan_arr + timedelta(days=late) if late else plan_arr - timedelta(days=1 if rng.random() < 0.3 else 0)
            freight = round(amount * plan["freight_ratio"] * rng.uniform(0.9, 1.1), 2)
            ws_log.append([f"L-{plan['prefix']}-{n_log:03d}", rid, src, dst, mode, plan_dep, act_dep, plan_arr, freight, "USD", deal - timedelta(days=7), act_arr])
            r = ws_log.max_row
            for col in (6, 7, 8, 11, 12):
                set_date(ws_log.cell(r, col), ws_log.cell(r, col).value)
    wb.save(path)
    print(f"{path.name}: 수출실적 +{n_act - 100}행, 물류 +{n_log - 100}행 (2025-10~2026-09)")


def main():
    for name, plan in PLANS.items():
        augment(SAMPLES / name, plan)


if __name__ == "__main__":
    main()
