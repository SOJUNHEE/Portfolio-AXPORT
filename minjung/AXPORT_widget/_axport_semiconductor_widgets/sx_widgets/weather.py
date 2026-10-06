"""HS-group export statistics, independent of the KSTAT/MTI methodology."""
import math
import calendar
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlencode, unquote
from urllib.request import urlopen

GROUPS = {
    'memory': ['854232'],
    'processor': ['854231'],
    'other': ['854233', '854239', '854290'],
    'device': ['8541'],
}
ENDPOINT = 'https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList'


def parse_page(raw):
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('cp949')
    root = ET.fromstring(text)
    if root.findtext('.//resultCode') not in ('00', '0'):
        raise ValueError('Customs API error; check approval and quota')
    rows = [{child.tag: child.text or '' for child in item} for item in root.findall('.//items/item')]
    total = root.findtext('.//totalCount')
    return rows, int(total) if total is not None else None


def fetch_prefix(key, year, month, prefix):
    records = []
    for page in range(1, 101):
        params = dict(serviceKey=unquote(key), strtYymm=f'{year}01', endYymm=f'{year}{month:02}',
                      hsSgn=prefix, numOfRows=100, pageNo=page)
        # Failures are sanitized by the CLI. Never print a URL containing the key.
        with urlopen(ENDPOINT + '?' + urlencode(params), timeout=30) as response:
            rows, total = parse_page(response.read(8_000_000))
        records.extend(rows)
        if total is not None and len(records) >= total:
            break
        if total is None and len(rows) < 100:
            break
        if not rows:
            raise ValueError('Incomplete pagination')
        time.sleep(0.3)
    else:
        raise ValueError('Pagination safety limit reached')
    return aggregate(records, year, month, prefix)


def aggregate(records, year, month, prefix):
    """Sum exact 10-digit leaf rows; exclude aggregate rows and reject duplicates."""
    monthly = {}
    seen = set()
    for row in records:
        period = row.get('year', '')
        if not re.fullmatch(r'\d{4}\.\d{2}', period):
            continue  # e.g. 총계, 합계; never count totals alongside leaves.
        yy, mm = map(int, period.split('.'))
        hs = row.get('hsCode', '')
        if yy != year or not 1 <= mm <= month:
            raise ValueError('Unexpected reporting period')
        if not re.fullmatch(r'\d{10}', hs) or not hs.startswith(prefix):
            raise ValueError('Expected exact 10-digit HS leaf rows')
        identity = period, hs
        if identity in seen:
            raise ValueError('Duplicate HS/month record')
        seen.add(identity)
        value = row.get('expDlr', '')
        if not re.fullmatch(r'\d+', value):
            raise ValueError('Missing or invalid export value')
        monthly[mm] = monthly.get(mm, 0) + int(value)
    if set(monthly) != set(range(1, month + 1)):
        raise ValueError('Missing monthly data; not replaced with zero')
    return sum(monthly.values())


def build_report(key, year, month, fetcher=fetch_prefix):
    now = datetime.now(timezone.utc)
    if not 2023 <= year <= now.year or not 1 <= month <= 12 or (year, month) >= (now.year, now.month):
        raise ValueError('Use a completed reporting month')
    rows = []
    for group, prefixes in GROUPS.items():
        current = sum(fetcher(key, year, month, prefix) for prefix in prefixes)
        previous = sum(fetcher(key, year - 1, month, prefix) for prefix in prefixes)
        yoy = float((Decimal(current) / Decimal(previous) - 1) * 100) if previous else None
        rows.append(dict(id=group, hs=prefixes, exports_million_usd=current / 1_000_000,
                         exports_usd=current, previous_exports_usd=previous, yoy=yoy))
    return dict(status='ok', mode='live', source='Korea Customs Service',
                as_of=f'{year}-{month:02}-{calendar.monthrange(year,month)[1]:02}T00:00:00+00:00', fetched_at=now.isoformat(),
                period=f'{year}.{month:02}', basis='cumulative', classification='HS 2022',
                note='Custom HS groups; 8541 includes photovoltaic devices, LEDs and mounted piezoelectric crystals. Not the KSTAT/MTI concordance.', rows=rows)


def validate_report(report):
    if report.get('status') != 'ok' or report.get('mode') != 'live' or report.get('basis') != 'cumulative':
        raise ValueError('Expected a live cumulative report')
    if not re.fullmatch(r'\d{4}\.(0[1-9]|1[0-2])', report.get('period', '')):
        raise ValueError('Invalid period')
    if report.get('source') != 'Korea Customs Service' or report.get('classification') != 'HS 2022':
        raise ValueError('Unexpected source/classification')
    datetime.fromisoformat(report['fetched_at'])
    datetime.fromisoformat(report['as_of'])
    rows = report.get('rows', [])
    if len(rows) != 4 or {row.get('id') for row in rows} != set(GROUPS):
        raise ValueError('Expected four unique groups')
    for row in rows:
        if row.get('hs') != GROUPS[row['id']]:
            raise ValueError('Unexpected group mapping')
        for key in ('exports_usd', 'previous_exports_usd'):
            if type(row.get(key)) is not int or row[key] < 0:
                raise ValueError('Invalid amount')
        amount, previous, millions, yoy = row['exports_usd'], row['previous_exports_usd'], row.get('exports_million_usd'), row.get('yoy')
        if not isinstance(millions, (int, float)) or not math.isfinite(millions) or not math.isclose(amount/1_000_000, millions):
            raise ValueError('Invalid amount scale')
        if previous == 0:
            if yoy is not None:
                raise ValueError('Zero denominator must not produce a rate')
        elif not isinstance(yoy, (int,float)) or not math.isfinite(yoy) or not math.isclose(yoy, float((Decimal(amount)/Decimal(previous)-1)*100), abs_tol=0.0001):
            raise ValueError('Invalid year-over-year calculation')
