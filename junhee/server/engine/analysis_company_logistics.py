# (junhee) 2026-09-27 sanghyeob/analysis_company_logistics.py 에서 옮김. 바꾼 것: 패키지 import 경로·원본 자료 경로(junhee/data/raw)만. 계산 로직은 그대로.
"""Pure calculations for enterprise-reported handover and final receipt.

Supported timestamps are ISO 8601 with an explicit offset, or a local datetime
with separate ``인계시간대``/``인수시간대`` fixed offsets (±HH:MM). A shared
``시간대`` column and IANA names are not inferred. POD references are labels in
the uploaded workbook, not verified documents. No files, URLs or APIs are read.
"""

from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
import re


VERSION = 'company-delivery-events-v1'
UTC = timezone.utc
KST = timezone(timedelta(hours=9))
TIMESTAMP = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}'
                       r'(?::[0-9]{2}(?:\.[0-9]{1,6})?)?(?:Z|[+-][0-9]{2}:[0-9]{2})?')


def _text(value):
    return '' if value is None else str(value).strip()


def _offset(value):
    text = _text(value)
    if text in ('Z', 'UTC'):
        return UTC
    match = re.fullmatch(r'([+-])([0-9]{2}):([0-9]{2})', text)
    if not match or int(match[2]) > 23 or int(match[3]) > 59:
        raise ValueError('시간대는 +09:00, -05:00 같은 고정 UTC offset으로 입력해 주세요. IANA 이름은 지원하지 않습니다.')
    minutes = int(match[2]) * 60 + int(match[3])
    return timezone(timedelta(minutes=minutes if match[1] == '+' else -minutes))


def _timestamp(raw, offset_raw=None):
    if isinstance(raw, datetime):
        text = raw.isoformat()
    elif isinstance(raw, date):
        text = raw.isoformat()
    else:
        text = _text(raw)
    if not text:
        return None, 'MISSING_TIMESTAMP', '시각이 기재되지 않았습니다.'
    if re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', text):
        return None, 'DATE_ONLY', '날짜만 기재되어 있습니다. 시·분과 시간대가 필요합니다.'
    if not TIMESTAMP.fullmatch(text):
        return None, 'INVALID_TIMESTAMP', '시각은 YYYY-MM-DDTHH:MM[:SS] 형식으로 입력해 주세요.'
    if (int(text[11:13]) > 23 or int(text[14:16]) > 59
            or (len(text) > 16 and text[16] == ':' and int(text[17:19]) > 59)):
        return None, 'INVALID_TIMESTAMP', '시각은 00:00:00~23:59:59 범위여야 합니다. 24시나 윤초를 임의로 보정하지 않습니다.'
    suffix = re.search(r'(Z|[+-][0-9]{2}:[0-9]{2})$', text)
    if suffix:
        try:
            _offset(suffix[1])
        except ValueError as exc:
            return None, 'UNSUPPORTED_TIMEZONE', str(exc)
    try:
        value = datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        return None, 'INVALID_TIMESTAMP', '존재하지 않거나 잘못된 날짜·시각입니다.'
    explicit = None
    if _text(offset_raw):
        try:
            explicit = _offset(offset_raw)
        except ValueError as exc:
            return None, 'UNSUPPORTED_TIMEZONE', str(exc)
    if value.tzinfo is None:
        if explicit is None:
            return None, 'TIMEZONE_REQUIRED', '인계시간대와 인수시간대를 각각 명시하거나 각 시각에 UTC offset을 포함해 주세요.'
        value = value.replace(tzinfo=explicit)
    elif explicit is not None and value.utcoffset() != explicit.utcoffset(None):
        return None, 'TIMEZONE_CONFLICT', '시각에 포함된 offset과 별도 시간대 열이 서로 다릅니다.'
    try:
        return value.astimezone(UTC), None, None
    except (ValueError, OverflowError):
        return None, 'INVALID_TIMESTAMP', 'UTC로 변환할 수 없는 시각입니다.'


def _evidence(company, row, field, sheet='물류'):
    return {'source_id': company.get('source', {}).get('id', 'company-upload'),
            'sheet': row.get('_sheet', sheet), 'row': row.get('_row'), 'field': field}


def _metric(identifier, label, value, unit, period, formula, status, reason, evidence):
    return {'id': identifier, 'label': label, 'value': value, 'unit': unit,
            'period': period, 'formula': formula, 'status': status, 'reason': reason,
            'evidence': evidence}


def _group(transaction, logistics):
    mode = _text(logistics.get('운송수단')).upper()
    mode = {'항공': 'AIR', '해상': 'SEA'}.get(mode, mode)
    values = (_text(transaction.get('제품ID')), mode,
              _text(logistics.get('출발지')), _text(logistics.get('도착지')))
    placeholders = {'', '-', 'N/A', 'NONE', 'NULL', 'UNKNOWN', '미상', '없음'}
    return values if all(value.upper() not in placeholders for value in values) else None


def evaluate_company_logistics(company, inputs):
    """Return metrics, transaction observations, groups and data coverage.

    The caller already restricts the product rows for an exact 8/10-digit HS.
    This helper also preserves that restriction when called independently.
    Mean duration is emitted only for exactly one identified product/mode/route
    group among valid timestamp+POD observations. No volume weighting, transit
    assumptions, forward delivery predictions, API calls or scores are added.

    ``analysis_as_of`` is the precise evaluation timestamp when provided. The
    calendar ``as_of`` is also bounded by next-day 00:00 KST (exclusive). With
    only as_of, the entire stated Korean calendar date is the explicit cutoff.
    """
    # Import at call time: the existing logistics module can integrate this helper.
    from .analysis_risk_logistics import _scope, _active_actual, _hs

    try:
        as_of = date.fromisoformat(inputs['as_of'])
        if inputs['hs_edition'] != 'HS2022' or not re.fullmatch(r'[0-9]{6}', inputs['hs6']):
            raise ValueError
        calendar_end = datetime.combine(as_of + timedelta(days=1), time(), KST).astimezone(UTC)
    except (KeyError, TypeError, ValueError, OverflowError):
        raise ValueError('기업 물류의 HS2022·6자리 HS·기준일을 확인해 주세요.') from None
    analysis_cutoff, cutoff_error, cutoff_reason = None, None, None
    if inputs.get('analysis_as_of'):
        analysis_cutoff, cutoff_error, cutoff_reason = _timestamp(inputs['analysis_as_of'])
    products, planned, actual = _scope(company, inputs)
    raw_hs = _text(inputs.get('hs_raw'))
    if len(raw_hs) in (8, 10):
        selected_ids = {_text(row.get('제품ID')) for row in products if _hs(row.get('HS코드')) == raw_hs}
        planned = [row for row in planned if _text(row.get('제품ID')) in selected_ids]
        actual = [row for row in actual if _text(row.get('제품ID')) in selected_ids]
    actual = _active_actual(actual, as_of)
    candidates = [(row, '거래ID', 'PLANNED') for row in planned] + [(row, '실적ID', 'ACTUAL') for row in actual]
    transactions = {}
    for transaction, field, kind in candidates:
        identifier = _text(transaction.get(field))
        if identifier:
            transactions[identifier] = (transaction, kind)
    # A logistics row lacks a namespace: collisions outside the selected scope
    # must not be silently attached to whichever transaction happens to remain.
    sheets = company.get('sheets', {})
    identifiers = Counter(_text(row.get(field))
                          for sheet, field in [('수출예정거래', '거래ID'), ('수출실적', '실적ID')]
                          for row in sheets.get(sheet, []) if _text(row.get(field)))
    matched = defaultdict(list)
    unmatched = 0
    for logistics in sheets.get('물류', []):
        identifier = _text(logistics.get('거래ID'))
        if identifier in transactions:
            matched[identifier].append(logistics)
        else:
            unmatched += 1
    observations, grouped = [], defaultdict(list)
    for identifier in sorted(transactions):
        transaction, kind = transactions[identifier]
        records = matched[identifier]
        refs = [_evidence(company, transaction, '제품ID/목적국/' + ('거래ID' if kind == 'PLANNED' else '실적ID'),
                          '수출예정거래' if kind == 'PLANNED' else '수출실적')]
        refs.extend(_evidence(company, row, '운송인인계시각/최종인수시각/인계시간대/인수시간대/POD참조') for row in records)
        observation = {'transaction_id': identifier, 'transaction_kind': kind,
                       'product_id': _text(transaction.get('제품ID')),
                       'logistics_ids': [_text(row.get('물류ID')) for row in records],
                       'days': None, 'reported_duration_days': None,
                       'handover_utc': None, 'receipt_utc': None,
                       'pod_reference': None, 'pod_status': 'MISSING',
                       'status': 'INSUFFICIENT', 'issues': [], 'evidence': refs, 'group': None}

        def exclude(status, detail, field=None):
            observation.update(status=status)
            observation['issues'].append({'code': status, 'detail': detail, 'field': field})

        if identifiers[identifier] > 1:
            exclude('TRANSACTION_ID_CONFLICT', '거래ID/실적ID가 중복되어 물류 기록의 대상 거래를 확정할 수 없습니다.')
        elif not records:
            exclude('MISSING_EVENTS', '이 거래와 연결된 물류 기록이 없습니다.')
        elif len(records) != 1:
            exclude('AMBIGUOUS_MULTIPLE_EVENTS', '동일 거래에 여러 물류 행이 있습니다. 분할배송·중간구간·중복 여부와 최종 인수를 구분해야 합니다.')
        elif cutoff_error:
            exclude('INVALID_CUTOFF', cutoff_reason, 'analysis_as_of')
        else:
            logistics = records[0]
            key = _group(transaction, logistics)
            if key:
                observation['group'] = dict(zip(('product_id', 'mode', 'origin', 'destination'), key))
            handover, handover_error, handover_reason = _timestamp(logistics.get('운송인인계시각'), logistics.get('인계시간대'))
            receipt, receipt_error, receipt_reason = _timestamp(logistics.get('최종인수시각'), logistics.get('인수시간대'))
            observation['handover_utc'] = handover.isoformat() if handover else None
            observation['receipt_utc'] = receipt.isoformat() if receipt else None
            pod = _text(logistics.get('POD참조'))
            if isinstance(logistics.get('POD참조'), bool) or pod.upper() in ('', '-', 'N/A', 'NONE', 'NULL', 'NAN', '없음'):
                pod = ''
            observation['pod_reference'] = pod or None
            observation['pod_status'] = 'REFERENCE_UNVERIFIED' if pod else 'MISSING'
            if handover_error:
                exclude(handover_error, handover_reason, '운송인인계시각/인계시간대')
            if receipt_error:
                exclude(receipt_error, receipt_reason, '최종인수시각/인수시간대')
            if not handover_error and not receipt_error:
                if receipt < handover:
                    exclude('REVERSED_TIMESTAMPS', '최종 인수의 UTC 시각이 운송인 인계보다 빠릅니다.')
                elif receipt >= calendar_end or (analysis_cutoff is not None and receipt > analysis_cutoff):
                    exclude('FUTURE_RECEIPT', '최종 인수가 분석 시각 또는 기준일 범위를 벗어나 실제 완료 관측으로 사용하지 않습니다.')
                else:
                    duration = (receipt - handover).total_seconds() / 86400
                    observation['reported_duration_days'] = duration
                    if not pod:
                        exclude('POD_REFERENCE_MISSING', '시각 차이는 기업 기재 참고값입니다. 최종 인수 POD참조가 없어 배송시간 평균에서 제외했습니다.', 'POD참조')
                    else:
                        observation.update(days=duration, status='COMPANY_REPORTED')
                        if key:
                            grouped[key].append(observation)
                        else:
                            observation['issues'].append({'code': 'GROUP_FIELDS_MISSING', 'field': '제품ID/운송수단/출발지/도착지',
                                'detail': '거래별 기재 시각 차이는 보존하지만 운송조건 그룹이 불명확해 통합 평균에 사용하지 않습니다.'})
        observations.append(observation)
    valid = [row for row in observations if row['status'] == 'COMPANY_REPORTED']
    groups = []
    for key, members in sorted(grouped.items()):
        groups.append({**dict(zip(('product_id', 'mode', 'origin', 'destination'), key)),
            'sample_count': len(members), 'mean_days': sum(row['days'] for row in members) / len(members),
            'status': 'COMPANY_REPORTED', 'transaction_ids': [row['transaction_id'] for row in members],
            'evidence': [ref for row in members for ref in row['evidence']],
            'reason': '같은 제품·운송수단·출발지·도착지의 기업 기재 표본평균입니다. 화물조건 일치와 POD 진위는 검증하지 않았습니다.'})
    comparable = bool(valid) and len(groups) == 1 and all(row['group'] for row in valid)
    mean = groups[0]['mean_days'] if comparable else None
    mean_count = len(valid) if comparable else 0
    metric_status = 'COMPANY_REPORTED' if comparable else 'NOT_COMPARABLE' if valid else 'INSUFFICIENT'
    denominator, count = len(transactions), len(valid)
    coverage = {'selected_transactions': denominator, 'observed_transactions': count,
                'excluded_transactions': denominator - count, 'ratio': count / denominator if denominator else None,
                'mean_sample_count': mean_count, 'comparable_groups': len(groups),
                'group_unresolved_observations': sum(not row['group'] for row in valid),
                'unmatched_logistics_rows': unmatched,
                'exclusions_by_status': dict(Counter(row['status'] for row in observations if row['status'] != 'COMPANY_REPORTED'))}
    reason = (f'유효한 기업 기재 {mean_count}개 거래의 같은 제품·운송수단·노선 평균입니다. POD참조의 진위는 미검증입니다.'
              if comparable else '제품·운송수단·출발지·도착지가 다른 그룹이 있거나 식별값이 없어 통합 평균을 만들지 않습니다.'
              if valid else '명확한 거래 연결, 인계·최종 인수 시각과 각 시간대, POD참조가 모두 필요합니다.')
    refs = [ref for row in valid for ref in row['evidence']]
    summary = {'source_id': company.get('source', {}).get('id', 'company-upload'),
               'kind': 'company_delivery_coverage', **coverage}
    metrics = [
        _metric('door_to_door_days', '기업 기재 전체 배송 소요일(동일 그룹 평균)', mean, '일', inputs['as_of'],
                '동일 그룹 거래별 (최종인수UTC − 운송인인계UTC) / 86,400초의 산술평균', metric_status, reason, refs + [summary]),
        _metric('door_to_door_observed_transactions', '시각·POD참조가 있는 기업 기재 거래', count, '건', inputs['as_of'],
                '유효한 인계·최종 인수 시각과 POD참조를 가진 서로 다른 거래ID 수',
                'COMPANY_REPORTED' if denominator else 'INSUFFICIENT', '문서 진위가 검증된 배송 완료 건수가 아닙니다.', [summary]),
        _metric('door_to_door_transaction_coverage', '기업 배송시각·인수참조 기재 완성도', coverage['ratio'], 'ratio', inputs['as_of'],
                '유효시각·POD참조 거래 수 / 선택 범위의 수출예정·유효실적 고유 거래ID 수',
                'COMPANY_REPORTED' if denominator else 'INSUFFICIENT', '예정 거래와 미기재 거래도 분모에 포함한 자료 완성도이며 운송 성공률이 아닙니다.', [summary]),
    ]
    warnings = ['기업이 기재한 사건 시각과 POD참조의 관측입니다. 실제 문서·최종 인수자·진위는 확인하지 않았습니다.',
                '동일 제품·노선 그룹도 포장·중량·취급조건이 같다고 확인된 것은 아닙니다. 표본평균은 미래 배송시간·성공률 또는 물류 점수가 아닙니다.']
    if not analysis_cutoff:
        warnings.append('정확한 분석 시각이 없어 명시된 기준일의 한국시간 하루 끝을 경계로 사용합니다.' if not cutoff_error
                        else '분석 시각의 시간대를 확인할 수 없어 배송시간 계산을 보류했습니다.')
    if any(_text(row.get('시간대')) for row in sheets.get('물류', [])):
        warnings.append('공통 시간대 열은 사용하지 않습니다. 인계·인수의 각 시각 offset 또는 별도 시간대가 필요합니다.')
    if coverage['excluded_transactions']:
        warnings.append(f'선택 거래 {denominator}건 중 {coverage["excluded_transactions"]}건은 식별·시각·POD참조 요건을 충족하지 못했습니다. 사유를 거래별로 보존했습니다.')
    return {'metrics': metrics, 'observations': observations, 'groups': groups, 'coverage': coverage,
            'warnings': warnings, 'checks': [
                {'label': '기업 배송 시각 기준', 'status': 'FIXED_OFFSET_ONLY', 'detail': '시각마다 명시적 UTC offset을 사용합니다. IANA 이름과 공통 시간대의 자동 추정은 지원하지 않습니다.'},
                {'label': '기업 최종 인수 근거', 'status': 'COMPANY_REPORTED_UNVERIFIED', 'detail': 'POD참조는 기업 기재 목록이며 실제 문서의 진위를 검증하지 않았습니다.'}],
            'scope': {'hs6': inputs['hs6'], 'hs_edition': 'HS2022', 'country': inputs.get('country'),
                      'as_of': inputs['as_of'], 'analysis_cutoff_utc': analysis_cutoff.isoformat() if analysis_cutoff else None,
                      'as_of_exclusive_utc': calendar_end.isoformat(), 'cutoff_status': cutoff_error or 'RESOLVED'},
            'adapter_version': VERSION}
