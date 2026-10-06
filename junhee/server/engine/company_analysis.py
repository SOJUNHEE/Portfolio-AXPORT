# (junhee) 2026-09-27 sanghyeob/company_analysis.py 에서 옮김. 바꾼 것: 패키지 import 경로·원본 자료 경로(junhee/data/raw)만. 계산 로직은 그대로.
"""Enterprise upload -> one persisted assessment shared by the existing five tabs."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import math
from pathlib import Path
from threading import Lock
import time

from .company_import import parse_company, validate_conditions, normalized_hs
from .company_simple import VERSION as SIMPLE_VERSION, bind_simple_conditions
from .market_service import MarketError, MarketStore, timestamp
from .analysis_policy import (CANDIDATES, COUNTRY_NAMES, country_window, policy_snapshot,
                             month_offset, refresh_comparison, select_comparisons, unavailable_comparisons)

FACTORS = [('regulation', '규제'), ('market', '시장성'), ('price', '가격'), ('logistics', '물류'), ('stability', '안정성')]


def apply_reference_scores(factors, comparison, inputs, trades):
    """Attach the approved independent domain indices, never a partial total."""
    from .analysis_scoring import score_comparison, rubric_snapshot
    rubric = rubric_snapshot()
    for domain, maximum in (('market', 40), ('stability', 10)):
        factor = next(f for f in factors if f['key'] == domain)
        window = comparison[domain]
        try:
            scoring = score_comparison(domain, window, inputs, trades)
        except Exception:
            scoring = {'domain': domain, 'rubric_version': rubric['version'],
                       'status': 'INVALID_SCORE_INPUT', 'raw_max': maximum,
                       'window_id': window.get('window_id'), 'scoring_id': None,
                       'scope': {k: inputs[k] for k in ('hs6', 'hs_edition', 'as_of')},
                       'included': list(window.get('included', [])), 'excluded': deepcopy(window.get('excluded', [])),
                       'country_scores': [], 'method': 'average_tie_rank',
                       'warnings': ['점수 입력 검증에 실패하여 이 영역의 상대 참고지수를 보류합니다.'], 'limitations': []}
        window['scoring'] = scoring
        selected = next((row for row in scoring['country_scores'] if row['country'] == inputs['country']), None)
        detail = {key: deepcopy(scoring.get(key)) for key in (
            'domain', 'rubric_version', 'window_id', 'scoring_id', 'scope', 'included', 'excluded',
            'method', 'limitations', 'comparability_status', 'valuation_bases', 'valuation_unknown_countries')}
        detail.update(deepcopy(selected) if selected else {
            'country': inputs['country'], 'status': scoring['status'] if scoring['status'] != 'CALCULATED_REFERENCE' else 'NOT_COMPARABLE',
            'raw_score': None, 'score': None, 'raw_max': maximum, 'score_max': 100, 'components': [],
            'reason': '선택 국가는 이 공통 비교집합에 포함되지 않거나 점수 입력 검증을 통과하지 못했습니다.'})
        # Keep a selected-tab processing failure from looking like a validated
        # score. Cohort scores stay independent of the chosen company/country.
        if detail['status'] == 'CALCULATED_REFERENCE':
            metrics = factor.get('metrics', [])
            expected_ids = {item['id'] for item in rubric['domains'][domain]['components']}
            valid = {item.get('id') for item in detail.get('components', [])} == expected_ids
            for component in detail.get('components', []):
                matches = [metric for metric in metrics if metric.get('id') == component['id']]
                metric = matches[0] if len(matches) == 1 else {}
                value, expected = metric.get('value'), component.get('value')
                if (type(value) not in (int, float) or type(expected) not in (int, float)
                        or not math.isfinite(value) or not math.isfinite(expected)
                        or metric.get('status') not in {'OBSERVED', 'OBSERVED_ZERO'}
                        or (metric.get('status') == 'OBSERVED_ZERO' and value != 0)
                        or metric.get('unit') != component.get('unit')
                        or metric.get('period') != component.get('period')
                        or value != component.get('comparison_value')):
                    valid = False
            if not valid:
                detail.update(status='INVALID_SCORE_INPUT', raw_score=None, score=None,
                              reason='선택 탭의 원지표와 점수 계산 입력이 일치하지 않아 점수를 보류합니다.')
        factor.update(scoring=detail, raw_score=detail.get('raw_score'), raw_max=maximum,
                      score=detail.get('score'), score_status=detail['status'])
        factor['checks'] = [check for check in factor.get('checks', []) if check.get('label') != '점수 산식']
        factor['checks'].append({'label': '상대 참고지수 산식', 'status': detail['status'],
                                'detail': detail.get('reason') or '같은 영역·기간·비교집합의 원값으로 계산한 상대 참고지수입니다.'})
        factor.setdefault('warnings', []).extend(scoring.get('warnings', []))
        factor['note'] = ('동일 기간의 원기관 신고수입액·한국 수출액을 비교한 시장성 상대 참고지수입니다.' if domain == 'market'
                          else '동일 36개월의 수입 변동계수·급감 빈도를 비교한 안정성 상대 참고지수입니다.')
        factor['note'] += ' 국가별 통계의 한계를 함께 확인해야 하며 기업 수익성·수출 성공확률·최종 적합 판정이 아닙니다.'


def unavailable_factor(key, label, reason):
    return {'key': key, 'label': label, 'state': 'insufficient', 'score': None,
            'score_status': 'PENDING_METHODOLOGY', 'note': reason, 'metrics': [],
            'warnings': [reason], 'checks': [], 'sources': [], 'series': []}


class CompanyAnalysis:
    def __init__(self, database, root, key_provider, *, inline=False):
        self.store = MarketStore(database)
        self.root = Path(root)
        self.key_provider = key_provider
        self.inline = inline
        self.executor = None
        self.lock = Lock()
        registry = json.loads((self.root / 'static/data/companies/index.json').read_text(encoding='utf-8-sig'))
        self.samples = {c['company_id']: c for c in registry['companies']}
        self.trade_collector = None
        self.trade_diagnoser = None
        self.reference_collector = None
        self.fx_collector = None
        self.law_collector = None

    def upload(self, user_id, data, filename):
        try:
            company = parse_company(data, filename)
        except ValueError as exc:
            raise MarketError('invalid_workbook', str(exc)) from None
        summary = {**company['source'], 'data_class': company['data_class'], 'size': len(data),
                   'row_count': company['row_count'], 'issues': company['issues'],
                   'missing_sheets': company['missing_sheets']}
        source_id = self.store.add_source(user_id, company['source']['name'], data, summary)
        return {'company_id': 'upload:' + source_id, 'name': company['source']['name'], 'summary': summary}

    def file_identity(self, user_id, company_id):
        if not isinstance(company_id, str) or not company_id.startswith('upload:') or len(company_id) > 50:
            return None
        try:
            row = self.store.source(user_id, company_id[7:])
        except MarketError:
            return None
        summary = json.loads(row['summary_json'])
        return {'company_id': company_id, 'file_name': row['name'], 'size': summary['size'], 'sample': False}

    def _company(self, user_id, company_id):
        if not isinstance(company_id, str):
            raise MarketError('invalid_company', '분석할 기업 파일을 선택해 주세요.')
        if company_id.startswith('upload:'):
            row = self.store.source(user_id, company_id[7:])
            data, name, source_id = bytes(row['content']), row['name'], row['id']
        else:
            entry = self.samples.get(company_id)
            if not entry:
                raise MarketError('source_not_found', '사용할 수 있는 기업 파일이 없습니다.', 404)
            name = entry['file_name']
            data = (self.root / 'static/samples' / name).read_bytes()
            uploaded = self.upload(user_id, data, name)
            source_id = uploaded['company_id'][7:]
        company = parse_company(data, name)
        company['source']['id'] = 'company:' + source_id
        company['source']['retrieved_at'] = timestamp()
        return company, source_id

    def submit(self, user_id, payload):
        try:
            inputs = validate_conditions(payload)
        except ValueError as exc:
            raise MarketError('invalid_input', str(exc)) from None
        company, source_id = self._company(user_id, payload.get('company_id'))
        company = bind_simple_conditions(company, inputs)
        matching = [p for p in company['sheets']['제품정보']
                    if normalized_hs(p.get('HS코드')).startswith(inputs['hs6'])]
        if len(inputs['hs_raw']) > 6:
            matching = [p for p in matching
                        if normalized_hs(p.get('HS코드')) == inputs['hs_raw']]
        if not matching:
            raise MarketError('product_scope_missing', '선택한 HS6에 해당하는 제품정보가 없습니다. 파일의 HS코드와 입력 조건을 확인해 주세요.')
        if any(str(p.get('HS버전', '')).replace(' ', '').upper() != 'HS2022' for p in matching):
            raise MarketError('hs_edition_unverified', '선택 품목의 HS버전을 HS2022로 확인해야 합니다. 임의로 분류판을 추정하지 않습니다.')
        # Keep enterprise joins at the selected product scope. Public trade remains HS6.
        for product in matching:
            if company['source'].get('workbook_format') != SIMPLE_VERSION:
                product['HS코드원문'] = product.get('HS코드')
                product['HS버전원문'] = product.get('HS버전')
            product['HS코드'] = normalized_hs(product.get('HS코드'))
            product['HS버전'] = 'HS2022'
        company['sheets']['제품정보'] = matching
        inputs.update(company_id=payload['company_id'], file_name=company['source']['name'],
                      source_id=source_id, analysis_as_of=timestamp(), policy=policy_snapshot())
        assessment_id = self.store.create(user_id, inputs, source_id)
        if self.inline:
            self.run(user_id, assessment_id, inputs, company)
        else:
            try:
                with self.lock:
                    if self.executor is None:
                        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='enterprise-analysis')
                    self.executor.submit(self.run, user_id, assessment_id, inputs, company)
            except RuntimeError:
                self.store.update(user_id, assessment_id, 'FAILED', '분석 작업을 시작하지 못했습니다.', error='worker_unavailable')
        return self.store.get(user_id, assessment_id)

    def _trade(self, inputs, progress):
        from .analysis_market_price import collect_trade
        cache_key = '|'.join([inputs['hs6'], inputs['hs_edition'], inputs['country'], inputs['as_of'], 'company-trade-v5-exact-observations'])
        with self.store.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS analysis_trade_cache (key TEXT PRIMARY KEY, created REAL NOT NULL, result_json TEXT NOT NULL)')
            cached = db.execute('SELECT result_json FROM analysis_trade_cache WHERE key=? AND created>?',
                                (cache_key, time.time() - 86400)).fetchone()
        if cached:
            progress('같은 품목·국가의 저장된 공식통계 근거를 확인합니다.')
            return json.loads(cached['result_json'])
        result = (self.trade_collector or collect_trade)(inputs, self.key_provider(), progress=progress)
        sources = result.get('sources', [])
        # A successful response can have unpublished months. Preserve those gaps
        # for the daily snapshot, but leave failed or invalid batches retryable.
        api_sources = [s for s in sources if s.get('provider') in ('UN Comtrade', '관세청', '검증 응답')]
        observations = result.get('monthly_imports', []) + result.get('kcs_exports', []) + result.get('annual_imports', [])
        valid_observations = all(o.get('status') in ('OBSERVED', 'OBSERVED_ZERO', 'MISSING', 'INCOMPATIBLE_SCOPE')
                                 for o in observations)
        if (api_sources and valid_observations
                and all(s.get('status') in ('OBSERVED', 'OBSERVED_ZERO', 'RECEIVED', 'OK', 'MISSING', 'PARTIAL')
                        for s in api_sources)):
            with self.store.connection() as db:
                db.execute('INSERT OR REPLACE INTO analysis_trade_cache VALUES(?,?,?)',
                           (cache_key, time.time(), json.dumps(result, ensure_ascii=False, allow_nan=False)))
        return result

    def _public_data(self, cache_key, collect):
        """Cache public-only supplements. Never pass company/FX results here."""
        with self.store.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS analysis_public_cache (key TEXT PRIMARY KEY, created REAL NOT NULL, result_json TEXT NOT NULL)')
            cached = db.execute('SELECT result_json FROM analysis_public_cache WHERE key=? AND created>?',
                                (cache_key, time.time() - 86400)).fetchone()
        if cached:
            return json.loads(cached['result_json'])
        result = collect()
        serialized = json.dumps(result, ensure_ascii=False, allow_nan=False)
        sources = result.get('sources', [])
        observations_valid = all(o.get('status') in ('OBSERVED', 'OBSERVED_ZERO', 'MISSING', 'INCOMPATIBLE_SCOPE')
                                 for o in result.get('monthly_exports', []))
        diagnostics_valid = all(d.get('diagnostic_status') in ('DATASET_NOT_LISTED', 'DATASET_LISTED_NO_OBSERVATION')
                                for d in result.get('diagnostics', []))
        response_valid = result.get('status') not in ('FETCH_ERROR', 'INVALID_SCOPE', 'INVALID_DATA', 'OUT_OF_PERIOD')
        if sources and response_valid and observations_valid and diagnostics_valid and all(
                s.get('status') in ('OBSERVED', 'OBSERVED_ZERO', 'RECEIVED', 'OK', 'MISSING', 'PARTIAL')
                for s in sources):
            with self.store.connection() as db:
                db.execute('INSERT OR REPLACE INTO analysis_public_cache VALUES(?,?,?)',
                           (cache_key, time.time(), serialized))
        return result

    def _diagnostics(self, trade, inputs):
        from .analysis_trade_metadata import diagnose_missing_months
        latest = month_offset(inputs['as_of'][:7], -1)
        # Covers all four allowed 36-month windows without inspecting the older
        # HS edition boundary. The adapter bounds its own diagnostic request set.
        required = [month_offset(latest, i) for i in range(-38, 1)]
        missing = [row['period'] for row in trade.get('monthly_imports', [])
                   if row.get('status') == 'MISSING' and row.get('period') in required]
        if not missing:
            return {'diagnostics': [], 'sources': [], 'checked_periods': [], 'skipped_periods': []}
        marks = [(s.get('id'), s.get('sha256'), s.get('status')) for s in trade.get('sources', [])]
        from hashlib import sha256
        version = sha256(json.dumps(marks, sort_keys=True).encode()).hexdigest()
        cache_key = '|'.join(['trade-diagnostics-v1', inputs['country'], inputs['hs6'], inputs['hs_edition'], inputs['as_of'], version])
        return self._public_data(cache_key, lambda: (self.trade_diagnoser or diagnose_missing_months)(
            trade, inputs, self.key_provider(), required_periods=required))

    def _reference(self, inputs, progress):
        from .analysis_trade_reference import collect_trade_reference
        cache_key = '|'.join(['kcs-world-reference-v1', inputs['hs6'], inputs['hs_edition'], inputs['as_of']])
        return self._public_data(cache_key, lambda: (self.reference_collector or collect_trade_reference)(
            inputs, self.key_provider(), progress=progress))

    def _law(self, inputs, progress):
        from .analysis_regulation_law import collect_regulation_law
        # Public current-version lookup, independent of HS/company/country.
        # Include retrieval day so an as_of rerun is not a historical-law claim.
        cache_key = '|'.join(['current-law-v1', inputs['as_of'], timestamp()[:10]])
        return self._public_data(cache_key, lambda: (self.law_collector or collect_regulation_law)(
            {'as_of': inputs['as_of']}, self.key_provider(), progress=progress))

    def run(self, user_id, assessment_id, inputs, company):
        def progress(message):
            if not self.store.update(user_id, assessment_id, 'RUNNING', message):
                raise InterruptedError('assessment_no_longer_active')
        try:
            from .analysis_market_price import evaluate_price, rebase_market
            from .analysis_risk_logistics import evaluate_regulation, evaluate_logistics, evaluate_stability
            progress('기업 파일과 선택 품목의 연결을 확인합니다.')
            factors = []
            trades = {}
            for country in CANDIDATES:
                scoped = {**inputs, 'country': country, 'country_name': COUNTRY_NAMES[country]}
                progress(f'{COUNTRY_NAMES[country]} 비교 자료를 확인합니다. ({len(trades) + 1}/{len(CANDIDATES)})')
                try:
                    trades[country] = self._trade(scoped, progress)
                except InterruptedError:
                    raise
                except Exception:
                    trades[country] = {'factor': unavailable_factor('market', '시장성', '외부 무역통계를 확인하지 못했습니다.'),
                                      'monthly_imports': [], 'annual_imports': [], 'kcs_exports': [], 'sources': []}
                try:
                    diagnosis = self._diagnostics(trades[country], scoped)
                except Exception:
                    diagnosis = {'diagnostics': [], 'sources': [], 'checked_periods': [], 'skipped_periods': [],
                                 'reason': '자료 제공 현황의 추가 조회에 실패했습니다. 수입 관측값은 변경하지 않습니다.'}
                trades[country]['missing_diagnostics'] = diagnosis
                trades[country]['sources'].extend(diagnosis.get('sources', []))
                factor = trades[country]['factor']
                factor.setdefault('checks', []).extend(
                    {'label': f'{d["period"]} 수입 자료 확인', 'status': d['diagnostic_status'], 'detail': d['reason']}
                    for d in diagnosis.get('diagnostics', []))
                if diagnosis.get('reason'):
                    factor.setdefault('warnings', []).append(diagnosis['reason'])
                if diagnosis.get('warning'):
                    factor.setdefault('warnings', []).append(diagnosis['warning'])
                by_period = {d['period']: d for d in diagnosis.get('diagnostics', [])}
                for observation in trades[country].get('monthly_imports', []):
                    diagnostic = by_period.get(observation.get('period'))
                    if diagnostic and observation.get('status') == 'MISSING':
                        observation['reason'] = diagnostic['reason']
                        observation['evidence'] = observation.get('evidence', []) + diagnostic.get('evidence', [])
            progress('5개 후보국의 공통 기간과 제외 사유를 확인합니다.')
            try:
                comparison = select_comparisons(trades, inputs)
            except Exception:
                comparison = unavailable_comparisons(inputs, trades)
            trade = trades[inputs['country']]
            market_window = country_window(comparison['market'], inputs['country'])
            if market_window['end_month'] and market_window['annual_year']:
                trade = rebase_market(trade, inputs, market_window['annual_year'], market_window['end_month'])
            trade['factor']['comparison_window'] = market_window
            if not market_window['eligible']:
                trade['factor'].setdefault('warnings', []).append('국가 비교 대상에서 제외했습니다: ' + market_window['reason'])
            for country in CANDIDATES:
                scoped = {**inputs, 'country': country, 'country_name': COUNTRY_NAMES[country]}
                public_trade = {**trades[country], 'stability_window': country_window(comparison['stability'], country)}
                # Only public market stability metrics enter cross-country rows.
                # Company currencies and shipment inputs remain in the selected tab.
                row = next(r for r in comparison['stability']['countries'] if r['country'] == country)
                try:
                    factor = evaluate_stability({'sheets': {}, 'source': {}}, scoped, public_trade, self.root)
                    row['metrics'] = [m for m in factor['metrics'] if m['id'] in ('market_months', 'market_cv_36m',
                                      'market_drop_pairs', 'market_drop_count', 'market_drop_frequency')]
                except Exception:
                    row.update(eligible=False, metrics=[], reason='이 국가의 안정성 비교 지표 처리 중 오류가 있어 비교 대상에서 제외했습니다.')
            refresh_comparison('stability', comparison['stability'], inputs, trades)
            trade['stability_window'] = country_window(comparison['stability'], inputs['country'])
            progress('한국 전체 수출 기준단가의 자료 범위를 확인합니다.')
            try:
                trade['world_reference'] = self._reference(inputs, progress)
            except InterruptedError:
                raise
            except Exception:
                trade['world_reference'] = {'monthly_exports': [], 'sources': [], 'status': 'FETCH_ERROR',
                                            'warnings': ['한국 전체 수출 기준자료를 확인하지 못했습니다.']}
            from .analysis_fx import collect_fx
            progress('기업 거래의 결제통화와 일별 환율을 확인합니다.')
            try:
                fx = (self.fx_collector or collect_fx)(company, inputs, self.key_provider(), progress=progress)
            except InterruptedError:
                raise
            except Exception:
                fx = {'metrics': [], 'sources': [], 'warnings': ['결제통화 환율 자료를 확인하지 못했습니다.'],
                      'checks': [], 'series': [], 'calendar_status': 'UNVERIFIED'}
            trade['fx'] = fx
            progress('공식 현행 고시의 판본과 본문을 확인합니다.')
            try:
                law_snapshot = self._law(inputs, progress)
            except InterruptedError:
                raise
            except Exception:
                law_snapshot = {'status': 'FETCH_ERROR', 'law': None, 'sources': [], 'checks': [],
                                'warnings': ['공식 고시 원문을 조회하지 못했습니다. 보유 원문의 효력을 추정하지 않습니다.']}
            calls = [
                ('regulation', '규제', lambda: evaluate_regulation(company, inputs, self.root, law_snapshot=law_snapshot)),
                ('market', '시장성', lambda: trade['factor']),
                ('price', '가격', lambda: evaluate_price(company, inputs, trade, self.root, self.key_provider())),
                ('logistics', '물류', lambda: evaluate_logistics(company, inputs, self.root)),
                ('stability', '안정성', lambda: evaluate_stability(company, inputs, trade, self.root)),
            ]
            for key, label, evaluate in calls:
                progress(f'{label} 지표와 근거를 확인합니다.')
                try:
                    factor = evaluate()
                    factor.update(key=key, label=label, score=None)
                    json.dumps(factor, allow_nan=False)
                except Exception:
                    factor = unavailable_factor(key, label, '자료 처리 중 오류가 발생하여 이 영역은 보류합니다. 재분석으로 확인해 주세요.')
                factors.append(factor)
            progress('승인된 시장성·안정성 상대 참고지수와 산정 근거를 확인합니다.')
            apply_reference_scores(factors, comparison, inputs, trades)
            from .analysis_suitability import evaluate_suitability, policy_snapshot as suitability_policy
            progress('기업 조건과 외부 원지표의 참고 적합도·근거 반영률을 계산합니다.')
            overall = evaluate_suitability(company, inputs, factors, fx=fx)
            for factor in factors:
                reference = next((d for d in overall['domains'] if d['key'] == factor['key']), None)
                if reference:
                    factor['reference_assessment'] = deepcopy(reference)
            policy = deepcopy(inputs['policy'])
            policy['suitability'] = suitability_policy()
            sources = {company['source']['id']: company['source']}
            for source in [s for t in trades.values() for s in t.get('sources', [])] + [s for f in factors for s in f.get('sources', [])]:
                sources[source['id']] = source
            result = {'assessment_id': assessment_id, 'company_id': inputs['company_id'], 'company_name': inputs['company'],
                      'file_name': inputs['file_name'], 'as_of': inputs['as_of'],
                      'country': inputs['country_name'], 'country_iso2': inputs['country'],
                      'hs': inputs['hs_raw'], 'hs6': inputs['hs6'], 'hs_edition': inputs['hs_edition'],
                      'data_class': company['data_class'], 'analysis_as_of': inputs['analysis_as_of'],
                      'overall': overall,
                      'policy': policy, 'comparison': comparison,
                      'data_gaps': {country: trades[country].get('missing_diagnostics', {}) for country in CANDIDATES},
                      'factors': factors, 'sources': list(sources.values()),
                      'validation': {k: company[k] for k in ('row_count', 'accepted_row_count', 'issues', 'missing_sheets')},
                      'method_version': 'enterprise-evidence-v6-reference-suitability',
                      'report_url': f'/analysis/assessments/{assessment_id}/report',
                      'warnings': ['조회 시점의 자료로 분석했습니다. 과거 당시 정보만 사용한 재현 평가가 아닙니다.',
                                   '국제 무역통계는 상위 HS6 범위입니다. 개별 제품·모델의 정확한 시장규모나 확보 가능한 매출이 아닙니다.',
                                   '기업 입력과 외부 통계는 증거 범위가 다릅니다. 자료 없음은 수출 부적합이나 수출금지를 뜻하지 않습니다.']}
            self.store.update(user_id, assessment_id, 'COMPLETED', '다섯 영역의 지표와 근거를 확인했습니다.', result=result)
        except InterruptedError:
            return
        except Exception:
            self.store.update(user_id, assessment_id, 'FAILED', '분석을 완료하지 못했습니다. 파일과 자료 연결 상태를 확인해 주세요.', error='assessment_failed')


def public_result(item):
    result = item.get('result')
    if result:
        for source in result.get('sources', []):
            source.pop('raw', None)
        for factor in result.get('factors', []):
            for source in factor.get('sources', []):
                source.pop('raw', None)
        for diagnosis in result.get('data_gaps', {}).values():
            for source in diagnosis.get('sources', []):
                source.pop('raw', None)
    return item
