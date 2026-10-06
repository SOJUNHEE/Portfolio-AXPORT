# -*- coding: utf-8 -*-
"""(2026-10-06 공개 데모) 로그인 없이 쓰는 방문자가 서버 자원을 소진하지 못하게 막는 장치.

로그인이 빠지면 방문자 id 는 쿠키를 지우는 것만으로 새로 생기므로, 계정별 한도(원본 30개·진행 중 분석 1개)만으로는
공개 서버를 지킬 수 없다. 그래서 다음을 더한다.
- IP 별 요청 횟수 제한(업로드·분석 요청·결측 확인·그 밖의 저장/삭제)
- 방문자 업로드 크기 상한(5 MB)과 동시에 엑셀을 해석하는 작업 수 상한(2개, 무료 서버 메모리 보호).
  해석 자리는 요청 본문을 다 받은 뒤 실제 해석하는 동안에만 잡는다(느린 업로드가 자리를 붙잡지 않게).
- 방문자 데이터(업로드 원본·분석 결과) 전체 용량 상한(300 MB)
- 마지막 사용 후 7일이 지난 방문자 데이터(원본·분석·바탕화면·업로드 파일) 자동 삭제(1시간에 한 번, 별도 스레드)
- 공개 데모 응답에 검색엔진 수집 금지(robots.txt·X-Robots-Tag)와 보안 헤더
"""
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import logging
import os
import threading
import time

from flask import current_app, jsonify, request

from .accounts import request_user
from .engine.market_service import MarketError

log = logging.getLogger(__name__)

VISITOR_PREFIX = 'visitor-'
VISITOR_MAX_UPLOAD = 5 * 1024 * 1024
VISITOR_TOTAL_BYTES = 300 * 1024 * 1024
RETENTION = timedelta(days=7)
UPLOAD_PATHS = ('/api/analysis/sources', '/api/analysis/company-files')
LIMITS = {'upload': (10, 600), 'analyze': (20, 600), 'inspect': (60, 600), 'write': (300, 600)}  # (요청 수, 초) IP 별
PARSE_SLOTS = 2
PARSE_WAIT = 3  # 초. 자리가 없으면 오래 기다리지 않고 429
SEEN_EVERY = 3600  # 방문자 마지막 사용 시각 기록 간격(초)
ROBOTS = 'User-agent: *\nDisallow: /\n'
SECURITY_HEADERS = {
    'X-Robots-Tag': 'noindex, nofollow, noarchive, nosnippet, noimageindex',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
    'Cross-Origin-Opener-Policy': 'same-origin',
}


def _bucket(path, method):
    if method == 'POST' and path in UPLOAD_PATHS:
        return 'upload'
    if method == 'POST' and path == '/api/analysis/assessments':
        return 'analyze'
    if method == 'GET' and path == '/api/analysis/inspect':
        return 'inspect'
    if method in ('POST', 'PUT', 'DELETE'):
        return 'write'
    return None


@contextmanager
def parse_slot():
    """엑셀 해석 등 메모리를 많이 쓰는 작업을 동시에 PARSE_SLOTS 개까지만 허용한다."""
    state = current_app.extensions.get('junhee_visitor_guard')
    if state is None:
        yield
        return
    if not state['parse'].acquire(timeout=PARSE_WAIT):
        raise MarketError('analysis_busy', '다른 파일을 처리 중입니다. 잠시 후 다시 시도해 주세요.', 429)
    try:
        yield
    finally:
        state['parse'].release()


def attach_visitor_guard(app):
    if app.extensions.get('junhee_visitor_guard'):
        return
    state = {'hits': {}, 'lock': threading.Lock(), 'parse': threading.BoundedSemaphore(PARSE_SLOTS),
             'purge_lock': threading.Lock(), 'last_purge': 0.0, 'seen': {}}
    app.extensions['junhee_visitor_guard'] = state

    def limited(kind):
        limit, window = LIMITS[kind]
        now, key = time.monotonic(), (kind, request.remote_addr or 'unknown')
        with state['lock']:
            store = state['hits']
            if len(store) > 5000:
                for k in [k for k, q in store.items() if not q or now - q[-1] > 600]:
                    store.pop(k, None)
            hits = store.setdefault(key, deque())
            while hits and now - hits[0] > window:
                hits.popleft()
            if len(hits) >= limit:
                return int(window - (now - hits[0])) + 1
            hits.append(now)
        return 0

    def maybe_purge():
        if time.time() - state['last_purge'] < 3600 or not state['purge_lock'].acquire(blocking=False):
            return
        state['last_purge'] = time.time()

        def run():
            try:
                with app.app_context():
                    purge_visitors(app)
            except Exception:  # 정리 실패가 서비스를 멈추지 않게 한다
                log.exception('visitor purge failed')
            finally:
                state['purge_lock'].release()
        threading.Thread(target=run, name='visitor-purge', daemon=True).start()

    def mark_seen(user_id):
        now = time.time()
        with state['lock']:
            if now - state['seen'].get(user_id, 0) < SEEN_EVERY:
                return
            state['seen'][user_id] = now
            if len(state['seen']) > 20000:
                state['seen'] = {k: v for k, v in state['seen'].items() if now - v < SEEN_EVERY}
        local = app.extensions.get('junhee_workspace_local')
        if local:
            local.touch(user_id, now)

    @app.route('/robots.txt')
    def _robots():
        return app.response_class(ROBOTS, mimetype='text/plain')

    @app.before_request
    def _visitor_guard():
        maybe_purge()
        path, method = request.path, request.method
        if path != '/app' and not path.startswith(('/api/analysis', '/api/workspace')):
            return None
        user = request_user()
        visitor = bool(user.get('visitor'))  # 로그인 사용자는 계정별 한도가 이미 적용된다
        if not visitor:
            return None
        mark_seen(user['id'])
        kind = _bucket(path, method)
        wait = limited(kind) if kind else 0
        if wait:
            response = jsonify(error='rate_limited', message='요청이 많습니다. 잠시 후 다시 시도해 주세요.')
            response.status_code, response.headers['Retry-After'] = 429, str(wait)
            return response
        if kind == 'upload':
            if (request.content_length or 0) > VISITOR_MAX_UPLOAD + 64 * 1024:
                return jsonify(error='invalid_upload', message='공개 데모에서는 5 MB 이하 파일만 올릴 수 있습니다.'), 413
            request.max_content_length = VISITOR_MAX_UPLOAD + 64 * 1024
        if kind in ('upload', 'analyze') and visitor_bytes(app) >= VISITOR_TOTAL_BYTES:
            return jsonify(error='storage_full', message='공개 데모의 저장 공간이 가득 찼습니다. 나중에 다시 시도해 주세요.'), 507
        return None

    @app.after_request
    def _public_demo_headers(response):
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response


def visitor_bytes(app):
    """방문자 업로드 원본 + 분석 결과(엔진 결과·대시보드 문서) 크기 합계."""
    like = VISITOR_PREFIX + '%'
    svc = app.extensions['junhee_analysis']
    with svc.store.connection() as db:
        return sum(db.execute(sql, (like,)).fetchone()[0] for sql in (
            'SELECT COALESCE(SUM(LENGTH(content)), 0) FROM market_sources WHERE user_id LIKE ?',
            'SELECT COALESCE(SUM(LENGTH(result_json)), 0) FROM market_assessments WHERE user_id LIKE ?',
            'SELECT COALESCE(SUM(LENGTH(doc_json)), 0) FROM junhee_handoff WHERE user_id LIKE ?'))


def purge_visitors(app, now=None):
    """마지막 사용 후 RETENTION 이 지난 방문자 데이터를 지운다. 진행 중인 분석과 그 원본은 남긴다.
    '마지막 사용'은 방문자 사용 기록(visitor_seen)·원본 업로드·분석 갱신 중 가장 늦은 것이다."""
    from .analysis import COMPANY_FILE_DIR
    now = now or datetime.now(timezone.utc)
    cutoff, cutoff_ts = (now - RETENTION).isoformat(), (now - RETENTION).timestamp()
    like = VISITOR_PREFIX + '%'
    svc = app.extensions['junhee_analysis']
    local = app.extensions.get('junhee_workspace_local')
    seen_recent = local.seen_since(VISITOR_PREFIX, cutoff_ts) if local else set()
    files = []
    with svc.store.connection() as db:
        db.execute('BEGIN IMMEDIATE')  # 고르는 동안 새로 생긴 원본·분석을 지우지 않도록 쓰기 잠금부터 잡는다
        active = {r[0] for r in db.execute("SELECT DISTINCT user_id FROM market_assessments "
                                           "WHERE user_id LIKE ? AND status IN ('QUEUED','RUNNING')", (like,))}
        recent = {r[0] for r in db.execute("SELECT user_id FROM market_assessments WHERE user_id LIKE ? AND updated_at >= ? "
                                           "UNION SELECT user_id FROM market_sources WHERE user_id LIKE ? AND created_at >= ?",
                                           (like, cutoff, like, cutoff))}
        stale = {r[0] for r in db.execute("SELECT user_id FROM market_assessments WHERE user_id LIKE ? "
                                          "UNION SELECT user_id FROM market_sources WHERE user_id LIKE ?", (like, like))}
        stale -= active | recent | seen_recent
        for user_id in stale:
            files += [r[0] for r in db.execute('SELECT file_name FROM junhee_company_files WHERE user_id=?', (user_id,))]
            for table in ('junhee_company_files', 'junhee_handoff', 'market_assessments', 'market_sources',
                          'workspace_source_deletions'):
                db.execute(f'DELETE FROM {table} WHERE user_id=?', (user_id,))
            svc.tokens.pop(user_id, None)
    for name in files:
        try:
            (COMPANY_FILE_DIR / os.path.basename(name)).unlink()
        except OSError:
            pass
    removed = local.purge(VISITOR_PREFIX, cutoff_ts) if local else 0
    if stale or removed:
        log.info('visitor purge: %d analysis users, %d workspaces', len(stale), removed)
    return len(stale), removed
