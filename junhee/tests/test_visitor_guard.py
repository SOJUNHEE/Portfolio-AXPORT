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
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        with svc.store.connection() as db:
            db.execute('INSERT INTO market_sources VALUES(?,?,?,?,?,?)', ('s-old', 'visitor-' + 'a' * 32, old, 'a.xlsx', b'1', '{}'))
            db.execute('INSERT INTO market_sources VALUES(?,?,?,?,?,?)', ('s-new', 'visitor-' + 'b' * 32, datetime.now(timezone.utc).isoformat(), 'b.xlsx', b'1', '{}'))
            db.execute('INSERT INTO market_sources VALUES(?,?,?,?,?,?)', ('s-user', '00000000-0000-0000-0000-000000000001', old, 'c.xlsx', b'1', '{}'))
        local = self.app.extensions['junhee_workspace_local']
        with local._db() as db:
            db.execute('UPDATE visitor_workspaces SET updated_at=?', (time.time() - 10 * 86400,))
        users, workspaces = self.guard.purge_visitors(self.app)
        self.assertGreaterEqual(users, 1)
        self.assertGreaterEqual(workspaces, 1)
        with svc.store.connection() as db:
            left = {r[0] for r in db.execute('SELECT id FROM market_sources')}
        self.assertNotIn('s-old', left)
        self.assertIn('s-new', left)   # 최근 방문자는 남긴다
        self.assertIn('s-user', left)  # 로그인 계정 자료는 건드리지 않는다
        self.assertEqual(self.c.get('/api/workspace').get_json(), {'revision': 0, 'state': None})


if __name__ == '__main__':
    unittest.main()
