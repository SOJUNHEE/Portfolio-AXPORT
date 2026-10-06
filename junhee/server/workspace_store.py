# -*- coding: utf-8 -*-
"""(junhee) 2026-09-27 계정별 바탕화면 저장(파일·폴더·아이콘 위치·파일별 분석 조건·마지막 분석).

sanghyeob/workspace_store.py 의 방식(Supabase PostgREST + 사용자 JWT + RLS, revision 비교 저장)을 따르되,
junhee 화면 구조(아이콘 cell 번호, 샘플 파일 id)에 맞춰 '바탕화면 상태 문서 1개'를 통째로 저장한다.
원본 엑셀 파일 내용은 여기에 저장하지 않는다.

(2026-10-05) 로그인하지 않은 방문자(세션 visitor_id)는 Supabase 대신 서버 SQLite(instance/visitor-workspaces.sqlite3)에
같은 revision 규칙으로 저장한다(LocalWorkspaceRepository). 로그인 사용자는 기존처럼 Supabase 에 저장한다.

API:
  GET /api/workspace          → {revision, state}    (처음이면 revision 0, state null → 화면 기본값 사용)
  PUT /api/workspace          ← {revision, state}    → {revision}   (다른 탭이 먼저 저장했으면 409 + 최신 상태)
"""
import json
from pathlib import Path
import re
import sqlite3
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request

from flask import Blueprint, current_app, jsonify, request

from .accounts import access_token, csrf_ok, request_user
from .auth_core import _OPENER

MAX_ITEMS = 500
MAX_STATE_BYTES = 512 * 1024
MAX_CELL = 5000
ID = re.compile(r'[A-Za-z0-9_:-]{1,80}')
CONDITION_KEYS = {'company', 'hs', 'country', 'file', 'fileId', 'period'}
SYSTEM_ICONS = ('analysis', 'trash', 'upload', 'company-file')  # (junhee) 2026-09-27 기업 파일 업로드 아이콘 추가


class WorkspaceError(Exception):
    """브라우저에는 안전한 오류 코드만 돌려준다."""

    def __init__(self, code, status=400):
        super().__init__(code)
        self.code, self.status = code, status


class SupabaseRest:
    """상태 없는 PostgREST 통신. 사용자의 access token 으로 요청하므로 RLS 가 본인 행만 허용한다."""

    def __init__(self, url, publishable_key):
        self.base_url = url.rstrip('/') + '/rest/v1'
        self.publishable_key = publishable_key

    def request(self, method, path, token, *, params=None, data=None):
        url = self.base_url + path + ('?' + urlencode(params) if params else '')
        headers = {'apikey': self.publishable_key, 'Authorization': 'Bearer ' + token, 'Accept': 'application/json'}
        body = None
        if data is not None:
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        try:
            with _OPENER.open(Request(url, data=body, headers=headers, method=method), timeout=10) as res:
                status, raw = res.status, res.read(4 * 1024 * 1024)
        except HTTPError as exc:
            try:
                status, raw = exc.code, exc.read(64 * 1024)
            finally:
                exc.close()
        except (URLError, OSError, ValueError):
            raise WorkspaceError('unavailable', 503) from None
        try:
            payload = json.loads(raw.decode('utf-8')) if raw else None
        except ValueError:
            payload = None
        code = payload.get('code') if isinstance(payload, dict) else None
        if status == 409 or code == 'PT409':
            raise WorkspaceError('conflict', 409)
        if code in ('PGRST202', 'PGRST205', '42P01', '42883') or status == 404:
            raise WorkspaceError('setup_required', 503)  # SQL 마이그레이션을 아직 적용하지 않음
        if status == 401:
            raise WorkspaceError('authentication_required', 401)
        if status == 403:
            raise WorkspaceError('setup_required', 503)
        if code == 'PT400' or status == 400:
            raise WorkspaceError('invalid', 400)
        if not 200 <= status < 300:
            raise WorkspaceError('unavailable', 503)
        return payload


class WorkspaceRepository:
    def __init__(self, rest):
        self.rest = rest

    def load(self, user_id, token):
        rows = self.rest.request('GET', '/axport_workspaces', token,
                                 params={'user_id': 'eq.' + user_id, 'select': 'user_id,revision,state', 'limit': '1'})
        if not isinstance(rows, list):
            raise WorkspaceError('unavailable', 503)
        return rows[0] if rows else None

    def save(self, user_id, token, state, revision):
        # RPC 는 소유자 인자를 받지 않는다. auth.uid() 가 유일한 소유자 근거.
        rows = self.rest.request('POST', '/rpc/save_axport_workspace', token,
                                 data={'p_expected_revision': revision, 'p_state': state})
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict) or rows[0].get('user_id') != user_id:
            raise WorkspaceError('unavailable', 503)
        return rows[0]


class LocalWorkspaceRepository:
    """(2026-10-05) 방문자 바탕화면 저장소. WorkspaceRepository 와 같은 load/save·revision 충돌 규칙(서버 디스크, 재배포 시 사라질 수 있음)."""

    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS visitor_workspaces (user_id TEXT PRIMARY KEY, revision INTEGER NOT NULL, '
                       'state TEXT NOT NULL, updated_at REAL NOT NULL DEFAULT 0)')
            if 'updated_at' not in {r[1] for r in db.execute('PRAGMA table_info(visitor_workspaces)')}:
                db.execute('ALTER TABLE visitor_workspaces ADD COLUMN updated_at REAL NOT NULL DEFAULT 0')  # 10-05 판 DB

    def _db(self):
        return closing_commit(sqlite3.connect(self.path, timeout=10))

    def load(self, user_id, token=None):
        try:
            with self._db() as db:
                row = db.execute('SELECT revision, state FROM visitor_workspaces WHERE user_id=?', (user_id,)).fetchone()
            return {'user_id': user_id, 'revision': row[0], 'state': json.loads(row[1])} if row else None
        except (sqlite3.Error, ValueError):
            raise WorkspaceError('unavailable', 503) from None

    def save(self, user_id, token, state, revision):
        try:
            with self._db() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT revision FROM visitor_workspaces WHERE user_id=?', (user_id,)).fetchone()
                # 행이 없으면(첫 저장, 또는 재시작·보관기간 정리로 서버 기록이 사라진 경우) 열린 창의 상태를 그대로 받는다
                if row and row[0] != revision:
                    raise WorkspaceError('conflict', 409)
                db.execute('INSERT OR REPLACE INTO visitor_workspaces VALUES (?, ?, ?, ?)',
                           (user_id, revision + 1, json.dumps(state, ensure_ascii=False), time.time()))
        except sqlite3.Error:
            raise WorkspaceError('unavailable', 503) from None
        return {'user_id': user_id, 'revision': revision + 1}

    def purge(self, prefix, before):
        """(2026-10-06) 마지막 저장이 before(초) 이전인 방문자 바탕화면을 지운다."""
        with self._db() as db:
            return db.execute('DELETE FROM visitor_workspaces WHERE user_id LIKE ? AND updated_at < ?',
                              (prefix + '%', before)).rowcount


class closing_commit:
    """sqlite3 연결을 with 문에서 커밋(오류면 롤백)한 뒤 닫는다."""

    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        self.conn.isolation_level = None  # BEGIN 을 직접 관리
        return self.conn

    def __exit__(self, exc_type, *_):
        try:
            if self.conn.in_transaction:
                self.conn.execute('ROLLBACK' if exc_type else 'COMMIT')
        finally:
            self.conn.close()
        return False


# ---------- 상태 문서 검증 ----------

def _int(value, lo=0, hi=MAX_CELL):
    return isinstance(value, int) and not isinstance(value, bool) and lo <= value <= hi


def _text(value, limit=200, allow_empty=True):
    if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 for c in value):
        raise WorkspaceError('invalid')
    value = unicodedata.normalize('NFC', value)
    if not allow_empty and not value.strip():
        raise WorkspaceError('invalid')
    return value


def clean_name(value):
    """파일·폴더 표시 이름. 앞뒤 공백 제거, 1~120자, 윈도우 금지 문자·예약어 불가."""
    if not isinstance(value, str):
        raise WorkspaceError('invalid_name')
    value = unicodedata.normalize('NFC', value).strip()
    if (not value or len(value) > 120 or value.endswith('.') or value in ('.', '..')
            or re.search(r'[<>:"/\\|?*\x00-\x1f\x7f]', value)
            or re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', value, re.I)):
        raise WorkspaceError('invalid_name')
    return value


def _id(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise WorkspaceError('invalid')
    return value


def validate_state(state):
    """브라우저가 보낸 바탕화면 상태를 허용 필드만 남겨 다시 만든다. 형식이 틀리면 저장하지 않는다."""
    if not isinstance(state, dict) or state.get('v') != 1 or not isinstance(state.get('items'), list):
        raise WorkspaceError('invalid')
    if len(state['items']) > MAX_ITEMS:
        raise WorkspaceError('limit_reached', 409)
    items, by_id = [], {}
    for raw in state['items']:
        if not isinstance(raw, dict) or raw.get('kind') not in ('file', 'folder'):
            raise WorkspaceError('invalid')
        item = {'id': _id(raw.get('id')), 'kind': raw['kind'], 'name': clean_name(raw.get('name')),
                'trash': raw.get('trash') is True}
        if item['id'] in by_id or item['id'] in SYSTEM_ICONS:
            raise WorkspaceError('invalid')
        if raw.get('cell') is not None:
            if not _int(raw['cell']):
                raise WorkspaceError('invalid')
            item['cell'] = raw['cell']
        if raw.get('parent_id') is not None:
            item['parent_id'] = _id(raw['parent_id'])
        if raw.get('trash_batch') is not None:
            item['trash_batch'] = _id(raw['trash_batch'])
        if item['kind'] == 'file':
            item['source_name'] = clean_name(raw.get('source_name') or raw['name'])
            item['sample'] = raw.get('sample') is True
            item['analyzed'] = raw.get('analyzed') is True
            size = raw.get('size', 0)
            item['size'] = size if _int(size, 0, 1 << 40) else 0
            for key in ('company_id', 'assessment_id', 'source_id'):
                if raw.get(key) is not None:
                    item[key] = _id(raw[key])
            if raw.get('conditions') is not None:
                cond = raw['conditions']
                if not isinstance(cond, dict) or set(cond) - CONDITION_KEYS:
                    raise WorkspaceError('invalid')
                item['conditions'] = {k: (_text(v, 200) if v is not None else None) for k, v in cond.items()}
        by_id[item['id']] = item
        items.append(item)
    # 같은 이름은 거부하지 않는다: junhee 바탕화면은 같은 파일을 다시 올리면 같은 이름 아이콘이 생기는 기존 동작을 유지한다.
    # (사용자가 이름을 정하는 '이름 바꾸기'·'새 폴더' 는 화면에서 같은 위치의 같은 이름을 막는다)
    for item in items:
        parent = by_id.get(item.get('parent_id')) if item.get('parent_id') else None
        if item.get('parent_id') and (parent is None or parent['kind'] != 'folder'):
            raise WorkspaceError('invalid')
        if item['kind'] == 'folder' and item.get('parent_id'):
            raise WorkspaceError('invalid')  # 폴더 안의 폴더는 아직 지원하지 않음
    system = state.get('system') or {}
    if not isinstance(system, dict) or set(system) - set(SYSTEM_ICONS) or not all(_int(v) for v in system.values()):
        raise WorkspaceError('invalid')
    clean = {'v': 1, 'items': items, 'system': dict(system)}
    last = state.get('last')
    if last is not None:
        if not isinstance(last, dict) or set(last) - {'fileId', 'tab', 'country', 'hs'}:
            raise WorkspaceError('invalid')
        clean['last'] = {k: _text(v, 100) for k, v in last.items() if v is not None}
    if len(json.dumps(clean, ensure_ascii=False).encode('utf-8')) > MAX_STATE_BYTES:
        raise WorkspaceError('limit_reached', 409)
    return clean


# ---------- 라우트 ----------

bp = Blueprint('junhee_workspace', __name__)


def _repo(user):
    """로그인 사용자는 Supabase 저장소, 방문자(또는 로그인 설정 없음)는 서버 SQLite 저장소."""
    remote = current_app.extensions['junhee_workspace']
    return current_app.extensions['junhee_workspace_local'] if user.get('visitor') or remote is None else remote


def _fail(exc):
    return jsonify(error=exc.code), exc.status


@bp.before_request
def _guard():
    if request.method not in ('GET', 'HEAD') and not csrf_ok():
        return jsonify(error='csrf_failed'), 403
    return None


@bp.get('/api/workspace')
def get_workspace():
    user = request_user()
    try:
        row = _repo(user).load(user['id'], access_token())
    except WorkspaceError as exc:
        return _fail(exc)
    if not row:
        return jsonify(revision=0, state=None)
    try:
        state = validate_state(row.get('state'))
    except WorkspaceError:
        state = None  # 손상된 문서는 쓰지 않고 기본 바탕화면으로 시작(다음 저장 때 덮어씀)
    return jsonify(revision=row['revision'], state=state)


@bp.put('/api/workspace')
def put_workspace():
    user = request_user()
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not _int(body.get('revision'), 0, 1 << 53):
        return jsonify(error='invalid'), 400
    try:
        state = validate_state(body.get('state'))
        row = _repo(user).save(user['id'], access_token(), state, body['revision'])
    except WorkspaceError as exc:
        if exc.code == 'conflict':
            try:
                latest = _repo(user).load(user['id'], access_token())
            except WorkspaceError:
                latest = None
            return jsonify(error='conflict', revision=(latest or {}).get('revision'), state=(latest or {}).get('state')), 409
        return _fail(exc)
    return jsonify(revision=row['revision'])


def attach_workspace(app):
    """accounts.attach_accounts(app) 다음에 부른다."""
    if app.extensions.get('junhee_workspace'):
        return
    import os
    ext = app.extensions['junhee_accounts']
    if ext['ready']:
        app.extensions['junhee_workspace'] = WorkspaceRepository(
            SupabaseRest(os.environ['SUPABASE_URL'].strip(), os.environ['SUPABASE_PUBLISHABLE_KEY'].strip()))
    else:
        app.extensions['junhee_workspace'] = None
    # (2026-10-05) 방문자 바탕화면(서버 디스크). 테스트는 AXPORT_VISITOR_DB 로 임시 경로를 쓴다
    root = Path(__file__).resolve().parents[2]
    app.extensions['junhee_workspace_local'] = LocalWorkspaceRepository(
        os.environ.get('AXPORT_VISITOR_DB') or root / 'instance' / 'visitor-workspaces.sqlite3')
    app.register_blueprint(bp)
