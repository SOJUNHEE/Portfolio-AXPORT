# (junhee) 2026-09-27 sanghyeob/market_data.py 에서 옮김. 바꾼 것: 패키지 import 경로·원본 자료 경로(junhee/data/raw)만. 계산 로직은 그대로.
"""Annual market evidence, without scores or Flask dependencies.

``collect_market(..., session=...)`` accepts a requests-compatible object whose
``get(url, params, headers, timeout, allow_redirects)`` returns a response with
``status_code``, ``content`` and ``close()``. Tests use this boundary without
credentials or network access. This module never writes files or logs URLs.

Comtrade: the live-verified annual HS route uses subscription-key in the query.
HS is the request family, not permission to mix revisions: every returned row
must explicitly declare H6 (HS 2022), otherwise it is rejected. KCS:
data.go.kr/data/15100475/openapi.do, annual requests cover at most 12 months.
"""

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
from email.utils import parsedate_to_datetime
import hashlib
import json
import math
import re
from threading import Lock
import time
from urllib.parse import quote, unquote
import xml.etree.ElementTree as ET

import requests


COUNTRIES = {
    'US': {'name': '미국', 'reporter_code': 842},
    'CN': {'name': '중국', 'reporter_code': 156},
}
COMTRADE_URL = 'https://comtradeapi.un.org/data/v1/get/C/A/HS'
KCS_URL = 'https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList'
TIMEOUT = (5, 20)
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
VALID_STATUSES = {'OBSERVED', 'OBSERVED_ZERO'}
MODULE_VERSION = 'annual-market-v1'
COMTRADE_MIN_INTERVAL = 1.0
MAX_RETRY_DELAY = 30.0
_COMTRADE_LOCK = Lock()
_COMTRADE_NEXT_AT = 0.0


def _wait_comtrade_turn():
    """Space request starts across collectors in this process, including retries."""
    global _COMTRADE_NEXT_AT
    with _COMTRADE_LOCK:
        delay = _COMTRADE_NEXT_AT - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        _COMTRADE_NEXT_AT = time.monotonic() + COMTRADE_MIN_INTERVAL


def _postpone_comtrade(delay):
    global _COMTRADE_NEXT_AT
    with _COMTRADE_LOCK:
        _COMTRADE_NEXT_AT = max(_COMTRADE_NEXT_AT, time.monotonic() + delay)


def _retry_delay(response, now=None):
    """Bound Retry-After seconds or HTTP dates; malformed values wait two seconds."""
    headers = getattr(response, 'headers', {}) or {}
    value = str(headers.get('Retry-After', '')).strip()
    try:
        seconds = float(value)
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError
    except (ValueError, TypeError):
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                raise ValueError
            seconds = max(0.0, (retry_at - (now or datetime.now(timezone.utc))).total_seconds())
        except (ValueError, TypeError, OverflowError):
            seconds = 2.0
    return min(MAX_RETRY_DELAY, seconds)


def validate_inputs(payload, today=None):
    """Validate the first release's two-country, HS2022, complete-year scope."""
    today = today or date.today()
    if not isinstance(payload, dict):
        raise ValueError('분석 입력은 객체 형식이어야 합니다.')
    result = {}
    for key, label in (('company', '기업명'), ('product', '제품명')):
        value = payload.get(key)
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= 120:
            raise ValueError(f'{label}은 1~120자의 문자열로 입력해 주세요.')
        if any(ord(ch) < 32 for ch in value):
            raise ValueError(f'{label}에 제어 문자를 사용할 수 없습니다.')
        result[key] = value.strip()
    hs6 = payload.get('hs6')
    if not isinstance(hs6, str) or not re.fullmatch(r'[0-9]{6}', hs6):
        raise ValueError('HS 코드는 앞자리 0을 보존한 6자리 숫자로 입력해 주세요.')
    if payload.get('hs_edition', 'HS2022') != 'HS2022':
        raise ValueError('현재는 HS2022 분류만 비교할 수 있습니다.')
    countries = payload.get('countries')
    if (not isinstance(countries, list) or len(countries) != 2
            or any(not isinstance(c, str) or c not in COUNTRIES for c in countries)
            or len(set(countries)) != 2):
        raise ValueError('서로 다른 두 비교국을 선택해 주세요. 현재는 미국과 중국을 지원합니다.')
    year = payload.get('year', today.year - 1)
    if isinstance(year, str) and re.fullmatch(r'[0-9]{4}', year):
        year = int(year)
    if isinstance(year, bool) or not isinstance(year, int) or not 2025 <= year < today.year:
        raise ValueError('기준연도는 2025년부터 직전 완결연도까지 선택할 수 있습니다.')
    result.update(hs6=hs6, hs_edition='HS2022', countries=list(countries), year=year)
    return result


def _decimal(value):
    if value is None or isinstance(value, bool):
        raise ValueError('금액이 없거나 숫자 형식이 아닙니다.')
    text = str(value).strip()
    # Commas are accepted only as thousands separators, never decimal marks.
    if not re.fullmatch(r'(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?', text):
        raise ValueError('금액이 없거나 숫자 형식이 아닙니다.')
    try:
        number = Decimal(text.replace(',', ''))
    except InvalidOperation:
        raise ValueError('금액을 읽을 수 없습니다.') from None
    if not number.is_finite() or number < 0 or number > Decimal('1e20'):
        raise ValueError('금액의 유효 범위를 확인할 수 없습니다.')
    return number


def _number(value):
    if value is None:
        return None
    return int(value) if value == value.to_integral_value() else float(value)


def _status(value):
    return 'OBSERVED_ZERO' if value == 0 else 'OBSERVED'


def _redact(text, api_keys):
    """Remove configured secrets and their common URL-encoded representations."""
    variants = set()
    for value in api_keys.values():
        if isinstance(value, str) and value:
            variants.update((value, unquote(value), quote(value, safe=''),
                             quote(unquote(value), safe='')))
    for value in sorted(variants, key=len, reverse=True):
        text = text.replace(value, '[REDACTED]')
    # Redact named credentials even if an upstream returned an unexpected key.
    text = re.sub(r'(?i)(servicekey|subscription-key|authkey|api_key)([=\"\s:>]+)([^&\s<\"]+)',
                  r'\1\2[REDACTED]', text)
    return text


def _fetch(session, url, params, provider, source_id, api_keys):
    is_comtrade = any(url.startswith('https://comtradeapi.un.org/data/v1/' + operation + '/')
                      for operation in ('get', 'getDA', 'getDa', 'getMetadata'))
    safe_params = {k: v for k, v in params.items() if k not in ('serviceKey', 'subscription-key')}
    source = {
        'id': source_id, 'provider': provider,
        'retrieved_at': datetime.now(timezone.utc).isoformat(),
        'request': {'url': url, 'params': safe_params},
        'sha256': None, 'status': 'FETCH_ERROR',
        'source_release_at': None, 'adapter_version': MODULE_VERSION,
    }
    for attempt in range(2):
        response = None
        retry = False
        retry_delay = 2.0
        try:
            if is_comtrade:
                _wait_comtrade_turn()
            response = session.get(url, params=params,
                                   headers={'Accept': 'application/json, application/xml, text/xml'},
                                   timeout=TIMEOUT, allow_redirects=False)
            source['http_status'] = response.status_code
            if response.status_code in (429, 500, 502, 503, 504):
                retry = True
                retry_delay = _retry_delay(response)
            elif response.status_code == 200:
                content = response.content
                if not isinstance(content, bytes) or len(content) > MAX_RESPONSE_BYTES:
                    source['reason'] = '응답 크기 또는 형식을 확인할 수 없습니다.'
                    return None, source
                source['sha256'] = hashlib.sha256(content).hexdigest()
                source['raw'] = _redact(content.decode('utf-8-sig', errors='replace'), api_keys)
                source['raw_redacted'] = True
                source['status'] = 'RECEIVED'
                return content, source
            else:
                break
        except requests.RequestException:
            # RequestException may contain the authenticated URL: never expose it.
            retry = True
        finally:
            if response is not None:
                response.close()
        if retry and is_comtrade:
            # Preserve a provider cooldown for the next request even when this
            # observation has exhausted its bounded two-attempt allowance.
            _postpone_comtrade(retry_delay)
        if not retry or attempt == 1:
            break
        if not is_comtrade:
            time.sleep(0.25)
    source['reason'] = '외부 통계 요청에 실패했습니다. 인증·이용 한도·연결 상태를 확인해 주세요.'
    return None, source


def _observation(year, value=None, status='MISSING', evidence=None, reason=None):
    result = {'year': year, 'value': _number(value), 'status': status,
              'evidence': evidence or []}
    if reason:
        result['reason'] = reason
    return result


def _comtrade(content, source, country, hs6, year):
    ref = {'source_id': source['id'], 'record': None}
    if content is None:
        return _observation(year, status='FETCH_ERROR', evidence=[ref], reason=source['reason']), []
    try:
        doc = json.loads(content)
    except (ValueError, UnicodeDecodeError):
        return _observation(year, status='INVALID_DATA', evidence=[ref], reason='Comtrade JSON 형식이 올바르지 않습니다.'), []
    if not isinstance(doc, dict) or not isinstance(doc.get('data'), list):
        return _observation(year, status='INVALID_DATA', evidence=[ref], reason='Comtrade 데이터 목록이 없습니다.'), []
    if doc.get('error') or doc.get('errorMessage'):
        return _observation(year, status='FETCH_ERROR', evidence=[ref], reason='Comtrade 업무 오류가 반환됐습니다.'), []
    rows = doc['data']
    if not rows:
        return _observation(year, evidence=[ref], reason='해당 연도의 수입 관측값이 없습니다. 0으로 간주하지 않습니다.'), []
    if len(rows) != 1 or (doc.get('count') is not None and str(doc['count']) != '1'):
        return _observation(year, status='INVALID_DATA', evidence=[ref], reason='요청 차원의 관측이 하나로 식별되지 않습니다.'), []
    row = rows[0]
    if not isinstance(row, dict):
        return _observation(year, status='INVALID_DATA', evidence=[ref], reason='Comtrade 관측 형식이 올바르지 않습니다.'), []
    expected = {'period': str(year), 'reporterCode': str(COUNTRIES[country]['reporter_code']),
                'partnerCode': '0', 'partner2Code': '0', 'flowCode': 'M',
                'cmdCode': hs6, 'classificationCode': 'H6', 'customsCode': 'C00',
                'motCode': '0', 'freqCode': 'A'}
    if any(str(row.get(k, '')) != v for k, v in expected.items()):
        return _observation(year, status='INVALID_SCOPE', evidence=[ref],
                            reason='반환 국가·기간·HS2022·수입 방향·집계 차원이 요청과 다릅니다.'), []
    try:
        value = _decimal(row.get('primaryValue'))
    except ValueError:
        return _observation(year, status='INVALID_DATA', evidence=[ref], reason='수입금액이 없거나 유효하지 않습니다.'), []
    warnings = []
    if row.get('isOriginalClassification') is False:
        warnings.append(f'{year}년은 HS2022 변환분류 자료입니다. 원분류와 범위 차이를 확인해 주세요.')
    if row.get('isNetWgtEstimated') is True:
        warnings.append(f'{year}년 순중량은 추정치입니다. 이 단계에서는 중량·단가를 계산하지 않습니다.')
    warnings.append('수입금액은 primaryValue 원값입니다. 보고국의 CIF/FOB 평가기준은 미확인입니다.')
    ref.update(record=1, field='primaryValue', value=_number(value), period=str(year),
               reporter_code=row['reporterCode'], partner_code=0, hs6=hs6,
               hs_edition='HS2022', flow='M', valuation_basis='UNKNOWN',
               flags={k: row.get(k) for k in ('isReported', 'isAggregate', 'isOriginalClassification',
                                             'isNetWgtEstimated', 'isQtyEstimated')})
    return _observation(year, value, _status(value), [ref]), warnings


def _kcs(content, source, country, hs6, year):
    ref = {'source_id': source['id'], 'field': 'expDlr', 'valuation_basis': 'FOB'}
    if content is None:
        return _observation(year, status='FETCH_ERROR', evidence=[ref], reason=source['reason'])
    try:
        # No DTD/entity expansion is needed for this numeric API.
        if b'<!DOCTYPE' in content.upper() or b'<!ENTITY' in content.upper():
            raise ET.ParseError('DTD not allowed')
        root = ET.fromstring(content)
    except ET.ParseError:
        return _observation(year, status='INVALID_DATA', evidence=[ref], reason='관세청 XML 형식이 올바르지 않습니다.')
    if root.findtext('.//resultCode') != '00':
        return _observation(year, status='FETCH_ERROR', evidence=[ref], reason='관세청 업무 응답이 정상 코드가 아닙니다.')
    by_month = defaultdict(dict)
    ignored_totals = 0
    for index, item in enumerate(root.findall('.//item'), 1):
        row = {child.tag: (child.text or '').strip() for child in item}
        period = row.get('year', '')
        if period in ('총계', '합계', 'Total', 'TOTAL'):
            ignored_totals += 1
            continue
        match = re.fullmatch(r'([0-9]{4})[.-]([0-9]{2})', period)
        code = row.get('hsCd', '')
        if (not match or int(match[1]) != year or not 1 <= int(match[2]) <= 12
                or row.get('statCd') != country
                or not re.fullmatch(r'[0-9]{6}(?:[0-9]{4})?', code)
                or not code.startswith(hs6)):
            return _observation(year, status='INVALID_SCOPE', evidence=[ref],
                                reason='관세청 반환 국가·기간·품목 범위를 확인할 수 없습니다.')
        month = int(match[2])
        if code in by_month[month]:
            return _observation(year, status='INVALID_DATA', evidence=[ref], reason='관세청 월·품목 관측이 중복됩니다.')
        try:
            value = _decimal(row.get('expDlr'))
        except ValueError:
            return _observation(year, status='INVALID_DATA', evidence=[ref], reason='한국 수출금액이 없거나 유효하지 않습니다.')
        by_month[month][code] = (value, index)
    missing = [f'{year}-{month:02d}' for month in range(1, 13) if month not in by_month]
    if missing:
        ref.update(observed_months=len(by_month), missing_months=missing, ignored_total_records=ignored_totals)
        return _observation(year, evidence=[ref], reason=f'12개월 중 {len(by_month)}개월만 확인됐습니다. 빠진 달은 0으로 채우지 않습니다.')
    total = Decimal(0)
    records = []
    monthly = []
    for month in range(1, 13):
        rows = by_month[month]
        details = {code: pair for code, pair in rows.items() if len(code) == 10}
        selected = details or rows
        value = sum((pair[0] for pair in selected.values()), Decimal(0))
        if details and hs6 in rows:
            if rows[hs6][0] != value:
                return _observation(year, status='INVALID_DATA', evidence=[ref], reason='HS6 소계와 HSK10 합계가 일치하지 않습니다.')
            ignored_totals += 1
        total += value
        monthly.append({'period': f'{year}-{month:02d}', 'value': _number(value), 'status': _status(value)})
        records.extend({'record': pair[1], 'hs_raw': code, 'period': f'{year}-{month:02d}',
                        'value': _number(pair[0])} for code, pair in selected.items())
    ref.update(records=records, months=monthly, observed_months=12,
               ignored_total_records=ignored_totals, hs6=hs6, hs_edition='HS2022',
               classification_note='HS2022 기간의 반환 세번을 HS6 상위 범위로 집계했습니다.')
    return _observation(year, total, _status(total), [ref])


def _metric(identifier, label, obs, unit, formula, period):
    result = {'id': identifier, 'label': label, 'value': obs['value'], 'unit': unit,
              'status': obs['status'], 'formula': formula, 'period': period,
              'evidence': obs.get('evidence', [])}
    if obs.get('reason'):
        result['reason'] = obs['reason']
    return result


def _growth(observations, end, start, years=1):
    needed = [observations[y] for y in range(start, end + 1)]
    evidence = [e for obs in needed for e in obs.get('evidence', [])]
    invalid = next((obs for obs in needed if obs['status'] not in VALID_STATUSES), None)
    if invalid:
        return _observation(end, status=invalid['status'], evidence=evidence,
                            reason='같은 범위의 비교기간 자료가 모두 확인되지 않았습니다.')
    denominator = Decimal(str(observations[start].get('value_decimal', observations[start]['value'])))
    numerator = Decimal(str(observations[end].get('value_decimal', observations[end]['value'])))
    if denominator == 0:
        return _observation(end, status='INVALID_DATA', evidence=evidence,
                            reason='기준연도 금액이 0이므로 증가율을 정의할 수 없습니다.')
    with localcontext() as context:
        context.prec = 28
        ratio = numerator / denominator
        value = (ratio if years == 1 else ratio ** (Decimal(1) / Decimal(years))) - 1
    if not math.isfinite(float(value)):
        return _observation(end, status='INVALID_DATA', evidence=evidence, reason='증가율의 유효 범위를 확인할 수 없습니다.')
    return _observation(end, value, _status(value), evidence)


def collect_market(inputs, api_keys, progress=None, *, session=None):
    """Collect annual raw indicators; missing observations remain null.

    The caller persists the returned snapshots in a private store. No score,
    success probability, company suitability or monthly-growth claim is made.
    """
    inputs = validate_inputs(inputs)
    keys = {name: api_keys.get(name, '') for name in ('KCS_TRADE_API_KEY', 'UN_COMTRADE_API_KEY')}
    year, hs6 = inputs['year'], inputs['hs6']
    own_session = session is None
    session = session or requests.Session()
    result = {'countries': [], 'sources': [], 'warnings': [
        '이 결과는 국가·HS6의 연간 시장 원지표입니다. 기업의 수출 성공·적법성·수익성을 판정하지 않습니다.',
        '월별 성장률·최근 3개월·가격·물류·안정성·종합 점수는 후속 단계입니다.',
        '한국 수출은 FOB이며 목적국 수입과 신고주체·평가기준이 다릅니다. 두 금액으로 점유율을 계산하지 않습니다.',
    ], 'method_version': MODULE_VERSION}
    try:
        for country in inputs['countries']:
            name = COUNTRIES[country]['name']
            annual, warnings = {}, []
            for observed_year in range(year - 3, year + 1):
                if progress:
                    progress(f'{name} {observed_year}년 수입자료 확인 중')
                source_id = f'comtrade-{country}-{observed_year}'
                params = {'period': str(observed_year), 'reporterCode': str(COUNTRIES[country]['reporter_code']),
                          'cmdCode': hs6, 'flowCode': 'M', 'partnerCode': '0', 'partner2Code': '0',
                          'customsCode': 'C00', 'motCode': '0', 'maxRecords': 10,
                          'format': 'JSON',
                          'subscription-key': keys['UN_COMTRADE_API_KEY']}
                if keys['UN_COMTRADE_API_KEY']:
                    content, source = _fetch(session, COMTRADE_URL, params, 'UN Comtrade', source_id, keys)
                    observation, notes = _comtrade(content, source, country, hs6, observed_year)
                    source['status'] = observation['status']
                    result['sources'].append(source)
                    warnings.extend(notes)
                else:
                    observation = _observation(observed_year, status='FETCH_ERROR', reason='UN Comtrade 인증키가 설정되지 않았습니다.')
                annual[observed_year] = observation
            if progress:
                progress(f'{name} {year}년 한국 수출자료 확인 중')
            if keys['KCS_TRADE_API_KEY']:
                params = {'strtYymm': f'{year}01', 'endYymm': f'{year}12', 'hsSgn': hs6,
                          'cntyCd': country, 'serviceKey': unquote(keys['KCS_TRADE_API_KEY'])}
                content, source = _fetch(session, KCS_URL, params, '관세청', f'kcs-{country}-{year}', keys)
                exports = _kcs(content, source, country, hs6, year)
                source['status'] = exports['status']
                result['sources'].append(source)
            else:
                exports = _observation(year, status='FETCH_ERROR', reason='관세청 무역 인증키가 설정되지 않았습니다.')
            yoy = _growth(annual, year, year - 1)
            cagr = _growth(annual, year, year - 3, 3)
            metrics = [
                _metric('import_value', '대세계 수입시장 규모', annual[year], 'USD',
                        '동일 국가·HS2022·HS6·연도·수입·대세계의 primaryValue', str(year)),
                _metric('import_yoy', '수입액 연간 증가율', yoy, 'ratio',
                        '수입액(Y) / 수입액(Y−1) − 1', f'{year - 1}~{year}'),
                _metric('import_cagr3', '수입액 3년 CAGR', cagr, 'ratio',
                        '(수입액(Y) / 수입액(Y−3))^(1/3) − 1', f'{year - 3}~{year}'),
                _metric('korea_exports', '한국의 해당국 수출액', exports, 'USD',
                        '총계·중복 소계를 제외한 동일 HS6 범위 월별 expDlr의 12개월 합', str(year)),
            ]
            warnings.extend(m['reason'] for m in metrics if m.get('reason'))
            result['countries'].append({'country': country, 'name': name, 'metrics': metrics,
                                        'series': [annual[y] for y in sorted(annual)],
                                        'warnings': list(dict.fromkeys(warnings))})
    finally:
        if own_session:
            session.close()
    return result
