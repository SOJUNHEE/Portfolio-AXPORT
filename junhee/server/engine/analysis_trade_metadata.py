# (junhee) 2026-09-27 sanghyeob/analysis_trade_metadata.py 에서 옮김. 바꾼 것: 패키지 import 경로·원본 자료 경로(junhee/data/raw)만. 계산 로직은 그대로.
"""Bounded, read-only explanations for missing monthly Comtrade observations.

Dataset availability is not an observation of a particular HS6 import flow.
Neither an empty response nor ``totalRecords == 0`` establishes zero trade,
non-publication, confidentiality, or the cause of a missing commodity row.

``diagnose_missing_months`` never mutates trade, imputes values, or scores data.
By default it checks missing observations in the last 12 completed months.
Explicit ``required_periods`` may include older months; newest missing months
take priority, subject to 12 months and two calendar-year batches. Each batch
uses getDA and getMetadata once (at most four logical requests; the shared
transport permits at most two HTTP attempts per request). Skips are explicit.

The API returns publication history inside ``notes``. As in the official UN
Python client, latest publication is selected locally, after validating dates.
This is a current lookup, not reconstruction of the API's historical state.

References:
https://uncomtrade.org/docs/un-comtrade-api/
https://github.com/uncomtrade/comtradeapicall/blob/main/src/comtradeapicall/Metadata.py
https://github.com/uncomtrade/comtradeapicall/blob/main/src/comtradeapicall/DataAvailability.py
"""

from collections import defaultdict
from datetime import date, datetime, timezone
import json
import re

import requests

from .market_data import _fetch, _redact


VERSION = 'comtrade-missing-metadata-v1'
DA_URL = 'https://comtradeapi.un.org/data/v1/getDA/C/M/HS'
METADATA_URL = 'https://comtradeapi.un.org/data/v1/getMetadata/C/M/HS'
REPORTERS = {'US': 842, 'CN': 156, 'JP': 392, 'DE': 276, 'VN': 704}
MAX_MONTHS = 12
MAX_YEAR_BATCHES = 2
CAUTION = ('데이터셋 등록·공표 이력은 해당 HS6 수입 관측이 아닙니다. '
           '결측을 무역 0·미공표·비밀처리로 판정하지 않습니다.')


class _InvalidScope(ValueError):
    pass


def _period(value):
    text = str(value)
    if re.fullmatch(r'[0-9]{6}', text):
        text = text[:4] + '-' + text[4:]
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}', text):
        raise ValueError('유효한 월이 아닙니다.')
    date.fromisoformat(text + '-01')
    return text


def _integer(value):
    if isinstance(value, bool) or not re.fullmatch(r'[0-9]+', str(value)):
        raise ValueError('유효한 정수가 아닙니다.')
    return int(value)


def _timestamp(value, *, optional=False):
    if optional and value in (None, ''):
        return None
    if not isinstance(value, str) or not re.fullmatch(
            r'[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T[0-9]{2}:[0-9]{2}:[0-9]{2}'
            r'(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})?)?', value):
        raise ValueError('공표일 형식을 확인할 수 없습니다.')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    # UN timestamps can lack an offset. UTC here is a comparison convention;
    # preserve the exact original timestamp in returned evidence.
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _validate_inputs(trade, inputs):
    try:
        anchor = date.fromisoformat(inputs['as_of'])
        if inputs['country'] not in REPORTERS or inputs['hs_edition'] != 'HS2022':
            raise ValueError
        if not isinstance(inputs['hs6'], str) or not re.fullmatch(r'[0-9]{6}', inputs['hs6']):
            raise ValueError
        if not isinstance(trade, dict) or not isinstance(trade.get('monthly_imports'), list):
            raise ValueError
        scope = trade.get('factor', {}).get('scope', {})
        if any(scope.get(key, inputs[key]) != inputs[key]
               for key in ('country', 'hs6', 'hs_edition', 'as_of')):
            raise ValueError
    except (ValueError, TypeError, KeyError, AttributeError):
        raise ValueError('원관측과 국가·HS2022 6자리·기준일 범위를 확인해 주세요.') from None
    return anchor


def _select_periods(trade, anchor, required_periods):
    observed = {}
    for row in trade['monthly_imports']:
        if not isinstance(row, dict):
            raise ValueError('월별 원관측 형식이 올바르지 않습니다.')
        period = _period(row.get('period'))
        if period in observed:
            raise ValueError('월별 원관측이 중복됩니다.')
        observed[period] = row
    missing = sorted(p for p, row in observed.items()
                     if row.get('status') == 'MISSING' and row.get('value') is None)
    anchor_month = anchor.strftime('%Y-%m')
    month_number = anchor.year * 12 + anchor.month - 1 - MAX_MONTHS
    recent_start = f'{month_number // 12:04d}-{month_number % 12 + 1:02d}'
    if required_periods is not None:
        if not isinstance(required_periods, (list, tuple, set, frozenset)):
            raise ValueError('필요 기간은 월 목록이어야 합니다.')
        required = {_period(p) for p in required_periods}
    else:
        required = None
    selected, skipped, years = [], [], set()
    for period in reversed(missing):
        reason = None
        if period < '2022-01':
            reason = 'HS2022 이전 기간은 진단하지 않습니다.'
        elif period >= anchor_month:
            reason = '기준일 이전의 완료 월만 진단합니다.'
        elif required is not None and period not in required:
            reason = '지정한 필요 기간에 포함되지 않습니다.'
        elif required is None and period < recent_start:
            reason = '기본 최근 12개월 범위 밖입니다.'
        elif len(selected) >= MAX_MONTHS:
            reason = '최신 결손 우선, 최대 12개월 조회 한도입니다.'
        elif period[:4] not in years and len(years) >= MAX_YEAR_BATCHES:
            reason = '최신 결손 우선, 최대 2개 연도 배치 조회 한도입니다.'
        if reason:
            skipped.append({'period': period, 'reason': reason})
        else:
            selected.append(period)
            years.add(period[:4])
    return sorted(selected), sorted(skipped, key=lambda item: item['period'])


def _row_scope(row, reporter, periods):
    if not isinstance(row, dict):
        raise ValueError('메타데이터 행 형식이 올바르지 않습니다.')
    period = _period(row.get('period'))
    if (period not in periods or str(row.get('reporterCode')) != str(reporter)
            or row.get('typeCode') != 'C' or row.get('freqCode') != 'M'):
        raise _InvalidScope('반환 국가·기간·상품·월별 범위가 요청과 다릅니다.')
    return period


def _availability(row, record, reporter, periods, anchor):
    period = _row_scope(row, reporter, periods)
    if row.get('classificationCode') != 'H6':
        raise _InvalidScope('데이터셋의 HS2022 분류를 확인할 수 없습니다.')
    dataset = _integer(row.get('datasetCode'))
    records = _integer(row.get('totalRecords'))
    original = row.get('isOriginalClassification')
    if original is not None and not isinstance(original, bool):
        raise ValueError('원분류 여부의 형식이 올바르지 않습니다.')
    first = _timestamp(row.get('firstReleased'), optional=True)
    last = _timestamp(row.get('lastReleased'), optional=True)
    if first and last and first > last:
        raise ValueError('최초·최종 공표일 순서가 올바르지 않습니다.')
    return period, {
        'listed': True, 'dataset_code': dataset, 'records': records,
        'classification': 'H6', 'first_released': row.get('firstReleased'),
        'published_at': row.get('lastReleased'),
        'published_after_as_of': last.date() > anchor if last else None,
        'is_original_classification': original,
        'record': record,
    }


def _metadata(row, record, reporter, periods, anchor, keys):
    period = _row_scope(row, reporter, periods)
    if row.get('classificationCode') not in (None, 'H6'):
        raise _InvalidScope('공표 이력의 HS2022 분류를 확인할 수 없습니다.')
    dataset = _integer(row.get('datasetCode'))
    notes = row.get('notes')
    if not isinstance(notes, list) or not notes:
        raise ValueError('공표 이력 목록이 없습니다.')
    publications = []
    for index, note in enumerate(notes, 1):
        if (_row_scope(note, reporter, periods) != period
                or _integer(note.get('datasetCode')) != dataset
                or note.get('classificationCode') != 'H6'):
            raise _InvalidScope('공표 이력의 데이터셋·기간·HS2022 범위가 다릅니다.')
        released = _timestamp(note.get('publicationDate'))
        short = note.get('publicationDateShort')
        local_date = datetime.fromisoformat(note['publicationDate'].replace('Z', '+00:00')).date()
        if short is not None and (not isinstance(short, str)
                                  or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', short)
                                  or date.fromisoformat(short) != local_date):
            raise ValueError('공표일과 공표일 요약이 일치하지 않습니다.')
        publications.append((released, index, note))
    latest_time = max(item[0] for item in publications)
    latest = [item for item in publications if item[0] == latest_time]
    if len(latest) > 1:
        raise ValueError('최신 공표 이력이 하나로 식별되지 않습니다.')
    released, index, note = latest[0]
    text_fields = ('publicationNote', 'importValuation', 'exportValuation',
                   'tradeSystem', 'currency', 'importPartnerCountry', 'exportPartnerCountry')
    details = {}
    for field in text_fields:
        value = note.get(field)
        if value is not None and not isinstance(value, str):
            raise ValueError('공표 이력의 설명 형식이 올바르지 않습니다.')
        details[field] = _redact(value, keys) if value is not None else None
    return period, {
        'dataset_code': dataset, 'classification': 'H6',
        'published_at': note['publicationDate'],
        'published_after_as_of': released.date() > anchor,
        'publication_note': details.pop('publicationNote'),
        'publication_count': len(notes), 'record': record, 'note': index,
        **details,
    }


def _parse(content, source, kind, reporter, periods, anchor, keys):
    if content is None:
        return {}, 'FETCH_ERROR'
    try:
        doc = json.loads(content)
        if not isinstance(doc, dict) or not isinstance(doc.get('data'), list):
            raise ValueError('메타데이터 목록이 없습니다.')
        if doc.get('error') or doc.get('errorMessage'):
            source.update(status='FETCH_ERROR', reason='Comtrade 메타데이터 업무 오류가 반환됐습니다.')
            return {}, 'FETCH_ERROR'
        rows = doc['data']
        if (len(rows) > len(periods)
                or (doc.get('count') is not None and _integer(doc['count']) != len(rows))):
            raise ValueError('메타데이터 응답 건수·중복·완전성을 확인할 수 없습니다.')
        parsed = {}
        for index, row in enumerate(rows, 1):
            if kind == 'availability':
                period, value = _availability(row, index, reporter, periods, anchor)
            else:
                period, value = _metadata(row, index, reporter, periods, anchor, keys)
            if period in parsed:
                raise ValueError('같은 월의 데이터셋이 중복됩니다.')
            parsed[period] = value
    except _InvalidScope as error:
        source.update(status='INVALID_SCOPE', reason=str(error))
        return {}, 'INVALID_SCOPE'
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, OverflowError):
        source.update(status='INVALID_DATA', reason='메타데이터 형식·건수·공표일을 검증할 수 없습니다.')
        return {}, 'INVALID_DATA'
    status = 'OBSERVED' if parsed else 'MISSING'
    source['status'] = status
    releases = [row['published_at'] for row in parsed.values() if row.get('published_at')]
    source['source_release_at'] = max(releases, key=_timestamp) if releases else None
    return parsed, status


def _diagnostic(period, availability, metadata, states, sources):
    failures = set(states)
    if 'INVALID_SCOPE' in failures:
        status, reason = 'METADATA_INVALID_SCOPE', '메타데이터의 요청 범위를 검증하지 못했습니다.'
    elif 'INVALID_DATA' in failures:
        status, reason = 'METADATA_INVALID_DATA', '메타데이터의 형식·공표 이력을 검증하지 못했습니다.'
    elif 'FETCH_ERROR' in failures:
        status, reason = 'METADATA_LOOKUP_FAILED', '메타데이터 조회가 완료되지 않아 결측 원인을 판단할 수 없습니다.'
    elif availability and metadata and availability['dataset_code'] != metadata['dataset_code']:
        status, reason = 'METADATA_INVALID_SCOPE', '등록 목록과 공표 이력의 데이터셋 식별자가 다릅니다.'
    elif availability or metadata:
        status, reason = ('DATASET_LISTED_NO_OBSERVATION',
                          '같은 국가·월·HS2022 데이터셋은 등록되어 있으나 요청한 HS6 수입 원관측은 없습니다.')
    else:
        status, reason = ('DATASET_NOT_LISTED',
                          '이번 조회의 등록 목록·공표 이력에서 같은 국가·월·HS2022 데이터셋을 찾지 못했습니다.')
    evidence = []
    for kind, source, value in zip(('availability', 'metadata'), sources, (availability, metadata)):
        evidence.append({'source_id': source['id'], 'period': period, 'kind': kind,
                         'record': value.get('record') if value else None,
                         **({'note': value['note']} if value and 'note' in value else {})})
    return {
        'period': period, 'observation_status': 'MISSING', 'value': None,
        'diagnostic_status': status, 'reason': reason + ' ' + CAUTION,
        'availability': availability or {'listed': False if states[0] == 'MISSING' else None},
        'metadata': metadata, 'lookup_status': dict(zip(('availability', 'metadata'), states)),
        'evidence': evidence,
    }


def diagnose_missing_months(trade, inputs, keys=None, *, session=None, required_periods=None):
    """Return dataset-level diagnostics and sources, without editing ``trade``.

    ``required_periods`` selects missing original observations, not invented rows.
    FETCH_ERROR/INVALID_SCOPE observations and observed zeroes are not diagnosed
    as missing. A missing key is a lookup failure and makes no HTTP requests.
    An injected requests-compatible session is borrowed and never closed here.
    ``requests_planned/executed`` count logical calls, not transport retries.
    """
    anchor = _validate_inputs(trade, inputs)
    periods, skipped = _select_periods(trade, anchor, required_periods)
    reporter = REPORTERS[inputs['country']]
    batches = defaultdict(list)
    for period in periods:
        batches[period[:4]].append(period)
    result = {
        'scope': {key: inputs[key] for key in ('country', 'hs6', 'hs_edition', 'as_of')},
        'diagnostics': [], 'sources': [], 'checked_periods': periods,
        'skipped_periods': [item['period'] for item in skipped], 'skipped': skipped,
        'requests_planned': 2 * len(batches), 'requests_executed': 0,
        'limits': {'max_months': MAX_MONTHS, 'max_year_batches': MAX_YEAR_BATCHES,
                   'priority': 'LATEST_MISSING_FIRST', 'default_recent_months': 12},
        'warning': CAUTION + ' 현재 조회 결과이며 기준일 당시의 제공 상태를 재현하지 않습니다.',
        'adapter_version': VERSION,
    }
    result['scope'].update(reporter_code=reporter, type_code='C', frequency='M',
                           classification='H6', data_level='DATASET', lookup_basis='CURRENT_LOOKUP')
    if not periods:
        return result
    keys = keys or {}
    key = keys.get('UN_COMTRADE_API_KEY')
    authenticated = isinstance(key, str) and bool(key.strip())
    own_session = session is None and authenticated
    client = requests.Session() if own_session else session
    try:
        for year in sorted(batches, reverse=True):
            batch = batches[year]
            parsed, states, sources = [], [], []
            for kind, url in (('availability', DA_URL), ('metadata', METADATA_URL)):
                source_id = f'comtrade:{inputs["country"]}:metadata:{kind}:{year}'
                params = {'reporterCode': str(reporter), 'period': ','.join(p.replace('-', '') for p in batch)}
                if authenticated:
                    params['subscription-key'] = key
                    content, source = _fetch(client, url, params, 'UN Comtrade', source_id, keys)
                    result['requests_executed'] += 1
                else:
                    content = None
                    source = {'id': source_id, 'provider': 'UN Comtrade',
                              'retrieved_at': datetime.now(timezone.utc).isoformat(),
                              'request': {'url': url, 'params': params}, 'sha256': None,
                              'source_release_at': None, 'status': 'FETCH_ERROR',
                              'reason': 'UN Comtrade 인증 설정이 없어 메타데이터를 조회하지 않았습니다.'}
                source.update(adapter_version=VERSION, observed_period=f'{batch[0]} ~ {batch[-1]}',
                              data_level='DATASET', metadata_kind=kind)
                rows, state = _parse(content, source, kind, reporter, batch, anchor, keys)
                parsed.append(rows)
                states.append(state)
                sources.append(source)
            result['sources'].extend(sources)
            for period in batch:
                # An absent row in a valid nonempty batch is still a successful
                # empty lookup for that month, not a failed metadata request.
                period_states = [state if state not in ('OBSERVED', 'MISSING') else
                                 ('OBSERVED' if period in rows else 'MISSING')
                                 for rows, state in zip(parsed, states)]
                result['diagnostics'].append(_diagnostic(
                    period, parsed[0].get(period), parsed[1].get(period), period_states, sources))
    finally:
        if own_session:
            client.close()
    result['diagnostics'].sort(key=lambda item: item['period'])
    return result
