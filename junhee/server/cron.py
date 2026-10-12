# -*- coding: utf-8 -*-
"""(2026-10-12 Vercel 배포) 하루 한 번 크론: 방문자 보관기간 정리 + 바탕화면 위젯 공식 자료 갱신.

Render 에서는 서버 안의 스레드가 이 일을 했다(visitor_guard.maybe_purge, widget_refresh.start). Vercel 은 응답이 끝나면
인스턴스가 멈추므로 스레드 대신 Vercel Cron 이 GET /api/cron/daily 를 부른다(vercel.json 의 crons, Hobby 요금제는 하루 1회).
  - CRON_SECRET 환경변수를 넣으면 Vercel 이 'Authorization: Bearer <값>' 을 붙여 부른다. 값이 맞을 때만 실행하고
    CRON_SECRET 이 없거나 틀리면 404 (외부에서 아무나 정리·외부 API 호출을 일으키지 못하게)
  - 위젯 자료는 static/ 에 쓸 수 없으므로 외부 DB(DATABASE_URL)의 widget_snapshots 에 저장하고,
    /static/data/widgets/widgets.json 요청을 DB 의 최신본으로 응답한다(없으면 배포에 들어 있는 파일 그대로)
"""
from contextlib import closing
import hmac
import json
import logging
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from flask import abort, jsonify, request

from . import dbcompat
from .widget_refresh import ROOT, SCRIPT

log = logging.getLogger(__name__)

WIDGET_PATH = '/static/data/widgets/widgets.json'
BUNDLED = ROOT / 'static' / 'data' / 'widgets' / 'widgets.json'
REFRESH_TIMEOUT = 240  # 초. vercel.json maxDuration(300초) 안에서 끝나게


def _db():
    return dbcompat.connect('widget-snapshots.sqlite3')


def latest_widgets():
    """DB 에 저장한 최신 위젯 자료(JSON 문자열). 외부 DB 를 쓰지 않거나 아직 없으면 None."""
    if not dbcompat.enabled():
        return None
    with closing(_db()) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS widget_snapshots (id TEXT PRIMARY KEY, data TEXT NOT NULL, updated REAL NOT NULL)')
        row = db.execute("SELECT data FROM widget_snapshots WHERE id='widgets'").fetchone()
    return row[0] if row else None


def refresh_widgets():
    """fetch_widget_data.py 를 그대로 실행하되 결과를 임시 파일로 받아 DB 에 저장한다. 실패한 항목은 이전 값을 유지한다."""
    base = latest_widgets() or BUNDLED.read_text(encoding='utf-8')
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / 'widgets.json'
        out.write_text(base, encoding='utf-8')
        done = subprocess.run([sys.executable, '-B', str(SCRIPT), '--only', 'fx,news,weather'], cwd=str(ROOT),
                              env={**os.environ, 'AXPORT_WIDGETS_OUT': str(out)}, timeout=REFRESH_TIMEOUT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # 출력에 키가 섞이지 않게 버린다
        text = out.read_text(encoding='utf-8')
    json.loads(text)  # 깨진 파일은 저장하지 않는다
    with closing(_db()) as db, db:
        db.execute('INSERT OR REPLACE INTO widget_snapshots VALUES (?, ?, ?)', ('widgets', text, time.time()))
    return done.returncode == 0


def attach_cron(app):
    if app.extensions.get('junhee_cron'):
        return
    app.extensions['junhee_cron'] = True

    @app.get('/api/cron/daily')
    def _cron_daily():
        secret = os.environ.get('CRON_SECRET', '')
        supplied = request.headers.get('Authorization', '')
        if not secret or not hmac.compare_digest(supplied.encode('utf-8'), ('Bearer ' + secret).encode('utf-8')):
            abort(404)
        from .visitor_guard import purge_visitors
        result = {}
        try:
            users, workspaces = purge_visitors(app)
            result['purge'] = {'analysis_users': users, 'workspaces': workspaces}
        except Exception:  # 정리가 실패해도 위젯 갱신은 한다
            log.exception('cron visitor purge failed')
            result['purge'] = 'failed'
        if dbcompat.enabled():
            try:
                result['widgets'] = 'ok' if refresh_widgets() else 'partial'
            except Exception:
                log.exception('cron widget refresh failed')
                result['widgets'] = 'failed'
        return jsonify(result)

    @app.before_request
    def _stored_widgets():
        if request.path != WIDGET_PATH or not dbcompat.enabled():
            return None
        try:
            text = latest_widgets()
        except sqlite3.Error:
            return None  # DB 를 못 쓰면 배포에 들어 있는 파일로
        if not text:
            return None
        response = app.response_class(text, mimetype='application/json')
        response.headers['Cache-Control'] = 'no-cache'
        return response
