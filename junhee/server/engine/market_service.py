# (junhee) 2026-09-27 sanghyeob/market_service.py 에서 옮김. 바꾼 것: 패키지 import 경로·원본 자료 경로(junhee/data/raw)만. 계산 로직은 그대로.
"""Private, durable first-stage market assessments for one Flask installation.

No external data is fetched at import/startup. Existing authentication owns all
routes; the local SQLite store always partitions reads and writes by user id.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from threading import Lock
import time
from uuid import uuid4

from .market_data import collect_market, validate_inputs
from .market_wsts import MAX_FILE_BYTES, parse_wsts


class MarketError(Exception):
    def __init__(self, code, message, status=400):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class WorkspaceSourceSession:
    """Source lifecycle operations within one reserved SQLite transaction.

    Only the owning workspace service supplies manifest items. A failed remote
    save may have committed, so prepare records a minimal intent; reconciliation
    resolves it against the next successfully loaded manifest.
    """

    def __init__(self, db, user_id, store):
        self.db = db
        self.user_id = user_id
        self.store = store
        self.prepared = {}
        self.completed_tokens = set()

    @staticmethod
    def _references(items):
        if not isinstance(items, list):
            raise ValueError('workspace items must be a list')
        identities, companies = set(), set()
        for item in items:
            if (not isinstance(item, dict) or not isinstance(item.get('id'), str)
                    or not item['id']):
                raise ValueError('workspace item identity is required')
            identities.add(item['id'])
            company = item.get('company_id')
            if company is not None:
                if not isinstance(company, str) or not company:
                    raise ValueError('workspace source identity is invalid')
                companies.add(company)
        return identities, companies

    def _write_intent(self, item_id, company_id):
        self.db.execute('INSERT INTO workspace_source_deletions(user_id,item_id,company_id) VALUES(?,?,?) '
                        'ON CONFLICT(user_id,item_id) DO UPDATE SET company_id=excluded.company_id',
                        (self.user_id, item_id, company_id))

    @staticmethod
    def _deletion_files(files):
        if not isinstance(files, list):
            raise ValueError('workspace deletion files must be a list')
        cleaned, identities = [], set()
        for item in files:
            if (not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id']
                    or not isinstance(item.get('company_id'), str) or not item['company_id']
                    or item['id'] in identities):
                raise ValueError('workspace deletion identity is invalid or duplicated')
            identities.add(item['id'])
            cleaned.append({'id': item['id'], 'company_id': item['company_id']})
        return cleaned

    def prepare(self, item_id, company_id):
        self.prepare_many([{'id': item_id, 'company_id': company_id}])

    def prepare_many(self, files):
        files = self._deletion_files(files)
        if not files:
            return
        # A separate, content-free journal can commit while the main database
        # keeps its write reservation. This survives termination during remote
        # CAS. All batch identities commit together before any remote mutation.
        self.store._journal_prepare_many(self.user_id, files)
        # Retained in memory only so the context can roll back every unsafe
        # local mutation before preserving every prepared identity mirror.
        self.prepared.update((item['id'], item['company_id']) for item in files)
        for item in files:
            self._write_intent(item['id'], item['company_id'])

    def _clear(self, item_id, token=None):
        self.db.execute('DELETE FROM workspace_source_deletions WHERE user_id=? AND item_id=?',
                        (self.user_id, item_id))
        if token is not None:
            self.completed_tokens.add((item_id, token))

    def _purge(self, company_id, companies):
        if not isinstance(company_id, str) or not company_id.startswith('upload:') or not company_id[7:]:
            return {'data_deleted': False, 'shared_source_retained': False}
        if company_id in companies:
            return {'data_deleted': False, 'shared_source_retained': True}
        source_id = company_id[7:]
        deleted_assessments = self.db.execute('DELETE FROM market_assessments WHERE user_id=? AND source_id=?',
                                              (self.user_id, source_id)).rowcount
        deleted_sources = self.db.execute('DELETE FROM market_sources WHERE user_id=? AND id=?',
                                          (self.user_id, source_id)).rowcount
        return {'data_deleted': bool(deleted_sources or deleted_assessments), 'shared_source_retained': False}

    def reconcile(self, items):
        identities, companies = self._references(items)
        pending = {row['item_id']: dict(row) for row in self.db.execute(
            'SELECT item_id,company_id FROM workspace_source_deletions WHERE user_id=?', (self.user_id,))}
        # A journal entry is authoritative if termination left an older mirror.
        for intent in self.store._journal_intents(self.user_id):
            pending[intent['item_id']] = intent
        for intent in pending.values():
            if intent['item_id'] in identities:
                # A timed-out remote CAS can still commit after this read.
                # Keep its identifier-only intent until absence is observed;
                # an existing item is not proof that the old CAS has failed.
                continue
            self._purge(intent['company_id'], companies)
            self._clear(intent['item_id'], intent.get('token'))

    def delete(self, item_id, company_id, remaining_items):
        return self.delete_many([{'id': item_id, 'company_id': company_id}], remaining_items)

    def delete_many(self, files, remaining_items):
        files = self._deletion_files(files)
        identities, companies = self._references(remaining_items)
        if any(item['id'] in identities for item in files):
            raise ValueError('deleted workspace item remains in manifest')
        result = {'data_deleted': False, 'shared_source_retained': False}
        if not files:
            return result
        pending = {row['item_id']: row for row in self.store._journal_intents(self.user_id)}
        # Different icons can share one immutable source. Evaluate the final
        # manifest once per source, never an intermediate removal sequence.
        for company_id in dict.fromkeys(item['company_id'] for item in files):
            purged = self._purge(company_id, companies)
            result = {key: result[key] or purged[key] for key in result}
        for item in files:
            intent = pending.get(item['id'], {})
            token = intent.get('token') if intent.get('company_id') == item['company_id'] else None
            self._clear(item['id'], token)
        return result


class MarketStore:
    def __init__(self, path):
        self.path = Path(path)
        self.deletion_journal_path = self.path.with_name(self.path.name + '.deletions.sqlite3')
        self._lock = Lock()

    @contextmanager
    def _journal_connection(self):
        self.deletion_journal_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(str(self.deletion_journal_path), timeout=10)) as db:
            db.row_factory = sqlite3.Row
            # FULL is SQLite's normal durability level; state it explicitly for
            # the small journal that bridges local storage and remote metadata.
            db.execute('PRAGMA synchronous=FULL')
            db.execute('CREATE TABLE IF NOT EXISTS workspace_source_deletions ('
                       'user_id TEXT NOT NULL,item_id TEXT NOT NULL,company_id TEXT NOT NULL,token TEXT NOT NULL,'
                       'PRIMARY KEY(user_id,item_id))')
            with db:
                yield db

    def _journal_prepare(self, user_id, item_id, company_id):
        return self._journal_prepare_many(user_id, [{'id': item_id, 'company_id': company_id}])[item_id]

    def _journal_prepare_many(self, user_id, files):
        tokens = {item['id']: str(uuid4()) for item in files}
        if not files:
            return tokens
        with self._journal_connection() as db:
            db.executemany('INSERT INTO workspace_source_deletions(user_id,item_id,company_id,token) VALUES(?,?,?,?) '
                           'ON CONFLICT(user_id,item_id) DO UPDATE SET company_id=excluded.company_id,token=excluded.token',
                           [(user_id, item['id'], item['company_id'], tokens[item['id']]) for item in files])
        return tokens

    def _journal_intents(self, user_id):
        with self._journal_connection() as db:
            return [dict(row) for row in db.execute(
                'SELECT item_id,company_id,token FROM workspace_source_deletions WHERE user_id=?', (user_id,))]

    def _journal_complete(self, user_id, completed_tokens):
        if not completed_tokens:
            return
        with self._journal_connection() as db:
            db.executemany('DELETE FROM workspace_source_deletions WHERE user_id=? AND item_id=? AND token=?',
                           [(user_id, item_id, token) for item_id, token in completed_tokens])

    @contextmanager
    def connection(self):
        with closing(self._connect()) as db:
            with db:
                yield db

    def _connect(self):
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            db = sqlite3.connect(str(self.path), timeout=10)
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS market_sources (
                    id TEXT PRIMARY KEY, user_id TEXT NOT NULL, created_at TEXT NOT NULL,
                    name TEXT NOT NULL, content BLOB NOT NULL, summary_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS market_assessments (
                    id TEXT PRIMARY KEY, user_id TEXT NOT NULL, status TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, started REAL NOT NULL,
                    inputs_json TEXT NOT NULL, source_id TEXT, progress TEXT NOT NULL,
                    result_json TEXT, error TEXT
                );
                CREATE INDEX IF NOT EXISTS market_user_created
                    ON market_assessments(user_id, created_at DESC);
                CREATE UNIQUE INDEX IF NOT EXISTS market_one_active_per_user
                    ON market_assessments(user_id) WHERE status IN ('QUEUED','RUNNING');
                CREATE TABLE IF NOT EXISTS workspace_source_deletions (
                    user_id TEXT NOT NULL, item_id TEXT NOT NULL, company_id TEXT NOT NULL,
                    PRIMARY KEY(user_id,item_id)
                );
            ''')
            return db

    @contextmanager
    def workspace_transaction(self, user_id):
        """Serialize manifest operations with source writes across processes.

        The independent journal commits intent before remote CAS while this
        transaction retains its BEGIN IMMEDIATE reservation. On an exception,
        roll back unsafe local changes and keep only identity mirrors. Clear
        journal tokens only after the main deletion transaction has committed.
        """
        with closing(self._connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('SAVEPOINT workspace_source_operations')
            session = WorkspaceSourceSession(db, user_id, self)
            try:
                yield session
            except BaseException:
                try:
                    db.execute('ROLLBACK TO SAVEPOINT workspace_source_operations')
                    db.execute('RELEASE SAVEPOINT workspace_source_operations')
                    for item_id, company_id in session.prepared.items():
                        session._write_intent(item_id, company_id)
                    db.commit()
                except BaseException:
                    db.rollback()
                    raise
                raise
            else:
                try:
                    db.execute('RELEASE SAVEPOINT workspace_source_operations')
                    db.commit()
                except BaseException:
                    db.rollback()
                    raise
                try:
                    self._journal_complete(user_id, session.completed_tokens)
                except (sqlite3.Error, OSError):
                    # Data deletion committed. Leaving the minimal journal for
                    # the next reconciliation is safe and does not resurrect it.
                    pass

    @staticmethod
    def expire(db):
        # A stopped process must not leave a user permanently locked out.
        db.execute("UPDATE market_assessments SET status='FAILED', progress=?, error=?, updated_at=? "
                   "WHERE status IN ('QUEUED','RUNNING') AND started < ?",
                   ('작업 시간이 초과되었습니다. 새 평가를 실행해 주세요.', 'job_interrupted',
                    timestamp(), time.time() - 900))

    def add_source(self, user_id, name, content, summary):
        source_id = str(uuid4())
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT id, summary_json FROM market_sources WHERE user_id=?', (user_id,)).fetchall()
            for row in existing:
                if json.loads(row['summary_json']).get('sha256') == summary['sha256']:
                    return row['id']
            if db.execute('SELECT COUNT(*) FROM market_sources WHERE user_id=?', (user_id,)).fetchone()[0] >= 30:
                raise MarketError('source_limit', '이 설치의 계정별 참고자료 보관 한도(30개)에 도달했습니다.', 409)
            db.execute('INSERT INTO market_sources VALUES(?,?,?,?,?,?)',
                       (source_id, user_id, timestamp(), name, content,
                        json.dumps(summary, ensure_ascii=False, allow_nan=False)))
        return source_id

    def source(self, user_id, source_id):
        with self.connection() as db:
            row = db.execute('SELECT * FROM market_sources WHERE user_id=? AND id=?',
                             (user_id, source_id)).fetchone()
        if row is None:
            raise MarketError('source_not_found', '사용할 수 있는 참고자료를 찾지 못했습니다.', 404)
        return row

    def create(self, user_id, inputs, source_id=None):
        assessment_id, now = str(uuid4()), timestamp()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if source_id is not None and not db.execute(
                    'SELECT 1 FROM market_sources WHERE user_id=? AND id=?', (user_id, source_id)).fetchone():
                raise MarketError('source_not_found', '사용할 수 있는 참고자료를 찾지 못했습니다.', 404)
            self.expire(db)
            if db.execute("SELECT 1 FROM market_assessments WHERE user_id=? AND status IN ('QUEUED','RUNNING')",
                          (user_id,)).fetchone():
                raise MarketError('analysis_running', '이미 진행 중인 평가가 있습니다. 진행 상황을 확인해 주세요.', 409)
            if db.execute("SELECT COUNT(*) FROM market_assessments WHERE status IN ('QUEUED','RUNNING')").fetchone()[0] >= 2:
                raise MarketError('analysis_busy', '다른 평가를 처리 중입니다. 잠시 후 다시 시도해 주세요.', 429)
            db.execute('INSERT INTO market_assessments VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (assessment_id, user_id, 'QUEUED', now, now, time.time(),
                        json.dumps(inputs, ensure_ascii=False), source_id,
                        '자료 조회를 준비합니다.', None, None))
        return assessment_id

    def update(self, user_id, assessment_id, status, progress, result=None, error=None):
        with self.connection() as db:
            updated = db.execute("UPDATE market_assessments SET status=?, progress=?, result_json=?, error=?, updated_at=?, started=? "
                       "WHERE user_id=? AND id=? AND status IN ('QUEUED','RUNNING')",
                       (status, progress, json.dumps(result, ensure_ascii=False, allow_nan=False) if result is not None else None,
                        error, timestamp(), time.time(), user_id, assessment_id))
            return updated.rowcount == 1

    @staticmethod
    def decode(row, include_result=True):
        item = {'assessment_id': row['id'], 'status': row['status'], 'created_at': row['created_at'],
                'updated_at': row['updated_at'], 'inputs': json.loads(row['inputs_json']),
                'progress': row['progress'], 'error': row['error']}
        if include_result:
            item['result'] = json.loads(row['result_json']) if row['result_json'] else None
        return item

    def get(self, user_id, assessment_id):
        with self.connection() as db:
            self.expire(db)
            row = db.execute('SELECT * FROM market_assessments WHERE user_id=? AND id=?',
                             (user_id, assessment_id)).fetchone()
        if row is None:
            raise MarketError('assessment_not_found', '평가를 찾을 수 없습니다.', 404)
        return self.decode(row)

    def list(self, user_id):
        with self.connection() as db:
            self.expire(db)
            rows = db.execute('SELECT id,status,created_at,updated_at,inputs_json,progress,error '
                              'FROM market_assessments WHERE user_id=? ORDER BY created_at DESC LIMIT 50',
                              (user_id,)).fetchall()
        return [self.decode(row, False) for row in rows]


class MarketService:
    def __init__(self, database, source_path, key_provider, *, inline=False, collector=None):
        self.store = MarketStore(database)
        self.source_path = Path(source_path)
        self.key_provider = key_provider
        self.inline = inline
        self.collector = collector or collect_market
        self.executor = None
        self._executor_lock = Lock()

    def upload(self, user_id, data, filename):
        # Never treat the submitted filename as a path on the server.
        name = str(filename).replace('\\', '/').rsplit('/', 1)[-1]
        if not name or len(name) > 180 or any(ord(c) < 32 for c in name):
            raise MarketError('invalid_filename', '파일 이름을 확인해 주세요.')
        try:
            summary = parse_wsts(data, name)
        except ValueError as exc:
            raise MarketError('invalid_workbook', str(exc)) from exc
        summary.pop('series')
        source_id = self.store.add_source(user_id, name, data, summary)
        return {'source_id': source_id, 'name': name, 'summary': summary}

    def submit(self, user_id, payload):
        if not isinstance(payload, dict):
            raise MarketError('invalid_input', '평가 조건을 입력해 주세요.')
        try:
            inputs = validate_inputs(payload)
        except ValueError as exc:
            raise MarketError('invalid_input', str(exc)) from exc
        source_id = payload.get('source_id')
        if source_id is not None:
            if not isinstance(source_id, str) or len(source_id) > 64:
                raise MarketError('invalid_input', '참고자료 식별자가 올바르지 않습니다.')
            self.store.source(user_id, source_id)
        # Snapshot the selected reference before starting work, so later file replacement
        # cannot change the evidence for this run.
        if source_id:
            source = self.store.source(user_id, source_id)
            content, name = bytes(source['content']), source['name']
        else:
            try:
                if self.source_path.stat().st_size > MAX_FILE_BYTES:
                    raise ValueError('기본 참고자료가 너무 큽니다.')
                content, name = self.source_path.read_bytes(), self.source_path.name
            except (OSError, ValueError) as exc:
                raise MarketError('reference_unavailable', '기본 WSTS 자료를 읽을 수 없습니다. 지원 양식을 업로드해 주세요.', 503) from exc
        try:
            industry = parse_wsts(content, name)
        except ValueError as exc:
            raise MarketError('invalid_workbook', str(exc)) from exc
        if not source_id:
            # One immutable raw reference per user/hash; never place originals under static/.
            with self.store.connection() as db:
                existing = db.execute('SELECT id, summary_json FROM market_sources WHERE user_id=?', (user_id,)).fetchall()
            source_id = next((row['id'] for row in existing
                              if json.loads(row['summary_json']).get('sha256') == industry['sha256']), None)
            if not source_id:
                summary = {k: v for k, v in industry.items() if k != 'series'}
                source_id = self.store.add_source(user_id, name, content, summary)
        inputs['source_id'] = source_id
        inputs['analysis_as_of'] = timestamp()
        assessment_id = self.store.create(user_id, inputs, source_id)
        if self.inline:
            self.run(user_id, assessment_id, inputs, industry)
        else:
            try:
                with self._executor_lock:
                    if self.executor is None:
                        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='market-assessment')
                    self.executor.submit(self.run, user_id, assessment_id, inputs, industry)
            except RuntimeError:
                self.store.update(user_id, assessment_id, 'FAILED', '작업을 시작하지 못했습니다. 잠시 후 다시 시도해 주세요.', error='worker_unavailable')
        return {'assessment_id': assessment_id, 'status': self.store.get(user_id, assessment_id)['status']}

    def run(self, user_id, assessment_id, inputs, industry):
        def progress(message):
            if not self.store.update(user_id, assessment_id, 'RUNNING', str(message)[:240]):
                raise InterruptedError('assessment_no_longer_active')
        try:
            progress('공식 무역통계를 조회합니다.')
            result = self.collector(inputs, self.key_provider(), progress=progress)
            result['industry'] = industry
            result.update(overall_score=None, market_score=None, regulation_status='NOT_ASSESSED',
                          overall_status='ASSESSMENT_PENDING', company_fit_status='NOT_ASSESSED',
                          rubric_version='market-annual-observations-v1-unscored',
                          assessment_scope='HS2022 연간 시장 원지표 · 기업별 수출적합도 미평가',
                          analysis_as_of=inputs['analysis_as_of'])
            result.setdefault('warnings', []).extend([
                '첫 구현은 연간 원지표만 제공합니다. 월별 YTD·최근 3개월 성장률과 시장성 40점은 아직 산출하지 않습니다.',
                '규제·가격·물류·안정성의 최종 검토가 완료되지 않아 종합점수는 보류합니다.',
                '조회 시점의 최신 수정 통계입니다. 과거 당시 공표된 자료만 사용한 역사적 재현 평가가 아닙니다.',
            ])
            metrics = [m for country in result.get('countries', []) for m in country.get('metrics', [])]
            available = sum(m.get('value') is not None for m in metrics)
            result['market_status'] = ('READY' if metrics and available == len(metrics)
                                       else 'PARTIAL' if available else 'INSUFFICIENT_DATA')
            self.store.update(user_id, assessment_id, 'COMPLETED', '시장 원지표 처리가 끝났습니다. 종합평가는 보류 상태입니다.', result)
        except Exception:
            # Provider exception text can contain URLs with secrets. Do not persist/log it.
            self.store.update(user_id, assessment_id, 'FAILED',
                              '평가를 완료하지 못했습니다. 입력과 연결 상태를 확인한 뒤 다시 시도해 주세요.',
                              error='assessment_failed')


def public_assessment(item):
    """Keep full immutable evidence private to the dedicated authenticated route."""
    result = item.get('result')
    if result:
        for source in result.get('sources', []):
            source.pop('raw', None)
        industry = result.get('industry') or {}
        series = industry.get('series', [])
        # Compact chart/table view; the snapshot retains every imported observation.
        periods = sorted({point['period'] for point in series})[-24:]
        industry['series'] = [point for point in series if point['period'] in periods and point['region'] == 'Worldwide']
    return item
