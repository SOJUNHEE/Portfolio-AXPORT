# -*- coding: utf-8 -*-
"""(junhee) 2026-09-27 sanghyeob 엔진 결과 → junhee 대시보드가 읽는 handoff-v1 문서.

화면(junhee-dashboard.js)을 바꾸지 않고 엔진 결과를 보여 주기 위한 변환기. 값을 새로 만들지 않는다:
- 엔진 지표(metric)를 같은 뜻의 junhee 항목 키로 옮긴다(비율은 % 로만 환산). 대응 키가 없으면 엔진 id 그대로 둔다.
- 엔진이 만들지 않는 junhee 항목(화물편·선박 등)은 넣지 않는다 → 화면 규칙대로 '자료 부족'.
- 점수는 엔진의 참고 적합도(suitability-reference-v1)와 영역별 점수를 그대로 쓴다. 근거 반영률 0% 영역은 '자료 부족'.
  엔진은 미평가 항목에 정책 기준 50점을 쓰므로 그 사실을 문구(note·highlights)에 그대로 밝힌다.
"""
from datetime import date

COUNTRY_KO = {'US': '미국', 'CN': '중국', 'JP': '일본', 'DE': '독일', 'VN': '베트남'}
OK = {'OBSERVED', 'OBSERVED_ZERO', 'REFERENCE_ONLY', 'REFERENCE_PROVISIONAL', 'PROVISIONAL', 'COMPANY_REPORTED',
      'COMPANY_QUOTE', 'CALCULATED_REFERENCE', 'REVIEW_REQUIRED', 'PARTIAL_SAMPLE', 'PARTIAL', 'IDENTITY'}
BLOCKED_FETCH = {'FETCH_ERROR', 'KEY_NOT_CONFIGURED'}
UNVERIFIED = {'NOT_VERIFIED', 'UNVERIFIED', 'DECLARED_UNVERIFIED'}
DOMAIN_TO_AREA = {'market': 'market', 'price': 'price', 'logistics': 'logistics', 'stability': 'stability'}
STATUS_KO = {'OBSERVED': '관측', 'OBSERVED_ZERO': '관측(0)', 'ASSUMED': '정책 기준 50점', 'COMPANY_REPORTED': '기업 기재'}

# 엔진 metric id(접두어) → (junhee 항목 키, 비율→% 환산 여부)
KEY_MAP = {
    'regulation': {'hsk_candidates': ('export_control_candidates', False), 'kotra_candidates': ('import_regulation_records', False),
                   'csl_candidates': ('csl_search', False)},
    'market': {'import_value': ('destination_imports', False), 'korea_exports': ('korea_exports_to_destination', False),
               'import_ytd_yoy': ('growth_yoy', True), 'import_3m_yoy': ('growth_3m_yoy', True), 'import_cagr3': ('cagr_3y', True),
               'industry_world_sales': ('wsts', False)},
    'price': {'korea_export_unit_value': ('trade_unit_price', False), 'korea_world_export_unit_value': ('baseline_unit_price', False),
              'tariff_reference': ('tariff_reference', True), 'fx_reference_rate': ('fx_reference', False),
              'electronics_export_price_index': ('price_index', False), 'company_unit_price': ('company_unit_price', False)},
    'logistics': {'observed_on_time_rate': ('delivery_ontime', False), 'door_to_door_days': ('lead_time', False),
                  'sea_export_reference': ('freight_reference', False)},
    'stability': {'market_cv_36m': ('cv', True), 'market_drop_count': ('sharp_drops', False), 'fx_volatility_60d': ('fx_volatility', False)},
}


def status_ko(status):
    if status in OK:
        return '확인됨'
    if status in BLOCKED_FETCH:
        return '검색 불가'
    if status in UNVERIFIED:
        return '미확인'
    return '자료 부족'


def _pct(value):
    return round(value * 100, 2) if isinstance(value, (int, float)) and not isinstance(value, bool) else value


def _source_names(metric, sources):
    ids = []
    for ev in metric.get('evidence') or []:
        if isinstance(ev, dict) and ev.get('source_id') and ev['source_id'] not in ids:
            ids.append(ev['source_id'])
    names = []
    for sid in ids[:3]:
        s = sources.get(sid) or {}
        label = s.get('name') or s.get('provider') or sid
        if s.get('provider') and s.get('name') and s['provider'] not in label:
            label = f"{s['provider']} · {s['name']}"
        if label not in names:
            names.append(label)
    return ' · '.join(names) or None


# 통화별로 여러 개 나오는 지표는 junhee 항목(원/USD 기준)에 USD 것을 쓴다
PREFER_SUFFIX = {'fx_reference_rate': 'USD', 'fx_volatility_60d': 'USD'}
PREFIX_KEYS = ('sea_export_reference',)  # 노선별로 id 뒤에 이름이 붙는 지표


def _target(mapping, mid):
    base, _, suffix = mid.partition(':')
    if base in mapping:
        want = PREFER_SUFFIX.get(base)
        return mapping[base] if not want or suffix == want else None
    prefix = next((k for k in PREFIX_KEYS if k in mapping and base.startswith(k)), None)
    return mapping[prefix] if prefix else None


def _item(metric, key, to_pct, sources, as_of):
    status = metric.get('status')
    value = metric.get('value')
    unit = metric.get('unit')
    if to_pct and unit in ('ratio', '비율'):
        value, unit = _pct(value), '%'
    note = metric.get('reason')
    if status not in ('OBSERVED', 'OBSERVED_ZERO') and status:
        note = f"[엔진 상태 {status}] " + (note or '')
    return {'key': key, 'label': metric.get('label') or key, 'status': status_ko(status),
            'value': value if status_ko(status) == '확인됨' else None, 'unit': unit, 'period': metric.get('period'),
            'as_of': as_of, 'source': _source_names(metric, sources), 'basis': metric.get('formula') or None,
            'note': note or None, 'engine_status': status, 'engine_id': metric.get('id')}


def _area_items(factor, area, sources, as_of, company_products, hs6):
    items, used = [], set()
    mapping = KEY_MAP.get(area, {})
    for metric in factor.get('metrics') or []:
        mid = str(metric.get('id') or '')
        target = _target(mapping, mid)
        if target and target[0] not in used:
            key, to_pct = target
            used.add(key)
        else:
            key, to_pct = mid, False  # 대응 키가 없으면 엔진 id 그대로 ('항목 전체 보기' 에 표시)
        items.append(_item(metric, key, to_pct, sources, as_of))
    by = {i['key']: i for i in items}
    # 규제: 통제번호 후보 행(junhee 형식)
    if area == 'regulation' and 'export_control_candidates' in by:
        rows = []
        names = {p.get('HS코드', ''): p.get('모델명') or p.get('제품명') or '' for p in company_products}
        for c in factor.get('hsk_candidates') or []:
            if not isinstance(c, dict):
                continue
            product = next((n for h, n in names.items() if h and str(c.get('hsk', '')).startswith(str(h)[:6])), '') or '선택 품목'
            rows.append({'status': '확인됨', 'control_numbers': list(c.get('control_codes') or []), 'hsk_name': c.get('product_name'),
                         'product': product, 'input_hsk': c.get('hsk'), 'match_level': c.get('match_level')})
        by['export_control_candidates']['rows'] = rows
        by['export_control_candidates']['unit'] = '후보 HSK 수 (통제번호 ' + str(by['export_control_candidates'].get('value')) + '개)'
        by['export_control_candidates']['value'] = len(rows)
        for key, field in (('import_regulation_records', 'regulation_candidates'), ('csl_search', 'party_candidates')):
            if key in by:
                by[key]['rows'] = [r if isinstance(r, dict) else {'item': str(r)} for r in (factor.get(field) or [])]
    # 관세: junhee 형식 {hs6: %} + 행
    if area == 'price' and 'tariff_reference' in by and by['tariff_reference']['value'] is not None:
        pct = by['tariff_reference']['value']
        by['tariff_reference'].update(value={hs6: pct}, unit='% (HS6 최신 조치)',
                                      rows=[{'hs6': hs6, 'year_dt': by['tariff_reference'].get('period') or '', 'best_avlbl_pct': pct}])
    # 안정성: 월별 수입 시계열 → destination_monthly_imports (관측된 달만, 빈 달은 null)
    if area == 'stability':
        series = [s for s in factor.get('series') or [] if isinstance(s, dict) and s.get('period') and s.get('unit') == 'USD']
        if series:
            rows, prev = [], None
            for s in series:
                v = s.get('value') if s.get('status') in ('OBSERVED', 'OBSERVED_ZERO') else None
                mom = round((v / prev - 1) * 100, 1) if v is not None and prev not in (None, 0) else None
                rows.append({'month': s['period'], 'value_usd': v, 'mom_pct': mom})
                prev = v
            observed = [r for r in rows if r['value_usd'] is not None]
            items.insert(0, {'key': 'destination_monthly_imports', 'label': '목적국 월별 수입금액·전월비', 'status': '확인됨' if observed else '자료 부족',
                             'value': observed[-1]['value_usd'] if observed else None, 'unit': 'USD (최근 월)',
                             'period': f"{rows[0]['month']}~{rows[-1]['month']}", 'as_of': observed[-1]['month'] if observed else None,
                             'source': 'UN Comtrade (엔진 수집)', 'basis': '대세계 월간 수입액 · 누락 월을 0으로 채우지 않음', 'note': None,
                             'rows': rows, 'missing_months': [r['month'] for r in rows if r['value_usd'] is None]})
    return items


def _factor_note(domain):
    parts = []
    for c in domain.get('components') or []:
        parts.append(f"{c.get('label')} {c.get('score'):.0f}점({STATUS_KO.get(c.get('status'), c.get('status'))})"
                     if isinstance(c.get('score'), (int, float)) else f"{c.get('label')} ({c.get('status')})")
    return ' · '.join(parts)


def _shift(month, n):
    k = int(month[:4]) * 12 + int(month[5:7]) - 1 + n
    return f"{k // 12}-{k % 12 + 1:02d}"


def _period(result, as_of_month):
    """자료기간: 엔진이 확정한 비교기간(안정성 36개월 → 시장성 12개월). 없으면 최근 완료 월 하나만(기간을 지어내지 않음)."""
    factors = {f.get('key'): f for f in result.get('factors') or []}
    sw = (factors.get('stability') or {}).get('comparison_window') or {}
    mw = (factors.get('market') or {}).get('comparison_window') or {}
    if sw.get('end_month'):
        return _shift(sw['end_month'], -35), sw['end_month']
    if mw.get('end_month'):
        return _shift(mw['end_month'], -11), mw['end_month']
    latest = ((result.get('comparison') or {}).get('market') or {}).get('latest_completed_month') or as_of_month
    return latest, latest


# 간편입력 v2 빈 칸의 점수 영향 (엔진 suitability-reference-v1 기준)
MISSING_IMPACT = {
    'unit_cost': (True, '가격: 희망가격의 제품원가 차감 여지를 계산하지 못해 정책 기준 50점'),
    'cost_currency': (True, '가격: 원가 통화가 없어 환산하지 못함 → 정책 기준 50점'),
    'desired_price': (True, '가격: 희망가격의 제품원가 차감 여지를 계산하지 못해 정책 기준 50점'),
    'price_currency': (True, '가격: 판매가 통화가 없어 환산하지 못함 → 정책 기준 50점'),
    'desired_quantity': (True, '물류: 30일 희망물량 충족을 계산하지 못해 정책 기준 50점'),
    'supply_quantity_30d': (True, '물류: 30일 희망물량 충족을 계산하지 못해 정책 기준 50점'),
    'preparation_days': (True, '물류: 출고 준비기간을 평가하지 못해 정책 기준 50점'),
    'unit': (True, '가격·수량의 공통 단위가 없음 (가격·물류 계산에 필요)'),
    'manufacturing_country': (False, '참고 정보 (점수 영향 없음)'),
    'trade_terms': (False, '참고 정보 (점수 영향 없음)'),
    'datasheet_reference': (False, '규제·서류 검토 참고 (점수 영향 없음)'),
    'certification_statement': (False, '규제·서류 검토 참고 (점수 영향 없음)'),
    'additional_notes': (False, '참고 정보 (점수 영향 없음)'),
}


def missing_inputs(company):
    """업로드 기업 파일의 결측: 간편입력은 빈 칸(셀 위치·점수 영향), 상세양식은 빠진 시트. 값을 채우지 않고 목록만 만든다."""
    source = (company or {}).get('source') or {}
    fields = []
    for fid, f in (source.get('raw_fields') or {}).items():
        if not isinstance(f, dict) or f.get('value') not in (None, ''):
            continue
        scored, impact = MISSING_IMPACT.get(fid, (False, '참고 정보'))
        fields.append({'id': fid, 'label': f.get('label') or fid, 'cell': f"{f.get('sheet') or ''}!{f.get('cell') or ''}".strip('!'),
                       'scored': scored, 'impact': impact})
    fields.sort(key=lambda x: (not x['scored'], x['cell']))
    simple = source.get('workbook_format') == 'company-simple-v2'  # 간편입력은 시트 하나라 상세양식 '빠진 시트'는 결측이 아님
    return {'format': source.get('workbook_format'), 'fields': fields,
            'missing_sheets': [] if simple else list((company or {}).get('missing_sheets') or []),
            'issues': [str(i) for i in (company or {}).get('issues') or []][:50]}


def _text(value):
    if isinstance(value, dict):
        return value.get('message') or value.get('detail') or value.get('reason') or ''
    return str(value or '')


def _month_series(series):
    """엔진 월간 관측(period·value·status) → [{m, v, st}] (관측값만 숫자, 나머지 null)."""
    out = []
    for s in series or []:
        if not isinstance(s, dict) or not isinstance(s.get('period'), str) or len(s['period']) != 7:
            continue
        v = s.get('value') if s.get('status') in ('OBSERVED', 'OBSERVED_ZERO') and isinstance(s.get('value'), (int, float)) else None
        out.append({'m': s['period'], 'v': v, 'st': s.get('status')})
    return out


def _detail(result):
    """세부 탭(상협 방식): 영역별 적합도 항목 · 차트 시계열 · 확인 항목 · 유의사항 · 출처. 값은 엔진 결과 그대로."""
    factors = {f.get('key'): f for f in result.get('factors') or []}
    domains = {d.get('key'): d for d in (result.get('overall') or {}).get('domains') or []}
    out = {}
    for key in ('regulation', 'market', 'price', 'logistics', 'stability'):
        f = factors.get(key) or {}
        d = domains.get(key) or {}
        comps = [{'label': c.get('label') or c.get('id'), 'score': c.get('score'), 'weight': c.get('weight'), 'contribution': c.get('contribution'),
                  'status': c.get('status'), 'value': c.get('value'), 'unit': c.get('unit'), 'period': c.get('period'),
                  'formula': c.get('formula'), 'reason': c.get('reason')} for c in d.get('components') or []]
        srcs = []
        for s in f.get('sources') or []:
            if isinstance(s, dict):
                srcs.append({'name': s.get('name') or s.get('id'), 'provider': s.get('provider'), 'status': s.get('status'),
                             'retrieved_at': (s.get('retrieved_at') or '')[:10], 'period': s.get('observed_period')})
        item = {'label': d.get('label'), 'score': d.get('score'), 'coverage_pct': d.get('coverage_pct'), 'raw_score': d.get('raw_score'),
                'raw_max': d.get('raw_max'), 'components': comps, 'state': f.get('state'), 'note': f.get('note'),
                'checks': [{'label': c.get('label'), 'status': c.get('status'), 'detail': _text(c.get('detail'))} for c in f.get('checks') or [] if isinstance(c, dict)],
                'warnings': [_text(w) for w in f.get('warnings') or []][:12], 'sources': srcs[:30], 'charts': {}}
        if key == 'market':
            item['charts']['imports'] = _month_series(f.get('series'))
            item['charts']['growth'] = [{'label': m.get('label'), 'v': round(m['value'] * 100, 1) if isinstance(m.get('value'), (int, float)) and m.get('status') in ('OBSERVED', 'OBSERVED_ZERO') else None,
                                         'st': m.get('status'), 'period': m.get('period')}
                                        for m in f.get('metrics') or [] if m.get('id') in ('import_ytd_yoy', 'import_3m_yoy', 'import_cagr3')]
        elif key == 'stability':
            item['charts']['imports'] = _month_series(f.get('series'))
            item['charts']['changes'] = [{'m': c.get('period'), 'v': round(c['change_pct'], 1) if isinstance(c.get('change_pct'), (int, float)) else None,
                                          'drop': bool(c.get('drop_at_least_20pct'))} for c in f.get('monthly_changes') or [] if isinstance(c, dict)]
            fx = next((x for x in f.get('fx_series') or [] if isinstance(x, dict) and x.get('currency') == 'USD'), None)
            if fx:
                item['charts']['fx'] = [{'d': o.get('observation_date') or o.get('period'), 'v': o.get('value')}
                                        for o in fx.get('observations') or [] if isinstance(o, dict) and isinstance(o.get('value'), (int, float))]
        elif key == 'logistics':
            routes = {}
            for s in f.get('series') or []:
                if isinstance(s, dict) and s.get('route') and isinstance(s.get('value'), (int, float)):
                    routes.setdefault(s['route'], []).append({'m': s.get('period'), 'v': s['value'], 'unit': s.get('unit')})
            item['charts']['freight'] = routes
        elif key == 'regulation':
            item['charts']['counts'] = [{'label': m.get('label'), 'v': m.get('value') if isinstance(m.get('value'), (int, float)) else None, 'st': m.get('status'), 'unit': m.get('unit')}
                                        for m in f.get('metrics') or [] if m.get('id') in ('hsk_candidates', 'kotra_candidates', 'csl_candidates', 'declared_documents')]
            item['candidates'] = [{'hsk': c.get('hsk'), 'name': c.get('product_name'), 'codes': list(c.get('control_codes') or [])[:40], 'level': c.get('match_level')}
                                  for c in f.get('hsk_candidates') or [] if isinstance(c, dict)][:40]
        out[key] = item
    # 가격: 환율 추이는 안정성 요인의 원/달러 일별 관측을 같이 쓴다
    out['price']['charts']['fx'] = out['stability']['charts'].get('fx', [])
    return out


def to_handoff(result, company, inputs):
    """엔진 결과(result) · 파싱한 기업 파일(company) · 입력(inputs) → handoff-v1 문서."""
    iso2 = result.get('country_iso2') or inputs.get('country')
    country = COUNTRY_KO.get(iso2, result.get('country') or iso2)
    hs6 = result.get('hs6') or inputs.get('hs6')
    as_of = (result.get('as_of') or date.today().isoformat())[:10]
    month = as_of[:7]
    start, month = _period(result, month)
    sources = {s.get('id'): s for s in result.get('sources') or [] if isinstance(s, dict)}
    for f in result.get('factors') or []:
        for s in f.get('sources') or []:
            if isinstance(s, dict) and s.get('id'):
                sources.setdefault(s['id'], s)
    products_raw = (company.get('sheets') or {}).get('제품정보') or []
    products = [{'id': p.get('제품ID') or f'P{i + 1}', 'name': p.get('모델명') or p.get('제품명') or f'제품 {i + 1}',
                 'family': p.get('제품군'), 'input_hsk': p.get('입력HSK') or p.get('HS코드원문') or p.get('HS코드'),
                 'analysis_hs6': str(p.get('HS코드') or hs6)[:6], 'hs_status': '확인됨', 'note': None,
                 'has_control_candidates': True} for i, p in enumerate(products_raw)]
    factors = {f.get('key'): f for f in result.get('factors') or []}
    overall = result.get('overall') or {}
    domains = {d.get('key'): d for d in overall.get('domains') or []}
    per_country_items = {area: _area_items(factors.get(area, {}), area, sources, as_of, products_raw, hs6)
                         for area in ('regulation', 'market', 'price', 'logistics', 'stability')}
    reg_status = overall.get('regulation_status') or 'REVIEW_REQUIRED'
    reg_factor = factors.get('regulation') or {}
    reg_note = ' · '.join(f"{m.get('label')} " + (f"{m.get('value')}{m.get('unit') or ''}" if m.get('value') is not None else '미확인')
                          for m in (reg_factor.get('metrics') or []) if m.get('id') in ('hsk_candidates', 'kotra_candidates', 'csl_candidates'))
    score_factors = [{'key': 'regulation', 'label_ko': '규제 관문', 'weight': None, 'score': None, 'state': 'insufficient',
                      'delta': None, 'series': [None], 'series_months': [month], 'gate': True, 'needs_review': True,
                      'note': f'점수 대신 관문으로 봅니다 ({reg_status}). {reg_note}', 'inputs': {'engine_gate': reg_status}}]
    weights = {}
    for key in ('market', 'price', 'logistics', 'stability'):
        d = domains.get(key) or {}
        cov = d.get('coverage_pct') or 0
        weights[key] = d.get('raw_max')
        score_factors.append({'key': key, 'label_ko': d.get('label') or key, 'weight': d.get('raw_max'),
                              'score': d.get('score') if cov > 0 else None, 'state': 'ok' if cov > 0 and d.get('score') is not None else 'insufficient',
                              'delta': None, 'series': [d.get('score') if cov > 0 else None], 'series_months': [month],
                              'note': f"근거 반영률 {cov:.0f}% · " + _factor_note(d), 'inputs': {'coverage_pct': cov, 'engine_score': d.get('score')},
                              'gate': False, 'needs_review': False})
    grade = overall.get('grade') or '판단 근거 부족'
    tone = {'FAVORABLE': 'ok', 'CONDITIONAL': 'info', 'PREPARATION_NEEDED': 'warn', 'REGULATION_BLOCKED': 'bad',
            'REGULATION_CONDITIONAL': 'warn', 'EVIDENCE_LIMITED': 'muted'}.get(overall.get('grade_code'), 'muted')
    highlights = (overall.get('reason') or '') + ' ' + ' '.join((overall.get('reasons') or [])[:2])
    score_overall = {'score': overall.get('score'), 'state': 'ok' if overall.get('score') is not None else 'insufficient',
                     'delta_vs_prev_month': None, 'series': [overall.get('score')], 'series_months': [month],
                     'weights': weights, 'weights_used': weights, 'excluded': [k for k, d in domains.items() if not (d.get('coverage_pct') or 0)],
                     'regulation_gate': reg_status, 'needs_regulation_review': True,
                     'note': f"{overall.get('coverage_label') or '근거 반영률'} {overall.get('coverage_pct', 0):.0f}% · 미평가 배점은 정책 기준 50점",
                     'grade': grade, 'grade_code': overall.get('grade_code'), 'tone': tone, 'coverage_pct': overall.get('coverage_pct')}
    validation = result.get('validation') or {}
    issues = validation.get('issues') or []
    return {
        'company_id': 'assessment:' + str(result.get('assessment_id')),
        'company_name': result.get('company_name') or inputs.get('company'),
        'company_name_en': '',
        'file_name': result.get('file_name'),
        'file_sha256': None,
        'schema': 'handoff-v1',
        'score_source': 'engine',
        'data_class': result.get('data_class') or '업로드 기업 데이터',
        'sample': bool(company.get('sample')),  # (2026-09-27 배포 QA) 가상 샘플이면 화면·보고서에 '가상 샘플'로 표시
        'template_version': (company.get('source') or {}).get('workbook_format') or 'company-workbook-v1',
        'generated_at': result.get('analysis_as_of'),
        'engine': {'assessment_id': result.get('assessment_id'), 'method_version': result.get('method_version'),
                   'suitability_version': overall.get('version'), 'grade': grade, 'grade_code': overall.get('grade_code'),
                   'coverage_pct': overall.get('coverage_pct'), 'reason': overall.get('reason'), 'gaps': overall.get('gaps') or [],
                   'assumptions': overall.get('assumptions') or [], 'warnings': result.get('warnings') or [],
                   'hs': result.get('hs'), 'hs_edition': result.get('hs_edition'), 'as_of': as_of,
                   'missing': missing_inputs(company)},  # 입력 결측(빈 칸·빠진 시트)
        'score': {'mode': 'engine', 'rule': 'suitability-reference-v1 (sanghyeob 엔진) — 시장 40·가격 20·물류 10·안정성 10, 규제는 별도 관문',
                  'weights': weights, 'overall_missing': 'policy_midpoint_50',
                  'note': '엔진 참고 적합도. 미평가 항목은 정책 기준 50점으로 계산하며 근거 반영률을 함께 표시한다. 수출 성공확률이 아님.',
                  'per_country': {country: {'overall': score_overall, 'factors': score_factors, 'highlights': highlights.strip()}}},
        'common': {'period': {'from': start, 'to': month}, 'products': products, 'hs_unknown_products': [],
                   'analysis_hs6': [hs6], 'countries': [{'name': country, 'iso2': iso2, 'export_share': None, 'amount_usd': None}],
                   'main_country': country, 'main_hs6': hs6, 'currency': 'USD',
                   'data_quality': {'rows_total': validation.get('row_count'), 'rows_valid': validation.get('accepted_row_count'),
                                    'missing_sheets': validation.get('missing_sheets') or [], 'issues': issues,
                                    'issue_counts': {'error': 0, 'warn': len(issues), 'info': 0}}},
        'per_country': {country: per_country_items},
        'rows_agg': [], 'logistics_agg': [], 'public_series': {'wsts_worldwide': []},
        'engine_detail': _detail(result),  # 세부 탭(상협 방식) 자료
    }
