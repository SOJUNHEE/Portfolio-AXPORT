# -*- coding: utf-8 -*-
"""(2026-10-06 공개 데모) 로그인 없이 쓰는 방문자가 서버 자원을 소진하지 못하게 막는 장치.

로그인이 빠지면 방문자 id 는 쿠키를 지우는 것만으로 새로 생기므로, 계정별 한도(원본 30개·진행 중 분석 1개)만으로는
공개 서버를 지킬 수 없다. 그래서 다음을 더한다.
- IP 별 요청 횟수 제한(업로드·분석 요청·그 밖의 저장/삭제)
- 방문자 업로드 크기 상한(5 MB)과 동시에 엑셀을 해석하는 요청 수 상한(2개, 무료 서버 메모리 보호)
- 방문자 업로드 원본 전체 용량 상한(200 MB)
- 마지막 사용 후 7일이 지난 방문자 데이터(원본·분석·바탕화면·업로드 파일) 자동 삭제(1시간에 한 번 검사)
"""
from collections import deque
from datetime import datetime, timedelta, timezone
import logging
import os
import threading
import time

from flask import g, jsonify, request

from .accounts import request_user

log = logging.getLogger(__name__)

VISITOR_PREFIX = 'visitor-'
VISITOR_MAX_UPLOAD = 5 * 1024 * 1024
VISITOR_TOTAL_SOURCE_BYTES = 200 * 1024 * 1024
RETENTION = timedelta(days=7)
UPLOAD_PATHS = ('/api/analysis/sources', '/api/analysis/company-files')
LIMITS = {'upload': (10, 600), 'analyze': (20, 600), 'write': (300, 600)}  # (요청 수, 초) IP 별
PARSE_SLOTS = 2


def _bucket(path, method):
    if method == 'POST' and path in UPLOAD_PATHS:
        return 'upload'
    if method == 'POST' and path == '/api/analysis/assessments':
        return 'analyze'
    return 'write'


def attach_visitor_guard(app):
    if app.extensions.get('junhee_visitor_guard'):
        return
    state = {'hits': {}, 'lock': threading.Lock(), 'parse': threading.BoundedSemaphore(PARSE_SLOTS), 'last_purge': 0.0}
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

    @app.before_request
    def _visitor_guard():
        if time.time() - state['last_purge'] > 3600:
            state['last_purge'] = time.time()
            try:
                purge_visitors(app)
            except Exception:  # 정리 실패가 요청을 막지 않게 한다
                log.exception('visitor purge failed')
        path, method = request.path, request.method
        if method not in ('POST', 'PUT', 'DELETE') or not path.startswith(('/api/analysis', '/api/workspace')):
            return None
        visitor = bool(request_user().get('visitor'))  # 로그인 사용자는 계정별 한도가 이미 적용된다
        wait = limited(_bucket(path, method)) if visitor else 0
        if wait:
            response = jsonify(error='rate_limited', message='요청이 많습니다. 잠시 후 다시 시도해 주세요.')
            response.status_code, response.headers['Retry-After'] = 429, str(wait)
            return response
        if method == 'POST' and path in UPLOAD_PATHS:
            if visitor:
                if (request.content_length or 0) > VISITOR_MAX_UPLOAD + 64 * 1024:
                    return jsonify(error='invalid_upload', message='공개 데모에서는 5 MB 이하 파일만 올릴 수 있습니다.'), 413
                request.max_content_length = VISITOR_MAX_UPLOAD + 64 * 1024
                if visitor_source_bytes(app) >= VISITOR_TOTAL_SOURCE_BYTES:
                    return jsonify(error='storage_full', message='공개 데모의 업로드 저장 공간이 가득 찼습니다. 나중에 다시 시도해 주세요.'), 507
            if not state['parse'].acquire(timeout=15):
                return jsonify(error='analysis_busy', message='다른 파일을 처리 중입니다. 잠시 후 다시 시도해 주세요.'), 429
            g.junhee_parse_slot = True
        return None

    @app.teardown_request
    def _release_parse_slot(_exc):
        if g.pop('junhee_parse_slot', False):
            state['parse'].release()


def visitor_source_bytes(app):
    svc = app.extensions['junhee_analysis']
    with svc.store.connection() as db:
        return db.execute("SELECT COALESCE(SUM(LENGTH(content)), 0) FROM market_sources WHERE user_id LIKE ?",
                          (VISITOR_PREFIX + '%',)).fetchone()[0]


def purge_visitors(app, now=None):
    """마지막 사용 후 RETENTION 이 지난 방문자 데이터를 지운다. 진행 중인 분석과 그 원본은 남긴다."""
    from .analysis import COMPANY_FILE_DIR
    now = now or datetime.now(timezone.utc)
    cutoff = (now - RETENTION).isoformat()
    like = VISITOR_PREFIX + '%'
    svc = app.extensions['junhee_analysis']
    files = []
    with svc.store.connection() as db:
        active = {r[0] for r in db.execute("SELECT DISTINCT user_id FROM market_assessments "
                                           "WHERE user_id LIKE ? AND status IN ('QUEUED','RUNNING')", (like,))}
        recent = {r[0] for r in db.execute("SELECT user_id FROM market_assessments WHERE user_id LIKE ? AND updated_at >= ? "
                                           "UNION SELECT user_id FROM market_sources WHERE user_id LIKE ? AND created_at >= ?",
                                           (like, cutoff, like, cutoff))}
        stale = {r[0] for r in db.execute("SELECT user_id FROM market_assessments WHERE user_id LIKE ? "
                                          "UNION SELECT user_id FROM market_sources WHERE user_id LIKE ?", (like, like))}
        stale -= active | recent
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
    local = app.extensions.get('junhee_workspace_local')
    removed = local.purge(VISITOR_PREFIX, (now - RETENTION).timestamp()) if local else 0
    if stale or removed:
        log.info('visitor purge: %d analysis users, %d workspaces', len(stale), removed)
    return len(stale), removed
