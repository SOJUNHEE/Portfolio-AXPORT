# (junhee) 2026-09-27 sanghyeob/analysis_regulation_law.py 에서 옮김. 바꾼 것: 패키지 import 경로·원본 자료 경로(junhee/data/raw)만. 계산 로직은 그대로.
"""Current LAW administrative-rule snapshot, never a product/legal decision.

Official contracts: open.law.go.kr/LSO/openApi/guideResult.do?htmlName=
admrulListGuide and admrulInfoGuide. The verified JSON body root contains
``행정규칙기본정보``, not ``기본정보``. The observed complete body is about
10.3 MiB because it includes annex text. Stream at most 20 MiB for the body and
512 KiB for the list; make two logical requests, with at most two attempts each.

Only title/current-version metadata is selected. No HS/product/company data is
sent. Full redacted JSON is private source evidence; public results contain
bounded excerpts and annex metadata/links. No binary attachment is downloaded.
The current API lookup does not reconstruct the law available at a past as_of.
"""

from datetime import date, datetime, timezone
from hashlib import sha256
import json
import re
import time
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import requests

from .market_data import _redact


TITLE = '전략물자수출입고시'
LIST_URL = 'https://www.law.go.kr/DRF/lawSearch.do'
BODY_URL = 'https://www.law.go.kr/DRF/lawService.do'
VERSION = 'current-administrative-rule-v1'
TIMEOUT = (5, 30)
MAX_LIST_BYTES = 512 * 1024
MAX_BODY_BYTES = 20 * 1024 * 1024
MAX_EXCERPTS = 12
MAX_EXCERPT_CHARS = 1200
REVIEW = ('현행 고시 원문 확보는 개별 제품·모델의 통제 해당 여부나 수출허가를 뜻하지 않습니다. '
          '기술사양·최종용도·거래처·목적국·허가 증빙을 별도로 검토해야 합니다.')
HISTORICAL = '조회 시점의 현행 판본입니다. 과거 기준일 당시의 법령·공표 상태를 재현한 자료가 아닙니다.'


class _ScopeError(ValueError):
    pass


class _LookupError(ValueError):
    pass


def _redact_law(text, keys):
    # A credential inside a JSON string can contain escaped quotes/backslashes
    # or Unicode escapes even when its plain spelling is absent in raw bytes.
    for value in keys.values():
        if isinstance(value, str) and value:
            for ascii_only in (False, True):
                text = text.replace(json.dumps(value, ensure_ascii=ascii_only)[1:-1], '[REDACTED]')
    text = _redact(text, keys)
    # OC may be echoed in a URL or a JSON property, including an unexpected key.
    text = re.sub(r'(?i)([?&]OC=)[^&\s"<>\\]*', r'\1[REDACTED]', text)
    return re.sub(r'(?i)("OC"\s*:\s*")[^"]*', r'\1[REDACTED]', text)


def _safe_url(value, *, download=False):
    """Accept official LAW paths, remove credentials, normalize HTTP to HTTPS."""
    if not isinstance(value, str) or not value or '\\' in value or any(ord(c) < 32 for c in value):
        return None
    try:
        parsed = urlsplit(urljoin('https://www.law.go.kr', value))
        if (parsed.scheme not in ('http', 'https') or parsed.hostname not in ('law.go.kr', 'www.law.go.kr')
                or parsed.username or parsed.password or parsed.port not in (None, 80, 443)):
            return None
    except ValueError:
        return None
    paths = {'/LSW/flDownload.do': {'flSeq'}, '/flDownload.do': {'flSeq'}}
    if not download:
        paths.update({'/LSW/admRulLsInfoP.do': {'admRulSeq', 'admRulId', 'efYd'},
                      '/admRulLsInfoP.do': {'admRulSeq', 'admRulId', 'efYd'},
                      '/DRF/lawService.do': {'target', 'ID', 'type', 'mobileYn'}})
    if parsed.path not in paths:
        return None
    params, seen = [], set()
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key not in paths[parsed.path]:
            continue
        if key in seen:
            return None
        seen.add(key)
        if key in ('flSeq', 'admRulSeq', 'admRulId', 'efYd', 'ID'):
            if not re.fullmatch(r'[0-9]+', value):
                return None
        elif (key == 'target' and value != 'admrul') or (key == 'type' and value not in ('HTML', 'XML', 'JSON')):
            return None
        elif key == 'mobileYn' and value not in ('', 'Y', 'N'):
            return None
        params.append((key, value))
    if ('flDownload.do' in parsed.path and 'flSeq' not in seen
            or 'admRulLsInfoP.do' in parsed.path and not seen.intersection({'admRulSeq', 'admRulId'})
            or parsed.path == '/DRF/lawService.do' and not {'ID', 'target'} <= seen):
        return None
    return urlunsplit(('https', parsed.hostname, parsed.path, urlencode(params), ''))


def _fetch_law(session, url, params, source_id, keys, limit):
    source = {'id': source_id, 'provider': '국가법령정보센터', 'adapter_version': VERSION,
              'retrieved_at': datetime.now(timezone.utc).isoformat(), 'sha256': None,
              'status': 'FETCH_ERROR', 'source_release_at': None,
              'request': {'url': url, 'params': {k: v for k, v in params.items() if k.upper() != 'OC'}}}
    for attempt in range(2):
        response, retry = None, False
        try:
            response = session.get(url, params=params, headers={'Accept': 'application/json'},
                                   timeout=TIMEOUT, allow_redirects=False, stream=True)
            source['http_status'] = response.status_code
            if response.status_code in (429, 500, 502, 503, 504):
                retry = True
            elif response.status_code == 200:
                chunks, size = [], 0
                if callable(getattr(response, 'iter_content', None)):
                    iterator = response.iter_content(chunk_size=65536)
                else:
                    iterator = [response.content]  # Small injected offline fixtures.
                for chunk in iterator:
                    if not isinstance(chunk, bytes):
                        source['reason'] = '법령 응답의 바이트 형식을 확인할 수 없습니다.'
                        return None, source
                    size += len(chunk)
                    if size > limit:
                        source['reason'] = '법령 응답이 허용한 크기를 초과하여 수신을 중단했습니다.'
                        return None, source
                    chunks.append(chunk)
                content = b''.join(chunks)
                source.update(sha256=sha256(content).hexdigest(), byte_count=len(content),
                              raw=_redact_law(content.decode('utf-8-sig', errors='replace'), keys),
                              raw_redacted=True, status='RECEIVED')
                return content, source
        except requests.RequestException:
            retry = True  # Exception strings can contain OC; never retain them.
        finally:
            if response is not None:
                response.close()
        if not retry or attempt == 1:
            break
        time.sleep(0.5)
    source['reason'] = '법령 API 요청에 실패했습니다. 인증·활용 권한·연결 상태를 확인해 주세요.'
    return None, source


def _pairs(pairs):
    output = {}
    for key, value in pairs:
        if key in output:
            raise ValueError('중복 JSON 필드')
        output[key] = value
    return output


def _document(content, root):
    if content is None:
        raise _LookupError('법령 API 응답을 확보하지 못했습니다.')
    doc = json.loads(content, object_pairs_hook=_pairs)
    if not isinstance(doc, dict) or not isinstance(doc.get(root), dict):
        raise ValueError('법령 JSON 응답 구조를 확인할 수 없습니다.')
    return doc[root]


def _digits(value):
    if isinstance(value, bool) or not re.fullmatch(r'[0-9]+', str(value)):
        raise ValueError('법령 숫자 식별자를 확인할 수 없습니다.')
    return str(value)


def _date(value):
    text = _digits(value)
    if len(text) != 8:
        raise ValueError('법령 날짜 형식을 확인할 수 없습니다.')
    return date.fromisoformat(text[:4] + '-' + text[4:6] + '-' + text[6:]).isoformat()


def _text(value, keys):
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        raise ValueError('필수 법령 문자열이 없습니다.')
    return _redact_law(value.strip(), keys)


def _law_fields(row, keys):
    if not isinstance(row, dict):
        raise ValueError('법령 기본정보 형식이 올바르지 않습니다.')
    if row.get('행정규칙명') != TITLE or row.get('행정규칙종류') != '고시':
        raise _ScopeError('요청한 고시명·종류와 반환된 법령이 다릅니다.')
    serial = _digits(row.get('행정규칙일련번호'))
    return {'serial': serial, 'law_id': _digits(row.get('행정규칙ID')),
            'title': TITLE, 'kind': '고시', 'issuer': _text(row.get('소관부처명'), keys),
            'issued_at': _date(row.get('발령일자')), 'effective_at': _date(row.get('시행일자')),
            'issue_number': _text(row.get('발령번호'), keys),
            'public_url': f'https://www.law.go.kr/LSW/admRulLsInfoP.do?admRulSeq={serial}'}


def _list_law(content, source, keys):
    doc = _document(content, 'AdmRulSearch')
    if str(doc.get('resultCode')) != '00':
        raise _LookupError('법령 목록 업무 응답이 정상 코드가 아닙니다.')
    if doc.get('target') != 'admrul':
        raise _ScopeError('법령 목록의 조회 대상이 다릅니다.')
    rows = doc.get('admrul', [])
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError('행정규칙 목록 형식이 올바르지 않습니다.')
    total = int(_digits(doc.get('totalCnt')))
    if (str(doc.get('page')) != '1' or total != len(rows) or total > 20
            or (doc.get('numOfRows') is not None and int(_digits(doc['numOfRows'])) != len(rows))):
        raise ValueError('목록 건수·페이지의 완전성을 확인할 수 없습니다. 첫 결과를 임의 선택하지 않습니다.')
    exact = [row for row in rows if row.get('행정규칙명') == TITLE]
    current = [row for row in exact if row.get('현행연혁구분') == '현행']
    if not exact:
        source.update(status='MISSING', reason='이번 정상 목록 조회에서 정확한 고시명을 찾지 못했습니다.')
        return None
    if len(exact) != 1 or len(current) != 1:
        raise _ScopeError('정확한 이름의 현행 고시 판본이 하나로 확인되지 않습니다.')
    law = _law_fields(current[0], keys)
    source.update(status='OBSERVED', source_release_at=law['issued_at'],
                  observed_period=law['effective_at'], law_serial=law['serial'])
    return law


def _text_size(value):
    """Validate nested annex strings without joining megabytes into the result."""
    stack, size = [value], 0
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            size += len(item)
        elif isinstance(item, list):
            stack.extend(item)
        elif item is not None:
            raise ValueError('별표 본문 형식을 확인할 수 없습니다.')
    return size


def _body_law(content, source, law, keys):
    doc = _document(content, 'AdmRulService')
    if 'resultCode' in doc and str(doc['resultCode']) != '00':
        raise _LookupError('법령 본문 업무 응답이 정상 코드가 아닙니다.')
    basic = doc.get('행정규칙기본정보')
    body_law = _law_fields(basic, keys)
    if body_law != law or basic.get('현행여부') != 'Y':
        raise _ScopeError('목록과 본문의 판본·이름·발령·시행일·현행 여부가 일치하지 않습니다.')
    paragraphs = doc.get('조문내용')
    if isinstance(paragraphs, str):
        paragraphs = [paragraphs]
    if not isinstance(paragraphs, list) or not paragraphs or any(not isinstance(p, str) for p in paragraphs):
        raise ValueError('고시 본문 조문을 확인할 수 없습니다.')
    if not any(p.strip() for p in paragraphs):
        raise ValueError('고시 본문이 비어 있습니다.')
    excerpts = [{'paragraph': index, 'text': _redact_law(text, keys)[:MAX_EXCERPT_CHARS],
                 'truncated': len(text) > MAX_EXCERPT_CHARS,
                 'evidence': [{'source_id': source['id'], 'field': '조문내용', 'paragraph': index}]}
                for index, text in enumerate(paragraphs[:MAX_EXCERPTS], 1)]
    container = doc.get('별표', {})
    if not isinstance(container, dict):
        raise ValueError('별표 목록 구조를 확인할 수 없습니다.')
    rows = container.get('별표단위', [])
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list) or len(rows) > 300:
        raise ValueError('별표 목록 크기·형식을 확인할 수 없습니다.')
    annexes, warnings, seen = [], [], set()
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError('별표 행 형식이 올바르지 않습니다.')
        number, sub = _digits(row.get('별표번호')), _digits(row.get('별표가지번호'))
        kind, title = _text(row.get('별표구분'), keys), _text(row.get('별표제목'), keys)
        identity = (kind, number, sub)
        if identity in seen:
            raise ValueError('별표 식별자가 중복되었습니다.')
        seen.add(identity)
        links = {}
        for output, field in (('document_url', '별표서식파일링크'), ('pdf_url', '별표서식PDF파일링크')):
            raw = row.get(field)
            links[output] = _safe_url(raw, download=True) if raw else None
            if raw and links[output] is None:
                warnings.append('공식 LAW 다운로드 경로로 검증되지 않은 별표 링크는 제공하지 않았습니다.')
        annexes.append({'number': number, 'sub_number': sub, 'kind': kind, 'title': title,
                        'text_character_count': _text_size(row.get('별표내용')), **links,
                        'evidence': [{'source_id': source['id'], 'field': '별표.별표단위', 'record': index}]})
    attachments = []
    container = doc.get('첨부파일', {})
    if not isinstance(container, dict):
        raise ValueError('첨부파일 목록 형식이 올바르지 않습니다.')
    names, urls = container.get('첨부파일명', []), container.get('첨부파일링크', [])
    names, urls = ([names] if isinstance(names, str) else names), ([urls] if isinstance(urls, str) else urls)
    if not isinstance(names, list) or not isinstance(urls, list) or len(names) != len(urls) or len(names) > 100:
        raise ValueError('첨부파일명과 링크의 대응을 확인할 수 없습니다.')
    for index, (name, raw) in enumerate(zip(names, urls), 1):
        link = _safe_url(raw, download=True)
        if link is None:
            warnings.append('공식 LAW 다운로드 경로로 검증되지 않은 첨부 링크는 제공하지 않았습니다.')
        attachments.append({'name': _text(name, keys), 'url': link,
                            'evidence': [{'source_id': source['id'], 'field': '첨부파일', 'record': index}]})
    if not annexes:
        warnings.append('별표 목록을 확보하지 못했습니다. 통제 품목 원문 확보가 완결되지 않았습니다.')
    source.update(status='OBSERVED', source_release_at=law['issued_at'], observed_period=law['effective_at'],
                  law_serial=law['serial'])
    return ({'paragraph_count': len(paragraphs), 'excerpt_count': len(excerpts),
             'excerpts': excerpts, 'excerpt_only': True,
             'omitted_paragraph_count': max(0, len(paragraphs) - len(excerpts))},
            annexes, attachments, list(dict.fromkeys(warnings)))


def collect_regulation_law(inputs, keys, progress=None, session=None):
    """Collect one current exact-title snapshot; keep applicability under review."""
    try:
        as_of = date.fromisoformat(inputs['as_of'])
    except (KeyError, ValueError, TypeError):
        raise ValueError('법령 자료의 분석 기준일을 확인해 주세요.') from None
    keys = keys or {}
    result = {'status': 'FETCH_ERROR', 'law': None, 'body': None, 'annexes': [], 'attachments': [],
              'sources': [], 'warnings': [HISTORICAL, REVIEW],
              'checks': [{'label': '개별 제품·거래 적용성', 'status': 'REVIEW_REQUIRED', 'detail': REVIEW}],
              'as_of': as_of.isoformat(), 'lookup_basis': 'CURRENT_LOOKUP',
              'adapter_version': VERSION, 'needs_regulation_review': True}
    key = keys.get('LAW_API_KEY')
    if not isinstance(key, str) or not key.strip():
        result['warnings'].append('국가법령정보 API 인증 설정이 없어 현행 고시를 조회하지 않았습니다.')
        result['checks'].append({'label': '현행 고시 원문 확보', 'status': 'FETCH_ERROR',
                                 'detail': result['warnings'][-1]})
        return result
    own_session = session is None
    client = requests.Session() if own_session else session
    source = None
    try:
        if progress:
            progress('현행 전략물자수출입고시의 판본을 확인합니다.')
        params = {'OC': key, 'target': 'admrul', 'type': 'JSON', 'nw': 1, 'search': 1,
                  'query': TITLE, 'knd': 3, 'sort': 'efdes', 'display': 20, 'page': 1}
        content, source = _fetch_law(client, LIST_URL, params, 'law:admrul:current:list', keys, MAX_LIST_BYTES)
        result['sources'].append(source)
        law = _list_law(content, source, keys)
        if law is None:
            result.update(status='MISSING')
            result['warnings'].append(source['reason'])
        else:
            result['law'] = {**law, 'is_current': True, 'lookup_basis': 'CURRENT_LOOKUP',
                             'evidence': [{'source_id': source['id'], 'field': 'admrul'}]}
            if progress:
                progress('동일 판본의 고시 본문과 별표 링크를 확인합니다.')
            params = {'OC': key, 'target': 'admrul', 'type': 'JSON', 'ID': law['serial']}
            content, source = _fetch_law(client, BODY_URL, params, 'law:admrul:' + law['serial'], keys, MAX_BODY_BYTES)
            result['sources'].append(source)
            body, annexes, attachments, warnings = _body_law(content, source, law, keys)
            result.update(status='PARTIAL' if warnings else 'OBSERVED', body=body, annexes=annexes, attachments=attachments)
            result['warnings'].extend(warnings)
            if law['effective_at'] > as_of.isoformat() or law['issued_at'] > as_of.isoformat():
                result['status'] = 'OUT_OF_PERIOD'
                result['warnings'].append('현재 확보한 판본의 발령일 또는 시행일이 분석 기준일 이후여서 기준일 적용 근거로 사용하지 않습니다.')
    except _LookupError as error:
        result['status'] = 'FETCH_ERROR'
        result['warnings'].append(str(error))
        if source:
            source.update(status='FETCH_ERROR', validation_reason=str(error))
    except _ScopeError as error:
        result['status'] = 'INVALID_SCOPE'
        result['warnings'].append(str(error))
        if source:
            source.update(status='INVALID_SCOPE', validation_reason=str(error))
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, RecursionError):
        result['status'] = 'INVALID_DATA'
        reason = '고시 응답의 구조·식별자·날짜·본문 완전성을 검증하지 못했습니다.'
        result['warnings'].append(reason)
        if source:
            source.update(status='INVALID_DATA', validation_reason=reason)
    finally:
        if own_session:
            client.close()
    result['checks'].append({'label': '현행 고시 원문 확보', 'status': result['status'],
                             'detail': '판본 일치·본문·별표 메타데이터를 확인했습니다. ' + REVIEW
                             if result['status'] == 'OBSERVED' else result['warnings'][-1]})
    return result
