# -*- coding: utf-8 -*-
"""(2026-10-06 공개 데모) 방문자 요청 제한·업로드 상한·보관기간 정리·서버 기록 유실 후 저장.

실행: python -m unittest junhee.tests.test_visitor_guard -v   (프로젝트 루트에서)
"""
from datetime import datetime, timedelta, timezone
import os
import re
import sys
import tempfile
import time
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
TMP = tempfile.mkdtemp(prefix='axport-guard-test-')
os.environ.update(AXPORT_ANALYSIS_DB=os.path.join(TMP, 'analysis.sqlite3'), AXPORT_WIDGET_REFRESH='0')

from junhee.tests.test_accounts import ENV, load_app  # noqa: E402

GUARD_ENV = dict(ENV, AXPORT_VISITOR_DB=os.path.join(TMP, 'visitor.sqlite3'), AXPORT_AUTH_DB=os.path.join(TMP, 'auth.sqlite3'))


class VisitorGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = load_app(GUARD_ENV)
        cls.guard = sys.modules['junhee.server.visitor_guard']

    def setUp(self):
        self.app.extensions['junhee_visitor_guard']['hits'].clear()
        self.c = self.app.test_client()
        self.token = re.search(r'data-csrf="([^"]+)"', self.c.get('/app').get_data(as_text=True)).group(1)

    def h(self):
        return {'X-CSRF-Token': self.token}

    def test_upload_size_and_rate_limit(self):
        big = b'x' * (self.guard.VISITOR_MAX_UPLOAD + 200 * 1024)
        r = self.c.post('/api/analysis/sources', data={'file': (__import__('io').BytesIO(big), 'big.xlsx')}, headers=self.h())
        self.assertEqual(r.status_code, 413)
        codes = [self.c.post('/api/analysis/sources', data={'file': (__import__('io').BytesIO(b'not excel'), 'a.xlsx')},
                             headers=self.h()).status_code for _ in range(12)]
        self.assertNotIn(429, codes[:9])  # 첫 요청(413)을 포함해 10번까지 허용
        self.assertEqual(codes[-1], 429)

    def test_workspace_saved_again_after_server_record_lost(self):
        body = {'revision': 5, 'state': {'v': 1, 'items': [], 'system': {}}}  # 서버에는 이 방문자 기록이 없음
        self.assertEqual(self.c.put('/api/workspace', json=body, headers=self.h()).get_json(), {'revision': 6})
        self.assertEqual(self.c.put('/api/workspace', json=body, headers=self.h()).status_code, 409)

    def test_purge_old_visitor_data_only(self):
        body = {'revision': 0, 'state': {'v': 1, 'items': [], 'system': {}}}
        self.assertEqual(self.c.put('/api/workspace', json=body, headers=self.h()).status_code, 200)
        svc = self.app.extensions['junhee_analysis']
        now = datetime.now(timezone.utc)
        old = (now - timedelta(days=10)).isoformat()
        a, b, c, d = ('visitor-' + ch * 32 for ch in 'abcd')
        company_dir = sys.modules['junhee.server.analysis'].COMPANY_FILE_DIR
        company_dir.mkdir(parents=True, exist_ok=True)
        stale_file = company_dir / 'guard-test-stale.xlsx'
        stale_file.write_bytes(b'1')
        with svc.store.connection() as db:
            for sid, uid, created in (('s-old', a, old), ('s-new', b, now.isoformat()), ('s-active', c, old),
                                      ('s-seen', d, old), ('s-user', '00000000-0000-0000-0000-000000000001', old)):
                db.execute('INSERT INTO market_sources VALUES(?,?,?,?,?,?)', (sid, uid, created, 'x.xlsx', b'1', '{}'))
            db.execute('INSERT INTO junhee_company_files VALUES (?, ?, ?)', (a, 's-old', stale_file.name))
            db.execute("INSERT INTO market_assessments VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                       ('00000000-0000-0000-0000-0000000000aa', c, 'QUEUED', old, old, time.time(), '{}', 's-active', 'x', None, None))
        local = self.app.extensions['junhee_workspace_local']
        local.touch(d, time.time())  # 최근에 화면만 열어 본 방문자도 '사용'으로 본다
        with local._db() as db:
            db.execute('UPDATE visitor_workspaces SET updated_at=?', (time.time() - 10 * 86400,))
            db.execute("UPDATE visitor_seen SET last_seen=? WHERE user_id != ?", (time.time() - 10 * 86400, d))
        users, workspaces = self.guard.purge_visitors(self.app)
        self.assertGreaterEqual(users, 1)
        self.assertGreaterEqual(workspaces, 1)
        with svc.store.connection() as db:
            left = {r[0] for r in db.execute('SELECT id FROM market_sources')}
            files = db.execute('SELECT COUNT(*) FROM junhee_company_files WHERE user_id=?', (a,)).fetchone()[0]
        mine = {'s-old', 's-new', 's-active', 's-seen', 's-user'}  # 다른 테스트가 같은 DB 에 남긴 행은 보지 않는다
        self.assertEqual(left & mine, {'s-new', 's-active', 's-seen', 's-user'})  # 최근·진행 중·최근 사용·로그인 계정은 남긴다
        self.assertEqual(files, 0)
        self.assertFalse(stale_file.exists())
        self.assertEqual(self.c.get('/api/workspace').get_json(), {'revision': 0, 'state': None})

    def test_parse_slot_is_released(self):
        state = self.app.extensions['junhee_visitor_guard']
        for _ in range(4):  # 해석 자리(2개)가 매번 반환되어야 계속 처리된다
            r = self.c.get('/api/analysis/inspect?company_id=gaon')
            self.assertNotEqual(r.status_code, 429)
        self.assertTrue(all(state['parse'].acquire(blocking=False) for _ in range(self.guard.PARSE_SLOTS)))
        for _ in range(self.guard.PARSE_SLOTS):
            state['parse'].release()

    def test_robots_and_headers(self):
        r = self.c.get('/robots.txt')
        self.assertEqual((r.status_code, r.mimetype), (200, 'text/plain'))
        self.assertIn('Disallow: /', r.get_data(as_text=True))
        for path in ('/', '/app'):
            h = self.c.get(path).headers
            self.assertIn('noindex', h['X-Robots-Tag'])
            self.assertIn('camera=()', h['Permissions-Policy'])

    def test_visitor_cookie_refreshed_daily(self):
        self.assertNotIn('Set-Cookie', self.c.get('/app').headers)  # 같은 날 재방문은 쿠키를 다시 쓰지 않는다
        with self.c.session_transaction() as sess:
            sess['seen'] = '2000-01-01'
        self.assertIn('Set-Cookie', self.c.get('/app').headers)  # 다른 날이면 다시 발급해 7일이 마지막 사용 기준이 된다

if __name__ == '__main__':
    unittest.main()
