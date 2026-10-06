# (junhee) 2026-09-27 sanghyeob/analysis_company_documents.py 에서 옮김. 바꾼 것: 패키지 import 경로·원본 자료 경로(junhee/data/raw)만. 계산 로직은 그대로.
"""Link enterprise-declared document metadata without opening any attachment.

Counts describe the submitted list only. Dates and identifiers do not verify
authenticity, a legal requirement, certificate possession or export permission.
"""

from collections import Counter
from datetime import date
import re


VERSION = 'company-document-metadata-v1'
DOCUMENT_FIELDS = ('증빙ID', '관련제품ID', '관련거래ID', '문서종류', '문서번호', '발행일', '만료일', '첨부참조')


def _text(value):
    return '' if value is None else str(value).strip()


def _date(value):
    raw = _text(value)
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', raw):
        raise ValueError
    return date.fromisoformat(raw)


def _evidence(company, row, fields, sheet='증빙목록'):
    return {'source_id': company.get('source', {}).get('id', 'company-upload'),
            'sheet': row.get('_sheet', sheet), 'row': row.get('_row'), 'field': fields}


def _metadata(row, as_of):
    issues = []
    for field in ('증빙ID', '문서종류', '문서번호', '첨부참조'):
        if not _text(row.get(field)):
            issues.append({'code': 'MISSING_' + {'증빙ID': 'ID', '문서종류': 'TYPE', '문서번호': 'NUMBER', '첨부참조': 'ATTACHMENT'}[field],
                           'field': field, 'detail': field + '가 기재되지 않았습니다.'})
    dates = {}
    for field in ('발행일', '만료일'):
        if not _text(row.get(field)):
            issues.append({'code': 'MISSING_DATE', 'field': field,
                           'detail': field + '이 기재되지 않았습니다. 날짜·무기한 유효를 추정하지 않습니다.'})
            continue
        try:
            dates[field] = _date(row[field])
        except ValueError:
            issues.append({'code': 'INVALID_DATE', 'field': field,
                           'detail': field + '은 실제 존재하는 YYYY-MM-DD 날짜여야 합니다.'})
    issued, expires = dates.get('발행일'), dates.get('만료일')
    status = 'DOCUMENT_METADATA_INCOMPLETE' if issues else 'DECLARED_UNVERIFIED'
    if issued and issued > as_of:
        status = 'FUTURE'
        issues.append({'code': 'FUTURE_ISSUE_DATE', 'field': '발행일', 'detail': '기재 발행일이 분석 기준일 이후입니다.'})
    if expires and expires < as_of:
        status = 'EXPIRED'
        issues.append({'code': 'PAST_EXPIRY_DATE', 'field': '만료일', 'detail': '기재 만료일이 분석 기준일보다 이릅니다. 문서 종류별 법적 효력을 판정한 결과가 아닙니다.'})
    if issued and expires and issued > expires:
        status = 'CONFLICT'
        issues.append({'code': 'REVERSED_DATES', 'field': '발행일/만료일', 'detail': '발행일이 만료일보다 늦어 날짜 기재가 충돌합니다.'})
    return status, issues


def evaluate_company_documents(company, inputs):
    """Return references, checks, warnings and list coverage; no I/O or scores.

    Detailed references are limited to rows mentioning a selected product or
    transaction. Unrelated/unlinked rows contribute only counts and minimal
    row-level diagnostics. A product-only link never establishes country scope.
    """
    from .analysis_risk_logistics import _scope, _active_actual, _hs, COUNTRIES

    try:
        as_of = _date(inputs['as_of'])
        if (inputs.get('country') not in COUNTRIES or inputs.get('hs_edition') != 'HS2022'
                or not re.fullmatch(r'[0-9]{6}', _text(inputs.get('hs6')))):
            raise ValueError
    except (KeyError, ValueError):
        raise ValueError('증빙 목록의 기준일·목적국·HS2022 범위를 확인해 주세요.') from None
    products, planned, actual = _scope(company, inputs)
    raw_hs = _text(inputs.get('hs_raw'))
    if len(raw_hs) in (8, 10):
        products = [r for r in products if _hs(r.get('HS코드')) == raw_hs]
    selected_products = {_text(r.get('제품ID')) for r in products if _text(r.get('제품ID'))}
    planned = [r for r in planned if _text(r.get('제품ID')) in selected_products]
    actual = _active_actual([r for r in actual if _text(r.get('제품ID')) in selected_products], as_of)
    selected = [(r, '거래ID', '수출예정거래') for r in planned] + [(r, '실적ID', '수출실적') for r in actual]
    selected_transactions = {_text(r.get(field)): (r, field, sheet) for r, field, sheet in selected if _text(r.get(field))}
    sheets = company.get('sheets', {})
    transaction_counts = Counter(_text(r.get(field)) for sheet, field in (('수출예정거래', '거래ID'), ('수출실적', '실적ID'))
                                 for r in sheets.get(sheet, []) if _text(r.get(field)))
    product_counts = Counter(_text(r.get('제품ID')) for r in sheets.get('제품정보', []) if _text(r.get('제품ID')))
    present = '증빙목록' in sheets
    rows = sheets.get('증빙목록', [])
    document_counts = Counter(_text(r.get('증빙ID')) for r in rows if _text(r.get('증빙ID')))
    references, checks, skipped = [], [], Counter()
    parser_issues = [issue for issue in company.get('issues', []) if issue.get('sheet') == '증빙목록']
    warnings = ['제출 목록의 기재 상태만 확인합니다. 문서 진위·첨부 실체·법적 적용·인증 보유·수출 허용을 판정하지 않습니다.',
                '첨부참조는 기업이 적은 문자열입니다. 파일·URL을 열거나 다운로드하지 않았습니다.',
                '관련제품만 확인한 문서는 해당 목적국 또는 특정 거래의 적용 증빙으로 해석할 수 없습니다.',
                '건수는 제출 목록 및 기재 상태 개수이며 인증 보유율이나 규제 충족률이 아닙니다.']
    for row in rows:
        product_id, transaction_id = _text(row.get('관련제품ID')), _text(row.get('관련거래ID'))
        candidate = product_id in selected_products or transaction_id in selected_transactions
        evidence = [_evidence(company, row, '/'.join(DOCUMENT_FIELDS))]
        if not candidate:
            code = 'DOCUMENT_LINK_MISSING' if not product_id and not transaction_id else 'DOCUMENT_OUT_OF_SCOPE'
            skipped[code] += 1
            checks.append({'label': f'증빙목록 {row.get("_row", "?")}행 연결', 'status': code,
                           'detail': '관련제품ID·관련거래ID가 없어 연결 범위를 확인하지 못했습니다.' if code == 'DOCUMENT_LINK_MISSING'
                           else '선택 제품·목적국의 거래에 연결되지 않아 문서 기재 내용을 평가 대상에 포함하지 않았습니다.',
                           'evidence': evidence})
            continue
        metadata_status, issues = _metadata(row, as_of)
        reference = {'document_id': _text(row.get('증빙ID')) or None, 'product_id': product_id or None,
                     'transaction_id': transaction_id or None, 'scope': 'UNLINKED', 'linked': False,
                     'status': metadata_status, 'metadata_status': metadata_status,
                     'document_type': _text(row.get('문서종류')) or None,
                     'document_number': _text(row.get('문서번호')) or None,
                     'issued_on': _text(row.get('발행일')) or None, 'expires_on': _text(row.get('만료일')) or None,
                     'attachment_reference': _text(row.get('첨부참조')) or None,
                     'verification': 'DECLARED_UNVERIFIED', 'issues': issues, 'evidence': evidence}

        def reject(code, detail, status='DOCUMENT_SCOPE_MISMATCH'):
            reference['status'] = status
            issues.append({'code': code, 'field': '관련제품ID/관련거래ID', 'detail': detail})

        if reference['document_id'] and document_counts[reference['document_id']] > 1:
            reject('DOCUMENT_ID_CONFLICT', '같은 증빙ID가 여러 행에 있어 중복·충돌 여부를 확정하지 못했습니다. 연결·합산하지 않습니다.', 'CONFLICT')
        elif not reference['document_id']:
            reject('DOCUMENT_ID_MISSING', '증빙ID가 없어 문서 행의 식별을 확정하지 못했습니다.', 'DOCUMENT_METADATA_INCOMPLETE')
        elif product_id and product_counts[product_id] > 1:
            reject('PRODUCT_ID_CONFLICT', '관련제품ID가 제품정보에서 중복되어 제품을 확정할 수 없습니다.', 'CONFLICT')
        elif transaction_id:
            if transaction_counts[transaction_id] > 1:
                reject('TRANSACTION_ID_CONFLICT', '관련거래ID가 예정거래·실적에서 중복되어 대상 거래를 확정할 수 없습니다.', 'CONFLICT')
            elif transaction_id not in selected_transactions:
                reject('TRANSACTION_OUT_OF_SCOPE', '관련거래가 선택 제품·목적국의 예정거래 또는 기준일 이전 정상 실적 범위에 없습니다.')
            else:
                transaction, field, sheet = selected_transactions[transaction_id]
                actual_product = _text(transaction.get('제품ID'))
                if product_id and product_id != actual_product:
                    reject('PRODUCT_TRANSACTION_MISMATCH', '문서의 관련제품ID와 관련거래의 제품ID가 다릅니다.')
                elif product_counts[actual_product] > 1:
                    reject('PRODUCT_ID_CONFLICT', '거래 제품의 제품ID가 중복되어 제품을 확정할 수 없습니다.', 'CONFLICT')
                else:
                    reference.update(linked=True, scope='TRANSACTION', product_id=actual_product)
                    evidence.append(_evidence(company, transaction, field + '/제품ID/목적국', sheet))
        elif product_id in selected_products:
            reference.update(linked=True, scope='PRODUCT_ONLY')
            issues.append({'code': 'COUNTRY_TRANSACTION_UNVERIFIED', 'field': '관련거래ID',
                           'detail': '제품 범위 참고입니다. 목적국·거래별 적용 여부는 확인하지 않았습니다.'})
        references.append(reference)
        checks.append({'label': f'증빙목록 {row.get("_row", "?")}행 기재 확인', 'status': reference['status'],
                       'detail': ' '.join(issue['detail'] for issue in issues) or '목록의 필수 기재값만 확인했습니다. 문서 진위·적용성은 미검증입니다.',
                       'evidence': evidence})
    if not present:
        warnings.append('증빙목록 시트가 확인되지 않았습니다. 문서·인증을 보유하지 않았다는 뜻이 아닙니다.')
    if parser_issues:
        warnings.append('업로드 파서가 증빙목록의 중복·충돌·수식·식별자 문제를 보고했습니다. 제외된 행을 보유 문서 없음으로 간주하지 않습니다.')
        checks.extend({'label': '증빙목록 업로드 확인', 'status': issue.get('status', 'DOCUMENT_METADATA_INCOMPLETE'),
                       'detail': '업로드 단계에서 증빙 행의 기재 구조를 확인하지 못했거나 중복을 정리했습니다.',
                       'evidence': [{'source_id': company.get('source', {}).get('id', 'company-upload'),
                                     'sheet': '증빙목록', 'row': issue.get('row'), 'field': '증빙ID/행 구조'}]}
                      for issue in parser_issues)
    coverage = {'list_status': 'PRESENT' if present else 'MISSING_SHEET',
                'submitted_rows': len(rows) if present else None,
                'relevant_rows': len(references) if present else None,
                'linked_rows': sum(r['linked'] for r in references) if present else None,
                'product_only_rows': sum(r['scope'] == 'PRODUCT_ONLY' for r in references) if present else None,
                'unlinked_rows': len(rows) - sum(r['linked'] for r in references) if present else None,
                'status_counts': dict(Counter(r['status'] for r in references)),
                'excluded_reason_counts': dict(skipped), 'parser_issue_count': len(parser_issues),
                'meaning': '파서가 전달한 제출목록 행·연결·기재상태 개수. 인증 보유율·법적 충족률이 아님.'}
    return {'references': references, 'checks': checks, 'warnings': warnings, 'coverage': coverage, 'method_version': VERSION}
