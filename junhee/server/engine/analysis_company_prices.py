# (junhee) 2026-09-27 sanghyeob/analysis_company_prices.py 에서 옮김. 바꾼 것: 패키지 import 경로·원본 자료 경로(junhee/data/raw)만. 계산 로직은 그대로.
"""Pure calculation of a product-cost deduction from selected actual sales.

The caller selects the product, destination and reporting period first.
``transactions`` uses the existing price adapter's ``(row, amount, quantity)``
tuples. A dated cost must cover every selected transaction; this helper never
silently drops transactions, converts currency/units, or verifies documents.
"""

from datetime import date
from decimal import Decimal, DecimalException, localcontext
import math
import re

from .market_data import _decimal


NORMAL_TRANSACTIONS = {'', 'N', 'NO', 'FALSE', '0', '정상', '아니오'}
DISCLAIMER = '제품원가 차감률이며 운임·보험·관세·판매비 등 전체 비용을 반영한 이익률이 아닙니다.'


def _text(value):
    return '' if value is None else str(value).strip()


def _day(value):
    value = _text(value)
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        raise ValueError
    return date.fromisoformat(value)


def _number(value):
    result = int(value) if value == value.to_integral_value() else float(value)
    if not math.isfinite(result):
        raise ValueError
    return result


def evaluate_product_cost(cost_rows, transactions, product, currency, unit, *,
                          period=None, source_id='company-upload'):
    """Return an observation compatible with ``analysis_market_price._obs``.

    No dates: SCENARIO, assuming one declared unit cost throughout the period.
    Both dates: COMPANY_COST_BASIS only when all actual sale dates are covered.
    A partial/invalid period or even one uncovered sale makes the value null.
    ``원가근거`` is the company's statement, not authenticated evidence.
    """
    result = {'period': period, 'value': None, 'status': 'NOT_VERIFIED', 'evidence': []}

    def hold(reason, status='NOT_VERIFIED'):
        result.update(status=status, reason=reason + ' ' + DISCLAIMER)
        return result

    product, currency, unit = _text(product), _text(currency).upper(), _text(unit)
    if not product or not re.fullmatch(r'[A-Z]{3}', currency) or not unit:
        return hold('제품ID·통화·수량단위를 확인해야 합니다.')
    selected = [row for row in cost_rows if isinstance(row, dict) and _text(row.get('제품ID')) == product]
    if len(selected) != 1:
        return hold('선택 제품의 원가·비용 행이 정확히 1개 필요합니다. 누락·중복 원가는 합산하지 않습니다.')
    cost = selected[0]
    cost_unit = _text(cost.get('원가단위')) or _text(cost.get('단위'))
    basis = _text(cost.get('원가근거'))
    first_raw, last_raw = _text(cost.get('원가적용시작일')), _text(cost.get('원가적용종료일'))
    cost_ref = {'source_id': source_id, 'sheet': cost.get('_sheet', '원가·비용'), 'row': cost.get('_row'),
                'field': '제품원가(단위당)/통화/원가단위/원가적용시작일/원가적용종료일/원가근거',
                'product': product, 'currency': _text(cost.get('통화')).upper(), 'unit': cost_unit,
                'cost_start_date': first_raw or None, 'cost_end_date': last_raw or None,
                'cost_basis_statement': basis or None, 'basis_verification': 'COMPANY_DECLARED_UNVERIFIED'}
    result['evidence'].append(cost_ref)
    if _text(cost.get('통화')).upper() != currency or cost_unit != unit:
        return hold('원가와 거래의 통화·수량단위가 명시적으로 같아야 합니다. 환산을 추정하지 않습니다.')
    try:
        unit_cost = _decimal(cost.get('제품원가(단위당)'))
        cost_ref['value'] = _number(unit_cost)
    except (ValueError, OverflowError):
        return hold('제품원가는 0을 포함한 유한한 비음수여야 합니다. 빈칸을 0으로 처리하지 않습니다.')
    if bool(first_raw) != bool(last_raw):
        return hold('원가 적용기간은 시작일과 종료일을 모두 입력해야 합니다.', 'COST_PERIOD_INVALID')
    first = last = None
    if first_raw:
        try:
            first, last = _day(first_raw), _day(last_raw)
            if first > last:
                raise ValueError
        except ValueError:
            return hold('원가 적용기간의 유효한 날짜와 순서를 확인해야 합니다. 날짜를 추정하지 않습니다.', 'COST_PERIOD_INVALID')
    if not transactions:
        return hold('선택 기간의 실제 거래가 없어 제품원가 차감률을 계산하지 않습니다.')
    total_amount, total_quantity = Decimal(0), Decimal(0)
    dates, outside = [], []
    for transaction in transactions:
        if not isinstance(transaction, (list, tuple)) or len(transaction) != 3 or not isinstance(transaction[0], dict):
            return hold('실제 거래의 행·금액·수량 구조를 확인해야 합니다.')
        row, amount, quantity = transaction
        ref = {'source_id': source_id, 'sheet': row.get('_sheet', '수출실적'), 'row': row.get('_row'),
               'field': '제품ID/거래일/통화/단위/금액/수량/취소반품', 'transaction_date': _text(row.get('거래일')) or None}
        result['evidence'].append(ref)
        if (_text(row.get('제품ID')) != product or _text(row.get('통화')).upper() != currency
                or _text(row.get('단위')) != unit
                or _text(row.get('취소반품')).upper() not in NORMAL_TRANSACTIONS):
            return hold('선택 제품·통화·단위의 정상 실제 거래만 사용할 수 있습니다. 다른 거래를 섞지 않습니다.')
        try:
            day = _day(row.get('거래일'))
        except ValueError:
            return hold('실제 거래일을 확인할 수 없어 원가 적용 여부를 판단하지 않습니다.', 'COST_PERIOD_INVALID')
        try:
            amount, quantity = _decimal(amount), _decimal(quantity)
            if quantity <= 0:
                raise ValueError
            ref.update(amount=_number(amount), quantity=_number(quantity))
        except (ValueError, OverflowError):
            return hold('실제 거래의 금액은 비음수, 수량은 양수인 유한한 숫자여야 합니다.')
        dates.append(day)
        if first and not first <= day <= last:
            outside.append(day.isoformat())
        total_amount += amount
        total_quantity += quantity
    if outside:
        return hold('원가 적용기간 밖의 실제 거래가 포함되어 차감률 전체를 보류합니다. 일부 거래만 골라 계산하지 않습니다.',
                    'COST_PERIOD_MISMATCH')
    if total_amount <= 0:
        return hold('선택 거래의 합계 매출이 양수여야 차감률을 정의할 수 있습니다.')
    try:
        with localcontext() as context:
            context.prec = 40
            total_cost = unit_cost * total_quantity
            value = _number((total_amount - total_cost) / total_amount)
    except (DecimalException, ValueError, OverflowError):
        return hold('계산 결과의 유한한 숫자 범위를 확인하지 못했습니다.')
    result['evidence'].append({'kind': 'calculation_inputs', 'product': product, 'currency': currency, 'unit': unit,
                               'amount': _number(total_amount), 'quantity': _number(total_quantity),
                               'unit_cost': _number(unit_cost), 'transaction_count': len(transactions),
                               'transaction_start': min(dates).isoformat(), 'transaction_end': max(dates).isoformat()})
    declared = '원가근거는 기업 기재 내용이며 진위를 확인하지 않았습니다.' if basis else '원가근거가 미기재되어 있으며 기업 기재 원가의 진위를 확인하지 않았습니다.'
    result.update(value=value, status='COMPANY_COST_BASIS' if first else 'SCENARIO',
                  reason=('기업이 명시한 원가 적용기간에 선택 거래일이 모두 포함됩니다.' if first else
                          '원가 적용일이 없어 제공한 단위원가가 비교기간 전체에 동일하게 적용된다는 가정입니다. 날짜를 추정하지 않았습니다.')
                         + ' ' + declared + ' ' + DISCLAIMER)
    return result
