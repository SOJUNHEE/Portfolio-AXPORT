"""Optional server-side providers. No credentials enter HTML or JSON responses."""
import json
import os
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen


class ProviderError(Exception):
    def __init__(self, code='upstream_unavailable', source=''):
        self.code, self.source = code, source


def fetch_json(url):
    try:
        request = Request(url, headers={'User-Agent': 'AXPORT-Student-Dashboard/1.0'})
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read(2_000_000))
    except Exception:
        raise ProviderError() from None


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class DataService:
    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()
        self.demo = os.getenv('AXPORT_DATA_MODE', 'demo').lower() != 'live'
        self.fx_snapshot = None
        self.fx_prior = None

    def get(self, kind, language='ko'):
        if self.demo:
            return self.demo_data(kind, language)
        identity = (kind, language if kind == 'news' else '')
        # One process-wide provider request at a time prevents duplicate quota use.
        with self.lock:
            old = self.cache.get(identity)
            if old and old[0] > time.monotonic():
                if isinstance(old[1], ProviderError):
                    raise old[1]
                return old[1]
            try:
                result = getattr(self, kind)(language)
            except ProviderError as error:
                self.cache[identity] = (time.monotonic() + 300, error)
                raise
            except Exception:
                error = ProviderError(source=kind)
                self.cache[identity] = (time.monotonic() + 300, error)
                raise error from None
            ttl = {'fx': 3600, 'news': 7200, 'weather': 86400}[kind]
            self.cache[identity] = (time.monotonic() + ttl, result)
            return result

    @staticmethod
    def key(name, source):
        value = os.getenv(name, '').strip()
        if not value:
            raise ProviderError('missing_key', source)
        return value

    def fx(self, _language):
        key = self.key('EXCHANGERATE_API_KEY', 'ExchangeRate-API')
        data = fetch_json('https://v6.exchangerate-api.com/v6/' + quote(key, safe='') + '/latest/USD')
        if data.get('result') != 'success':
            raise ProviderError(source='ExchangeRate-API')
        rates = data['conversion_rates']
        values = {'USD/KRW': rates['KRW'], 'USD/CNY': rates['CNY'],
                  'EUR/KRW': rates['KRW'] / rates['EUR']}
        timestamp = data['time_last_update_unix']
        if self.fx_snapshot and self.fx_snapshot[0] != timestamp:
            self.fx_prior = self.fx_snapshot
        previous = self.fx_prior
        rows = []
        for pair, value in values.items():
            # Only call a delta "previous day" when snapshots are consecutive UTC days.
            delta = None
            if previous and 0 < timestamp - previous[0] <= 90000 and datetime.fromtimestamp(timestamp, timezone.utc).date() != datetime.fromtimestamp(previous[0], timezone.utc).date():
                delta = (value / previous[1][pair] - 1) * 100
            rows.append(dict(pair=pair, value=value, change=delta))
        if not self.fx_snapshot or self.fx_snapshot[0] != timestamp:
            self.fx_snapshot = (timestamp, values)
        return dict(status='ok', mode='live', source='ExchangeRate-API', rows=rows,
                    as_of=datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
                    fetched_at=utc_now(), frequency='daily')

    def news(self, language):
        key = self.key('THENEWS_API_KEY', 'The News API')
        queries = {
            'ko': '반도체 | 수출통제 | CBAM',
            'en': 'semiconductor | "export controls" | CBAM',
            'ja': '半導体 | 輸出規制 | CBAM',
            'zh': '半导体 | 出口管制 | CBAM',
        }
        parameters = dict(api_token=key, language=language, search=queries[language],
                          search_fields='title,description', sort='published_at', limit=3)
        data = fetch_json('https://api.thenewsapi.com/v1/news/all?' + urlencode(parameters))
        if not isinstance(data.get('data'), list):
            raise ProviderError(source='The News API')
        rows = [{key: row.get(key) for key in ('title', 'source', 'url', 'published_at', 'language')}
                for row in data['data'][:3]]
        return dict(status='ok', mode='live', source='The News API', rows=rows,
                    language=language, fetched_at=utc_now(), as_of=utc_now())

    def weather(self, _language):
        # Explicit offline import boundary: do not invent a KSTAT/MTI concordance.
        # Validated aggregated customs data can be exported by the supplied CLI.
        from pathlib import Path
        path = os.getenv('AXPORT_WEATHER_JSON', '').strip()
        if not path:
            raise ProviderError('weather_not_configured', 'Korea Customs Service')
        from .weather import validate_report
        try:
            report = json.loads(Path(path).read_text(encoding='utf-8-sig'))
            validate_report(report)
        except Exception:
            raise ProviderError('invalid_weather_data', 'Korea Customs Service') from None
        return report

    @staticmethod
    def demo_data(kind, language):
        base = dict(status='ok', mode='demo', source='AXPORT UI sample',
                    as_of='2026-08-31T00:00:00+00:00', fetched_at=utc_now())
        if kind == 'fx':
            base['rows'] = [dict(pair='USD/KRW', value=1382.50, change=0.32),
                            dict(pair='USD/CNY', value=7.1248, change=-0.08),
                            dict(pair='EUR/KRW', value=1514.86, change=0.21)]
        elif kind == 'news':
            titles = {
                'ko': ['AI 수요와 메모리 반도체 수출 동향 살펴보기', '주요국 반도체 수출통제: 거래 전 확인할 사항', 'EU CBAM 규제와 공급망: 적용 범위 확인하기'],
                'en': ['AI demand and memory chip exports: a market overview', 'Semiconductor export controls: checks before a trade', 'EU CBAM and supply chains: understanding the scope'],
                'ja': ['AI需要とメモリー半導体の輸出動向', '半導体の輸出規制：取引前の確認事項', 'EU CBAMとサプライチェーン：適用範囲の確認'],
                'zh': ['AI需求与存储芯片出口趋势', '半导体出口管制：交易前的核查事项', '欧盟CBAM与供应链：确认适用范围'],
            }
            base['rows'] = [dict(title=title, source='AXPORT · DEMO', url=None,
                                 published_at=None, language=language) for title in titles[language]]
        else:
            base.update(period='2026.08', basis='cumulative', classification='HS 2022',
                        rows=[dict(id='memory', hs=['854232'], exports_million_usd=240353, yoy=256.6),
                              dict(id='processor', hs=['854231'], exports_million_usd=38216, yoy=18.4),
                              dict(id='other', hs=['854233','854239','854290'], exports_million_usd=12408, yoy=-6.2),
                              dict(id='device', hs=['8541'], exports_million_usd=4826, yoy=-22.8)])
        return base
