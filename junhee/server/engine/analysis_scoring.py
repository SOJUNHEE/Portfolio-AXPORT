# (junhee) 2026-09-27 sanghyeob/analysis_scoring.py 에서 옮김. 바꾼 것: 패키지 import 경로·원본 자료 경로(junhee/data/raw)만. 계산 로직은 그대로.
"""Pure, auditable relative reference scores for an already frozen cohort.

This module does not select countries or periods, fill gaps, fetch data, or make
export decisions. It rechecks the supplied cohort and ranks exact raw amounts.
UNKNOWN import valuation is retained as a limitation, not claimed comparable.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
from hashlib import sha256
import json
import math
import re


VERSION = 'relative-evidence-v1'
POLICY_VERSION = 'comparison-policy-v1'
VALID = {'OBSERVED', 'OBSERVED_ZERO'}
REPORTERS = {'US': 842, 'CN': 156, 'JP': 392, 'DE': 276, 'VN': 704}
SPECS = {
    'market': (
        ('import_value', '대세계 연간 수입시장 규모', 15, 'HIGHER'),
        ('korea_exports', '한국의 해당국 연간 수출액', 5, 'HIGHER'),
        ('import_ytd_yoy', '수입액 누계 전년동기 증가율', 10, 'HIGHER'),
        ('import_cagr3', '수입액 3년 CAGR', 5, 'HIGHER'),
        ('import_3m_yoy', '최근 3개월 수입액 전년동기 증가율', 5, 'HIGHER'),
    ),
    'stability': (
        ('market_cv_36m', '36개월 월간 수입 변동계수', 6, 'LOWER'),
        ('market_drop_frequency', '급감 빈도(유효 쌍 기준)', 4, 'LOWER'),
    ),
}
METHOD = '원관측의 정확값으로 평균 동점 순위를 계산합니다. 유리한 방향의 순위 R=(rank−1)/(N−1), 기여도=배점×R입니다.'
LIMITATIONS = (
    '원기관 신고수입액 기준 상대 참고지수; 국가별 CIF/FOB 완전동일검증 아님.',
    '포함 국가와 공통 기간에 한정한 상대값이며 성공확률·품질 검증·등급 기준이 아닙니다.',
    '시장성과 안정성만 계산하며 가격·물류·종합점수를 대신하거나 규제 검토를 상쇄하지 않습니다.',
    '성장률의 기저효과, 계절성, 추세 및 기업별 적합성을 제거한 지표가 아닙니다. FX와 WSTS는 점수에서 제외합니다.',
)


class _Invalid(ValueError):
    pass


def rubric_snapshot():
    """Return a fresh serializable copy of the fixed, limited methodology."""
    return {
        'version': VERSION, 'approved_domains': ['market', 'stability'],
        'method': METHOD, 'rank_formula': '(rank - 1) / (N - 1)',
        'ties': 'average_rank', 'all_tied_ratio': 0.5, 'minimum_countries': 2,
        'zero_override': ['import_value', 'korea_exports'],
        'domains': {domain: {'raw_max': sum(s[2] for s in specs),
                    'components': [{'id': s[0], 'label': s[1], 'weight': s[2], 'direction': s[3]}
                                   for s in specs]} for domain, specs in SPECS.items()},
        'aggregate_enabled': False, 'is_success_probability': False,
        'regulation_is_separate_gate': True, 'limitations': list(LIMITATIONS),
    }


def _month(month, offset):
    parsed = date.fromisoformat(month + '-01')
    index = parsed.year * 12 + parsed.month - 1 + offset
    return f'{index // 12:04d}-{index % 12 + 1:02d}'


def _decimal(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise _Invalid('숫자가 없거나 숫자 형식이 아닙니다.')
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise _Invalid('숫자 형식이 올바르지 않습니다.') from None
    # Real observations are small; this also bounds malformed exponent inputs.
    if not number.is_finite() or abs(number.adjusted()) > 1000:
        raise _Invalid('유한한 계산 범위의 숫자가 아닙니다.')
    return number


def _canonical(number):
    if number == 0:
        return '0'
    return format(number, 'f').rstrip('0').rstrip('.') if number.as_tuple().exponent < 0 else format(number, 'f')


def _ratio(value):
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}


def _display(value, root=None):
    with localcontext() as context:
        context.prec = 50
        number = Decimal(value.numerator) / Decimal(value.denominator)
        if root == 2:
            number = number.sqrt()
        elif root == 3:
            number = number ** (Decimal(1) / 3) - 1 if number else Decimal(-1)
        result = float(number)
    if not math.isfinite(result):
        raise _Invalid('표시 가능한 수치 범위를 벗어났습니다.')
    return int(number) if root is None and number == number.to_integral_value() else result


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _unique_evidence(observations):
    indexed = {}
    for row in observations:
        for ref in row['evidence']:
            indexed[_canonical_json(ref)] = deepcopy(ref)
    return [indexed[key] for key in sorted(indexed)]


def _scope(inputs, comparison, domain):
    if not isinstance(inputs, dict) or not isinstance(comparison, dict):
        raise _Invalid('분석 조건 또는 비교군 형식이 올바르지 않습니다.')
    if inputs.get('hs_edition') != 'HS2022' or not re.fullmatch(r'[0-9]{6}', str(inputs.get('hs6', ''))):
        raise _Invalid('HS2022 6자리 품목 범위를 확인할 수 없습니다.')
    if inputs.get('country') is not None and inputs['country'] not in REPORTERS:
        raise _Invalid('선택 국가가 승인된 후보국 범위가 아닙니다.')
    if comparison.get('policy_version') != POLICY_VERSION:
        raise _Invalid('공통 비교기간의 정책 판본을 확인할 수 없습니다.')
    try:
        as_of = date.fromisoformat(inputs['as_of'])
        if inputs['as_of'] != as_of.isoformat():
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise _Invalid('분석 기준일이 올바르지 않습니다.') from None
    return {'hs6': inputs['hs6'], 'hs_edition': 'HS2022', 'as_of': as_of.isoformat(),
            'policy_version': POLICY_VERSION,
            'end_month': comparison.get('end_month'),
            'annual_year': comparison.get('annual_year') if domain == 'market' else None}


def _members(comparison):
    included, rows, excluded = comparison.get('included'), comparison.get('countries'), comparison.get('excluded')
    if not all(isinstance(value, list) for value in (included, rows, excluded)):
        raise _Invalid('비교군의 포함·제외 목록이 없습니다.')
    if any(not isinstance(c, str) or c not in REPORTERS for c in included) or len(set(included)) != len(included):
        raise _Invalid('포함 국가가 중복되거나 후보국 범위가 아닙니다.')
    by_country = {}
    for row in rows:
        if not isinstance(row, dict) or row.get('country') not in REPORTERS or not isinstance(row.get('eligible'), bool):
            raise _Invalid('국가별 비교 가능 여부의 형식이 올바르지 않습니다.')
        if row['country'] in by_country:
            raise _Invalid('국가별 비교 행이 중복되었습니다.')
        by_country[row['country']] = row
    if set(by_country) != set(REPORTERS):
        raise _Invalid('승인된 5개 후보국의 포함·제외 행이 모두 있어야 합니다.')
    if set(included) != {c for c, r in by_country.items() if r['eligible']}:
        raise _Invalid('포함 국가와 비교 가능 행이 일치하지 않습니다. 재순위하지 않습니다.')
    codes = [row.get('country') if isinstance(row, dict) else None for row in excluded]
    if any(not isinstance(c, str) for c in codes) or len(set(codes)) != len(codes):
        raise _Invalid('제외 국가가 중복되거나 형식이 올바르지 않습니다.')
    if set(codes) != {c for c, r in by_country.items() if not r['eligible']}:
        raise _Invalid('제외 국가와 비교 불가 행이 일치하지 않습니다.')
    return by_country


def _window(scope, comparison, domain):
    end = scope['end_month']
    try:
        if not isinstance(end, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}', end):
            raise ValueError
        parsed = date.fromisoformat(end + '-01')
        latest = _month(scope['as_of'][:7], -1)
        lag = (int(latest[:4]) - parsed.year) * 12 + int(latest[5:]) - parsed.month
        supplied_lag = comparison.get('lag_months')
        if isinstance(supplied_lag, bool) or not isinstance(supplied_lag, int) or supplied_lag != lag or not 0 <= lag <= 3:
            raise ValueError
        if comparison.get('latest_completed_month', latest) != latest:
            raise ValueError
    except (TypeError, ValueError):
        raise _Invalid('월별 비교기간이 완료 월 또는 허용된 0~3개월 지연 범위와 다릅니다.') from None
    if not isinstance(comparison.get('window_id'), str) or not comparison['window_id']:
        raise _Invalid('고정된 공통 비교기간 식별자가 없습니다.')
    if domain == 'market':
        year = scope['annual_year']
        if isinstance(year, bool) or not isinstance(year, int) or int(scope['as_of'][:4]) - year not in (1, 2) or year - 3 < 2022:
            raise _Invalid('연간 비교기간이 최근 완료 1~2년 또는 동일 HS2022 4개년 범위를 충족하지 않습니다.')
    elif _month(end, -35) < '2022-01':
        raise _Invalid('36개월 비교기간이 동일 HS2022 범위를 충족하지 않습니다.')
    scope.update(lag_months=lag, latest_completed_month=latest)


def _matches(mapping, field, expected):
    if field in mapping and str(mapping[field]) != str(expected):
        raise _Invalid('원관측 근거의 국가·품목·기간·집계 범위가 분석 조건과 다릅니다.')


def _evidence_scope(ref, country, period, kind, scope, sources):
    if not isinstance(ref, dict):
        raise _Invalid('관측 근거의 형식이 올바르지 않습니다.')
    for field, expected in (('hs6', scope['hs6']), ('hs_edition', 'HS2022'),
                            ('classificationCode', 'H6'), ('country', country), ('period', period)):
        _matches(ref, field, expected)
    if 'hs_raw' in ref and not re.fullmatch(re.escape(scope['hs6']) + r'(?:[0-9]{4})?', str(ref['hs_raw'])):
        raise _Invalid('관측 근거의 HS6/HSK10 품목 범위가 다릅니다.')
    if kind != 'kcs_exports':
        for field, expected in (('reporter_code', REPORTERS[country]), ('partner_code', 0), ('flow', 'M')):
            _matches(ref, field, expected)
    source = sources.get(ref.get('source_id'))
    if source is None:
        return
    if source.get('status') not in {'OBSERVED', 'OBSERVED_ZERO', 'PARTIAL'}:
        raise _Invalid('참조 원자료의 관측 가능 상태를 확인할 수 없습니다.')
    params = source.get('request', {}).get('params', {})
    if not isinstance(params, dict):
        raise _Invalid('원자료 조회 조건이 올바르지 않습니다.')
    if kind == 'kcs_exports':
        for field, expected in (('cntyCd', country), ('hsSgn', scope['hs6'])):
            _matches(params, field, expected)
        compact = period.replace('-', '')
        if ('strtYymm' in params and str(params['strtYymm']) > compact
                or 'endYymm' in params and str(params['endYymm']) < compact):
            raise _Invalid('관세청 관측 기간이 원자료 조회 조건과 다릅니다.')
    else:
        for field, expected in (('reporterCode', REPORTERS[country]), ('cmdCode', scope['hs6']),
                                ('flowCode', 'M'), ('partnerCode', 0), ('partner2Code', 0),
                                ('customsCode', 'C00'), ('motCode', 0)):
            _matches(params, field, expected)
        if 'period' in params and period.replace('-', '') not in str(params['period']).split(','):
            raise _Invalid('수입 관측 기간이 원자료 조회 조건과 다릅니다.')
        url = source.get('request', {}).get('url', '')
        if '/data/v1/get/' in url:
            expected_path = '/data/v1/get/C/' + ('A' if kind == 'annual_imports' else 'M') + '/HS'
            if expected_path not in url:
                raise _Invalid('수입 원자료의 빈도·상품 집계 범위가 다릅니다.')


def _observations(trade, kind, periods, country, scope, sources, valuation, scoped):
    rows = trade.get(kind)
    if not isinstance(rows, list):
        raise _Invalid('필수 원관측 목록이 없습니다.')
    indexed = {}
    wanted = set(periods)
    for row in rows:
        if not isinstance(row, dict):
            raise _Invalid('원관측 행의 형식이 올바르지 않습니다.')
        period = row.get('period')
        if period not in wanted:
            continue
        if period in indexed:
            raise _Invalid('필수 기간의 원관측이 중복되었습니다.')
        indexed[period] = row
    output = []
    for period in periods:
        row = indexed.get(period, {})
        if row.get('status') not in VALID:
            raise _Invalid('필수 기간의 원관측이 누락되거나 오류입니다. 0으로 대체하지 않습니다.')
        displayed = _decimal(row.get('value'))
        exact = _decimal(row.get('value_decimal', row.get('value')))
        if exact < 0 or (row['status'] == 'OBSERVED_ZERO' and exact != 0):
            raise _Invalid('관측 금액 또는 확인된 0 상태가 올바르지 않습니다.')
        if float(exact) != float(displayed) or not math.isfinite(float(exact)):
            raise _Invalid('원관측의 정확값과 표시값이 일치하지 않습니다.')
        refs = row.get('evidence', [])
        if not isinstance(refs, list) or not refs:
            raise _Invalid('원관측의 출처 근거가 없습니다.')
        # The adapter's own dimensions are checked when present, as are refs.
        _evidence_scope(row, country, period, kind, scope, {})
        for ref in refs:
            _evidence_scope(ref, country, period, kind, scope, sources)
            source = sources.get(ref.get('source_id'))
            if source is None or not isinstance(source.get('sha256'), str) or not re.fullmatch(r'[0-9a-fA-F]{64}', source['sha256']):
                raise _Invalid('원관측 출처와 유효한 원문 SHA256 근거를 연결할 수 없습니다.')
            if not scoped:
                same_country = ref.get('country') == country or (kind != 'kcs_exports' and str(ref.get('reporter_code')) == str(REPORTERS[country]))
                same_hs = ref.get('hs6') == scope['hs6'] or (kind == 'kcs_exports' and str(ref.get('hs_raw', '')).startswith(scope['hs6']))
                if not same_country or not same_hs or ref.get('hs_edition') != 'HS2022':
                    raise _Invalid('원자료 범위 또는 개별 근거에서 국가·HS6·HS2022를 증명할 수 없습니다.')
            if kind != 'kcs_exports':
                basis = ref.get('valuation_basis', 'UNKNOWN')
                if basis in ('CIF', 'FOB'):
                    valuation['known'].add(basis)
                else:
                    valuation['unknown'] = True
        marks = [{'id': ref['source_id'], **{key: sources[ref['source_id']][key]
                 for key in ('sha256', 'status') if key in sources[ref['source_id']]}}
                 for ref in refs if ref.get('source_id') in sources]
        output.append({'period': period, 'value_decimal': _canonical(exact),
                       'status': row['status'], 'evidence': sorted(deepcopy(refs), key=_canonical_json),
                       'sources': sorted({_canonical_json(mark): mark for mark in marks}.values(), key=lambda x: x['id'])})
    return output


def _total(observations):
    return sum((Fraction(Decimal(row['value_decimal'])) for row in observations), Fraction(0))


def _component(spec, metric, exact, observations, period, method, root=None):
    identifier, label, weight, direction = spec
    value = _display(exact, root)
    supplied = float(_decimal(metric['value']))
    amount = identifier in ('import_value', 'korea_exports')
    # Money must use the same float representation; ratios may differ by a few
    # floating point operations (not the former eight-decimal rounding step).
    tolerance = 8 * max(math.ulp(float(value)), math.ulp(1.0))
    if (amount and supplied != float(value)) or (not amount and abs(supplied - float(value)) > tolerance):
        raise _Invalid('비교표 지표와 원관측 재계산 결과가 일치하지 않습니다.')
    if metric.get('period') != period:
        raise _Invalid('비교표 지표와 공통 계산기간이 다릅니다.')
    expected_units = ('USD',) if identifier in ('import_value', 'korea_exports') else ('ratio', '비율')
    if metric.get('unit') not in expected_units:
        raise _Invalid('비교표 지표의 단위가 원계산 단위와 다릅니다.')
    return {
        'id': identifier, 'label': metric.get('label') or label, 'value': value,
        'comparison_value': metric['value'], 'unit': metric['unit'], 'period': period,
        'direction': direction, 'weight': weight, 'rank': None, 'rank_ratio': None,
        'contribution': None, 'tied_count': None, 'all_tied': None,
        'zero_override': identifier in ('import_value', 'korea_exports') and exact == 0,
        'rank_basis': {'method': method, 'exact_ratio': _ratio(exact), 'observations': observations,
            'note': '순위는 표시 반올림값이 아닌 원관측의 정확한 분수값으로 계산합니다. CAGR은 양의 세제곱근 전 비율, CV는 제곱값의 단조성을 사용합니다.'},
        'evidence': _unique_evidence(observations),
    }


def _country(domain, row, trade, scope):
    country = row['country']
    if not isinstance(trade, dict):
        raise _Invalid('포함 국가의 원자료가 없습니다.')
    trade_scope = trade.get('factor', {}).get('scope', {})
    if not isinstance(trade_scope, dict):
        raise _Invalid('원자료의 분석 범위 형식이 올바르지 않습니다.')
    for field, expected in (('country', country), ('hs6', scope['hs6']), ('hs_edition', 'HS2022'), ('as_of', scope['as_of'])):
        _matches(trade_scope, field, expected)
    scoped = all(trade_scope.get(field) == expected for field, expected in
                 (('country', country), ('hs6', scope['hs6']), ('hs_edition', 'HS2022')))
    sources = {}
    for source in trade.get('sources', []):
        if not isinstance(source, dict) or not isinstance(source.get('id'), str):
            raise _Invalid('원자료 식별자의 형식이 올바르지 않습니다.')
        if source['id'] in sources and any(source.get(k) != sources[source['id']].get(k) for k in ('sha256', 'status', 'request')):
            raise _Invalid('같은 원자료 식별자에 서로 다른 근거가 연결되어 있습니다.')
        sources[source['id']] = source
    metrics = {}
    required = {s[0] for s in SPECS[domain]}
    if not isinstance(row.get('metrics'), list):
        raise _Invalid('비교표의 필수 지표가 없습니다.')
    for metric in row['metrics']:
        if not isinstance(metric, dict):
            raise _Invalid('비교표 지표의 형식이 올바르지 않습니다.')
        if metric.get('id') not in required:
            continue
        if metric['id'] in metrics:
            raise _Invalid('비교표의 필수 지표가 중복되었습니다.')
        if metric.get('status') not in VALID:
            raise _Invalid('비교표의 필수 지표가 미관측 또는 오류입니다.')
        value = _decimal(metric.get('value'))
        if metric['status'] == 'OBSERVED_ZERO' and value != 0:
            raise _Invalid('비교표의 확인된 0 상태와 값이 다릅니다.')
        metrics[metric['id']] = metric
    if set(metrics) != required:
        raise _Invalid('비교표의 필수 지표가 누락되었습니다.')
    valuation = {'known': set(), 'unknown': False}
    def observations(kind, periods):
        return _observations(trade, kind, periods, country, scope, sources, valuation, scoped)
    end = scope['end_month']
    calculated = []
    if domain == 'market':
        year = scope['annual_year']
        annual = observations('annual_imports', [str(y) for y in range(year - 3, year + 1)])
        exports = observations('kcs_exports', [f'{year}-{m:02d}' for m in range(1, 13)])
        ytd_periods = [f'{end[:4]}-{m:02d}' for m in range(1, int(end[5:]) + 1)]
        recent_periods = [_month(end, i) for i in range(-2, 1)]
        ytd = observations('monthly_imports', ytd_periods)
        prior_ytd = observations('monthly_imports', [_month(p, -12) for p in ytd_periods])
        recent = observations('monthly_imports', recent_periods)
        prior_recent = observations('monthly_imports', [_month(p, -12) for p in recent_periods])
        base = _total(annual[:1])
        if base <= 0 or _total(prior_ytd) <= 0 or _total(prior_recent) <= 0:
            raise _Invalid('성장률의 기준기간 금액이 0이어서 비교할 수 없습니다.')
        calculated = [
            (_total(annual[-1:]), annual[-1:], str(year), 'annual_import_amount', None),
            (_total(exports), exports, str(year), 'sum_12_korean_export_months', None),
            (_total(ytd) / _total(prior_ytd) - 1, ytd + prior_ytd,
             f'{ytd[0]["period"]}~{end} / {prior_ytd[0]["period"]}~{prior_ytd[-1]["period"]}', 'current_ytd / prior_ytd - 1', None),
            (_total(annual[-1:]) / base, annual, f'{year - 3}~{year}', 'annual_Y / annual_Y_minus_3 (monotonic CAGR basis)', 3),
            (_total(recent) / _total(prior_recent) - 1, recent + prior_recent,
             f'{recent[0]["period"]}~{end} / {prior_recent[0]["period"]}~{prior_recent[-1]["period"]}', 'recent_3m / prior_3m - 1', None),
        ]
    else:
        monthly = observations('monthly_imports', [_month(end, i) for i in range(-35, 1)])
        values = [Fraction(Decimal(obs['value_decimal'])) for obs in monthly]
        total = sum(values)
        if total <= 0 or any(value <= 0 for value in values[:-1]):
            raise _Invalid('양수 평균 및 35개 인접 월의 양수 분모를 확인할 수 없습니다.')
        n = len(values)
        cv_squared = n * (n * sum(value * value for value in values) - total * total) / ((n - 1) * total * total)
        drops = sum(current <= previous * Fraction(4, 5) for previous, current in zip(values, values[1:]))
        period = f'{monthly[0]["period"]}~{end}'
        calculated = [(cv_squared, monthly, period,
                       'sample_CV_squared = n*(n*sum(x^2)-sum(x)^2)/((n-1)*sum(x)^2)', 2),
                      (Fraction(drops, 35), monthly, period, 'count(current <= previous*4/5) / 35', None)]
    if len(valuation['known']) > 1:
        raise _Invalid('한 국가의 비교기간 중 확인된 수입평가기준이 서로 달라 동일 범위로 비교할 수 없습니다.')
    components = [_component(spec, metrics[spec[0]], *values) for spec, values in zip(SPECS[domain], calculated)]
    return components, valuation


def _hold(result, status, reason):
    result.update(status=status, reason=reason, scoring_id=None)
    result['warnings'].append(reason)
    result['country_scores'] = [
        {'country': country, 'status': status, 'raw_score': None, 'score': None,
         'raw_max': result['raw_max'], 'score_max': 100, 'reason': reason, 'components': []}
        for country in result['included'] if isinstance(country, str)
    ]
    return result


def score_comparison(domain, comparison, inputs, trades):
    """Score a frozen cohort, or withhold *all* its scores on an invalid input.

    No ranking is computed from rounded metrics. All required observations,
    including the four annual CAGR years and 35 stability pairs, are rechecked.
    Absent historical scope metadata is not invented; known contradictions fail.
    """
    comparison = comparison if isinstance(comparison, dict) else {}
    result = {'rubric_version': VERSION, 'domain': domain, 'status': 'INVALID_SCORE_INPUT',
              'raw_max': sum(s[2] for s in SPECS.get(domain, ())),
              'window_id': comparison.get('window_id'), 'scoring_id': None, 'scope': {},
              'included': deepcopy(comparison.get('included', [])) if isinstance(comparison.get('included'), list) else [],
              'excluded': deepcopy(comparison.get('excluded', [])), 'country_scores': [],
              'warnings': [], 'method': METHOD, 'limitations': list(LIMITATIONS),
              'comparability_status': 'VALUATION_UNVERIFIED', 'valuation_bases': {},
              'valuation_unknown_countries': []}
    try:
        if domain not in SPECS:
            raise _Invalid('승인된 시장성·안정성 영역만 참고지수를 계산합니다.')
        scope = _scope(inputs, comparison, domain)
        result['scope'] = scope
        members = _members(comparison)
        if len(result['included']) < 2:
            return _hold(result, 'INSUFFICIENT_COMPARISON', '같은 기간의 유효 국가가 2개 미만이어서 상대 참고지수를 보류합니다.')
        if comparison.get('status') != 'ready':
            raise _Invalid('고정 비교군이 비교 가능 상태가 아닙니다.')
        _window(scope, comparison, domain)
        if not isinstance(trades, dict):
            raise _Invalid('국가별 원자료가 없습니다.')
        prepared = {}
        for country in sorted(result['included']):
            components, valuation = _country(domain, members[country], trades.get(country), scope)
            prepared[country] = components
            result['valuation_bases'][country] = sorted(valuation['known'])
            if valuation['unknown']:
                result['valuation_unknown_countries'].append(country)
        bases = {basis for labels in result['valuation_bases'].values() for basis in labels}
        if domain == 'market' and len(bases) > 1:
            raise _Invalid('포함 국가의 확인된 수입평가기준(CIF/FOB)이 달라 시장 규모를 같은 기준으로 순위화할 수 없습니다.')
        if result['valuation_unknown_countries']:
            result['warnings'].append('일부 수입 관측의 CIF/FOB 평가기준을 확인하지 못했습니다. 원기관 신고액의 상대 참고값입니다.')
        if domain == 'stability' and len(bases) > 1:
            result['warnings'].append('국가 간 수입평가기준이 다릅니다. 확인된 기간 내 기준 변경이 발견되지 않은 자료의 CV·급감 빈도만 비교합니다.')
        countries = sorted(prepared)
        n = len(countries)
        exact_contributions = {country: [] for country in countries}
        for index, spec in enumerate(SPECS[domain]):
            exact = {c: Fraction(int(prepared[c][index]['rank_basis']['exact_ratio']['numerator']),
                                 int(prepared[c][index]['rank_basis']['exact_ratio']['denominator'])) for c in countries}
            for country in countries:
                component = prepared[country][index]
                value = exact[country]
                worse = sum(other < value if spec[3] == 'HIGHER' else other > value for other in exact.values())
                tied = sum(other == value for other in exact.values())
                rank = Fraction(2 * worse + tied + 1, 2)
                rank_ratio = (rank - 1) / (n - 1)
                contribution = Fraction(0) if component['zero_override'] else spec[2] * rank_ratio
                exact_contributions[country].append(contribution)
                component.update(rank=_display(rank), rank_ratio=_display(rank_ratio),
                                 contribution=_display(contribution), tied_count=tied, all_tied=tied == n)
        identity = {'version': VERSION, 'domain': domain, 'scope': scope, 'window_id': result['window_id'],
                    'formula': rubric_snapshot(),
                    'excluded': sorted([{'country': row['country'], 'reason': row.get('reason')}
                                        for row in result['excluded']], key=lambda row: row['country']),
                    'countries': [{'country': c, 'components': [{k: component[k] for k in
                        ('id', 'direction', 'weight', 'zero_override', 'rank_basis')}
                        for component in prepared[c]]} for c in countries]}
        result['scoring_id'] = domain + '-score-' + sha256(_canonical_json(identity).encode('utf-8')).hexdigest()[:32]
        for country in countries:
            raw = sum(exact_contributions[country], Fraction(0))
            result['country_scores'].append({'country': country, 'status': 'CALCULATED_REFERENCE',
                'raw_score': _display(raw), 'score': _display(raw / result['raw_max'] * 100),
                'raw_max': result['raw_max'], 'score_max': 100,
                'reason': '고정 비교군·공통기간의 원관측으로 산출한 상대 참고지수입니다.',
                'components': prepared[country]})
        result.update(status='CALCULATED_REFERENCE', reason='원관측과 고정 비교군을 확인한 상대 참고지수입니다.')
        return result
    except _Invalid as error:
        return _hold(result, 'INVALID_SCORE_INPUT', str(error))
    except (TypeError, ValueError, KeyError, AttributeError, OverflowError, InvalidOperation):
        return _hold(result, 'INVALID_SCORE_INPUT', '입력 근거의 형식 또는 계산 범위를 확인할 수 없어 비교군 전체의 점수를 보류합니다.')
