# -*- coding: utf-8 -*-
"""(junhee) 2026-09-27 기업 파일 업로드 → sanghyeob 엔진 분석 → junhee 대시보드(handoff-v1) 연결.

API (로그인·CSRF 필요. accounts.py 가 /api/analysis 를 보호):
  POST /api/analysis/sources                      기업 엑셀 업로드(.xlsx/.xls, 20MB) → {company_id: 'upload:<id>', name, summary}
  POST /api/analysis/assessments                  {company_id ('upload:<id>' 또는 샘플 id), company, hs, country} → 202 {assessment_id, status, progress}
  GET  /api/analysis/sources/<id>/file            업로드한 원본 엑셀 내려받기(바탕화면에서 열기)
  POST /api/analysis/company-files               '기업 파일 업로드': 작업 데이터 폴더(junhee/data/samples/uploads)에 저장 + 분석 원본 등록
  GET  /api/analysis/inspect?company_id=...       분석 전 결측 확인(빈 칸 셀·점수 영향, 빠진 시트)
  GET  /api/analysis/samples                      분석 엔진 샘플 목록(junhee/data/engine_samples.json, 파일은 static/samples/)
  GET  /api/analysis/assessments/<id>             진행 상태 {status, progress, error}
  GET  /api/analysis/assessments/<id>/handoff     완료된 분석의 대시보드 문서(handoff-v1)
  DELETE /api/analysis/assessments/<id>           계정에 저장한 분석 결과 삭제(파일 영구 삭제 때)

엔진의 원본 파일·진행 상태는 instance/company-assessments.sqlite3 (Render 무료 서버는 재배포 때 지워짐).
완료된 대시보드 문서는 Supabase axport_assessments 에도 계정별로 저장해 재배포·재로그인 후에도 불러온다.
외부 API 키(.env): UN_COMTRADE_API_KEY · KCS_TRADE_API_KEY · ECOS_API_KEY · LAW_API_KEY — 없으면 해당 지표만 '검색 불가'.
"""
import io
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import threading
import time

from flask import Blueprint, current_app, jsonify, request, send_file

from .accounts import access_token, csrf_ok, request_user
from .engine.company_analysis import CompanyAnalysis, public_result
from .engine.company_import import MAX_COMPANY_BYTES
from .engine.market_service import MarketError
from .engine.company_import import parse_company, validate_conditions
from .engine_adapter import missing_inputs, to_handoff
from .workspace_store import SupabaseRest, WorkspaceError

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / 'junhee' / 'data' / 'engine_samples.json'  # sanghyeob 샘플(상세양식) + 간편입력 예시
KEY_NAMES = ('KCS_TRADE_API_KEY', 'UN_COMTRADE_API_KEY', 'ECOS_API_KEY', 'LAW_API_KEY')
UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
log = logging.getLogger(__name__)


class AssessmentRepository:
    """완료된 대시보드 문서를 Supabase 에 계정별로 저장(RLS: 본인 행만)."""

    def __init__(self, rest):
        self.rest = rest

    def save(self, user_id, token, assessment_id, doc):
        self.rest.request('POST', '/axport_assessments', token,
                          data={'id': assessment_id, 'user_id': user_id, 'doc': doc})

    def load(self, user_id, token, assessment_id):
        rows = self.rest.request('GET', '/axport_assessments', token,
                                 params={'id': 'eq.' + assessment_id, 'user_id': 'eq.' + user_id, 'select': 'doc', 'limit': '1'})
        return rows[0]['doc'] if isinstance(rows, list) and rows else None

    def delete(self, user_id, token, assessment_id):
        self.rest.request('DELETE', '/axport_assessments', token, params={'id': 'eq.' + assessment_id, 'user_id': 'eq.' + user_id})


class _HandoffFirstStore:
    """(2026-09-27 검토 반영) 엔진이 상태를 COMPLETED 로 바꾸기 직전에 대시보드 문서를 먼저 저장한다.
    그래야 폴링이 COMPLETED 를 본 순간 /handoff 가 반드시 있고, 변환이 실패하면 COMPLETED 대신 FAILED 로 남는다."""

    def __init__(self, store, owner):
        self._store, self._owner = store, owner

    def __getattr__(self, name):
        return getattr(self._store, name)

    def update(self, user_id, assessment_id, status, progress, result=None, error=None):
        ctx = getattr(self._owner._local, 'ctx', None)
        if status == 'COMPLETED' and result is not None:
            # (2026-09-27) 외부 API 원문 응답(raw)은 화면·결과 조회(public_result)에서 어차피 빼는 값이다. 저장하면 결과 1건이
            # 약 20MB(대부분 규제 원문)라 서버 디스크가 금방 찬다 → 저장 전에 뺀다(결과 1건 약 1.6MB)
            public_result({'result': result})
        if status == 'COMPLETED' and result is not None and ctx is not None:
            try:
                doc = to_handoff(json.loads(json.dumps(result, ensure_ascii=False, allow_nan=False)), *ctx)
                text = json.dumps(doc, ensure_ascii=False, allow_nan=False, default=str)
                with self._store.connection() as db:
                    db.execute('INSERT OR REPLACE INTO junhee_handoff VALUES (?, ?, ?)', (user_id, assessment_id, text))
                self._owner._local.text = text
            except Exception:
                log.exception('handoff conversion failed')
                return self._store.update(user_id, assessment_id, 'FAILED', '분석 결과를 대시보드 형식으로 바꾸지 못했습니다.',
                                          error='handoff_failed')
        return self._store.update(user_id, assessment_id, status, progress, result=result, error=error)


class JunheeAnalysis(CompanyAnalysis):
    """엔진(CompanyAnalysis)을 그대로 쓰고, 완료 시 handoff-v1 문서를 만들어 저장만 덧붙인다."""

    def __init__(self, database, root, key_provider, repository=None, *, inline=False):
        super().__init__(database, root, key_provider, inline=inline)
        # 샘플은 junhee 대시보드 목록(static/data/companies) 대신 sanghyeob 샘플 목록을 쓴다
        self.samples = {c['company_id']: c for c in json.loads(SAMPLES.read_text(encoding='utf-8'))['companies']}
        self.sample_hashes = {c.get('file_sha256') for c in self.samples.values() if c.get('file_sha256')}
        self.repository = repository
        self.tokens = {}  # user_id → 제출 시점 access token (백그라운드 저장용, 메모리에만)
        self._local = threading.local()  # 실행 중인 분석의 (기업 파일, 입력) — _HandoffFirstStore 가 읽는다
        self.store = _HandoffFirstStore(self.store, self)
        with self.store.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS junhee_handoff (user_id TEXT NOT NULL, assessment_id TEXT NOT NULL, '
                       'doc_json TEXT NOT NULL, PRIMARY KEY (user_id, assessment_id))')
            db.execute('CREATE TABLE IF NOT EXISTS junhee_company_files (user_id TEXT NOT NULL, source_id TEXT NOT NULL, '
                       'file_name TEXT NOT NULL, PRIMARY KEY (user_id, source_id))')  # '기업 파일 업로드' 저장 파일 ↔ 원본
            # (2026-09-27 배포 QA) 분석을 실행하는 프로세스(pid). 워커가 죽으면 그 분석이 15분 동안 '진행 중'으로 남지 않게 한다
            db.execute('CREATE TABLE IF NOT EXISTS junhee_job_owner (assessment_id TEXT PRIMARY KEY, pid INTEGER NOT NULL)')

    def submit_for(self, user_id, token, payload):
        self.reap_orphans()
        self.tokens[user_id] = token
        item = self.submit(user_id, payload)
        if item.get('status') in ('QUEUED', 'RUNNING'):
            with self.store.connection() as db:
                db.execute('INSERT OR REPLACE INTO junhee_job_owner VALUES (?, ?)', (item['assessment_id'], os.getpid()))
        return item

    def reap_orphans(self):
        """(2026-09-27 배포 QA) 실행하던 워커 프로세스가 없어진 '진행 중' 분석을 실패로 정리한다(POSIX 만: gunicorn 워커 재시작 등).
        같은 서버의 다른 워커가 실행 중인 분석은 그 pid 가 살아 있으므로 건드리지 않는다."""
        if os.name != 'posix':
            return
        with self.store.connection() as db:
            rows = db.execute("SELECT a.user_id, a.id, o.pid FROM market_assessments a JOIN junhee_job_owner o ON o.assessment_id = a.id "
                              "WHERE a.status IN ('QUEUED','RUNNING')").fetchall()
            db.execute("DELETE FROM junhee_job_owner WHERE assessment_id NOT IN "
                       "(SELECT id FROM market_assessments WHERE status IN ('QUEUED','RUNNING'))")
        for user_id, assessment_id, pid in rows:
            if not _process_alive(pid):
                self.store.update(user_id, assessment_id, 'FAILED', '서버가 다시 시작되어 분석이 중단되었습니다. 다시 분석해 주세요.',
                                  error='job_interrupted')

    def mark_sample(self, company, inputs):
        """(2026-09-27 배포 QA) 가상 샘플(샘플 id 또는 같은 파일을 다시 올린 경우 sha256 일치)은 '업로드 기업 데이터'가 아니라
        가상 자료로 표시한다. 파서(company_simple)는 샘플 여부를 모르므로 여기서 자료 구분만 바꾼다(계산값은 그대로)."""
        sha = (company.get('source') or {}).get('sha256')
        if inputs.get('company_id') in self.samples or (sha and sha in self.sample_hashes):
            company['data_class'] = '샘플 기업 (가상) · 외부 근거 연계'
            company['sample'] = True
        return company

    def run(self, user_id, assessment_id, inputs, company):
        self.mark_sample(company, inputs)
        self._local.ctx, self._local.text = (company, inputs), None
        try:
            super().run(user_id, assessment_id, inputs, company)  # COMPLETED 직전에 handoff 저장(_HandoffFirstStore)
        finally:
            text, self._local.ctx, self._local.text = self._local.text, None, None
        token = self.tokens.get(user_id)
        if text and self.repository and token:
            for attempt in (1, 2):  # (2026-09-27 배포 QA) 일시 오류면 한 번 더 저장한다(로컬 디스크는 재시작 때 지워지므로)
                try:
                    self.repository.save(user_id, token, assessment_id, json.loads(text))
                    break
                except WorkspaceError as exc:
                    log.warning('assessment save to Supabase failed (attempt %d): %s', attempt, exc.code)  # 로컬 SQLite 에는 남아 있다
                    if attempt == 2 or exc.code in ('invalid', 'conflict'):
                        break
                    time.sleep(2)

    def running_for(self, user_id, payload):
        """같은 파일·조건으로 이미 진행 중인 분석(창을 닫았다 다시 연 경우 등)이 있으면 그 상태를 돌려준다."""
        try:
            want = validate_conditions(payload)
        except ValueError:
            return None
        for item in self.store.list(user_id):
            inp = item.get('inputs') or {}
            if (item.get('status') in ('QUEUED', 'RUNNING') and inp.get('company_id') == payload.get('company_id')
                    and inp.get('hs_raw') == want['hs_raw'] and inp.get('country') == want['country']):
                return item
        return None

    def delete_source(self, user_id, source_id):
        """영구 삭제한 업로드 원본을 지운다(계정별 보관 한도 30개가 다시 비도록). 진행 중인 분석이 있으면 남긴다.
        (검토 반영) 같은 내용의 파일은 원본 1개를 함께 쓰므로(샘플을 내려받아 다시 올린 경우 등) 분석 결과는 지우지 않는다.
        '기업 파일 업로드'로 작업 데이터 폴더에 저장한 그 원본의 파일도 함께 지운다."""
        with self.store.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT 1 FROM market_assessments WHERE user_id=? AND source_id=? AND status IN ('QUEUED','RUNNING')",
                          (user_id, source_id)).fetchone():
                raise MarketError('analysis_running', '이 파일로 분석이 진행 중입니다. 끝난 뒤 다시 시도해 주세요.', 409)
            files = [r[0] for r in db.execute('SELECT file_name FROM junhee_company_files WHERE user_id=? AND source_id=?', (user_id, source_id))]
            db.execute('DELETE FROM junhee_company_files WHERE user_id=? AND source_id=?', (user_id, source_id))
            deleted = db.execute('DELETE FROM market_sources WHERE user_id=? AND id=?', (user_id, source_id)).rowcount == 1
        for name in files:
            try:
                (COMPANY_FILE_DIR / os.path.basename(name)).unlink()
            except OSError:
                pass
        return deleted

    def company_file(self, user_id, source_id):
        """이 계정 원본을 이미 작업 데이터 폴더에 저장했으면 그 파일 이름(같은 파일을 다시 올려도 새로 쓰지 않음)."""
        with self.store.connection() as db:
            row = db.execute('SELECT file_name FROM junhee_company_files WHERE user_id=? AND source_id=?', (user_id, source_id)).fetchone()
        return row[0] if row and (COMPANY_FILE_DIR / row[0]).is_file() else None

    def remember_company_file(self, user_id, source_id, file_name):
        with self.store.connection() as db:
            db.execute('INSERT OR REPLACE INTO junhee_company_files VALUES (?, ?, ?)', (user_id, source_id, file_name))

    def handoff(self, user_id, token, assessment_id):
        with self.store.connection() as db:
            row = db.execute('SELECT doc_json FROM junhee_handoff WHERE user_id = ? AND assessment_id = ?',
                             (user_id, assessment_id)).fetchone()
        if row:
            return json.loads(row['doc_json'] if isinstance(row, sqlite3.Row) else row[0])
        if self.repository and token:
            return self.repository.load(user_id, token, assessment_id)
        return None

    def forget(self, user_id, token, assessment_id):
        with self.store.connection() as db:
            db.execute('DELETE FROM junhee_handoff WHERE user_id = ? AND assessment_id = ?', (user_id, assessment_id))
        if self.repository and token:
            self.repository.delete(user_id, token, assessment_id)


def _process_alive(pid):
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except (PermissionError, OSError, ValueError):
        return True
    return True


bp = Blueprint('junhee_analysis', __name__)


def service():
    return current_app.extensions['junhee_analysis']


@bp.before_request
def _guard():
    # (2026-10-05) 로그인 없이도 쓴다: 방문자는 세션의 visitor_id 로 본인 파일·분석만 다룬다(request_user)
    if request.method not in ('GET', 'HEAD') and not csrf_ok():
        return jsonify(error='csrf_failed'), 403
    return None


@bp.errorhandler(MarketError)
def _market_error(exc):
    return jsonify(error=exc.code, message=exc.message), exc.status


@bp.errorhandler(sqlite3.Error)
def _storage_error(_exc):
    return jsonify(error='analysis_storage_unavailable', message='분석 저장소를 사용할 수 없습니다. 잠시 후 다시 시도해 주세요.'), 503


@bp.errorhandler(WorkspaceError)
def _remote_error(exc):
    return jsonify(error=exc.code, message='계정 저장소에 연결하지 못했습니다.'), exc.status


def _status(item):
    return {'assessment_id': item['assessment_id'], 'status': item['status'], 'progress': item.get('progress'),
            'error': item.get('error')}


@bp.post('/api/analysis/sources')
def upload_source():
    files = request.files.getlist('file')
    if len(files) != 1 or len(request.files) != 1:
        raise MarketError('invalid_upload', '기업 엑셀 한 개를 선택해 주세요.')
    return jsonify(service().upload(request_user()['id'], files[0].read(MAX_COMPANY_BYTES + 1), files[0].filename)), 201


@bp.get('/api/analysis/sources/<source_id>/file')
def download_source(source_id):
    """(junhee) 바탕화면에서 업로드 파일을 열 때: 계정에 올린 원본 엑셀을 그대로 내려준다(본인 파일만)."""
    if not UUID.fullmatch(source_id):
        raise MarketError('not_found', '파일을 찾을 수 없습니다.', 404)
    row = service().store.source(request_user()['id'], source_id)
    name = str(row['name'] or 'company.xlsx')
    mime = 'application/vnd.ms-excel' if name.lower().endswith('.xls') else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response = send_file(io.BytesIO(bytes(row['content'])), mimetype=mime, as_attachment=True, download_name=name)
    response.headers['Cache-Control'] = 'private, no-store'
    return response


@bp.post('/api/analysis/assessments')
def create_assessment():
    payload = request.get_json(silent=True)
    company_id = str((payload or {}).get('company_id') or '') if isinstance(payload, dict) else ''
    if not (company_id.startswith('upload:') or company_id in service().samples):
        raise MarketError('invalid_company', '업로드한 기업 파일이나 샘플 파일을 선택해 주세요.')
    try:
        return jsonify(_status(service().submit_for(request_user()['id'], access_token(), payload))), 202
    except MarketError as exc:
        running = service().running_for(request_user()['id'], payload) if exc.code == 'analysis_running' else None
        if running is None:
            raise
        return jsonify(_status(running)), 202  # 같은 조건의 진행 중 분석을 이어서 기다린다


@bp.delete('/api/analysis/sources/<source_id>')
def delete_source(source_id):
    """(junhee) 휴지통 '영구 삭제': 어떤 바탕화면 파일도 가리키지 않는 업로드 원본을 지운다(본인 것만)."""
    if not UUID.fullmatch(source_id):
        raise MarketError('not_found', '파일을 찾을 수 없습니다.', 404)
    return jsonify(deleted=service().delete_source(request_user()['id'], source_id))


COMPANY_FILE_DIR = ROOT / 'junhee' / 'data' / 'samples' / 'uploads'  # (junhee) '기업 파일 업로드'로 올린 파일을 두는 작업 데이터 폴더(공개 static 아님)
MAX_COMPANY_FILES = 300  # 작업 데이터 폴더 전체 파일 수 상한(서버 디스크 보호)


def _safe_file_name(name):
    """경로 문자·예약 문자를 빼고 확장자는 .xlsx/.xls 만 남긴다."""
    base = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', os.path.basename(str(name or '')).strip()) or 'company.xlsx'
    stem, dot, ext = base.rpartition('.')
    if not dot or ext.lower() not in ('xlsx', 'xls'):
        raise MarketError('invalid_upload', '엑셀 파일(.xlsx, .xls)을 선택해 주세요.')
    return stem.strip(' .')[:80] or 'company', ext.lower()


@bp.post('/api/analysis/company-files')
def upload_company_file():
    """(junhee) 2026-09-27 '기업 파일 업로드': 양식을 검사한 뒤 작업 데이터 폴더(junhee/data/samples/uploads)에 저장하고
    계정의 분석 원본으로도 등록한다(바탕화면 회사 파일로 쓰고, 종합 수출적합도를 바로 계산할 수 있게)."""
    files = request.files.getlist('file')
    if len(files) != 1 or len(request.files) != 1:
        raise MarketError('invalid_upload', '기업 엑셀 한 개를 선택해 주세요.')
    stem, ext = _safe_file_name(files[0].filename)
    data = files[0].read(MAX_COMPANY_BYTES + 1)
    if not data or len(data) > MAX_COMPANY_BYTES:
        raise MarketError('invalid_upload', '0바이트보다 크고 20 MB 이하인 파일을 선택해 주세요.')
    try:
        company = parse_company(data, f'{stem}.{ext}')
    except ValueError as exc:
        raise MarketError('invalid_workbook', str(exc)) from None
    user_id = request_user()['id']
    uploaded = service().upload(user_id, data, f'{stem}.{ext}')  # 계정 원본 등록이 먼저(보관 한도 초과 등이면 파일을 남기지 않음)
    source_id = uploaded['company_id'][7:]
    known = service().company_file(user_id, source_id)
    if known:  # (검토 반영) 같은 내용을 다시 올리면 새 파일을 쓰지 않는다 → 반복 업로드로 서버 디스크가 차지 않음
        target = COMPANY_FILE_DIR / known
    else:
        COMPANY_FILE_DIR.mkdir(parents=True, exist_ok=True)
        if sum(1 for p in COMPANY_FILE_DIR.iterdir() if p.suffix.lower() in ('.xlsx', '.xls')) >= MAX_COMPANY_FILES:
            raise MarketError('storage_full', '작업 데이터 폴더가 가득 찼습니다. 쓰지 않는 파일을 휴지통에서 영구 삭제해 주세요.', 507)
        target, n = COMPANY_FILE_DIR / f'{stem}.{ext}', 2
        while True:  # 같은 이름이 있으면 (2), (3)… 을 붙인다(덮어쓰지 않음, 동시 요청도 'x' 모드로 안전)
            try:
                with open(target, 'xb') as fh:
                    fh.write(data)
                break
            except FileExistsError:
                target, n = COMPANY_FILE_DIR / f'{stem} ({n}).{ext}', n + 1
        service().remember_company_file(user_id, source_id, target.name)
    return jsonify(company_id=uploaded['company_id'], name=target.name, size=len(data),
                   saved_path=target.relative_to(ROOT).as_posix(), missing=missing_inputs(company)), 201


@bp.get('/api/analysis/inspect')
def inspect_file():
    """(junhee) 분석 전 결측 확인: 업로드 원본('upload:<id>')이나 샘플 id 의 파일을 읽어 빈 칸·빠진 시트를 알려 준다."""
    company_id = request.args.get('company_id', '')
    svc = service()
    if company_id.startswith('upload:') and UUID.fullmatch(company_id[7:]):
        row = svc.store.source(request_user()['id'], company_id[7:])
        data, name = bytes(row['content']), row['name']
    elif company_id in svc.samples:
        name = svc.samples[company_id]['file_name']
        data = (ROOT / 'static' / 'samples' / name).read_bytes()
    else:
        raise MarketError('not_found', '파일을 찾을 수 없습니다.', 404)
    try:
        company = parse_company(data, name)
    except ValueError as exc:
        raise MarketError('invalid_workbook', str(exc)) from None
    return jsonify(file_name=name, **missing_inputs(company))


@bp.get('/api/analysis/samples')
def list_samples():
    keys = ('company_id', 'company_name', 'file_name', 'format', 'hs', 'country_iso2')
    return jsonify(samples=[{k: c.get(k) for k in keys} for c in service().samples.values()])


@bp.get('/api/analysis/assessments/<assessment_id>')
def get_assessment(assessment_id):
    if not UUID.fullmatch(assessment_id):
        raise MarketError('not_found', '분석을 찾을 수 없습니다.', 404)
    service().reap_orphans()
    return jsonify(_status(service().store.get(request_user()['id'], assessment_id)))


@bp.get('/api/analysis/assessments/<assessment_id>/handoff')
def get_handoff(assessment_id):
    if not UUID.fullmatch(assessment_id):
        raise MarketError('not_found', '분석을 찾을 수 없습니다.', 404)
    doc = service().handoff(request_user()['id'], access_token(), assessment_id)
    if doc is None:
        raise MarketError('not_found', '저장된 분석 결과가 없습니다. 파일을 다시 분석해 주세요.', 404)
    return jsonify(doc)


@bp.delete('/api/analysis/assessments/<assessment_id>')
def delete_assessment(assessment_id):
    if not UUID.fullmatch(assessment_id):
        raise MarketError('not_found', '분석을 찾을 수 없습니다.', 404)
    service().forget(request_user()['id'], access_token(), assessment_id)
    return jsonify(ok=True)


def attach_analysis(app):
    """accounts.attach_accounts(app) 안에서 부른다."""
    if app.extensions.get('junhee_analysis'):
        return
    ext = app.extensions['junhee_accounts']
    repository = None
    if ext['ready']:
        repository = AssessmentRepository(SupabaseRest(os.environ['SUPABASE_URL'].strip(), os.environ['SUPABASE_PUBLISHABLE_KEY'].strip()))
    database = os.environ.get('AXPORT_ANALYSIS_DB') or str(ROOT / 'instance' / 'company-assessments.sqlite3')
    Path(database).parent.mkdir(parents=True, exist_ok=True)

    def keys():
        return {name: os.environ.get(name, '').strip() for name in KEY_NAMES}

    app.extensions['junhee_analysis'] = JunheeAnalysis(database, ROOT, keys, repository,
                                                       inline=os.environ.get('AXPORT_ANALYSIS_INLINE') == '1')

    @app.before_request
    def _upload_limit():
        # 기업 엑셀 업로드 경로만 20MB 까지 허용(나머지 요청 크기 제한은 그대로)
        if request.path in ('/api/analysis/sources', '/api/analysis/company-files'):  # (검토 반영) 기업 파일 업로드도 20MB
            request.max_content_length = MAX_COMPANY_BYTES + 64 * 1024
    app.register_blueprint(bp)
