# (junhee) 2026-09-27 sanghyeob/analysis_trade_reference.py 에서 옮김. 바꾼 것: 패키지 import 경로·원본 자료 경로(junhee/data/raw)만. 계산 로직은 그대로.
"""Korea's all-destination exports from the dedicated Itemtrade service.

Official contract: https://www.data.go.kr/data/15101609/openapi.do
This is not the country endpoint with ``cntyCd`` omitted. It provides raw
monthly FOB USD/net-kg evidence, never a score, eligibility threshold or price
comparison. A requests-compatible ``session`` supports offline testing. No
credentials are read from disk and no files are written.
"""

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
import re
from urllib.parse import unquote
import xml.etree.ElementTree as ET

import requests

from .market_data import _decimal, _fetch, _number


KCS_ITEM_URL = 'https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList'
OFFICIAL_URL = 'https://www.data.go.kr/data/15101609/openapi.do'
VERSION = 'kcs-all-destinations-v1'
VALID = {'OBSERVED', 'OBSERVED_ZERO'}
TOTAL_MARKERS = {'총계', '합계', 'Total', 'TOTAL'}


def _periods(as_of):
    anchor = as_of.year * 12 + as_of.month - 1
    return [f'{(anchor + offset) // 12:04d}-{(anchor + offset) % 12 + 1:02d}'
            for offset in range(-24, 0)]


def _empty(period, status='MISSING', reason=None, evidence=None):
    # These zeroes are sums over the usable paired sample, not observed totals.
    return {'period': period, 'value': None, 'status': status,
            'evidence': evidence or [], 'reason': reason,
            'usable_value_usd': 0, 'net_weight_kg': 0,
            'reported_net_weight_kg': None, 'records': 0, 'usable_records': 0,
            'excluded_records': 0, 'value_coverage_ratio': None,
            'weight_status': 'MISSING', 'weight_complete': False, 'weight_missing_records': 0,
            'weight_invalid_records': 0, 'weight_zero_records': 0,
            'missing_weight_records': 0, 'zero_zero_records': 0,
            'zero_value_positive_weight_records': 0}


def _weight(raw):
    if raw is None or not raw.strip():
        return None, 'MISSING'
    try:
        value = _decimal(raw)
        return value, 'ZERO' if value == 0 else 'OBSERVED'
    except ValueError:
        return None, 'INVALID_DATA'


def _parse_batch(content, source, hs6, periods):
    """Validate dimensions before aggregating disjoint HS10 or one HS6 row.

    A response can include a period grand total and HS6 subtotal alongside its
    HSK10 children. Totals are excluded, parent/child values are cross-checked,
    and child rows alone determine paired-weight coverage. Missing weight is
    not reconstructed from a parent subtotal.
    """
    refs = [{'source_id': source['id']}]

    def failed(status, reason):
        source['validation_reason'] = reason
        return {p: _empty(p, status, reason, refs) for p in periods}

    if content is None:
        return failed('FETCH_ERROR', source.get('reason', '관세청 전체 수출 응답이 없습니다.'))
    try:
        if not isinstance(content, bytes):
            raise ET.ParseError
        declarations = content.replace(b'\x00', b'').upper()
        if b'<!DOCTYPE' in declarations or b'<!ENTITY' in declarations:
            raise ET.ParseError
        doc = ET.fromstring(content)
    except (ET.ParseError, ValueError):
        return failed('INVALID_DATA', '관세청 전체 수출 XML 형식을 확인할 수 없습니다.')
    result_codes = doc.findall('./header/resultCode')
    if len(result_codes) > 1:
        return failed('INVALID_DATA', '관세청 전체 수출 업무 결과코드가 중복되었습니다.')
    business_code = (doc.findtext('./header/resultCode') or doc.findtext('.//returnReasonCode') or '').strip()
    if business_code in {'00', '20', '30', '31'}:
        source['business_code'] = business_code
    if business_code in {'20', '30', '31'}:
        source['authorization_error'] = True
    if not result_codes or business_code != '00':
        return failed('FETCH_ERROR', '관세청 전체 수출 업무 응답이 정상 코드가 아닙니다. 활용 권한도 확인해 주세요.')
    if doc.tag != 'response' or doc.find('./body/items') is None:
        return failed('INVALID_DATA', '관세청 전체 수출 관측 목록 구조가 다릅니다.')
    items = doc.findall('./body/items/item')
    total_count = doc.findtext('./body/totalCount')
    if total_count is not None and (not re.fullmatch(r'[0-9]+', total_count.strip())
                                    or (total_count.strip().lstrip('0') or '0') != str(len(items))):
        return failed('INVALID_DATA', '관세청 전체 수출 응답 건수가 일치하지 않거나 잘렸습니다.')
    groups = defaultdict(dict)
    excluded_totals = 0
    for index, item in enumerate(items, 1):
        if len(item) != len({child.tag for child in item}):
            return failed('INVALID_DATA', '관세청 전체 수출 행에 같은 필드가 중복되었습니다.')
        row = {child.tag: (child.text or '').strip() for child in item}
        raw_period = row.get('year', '')
        if raw_period in TOTAL_MARKERS:
            excluded_totals += 1
            continue
        match = re.fullmatch(r'([0-9]{4})[.-]?([0-9]{2})', raw_period)
        period = f'{match[1]}-{match[2]}' if match else None
        code = row.get('hsCode', '')
        if (period not in periods or row.get('statCd') or row.get('cntyCd')
                or not re.fullmatch(r'[0-9]{6}(?:[0-9]{4})?', code)
                or not code.startswith(hs6)):
            return failed('INVALID_SCOPE', '전체 수출의 연월·HS 범위 또는 국가 구분 없는 응답 조건이 요청과 다릅니다.')
        if any(row.get(field) and row[field] not in {'HS2022', '2022', 'H6'}
               for field in ('hs_edition', 'hsEdition', 'classificationCode')):
            return failed('INVALID_SCOPE', '반환된 HS 분류판이 HS2022와 다릅니다.')
        if code in groups[period]:
            return failed('INVALID_DATA', '관세청 전체 수출의 같은 월·HS 관측이 중복되었습니다.')
        try:
            amount = _decimal(row.get('expDlr'))
        except ValueError:
            amount = None
        weight, weight_status = _weight(row.get('expWgt'))
        groups[period][code] = {'amount': amount, 'weight': weight,
                                'weight_status': weight_status, 'record': index}
    source['excluded_period_total_rows'] = excluded_totals
    output = {}
    for period in periods:
        rows = groups[period]
        if not rows:
            output[period] = _empty(period, reason='해당 월의 전체 수출 관측이 없습니다. 0으로 채우지 않습니다.', evidence=refs)
            continue
        children = {code: row for code, row in rows.items() if len(code) == 10}
        selected = children or rows
        evidence = [{'source_id': source['id'], 'record': row['record'], 'period': period,
                     'hs_raw': code, 'field': 'expDlr/expWgt',
                     'value_usd': _number(row['amount']), 'net_weight_kg': _number(row['weight']),
                     'weight_status': row['weight_status'], 'valuation_basis': 'FOB',
                     'partner_scope': 'ALL_DESTINATIONS',
                     'aggregation_role': 'SELECTED' if code in selected else 'PARENT_CHECK_ONLY'}
                    for code, row in rows.items()]
        if any(row['amount'] is None for row in rows.values()):
            output[period] = _empty(period, 'INVALID_DATA', '전체 수출 금액이 누락되거나 유효하지 않아 총액·커버리지를 계산하지 않습니다.', evidence)
            continue
        amount = sum((row['amount'] for row in selected.values()), Decimal(0))
        parent = rows.get(hs6) if children else None
        if parent and parent['amount'] != amount:
            output[period] = _empty(period, 'INVALID_DATA', 'HS6 소계와 하위 HSK10의 수출금액 합계가 다릅니다.', evidence)
            continue
        if (parent and parent['weight'] is not None
                and all(row['weight'] is not None for row in children.values())
                and parent['weight'] != sum((row['weight'] for row in children.values()), Decimal(0))):
            output[period] = _empty(period, 'INVALID_DATA', 'HS6 소계와 하위 HSK10의 순중량 합계가 다릅니다.', evidence)
            continue
        usable = [row for row in selected.values() if row['weight'] is not None and row['weight'] > 0]
        usable_amount = sum((row['amount'] for row in usable), Decimal(0))
        paired_weight = sum((row['weight'] for row in usable), Decimal(0))
        weight_states = [row['weight_status'] for row in selected.values()]
        zero_zero = sum(row['amount'] == 0 and row['weight'] == 0 for row in selected.values())
        weight_complete = len(usable) + zero_zero == len(selected)
        missing_weight = sum(row['amount'] > 0 and (row['weight'] is None or row['weight'] <= 0)
                             for row in selected.values())
        if weight_complete and usable:
            weight_status = 'COMPLETE'
        elif all(state == 'ZERO' for state in weight_states):
            weight_status = 'ZERO'
        elif all(state == 'MISSING' for state in weight_states):
            weight_status = 'MISSING'
        elif all(state == 'INVALID_DATA' for state in weight_states):
            weight_status = 'INVALID_DATA'
        else:
            weight_status = 'PARTIAL'
        observed_weight = (sum((row['weight'] for row in selected.values()), Decimal(0))
                           if all(row['weight'] is not None for row in selected.values()) else None)
        observation = _empty(period, 'OBSERVED_ZERO' if amount == 0 else 'OBSERVED', evidence=evidence)
        observation.update(value=_number(amount), usable_value_usd=_number(usable_amount),
                           net_weight_kg=_number(paired_weight), reported_net_weight_kg=_number(observed_weight),
                           records=len(selected), usable_records=len(usable),
                           excluded_records=len(selected)-len(usable)-zero_zero,
                           value_coverage_ratio=_number(usable_amount / amount) if amount > 0 else None,
                           weight_status=weight_status, weight_complete=weight_complete,
                           weight_missing_records=weight_states.count('MISSING'),
                           weight_invalid_records=weight_states.count('INVALID_DATA'), weight_zero_records=weight_states.count('ZERO'),
                           missing_weight_records=missing_weight, zero_zero_records=zero_zero,
                           zero_value_positive_weight_records=sum(row['amount'] == 0 for row in usable),
                           aggregation_basis='HSK10_SUM' if children else 'HS6', parent_row_excluded=bool(parent))
        if not weight_complete:
            observation['reason'] = '양의 순중량이 확인된 행의 금액·중량만 단가용 표본에 포함했습니다. 전체 금액과 구분합니다.'
        if observation['zero_value_positive_weight_records']:
            observation['reason'] = '금액 0·양의 중량 관측을 보존했습니다. 무상거래 등 거래 성격 확인 전 판매가격으로 해석하지 않습니다.'
        output[period] = observation
    return output


def _coverage(observations):
    observed = [row for row in observations if row['status'] in VALID]
    complete = len(observed) == len(observations)
    subtotal = sum((Decimal(str(row['value'])) for row in observed), Decimal(0))
    usable = sum((Decimal(str(row['usable_value_usd'])) for row in observed), Decimal(0))
    return {'expected_months': len(observations), 'observed_months': len(observed),
            'missing_or_invalid_months': [row['period'] for row in observations if row['status'] not in VALID],
            'amount_complete': complete, 'total_value_usd': _number(subtotal) if complete else None,
            'observed_value_usd': _number(subtotal) if observed else None,
            'usable_value_usd': _number(usable),
            'value_coverage_ratio': _number(usable / subtotal) if complete and subtotal > 0 else None,
            'weight_complete_months': sum(row['weight_complete'] for row in observed),
            'usable_months': sum(row['usable_records'] > 0 for row in observed),
            'records': sum(row['records'] for row in observed),
            'usable_records': sum(row['usable_records'] for row in observed),
            'excluded_records': sum(row['excluded_records'] for row in observed),
            'zero_zero_records': sum(row['zero_zero_records'] for row in observed),
            'missing_weight_records': sum(row['missing_weight_records'] for row in observed),
            'zero_value_positive_weight_records': sum(row['zero_value_positive_weight_records'] for row in observed)}


def collect_trade_reference(inputs, keys, progress=None, session=None):
    """Return the preceding 24 completed calendar months, split by year.

    ``inputs`` requires hs6, hs_edition='HS2022', as_of (ISO date). The API has
    no edition selector/echo; the requested classification and this limitation
    are retained. Months before 2022 are unavailable, never silently remapped.
    ``net_weight_kg`` is the paired usable-sample sum for compatibility with the
    country collector. ``reported_net_weight_kg`` is null if any selected row's
    weight is absent/invalid. No whole-analysis failure is raised for a source
    HTTP/business/parsing error or a missing credential.
    """
    try:
        as_of = date.fromisoformat(inputs['as_of'])
        hs6 = inputs['hs6']
        if inputs['hs_edition'] != 'HS2022' or not isinstance(hs6, str) or not re.fullmatch(r'[0-9]{6}', hs6):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise ValueError('전체 수출 참고자료의 HS2022 6자리·분석 기준일을 확인해 주세요.') from None
    periods = _periods(as_of)
    key = keys.get('KCS_TRADE_API_KEY', '') if isinstance(keys, dict) else ''
    key = key if isinstance(key, str) else ''
    safe_keys = {'KCS_TRADE_API_KEY': key}
    own_session = session is None
    session = session if session is not None else requests.Session()
    monthly, sources, access_error_source = {}, [], None
    try:
        for year in sorted({period[:4] for period in periods}):
            batch = [period for period in periods if period[:4] == year]
            if int(year) < 2022:
                monthly.update({p: _empty(p, 'INCOMPATIBLE_SCOPE', 'HS2022 시행 전 자료는 자동 연결하지 않습니다.') for p in batch})
                continue
            if access_error_source is not None:
                for period in batch:
                    monthly[period] = _empty(period, 'FETCH_ERROR',
                        '앞선 요청에서 서비스 접근·인증 오류가 확인되어 같은 서비스의 후속 요청을 보류했습니다.',
                        [{'source_id': access_error_source['id'], 'kind': 'blocked_request'}])
                    monthly[period]['collection_status'] = 'NOT_REQUESTED_AFTER_ACCESS_ERROR'
                access_error_source.setdefault('not_requested_periods', []).extend(batch)
                continue
            sid = f'kcs-all-{hs6}-{batch[0]}-{batch[-1]}'
            params = {'strtYymm': batch[0].replace('-', ''), 'endYymm': batch[-1].replace('-', ''),
                      'hsSgn': hs6, 'serviceKey': unquote(key)}
            if progress:
                progress(f'한국 전체 목적지 수출 {batch[0]}~{batch[-1]} 금액·중량 확인')
            if key:
                content, source = _fetch(session, KCS_ITEM_URL, params, '관세청 품목별 전체 수출', sid, safe_keys)
            else:
                content = None
                source = {'id': sid, 'provider': '관세청 품목별 전체 수출',
                          'retrieved_at': datetime.now(timezone.utc).isoformat(), 'sha256': None,
                          'status': 'FETCH_ERROR', 'reason': 'KCS_TRADE_API_KEY가 설정되지 않았습니다.',
                          'request': {'url': KCS_ITEM_URL, 'params': {k: v for k, v in params.items() if k != 'serviceKey'}}}
            source.update(adapter_version=VERSION, observed_period=f'{batch[0]}~{batch[-1]}',
                          official_metadata_url=OFFICIAL_URL, hs_edition='HS2022',
                          classification_verification='REQUEST_SCOPE_ONLY', partner_scope='ALL_DESTINATIONS',
                          valuation_basis='FOB', currency='USD', weight_unit='kg')
            if source.get('http_status') in (401, 403):
                source['authorization_error'] = True
            result = _parse_batch(content, source, hs6, batch)
            states = {row['status'] for row in result.values()}
            source['status'] = 'OBSERVED' if states <= VALID else next(iter(states)) if len(states) == 1 else 'PARTIAL'
            monthly.update(result)
            sources.append(source)
            if source.get('authorization_error'):
                access_error_source = source
    finally:
        if own_session:
            session.close()
    observations = [monthly[period] for period in periods]
    coverage = _coverage(observations)
    status = ('OBSERVED' if coverage['amount_complete'] and coverage['weight_complete_months'] == 24
              else 'PARTIAL' if coverage['observed_months'] else 'INSUFFICIENT')
    warnings = ['전 목적지 수출은 별도 Itemtrade 서비스입니다. 5개 후보국의 합계가 아닙니다.',
                'API에 HS판 선택·반환 필드가 없어 HS2022 입력 범위를 기록하며 분류판을 응답으로 독립 검증한 것은 아닙니다.',
                '현재 조회한 수정 통계입니다. 과거 기준일 당시 공표 상태를 재현한 자료가 아닙니다.',
                '금액 0·중량 0·중량 누락을 구분합니다. 무역통계 USD/kg은 개별 제품 판매가·수익성 또는 점수가 아닙니다.']
    if not coverage['amount_complete']:
        warnings.append('최근 24개월의 전체 수출금액이 완결되지 않아 전기간 총액·금액 커버리지는 미산출입니다.')
    if coverage['weight_complete_months'] != 24:
        warnings.append('중량>0인 행의 대응 금액만 단가용 표본에 포함합니다. 표본 허용 임계값은 결정하지 않았습니다.')
    return {'status': status, 'scope': {'hs6': hs6, 'hs_edition': 'HS2022', 'reporter': 'KR',
            'partner_scope': 'ALL_DESTINATIONS', 'flow': 'EXPORT', 'valuation_basis': 'FOB',
            'currency': 'USD', 'weight_unit': 'kg', 'as_of': as_of.isoformat(),
            'start_month': periods[0], 'end_month': periods[-1]},
            'monthly_exports': observations, 'sources': sources, 'coverage': coverage,
            'warnings': warnings, 'adapter_version': VERSION}
