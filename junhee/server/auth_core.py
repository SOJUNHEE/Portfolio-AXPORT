# -*- coding: utf-8 -*-
"""(junhee) 2026-09-27 Supabase 인증 통신 + 서버 쪽 세션 보관. sanghyeob/auth.py·auth_signup.py 를 옮겨 온 것.

- 브라우저 쿠키에는 무작위 세션 ID 만 둔다. access/refresh 토큰은 instance/ SQLite 에 암호화(Fernet)해 보관한다.
- 비밀번호는 저장하지 않는다. Supabase 응답 본문·토큰은 오류 메시지로 내보내지 않는다(오류 코드만).
- HTTP 는 표준 urllib 로 보낸다(requests 의존 없음).
"""
import base64
from contextlib import contextmanager
import hashlib
import hmac
import json
import math
from pathlib import Path
import secrets
import sqlite3
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class AuthError(Exception):
    """오류 코드만 담는다. 상대 서버의 본문·자격 정보·토큰은 담지 않는다."""

    def __init__(self, code, status=401, *, retry_after=None):
        super().__init__(code)
        self.code = code
        self.status = status
        self.retry_after = retry_after


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # 리다이렉트를 따라가지 않고 HTTPError 로 받는다


_OPENER = build_opener(_NoRedirect)


class _Response:
    def __init__(self, status, headers, body):
        self.status_code, self.headers, self._body = status, headers, body

    def json(self):
        return json.loads(self._body.decode('utf-8'))


class SupabaseAuth:
    """상태를 갖지 않는다. 토큰은 요청마다 명시적으로 넘긴다."""

    def __init__(self, url, publishable_key):
        self.base_url = url.rstrip('/') + '/auth/v1'
        self.publishable_key = publishable_key

    @staticmethod
    def _registration_error(response, context):
        # Supabase 판본에 따라 error_code 또는 code. 자유 문구로 분류하지 않는다.
        try:
            body = response.json()
        except ValueError:
            body = None
        code = None
        if isinstance(body, dict):
            for field in ('error_code', 'code'):
                if isinstance(body.get(field), str):
                    code = body[field]
                    break
        if response.status_code == 429 or code in ('over_email_send_rate_limit', 'over_request_rate_limit'):
            header = (response.headers.get('Retry-After') or '').strip()
            retry_after = min(3600, max(1, int(header))) if header.isascii() and header.isdecimal() and len(header) <= 9 else None
            raise AuthError('rate_limited', 429, retry_after=retry_after)
        if context == 'confirmation':
            if code == 'otp_expired':
                raise AuthError('otp_expired', 400)
            if response.status_code in (400, 401, 403, 404, 422):
                raise AuthError('invalid_confirmation', 400)
        elif context == 'password':
            # reauthentication_needed: Supabase 'Secure password change' 가 켜져 있고 로그인한 지 24시간이 지난 경우
            if code in ('weak_password', 'same_password', 'reauthentication_needed'):
                raise AuthError(code, 400)
            if response.status_code in (401, 403):
                raise AuthError('invalid_session', 401)
            if response.status_code in (400, 404, 422):
                raise AuthError('password_update_failed', 400)
        else:
            if code in ('weak_password', 'email_address_invalid', 'email_exists', 'user_already_exists', 'user_not_found'):
                raise AuthError(code, 400)
            if code in ('signup_disabled', 'email_provider_disabled'):
                raise AuthError('signup_disabled', 503)
            if code == 'email_address_not_authorized':
                raise AuthError('email_address_not_authorized', 503)
            if code in ('email_send_failed', 'hook_timeout', 'hook_timeout_after_retry',
                        'hook_payload_invalid_content_type', 'hook_payload_over_size_limit'):
                raise AuthError('email_send_failed', 503)
            if response.status_code in (400, 401, 403, 404, 422):
                raise AuthError('signup_failed', 400)
        raise AuthError('unavailable', 503)

    def _send(self, method, path, data=None, token=None):
        headers = {'apikey': self.publishable_key, 'Accept': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        body = None
        if data is not None:
            body = json.dumps(data).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        req = Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with _OPENER.open(req, timeout=8) as res:
                return _Response(res.status, res.headers, res.read(1024 * 1024))
        except HTTPError as exc:
            try:
                return _Response(exc.code, exc.headers, exc.read(1024 * 1024))
            finally:
                exc.close()
        except (URLError, OSError, ValueError):
            raise AuthError('unavailable', 503) from None

    def _request(self, method, path, *, data=None, token=None, error_context=None):
        response = self._send(method, path, data, token)
        if error_context and not 200 <= response.status_code < 300:
            self._registration_error(response, error_context)
        if response.status_code == 429:
            raise AuthError('rate_limited', 429)
        if response.status_code in (400, 401, 403, 422):
            raise AuthError('invalid_credentials', 401)
        if not 200 <= response.status_code < 300:
            raise AuthError('unavailable', 503)
        if response.status_code == 204:
            return {} if error_context else None
        try:
            result = response.json()
        except ValueError:
            raise AuthError('unavailable', 503) from None
        if not isinstance(result, dict):
            raise AuthError('unavailable', 503)
        return result

    def sign_in(self, email, password):
        return self._request('POST', '/token?grant_type=password', data={'email': email, 'password': password})

    def sign_up(self, email, password, redirect_to):
        """이메일 가입. 돌아온 세션이 있어도 호출한 쪽에서 저장하지 않는다."""
        return self._request('POST', '/signup?' + urlencode({'redirect_to': redirect_to}),
                             data={'email': email, 'password': password}, error_context='signup')

    def resend_signup(self, email, redirect_to):
        return self._request('POST', '/resend?' + urlencode({'redirect_to': redirect_to}),
                             data={'type': 'signup', 'email': email}, error_context='resend')

    def confirm_email(self, token_hash):
        return self._request('POST', '/verify', data={'token_hash': token_hash, 'type': 'email'},
                             error_context='confirmation')

    def get_user(self, access_token):
        return self._request('GET', '/user', token=access_token)

    def update_password(self, access_token, password):
        """(2026-09-29) 로그인한 사용자의 비밀번호를 바로 바꾼다(메일 인증 없음). 현재 세션은 유지된다."""
        return self._request('PUT', '/user', data={'password': password}, token=access_token, error_context='password')

    def refresh(self, refresh_token):
        return self._request('POST', '/token?grant_type=refresh_token', data={'refresh_token': refresh_token})

    def sign_out(self, access_token):
        # 다른 브라우저·기기의 로그인은 그대로 둔다.
        self._request('POST', '/logout?scope=local', token=access_token)


def public_user(user):
    if (not isinstance(user, dict) or not isinstance(user.get('id'), str) or not user['id']
            or not isinstance(user.get('email'), str) or not user['email']):
        raise AuthError('invalid_session')
    return {'id': user['id'], 'email': user['email']}


class SessionStore:
    """단일 서버용 SQLite 세션 저장소. 토큰 갱신 중에만 쓰기 잠금을 잡는다."""

    def __init__(self, path, secret_key, ttl=604800, refresh_margin=60):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl
        self.refresh_margin = refresh_margin
        key = HKDF(algorithm=hashes.SHA256(), length=32, salt=b'axport-auth-session-v1',
                   info=b'server-token-encryption').derive(secret_key.encode('utf-8'))
        self.cipher = Fernet(base64.urlsafe_b64encode(key))
        with self._connect() as conn:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('CREATE TABLE IF NOT EXISTS auth_sessions (sid_hash TEXT PRIMARY KEY, token_box TEXT NOT NULL, '
                         'access_expires_at REAL NOT NULL, expires_at REAL NOT NULL)')
            conn.execute('DELETE FROM auth_sessions WHERE expires_at <= ?', (time.time(),))

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @staticmethod
    def _key(sid):
        if not isinstance(sid, str) or not 32 <= len(sid) <= 128:
            raise AuthError('invalid_session')
        return hashlib.sha256(sid.encode('utf-8')).hexdigest()

    def _pack(self, tokens, user_id):
        if not isinstance(tokens, dict):
            raise AuthError('unavailable', 503)
        access, refresh = tokens.get('access_token'), tokens.get('refresh_token')
        if not isinstance(access, str) or not access or not isinstance(refresh, str) or not refresh:
            raise AuthError('unavailable', 503)
        try:
            lifetime = float(tokens['expires_in'])
            if not 0 < lifetime <= 604800:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise AuthError('unavailable', 503) from None
        box = self.cipher.encrypt(json.dumps({'access_token': access, 'refresh_token': refresh,
                                              'user_id': user_id}).encode('utf-8')).decode('ascii')
        return box, time.time() + lifetime

    def _unpack(self, row):
        try:
            return json.loads(self.cipher.decrypt(row['token_box'].encode('ascii')))
        except (InvalidToken, ValueError, KeyError, TypeError):
            raise AuthError('invalid_session') from None

    def create(self, tokens, user):
        user = public_user(user)
        box, access_expires = self._pack(tokens, user['id'])
        sid = secrets.token_urlsafe(32)
        now = time.time()
        with self._connect() as conn:
            conn.execute('DELETE FROM auth_sessions WHERE expires_at <= ?', (now,))
            conn.execute('INSERT INTO auth_sessions VALUES (?, ?, ?, ?)', (self._key(sid), box, access_expires, now + self.ttl))
        return sid

    def _read(self, sid):
        with self._connect() as conn:
            row = conn.execute('SELECT * FROM auth_sessions WHERE sid_hash = ?', (self._key(sid),)).fetchone()
        if row is None or row['expires_at'] <= time.time():
            self.revoke(sid)
            raise AuthError('expired')
        return row

    def _refresh_if_needed(self, sid, provider):
        with self._connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT * FROM auth_sessions WHERE sid_hash = ?', (self._key(sid),)).fetchone()
            if row is None or row['expires_at'] <= time.time():
                raise AuthError('expired')
            if row['access_expires_at'] > time.time() + self.refresh_margin:
                return self._unpack(row)
            previous = self._unpack(row)
            tokens = provider.refresh(previous['refresh_token'])
            if public_user(tokens.get('user'))['id'] != previous['user_id']:
                raise AuthError('invalid_session')
            box, expires = self._pack(tokens, previous['user_id'])
            conn.execute('UPDATE auth_sessions SET token_box = ?, access_expires_at = ? WHERE sid_hash = ?',
                         (box, expires, self._key(sid)))
            # 앱 세션의 절대 만료 시각은 토큰 갱신으로 늘리지 않는다.
            return {'access_token': tokens['access_token'], 'refresh_token': tokens['refresh_token'],
                    'user_id': previous['user_id']}

    def resolve_credentials(self, sid, provider):
        """확인된 사용자와 서버 전용 access token 을 돌려준다. 토큰은 쿠키·화면으로 나가지 않는다."""
        row = self._read(sid)
        state = self._unpack(row)
        if row['access_expires_at'] <= time.time() + self.refresh_margin:
            state = self._refresh_if_needed(sid, provider)
        user = public_user(provider.get_user(state['access_token']))
        if user['id'] != state['user_id']:
            raise AuthError('invalid_session')
        self._read(sid)  # 동시에 로그아웃했으면 로그아웃이 이긴다
        return user, state['access_token']

    def revoke(self, sid):
        try:
            key = self._key(sid)
        except AuthError:
            return None
        with self._connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT * FROM auth_sessions WHERE sid_hash = ?', (key,)).fetchone()
            conn.execute('DELETE FROM auth_sessions WHERE sid_hash = ?', (key,))
        if row is not None:
            try:
                return self._unpack(row)['access_token']
            except AuthError:
                pass
        return None


class MailCooldown:
    """인증 메일 재요청 간격(기본 60초). 이메일은 HMAC 으로만 기록한다."""

    def __init__(self, database, secret, seconds=60):
        self.database = database
        self.secret = secret.encode('utf-8')
        self.seconds = max(1, int(seconds))
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS auth_mail_cooldowns (email_key TEXT PRIMARY KEY, available_at REAL NOT NULL)')

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def _key(self, email):
        return hmac.new(self.secret, ('signup-mail:' + email.strip().casefold()).encode('utf-8'), hashlib.sha256).hexdigest()

    def reserve(self, email):
        now = time.time()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM auth_mail_cooldowns WHERE available_at <= ?', (now,))
            row = db.execute('SELECT available_at FROM auth_mail_cooldowns WHERE email_key = ?', (self._key(email),)).fetchone()
            if row:
                return max(1, math.ceil(row[0] - now))
            db.execute('INSERT INTO auth_mail_cooldowns VALUES (?, ?)', (self._key(email), now + self.seconds))
        return 0

    def extend(self, email, seconds):
        seconds = max(self.seconds, min(3600, int(seconds or self.seconds)))
        with self._connect() as db:
            db.execute('INSERT INTO auth_mail_cooldowns VALUES (?, ?) ON CONFLICT(email_key) DO UPDATE SET '
                       'available_at = MAX(available_at, excluded.available_at)', (self._key(email), time.time() + seconds))
        return seconds

    def release(self, email):
        with self._connect() as db:
            db.execute('DELETE FROM auth_mail_cooldowns WHERE email_key = ?', (self._key(email),))


class ConfirmQueryMiddleware:
    """/auth/confirm 의 token_hash 가 로그·오류 화면에 남지 않도록 Flask 보다 먼저 쿼리를 떼어 둔다."""

    def __init__(self, application):
        self.application = application

    def __call__(self, environ, start_response):
        if environ.get('PATH_INFO') == '/auth/confirm':
            try:
                pairs = parse_qsl(environ.get('QUERY_STRING', ''), keep_blank_values=True,
                                  max_num_fields=4, encoding='utf-8', errors='strict')
            except (ValueError, UnicodeError):
                pairs = []
            environ['axport.confirm_query'] = pairs
            environ['QUERY_STRING'] = ''
            for key in ('RAW_URI', 'REQUEST_URI'):
                if key in environ:
                    environ[key] = '/auth/confirm'
        return self.application(environ, start_response)
