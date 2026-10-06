# -*- coding: utf-8 -*-
"""(junhee) 기업 파일 → sanghyeob 엔진 → handoff-v1 문서. 외부 API 키 없이(네트워크 호출 없음) 실행한다.

실행: python -m unittest junhee.tests.test_analysis -v
"""
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.update(AXPORT_ANALYSIS_INLINE='1', AXPORT_ANALYSIS_DB=os.path.join(tempfile.mkdtemp(), 'analysis.sqlite3'))
for _k in ('UN_COMTRADE_API_KEY', 'KCS_TRADE_API_KEY', 'ECOS_API_KEY', 'LAW_API_KEY'):
    os.environ[_k] = ''
from junhee.tests.test_accounts import ENV, TOKENS, USER, csrf, load_app  # noqa: E402

SAMPLES = ROOT / 'static' / 'samples'
EXAMPLE = '기업데이터_예시1_한울메모리.xlsx'


class EngineFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = load_app(ENV)

    def setUp(self):
        self.saved = []
        repo = mock.MagicMock()
        repo.save.side_effect = lambda user_id, token, aid, doc: self.saved.append((user_id, token, aid, doc))
        repo.load.return_value = None
        self.app.extensions['junhee_analysis'].repository = repo
        provider = mock.MagicMock()
        provider.get_user.return_value = USER
        provider.sign_in.return_value = dict(TOKENS)
        self.app.extensions['junhee_accounts']['provider'] = provider
        self.c = self.app.test_client()
        t = csrf(self.c.get('/app').get_data(as_text=True))
        self.c.post('/auth/login', data={'csrf_token': t, 'email': USER['email'], 'password': 'pw'})
        self.h = {'X-CSRF-Token': re.search(r'data-csrf="([^"]+)"', self.c.get('/app').get_data(as_text=True)).group(1)}

    def analyze(self, name, hs='854232', country='US'):
        data = (SAMPLES / name).read_bytes()
        r = self.c.post('/api/analysis/sources', data={'file': (io.BytesIO(data), name)}, headers=self.h, content_type='multipart/form-data')
        self.assertEqual(r.status_code, 201, r.get_json())
        r = self.c.post('/api/analysis/assessments', json={'company_id': r.get_json()['company_id'], 'company': '테스트기업', 'hs': hs, 'country': country}, headers=self.h)
        self.assertEqual(r.status_code, 202, r.get_json())
        return r.get_json()

    def test_simple_template_to_dashboard_doc(self):
        st = self.analyze(EXAMPLE)
        self.assertEqual(st['status'], 'COMPLETED')
        doc = self.c.get(f"/api/analysis/assessments/{st['assessment_id']}/handoff").get_json()
        self.assertEqual((doc['schema'], doc['score_source'], doc['company_name']), ('handoff-v1', 'engine', '테스트기업'))
        self.assertEqual(list(doc['per_country']), ['미국'])
        so = doc['score']['per_country']['미국']['overall']
        self.assertIsInstance(so['score'], float)
        self.assertIn('정책 기준 50점', so['note'])
        factors = {f['key']: f for f in doc['score']['per_country']['미국']['factors']}
        self.assertEqual(set(factors), {'regulation', 'market', 'price', 'logistics', 'stability'})
        self.assertIsNone(factors['regulation']['score'])  # 규제는 점수 없이 관문
        for f in factors.values():  # 근거 반영률 0% 요인은 점수를 보이지 않는다(자료 부족)
            if f['key'] != 'regulation' and not f['inputs']['coverage_pct']:
                self.assertEqual((f['state'], f['score']), ('insufficient', None))
        self.assertEqual(factors['logistics']['state'], 'ok')  # 간편입력의 공급·출고 계획은 키 없이도 반영
        items = {i['key']: i for area in doc['per_country']['미국'].values() for i in area}
        self.assertEqual(items['destination_imports']['status'], '검색 불가')  # 키 없음 → 값을 만들지 않음
        self.assertIsNone(items['destination_imports']['value'])
        self.assertEqual(items['tariff_reference']['value'], {'854232': 0})
        self.assertTrue(items['export_control_candidates']['rows'])
        # Supabase 저장(계정별)
        self.assertEqual(len(self.saved), 1)
        self.assertEqual((self.saved[0][0], self.saved[0][2]), (USER['id'], st['assessment_id']))
        json.dumps(doc, allow_nan=False)

    def test_sanghyeob_samples_by_id(self):
        """바탕화면 샘플(sanghyeob v0.1 상세양식 · 간편입력 예시)은 업로드 없이 샘플 id 로 분석한다."""
        samples = {s['company_id']: s for s in self.c.get('/api/analysis/samples').get_json()['samples']}
        self.assertEqual(set(samples), {'gaon', 'nuri', 'mirinae', 'hanbit', 'daesung', 'hanul', 'daon'})
        for cid in ('hanbit', 'gaon', 'mirinae'):
            s = samples[cid]
            self.assertTrue((SAMPLES / s['file_name']).is_file())
            r = self.c.post('/api/analysis/assessments', json={'company_id': cid, 'company': s['company_name'], 'hs': s['hs'], 'country': s['country_iso2']}, headers=self.h)
            self.assertEqual((r.status_code, r.get_json()['status']), (202, 'COMPLETED'), r.get_json())
            doc = self.c.get(f"/api/analysis/assessments/{r.get_json()['assessment_id']}/handoff").get_json()
            self.assertEqual((doc['file_name'], doc['company_name']), (s['file_name'], s['company_name']))
        r = self.c.post('/api/analysis/assessments', json={'company_id': 'saebyeok', 'company': 'x', 'hs': '854232', 'country': 'US'}, headers=self.h)
        self.assertEqual(r.status_code, 400)  # 목록에 없는 id 는 거부

    def test_download_uploaded_original(self):
        """바탕화면에서 업로드 파일 열기: 계정에 올린 원본을 그대로 내려받는다(본인 것만)."""
        data = (SAMPLES / EXAMPLE).read_bytes()
        r = self.c.post('/api/analysis/sources', data={'file': (io.BytesIO(data), EXAMPLE)}, headers=self.h, content_type='multipart/form-data')
        sid = r.get_json()['company_id'][7:]
        got = self.c.get(f'/api/analysis/sources/{sid}/file')
        self.assertEqual((got.status_code, got.data), (200, data))
        self.assertIn('attachment', got.headers['Content-Disposition'])
        self.assertEqual(self.c.get('/api/analysis/sources/not-a-uuid/file').status_code, 404)
        other = {'id': '00000000-0000-0000-0000-000000000009', 'email': 'o@example.com'}
        provider = self.app.extensions['junhee_accounts']['provider']
        provider.get_user.return_value = other
        provider.sign_in.return_value = dict(TOKENS, user=other)
        c2 = self.app.test_client()
        t = csrf(c2.get('/app').get_data(as_text=True))
        c2.post('/auth/login', data={'csrf_token': t, 'email': other['email'], 'password': 'pw'})
        self.assertEqual(c2.get(f'/api/analysis/sources/{sid}/file').status_code, 404)

    def test_company_file_upload_saves_to_work_folder(self):
        """'기업 파일 업로드': 작업 데이터 폴더에 저장(다른 내용·같은 이름은 (2), 같은 내용은 다시 쓰지 않음), 분석 원본 등록,
        양식이 아니면 저장하지 않음, 원본을 영구 삭제하면 저장 파일도 지움."""
        from junhee.server import analysis
        data = (SAMPLES / '기업데이터_가상_미리내전자_결측.xlsx').read_bytes()
        other = (SAMPLES / '기업데이터_가상_가온반도체.xlsx').read_bytes()
        with tempfile.TemporaryDirectory(dir=ROOT / 'junhee') as tmp, mock.patch.object(analysis, 'COMPANY_FILE_DIR', Path(tmp) / 'uploads'):
            folder = Path(tmp) / 'uploads'

            def up(body, name):
                return self.c.post('/api/analysis/company-files', data={'file': (io.BytesIO(body), name)}, headers=self.h, content_type='multipart/form-data')
            r1, r2, r3 = up(data, '../미리내.xlsx'), up(data, '미리내.xlsx'), up(other, '미리내.xlsx')
            self.assertEqual((r1.status_code, r2.status_code, r3.status_code), (201, 201, 201), r1.get_json())
            a, b, c = r1.get_json(), r2.get_json(), r3.get_json()
            self.assertEqual((a['name'], b['name'], c['name']), ('미리내.xlsx', '미리내.xlsx', '미리내 (2).xlsx'))  # 경로 문자 제거, 덮어쓰지 않음
            self.assertTrue(a['saved_path'].endswith('/uploads/미리내.xlsx'))
            self.assertEqual((folder / '미리내.xlsx').read_bytes(), data)
            self.assertEqual(len(a['missing']['fields']), 12)  # 결측 칸을 바로 알려 줌
            got = self.c.get(f"/api/analysis/sources/{a['company_id'][7:]}/file")  # 분석 원본으로도 등록
            self.assertEqual((got.status_code, got.data), (200, data))
            self.assertEqual(up(b'not excel', 'x.xlsx').status_code, 400)
            self.assertEqual(up(data, 'x.csv').status_code, 400)
            self.assertEqual(sorted(p.name for p in folder.iterdir()), ['미리내 (2).xlsx', '미리내.xlsx'])
            self.assertEqual(self.c.delete(f"/api/analysis/sources/{c['company_id'][7:]}", headers=self.h).get_json(), {'deleted': True})
            self.assertEqual(sorted(p.name for p in folder.iterdir()), ['미리내.xlsx'])  # 원본 삭제 → 저장 파일도 삭제
            with mock.patch.object(analysis, 'MAX_COMPANY_FILES', 1):
                self.assertEqual(up(other, '새파일.xlsx').status_code, 507)  # 폴더 상한

    def test_missing_inputs_inspect_and_doc(self):
        """결측 확인: 빈 칸의 셀·점수 영향을 알려 주고, 분석 문서에도 남긴다(값은 채우지 않음)."""
        chk = self.c.get('/api/analysis/inspect?company_id=mirinae').get_json()
        self.assertEqual((len(chk['fields']), sum(f['scored'] for f in chk['fields']), chk['missing_sheets']), (12, 8, []))
        self.assertIn('간편입력!B13', [f['cell'] for f in chk['fields']])  # 단위원가
        self.assertEqual(self.c.get('/api/analysis/inspect?company_id=gaon').get_json()['fields'], [])
        self.assertEqual(self.c.get('/api/analysis/inspect?company_id=nope').status_code, 404)
        r = self.c.post('/api/analysis/assessments', json={'company_id': 'mirinae', 'company': '미리내전자', 'hs': '854232', 'country': 'US'}, headers=self.h)
        doc = self.c.get(f"/api/analysis/assessments/{r.get_json()['assessment_id']}/handoff").get_json()
        self.assertEqual(len(doc['engine']['missing']['fields']), 12)

    def test_legacy_v03_sample_through_engine(self):
        """기존 junhee v0.3 샘플(수출실적 시트)도 엔진이 읽는지 — 호환성 확인."""
        st = self.analyze('한빛반도체_수출데이터_v0.3.xlsx')
        self.assertEqual(st['status'], 'COMPLETED', st)
        doc = self.c.get(f"/api/analysis/assessments/{st['assessment_id']}/handoff").get_json()
        self.assertTrue(doc['common']['products'])

    def test_handoff_saved_before_completed(self):
        """(검토 반영) COMPLETED 로 보이는 순간 /handoff 가 있어야 하고, 변환 실패면 COMPLETED 가 아니라 FAILED."""
        from junhee.server import analysis
        from junhee.server.engine.market_service import MarketStore
        seen = []
        real = MarketStore.update

        def spy(store, user_id, aid, status, progress, result=None, error=None):
            if status == 'COMPLETED':  # 실제로 COMPLETED 를 쓰는 순간 문서가 이미 있어야 한다
                with store.connection() as db:
                    seen.append(db.execute('SELECT 1 FROM junhee_handoff WHERE assessment_id=?', (aid,)).fetchone() is not None)
            return real(store, user_id, aid, status, progress, result=result, error=error)
        with mock.patch.object(MarketStore, 'update', spy):
            st = self.analyze(EXAMPLE)
        self.assertEqual((st['status'], seen), ('COMPLETED', [True]))
        with self.app.extensions['junhee_analysis'].store.connection() as db:  # 원문 응답(raw)은 저장하지 않는다(디스크 절약)
            stored = db.execute('SELECT result_json FROM market_assessments WHERE id=?', (st['assessment_id'],)).fetchone()[0]
        self.assertNotIn('"raw":', stored)
        self.assertEqual(self.c.get(f"/api/analysis/assessments/{st['assessment_id']}/handoff").status_code, 200)
        with mock.patch.object(analysis, 'to_handoff', side_effect=RuntimeError('x')):
            st = self.analyze(EXAMPLE, country='JP')
        self.assertEqual((st['status'], st['error']), ('FAILED', 'handoff_failed'))

    def test_delete_source_frees_quota(self):
        """(검토 반영) 영구 삭제한 업로드 원본을 지운다. 같은 내용을 쓰는 다른 파일의 분석 결과는 남긴다."""
        st = self.analyze(EXAMPLE)
        store = self.app.extensions['junhee_analysis'].store
        with store.connection() as db:
            sid = db.execute('SELECT source_id FROM market_assessments WHERE id=?', (st['assessment_id'],)).fetchone()[0]
        self.assertEqual(self.c.delete(f'/api/analysis/sources/{sid}').status_code, 403)  # CSRF
        r = self.c.delete(f'/api/analysis/sources/{sid}', headers=self.h)
        self.assertEqual((r.status_code, r.get_json()), (200, {'deleted': True}))
        self.assertEqual(self.c.get(f'/api/analysis/sources/{sid}/file').status_code, 404)
        self.assertEqual(self.c.get(f"/api/analysis/assessments/{st['assessment_id']}/handoff").status_code, 200)
        self.assertEqual(self.c.delete(f'/api/analysis/sources/{sid}', headers=self.h).get_json(), {'deleted': False})
        self.assertEqual(self.c.delete('/api/analysis/sources/not-a-uuid', headers=self.h).status_code, 404)

    def test_company_file_upload_size_limit(self):
        big = b'0' * (21 * 1024 * 1024)
        r = self.c.post('/api/analysis/company-files', data={'file': (io.BytesIO(big), 'big.xlsx')}, headers=self.h, content_type='multipart/form-data')
        self.assertEqual(r.status_code, 413)

    def test_errors_are_messages_not_crashes(self):
        r = self.c.post('/api/analysis/sources', data={'file': (io.BytesIO(b'not excel'), 'x.xlsx')}, headers=self.h, content_type='multipart/form-data')
        self.assertEqual(r.status_code, 400)
        self.assertTrue(r.get_json()['message'])
        r = self.c.post('/api/analysis/assessments', json={'company_id': 'upload:00000000-0000-0000-0000-000000000000', 'company': 'x', 'hs': '854232', 'country': 'US'}, headers=self.h)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.c.get('/api/analysis/assessments/not-a-uuid').status_code, 404)
        self.assertEqual(self.c.post('/api/analysis/assessments', json={}).status_code, 403)  # CSRF

    def test_other_account_cannot_read(self):
        st = self.analyze(EXAMPLE)
        other = {'id': '00000000-0000-0000-0000-000000000009', 'email': 'o@example.com'}
        provider = self.app.extensions['junhee_accounts']['provider']
        # 같은 세션으로 다른 사용자를 흉내 내면 세션이 무효가 되고, (2026-10-05) 방문자로 바뀌어 결과를 찾을 수 없다(404)
        provider.get_user.return_value = other
        self.assertEqual(self.c.get(f"/api/analysis/assessments/{st['assessment_id']}/handoff").status_code, 404)
        # 다른 계정으로 따로 로그인한 브라우저는 결과를 찾을 수 없다(404)
        provider.sign_in.return_value = dict(TOKENS, user=other)
        c2 = self.app.test_client()
        t = csrf(c2.get('/app').get_data(as_text=True))
        c2.post('/auth/login', data={'csrf_token': t, 'email': other['email'], 'password': 'pw'})
        self.assertEqual(c2.get(f"/api/analysis/assessments/{st['assessment_id']}/handoff").status_code, 404)
        self.assertEqual(c2.get(f"/api/analysis/assessments/{st['assessment_id']}").status_code, 404)


class Adapter(unittest.TestCase):
    def test_key_mapping_and_percent(self):
        sys.modules.pop('junhee.server.engine_adapter', None)
        from junhee.server.engine_adapter import to_handoff
        metric = lambda i, v, u, s='OBSERVED': {'id': i, 'label': i, 'value': v, 'unit': u, 'status': s, 'period': '2025', 'evidence': []}
        result = {'assessment_id': 'a1', 'country_iso2': 'DE', 'hs6': '854231', 'as_of': '2026-09-27', 'company_name': 'X', 'file_name': 'x.xlsx',
                  'overall': {'score': 61.0, 'grade': '조건부 검토', 'grade_code': 'CONDITIONAL', 'coverage_pct': 60.0, 'regulation_status': 'REVIEW_REQUIRED',
                              'domains': [{'key': 'market', 'score': 70.0, 'raw_max': 40, 'coverage_pct': 100.0, 'components': []}]},
                  'factors': [{'key': 'market', 'metrics': [metric('import_ytd_yoy', 0.125, 'ratio'), metric('import_value', 5e9, 'USD'),
                                                             metric('korea_exports', None, 'USD', 'FETCH_ERROR')]},
                              {'key': 'price', 'metrics': [metric('fx_reference_rate:KRW', 1, 'x'), metric('fx_reference_rate:USD', 1390.0, 'KRW/USD')]}]}
        doc = to_handoff(result, {'sheets': {'제품정보': []}}, {})
        items = {i['key']: i for a in doc['per_country']['독일'].values() for i in a}
        self.assertEqual((items['growth_yoy']['value'], items['growth_yoy']['unit']), (12.5, '%'))
        self.assertEqual(items['destination_imports']['value'], 5e9)
        self.assertEqual((items['korea_exports_to_destination']['status'], items['korea_exports_to_destination']['value']), ('검색 불가', None))
        self.assertEqual(items['fx_reference']['value'], 1390.0)  # 원/USD 는 USD 지표
        self.assertIn('fx_reference_rate:KRW', items)
        self.assertEqual(doc['common']['period'], {'from': '2026-09', 'to': '2026-09'})  # 비교기간 없음 → 기준월 하나(지어내지 않음)
        result['factors'].append({'key': 'stability', 'metrics': [], 'comparison_window': {'end_month': '2026-06'}})
        self.assertEqual(to_handoff(result, {'sheets': {}}, {})['common']['period'], {'from': '2023-07', 'to': '2026-06'})  # 36개월 창
        market = next(f for f in doc['score']['per_country']['독일']['factors'] if f['key'] == 'market')
        self.assertEqual((market['score'], market['state']), (70.0, 'ok'))


if __name__ == '__main__':
    unittest.main()
