# -*- coding: utf-8 -*-
"""(2026-10-12 Vercel 배포) SQLite→Postgres 호환 계층, 크론, Vercel 환경 설정.

실행: python -m unittest junhee.tests.test_vercel_support -v   (프로젝트 루트에서)
Postgres 실제 연결 검사는 AXPORT_TEST_DATABASE_URL 이 있을 때만 돈다(빈 테스트용 DB 를 가리킬 것).
"""
import importlib
import io
import os
import re
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
TMP = tempfile.mkdtemp(prefix='axport-vercel-test-')
NO_DB = {'DATABASE_URL': '', 'AXPORT_DATABASE_URL': '', 'POSTGRES_URL': ''}

from junhee.server import dbcompat  # noqa: E402

VISITOR_ENV = {'SUPABASE_URL': '', 'SUPABASE_PUBLISHABLE_KEY': '', 'FLASK_SECRET_KEY': 'v' * 48, 'SESSION_COOKIE_SECURE': 'false',
               'AXPORT_AUTH_DB': os.path.join(TMP, 'auth.sqlite3'), 'AXPORT_VISITOR_DB': os.path.join(TMP, 'visitor.sqlite3'),
               'AXPORT_ANALYSIS_DB': os.path.join(TMP, 'analysis.sqlite3'), 'AXPORT_WIDGET_REFRESH': '0',
               'AXPORT_DATA_MODE': 'demo', 'AXPORT_CHAT_MODE': 'demo', 'DATABASE_URL': '', 'AXPORT_DATABASE_URL': '', 'POSTGRES_URL': ''}


def load_visitor_app(**extra):
    """로그인 설정 없이(.env 무시) 공개 데모 모드로 앱을 새로 불러온다."""
    with mock.patch.dict(os.environ, dict(VISITOR_ENV, **extra)):
        for name in [n for n in sys.modules if n == 'app' or n.startswith('junhee.server')]:
            del sys.modules[name]
        import junhee.server.accounts as acc
        with mock.patch.object(acc, '_load_root_env'):
            return importlib.import_module('app').app


class Translate(unittest.TestCase):
    def test_placeholders_skip_string_literals_and_escape_percent(self):
        sql = dbcompat._translate("SELECT '?', x FROM t WHERE a=? AND b LIKE 'v-%' AND c LIKE ?")
        self.assertEqual(sql, "SELECT '?', x FROM t WHERE a=%s AND b LIKE 'v-%%' AND c LIKE %s")

    def test_scalar_max_and_ddl_types(self):
        self.assertIn('GREATEST(available_at, excluded.available_at)',
                      dbcompat._translate('UPDATE SET available_at = MAX(available_at, excluded.available_at)'))
        ddl = dbcompat._translate('CREATE TABLE IF NOT EXISTS t (a BLOB, b REAL NOT NULL, c INTEGER)')
        self.assertEqual(ddl, 'CREATE TABLE IF NOT EXISTS t (a BYTEA, b DOUBLE PRECISION NOT NULL, c BIGINT)')
        self.assertNotIn('BIGINT', dbcompat._translate("SELECT 'INTEGER' FROM t"))  # 정의문이 아니면 그대로

    def test_row_supports_key_index_and_dict(self):
        row = dbcompat.Cursor([(1, 'a')], ('n', 's')).fetchone()
        self.assertEqual((row[0], row['s'], dict(row), list(row)), (1, 'a', {'n': 1, 's': 'a'}, [1, 'a']))

    def test_sqlite_used_without_database_url(self):
        with mock.patch.dict(os.environ, {n: '' for n in dbcompat.URL_NAMES}):
            self.assertFalse(dbcompat.enabled())
            db = dbcompat.connect(os.path.join(TMP, 'plain.sqlite3'))
            try:
                self.assertIsInstance(db, sqlite3.Connection)
            finally:
                db.close()


class Cron(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = load_visitor_app()

    def test_requires_matching_cron_secret(self):
        c = self.app.test_client()
        with mock.patch.dict(os.environ, {'CRON_SECRET': ''}):
            self.assertEqual(c.get('/api/cron/daily', headers={'Authorization': 'Bearer '}).status_code, 404)
        with mock.patch.dict(os.environ, {'CRON_SECRET': 's' * 32}):
            self.assertEqual(c.get('/api/cron/daily').status_code, 404)
            self.assertEqual(c.get('/api/cron/daily', headers={'Authorization': 'Bearer wrong'}).status_code, 404)
            with mock.patch.dict(os.environ, NO_DB):
                r = c.get('/api/cron/daily', headers={'Authorization': 'Bearer ' + 's' * 32})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {'purge': {'analysis_users': 0, 'workspaces': 0}})  # 외부 DB 가 없으면 위젯 갱신은 건너뜀

    def test_bundled_widgets_served_without_database(self):
        r = self.app.test_client().get('/static/data/widgets/widgets.json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('fx', r.get_json())
        r.close()


class VercelEnvironment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = load_visitor_app(VERCEL='1')
        cls.guard = sys.modules['junhee.server.visitor_guard']
        cls.analysis = sys.modules['junhee.server.analysis']

    def test_runs_analysis_inline_and_limits_upload_below_vercel_body_limit(self):
        self.assertTrue(self.app.extensions['junhee_analysis'].inline)
        self.assertEqual(self.guard.VISITOR_MAX_UPLOAD, 4 * 1024 * 1024)
        c = self.app.test_client()
        with mock.patch.dict(os.environ, NO_DB):
            html = c.get('/app').get_data(as_text=True)
        self.assertIn('업로드는 4 MB 이하로', html)
        self.assertIn('서버가 다시 시작되면', html)  # 외부 DB 가 없으면 임시 저장이라는 안내를 유지
        token = re.search(r'data-csrf="([^"]+)"', html).group(1)
        big = b'x' * (4 * 1024 * 1024 + 100 * 1024)
        r = c.post('/api/analysis/sources', data={'file': (io.BytesIO(big), 'big.xlsx')}, headers={'X-CSRF-Token': token})
        self.assertEqual(r.status_code, 413)
        self.assertIn('4 MB', r.get_json()['message'])

    def test_trusts_vercel_proxy_and_does_not_keep_upload_files(self):
        r = self.app.test_client().get('/', headers={'X-Forwarded-Proto': 'https'})
        self.assertIn('Strict-Transport-Security', r.headers)  # ProxyFix 로 https 요청으로 인식
        with mock.patch.dict(os.environ, {'VERCEL': '1'}):
            self.assertFalse(self.analysis.keep_upload_files())
        with mock.patch.dict(os.environ, {'VERCEL': '', **{n: '' for n in dbcompat.URL_NAMES}}):
            self.assertTrue(self.analysis.keep_upload_files())


    def test_company_file_upload_records_name_without_writing_files(self):
        from pathlib import Path
        data = (Path(ROOT) / 'static' / 'samples' / '기업데이터_가상_가온반도체.xlsx').read_bytes()
        other = (Path(ROOT) / 'static' / 'samples' / '기업데이터_가상_미리내전자_결측.xlsx').read_bytes()
        c = self.app.test_client()
        token = re.search(r'data-csrf="([^"]+)"', c.get('/app').get_data(as_text=True)).group(1)

        def up(body, name):
            return c.post('/api/analysis/company-files', data={'file': (io.BytesIO(body), name)},
                          headers={'X-CSRF-Token': token}, content_type='multipart/form-data')
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'VERCEL': '1'}), \
                mock.patch.object(self.analysis, 'COMPANY_FILE_DIR', Path(tmp) / 'uploads'):
            a, b, d = up(data, '가온.xlsx'), up(data, '가온.xlsx'), up(other, '가온.xlsx')
            self.assertEqual((a.status_code, b.status_code, d.status_code), (201, 201, 201), a.get_json())
            names = [r.get_json()['name'] for r in (a, b, d)]
            self.assertEqual(names, ['가온.xlsx', '가온.xlsx', '가온 (2).xlsx'])  # 같은 내용은 같은 이름, 다른 내용은 (2)
            self.assertEqual(a.get_json()['saved_path'], '가온.xlsx')  # 실제 경로가 없으므로 이름만
            self.assertFalse((Path(tmp) / 'uploads').exists())  # 파일을 쓰지 않음
            got = c.get(f"/api/analysis/sources/{a.get_json()['company_id'][7:]}/file")
            self.assertEqual((got.status_code, got.data), (200, data))  # 원본은 분석 저장소에서 내려받음
            with mock.patch.object(self.analysis, 'MAX_COMPANY_FILES', 1):
                third = (Path(ROOT) / 'static' / 'samples' / '기업데이터_가상_누리하이테크.xlsx').read_bytes()
                self.assertEqual(up(third, '누리.xlsx').status_code, 507)  # 전체 개수 상한은 DB 기록으로 센다


@unittest.skipUnless(os.environ.get('AXPORT_TEST_DATABASE_URL'), 'AXPORT_TEST_DATABASE_URL 이 없으면 Postgres 검사를 건너뜀')
class Postgres(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {'DATABASE_URL': os.environ['AXPORT_TEST_DATABASE_URL']})
        self.env.start()
        self.addCleanup(self.env.stop)
        with self.db() as db:
            for table in ('compat_items', 'compat_journal'):
                db.execute(f'DROP TABLE IF EXISTS {table}')
        dbcompat._ddl_done.clear()
        dbcompat._schema_cache.clear()

    def db(self, name='compat.sqlite3', **kw):
        return _Closing(dbcompat.connect(name, **kw))

    def test_sqlite_style_statements(self):
        now = time.time()
        with self.db() as db:
            self.assertIsInstance(db, dbcompat.PgConnection)
            db.execute('CREATE TABLE IF NOT EXISTS compat_items (id TEXT PRIMARY KEY, n INTEGER NOT NULL, at REAL NOT NULL, body BLOB)')
            db.execute('INSERT OR REPLACE INTO compat_items VALUES (?, ?, ?, ?)', ('visitor-1', 1, now, b'\x00\xff'))
            db.execute('INSERT OR REPLACE INTO compat_items VALUES (?, ?, ?, ?)', ('visitor-1', 2, now, b'\x01'))
            db.execute('INSERT INTO compat_items VALUES (?, ?, ?, ?)', ('other', 3, now, None))
        with self.db() as db:
            rows = db.execute("SELECT * FROM compat_items WHERE id LIKE ? AND id <> '%x' ORDER BY id", ('visitor-%',)).fetchall()
            self.assertEqual([(r['id'], r['n'], r['body']) for r in rows], [('visitor-1', 2, b'\x01')])
            self.assertAlmostEqual(rows[0]['at'], now, places=3)  # REAL → DOUBLE PRECISION (4바이트 실수면 초 단위가 뭉개짐)
            self.assertEqual(db.execute('SELECT COALESCE(SUM(n), 0) FROM compat_items').fetchone()[0], 5)
            self.assertEqual([r[1] for r in db.execute('PRAGMA table_info(compat_items)')], ['id', 'n', 'at', 'body'])
            db.execute('PRAGMA journal_mode=WAL')  # 무시
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO compat_items VALUES (?, ?, ?, ?)', ('other', 4, now, None))

    def test_begin_immediate_rolls_back_like_sqlite(self):
        from junhee.server.workspace_store import closing_commit
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS compat_items (id TEXT PRIMARY KEY, n INTEGER NOT NULL, at REAL NOT NULL, body BLOB)')
        with self.assertRaises(RuntimeError):
            with closing_commit(dbcompat.connect('compat.sqlite3')) as db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('INSERT INTO compat_items VALUES (?, ?, ?, ?)', ('rolled-back', 1, 0.0, None))
                raise RuntimeError('x')
        with self.db() as db:
            self.assertIsNone(db.execute("SELECT 1 FROM compat_items WHERE id='rolled-back'").fetchone())

    def test_aliases_keep_same_named_tables_apart(self):
        with self.db('journal.sqlite3', aliases={'compat_items': 'compat_journal'}) as db:
            db.execute('CREATE TABLE IF NOT EXISTS compat_items (k TEXT PRIMARY KEY)')
            db.execute('INSERT INTO compat_items VALUES (?)', ('j',))
        with self.db() as db:
            self.assertEqual(db.execute('SELECT k FROM compat_journal').fetchall()[0]['k'], 'j')


class _Closing:
    """with 블록이 끝나면 커밋(오류면 롤백)하고 연결을 돌려준다."""

    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, *_):
        try:
            self.conn.rollback() if exc_type else self.conn.commit()
        finally:
            self.conn.close()
        return False


if __name__ == '__main__':
    unittest.main()
