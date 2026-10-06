# -*- coding: utf-8 -*-
"""(junhee) 2026-09-27 회원가입·이메일 인증·로그인·로그아웃. sanghyeob 의 app.py 인증 라우트를 Blueprint 로 옮겨 온 것.

app.py 에서는 `attach_accounts(app)` 한 줄만 부른다. 기존 라우트(/, /app, /api/contact, /api/chat …)는 바꾸지 않는다.
- (2026-10-05) 로그인 없이 모든 기능을 쓴다: 로그인하지 않은 브라우저는 세션 쿠키의 방문자 id(visitor_id)로 구분하고,
  업로드·분석·바탕화면 저장은 그 id 로 서버 디스크(instance/)에 남는다. 로그인 라우트는 남겨 두지만 화면에서 요구하지 않는다.
- 설정(.env)이 없어도 /app 은 그대로 열린다(임시 세션 키 사용, 서버를 다시 시작하면 방문자 작업은 이어지지 않음).
- 인증 메일은 Supabase 가 보낸다. 메일 계정(SMTP)은 Supabase 대시보드에서 설정하며 이 코드에는 없다.

환경변수(.env / Render Environment): SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, FLASK_SECRET_KEY,
SESSION_COOKIE_SECURE(선택, 기본: Render 면 true), AXPORT_PUBLIC_URL(선택, 인증 메일 링크의 기준 주소).
"""
from collections import deque
from datetime import timedelta
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from urllib.parse import urlsplit

from flask import Blueprint, g, jsonify, redirect, render_template, request, session

from .auth_core import AuthError, ConfirmQueryMiddleware, MailCooldown, SessionStore, SupabaseAuth, public_user

ROOT = Path(__file__).resolve().parents[2]
PROTECTED_PAGES = ('/app', '/_axp_semiconductor/original')  # 두 번째는 minjung 위젯이 만든 원본 워크스페이스 경로
PROTECTED_API = ('/api/workspace', '/api/analysis', '/analysis/')
_EMAIL = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
                    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+")
MAIL_COOLDOWN_SECONDS = 60
# (2026-09-27 배포 QA) 로그인·가입 요청 제한(IP 별, 프로세스 메모리). Supabase 호출이 모두 서버 IP 하나로 나가므로 앱에서 먼저 막는다.
# 발표장처럼 여러 사람이 같은 IP(NAT)를 쓰는 경우를 막지 않도록 넉넉히 둔다(대입·메일 남용만 막는 수준).
AUTH_LIMITS = {'junhee_accounts.login': (60, 300), 'junhee_accounts.signup': (20, 600), 'junhee_accounts.resend': (20, 600),
               'junhee_accounts.change_password': (10, 600)}

bp = Blueprint('junhee_accounts', __name__)


def _load_root_env():
    """루트 .env 만 읽는다. 이미 있는 OS 환경변수가 우선한다(minjung 위젯과 같은 규칙)."""
    path = ROOT / '.env'
    if path.is_file():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            name, sep, value = line.partition('=')
            if sep and name.strip().isidentifier():
                os.environ.setdefault(name.strip(), value.strip().strip('"\''))


def _env_bool(name, default):
    value = os.environ.get(name, '').strip().lower()
    return default if value not in ('true', 'false') else value == 'true'


def _config_problem(url, key, secret):
    if not isinstance(secret, str) or len(secret) < 32:
        return 'FLASK_SECRET_KEY(32자 이상 무작위 문자열)'
    parts = urlsplit(url)
    if (parts.scheme != 'https' or not parts.hostname or parts.username or parts.password
            or parts.query or parts.fragment or parts.path not in ('', '/')):
        return 'SUPABASE_URL(https 프로젝트 주소)'
    if not key.startswith('sb_publishable_'):
        return 'SUPABASE_PUBLISHABLE_KEY(sb_publishable_ 로 시작하는 공개 키. secret/service_role 키는 쓰지 않음)'
    return None


def _ext():
    from flask import current_app
    return current_app.extensions['junhee_accounts']


# ---------- 세션·CSRF 도우미 (다른 junhee 서버 모듈도 사용) ----------

def csrf_token():
    if not isinstance(session.get('csrf_token'), str):
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']


def current_user():
    """로그인 사용자 {'id','email'} 또는 None. 요청마다 한 번만 Supabase 로 확인한다."""
    if 'junhee_user' in g:
        return g.junhee_user
    g.junhee_user, g.junhee_access_token = None, None
    ext = _ext()
    sid = session.get('auth_sid') if ext['ready'] else None
    if sid:
        try:
            g.junhee_user, g.junhee_access_token = ext['sessions'].resolve_credentials(sid, ext['provider'])
        except AuthError as exc:
            if exc.status in (429, 503):
                g.junhee_auth_unavailable = True
            else:
                _clear_local_session()
        except sqlite3.Error:
            g.junhee_auth_unavailable = True
    return g.junhee_user


def access_token():
    current_user()
    return g.get('junhee_access_token')


def request_user():
    """(2026-10-05) 로그인 사용자, 아니면 이 브라우저의 방문자 {'id','email':'','visitor':True}. 항상 값이 있다."""
    user = current_user()
    if user is not None:
        return user
    vid = session.get('visitor_id')
    if not (isinstance(vid, str) and re.fullmatch(r'visitor-[0-9a-f]{32}', vid)):
        vid = session['visitor_id'] = 'visitor-' + secrets.token_hex(16)
        session.permanent = True
    return {'id': vid, 'email': '', 'visitor': True}


def _clear_local_session():
    sid = session.get('auth_sid')
    token = None
    if sid:
        try:
            token = _ext()['sessions'].revoke(sid)
        except sqlite3.Error:
            pass
    session.clear()
    csrf_token()
    g.junhee_user, g.junhee_access_token = None, None
    return token


def csrf_ok():
    supplied = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
    expected = session.get('csrf_token')
    same_origin = True
    for value in (request.headers.get('Origin'), request.headers.get('Referer')):
        if value:
            try:
                src, dst = urlsplit(value), urlsplit(request.host_url)
                same_origin = same_origin and (src.scheme, src.netloc) == (dst.scheme, dst.netloc)
            except ValueError:
                same_origin = False
    return (isinstance(expected, str) and expected and isinstance(supplied, str)
            and secrets.compare_digest(expected.encode(), supplied.encode())
            and same_origin and request.headers.get('Sec-Fetch-Site') != 'cross-site')


# ---------- 로그인 화면 ----------

def _page(status=200, **state):
    base = {'tab': 'login', 'login_email': '', 'login_error': None, 'notice': '', 'signup_email': '',
            'signup_error': None, 'signup_pending': False, 'resend_notice': '', 'resend_error': None,
            'cooldown': 0, 'setup_error': None, 'confirm_state': None}
    base.update(state)
    response = _ext()['app'].make_response((render_template('junhee_login.html', auth=base,
                                                            csrf_token=csrf_token() if _ext()['ready'] else ''), status))
    if status == 429 and base['cooldown']:
        response.headers['Retry-After'] = str(max(1, base['cooldown']))
    return response


def _unavailable():
    return _page(503, login_error='로그인 서비스에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.')


def _auth_limited(endpoint):
    limit, window = AUTH_LIMITS[endpoint]
    now, key = time.monotonic(), (endpoint, request.remote_addr or 'unknown')
    ext = _ext()
    with ext['auth_lock']:
        store = ext['auth_hits']
        if len(store) > 5000:  # 오래된 기록 정리(메모리 상한)
            for k in [k for k, q in store.items() if not q or now - q[-1] > 600]:
                store.pop(k, None)
        hits = store.setdefault(key, deque())
        while hits and now - hits[0] > window:
            hits.popleft()
        if len(hits) >= limit:
            return int(window - (now - hits[0])) + 1
        hits.append(now)
    return 0


# ---------- 라우트 ----------

@bp.before_request
def _bp_guard():
    if not _ext()['ready']:
        if request.path.startswith('/api/'):
            return jsonify(error='auth_not_configured'), 503
        return _page(503, setup_error=_ext()['problem'])
    if request.method == 'POST' and request.endpoint in AUTH_LIMITS:
        wait = _auth_limited(request.endpoint)
        if wait and request.path.startswith('/api/'):
            response = jsonify(error='rate_limited')
            response.status_code = 429
            response.headers['Retry-After'] = str(wait)
            return response
        if wait:
            tab = 'login' if request.endpoint == 'junhee_accounts.login' else 'signup'
            message = '요청이 많습니다. 잠시 후 다시 시도해 주세요.'
            response = _page(429, tab=tab, login_error=message if tab == 'login' else None,
                             signup_error=message if tab == 'signup' else None)
            response.headers['Retry-After'] = str(wait)
            return response
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and not csrf_ok():
        if request.path.startswith('/api/'):
            return jsonify(error='csrf_failed'), 403
        tab = 'signup' if request.endpoint in ('junhee_accounts.signup', 'junhee_accounts.resend') else 'login'
        return _page(403, tab=tab, login_error='요청이 만료되었습니다. 화면을 새로고침한 뒤 다시 시도해 주세요.',
                     signup_error='요청이 만료되었습니다. 화면을 새로고침한 뒤 다시 시도해 주세요.' if tab == 'signup' else None)
    return None


@bp.post('/auth/login')
def login():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    if not email or '@' not in email or len(email) > 254 or not password or len(password) > 4096:
        return _page(400, login_error='이메일과 비밀번호를 확인해 주세요.', login_email=email[:254])
    ext = _ext()
    try:
        tokens = ext['provider'].sign_in(email, password)
        user = public_user(ext['provider'].get_user(tokens.get('access_token', '')))
        new_sid = ext['sessions'].create(tokens, user)
    except AuthError as exc:
        if exc.status == 503:
            return _unavailable()
        error = ('요청이 많습니다. 잠시 후 다시 시도해 주세요.' if exc.status == 429
                 else '로그인하지 못했습니다. 이메일·비밀번호와 이메일 인증 여부를 확인해 주세요.')
        return _page(exc.status, login_error=error, login_email=email)
    except sqlite3.Error:
        return _unavailable()
    old_token = _clear_local_session()
    session['auth_sid'] = new_sid
    session.permanent = True
    if old_token:
        try:
            ext['provider'].sign_out(old_token)
        except AuthError:
            pass
    return redirect('/app', code=303)


@bp.post('/auth/logout')
def logout():
    token = _clear_local_session()
    if token:
        try:
            _ext()['provider'].sign_out(token)
        except AuthError as exc:
            if exc.status in (429, 503):
                return redirect('/app?auth=logout_pending', code=303)
    return redirect('/app?auth=logged_out', code=303)


def _callback_url():
    base = os.environ.get('AXPORT_PUBLIC_URL', '').strip().rstrip('/') or request.host_url.rstrip('/')
    return base + '/auth/confirm'


def _signup_mail(email, password=None):
    """password 가 None 이면 인증 메일 재발송."""
    ext = _ext()
    cooldowns, resending = ext['cooldown'], password is None
    try:
        remaining = cooldowns.reserve(email)
        if remaining:
            return _page(429, tab='signup', signup_email=email, signup_pending=True, cooldown=remaining,
                         resend_error='잠시 후 인증 메일을 다시 요청해 주세요.')
        if resending:
            ext['provider'].resend_signup(email, _callback_url())
        else:
            result = ext['provider'].sign_up(email, password, _callback_url())
            if result.get('access_token'):
                # Supabase 의 'Confirm email' 이 꺼져 있으면 가입 즉시 세션이 온다. 설치하지 않고 폐기한다.
                try:
                    ext['provider'].sign_out(result['access_token'])
                except AuthError:
                    pass
                return _page(503, tab='signup', signup_email=email,
                             signup_error='이메일 인증 설정(Confirm email)을 확인해야 합니다. 관리자에게 문의해 주세요.')
    except AuthError as exc:
        if exc.code not in ('email_exists', 'user_already_exists', 'user_not_found'):
            if exc.status == 429:
                remaining = cooldowns.extend(email, exc.retry_after)
                message = '요청이 많습니다. 잠시 후 다시 시도해 주세요.'
                return _page(429, tab='signup', signup_email=email, signup_pending=resending, cooldown=remaining,
                             signup_error=None if resending else message, resend_error=message if resending else None)
            messages = {
                'weak_password': '비밀번호가 보안 조건을 충족하지 않습니다. 더 길게, 대문자·소문자·숫자·기호를 섞어 다시 입력해 주세요.',
                'email_address_invalid': '올바른 이메일 주소를 입력해 주세요.',
                'signup_disabled': '현재 회원가입을 이용할 수 없습니다. 관리자에게 문의해 주세요.',
                'email_address_not_authorized': '현재 메일 발송 설정으로 이 주소에 인증 메일을 보낼 수 없습니다. 관리자에게 문의해 주세요.',
                'email_send_failed': '인증 메일을 보내지 못했습니다. 잠시 후 다시 시도해 주세요.',
                'signup_failed': '입력 내용을 확인한 뒤 다시 시도해 주세요.',
            }
            if exc.code in ('weak_password', 'email_address_invalid', 'signup_disabled', 'email_address_not_authorized'):
                cooldowns.release(email)
                remaining = 0
            else:
                remaining = MAIL_COOLDOWN_SECONDS
            message = messages.get(exc.code, '인증 서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.')
            return _page(exc.status, tab='signup', signup_email=email, signup_pending=resending, cooldown=remaining,
                         signup_error=None if resending else message, resend_error=message if resending else None)
        # 이미 가입된 주소도 같은 안내를 보여 준다(가입 여부를 드러내지 않음).
    except sqlite3.Error:
        return _page(503, tab='signup', signup_email=email, signup_error='요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.')
    return _page(tab='signup', signup_email=email, signup_pending=True, cooldown=MAIL_COOLDOWN_SECONDS,
                 resend_notice='해당 이메일로 인증이 필요한 경우 메일이 발송됩니다. 받은편지함을 확인해 주세요.' if resending else '')


@bp.post('/auth/signup')
def signup():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    confirmation = request.form.get('password_confirm', '')
    if not (len(email) <= 254 and _EMAIL.fullmatch(email)):
        return _page(400, tab='signup', signup_email=email[:254], signup_error='올바른 이메일 주소를 입력해 주세요.')
    if password != confirmation:
        return _page(400, tab='signup', signup_email=email, signup_error='비밀번호와 비밀번호 확인이 일치하지 않습니다.')
    if not 8 <= len(password) <= 128:
        return _page(400, tab='signup', signup_email=email, signup_error='비밀번호는 8자 이상 128자 이하로 입력해 주세요.')
    return _signup_mail(email, password)


@bp.post('/auth/resend')
def resend():
    email = request.form.get('email', '').strip()
    if not (len(email) <= 254 and _EMAIL.fullmatch(email)):
        return _page(400, tab='signup', signup_email=email[:254], signup_pending=True,
                     resend_error='올바른 이메일 주소를 입력해 주세요.')
    return _signup_mail(email)


@bp.get('/auth/confirm')
def confirm_email():
    pairs = request.environ.pop('axport.confirm_query', [])
    values = dict(pairs)
    state = 'invalid'
    if (len(pairs) == 2 and set(values) == {'token_hash', 'type'} and values['type'] == 'email'
            and re.fullmatch(r'[0-9a-fA-F]{32,256}', values['token_hash'])):
        provider = _ext()['provider']
        try:
            result = provider.confirm_email(values['token_hash'])
            user = result.get('user') or {}
            public_user(user)
            if user.get('email_confirmed_at') and isinstance(result.get('access_token'), str) and result['access_token']:
                state = 'success'
                try:  # 인증만 하고 자동 로그인은 하지 않는다
                    provider.sign_out(result['access_token'])
                except AuthError:
                    pass
        except AuthError as exc:
            if exc.status in (429, 503):
                state = 'unavailable'
    session['signup_confirmation_result'] = state
    return redirect('/auth/confirm/result', code=303)


@bp.get('/auth/confirm/result')
def confirm_result():
    state = session.pop('signup_confirmation_result', 'invalid')
    messages = {
        'success': '이메일 인증이 완료되었습니다. 이제 로그인할 수 있습니다.',
        'invalid': '인증 링크가 유효하지 않거나 만료되었습니다. 이미 인증했다면 로그인해 주세요. 아니라면 인증 메일을 다시 요청해 주세요.',
        'unavailable': '인증 서버에 연결하지 못했습니다. 잠시 후 메일의 링크를 다시 열어 주세요.',
    }
    state = state if state in messages else 'invalid'
    return _page(confirm_state=state, notice=messages[state])


@bp.get('/api/auth/session')
def auth_session():
    user = current_user()
    if user is None:
        return jsonify(error='authentication_required'), 401
    return jsonify(user=user)


@bp.post('/api/auth/password')
def change_password():
    """(2026-09-29) 계정 창의 비밀번호 변경. 로그인 세션만 확인하고 메일 인증 없이 바로 바꾼다. 현재 로그인은 유지."""
    user = current_user()
    if user is None:
        if g.get('junhee_auth_unavailable'):
            return jsonify(error='auth_unavailable'), 503
        return jsonify(error='authentication_required'), 401
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    password, confirmation = data.get('password'), data.get('password_confirm')
    if not isinstance(password, str) or not isinstance(confirmation, str):
        return jsonify(error='invalid_request', message='새 비밀번호를 입력해 주세요.'), 400
    if password != confirmation:
        return jsonify(error='password_mismatch', message='새 비밀번호와 비밀번호 확인이 일치하지 않습니다.'), 400
    if not 8 <= len(password) <= 128:
        return jsonify(error='password_length', message='비밀번호는 8자 이상 128자 이하로 입력해 주세요.'), 400
    try:
        _ext()['provider'].update_password(access_token(), password)
    except AuthError as exc:
        messages = {
            'weak_password': '비밀번호가 보안 조건을 충족하지 않습니다. 더 길게, 대문자·소문자·숫자·기호를 섞어 다시 입력해 주세요.',
            'same_password': '지금 쓰는 비밀번호와 다른 비밀번호를 입력해 주세요.',
            'reauthentication_needed': '로그인한 지 오래되어 바로 바꿀 수 없습니다. 로그아웃 후 다시 로그인한 뒤 바꿔 주세요.',
            'invalid_session': '로그인이 만료되었습니다. 다시 로그인해 주세요.',
            'rate_limited': '요청이 많습니다. 잠시 후 다시 시도해 주세요.',
            'password_update_failed': '비밀번호를 바꾸지 못했습니다. 입력 내용을 확인해 주세요.',
        }
        return jsonify(error=exc.code, message=messages.get(exc.code, '인증 서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.')), exc.status
    return jsonify(ok=True, message='비밀번호를 바꿨습니다. 다음 로그인부터 새 비밀번호를 쓰세요.')


# ---------- 연결 ----------

def attach_accounts(app):
    """app.py 에서 한 번 부른다. 로그인 검사·보안 헤더·세션 쿠키 설정을 붙인다."""
    if app.extensions.get('junhee_accounts'):
        return
    _load_root_env()
    url = os.environ.get('SUPABASE_URL', '').strip()
    key = os.environ.get('SUPABASE_PUBLISHABLE_KEY', '').strip()
    secret = os.environ.get('FLASK_SECRET_KEY', '')
    problem = _config_problem(url, key, secret)
    on_render = bool(os.environ.get('RENDER'))
    ext = {'app': app, 'ready': problem is None, 'problem': problem, 'auth_hits': {}, 'auth_lock': threading.Lock()}
    if on_render or _env_bool('AXPORT_TRUST_PROXY', False):
        # Render 는 TLS 를 앞단 프록시에서 끝낸다. X-Forwarded-Proto/For 를 1단계만 믿는다.
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.wsgi_app = ConfirmQueryMiddleware(app.wsgi_app)
    # (2026-09-27 배포 QA) 전체 요청 본문 상한 2MB. 기업 엑셀 업로드(20MB)·챗봇(120KB)은 각 경로에서 따로 정한다.
    if app.config.get('MAX_CONTENT_LENGTH') is None:  # Flask 기본값 None(무제한)일 때만
        app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
    if problem is not None and not app.config.get('SECRET_KEY'):
        # (2026-10-05) 로그인 설정이 없어도 방문자 세션·CSRF 를 쓴다. FLASK_SECRET_KEY 가 있으면 그 값, 없으면 임시 키(재시작하면 바뀜).
        app.config.update(SECRET_KEY=secret if isinstance(secret, str) and len(secret) >= 32 else secrets.token_hex(32), SESSION_COOKIE_NAME='axport_session', SESSION_COOKIE_HTTPONLY=True,
                          SESSION_COOKIE_SECURE=_env_bool('SESSION_COOKIE_SECURE', on_render), SESSION_COOKIE_SAMESITE='Lax',
                          PERMANENT_SESSION_LIFETIME=timedelta(days=7))
    if problem is None:
        db = os.environ.get('AXPORT_AUTH_DB') or str(ROOT / 'instance' / 'auth-sessions.sqlite3')  # 테스트는 임시 경로
        app.config.update(
            SECRET_KEY=secret, SESSION_COOKIE_NAME='axport_session', SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SECURE=_env_bool('SESSION_COOKIE_SECURE', on_render), SESSION_COOKIE_SAMESITE='Lax',
            SESSION_REFRESH_EACH_REQUEST=False, PERMANENT_SESSION_LIFETIME=timedelta(days=7))
        ext.update(provider=SupabaseAuth(url, key), sessions=SessionStore(db, secret),
                   cooldown=MailCooldown(db, secret, MAIL_COOLDOWN_SECONDS))
    app.extensions['junhee_accounts'] = ext
    app.register_blueprint(bp)
    from .workspace_store import attach_workspace  # 계정별 바탕화면 저장 (/api/workspace)
    attach_workspace(app)
    from .analysis import attach_analysis  # 기업 파일 분석 엔진 (/api/analysis)
    attach_analysis(app)
    from .widget_refresh import start as start_widget_refresh  # (2026-09-27) 위젯 공식 자료 자동 갱신(Render 기본 켜짐)
    start_widget_refresh()

    # (2026-10-05) 로그인 검사(_junhee_login_gate)는 뺐다. /app 과 분석·바탕화면 API 는 방문자도 쓴다(request_user()).

    @app.context_processor
    def _junhee_account_context():
        if request.path not in PROTECTED_PAGES:
            return {}
        return {'junhee_user': request_user(), 'junhee_csrf': csrf_token()}

    @app.after_request
    def _junhee_security_headers(response):
        # (2026-09-27 배포 QA) 모든 응답의 기본 보안 헤더(이미 정한 값은 덮어쓰지 않음). HTTPS(Render)면 HSTS.
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'same-origin')
        if request.is_secure:
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000')
        if request.path in PROTECTED_PAGES or request.path.startswith(('/auth/', '/api/auth/') + PROTECTED_API):
            response.headers['Cache-Control'] = 'private, no-store'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            # 토큰이 주소에 오는 /auth/confirm 만 no-referrer. 결과 화면까지 no-referrer 면 그 화면의 로그인 폼이 Origin: null 로 가서 CSRF 에 막힌다.
            response.headers['Referrer-Policy'] = 'no-referrer' if request.path == '/auth/confirm' else 'same-origin'
        return response
