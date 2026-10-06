# -*- coding: utf-8 -*-
"""(junhee) 회원가입 → 인증 메일 → 인증 링크 → 로그인 → 로그아웃 흐름. Supabase 는 가짜(mock)로 대신한다.

실행: python -m unittest junhee.tests.test_accounts -v   (프로젝트 루트에서)
"""
import importlib
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

TMP = tempfile.mkdtemp(prefix='axport-auth-test-')
ENV = {'SUPABASE_URL': 'https://example-project.supabase.co', 'SUPABASE_PUBLISHABLE_KEY': 'sb_publishable_test',
       'FLASK_SECRET_KEY': 'x' * 48, 'SESSION_COOKIE_SECURE': 'false',
       'AXPORT_AUTH_DB': os.path.join(TMP, 'auth.sqlite3'), 'AXPORT_VISITOR_DB': os.path.join(TMP, 'visitor.sqlite3'),
       'AXPORT_DATA_MODE': 'demo', 'AXPORT_CHAT_MODE': 'demo'}
USER = {'id': '00000000-0000-0000-0000-000000000001', 'email': 'tester@example.com', 'email_confirmed_at': '2026-09-27T00:00:00Z'}
TOKENS = {'access_token': 'access-1', 'refresh_token': 'refresh-1', 'expires_in': 3600, 'user': USER}


def load_app(env):
    with mock.patch.dict(os.environ, env, clear=False):
        for name in [n for n in sys.modules if n == 'app' or n.startswith('junhee.server')]:
            del sys.modules[name]
        return importlib.import_module('app').app


def csrf(html):
    # (2026-10-05) 로그인 화면 폼이 아니라 /app 의 방문자 정보(data-csrf)에서도 같은 세션 토큰을 읽는다
    m = re.search(r'(?:name="csrf_token" value|data-csrf)="([^"]+)"', html)
    return m.group(1) if m else ''


class NotConfigured(unittest.TestCase):
    def test_app_works_without_login_settings(self):
        # (2026-10-05) 로그인 설정이 없어도 /app 과 방문자 저장이 동작한다
        env = {k: '' for k in ('SUPABASE_URL', 'SUPABASE_PUBLISHABLE_KEY', 'FLASK_SECRET_KEY')}
        env['AXPORT_VISITOR_DB'] = os.path.join(TMP, 'visitor-notconfigured.sqlite3')
        # _load_root_env 를 막은 상태로 새로 불러온다(.env 에 값이 있어도 무시)
        with mock.patch.dict(os.environ, env):
            for name in [n for n in sys.modules if n == 'app' or n.startswith('junhee.server')]:
                del sys.modules[name]
            import junhee.server.accounts as acc
            with mock.patch.object(acc, '_load_root_env'):
                app = importlib.import_module('app').app
        c = app.test_client()
        self.assertEqual(c.get('/').status_code, 200)
        r = c.get('/app')
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertIn('id="analysis-window"', html)
        self.assertIn('data-visitor="1"', html)
        self.assertNotIn('action="/auth/login"', html)
        self.assertEqual(c.get('/api/workspace').get_json(), {'revision': 0, 'state': None})
        t = csrf(html)
        body = {'revision': 0, 'state': {'v': 1, 'items': [], 'system': {}}}
        self.assertEqual(c.put('/api/workspace', json=body, headers={'X-CSRF-Token': t}).get_json(), {'revision': 1})
        self.assertEqual(c.get('/api/auth/session').status_code, 503)


class Flow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = load_app(ENV)
        cls.acc = sys.modules['junhee.server.accounts']

    def setUp(self):
        self.provider = mock.MagicMock()
        self.provider.get_user.return_value = USER
        self.app.extensions['junhee_accounts']['provider'] = self.provider
        self.c = self.app.test_client()

    def token(self):
        return csrf(self.c.get('/app').get_data(as_text=True))

    def test_pages_open_without_login(self):
        # (2026-10-05) 로그인 없이 작업공간·분석·바탕화면 저장을 쓴다. 로그인 세션 API 만 401
        for path in ('/app', '/_axp_semiconductor/original'):
            r = self.c.get(path)
            self.assertEqual(r.status_code, 200)
            self.assertNotIn('action="/auth/login"', r.get_data(as_text=True))
        html = self.c.get('/app').get_data(as_text=True)
        self.assertIn('id="analysis-window"', html)
        self.assertIn('data-visitor="1"', html)
        self.assertNotIn('id="password-form"', html)  # 계정 창은 로그인 사용자만
        self.assertEqual(self.c.get('/api/auth/session').status_code, 401)
        self.assertEqual(self.c.get('/api/workspace').status_code, 200)
        self.assertEqual(self.c.get('/api/analysis/samples').status_code, 200)

    def test_visitors_are_separated_and_csrf_checked(self):
        body = {'revision': 0, 'state': {'v': 1, 'items': [{'id': 'f1', 'kind': 'folder', 'name': '방문자 폴더'}], 'system': {}}}
        t = self.token()
        self.assertEqual(self.c.put('/api/workspace', json=body).status_code, 403)  # CSRF 없음
        self.assertEqual(self.c.put('/api/workspace', json=body, headers={'X-CSRF-Token': t}).get_json(), {'revision': 1})
        self.assertEqual(self.c.put('/api/workspace', json=body, headers={'X-CSRF-Token': t}).status_code, 409)  # 오래된 revision
        self.assertEqual(self.c.get('/api/workspace').get_json()['state']['items'][0]['name'], '방문자 폴더')
        other = self.app.test_client()
        other.get('/app')
        self.assertEqual(other.get('/api/workspace').get_json(), {'revision': 0, 'state': None})  # 다른 브라우저는 따로

    def test_public_routes_untouched(self):
        self.assertEqual(self.c.get('/').status_code, 200)
        r = self.c.post('/api/contact', json={})  # CSRF 검사 대상이 아님 → 입력 검증 400
        self.assertEqual(r.status_code, 400)

    def test_csrf_required(self):
        self.c.get('/app')
        r = self.c.post('/auth/login', data={'email': 'a@b.co', 'password': 'x'})
        self.assertEqual(r.status_code, 403)
        self.provider.sign_in.assert_not_called()

    def test_signup_confirm_login_logout(self):
        email = 'new-user@example.com'
        t = self.token()
        self.provider.sign_up.return_value = {'id': 'u'}
        r = self.c.post('/auth/signup', data={'csrf_token': t, 'email': email, 'password': 'Passw0rd!x', 'password_confirm': 'Passw0rd!x'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('인증 메일을 보냈습니다', r.get_data(as_text=True))
        args = self.provider.sign_up.call_args[0]
        self.assertEqual(args[:2], (email, 'Passw0rd!x'))
        self.assertEqual(args[2], 'http://localhost/auth/confirm')
        # 60초 안에 재요청 → 429, Supabase 호출 없음
        r = self.c.post('/auth/resend', data={'csrf_token': t, 'email': email})
        self.assertEqual(r.status_code, 429)
        self.provider.resend_signup.assert_not_called()
        # 메일의 인증 링크
        self.provider.confirm_email.return_value = {'user': USER, 'access_token': 'verify-token'}
        r = self.c.get('/auth/confirm?token_hash=' + 'ab' * 20 + '&type=email')
        self.assertEqual(r.status_code, 303)
        r = self.c.get(r.headers['Location'])
        self.assertIn('이메일 인증이 완료되었습니다', r.get_data(as_text=True))
        self.provider.sign_out.assert_called_with('verify-token')  # 인증만 하고 자동 로그인하지 않음
        self.assertEqual(self.c.get('/api/auth/session').status_code, 401)
        # 로그인
        self.provider.sign_in.return_value = dict(TOKENS)
        r = self.c.post('/auth/login', data={'csrf_token': t, 'email': USER['email'], 'password': 'Passw0rd!x'})
        self.assertEqual((r.status_code, r.headers['Location']), (303, '/app'))
        r = self.c.get('/app')
        html = r.get_data(as_text=True)
        self.assertIn('id="analysis-window"', html)
        self.assertIn('data-email="tester@example.com"', html)
        self.assertNotIn('access-1', html)  # 토큰은 화면·쿠키로 나가지 않는다
        self.assertEqual(self.c.get('/api/auth/session').get_json()['user']['email'], USER['email'])
        # 로그아웃
        t2 = csrf(html)
        r = self.c.post('/auth/logout', data={'csrf_token': t2})
        self.assertEqual(r.status_code, 303)
        self.provider.sign_out.assert_called_with('access-1')
        self.assertIn('data-visitor="1"', self.c.get('/app?auth=logged_out').get_data(as_text=True))  # 로그아웃 뒤에도 바로 사용

    def test_wrong_password(self):
        t = self.token()
        self.provider.sign_in.side_effect = self.acc.AuthError('invalid_credentials', 401)
        r = self.c.post('/auth/login', data={'csrf_token': t, 'email': USER['email'], 'password': 'bad'})
        self.assertEqual(r.status_code, 401)
        self.assertIn('이메일 인증 여부', r.get_data(as_text=True))

    def login(self):
        self.provider.sign_in.return_value = dict(TOKENS)
        self.c.post('/auth/login', data={'csrf_token': self.token(), 'email': USER['email'], 'password': 'Passw0rd!x'})
        html = self.c.get('/app').get_data(as_text=True)
        self.assertIn('id="password-form"', html)
        return csrf(html)

    def test_change_password_immediately(self):
        url = '/api/auth/password'
        body = {'password': 'NewPassw0rd!', 'password_confirm': 'NewPassw0rd!'}
        self.assertEqual(self.c.post(url, json=body, headers={'X-CSRF-Token': self.token()}).status_code, 401)
        t = self.login()
        self.assertEqual(self.c.post(url, json=body).status_code, 403)  # CSRF 없음
        r = self.c.post(url, json={**body, 'password_confirm': 'other'}, headers={'X-CSRF-Token': t})
        self.assertEqual((r.status_code, r.get_json()['error']), (400, 'password_mismatch'))
        r = self.c.post(url, json={'password': 'short', 'password_confirm': 'short'}, headers={'X-CSRF-Token': t})
        self.assertEqual((r.status_code, r.get_json()['error']), (400, 'password_length'))
        self.provider.update_password.assert_not_called()
        self.provider.update_password.return_value = USER
        r = self.c.post(url, json=body, headers={'X-CSRF-Token': t})
        self.assertEqual(r.status_code, 200)
        self.provider.update_password.assert_called_once_with('access-1', 'NewPassw0rd!')  # 메일 인증 없이 바로
        self.assertEqual(self.c.get('/api/auth/session').status_code, 200)  # 로그인 유지
        self.provider.update_password.side_effect = self.acc.AuthError('same_password', 400)
        r = self.c.post(url, json=body, headers={'X-CSRF-Token': t})
        self.assertEqual((r.status_code, r.get_json()['error']), (400, 'same_password'))
        self.assertIn('다른 비밀번호', r.get_json()['message'])

    def test_update_password_error_codes(self):
        from junhee.server.auth_core import SupabaseAuth, _Response
        auth = SupabaseAuth('https://example-project.supabase.co', 'sb_publishable_test')
        cases = [(422, {'error_code': 'same_password'}, 'same_password'),
                 (422, {'error_code': 'weak_password'}, 'weak_password'),
                 (401, {'error_code': 'reauthentication_needed'}, 'reauthentication_needed'),
                 (401, {'code': 'bad_jwt'}, 'invalid_session'),
                 (422, {}, 'password_update_failed'),
                 (429, {}, 'rate_limited'),
                 (500, {}, 'unavailable')]
        for status, payload, code in cases:
            res = _Response(status, {}, __import__('json').dumps(payload).encode())
            with mock.patch.object(auth, '_send', return_value=res) as send:
                with self.assertRaises(self.acc.AuthError) as ctx:
                    auth.update_password('tok', 'NewPassw0rd!')
                self.assertEqual(ctx.exception.code, code)
                self.assertEqual(send.call_args[0][:2], ('PUT', '/user'))
        ok = _Response(200, {}, b'{"id": "u"}')
        with mock.patch.object(auth, '_send', return_value=ok):
            self.assertEqual(auth.update_password('tok', 'NewPassw0rd!'), {'id': 'u'})

    def test_invalid_confirm_link(self):
        r = self.c.get('/auth/confirm?token_hash=zz&type=email')
        r = self.c.get(r.headers['Location'])
        self.assertIn('유효하지 않거나 만료', r.get_data(as_text=True))
        self.provider.confirm_email.assert_not_called()


if __name__ == '__main__':
    unittest.main()
