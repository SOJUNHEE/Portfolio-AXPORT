# (junhee) 2026-09-27 sanghyeob/analysis_suitability.py 에서 옮김. 바꾼 것: 패키지 import 경로·원본 자료 경로(junhee/data/raw)만. 계산 로직은 그대로.
"""Versioned decision-support policy, separate from observed/relative indices.

Missing evidence receives an explicitly disclosed policy midpoint, never a
fabricated observation. Thresholds are product policy, not a fitted prediction
or an official trade/credit/regulatory rating. This module performs no I/O.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
import math
import re

VERSION = 'suitability-reference-v1'
WEIGHTS = {'market': 40, 'price': 20, 'logistics': 10, 'stability': 10}
LABELS = {'market': '시장성', 'price': '가격·제품원가 여지',
          'logistics': '공급·출고 준비', 'stability': '시장 안정성'}
VALID = {'OBSERVED', 'OBSERVED_ZERO'}


def policy_snapshot():
    return {'version': VERSION, 'weights': dict(WEIGHTS), 'raw_max': 80,
            'formula': 'sum(weight * component_score / 100) / 80 * 100',
            'missing_score': 50, 'missing_is_observation': False,
            'coverage_formula': '평가한 항목의 배점 / 80 × 100 (기업 기재 포함)',
            'grade_thresholds': {'favorable': 70, 'conditional': 50, 'minimum_coverage': 50},
            'company_max_age_days': 29, 'fx_max_age_days': 7,
            'is_success_probability': False, 'regulation_is_separate_gate': True,
            'threshold_basis': '서비스의 초기 참고평가 정책; 수출성과로 검증한 예측모형이 아님',
            'rules': {
                'import_value': 'USD 0→0점, 100만→20점, 1천만→40점, 1억→60점, 10억→80점, 100억→100점; 로그 보간',
                'korea_exports': 'USD 0→0점, 10만→20점, 100만→40점, 1천만→60점, 1억→80점, 10억→100점; 로그 보간',
                'growth': '증가율 -20%→0점, 0%→50점, +20%→100점; 선형 보간·범위 제한',
                'planned_product_margin': '원값=(희망판매가−제품원가)/희망판매가 (동일 통화 환산); 0% 이하→0점, 10%→50점, 20% 이상→100점',
                'supply_fulfillment': '30일 공급가능량 / 희망수출수량 × 100; 100점 상한',
                'preparation_days': '7일 이하→100점, 30일 이상→0점; 사이 구간 선형 보간',
                'international_transport': '국제운송 경로·비용·인도기한 미평가: 정책 기준 50점',
                'market_cv_36m': '100 × (1 − min(36개월 변동계수, 1))',
                'market_drop_frequency': '100 × (1 − min(급감 빈도 / 0.5, 1))'}}


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        n = Decimal(str(value))
        return n if n.is_finite() and (n == 0 or -100 <= n.adjusted() <= 100) else None
    except (ValueError, InvalidOperation):
        return None


def _date(value):
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _clamp(value):
    return float(max(Decimal(0), min(Decimal(100), Decimal(str(value)))))


def _component(identifier, domain, label, weight, formula, reason):
    return {'id': identifier, 'domain': domain, 'label': label, 'weight': weight,
            'score': 50.0, 'contribution': weight / 2, 'status': 'ASSUMED',
            'value': None, 'unit': None, 'period': None, 'formula': formula,
            'reason': reason, 'evidence': []}


def _observed(component, value, score, unit, period, evidence, reason, company=False):
    try:
        displayed = float(value)
    except (ValueError, OverflowError):
        displayed = float('inf')
    if not math.isfinite(displayed):
        component['reason'] = '계산 결과가 표시 가능한 숫자 범위를 벗어나 해당 항목을 미평가했습니다.'
        return
    component.update(value=displayed, score=_clamp(score), unit=unit, period=period,
                     evidence=deepcopy(evidence), reason=reason,
                     status='COMPANY_REPORTED' if company else 'OBSERVED')
    component['contribution'] = component['weight'] * component['score'] / 100


def _metric(factor, identifier):
    items = [m for m in factor.get('metrics', []) if m.get('id') == identifier]
    return items[0] if len(items) == 1 else {}


def _valid_metric(metric):
    n = _number(metric.get('value'))
    refs = metric.get('evidence')
    return (n is not None and metric.get('status') in VALID
            and (metric['status'] != 'OBSERVED_ZERO' or n == 0)
            and isinstance(refs, list) and bool(refs)
            and all(isinstance(r, dict) and r.get('source_id') for r in refs))


def _fresh_period(period, as_of, annual=False):
    if not isinstance(period, str):
        return False
    if annual:
        years = re.findall(r'\b(20[0-9]{2})\b', period)
        return bool(years) and as_of.year - 2 <= max(map(int, years)) <= as_of.year - 1
    months = re.findall(r'(20[0-9]{2})-(0[1-9]|1[0-2])', period)
    indices = [int(y) * 12 + int(m) for y, m in months]
    return bool(indices) and 0 <= as_of.year * 12 + as_of.month - 1 - max(indices) <= 3


def _scale_amount(value, first):
    if value <= first:
        return 20 * value / first
    # Conversion follows positive, bounded Decimal validation above.
    return _clamp(20 + 20 * math.log10(float(value / first)))


def _public_components(factors, inputs):
    as_of = date.fromisoformat(inputs['as_of'])
    rules = policy_snapshot()['rules']
    specs = [('import_value', 'market', '대세계 수입시장 규모', 15, 'USD', 'import_value'),
             ('korea_exports', 'market', '한국의 해당국 수출규모', 5, 'USD', 'korea_exports'),
             ('import_ytd_yoy', 'market', '수입 누계 성장', 10, 'ratio', 'growth'),
             ('import_cagr3', 'market', '수입 3년 성장', 5, 'ratio', 'growth'),
             ('import_3m_yoy', 'market', '최근 3개월 수입 성장', 5, 'ratio', 'growth'),
             ('market_cv_36m', 'stability', '수입 변동성', 6, '비율', 'market_cv_36m'),
             ('market_drop_frequency', 'stability', '수입 급감 빈도', 4, '비율', 'market_drop_frequency')]
    result = []
    for identifier, domain, label, weight, unit, rule in specs:
        factor = factors.get(domain, {})
        metric = _metric(factor, identifier)
        component = _component(identifier, domain, label, weight, rules[rule],
                               '유효한 기간·단위·출처의 원지표가 없어 정책 기준 50점을 적용했습니다.')
        result.append(component)
        scope = factor.get('scope', {})
        if any(scope.get(k, inputs[k]) != inputs[k] for k in ('country', 'hs6', 'hs_edition', 'as_of')):
            component['reason'] = '원지표의 국가·품목·분류판·기준일이 분석 조건과 다릅니다.'
            continue
        if not _valid_metric(metric) or metric.get('unit') != unit:
            continue
        valuation_bases = {r.get('valuation_basis') for r in metric['evidence']
                           if r.get('valuation_basis') in ('CIF', 'FOB')}
        if len(valuation_bases) > 1:
            component['reason'] = '같은 지표의 관측 근거에서 CIF·FOB 평가기준 단절이 확인되어 미평가했습니다.'
            continue
        if not _fresh_period(metric.get('period'), as_of, identifier in ('import_value', 'korea_exports', 'import_cagr3')):
            component['reason'] = '원지표 기간이 허용 범위 밖이거나 미래 기간이어서 미평가했습니다.'
            continue
        value = _number(metric['value'])
        if identifier in ('import_value', 'korea_exports'):
            if value < 0:
                continue
            score = _scale_amount(value, Decimal(1000000 if identifier == 'import_value' else 100000))
        elif domain == 'market':
            if value < -1:
                continue
            score = _clamp(50 + 250 * value)
        else:
            months, pairs = _metric(factor, 'market_months'), _metric(factor, 'market_drop_pairs')
            if (not _valid_metric(months) or not _valid_metric(pairs)
                    or months.get('unit') != '개월/36개월' or pairs.get('unit') != '쌍/35쌍'
                    or months.get('period') != metric['period'] or pairs.get('period') != metric['period']
                    or months.get('value') != 36 or pairs.get('value') != 35 or value < 0
                    or (identifier == 'market_drop_frequency' and value > 1)):
                component['reason'] = '연속 36개월·유효 35쌍의 안정성 근거가 완비되지 않았습니다.'
                continue
            score = _clamp(100 * (1 - min(value / (Decimal('.5') if identifier == 'market_drop_frequency' else 1), 1)))
        _observed(component, value, score, unit, metric['period'], metric['evidence'],
                  '확인된 원지표에 고정된 서비스 참고기준을 적용했습니다. 국가 간 상대순위와 별개의 점수입니다.')
    return result


def _refs(company, row, fields):
    refs = []
    for field in fields:
        origin = row.get('_field_origins', {}).get(field, {})
        refs.append({'source_id': company.get('source', {}).get('id', 'company-upload'),
                     'sheet': origin.get('sheet', row.get('_sheet')),
                     'row': origin.get('row', row.get('_row')), 'cell': origin.get('cell'),
                     'field': origin.get('label', field), 'value': row.get(field)})
    return refs


def _rate(currency, fx, as_of):
    if currency == 'KRW':
        return Decimal(1), None, []
    metric = _metric(fx or {}, 'fx_reference_rate:' + currency)
    n, observed = _number(metric.get('value')), _date(metric.get('period'))
    if (not _valid_metric(metric) or metric.get('status') != 'OBSERVED'
            or metric.get('unit') != 'KRW/' + currency or n is None or n <= 0
            or observed is None or not 0 <= (as_of - observed).days <= 7):
        return None, None, []
    return n, observed, metric['evidence']


def _company_components(company, inputs, fx):
    rules = policy_snapshot()['rules']
    result = [_component(identifier, domain, label, weight, rules[identifier],
                         '필요한 기업 기재값이 없어 정책 기준 50점을 적용했습니다.')
              for identifier, domain, label, weight in (
                  ('planned_product_margin', 'price', '희망가격의 제품원가 차감 여지', 20),
                  ('supply_fulfillment', 'logistics', '30일 희망물량 충족', 6),
                  ('preparation_days', 'logistics', '출고 준비기간', 2),
                  ('international_transport', 'logistics', '국제운송 실행조건', 2))]
    price, supply, preparation, transport = result
    transport['reason'] = '경로·화물 수용·운임·최종 인도기한이 확인되지 않았습니다. 준비기간을 국제배송시간으로 사용하지 않습니다.'
    if company.get('source', {}).get('workbook_format') != 'company-simple-v2':
        for component in result[:3]:
            component['reason'] = '기존 상세양식의 개별 지표는 유지합니다. 이번 기업 계획 참고평가는 간편양식의 한 제품에 적용합니다.'
        return result
    sheets = company.get('sheets', {})
    products = sheets.get('제품정보', [])
    if (len(products) != 1 or str(products[0].get('HS코드', ''))[:6] != inputs['hs6']
            or products[0].get('HS버전') != inputs['hs_edition']):
        for component in result[:3]:
            component['reason'] = '기업 제품과 선택 HS·분류판이 유일하게 연결되지 않았습니다.'
        return result
    product = products[0]
    as_of, basis = date.fromisoformat(inputs['as_of']), _date(product.get('작성기준일'))
    if basis is None or not 0 <= (as_of - basis).days <= 29:
        for component in result[:3]:
            component['reason'] = '작성기준일이 미래이거나 작성 후 30일 적용기간이 지나 기업 계획을 미평가했습니다.'
        return result
    records = []
    for name in ('수출예정거래', '원가·비용', '재고·생산'):
        rows = sheets.get(name, [])
        if len(rows) > 1 or any(r.get('제품ID') != product.get('제품ID') for r in rows):
            for component in result[:3]:
                component['reason'] = '제품별 계획·원가·공급 기록이 중복되거나 연결되지 않았습니다.'
            return result
        records.append(rows[0] if rows else {})
    planned, cost, inventory = records
    if planned and planned.get('목적국') != inputs['country']:
        for component in result[:3]:
            component['reason'] = '수출계획의 대상국이 선택 국가와 다릅니다.'
        return result
    unit = product.get('판매단위')
    price_value, cost_value = _number(planned.get('희망판매단가')), _number(cost.get('제품원가(단위당)'))
    cc, pc = str(cost.get('통화') or ''), str(planned.get('통화') or '')
    if price_value is not None and price_value > 0 and cost_value is not None and cost_value >= 0:
        if (unit and planned.get('단위') == cost.get('원가단위') == unit
                and re.fullmatch('[A-Z]{3}', cc) and re.fullmatch('[A-Z]{3}', pc)):
            cost_rate, price_rate, fx_refs = Decimal(1), Decimal(1), []
            if cc != pc:
                cost_rate, cost_day, cost_refs = _rate(cc, fx, as_of)
                price_rate, price_day, price_refs = _rate(pc, fx, as_of)
                if cost_day and price_day and cost_day != price_day:
                    cost_rate = None
                fx_refs = cost_refs + price_refs
            if cost_rate is not None and price_rate is not None:
                margin = 1 - (cost_value * cost_rate) / (price_value * price_rate)
                refs = (_refs(company, planned, ['희망판매단가', '통화', '단위', '작성기준일'])
                        + _refs(company, cost, ['제품원가(단위당)', '통화', '원가단위']) + fx_refs)
                _observed(price, margin, _clamp(500 * margin), 'ratio', basis.isoformat(), refs,
                          '기업의 희망가격과 기재 제품원가 기준입니다. 미확인 운임·보험·관세·수수료 차감 전이며 순이익률이 아닙니다.'
                          + (' 분석일 이전 7일 이내 공표환율로 환산한 시나리오입니다.' if cc != pc else ' 동일 통화·판매단위로 계산했습니다.')
                          + (' 원가 0은 기업 기재값이므로 포함 범위를 확인해야 합니다.' if cost_value == 0 else ''), True)
            else:
                price['reason'] = '통화가 다르지만 같은 관측일의 최근 양수 환율이 없어 원가·희망가격 비교를 미평가했습니다.'
        else:
            price['reason'] = '원가와 희망가격의 통화·판매단위를 확인할 수 없어 미평가했습니다.'
    elif price_value is not None and price_value <= 0:
        price['reason'] = '희망판매단가가 0이므로 원가 차감 비율을 계산할 수 없습니다.'
    desired, available = _number(planned.get('수량')), _number(inventory.get('공급가능수량'))
    if (desired is not None and desired > 0 and available is not None and available >= 0
            and unit and planned.get('단위') == inventory.get('단위') == unit
            and inventory.get('공급계획시작일') == basis.isoformat()
            and _date(inventory.get('공급계획종료일')) is not None
            and (_date(inventory['공급계획종료일']) - basis).days == 29):
        ratio = available / desired
        _observed(supply, ratio, _clamp(100 * ratio), 'ratio', basis.isoformat(),
                  _refs(company, planned, ['수량', '단위']) + _refs(company, inventory, ['공급가능수량', '단위', '공급계획시작일', '공급계획종료일']),
                  f'기업 기재 30일 공급량 {available:g}{unit} / 희망수출량 {desired:g}{unit}. '
                  + ('희망물량을 충족합니다.' if ratio >= 1 else f'희망물량 대비 {desired - available:g}{unit} 부족합니다.')
                  + ' 확정 주문·예약·실제 생산능력 검증은 아닙니다.', True)
    elif desired == 0:
        supply['reason'] = '희망수출수량이 0이므로 공급 충족률을 계산할 수 없습니다.'
    days = _number(inventory.get('준비기간(일)'))
    if days is not None and days >= 0:
        _observed(preparation, days, _clamp((30 - days) / 23 * 100), '일', basis.isoformat(),
                  _refs(company, inventory, ['준비기간(일)']) + _refs(company, product, ['작성기준일']),
                  '주문 후 생산·검사·포장의 기재 준비기간입니다. 해외 운송·통관시간과 약정 납기 충족 여부는 포함하지 않습니다.', True)
    return result


def evaluate_suitability(company, inputs, factors, fx=None):
    """Always produce a disclosed reference score for validated analysis inputs."""
    indexed = {f['key']: f for f in factors}
    components = _public_components(indexed, inputs) + _company_components(company, inputs, fx)
    components.sort(key=lambda c: list(WEIGHTS).index(c['domain']))
    domains = []
    for key, maximum in WEIGHTS.items():
        selected = [c for c in components if c['domain'] == key]
        raw = sum(c['contribution'] for c in selected)
        observed = sum(c['weight'] for c in selected if c['status'] != 'ASSUMED')
        domains.append({'key': key, 'label': LABELS[key], 'raw_max': maximum, 'raw_score': raw,
                        'score': round(raw / maximum * 100, 1), 'coverage_pct': round(observed / maximum * 100, 1),
                        'components': deepcopy(selected)})
    raw = sum(c['contribution'] for c in components)
    score = round(raw / 80 * 100, 1)
    weight = sum(c['weight'] for c in components if c['status'] != 'ASSUMED')
    coverage = round(weight / 80 * 100, 1)
    grade_code, grade = ('EVIDENCE_LIMITED', '판단 근거 부족') if weight < 40 else (
        ('FAVORABLE', '조건부 검토 유망') if raw / 80 * 100 >= 70 else
        ('CONDITIONAL', '조건부 검토') if raw / 80 * 100 >= 50 else ('PREPARATION_NEEDED', '준비 보완 필요'))
    regulation_status = indexed.get('regulation', {}).get('gate_status') or 'REVIEW_REQUIRED'
    if regulation_status == 'BLOCKED':
        grade_code, grade = 'REGULATION_BLOCKED', '규제상 진행 제한'
    elif regulation_status == 'CONDITIONAL':
        grade_code, grade = 'REGULATION_CONDITIONAL', '규제 요건 확인 필요'
    observed = [c for c in components if c['status'] != 'ASSUMED']
    assumed = [c for c in components if c['status'] == 'ASSUMED']
    reasons = [f'{c["label"]}: {c["score"]:.1f}점 — {c["reason"]}'
               for c in sorted(observed, key=lambda c: -abs(c['contribution'] - c['weight'] / 2))[:4]]
    if not reasons:
        reasons = ['평가할 원지표가 없어 모든 항목에 정책 기준 50점을 적용했습니다. 기업의 적합성을 확인한 결과가 아닙니다.']
    gaps = [f'{c["label"]}: {c["reason"]}' for c in assumed]
    next_actions = ['제품 사양·거래처·최종사용자를 기준으로 규제·인증·허가 적용 여부를 확인하세요.']
    if regulation_status == 'BLOCKED':
        next_actions[0] = '규제상 진행 제한 상태입니다. 규제 탭의 제한 근거와 해소 요건을 먼저 확인하세요. 참고점수로 제한을 해제할 수 없습니다.'
    elif regulation_status == 'CONDITIONAL':
        next_actions[0] = '규제상 조건부 상태입니다. 규제 탭의 필수요건 충족 여부를 먼저 확인하세요.'
    if any(c['id'] == 'planned_product_margin' for c in assumed):
        next_actions.append('현재 기준의 원가·희망판매가·각 통화·판매단위를 확인하세요. 통화가 다르면 참고환율도 필요합니다.')
    else:
        next_actions.append('제품원가 외 운임·보험·관세·수수료를 확인해 실제 거래의 손익을 점검하세요.')
    s = next(c for c in components if c['id'] == 'supply_fulfillment')
    if s['status'] == 'ASSUMED':
        next_actions.append('유효한 작성기준일과 희망물량·30일 공급량·출고 준비기간을 확인하세요.')
    elif s['value'] < 1:
        next_actions.append('부족한 공급량의 추가 생산 일정 또는 수출물량 조정을 협의하세요.')
    next_actions.append('실제 국제운송 경로·화물 예약·도착기한을 확인하세요. 출고 준비기간만으로 납기를 판단하지 않습니다.')
    if any(c['domain'] in ('market', 'stability') for c in assumed):
        next_actions.append('미확보 시장지표의 API 응답·제공기간을 확인하고 자료가 갱신되면 재분석하세요.')
    return {'version': VERSION, 'state': 'reference',
            'scope': {k: inputs[k] for k in ('hs6', 'hs_edition', 'country', 'as_of')},
            'score': score, 'raw_score': raw, 'raw_max': 80, 'display_max': 100,
            'grade': grade, 'grade_code': grade_code, 'coverage_pct': coverage,
            'coverage_label': '근거 반영률 (기업 기재 포함)', 'observed_weight': weight, 'assumed_weight': 80 - weight,
            'external_weight': sum(c['weight'] for c in components if c['status'] == 'OBSERVED'),
            'company_weight': sum(c['weight'] for c in components if c['status'] == 'COMPANY_REPORTED'),
            'needs_regulation_review': True, 'regulation_status': regulation_status,
            'is_success_probability': False,
            'reason': f'참고 적합도 {score:.1f}/100 · {grade}. 배점 {weight}/80에 근거가 반영됐고 나머지는 정책 기준 50점입니다. 규제 검토는 별도입니다.',
            'reasons': reasons, 'assumptions': [
                '미평가 항목은 관측값을 만들지 않고 점수 계산에만 정책 기준 50점을 적용합니다. 유리·불리를 확인했다는 뜻이 아닙니다.',
                '근거 반영률은 평가한 배점 비중이며 기업 기재값도 포함합니다. 정확도·신뢰확률·수출 성공확률이 아닙니다.',
                '규모·성장·원가 여지·공급 준비의 기준선과 등급은 초기 서비스 정책이며 실제 수출성과로 검증한 모형이 아닙니다.',
                'HS6 시장통계는 개별 제품의 수요가 아니며, 가격은 순이익률·물류는 실제 국제배송 성과를 뜻하지 않습니다.',
                '수입시장 금액은 원기관 신고기준이며 국가별 CIF·FOB의 완전한 동일성을 검증한 값이 아닙니다.',
                '가격·공급 계획은 작성일 포함 30일만 반영합니다. 환산은 분석일 이전 7일 이내 같은 관측일의 참고환율을 사용합니다.',
            ], 'gaps': gaps, 'next_actions': next_actions, 'components': components, 'domains': domains}
