# (junhee) 2026-09-27 sanghyeob/company_import.py 에서 옮김. 바꾼 것: 패키지 import 경로·원본 자료 경로(junhee/data/raw)만. 계산 로직은 그대로.
"""Read enterprise workbooks; never execute formulas, macros or external links."""
from collections import Counter
from datetime import date, datetime
from hashlib import sha256
from io import BytesIO
import math
import re
from struct import error as StructError
import xml.etree.ElementTree as ET
from zipfile import ZipFile, BadZipFile

import openpyxl
import xlrd
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl.styles.numbers import is_datetime

from .company_simple import SHEET as SIMPLE_SHEET, SimpleWorkbookError, parse_simple

MAX_COMPANY_BYTES = 20 * 1024 * 1024
MAX_ROWS = 20000
MAX_COLUMNS = 100
MAX_SHEETS = 30
MAX_CELLS = 300000
SHEETS = {
    '제품정보': '제품ID', '수출예정거래': '거래ID', '수출실적': '실적ID',
    '원가·비용': '제품ID', '재고·생산': '제품ID', '물류': '물류ID',
    '거래처': '거래처ID', '증빙목록': '증빙ID',
}
COUNTRIES = {'US': '미국', 'CN': '중국', 'JP': '일본', 'DE': '독일', 'VN': '베트남'}
EVENT_TIME_HEADERS = {'운송인인계시각', '최종인수시각'}


def normalized_hs(value):
    if isinstance(value, bool):
        return ''
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            return ''
        value = int(value)
    if not isinstance(value, (str, int)):
        return ''
    text = re.sub(r'[.\s]', '', str(value))
    return text if re.fullmatch(r'[0-9]{6}(?:[0-9]{2}|[0-9]{4})?', text) else ''


def validate_conditions(payload):
    if not isinstance(payload, dict):
        raise ValueError('기업명·HS 코드·대상국을 확인해 주세요.')
    company = payload.get('company')
    if not isinstance(company, str) or not 1 <= len(company.strip()) <= 120 or any(ord(c) < 32 for c in company):
        raise ValueError('기업명은 1~120자로 입력해 주세요.')
    hs = payload.get('hs', payload.get('hs_raw'))
    if not isinstance(hs, str) or not re.fullmatch(r'\d{6}(?:\d{2}|\d{4})?', hs, re.ASCII):
        raise ValueError('HS 코드는 숫자 6·8·10자리로 입력해 주세요.')
    country = payload.get('country')
    if not isinstance(country, str) or country not in COUNTRIES:
        raise ValueError('현재 분석 화면의 지원 대상국을 선택해 주세요.')
    return {'company': company.strip(), 'hs_raw': hs, 'hs6': hs[:6], 'hs_edition': 'HS2022',
            'country': country, 'country_name': COUNTRIES[country], 'as_of': date.today().isoformat()}


def _value(value, *, preserve_time=False):
    if isinstance(value, datetime) and preserve_time:
        return value.isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()[:10]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('유한하지 않은 숫자가 있습니다.')
    if value is None or isinstance(value, (str, int, float, bool)):
        return value.strip() if isinstance(value, str) else value
    return str(value)


def _xlsx_rows(data):
    try:
        with ZipFile(BytesIO(data)) as z:
            entries = z.infolist()
            names = [x.filename for x in entries]
            if (len(entries) > 2000 or len(names) != len(set(names))
                    or sum(x.file_size for x in entries) > 80 * 1024 * 1024
                    or any(x.flag_bits & 1 for x in entries)
                    or any('vbaproject' in n.lower() or n.startswith('xl/externalLinks/') for n in names)):
                raise ValueError('암호화·매크로·외부 링크 또는 너무 큰 엑셀 구성은 지원하지 않습니다.')
            for name in names:
                if name.lower().endswith(('.xml', '.rels')):
                    raw = z.read(name)
                    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper() or b'\x00' in raw[:100]:
                        raise ValueError('지원하지 않는 XML 구성입니다.')
        wb = openpyxl.load_workbook(BytesIO(data), read_only=True, data_only=False, keep_links=False)
        try:
            if len(wb.sheetnames) > MAX_SHEETS:
                raise ValueError('시트는 30개 이하로 업로드해 주세요.')
            if SIMPLE_SHEET in wb.sheetnames and len(wb.sheetnames) != 1:
                raise SimpleWorkbookError('간편입력은 한 파일에 한 제품·한 시트만 작성해 주세요. 기존 상세 시트나 다른 제품 시트와 혼합할 수 없습니다.')
            out = {}
            cell_count = 0
            for ws in wb.worksheets:
                if ws.title not in SHEETS and ws.title != SIMPLE_SHEET:
                    continue
                if (ws.max_row or 0) > MAX_ROWS or (ws.max_column or 0) > MAX_COLUMNS:
                    raise ValueError(f'{ws.title} 시트는 {MAX_ROWS:,}행·100열 이하로 정리해 주세요.')
                # Worksheet dimension metadata can lie or be absent. Bound actual reads too.
                ws.reset_dimensions()
                parsed_rows = []
                event_columns = set()
                for index, row in enumerate(ws.iter_rows(), 1):
                    cell_count += len(row)
                    if index > MAX_ROWS or len(row) > MAX_COLUMNS or cell_count > MAX_CELLS:
                        raise ValueError('실제 시트 내용이 행·열·전체 셀 수의 지원 범위를 넘었습니다.')
                    if ws.title in SHEETS and index <= 20 and row and _value(row[0].value) == SHEETS[ws.title]:
                        event_columns = {i for i, c in enumerate(row) if _value(c.value) in EVENT_TIME_HEADERS}
                    parsed_rows.append([('FORMULA', c.coordinate) if c.data_type == 'f' else _value(
                        c.value, preserve_time=i in event_columns and is_datetime(c.number_format) == 'datetime')
                        for i, c in enumerate(row)])
                out[ws.title] = parsed_rows
            return out
        finally:
            wb.close()
    except (BadZipFile, KeyError, OSError, TypeError, ET.ParseError, InvalidFileException,
            IndexError, RuntimeError, SyntaxError) as exc:
        raise ValueError('엑셀을 읽을 수 없습니다. 원본 .xlsx 파일인지 확인해 주세요.') from exc


def _xls_rows(data):
    try:
        # Ragged rows prevent xlrd from padding every sparse row to the widest
        # column before our dimensions and aggregate-cell checks can run.
        wb = xlrd.open_workbook(file_contents=data, on_demand=True, ragged_rows=True, formatting_info=True)
        try:
            out = {}
            names = wb.sheet_names()
            if len(names) > MAX_SHEETS:
                raise ValueError('시트는 30개 이하로 업로드해 주세요.')
            if SIMPLE_SHEET in names and len(names) != 1:
                raise SimpleWorkbookError('간편입력은 한 파일에 한 제품·한 시트만 작성해 주세요. 기존 상세 시트나 다른 제품 시트와 혼합할 수 없습니다.')
            cell_count = 0
            for name in names:
                if name not in SHEETS and name != SIMPLE_SHEET:
                    continue
                ws = wb.sheet_by_name(name)
                if ws.nrows > MAX_ROWS or ws.ncols > MAX_COLUMNS:
                    raise ValueError(f'{name} 시트의 크기가 지원 범위를 넘었습니다.')
                # Count the same row widths that XLSX's streaming iterator reads,
                # without charging all blank rows as a dense bounding rectangle.
                cell_count += sum(ws.row_len(r) for r in range(ws.nrows))
                if cell_count > MAX_CELLS:
                    raise ValueError('전체 셀 수의 지원 범위를 넘었습니다.')
                rows = []
                event_columns = set()
                for r in range(ws.nrows):
                    values = []
                    raw_row = ws.row(r)
                    if name in SHEETS and r < 20 and raw_row and _value(raw_row[0].value) == SHEETS[name]:
                        event_columns = {i for i, c in enumerate(raw_row) if _value(c.value) in EVENT_TIME_HEADERS}
                    for i, c in enumerate(raw_row):
                        value = c.value
                        preserve_time = False
                        if c.ctype == xlrd.XL_CELL_DATE:
                            value = xlrd.xldate.xldate_as_datetime(c.value, wb.datemode)
                            format_key = wb.xf_list[c.xf_index].format_key
                            format_string = wb.format_map[format_key].format_str
                            preserve_time = i in event_columns and is_datetime(format_string) == 'datetime'
                        values.append(_value(value, preserve_time=preserve_time))
                    rows.append(values)
                out[name] = rows
            return out
        finally:
            wb.release_resources()
    except SimpleWorkbookError:
        raise
    except (xlrd.XLRDError, xlrd.compdoc.CompDocError, OSError, ValueError, IndexError, StructError) as exc:
        raise ValueError('구형 엑셀을 읽을 수 없습니다. 암호를 해제하거나 .xlsx 값 파일로 저장해 주세요.') from exc


def parse_company(data, filename):
    name = str(filename).replace('\\', '/').rsplit('/', 1)[-1]
    safe_name = name
    if not name or len(name) > 120 or any(ord(c) < 32 for c in name):
        raise ValueError('파일 이름은 제어문자 없이 120자 이하로 지정해 주세요.')
    if not isinstance(data, bytes) or not data or len(data) > MAX_COMPANY_BYTES:
        raise ValueError('비어 있지 않은 20MB 이하의 기업 엑셀을 선택해 주세요.')
    if name.lower().endswith('.xlsx'):
        raw_sheets = _xlsx_rows(data)
    elif name.lower().endswith('.xls'):
        raw_sheets = _xls_rows(data)
    else:
        raise ValueError('기업 데이터는 .xlsx 또는 .xls 파일로 업로드해 주세요.')
    if SIMPLE_SHEET in raw_sheets:
        return parse_simple(raw_sheets[SIMPLE_SHEET], data, safe_name, SHEETS)
    if '제품정보' not in raw_sheets:
        raise ValueError('제품정보 시트가 없습니다. 기존 샘플과 같은 기업 데이터 양식을 사용해 주세요.')
    sheets, issues, raw_count = {}, [], 0
    demo = False
    for name, rows in raw_sheets.items():
        marker = SHEETS[name]
        header_at = next((i for i, row in enumerate(rows[:20]) if row and row[0] == marker), None)
        if header_at is None:
            issues.append({'sheet': name, 'row': None, 'reason': f'{marker}로 시작하는 헤더를 찾지 못했습니다.', 'status': 'INVALID_SCHEMA'})
            continue
        demo |= any('가상 데이터' in str(v) for row in rows[:header_at] for v in row)
        headers = rows[header_at]
        labels = [h for h in headers if h not in (None, '')]
        if any(not isinstance(h, str) for h in labels) or len(labels) != len(set(labels)):
            raise ValueError(f'{name} 시트의 열 이름이 중복되었거나 올바르지 않습니다.')
        accepted, seen = [], {}
        conflicts = set()
        for index, row in enumerate(rows[header_at + 1:], header_at + 2):
            if not any(v not in (None, '') for v in row):
                continue
            raw_count += 1
            if any(isinstance(v, tuple) and v[0] == 'FORMULA' for v in row):
                # A cached/unverified formula row must not leave another row of
                # the same identity looking authoritative merely by appearing first.
                literal_id = row[0]
                if (isinstance(literal_id, (str, int, float)) and not isinstance(literal_id, bool)
                        and str(literal_id).strip()):
                    conflicts.add(str(literal_id))
                issues.append({'sheet': name, 'row': index, 'status': 'FORMULA_NOT_VERIFIED',
                               'reason': '수식이 포함된 행과 같은 ID의 행을 계산에서 제외했습니다. 확인된 값을 붙여넣어 다시 제출해 주세요.'})
                continue
            record = {h: row[i] if i < len(row) else None for i, h in enumerate(headers) if h}
            record.update(_row=index, _sheet=name)
            identifier = record.get(marker)
            if identifier is None or isinstance(identifier, bool) or not str(identifier).strip():
                issues.append({'sheet': name, 'row': index, 'status': 'MISSING_ID', 'reason': f'{marker}가 없는 행을 제외했습니다.'})
                continue
            identifier = str(identifier)
            record[marker] = identifier
            if identifier in seen:
                first = seen[identifier]
                same = {k: v for k, v in first.items() if not k.startswith('_')} == {k: v for k, v in record.items() if not k.startswith('_')}
                if not same:
                    conflicts.add(identifier)
                issues.append({'sheet': name, 'row': index, 'status': 'DUPLICATE_ID' if same else 'CONFLICT',
                               'reason': f'{marker} {identifier}: ' + ('완전 중복 행은 한 번만 사용합니다.' if same else '값이 충돌해 해당 ID의 모든 행을 제외합니다.')})
                continue
            seen[identifier] = record
            accepted.append(record)
        sheets[name] = [r for r in accepted if r[marker] not in conflicts]
    if not sheets.get('제품정보'):
        raise ValueError('분석 가능한 제품정보 행이 없습니다. 제품ID·HS코드·HS버전을 확인해 주세요.')
    if safe_name.lower().endswith('.xls'):
        issues.append({'sheet': None, 'row': None, 'status': 'LEGACY_VALUES',
                       'reason': '구형 .xls의 저장된 값만 읽었습니다. 원본 수식의 최신 재계산 여부는 확인하지 못합니다.'})
    return {'sheets': sheets, 'issues': issues, 'row_count': raw_count,
            'accepted_row_count': sum(len(x) for x in sheets.values()),
            'missing_sheets': sorted(set(SHEETS) - set(sheets)),
            'data_class': '가상 기업 데이터 · 외부 근거 연계' if demo else '업로드 기업 데이터 · 외부 근거 연계',
            'source': {'id': 'company-upload', 'name': safe_name, 'provider': '기업 업로드',
                       'sha256': sha256(data).hexdigest(), 'parser_version': 'company-workbook-v1'}}
