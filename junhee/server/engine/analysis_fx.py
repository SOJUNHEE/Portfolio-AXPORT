# (junhee) 2026-09-27 sanghyeob/analysis_fx.py 에서 옮김. 바꾼 것: 패키지 import 경로·원본 자료 경로(junhee/data/raw)만. 계산 로직은 그대로.
"""ECOS settlement-currency references, isolated from market scores.

Official definitions: https://ecos.bok.or.kr/api/ . The five initial item codes
were verified against the provider's 731Y001 metadata. Each collection validates
them again; codes alone never establish the rate's unit or meaning.

``collect_fx(company, inputs, keys, progress=None, session=None)`` accepts a
requests-compatible session (GET, streaming response and close). It reads no
files, stores no authenticated URL/raw response, and never interpolates dates.
The returned 60-observation statistic is only a reference: a complete calendar
of expected publication dates is not supplied by this adapter.
"""

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, localcontext
from hashlib import sha256
import json
import math
import re
import statistics
import time
from urllib.parse import quote, unquote

import requests

from .company_import import normalized_hs


BASE = 'https://ecos.bok.or.kr/api'
TABLE = '731Y001'
VERSION = 'ecos-settlement-fx-v1'
MAX_BYTES = 2 * 1024 * 1024
TIMEOUT = (5, 15)
LOOKBACK_DAYS = 180
SUPPORTED = {
    'USD': {'item': '0000001', 'name': '원/미국달러(매매기준율)', 'quote_units': 1, 'rate_type': '매매기준율'},
    'CNY': {'item': '0000053', 'name': '원/위안(매매기준율)', 'quote_units': 1, 'rate_type': '매매기준율'},
    'JPY': {'item': '0000002', 'name': '원/일본엔(100엔)', 'quote_units': 100, 'rate_type': 'ECOS 항목 정의 고시환율'},
    'EUR': {'item': '0000003', 'name': '원/유로', 'quote_units': 1, 'rate_type': 'ECOS 항목 정의 고시환율'},
    'VND': {'item': '0000035', 'name': '원/베트남동(100동)', 'quote_units': 100, 'rate_type': 'ECOS 항목 정의 고시환율'},
}
COUNTRIES = {'US': {'US', 'USA', '미국'}, 'CN': {'CN', 'CHINA', '중국'},
             'JP': {'JP', 'JAPAN', '일본'}, 'DE': {'DE', 'GERMANY', '독일'},
             'VN': {'VN', 'VIETNAM', '베트남'}}


def _text(value):
    return '' if value is None else str(value).strip()


def _canonical(value):
    return re.sub(r'\s+', '', _text(value))


def _date(value):
    try:
        return date.fromisoformat(_text(value)[:10])
    except ValueError:
        return None


def _api_date(value):
    value = _text(value)
    if not re.fullmatch(r'[0-9]{8}', value):
        raise ValueError
    return date(int(value[:4]), int(value[4:6]), int(value[6:]))


def _safe(value, key):
    """Never return a configured key, including common URL encodings."""
    if isinstance(value, str):
        variants = {key, unquote(key), quote(key, safe=''), quote(unquote(key), safe='')} - {''}
        for secret in sorted(variants, key=len, reverse=True):
            value = value.replace(secret, '[REDACTED]')
        return value
    if isinstance(value, list):
        return [_safe(item, key) for item in value]
    if isinstance(value, dict):
        return {_safe(k, key): _safe(v, key) for k, v in value.items()}
    return value


def _metric(identifier, label, currency=None, value=None, unit='ratio', period=None,
            status='INSUFFICIENT', reason=None, evidence=None, formula=''):
    return {'id': identifier + (':' + currency if currency else ''), 'label': label,
            'currency': currency, 'value': value, 'unit': unit, 'period': period,
            'status': status, 'reason': reason, 'evidence': evidence or [], 'formula': formula}


def _source_id(service, currency, start, end):
    return f'ecos-{service}-{TABLE}-{currency or "metadata"}-{start}-{end}'


def _invalid_json_constant(value):
    raise ValueError('Non-finite JSON value')


def _finite_json_float(value):
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError('Non-finite JSON value')
    return parsed


def _fetch(session, key, service, currency, start, end):
    """Only safe structured request arguments survive this function."""
    request = {'host': 'https://ecos.bok.or.kr', 'service': service, 'format': 'json',
               'language': 'kr', 'start_index': 1, 'end_index': 1000 if service == 'StatisticItemList' else 500,
               'stat_code': TABLE}
    if currency:
        request.update(item_code=SUPPORTED[currency]['item'], cycle='D', start_date=start, end_date=end)
    source = {'id': _source_id(service, currency, start, end), 'provider': '한국은행 ECOS',
              'retrieved_at': datetime.now(timezone.utc).isoformat(), 'request': request,
              'sha256': None, 'status': 'FETCH_ERROR', 'adapter_version': VERSION,
              'sha256_scope': 'decoded_response_bytes',
              'source_release_at': None, 'raw_stored': False}
    if not key:
        source.update(status='KEY_NOT_CONFIGURED', reason='ECOS 인증키가 설정되지 않았습니다.')
        return None, source
    parts = [service, quote(key, safe=''), 'json', 'kr', '1', str(request['end_index']), TABLE]
    if currency:
        parts += ['D', start, end, SUPPORTED[currency]['item']]
    url = BASE + '/' + '/'.join(parts)
    for attempt in range(2):
        response, retry, delay = None, False, .5
        try:
            response = session.get(url, headers={'Accept': 'application/json'}, timeout=TIMEOUT,
                                   allow_redirects=False, stream=True)
            source['http_status'] = response.status_code
            if response.status_code in (429, 500, 502, 503, 504):
                retry = True
                raw_delay = response.headers.get('Retry-After', '')
                if raw_delay:
                    try:
                        proposed = float(raw_delay)
                        if not math.isfinite(proposed) or proposed < 0 or proposed > 5:
                            retry = False
                        else:
                            delay = max(.5, proposed)
                    except (TypeError, ValueError):
                        # Do not retry before an unparsed provider deadline.
                        retry = False
            elif response.status_code == 200:
                length = response.headers.get('Content-Length')
                identity_encoding = _text(response.headers.get('Content-Encoding')).lower() in ('', 'identity')
                if length and (not str(length).isdigit() or int(length) > MAX_BYTES):
                    source.update(status='INVALID_DATA', reason='ECOS 응답 크기 제한을 초과하거나 형식이 다릅니다.')
                    return None, source
                chunks, size = [], 0
                for chunk in response.iter_content(chunk_size=65536):
                    if not isinstance(chunk, bytes):
                        raise ValueError
                    size += len(chunk)
                    if size > MAX_BYTES:
                        source.update(status='INVALID_DATA', reason='ECOS 응답 크기 제한을 초과했습니다.')
                        return None, source
                    chunks.append(chunk)
                content = b''.join(chunks)
                source['sha256'] = sha256(content).hexdigest()
                # requests.iter_content decodes gzip/deflate before yielding bytes.
                # Content-Length measures wire bytes and is comparable only for identity.
                if identity_encoding and length and size != int(length):
                    source.update(status='INVALID_DATA', reason='ECOS 응답 길이가 선언된 크기와 다릅니다.')
                    return None, source
                try:
                    doc = json.loads(content, parse_constant=_invalid_json_constant, parse_float=_finite_json_float)
                except (ValueError, UnicodeError):
                    source.update(status='INVALID_DATA', reason='ECOS JSON 응답을 읽을 수 없습니다.')
                    return None, source
                if not isinstance(doc, dict):
                    source.update(status='INVALID_DATA', reason='ECOS 응답 구조가 올바르지 않습니다.')
                    return None, source
                if isinstance(doc.get('RESULT'), dict):
                    empty = doc['RESULT'].get('CODE') == 'INFO-200'
                    source.update(status='MISSING' if empty else 'FETCH_ERROR',
                                  reason='요청한 ECOS 관측이 없습니다.' if empty else 'ECOS 업무 응답이 정상적이지 않습니다.')
                    return None, source
                source['status'] = 'RECEIVED'
                return doc, source
            else:
                break
        except requests.RequestException:
            retry = True
        except Exception:
            # Neither an exception message nor its authenticated request is persisted.
            break
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
        if not retry or attempt == 1:
            break
        time.sleep(delay)
    source['reason'] = 'ECOS 요청에 실패했습니다. 인증·이용한도·연결 상태를 확인해 주세요.'
    return None, source


def _rows(doc, service, maximum):
    block = doc.get(service)
    if not isinstance(block, dict) or not isinstance(block.get('row'), list):
        raise ValueError('ECOS 관측 목록이 없습니다.')
    rows = block['row']
    count = block.get('list_total_count')
    if (isinstance(count, bool) or not re.fullmatch(r'[0-9]+', _text(count))
            or int(count) != len(rows) or len(rows) > maximum or any(not isinstance(r, dict) for r in rows)):
        raise ValueError('ECOS 총건수·반환건수·잘림 여부가 일치하지 않습니다.')
    return rows


def _metadata(rows, currency):
    expected = SUPPORTED[currency]
    matched = [(n, row) for n, row in enumerate(rows, 1) if _text(row.get('ITEM_CODE')) == expected['item']]
    if len(matched) != 1:
        raise ValueError('ECOS 항목 정의가 없거나 중복되어 확인할 수 없습니다.')
    number, row = matched[0]
    if (_text(row.get('STAT_CODE')) != TABLE or '환율' not in _text(row.get('STAT_NAME'))
            or _text(row.get('CYCLE')) != 'D' or _text(row.get('UNIT_NAME')) != '원'
            or _canonical(row.get('ITEM_NAME')) != _canonical(expected['name'])):
        raise ValueError('ECOS 통계표·통화·환율 종류·고시단위 정의가 예상 범위와 다릅니다.')
    try:
        first, last = _api_date(row.get('START_TIME')), _api_date(row.get('END_TIME'))
        if first > last:
            raise ValueError
    except ValueError:
        raise ValueError('ECOS 항목의 수록기간을 확인할 수 없습니다.') from None
    return {'record': number, 'stat_code': TABLE, 'stat_name': row['STAT_NAME'],
            'item_code': expected['item'], 'item_name': row['ITEM_NAME'], 'cycle': 'D',
            'unit_raw': '원', 'quote_units': expected['quote_units'], 'currency': currency,
            'rate_type': expected['rate_type'], 'start_date': first.isoformat(), 'end_date': last.isoformat()}


def _positive(value):
    if value is None or isinstance(value, bool):
        raise ValueError
    text = _text(value)
    if not re.fullmatch(r'(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?', text):
        raise ValueError
    try:
        result = Decimal(text.replace(',', ''))
    except InvalidOperation:
        raise ValueError from None
    if not result.is_finite() or not Decimal('1e-12') <= result <= Decimal('1e15'):
        raise ValueError
    return result


def _observations(rows, metadata, source_id, start, end):
    seen, result = set(), []
    for number, row in enumerate(rows, 1):
        try:
            day = _api_date(row.get('TIME')).isoformat()
        except ValueError:
            raise ValueError('ECOS 관측일 형식이 유효하지 않습니다.') from None
        if day in seen:
            raise ValueError('ECOS 관측일이 중복되어 같은 시계열로 사용할 수 없습니다.')
        seen.add(day)
        if (not start <= day <= end or not metadata['start_date'] <= day <= metadata['end_date']
                or _text(row.get('STAT_CODE')) != TABLE or _text(row.get('ITEM_CODE1')) != metadata['item_code']
                or _canonical(row.get('ITEM_NAME1')) != _canonical(metadata['item_name'])
                or _text(row.get('UNIT_NAME')) != '원'
                or any(_text(row.get(f'ITEM_CODE{i}')) for i in (2, 3, 4))
                or ('CYCLE' in row and row['CYCLE'] != 'D')):
            raise ValueError('ECOS 관측의 통계표·항목·단위·기간 범위가 메타데이터와 다릅니다.')
        reference = {'source_id': source_id, 'record': number, 'field': 'DATA_VALUE',
                     'observation_date': day, 'stat_code': TABLE, 'item_code': metadata['item_code']}
        raw = row.get('DATA_VALUE')
        observation = {'period': day, 'observation_date': day, 'value_raw': raw, 'value': None,
                       'unit_raw': '원', 'quote_units': metadata['quote_units'],
                       'unit': 'KRW/' + metadata['currency'], 'status': 'MISSING', 'evidence': [reference]}
        if raw is not None and _text(raw):
            try:
                observation.update(value=float(_positive(raw) / metadata['quote_units']), status='OBSERVED')
            except ValueError:
                observation['status'] = 'INVALID_DATA'
                observation['reason'] = '환율은 유한한 양수여야 합니다.'
        else:
            observation['reason'] = '반환된 날짜의 환율이 비어 있습니다. 건너뛰어 연결하지 않습니다.'
        result.append(observation)
    return sorted(result, key=lambda row: row['period'])


def _currencies(company, inputs, as_of):
    sheets = company.get('sheets', {})
    selected = set()
    raw_scope = normalized_hs(inputs.get('hs_raw', inputs['hs6']))
    for row in sheets.get('제품정보', []):
        hs = normalized_hs(row.get('HS코드'))
        if (hs.startswith(inputs['hs6']) and (len(raw_scope) == 6 or hs == raw_scope)
                and _canonical(row.get('HS버전')).upper() == 'HS2022'):
            selected.add(_text(row.get('제품ID')))
    currencies, refs, missing = set(), {}, 0
    # The simple form's cost currency also needs a rate for the explicitly
    # labelled planned product-cost scenario. Never infer destination currency.
    currency_sheets = ['수출예정거래', '수출실적']
    if company.get('source', {}).get('workbook_format') == 'company-simple-v2':
        currency_sheets.append('원가·비용')
    for sheet in currency_sheets:
        for row in sheets.get(sheet, []):
            if (_text(row.get('제품ID')) not in selected
                    or (sheet != '원가·비용' and _text(row.get('목적국')).upper() not in COUNTRIES[inputs['country']])):
                continue
            if sheet == '수출실적':
                occurred = _date(row.get('거래일'))
                if (occurred is None or occurred > as_of
                        or _text(row.get('취소반품')).upper() not in ('', 'N', 'NO', 'FALSE', '0', '정상', '아니오')):
                    continue
            currency = _text(row.get('통화')).upper()
            if not re.fullmatch(r'[A-Z]{3}', currency):
                missing += 1
                continue
            currencies.add(currency)
            refs.setdefault(currency, []).append({'source_id': company.get('source', {}).get('id', 'company-upload'),
                'sheet': row.get('_sheet', sheet), 'row': row.get('_row'), 'field': '통화'})
    return sorted(currencies), refs, missing


def _currency_metrics(currency, metadata, observations, refs, status=None, reason=None):
    definition_refs = refs
    latest = observations[-1] if observations else None
    chosen = observations[-61:]
    available = len(chosen) == 61 and all(row['status'] == 'OBSERVED' for row in chosen)
    value, returns = None, []
    if available:
        for previous, current in zip(chosen, chosen[1:]):
            with localcontext() as context:
                context.prec = 32
                # Quote scaling cancels; use provider values before float conversion.
                change = float((_positive(current['value_raw']) / _positive(previous['value_raw'])).ln())
            returns.append({'from': previous['period'], 'to': current['period'], 'value': change,
                            'elapsed_calendar_days': (date.fromisoformat(current['period']) - date.fromisoformat(previous['period'])).days})
        value = statistics.stdev(row['value'] for row in returns)
    period = f'{chosen[0]["period"]}~{chosen[-1]["period"]}' if chosen else None
    evidence = definition_refs + [ref for row in chosen for ref in row['evidence']]
    issue = status or ('CALENDAR_UNVERIFIED' if available else 'INSUFFICIENT' if len(chosen) < 61 else 'INVALID_DATA')
    note = reason or ('61개 관측으로 계산한 참고값입니다. 공표 달력이 없어 60거래일 완전성은 확인하지 못했습니다.'
                      if available else '61개 연속 반환 관측이 필요하며 빈값·오류 날짜를 건너뛰어 계산하지 않습니다.')
    latest_status = status or (latest['status'] if latest else 'MISSING')
    metrics = [
        _metric('fx_reference_rate', f'{currency} 최신 공표 참고환율', currency,
                latest['value'] if latest else None, 'KRW/' + currency, latest['period'] if latest else None,
                latest_status, reason or '실제 관측일의 참고환율이며 은행 체결환율·수수료를 대신하지 않습니다.',
                definition_refs + (latest['evidence'] if latest else []), '원 고시환율 / 고시통화량'),
        _metric('fx_volatility_60obs', f'{currency} 최근 60개 관측간격 로그변화 표준편차(참고)', currency,
                value, 'ratio', period, issue, note, evidence,
                '61개 환율 수준 → ln(e[i]/e[i-1]) 60개 → 표본표준편차(ddof=1), 비연율화'),
        _metric('fx_volatility_60d', f'{currency} 60거래일 환율 변동성', currency,
                status=status or 'CALENDAR_UNVERIFIED', period=period, reason=reason or '계열별 기대 공표일을 검증하기 전까지 확정 지표를 산출하지 않습니다.',
                evidence=evidence, formula='61개 수준·60개 일별 로그변화 및 기대 공표일 완전성 검증 필요'),
    ]
    return metrics, {'currency': currency, **(metadata or {}), 'observations': observations,
                     'selected_observations': deepcopy(chosen), 'log_returns': returns,
                     'observed_levels': sum(row['status'] == 'OBSERVED' for row in observations),
                     'selected_levels': len(chosen), 'calendar_status': 'UNVERIFIED',
                     'complete_60_business_days': False}


def collect_fx(company, inputs, keys, progress=None, session=None):
    """Return separate currency series and evidence; never a country FX score."""
    as_of = _date(inputs.get('as_of'))
    if (as_of is None or inputs.get('country') not in COUNTRIES or inputs.get('hs_edition') != 'HS2022'
            or not re.fullmatch(r'[0-9]{6}', _text(inputs.get('hs6')))):
        raise ValueError('환율 분석의 기준일·국가·HS 범위를 확인해 주세요.')
    key = _text(keys.get('ECOS_API_KEY'))
    currencies, company_refs, missing = _currencies(company, inputs, as_of)
    result = {'key': 'fx', 'label': '결제통화 환율', 'state': 'insufficient', 'score': None,
              'score_status': 'PENDING_METHODOLOGY', 'method_version': VERSION,
              'settlement_currencies': currencies, 'calendar_status': 'UNVERIFIED',
              'metrics': [], 'series': [], 'sources': [], 'checks': [],
              'warnings': ['기업 거래 및 간편양식 제품원가에 기재된 통화만 확인합니다. 목적국 통화로 추정하지 않으며 실제 순노출·헤지·손익을 판정하지 않습니다.',
                           '60개 관측간격 참고값과 60거래일 완결 지표를 구분합니다. 결측 보간·휴일 환율 생성·연율화는 하지 않습니다.']}
    if company.get('source'):
        result['sources'].append({'provider': '기업 업로드', **deepcopy(company['source'])})
    if missing:
        result['warnings'].append(f'선택 거래 {missing}행의 결제통화가 없거나 형식을 확인하지 못했습니다.')
    result['checks'].append({'label': '선택 거래의 통화', 'status': 'PARTIAL' if missing else 'OBSERVED' if currencies else 'MISSING',
                             'detail': ', '.join(currencies) if currencies else '실제 결제통화가 확인되지 않았습니다.'})
    if not currencies:
        result['metrics'].append(_metric('fx_volatility_60d', '결제통화 환율 변동성',
                                         status='CURRENCY_MISSING', reason='선택 거래의 실제 결제통화를 입력해 주세요.'))
        return _safe(result, key)
    start, end = (as_of - timedelta(days=LOOKBACK_DAYS)).strftime('%Y%m%d'), as_of.strftime('%Y%m%d')
    supported = [currency for currency in currencies if currency in SUPPORTED]
    own_session = session is None
    session = session or requests.Session()
    metadata_rows, metadata_source = None, None
    try:
        if supported:
            if progress:
                progress('ECOS 결제통화의 일별 계열·고시단위를 확인합니다.')
            doc, metadata_source = _fetch(session, key, 'StatisticItemList', None, start, end)
            result['sources'].append(metadata_source)
            if doc is not None:
                try:
                    metadata_rows = _rows(doc, 'StatisticItemList', 1000)
                    metadata_source['status'] = 'OBSERVED'
                    metadata_source['excerpt'] = {'list_total_count': len(metadata_rows), 'validated_items': []}
                except ValueError as exc:
                    metadata_source.update(status='INVALID_DATA', reason=str(exc))
        for currency in currencies:
            refs = company_refs[currency]
            if currency == 'KRW':
                result['metrics'].append(_metric('fx_reference_rate', 'KRW 직접 환산 기준', currency, 1, 'KRW/KRW',
                    as_of.isoformat(), 'IDENTITY', '원화 직접 환산 관계입니다. 수입원가 등 간접 환율 노출이 없다는 뜻은 아닙니다.', refs, 'KRW/KRW = 1'))
                result['metrics'].append(_metric('fx_volatility_60d', 'KRW 직접 환산 변동성', currency,
                    status='NOT_APPLICABLE', reason='원화 직접 환산을 외화 시장 변동성이나 무위험으로 평가하지 않습니다.', evidence=refs))
                continue
            if currency not in SUPPORTED:
                metrics, series = _currency_metrics(currency, None, [], refs, 'UNSUPPORTED_CURRENCY',
                    '이 통화의 ECOS 계열·단위 매핑은 아직 검증되지 않았습니다. 다른 통화로 대체하지 않습니다.')
                result['metrics'].extend(metrics)
                result['series'].append(series)
                continue
            refs = refs + [{'source_id': metadata_source['id'], 'field': 'ITEM_CODE/ITEM_NAME/CYCLE/UNIT_NAME'}]
            if metadata_rows is None:
                metrics, series = _currency_metrics(currency, None, [], refs, metadata_source['status'], metadata_source['reason'])
                result['metrics'].extend(metrics)
                result['series'].append(series)
                continue
            try:
                metadata = _metadata(metadata_rows, currency)
            except ValueError as exc:
                metrics, series = _currency_metrics(currency, None, [], refs, 'INVALID_METADATA', str(exc))
                result['metrics'].extend(metrics)
                result['series'].append(series)
                continue
            metadata_source['excerpt']['validated_items'].append(metadata)
            if progress:
                progress(f'{currency} 실제 일별 환율과 61개 관측을 확인합니다.')
            doc, source = _fetch(session, key, 'StatisticSearch', currency, start, end)
            result['sources'].append(source)
            refs = refs + [{'source_id': source['id']}]
            observations = []
            if doc is not None:
                try:
                    rows = _rows(doc, 'StatisticSearch', 500)
                    observations = _observations(rows, metadata, source['id'],
                                                 (as_of - timedelta(days=LOOKBACK_DAYS)).isoformat(), as_of.isoformat())
                    if (start <= metadata['end_date'].replace('-', '') <= end
                            and (not observations or observations[-1]['period'] != metadata['end_date'])):
                        observations = []
                        raise ValueError('ECOS 메타데이터의 마지막 수록일이 응답에 없어 완전성을 확인하지 못했습니다.')
                    source['status'] = 'OBSERVED' if observations and all(o['status'] == 'OBSERVED' for o in observations) else 'PARTIAL' if observations else 'MISSING'
                    source['observed_period'] = f'{observations[0]["period"]}~{observations[-1]["period"]}' if observations else None
                    source['excerpt'] = {'list_total_count': len(rows), 'definition': metadata,
                                         'selected_observations': deepcopy(observations[-61:])}
                except ValueError as exc:
                    source.update(status='INVALID_DATA', reason=str(exc))
            metrics, series = _currency_metrics(currency, metadata, observations, refs,
                source['status'] if not observations else None,
                source.get('reason') if not observations else None)
            if observations:
                series['days_since_latest_observation'] = (as_of - date.fromisoformat(observations[-1]['period'])).days
            result['metrics'].extend(metrics)
            result['series'].append(series)
    finally:
        if own_session:
            try:
                session.close()
            except Exception:
                pass
    result['state'] = 'partial' if any(m['value'] is not None for m in result['metrics']) else 'insufficient'
    result['checks'].append({'label': '60거래일 공표 완전성', 'status': 'CALENDAR_UNVERIFIED',
                             'detail': '계열별 공표 달력은 미확인입니다. 61개 값 확보만으로 연속 60거래일이라고 표시하지 않습니다.'})
    return _safe(result, key)
