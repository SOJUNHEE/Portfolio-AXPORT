# (junhee) 2026-09-27 sanghyeob/company_simple.py 에서 옮김. 바꾼 것: 패키지 import 경로·원본 자료 경로(junhee/data/raw)만. 계산 로직은 그대로.
"""Validate a one-product form and preserve its original cells during normalization.

The workbook contains no HS or destination assertion. Analysis-form selections
are bound later, with their own provenance, and never represented as workbook
classification evidence. No observations, certifications or scores are inferred.
"""

from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import math
from pathlib import Path
import re


SHEET = '간편입력'
VERSION = 'company-simple-v2'
PRODUCT_ID = 'SIMPLE-P001'
PLAN_ID = 'SIMPLE-PLAN001'


class SimpleWorkbookError(ValueError):
    """Keep an actionable form-shape error through legacy XLS decoding."""


def _schema():
    return json.loads(Path(__file__).with_name('company_template_schema.json').read_text(encoding='utf-8'))


def _cell(rows, row, column):
    values = rows[row - 1] if row <= len(rows) else []
    return values[column - 1] if column <= len(values) else None


def _empty(value):
    return value is None or value == ''


def _number(value, label, cell):
    try:
        if isinstance(value, bool):
            raise ValueError
        number = Decimal(str(value))
        if not number.is_finite() or number < 0:
            raise ValueError
        numeric = float(number)
        if not math.isfinite(numeric) or (number != 0 and numeric == 0):
            raise ValueError
        return int(number) if number == number.to_integral_value() else numeric
    except (InvalidOperation, ValueError, OverflowError):
        raise ValueError(f'{SHEET}!{cell} {label}은 0 이상의 유한한 숫자로 작성해 주세요. 빈칸은 0으로 처리하지 않습니다.') from None


def parse_simple(rows, data, filename, legacy_sheets):
    """Return the existing company structure, without analysis-form bindings."""
    schema = _schema()
    if _cell(rows, 1, 1) != schema['marker']:
        raise ValueError('간편입력 양식의 A1 식별값을 확인해 주세요. 내려받은 양식의 구조를 유지해 주세요.')
    if any(isinstance(value, tuple) and value[0] == 'FORMULA' for row in rows for value in row):
        raise ValueError('간편입력에는 수식을 사용할 수 없습니다. 계산 결과를 값으로 붙여넣어 주세요.')
    fields = schema['fields']
    expected_rows = {field['row'] for field in fields}
    label_rows = {field['label']: field['row'] for field in fields}
    # Extra inputs must not silently disappear, particularly a pasted second
    # product. Printed instructions occupy A/D; B/C are otherwise blank.
    for index in range(1, len(rows) + 1):
        label = _cell(rows, index, 1)
        if isinstance(label, str) and label in label_rows and label_rows[label] != index:
            raise ValueError(f'간편입력 {index}행에 중복되거나 이동한 항목이 있습니다. 한 파일에는 한 제품만 작성해 주세요.')
        if any(not _empty(value) for value in rows[index - 1][4:]):
            raise ValueError(f'간편입력 {index}행에 양식 밖의 열이 있습니다. 한 파일에는 한 제품만 작성해 주세요.')
        if (index not in expected_rows and index != schema['header_row']
                and any(not _empty(_cell(rows, index, column)) for column in (2, 3))):
            raise ValueError(f'간편입력 {index}행에 입력칸 밖의 값이 있습니다. 한 파일에는 한 제품만 작성해 주세요.')
    values, raw_fields, cells = {}, {}, {}
    for field in fields:
        row, identifier, label = field['row'], field['id'], field['label']
        if _cell(rows, row, 1) != label:
            raise ValueError(f'간편입력 A{row} 항목은 {label}이어야 합니다. 행을 추가하거나 옮기지 말고 새 양식을 사용해 주세요.')
        cell = f'B{row}'
        raw = _cell(rows, row, 2)
        raw_fields[identifier] = {'sheet': SHEET, 'cell': cell, 'row': row, 'label': label, 'value': raw}
        cells[identifier] = {'origin': 'WORKBOOK', 'sheet': SHEET, 'cell': cell, 'row': row, 'label': label}
        if _empty(raw):
            if field.get('required'):
                raise ValueError(f'간편입력!{cell} {label}을 작성해 주세요.')
            value = None
        elif field['type'] == 'number':
            value = _number(raw, label, cell)
        elif field['type'] == 'date':
            try:
                if not isinstance(raw, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', raw):
                    raise ValueError
                value = date.fromisoformat(raw).isoformat()
            except ValueError:
                raise ValueError(f'간편입력!{cell} {label}은 실제 존재하는 YYYY-MM-DD 날짜로 작성해 주세요.') from None
        else:
            if isinstance(raw, bool):
                raise ValueError(f'간편입력!{cell} {label}을 문자로 작성해 주세요.')
            value = str(raw).strip()
        values[identifier] = value
        currency_id = field.get('currency')
        if currency_id:
            currency_cell = f'C{row}'
            currency = _cell(rows, row, 3)
            raw_fields[currency_id] = {'sheet': SHEET, 'cell': currency_cell, 'row': row,
                                       'label': label + ' 통화', 'value': currency}
            cells[currency_id] = {'origin': 'WORKBOOK', 'sheet': SHEET, 'cell': currency_cell,
                                  'row': row, 'label': label + ' 통화'}
            if _empty(currency):
                currency = None
                if value is not None:
                    raise ValueError(f'간편입력!{currency_cell} {label}의 통화를 USD·KRW 등 영문 대문자 3자리로 작성해 주세요.')
            elif not isinstance(currency, str) or not re.fullmatch(r'[A-Z]{3}', currency, re.ASCII):
                raise ValueError(f'간편입력!{currency_cell} 통화는 USD·KRW 등 영문 대문자 3자리로 작성해 주세요.')
            values[currency_id] = currency
        else:
            printed_hint = {'desired_quantity': '판매단위 기준', 'supply_quantity_30d': '판매단위 기준',
                            'preparation_days': '일', 'basis_date': '날짜'}.get(identifier)
            extra = _cell(rows, row, 3)
            if not _empty(extra) and extra != printed_hint:
                raise ValueError(f'간편입력!C{row}은 입력칸이 아닙니다. {label}의 값은 B{row}에 작성해 주세요.')
    if not values['unit'] and any(values[field] is not None for field in (
            'unit_cost', 'desired_price', 'desired_quantity', 'supply_quantity_30d')):
        raise ValueError('간편입력!B10 가격·수량을 작성한 경우 공통 판매단위(개·웨이퍼 등)를 작성해 주세요.')
    try:
        supply_end = (date.fromisoformat(values['basis_date']) + timedelta(days=29)).isoformat()
    except (ValueError, OverflowError):
        raise ValueError('작성기준일부터 30일의 공급계획 기간을 계산할 수 있는 날짜를 작성해 주세요.') from None

    mappings = {}

    def record(sheet, field_ids, constants=None, generated=None):
        row = {field: values[identifier] for field, identifier in field_ids.items()}
        origins = {field: deepcopy(cells[identifier]) for field, identifier in field_ids.items()}
        row.update(constants or {})
        for field in constants or {}:
            origins[field] = {'origin': 'TEMPLATE_CONVENTION', 'rule_version': VERSION}
        for field in generated or ():
            origins[field] = {'origin': 'GENERATED_IDENTIFIER', 'rule_version': VERSION}
        first_row = min((origin['row'] for origin in origins.values() if 'row' in origin), default=7)
        row.update(_sheet=SHEET, _row=first_row, _field_origins=deepcopy(origins))
        mappings[sheet] = origins
        return row

    product = record('제품정보', {
        '모델명': 'product_name', '제품설명': 'product_description', '사양': 'product_description',
        '제조국': 'manufacturing_country', '판매단위': 'unit', '사양서참조': 'datasheet_reference',
        '보유인증시험자료기재': 'certification_statement', '추가설명': 'additional_notes', '작성기준일': 'basis_date',
    }, {'제품ID': PRODUCT_ID, 'HS코드': None, 'HS버전': None,
        'HS코드원문': None, 'HS버전원문': None}, ['제품ID'])
    planned = record('수출예정거래', {
        '희망판매단가': 'desired_price', '통화': 'price_currency', '수량': 'desired_quantity', '단위': 'unit',
        '거래조건': 'trade_terms', '작성기준일': 'basis_date',
    }, {'거래ID': PLAN_ID, '제품ID': PRODUCT_ID, '목적국': None, '거래처ID': None,
        '최종사용자': None, '납기일': None, '단가(USD)': None}, ['거래ID', '제품ID'])
    if values['price_currency'] == 'USD':
        planned['단가(USD)'] = values['desired_price']
        planned['_field_origins']['단가(USD)'] = deepcopy(cells['desired_price'])
        mappings['수출예정거래']['단가(USD)'] = deepcopy(cells['desired_price'])
    cost = record('원가·비용', {
        '제품원가(단위당)': 'unit_cost', '통화': 'cost_currency', '원가단위': 'unit', '원가기준일': 'basis_date',
    }, {'제품ID': PRODUCT_ID, '원가적용시작일': None, '원가적용종료일': None}, ['제품ID'])
    supply = record('재고·생산', {
        '단위': 'unit', '재고기준일': 'basis_date', '공급계획시작일': 'basis_date',
        '공급가능수량': 'supply_quantity_30d', '준비기간(일)': 'preparation_days',
    }, {'제품ID': PRODUCT_ID, '가용재고': None, '추가공급가능수량': None,
        '공급계획종료일': supply_end, '공급기간일수': 30, '가용재고포함': True}, ['제품ID'])
    supply_origin = {'origin': 'DERIVED_TEMPLATE_PERIOD', 'rule_version': VERSION,
                     'formula': '작성기준일 + 29일 (기준일 포함 30일)', 'inputs': [deepcopy(cells['basis_date'])]}
    supply['_field_origins']['공급계획종료일'] = deepcopy(supply_origin)
    mappings['재고·생산']['공급계획종료일'] = supply_origin
    sheets = {'제품정보': [product]}
    if any(values[key] is not None for key in ('desired_price', 'price_currency', 'desired_quantity', 'trade_terms')):
        sheets['수출예정거래'] = [planned]
    if any(values[key] is not None for key in ('unit_cost', 'cost_currency')):
        sheets['원가·비용'] = [cost]
    if any(values[key] is not None for key in ('supply_quantity_30d', 'preparation_days')):
        sheets['재고·생산'] = [supply]
    if values['datasheet_reference']:
        sheets['증빙목록'] = [record('증빙목록', {'첨부참조': 'datasheet_reference'}, {
            '증빙ID': 'SIMPLE-DOC001', '관련제품ID': PRODUCT_ID, '관련거래ID': None,
            '문서종류': '제품 사양서', '문서번호': None, '발행일': None, '만료일': None,
        }, ['증빙ID', '관련제품ID'])]
    issues = []
    if filename.lower().endswith('.xls'):
        issues.append({'sheet': SHEET, 'row': None, 'status': 'LEGACY_VALUES',
                       'reason': '구형 .xls의 저장된 값만 읽었습니다. 원본 수식의 최신 재계산 여부는 확인하지 못합니다.'})
    input_row_count = sum(not _empty(_cell(rows, field['row'], 2)) for field in fields)
    return {'sheets': sheets, 'issues': issues,
            'row_count': input_row_count, 'accepted_row_count': input_row_count,
            'missing_sheets': sorted(set(legacy_sheets) - set(sheets)),
            'data_class': '업로드 기업 데이터 · 외부 근거 연계',
            'source': {'id': 'company-upload', 'name': filename, 'provider': '기업 업로드',
                       'sha256': sha256(data).hexdigest(), 'parser_version': VERSION,
                       'workbook_format': VERSION, 'original_sheet': SHEET,
                       'raw_fields': raw_fields, 'field_mapping': {sheet: mappings[sheet] for sheet in sheets},
                       'count_units': {'row_count': '작성한 B열 입력항목 수', 'accepted_row_count': '형식 검증을 통과한 B열 입력항목 수'},
                       'normalized_record_count': sum(len(records) for records in sheets.values()),
                       'normalization_notes': [
                           '한 파일의 한 제품을 내부 제품·계획 식별자로 연결했습니다. 실제 거래 식별자가 아닙니다.',
                           'HS·분류판·목적국은 분석 화면 선택조건이며 엑셀에서 확인한 분류·거래 증빙이 아닙니다.',
                           '공급가능수량은 작성기준일 포함 30일간의 총량이며 가용재고를 포함합니다.',
                           '원가와 희망가격의 통화를 각각 보존하며 환산하지 않았습니다.',
                           '보유 인증·시험자료는 기업의 자유기재이며 증빙 건수·인증 유효성을 생성하지 않습니다.',
                       ]}}


def bind_simple_conditions(company, inputs):
    """Apply validated UI conditions only to this explicitly marked form."""
    if company.get('source', {}).get('workbook_format') != VERSION:
        return company
    company = deepcopy(company)
    source = company['source']
    source['analysis_conditions'] = {'origin': 'ANALYSIS_FORM',
                                     **{key: inputs[key] for key in ('company', 'hs_raw', 'hs6', 'hs_edition', 'country')}}
    for sheet, assignments in (
        ('제품정보', {'HS코드': ('hs_raw', inputs['hs_raw']), 'HS버전': ('hs_edition', inputs['hs_edition'])}),
        ('수출예정거래', {'목적국': ('country', inputs['country'])}),
    ):
        for row in company['sheets'].get(sheet, []):
            for field, (input_field, value) in assignments.items():
                origin = {'origin': 'ANALYSIS_FORM', 'input_field': input_field, 'value': value}
                row[field] = value
                row['_field_origins'][field] = deepcopy(origin)
                source['field_mapping'][sheet][field] = origin
    return company
