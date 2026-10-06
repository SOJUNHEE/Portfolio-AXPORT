# (junhee) 2026-09-27 sanghyeob/analysis_policy.py 에서 옮김. 바꾼 것: 패키지 import 경로·원본 자료 경로(junhee/data/raw)만. 계산 로직은 그대로.
"""Approved scope/calendar policy and the limited market/stability rubric.

Period selection is independent of the selected destination and company. Within
the allowed lag choose the largest complete cohort, then the latest year/month.
Raw observations are never interpolated or renormalized when inputs are missing.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json

CANDIDATES = ('US', 'CN', 'JP', 'DE', 'VN')
COUNTRY_NAMES = dict(zip(CANDIDATES, ('미국', '중국', '일본', '독일', '베트남')))
VERSION = 'comparison-policy-v1'
WEIGHTS = {'market': 40, 'price': 20, 'logistics': 10, 'stability': 10}
VALID = {'OBSERVED', 'OBSERVED_ZERO'}
DATA_ERRORS = {'FETCH_ERROR', 'INVALID_DATA', 'INVALID_SCOPE', 'CONFLICT', 'DUPLICATE_PERIOD'}
MARKET_METRICS = ('import_value', 'korea_exports', 'import_ytd_yoy', 'import_cagr3', 'import_3m_yoy')


def policy_snapshot():
    from .analysis_scoring import rubric_snapshot
    rubric = rubric_snapshot()
    return {'version': VERSION, 'candidate_countries': list(CANDIDATES),
            'max_lag_months': 3, 'monthly_history': 60, 'annual_history': 5, 'stability_months': 36,
            'period_selection': 'maximum_complete_countries_then_latest_year_month',
            'score': {'raw_max': 80, 'display_max': 100, 'formula': 'raw / 80 * 100',
                      'weights': dict(WEIGHTS), 'methodology_status': 'APPROVED_PARTIAL',
                      'approved_domains': ['market', 'stability'], 'rubric_version': rubric['version'],
                      'rubric': rubric, 'aggregate_enabled': False,
                      'regulation_is_separate_gate': True, 'is_success_probability': False}}


def convert_raw_total(contributions):
    """The approved scale only, not a formula that creates factor scores.

    The assessment pipeline keeps the total withheld while price/logistics
    remain pending. Missing factors cannot shrink the denominator.
    """
    empty = {'raw_score': None, 'score': None, 'raw_max': 80, 'display_max': 100}
    if not isinstance(contributions, dict) or set(contributions) != set(WEIGHTS):
        return empty
    values = []
    for key, maximum in WEIGHTS.items():
        raw = contributions[key]
        if raw is None or isinstance(raw, bool):
            return empty
        try:
            value = Decimal(str(raw))
        except (InvalidOperation, ValueError):
            return empty
        if not value.is_finite() or not 0 <= value <= maximum:
            return empty
        values.append(value)
    total = sum(values)
    return {**empty, 'raw_score': float(total), 'score': float(total / 80 * 100)}


def month_offset(month, offset):
    parsed = date.fromisoformat(month + '-01')
    index = parsed.year * 12 + parsed.month - 1 + offset
    return f'{index // 12:04d}-{index % 12 + 1:02d}'


def _amount(observation):
    if observation.get('status') not in VALID or isinstance(observation.get('value'), bool):
        return None
    try:
        value = Decimal(str(observation.get('value_decimal', observation.get('value'))))
        display = Decimal(str(observation.get('value')))
    except (ValueError, InvalidOperation):
        return None
    if (not value.is_finite() or not display.is_finite() or value < 0
            or float(value) != float(display)
            or (observation['status'] == 'OBSERVED_ZERO' and value != 0)):
        return None
    return value


def stability_eligibility(trade, end_month):
    indexed, duplicate = {}, set()
    for observation in trade.get('monthly_imports', []):
        period = observation.get('period')
        if period in indexed:
            duplicate.add(period)
        indexed[period] = observation
    periods = [month_offset(end_month, i) for i in range(-35, 1)]
    values = [None if p in duplicate else _amount(indexed.get(p, {})) for p in periods]
    missing = [p for p, value in zip(periods, values) if value is None]
    if missing:
        return False, f'공통 36개월 중 {len(missing)}개월이 누락·오류·중복입니다. ({", ".join(missing[:3])}{" 외" if len(missing) > 3 else ""})'
    if sum(values) == 0:
        return False, '36개월 수입액이 모두 0이어서 변동계수를 정의할 수 없습니다.'
    pairs = sum(values[i] > 0 for i in range(35))
    if pairs != 35:
        return False, f'전월 금액 0 때문에 유효한 인접 월 비교가 {pairs}/35쌍입니다.'
    return True, '연속 36개월·양수 평균·35개 인접 월 비교를 확인했습니다.'


def _valid_metric(metric):
    if metric.get('status') not in VALID or isinstance(metric.get('value'), bool):
        return False
    try:
        return Decimal(str(metric.get('value'))).is_finite()
    except (ValueError, InvalidOperation):
        return False


def _market_evaluation(trade, inputs, year, end):
    from .analysis_market_price import rebase_market
    rebased = rebase_market(trade, inputs, year, end)
    metrics = {m['id']: m for m in rebased['factor']['metrics']}
    missing = [metrics.get(key, {'label': key, 'reason': '관측 자료 없음'})
               for key in MARKET_METRICS if not _valid_metric(metrics.get(key, {}))]
    if missing:
        detail = '; '.join(f'{m["label"]}: {m.get("reason") or m.get("status") or "자료 부족"}' for m in missing)
        return False, detail, rebased
    return True, '같은 연도·월의 시장성 5개 핵심지표를 확인했습니다.', rebased


def _rollback_error(trade, end, latest, annual_year=None):
    """Publication delay allows rollback; a failed/invalid recent batch does not."""
    seen = set()
    for observation in trade.get('monthly_imports', []):
        period = observation.get('period', '')
        if not isinstance(period, str) or not end <= period <= latest:
            continue
        invalid = observation.get('status') in VALID and _amount(observation) is None
        if observation.get('status') in DATA_ERRORS or period in seen or invalid:
            return f'{period}의 조회 실패·자료 오류가 미해결이므로 과거 월로 후퇴해 비교하지 않습니다.'
        seen.add(period)
    if annual_year is not None:
        seen_annual = set()
        for observation in trade.get('annual_imports', []):
            period = str(observation.get('period', observation.get('year')))
            if period != str(annual_year):
                continue
            invalid = observation.get('status') in VALID and _amount(observation) is None
            if observation.get('status') in DATA_ERRORS or period in seen_annual or invalid:
                return f'{annual_year}년 수입자료의 조회 실패·범위 오류·중복이 있어 과거 연도로 대체하지 않습니다.'
            seen_annual.add(period)
        seen_kcs = set()
        for observation in trade.get('kcs_exports', []):
            period = str(observation.get('period', ''))
            if not f'{annual_year}-01' <= period <= f'{annual_year}-12':
                continue
            invalid = observation.get('status') in VALID and _amount(observation) is None
            if observation.get('status') in DATA_ERRORS or period in seen_kcs or invalid:
                return f'{annual_year}년 관세청 수출자료의 조회 실패·범위 오류·중복이 있어 과거 연도로 대체하지 않습니다.'
            seen_kcs.add(period)
    return None


def _identity(domain, inputs, window, trades):
    source_marks = [{key: source.get(key) for key in ('id', 'sha256', 'status')}
                    for country in CANDIDATES for source in trades.get(country, {}).get('sources', [])]
    value = {'policy': VERSION, 'domain': domain, 'hs6': inputs['hs6'], 'hs_edition': inputs['hs_edition'],
             'as_of': inputs['as_of'], 'end_month': window['end_month'], 'annual_year': window.get('annual_year'),
             'included': window['included'], 'excluded': window['excluded'], 'sources': source_marks}
    return domain + '-' + sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]


def refresh_comparison(domain, window, inputs, trades):
    """Keep membership, status and provenance consistent after a domain error."""
    rows = window['countries']
    window['included'] = [r['country'] for r in rows if r['eligible']]
    window['excluded'] = [{k: r[k] for k in ('country', 'country_name', 'reason')} for r in rows if not r['eligible']]
    enough = len(window['included']) >= 2
    window['status'] = 'ready' if enough else 'insufficient'
    window['reason'] = ('같은 기간의 자료 요건을 충족한 국가끼리 원지표를 비교합니다.' if enough
                        else '동일 기간의 요건을 충족하는 국가가 2개 미만이므로 국가 비교를 보류합니다.')
    if window['end_month'] is None:
        window['reason'] += ' 최근 완료 월보다 3개월 넘게 이전인 기간으로 후퇴하지 않습니다.'
    window['window_id'] = _identity(domain, inputs, window, trades)
    return window


def unavailable_comparisons(inputs, trades):
    latest = month_offset(inputs['as_of'][:7], -1)
    result = {}
    for domain in ('market', 'stability'):
        window = {'annual_year': None, 'end_month': None, 'lag_months': None,
                  'latest_completed_month': latest, 'candidate_months': [month_offset(latest, -i) for i in range(4)],
                  'policy_version': VERSION, 'max_lag_months': 3,
                  'countries': [{'country': c, 'country_name': COUNTRY_NAMES[c], 'eligible': False,
                                 'reason': '비교기간 처리 오류로 국가 비교를 보류했습니다. 선택국 원지표는 별도로 확인합니다.',
                                 'metrics': []} for c in CANDIDATES]}
        result[domain] = refresh_comparison(domain, window, inputs, trades)
    result['periods_differ'] = False
    return result


def select_comparisons(trades, inputs):
    """Select and describe independent market/stability cohorts, without scores."""
    as_of = date.fromisoformat(inputs['as_of'])
    latest = month_offset(as_of.strftime('%Y-%m'), -1)
    months = [month_offset(latest, -lag) for lag in range(4)]
    result = {}
    for domain in ('market', 'stability'):
        candidates = []
        years = (as_of.year - 1, as_of.year - 2) if domain == 'market' else (None,)
        for year in years:
            for lag, end in enumerate(months):
                rows = []
                for country in CANDIDATES:
                    trade = trades.get(country, {})
                    scoped = {**inputs, 'country': country, 'country_name': COUNTRY_NAMES[country]}
                    try:
                        if domain == 'market':
                            eligible, reason, rebased = _market_evaluation(trade, scoped, year, end)
                            metrics = [m for m in rebased['factor']['metrics'] if m['id'] in MARKET_METRICS]
                        else:
                            eligible, reason = stability_eligibility(trade, end)
                            metrics = []
                        error = _rollback_error(trade, end, latest, as_of.year - 1 if domain == 'market' else None)
                        if error:
                            eligible, reason = False, error
                    except Exception:
                        eligible, metrics = False, []
                        reason = '이 국가의 비교 지표 처리 중 오류가 있어 비교 대상에서 제외했습니다. 재분석으로 확인해 주세요.'
                    rows.append({'country': country, 'country_name': COUNTRY_NAMES[country],
                                 'eligible': eligible, 'reason': reason, 'metrics': metrics})
                count = sum(row['eligible'] for row in rows)
                candidates.append((count, year or 0, -lag, end, rows))
        count, year, reverse_lag, end, rows = max(candidates, key=lambda item: item[:3])
        window = {'status': 'ready' if count >= 2 else 'insufficient',
                  'annual_year': year if domain == 'market' and count else None,
                  'end_month': end if count else None, 'lag_months': -reverse_lag if count else None,
                  'latest_completed_month': latest, 'candidate_months': months,
                  'included': [r['country'] for r in rows if r['eligible']],
                  'excluded': [{'country': r['country'], 'country_name': r['country_name'], 'reason': r['reason']}
                               for r in rows if not r['eligible']], 'countries': rows,
                  'policy_version': VERSION, 'max_lag_months': 3,
                  'reason': ('같은 기간의 자료 요건을 충족한 국가끼리 원지표를 비교합니다.' if count >= 2
                             else '동일 기간의 요건을 충족하는 국가가 2개 미만이므로 국가 비교를 보류합니다.')}
        if count == 0:
            window['reason'] += ' 최근 완료 월보다 3개월 넘게 이전인 기간으로 후퇴하지 않습니다.'
            for row in rows:
                row['metrics'] = []
        result[domain] = refresh_comparison(domain, window, inputs, trades)
    result['periods_differ'] = result['market']['end_month'] != result['stability']['end_month']
    return result


def country_window(comparison, country):
    """The factor calculator receives the same frozen window as the dashboard."""
    row = next(r for r in comparison['countries'] if r['country'] == country)
    return {key: deepcopy(comparison[key]) for key in ('end_month', 'annual_year', 'lag_months', 'status',
            'window_id', 'policy_version', 'max_lag_months')} | {'eligible': row['eligible'], 'reason': row['reason']}
