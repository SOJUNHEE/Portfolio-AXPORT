# (junhee) 2026-09-27 sanghyeob/market_wsts.py 에서 옮김. 바꾼 것: 패키지 import 경로·원본 자료 경로(junhee/data/raw)만. 계산 로직은 그대로.
"""Read the supported WSTS workbook without executing Excel or extracting files."""

from calendar import month_name
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
from pathlib import PurePosixPath
import re
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile

MAX_FILE_BYTES = 8 * 1024 * 1024
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REGIONS = ('Americas', 'Europe', 'Japan', 'Asia Pacific', 'Worldwide')


def _amount(raw, address):
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f'{address}의 월별 금액을 확인해 주세요.') from exc
    if not value.is_finite() or value < 0 or value > Decimal('1e18'):
        raise ValueError(f'{address}의 월별 금액이 올바르지 않습니다.')
    return value


def parse_wsts(data, filename='WSTS.xlsx'):
    """Only monthly B:M observations; totals and 3MMA never enter country metrics."""
    if not isinstance(data, bytes) or not data or len(data) > MAX_FILE_BYTES:
        raise ValueError('WSTS 엑셀은 8MB 이하의 비어 있지 않은 파일이어야 합니다.')
    if not str(filename).lower().endswith('.xlsx'):
        raise ValueError('첫 구현에서는 WSTS .xlsx 양식만 지원합니다.')
    try:
        with ZipFile(BytesIO(data)) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if (len(entries) > 200 or len(names) != len(set(names))
                    or sum(entry.file_size for entry in entries) > 32 * 1024 * 1024
                    or any(entry.flag_bits & 1 for entry in entries)
                    or any('vbaProject' in name or name.startswith('xl/externalLinks/') for name in names)):
                raise ValueError('지원하지 않는 엑셀 구성 또는 파일 크기입니다.')

            def xml(name):
                content = archive.read(name)
                if b'<!DOCTYPE' in content.upper() or b'<!ENTITY' in content.upper():
                    raise ValueError('지원하지 않는 XML 구성입니다.')
                return ET.fromstring(content)

            sheets = xml('xl/workbook.xml').findall('m:sheets/m:sheet', NS)
            monthly = next((s for s in sheets if s.get('name') == 'Monthly Data'), None)
            if monthly is None:
                raise ValueError('WSTS의 Monthly Data 시트를 찾을 수 없습니다.')
            relationships = xml('xl/_rels/workbook.xml.rels')
            target = next((r.get('Target') for r in relationships
                           if r.get('Id') == monthly.get('{' + REL + '}id')
                           and r.get('TargetMode') != 'External'), None)
            if not target or '..' in PurePosixPath(target).parts:
                raise ValueError('올바른 시트 경로가 아닙니다.')
            target = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            strings = []
            if 'xl/sharedStrings.xml' in names:
                strings = [''.join(s.itertext()) for s in xml('xl/sharedStrings.xml')]
            cells, shared = {}, {}
            for cell in xml(target).findall('m:sheetData/m:row/m:c', NS):
                address = cell.get('r', '')
                if not re.fullmatch(r'[A-Z]{1,3}[1-9]\d{0,4}', address):
                    raise ValueError('지원하지 않는 셀 주소입니다.')
                if address in cells:
                    raise ValueError('중복된 셀 주소가 있습니다.')
                value = cell.find('m:v', NS)
                value = value.text if value is not None else None
                if cell.get('t') == 's' and value is not None:
                    value = strings[int(value)]
                elif cell.get('t') == 'inlineStr':
                    inline = cell.find('m:is', NS)
                    if inline is None:
                        raise ValueError('올바르지 않은 문자열 셀입니다.')
                    value = ''.join(inline.itertext())
                formula = cell.find('m:f', NS)
                if formula is not None and formula.get('t') == 'shared' and formula.text:
                    index = formula.get('si')
                    if index is None or index in shared:
                        raise ValueError('공유 수식의 기준 셀이 올바르지 않습니다.')
                    shared[index] = (address, formula)
                cells[address] = (value, formula)
    except (BadZipFile, KeyError, IndexError, ET.ParseError, TypeError, OSError,
            RuntimeError, NotImplementedError) as exc:
        raise ValueError('WSTS 엑셀을 읽을 수 없습니다. 원본 .xlsx 양식을 확인해 주세요.') from exc

    def text(address):
        return str(cells.get(address, (None, None))[0] or '').strip()

    def populated(address):
        raw, formula = cells.get(address, (None, None))
        return raw not in (None, '') or formula is not None

    if '1000 US$' not in text('A3'):
        raise ValueError('WSTS 원단위(1000 US$)를 확인할 수 없습니다.')
    if any(text(chr(65 + month) + '4') != month_name[month] for month in range(1, 13)):
        raise ValueError('WSTS 월별 열 구조가 다릅니다. 자동으로 추정하지 않습니다.')
    series, missing, regions, seen = [], 0, set(), set()
    year_rows, region_rows, verified = {}, {}, 0
    year = None
    rows = sorted({int(re.search(r'\d+$', address).group()) for address in cells})
    for row in rows:
        label = text(f'A{row}')
        if re.fullmatch(r'(19|20)\d{2}', label):
            year = int(label)
            if year in year_rows or any(populated(f'{chr(65 + m)}{row}') for m in range(1, 13)):
                raise ValueError('연도 행이 중복되었거나 월별 열 구조가 다릅니다.')
            year_rows[year] = []
        elif year and label:
            label = 'Asia Pacific' if label == 'Asia Pacific/All Other' else label
            if label not in REGIONS or label in year_rows[year]:
                raise ValueError('알 수 없거나 중복된 권역 행이 있습니다. 원본 양식을 확인해 주세요.')
            year_rows[year].append(label)
            region_rows[row] = (year, label)
            regions.add(label)
        elif year and any(populated(f'{chr(65 + m)}{row}') for m in range(1, 13)):
            raise ValueError('권역 이름 없이 월별 금액이 있는 행입니다.')
        elif year is None and row >= 5 and (label or any(populated(f'{chr(65 + m)}{row}') for m in range(1, 13))):
            raise ValueError('연도 없이 월별 자료가 있는 행입니다.')
    if not year_rows or any(tuple(labels) != REGIONS for labels in year_rows.values()):
        raise ValueError('각 연도에 세계·4개 권역이 원본 순서대로 있어야 합니다.')

    for row, (year, label) in region_rows.items():
            for month in range(1, 13):
                address = f'{chr(65 + month)}{row}'
                raw, formula = cells.get(address, (None, None))
                formula_text, inputs = None, []
                if formula is not None:
                    # Only the documented same-column sum of four regional observations
                    # is evaluated. No Excel engine, arbitrary functions or external refs.
                    formula_text = formula.text
                    if formula.get('t') == 'shared':
                        master = shared.get(formula.get('si'))
                        if master is None:
                            raise ValueError('공유 수식의 기준 셀을 찾을 수 없습니다.')
                        master_address, master_formula = master
                        bounds = re.fullmatch(r'([B-M])(\d+):([B-N])(\d+)', master_formula.get('ref', ''))
                        source = re.fullmatch(r'SUM\(([B-M])(\d+):\1(\d+)\)', master_formula.text or '')
                        if (not bounds or not source or bounds[2] != str(row) or bounds[4] != str(row)
                                or not bounds[1] <= address[0] <= bounds[3]
                                or master_address != bounds[1] + str(row)
                                or source[1] != master_address[0]):
                            raise ValueError('지원하지 않는 공유 수식 범위입니다.')
                        formula_text = f'SUM({address[0]}{source[2]}:{address[0]}{source[3]})'
                    elif formula.get('t') not in (None, 'normal'):
                        raise ValueError('지원하지 않는 월별 수식 형식입니다.')
                    expected = f'SUM({address[0]}{row - 4}:{address[0]}{row - 1})'
                    if (label != 'Worldwide' or formula_text != expected
                            or [region_rows.get(r) for r in range(row - 4, row)]
                            != [(year, region) for region in REGIONS[:4]]):
                        raise ValueError('월별 수식은 같은 열의 4개 권역 합계만 지원합니다.')
                    inputs = [f'{address[0]}{r}' for r in range(row - 4, row)]
                    if any(cells.get(ref, (None, None))[1] is not None for ref in inputs):
                        raise ValueError('권역 원관측에 수식이 있습니다. 검토가 필요합니다.')
                    calculated = sum((_amount(cells.get(ref, (None, None))[0], ref) for ref in inputs), Decimal(0))
                    if _amount(raw, address) != calculated:
                        raise ValueError(f'{address}의 세계 합계 수식과 저장된 값이 일치하지 않습니다.')
                    verified += 1
                if raw in (None, ''):
                    missing += 1
                    continue
                amount = _amount(raw, address)
                value = float(amount * 1000)
                period = f'{year:04d}-{month:02d}'
                if (period, label) in seen:
                    raise ValueError('같은 기간·권역의 관측이 중복되었습니다.')
                seen.add((period, label))
                series.append({'period': period, 'region': label, 'value_usd': value,
                               'source_sheet': 'Monthly Data', 'source_cell': address,
                               'value_raw': str(raw), 'unit_raw': '1000 US$',
                               'status': 'OBSERVED_ZERO' if amount == 0 else 'OBSERVED',
                               'formula': formula_text, 'formula_verified': formula is not None,
                               'formula_input_cells': inputs})
    if not series or len(regions) != 5 or 'Worldwide' not in regions:
        raise ValueError('WSTS의 세계·4개 권역 월별 자료를 확인할 수 없습니다.')
    return {'name': str(filename), 'sha256': sha256(data).hexdigest(), 'status': 'READY',
            'latest_period': max(p['period'] for p in series), 'unit': 'USD',
            'scope': '세계·권역 반도체 산업 참고자료. 국가·HS 시장 점수에는 반영하지 않습니다.',
            'series': series, 'observed_count': len(series), 'missing_count': missing,
            'formula_verified_count': verified, 'parser_version': 'wsts-monthly-v1',
            'regions': sorted(regions),
            'warnings': ['원단위 천 USD를 USD로 변환했습니다. 연간·분기 합계와 3MMA는 합산하지 않습니다.',
                         '미수록 셀은 0으로 채우지 않습니다. 산업자료와 무역통계의 기준기간은 별도입니다.']}
