# -*- coding: utf-8 -*-
"""(2026-10-12 Vercel 배포) DATABASE_URL 이 있으면 SQLite 파일 대신 Postgres 에 저장하는 얇은 호환 계층.

Vercel 은 요청마다 다른 인스턴스가 응답할 수 있고 배포 디렉터리가 읽기 전용이라, instance/*.sqlite3 에 둔
방문자 바탕화면·업로드 원본·분석 결과가 유지되지 않는다. 엔진(sanghyeob 코드)의 SQL 은 그대로 두고,
connect() 가 돌려주는 연결만 바꾼다.
  - 환경변수 없음(로컬·Render·테스트): 지금처럼 sqlite3.connect(path) 그대로
  - AXPORT_DATABASE_URL / DATABASE_URL / POSTGRES_URL 중 하나가 있으면: 아래 PgConnection

PgConnection 은 이 프로젝트가 쓰는 sqlite3 기능만 흉내 낸다.
  - ? 자리표시자, INSERT OR REPLACE(기본키로 ON CONFLICT), 두 인자 MAX() → GREATEST
  - BEGIN IMMEDIATE → 트랜잭션 + 파일(경로 이름)별 advisory lock: SQLite 의 '파일 하나에 쓰기 하나' 직렬화와 같게
  - CREATE ... IF NOT EXISTS 는 프로세스마다 한 번만, 호출한 트랜잭션과 따로 실행(롤백돼도 표가 남게)
  - BLOB/REAL/INTEGER → BYTEA/DOUBLE PRECISION/BIGINT (REAL 은 Postgres 에서 4바이트라 time.time() 이 뭉개진다)
  - PRAGMA table_info 만 지원(나머지 PRAGMA 는 무시), 행은 row['열'] 과 row[0] 둘 다 된다
  - Postgres 오류는 sqlite3.Error 하위 클래스로 바꿔 올린다 → 기존 except sqlite3.Error 처리가 그대로 동작
"""
import atexit
from functools import lru_cache
import decimal
import os
from pathlib import Path
import re
import sqlite3
import threading
import zlib

URL_NAMES = ('AXPORT_DATABASE_URL', 'DATABASE_URL', 'POSTGRES_URL')


def database_url():
    for name in URL_NAMES:
        value = os.environ.get(name, '').strip()
        if value:
            return value
    return ''


def enabled():
    return bool(database_url())


def connect(path, timeout=10, *, aliases=None):
    """sqlite3.connect(path, timeout) 대신 부른다. aliases: {SQLite 표 이름: Postgres 표 이름} (같은 이름이 두 파일에 있을 때)."""
    url = database_url()
    if not url:
        return sqlite3.connect(str(path), timeout=timeout)
    return PgConnection(_pool(url, timeout), Path(str(path)).name, aliases or {})


# ---------- 오류: sqlite3 예외 계층으로 ----------

class PgError(sqlite3.DatabaseError):
    pass


class PgIntegrityError(sqlite3.IntegrityError):
    pass


class PgOperationalError(sqlite3.OperationalError):
    pass


def _wrap(exc):
    import psycopg
    if isinstance(exc, psycopg.IntegrityError):
        return PgIntegrityError(str(exc))
    if isinstance(exc, psycopg.OperationalError):
        return PgOperationalError(str(exc))
    return PgError(str(exc))


# ---------- 연결 풀 ----------

_pools, _pools_lock = {}, threading.Lock()


def _pool(url, timeout):
    with _pools_lock:
        pool = _pools.get(url)
        if pool is None:
            from psycopg_pool import ConnectionPool
            # prepare_threshold=None: 트랜잭션 단위 풀러(PgBouncer 등)를 거쳐도 서버 쪽 prepared statement 를 쓰지 않는다
            pool = ConnectionPool(url, min_size=0, max_size=int(os.environ.get('AXPORT_DB_POOL_SIZE', '4')), open=True,
                                  timeout=max(5, timeout), check=ConnectionPool.check_connection, max_idle=120,
                                  kwargs={'prepare_threshold': None, 'connect_timeout': max(5, int(timeout))})
            _pools[url] = pool
        return pool


def close_pools():
    """테스트·종료용."""
    with _pools_lock:
        pools = list(_pools.values())
        _pools.clear()
    for pool in pools:
        pool.close()


# ---------- 행 ----------

class Row:
    """sqlite3.Row 처럼 row['열'], row[0], dict(row), 반복(값) 을 지원한다."""
    __slots__ = ('_keys', '_values')

    def __init__(self, keys, values):
        self._keys, self._values = keys, values

    def keys(self):
        return list(self._keys)

    def __getitem__(self, key):
        if isinstance(key, (int, slice)):
            return self._values[key]
        try:
            return self._values[self._keys.index(key)]
        except ValueError:
            raise IndexError('No item with that key') from None

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def __eq__(self, other):
        return isinstance(other, Row) and self._keys == other._keys and self._values == other._values

    def __repr__(self):
        return f'Row({dict(zip(self._keys, self._values))!r})'


def _plain(value):
    # SUM(BIGINT) 등은 Decimal 로 온다. SQLite 처럼 정수/실수로 돌려준다.
    if isinstance(value, decimal.Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, memoryview):
        return value.tobytes()
    return value


class Cursor:
    def __init__(self, rows=(), keys=(), rowcount=-1):
        self._rows, self._keys, self.rowcount = list(rows), tuple(keys), rowcount
        self._index = 0

    @classmethod
    def from_pg(cls, cur):
        if cur.description is None:
            return cls(rowcount=cur.rowcount)
        keys = tuple(d.name for d in cur.description)
        return cls([tuple(_plain(v) for v in r) for r in cur.fetchall()], keys, cur.rowcount)

    def _make(self, values):
        return Row(self._keys, values)

    def fetchone(self):
        if self._index >= len(self._rows):
            return None
        self._index += 1
        return self._make(self._rows[self._index - 1])

    def fetchall(self):
        rows, self._index = self._rows[self._index:], len(self._rows)
        return [self._make(r) for r in rows]

    def __iter__(self):
        while True:
            row = self.fetchone()
            if row is None:
                return
            yield row


# ---------- SQL 바꾸기 ----------

_DDL = re.compile(r'^\s*CREATE\s+(UNIQUE\s+)?(TABLE|INDEX)\s+IF\s+NOT\s+EXISTS\b', re.I)
_ALTER = re.compile(r'^\s*ALTER\s+TABLE\b', re.I)
_BEGIN = re.compile(r'^\s*BEGIN(\s+(IMMEDIATE|EXCLUSIVE|DEFERRED))?(\s+TRANSACTION)?\s*;?\s*$', re.I)
_COMMIT = re.compile(r'^\s*(COMMIT|END)(\s+TRANSACTION)?\s*;?\s*$', re.I)
_ROLLBACK = re.compile(r'^\s*ROLLBACK(\s+TRANSACTION)?\s*;?\s*$', re.I)
_PRAGMA = re.compile(r'^\s*PRAGMA\s+(\w+)\s*(?:\(\s*(\w+)\s*\)|=\s*\w+)?\s*;?\s*$', re.I)
_UPSERT = re.compile(r'^\s*INSERT\s+OR\s+(REPLACE|IGNORE)\s+INTO\s+(\w+)\s*(\(([^)]*)\))?', re.I)
_MAX2 = re.compile(r'\bMAX\(\s*([\w.]+)\s*,\s*([\w.]+)\s*\)', re.I)


def _outside_quotes(sql, fn):
    """작은따옴표 문자열 밖의 부분에만 fn 을 적용한다."""
    parts = re.split(r"('(?:[^']|'')*')", sql)
    return ''.join(p if i % 2 else fn(p) for i, p in enumerate(parts))


@lru_cache(maxsize=512)
def _translate(sql):
    if _DDL.match(sql) or _ALTER.match(sql):
        sql = _outside_quotes(sql, lambda s: re.sub(r'\bINTEGER\b', 'BIGINT', re.sub(
            r'\bREAL\b', 'DOUBLE PRECISION', re.sub(r'\bBLOB\b', 'BYTEA', s, flags=re.I), flags=re.I), flags=re.I))
    sql = _outside_quotes(sql, lambda s: _MAX2.sub(r'GREATEST(\1, \2)', s))
    # psycopg 는 문자열 안의 % 도 자리표시자로 읽으므로 모두 %% 로, ? 는 따옴표 밖만 %s 로
    sql = sql.replace('%', '%%')
    return _outside_quotes(sql, lambda s: s.replace('?', '%s'))


# ---------- 연결 ----------

_ddl_done, _ddl_lock = set(), threading.Lock()
_schema_cache = {}
DDL_LOCK_KEY = 0x41585054  # 'AXPT'


class PgConnection:
    """sqlite3.Connection 대용(이 프로젝트가 쓰는 범위만)."""

    def __init__(self, pool, name, aliases):
        self._pool, self._name = pool, name
        self._aliases = tuple(sorted(aliases.items()))
        self._conn = None
        self.row_factory = None  # sqlite3.Row 를 넣어도 무시(행은 늘 Row)
        self.isolation_level = ''

    # sqlite3 와 같은 속성·with 문
    @property
    def in_transaction(self):
        from psycopg.pq import TransactionStatus
        return self._conn is not None and self._conn.info.transaction_status != TransactionStatus.IDLE

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False

    def _raw(self):
        if self._conn is None:
            try:
                self._conn = self._pool.getconn()
            except Exception as exc:  # 풀 시간 초과·연결 실패
                raise PgOperationalError(str(exc)) from None
        return self._conn

    def commit(self):
        if self._conn is not None:
            try:
                self._conn.commit()
            except Exception as exc:
                raise _wrap(exc) from None

    def rollback(self):
        if self._conn is not None:
            try:
                self._conn.rollback()
            except Exception as exc:
                raise _wrap(exc) from None

    def close(self):
        conn, self._conn = self._conn, None
        if conn is not None:
            try:
                if not conn.closed:
                    conn.rollback()  # sqlite3 처럼 커밋하지 않은 변경은 버린다
            except Exception:
                pass
            self._pool.putconn(conn)

    def _lock_key(self):
        return zlib.crc32(('axport:' + self._name).encode('utf-8'))

    def _ddl(self, sql):
        """IF NOT EXISTS 정의문은 프로세스마다 한 번만, 별도 연결·별도 트랜잭션으로(같은 이름 동시 생성 경합은 잠금으로 막음)."""
        with _ddl_lock:
            if sql in _ddl_done:
                return
        try:
            with self._pool.connection() as conn:
                with conn.transaction():
                    conn.execute('SELECT pg_advisory_xact_lock(%s)', (DDL_LOCK_KEY,))
                    conn.execute(sql)
        except Exception as exc:
            raise _wrap(exc) from None
        with _ddl_lock:
            _ddl_done.add(sql)

    def _columns(self, table):
        cached = _schema_cache.get(table)
        if cached is None:
            with self._pool.connection() as conn:
                cols = [r[0] for r in conn.execute(
                    'SELECT column_name FROM information_schema.columns WHERE table_schema = current_schema() '
                    'AND table_name = %s ORDER BY ordinal_position', (table,))]
                pk = [r[0] for r in conn.execute(
                    "SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
                    "WHERE i.indrelid = to_regclass(%s) AND i.indisprimary", (table,))]
            cached = (cols, pk)
            if cols:
                _schema_cache[table] = cached
        return cached

    def _upsert(self, match, sql):
        mode, table, given = match.group(1).upper(), match.group(2), match.group(4)
        cols, pk = self._columns(table)
        if not cols:
            raise PgOperationalError(f'no such table: {table}')
        used = [c.strip() for c in given.split(',')] if given else cols
        rest = sql[match.end(2):]
        if mode == 'IGNORE' or not pk:
            tail = ' ON CONFLICT DO NOTHING'
        else:
            update = [c for c in used if c not in pk]
            tail = (f" ON CONFLICT ({', '.join(pk)}) DO UPDATE SET " + ', '.join(f'{c} = EXCLUDED.{c}' for c in update)
                    if update else f" ON CONFLICT ({', '.join(pk)}) DO NOTHING")
        return f'INSERT INTO {table}{rest.rstrip().rstrip(";")}{tail}'

    def _pragma(self, match):
        if match.group(1).lower() == 'table_info' and match.group(2):
            cols, pk = self._columns(match.group(2))
            return Cursor([(i, c, '', 0, None, int(c in pk)) for i, c in enumerate(cols)],
                          ('cid', 'name', 'type', 'notnull', 'dflt_value', 'pk'))
        return Cursor()  # journal_mode·synchronous 등: Postgres 에는 해당 없음

    def execute(self, sql, params=()):
        if _BEGIN.match(sql):
            conn = self._raw()
            if self.in_transaction:
                self.commit()  # isolation_level=None 의 SQLite 처럼, 앞선 문장은 이미 확정된 것으로
            return self._run(conn, 'SELECT pg_advisory_xact_lock(%s)', (self._lock_key(),))
        if _COMMIT.match(sql):
            self.commit()
            return Cursor()
        if _ROLLBACK.match(sql):
            self.rollback()
            return Cursor()
        pragma = _PRAGMA.match(sql)
        if pragma:
            return self._pragma(pragma)
        for old, new in self._aliases:
            sql = re.sub(rf'\b{re.escape(old)}\b', new, sql)
        if _DDL.match(sql):
            self._ddl(_translate(sql).replace('%%', '%'))
            return Cursor()
        upsert = _UPSERT.match(sql)
        if upsert:
            sql = self._upsert(upsert, sql)
        return self._run(self._raw(), _translate(sql), tuple(params or ()))

    def _run(self, conn, sql, params):
        try:
            cur = conn.execute(sql, params)
            return Cursor.from_pg(cur)
        except Exception as exc:
            raise _wrap(exc) from None

    def executemany(self, sql, seq):
        total = 0
        for params in seq:
            cur = self.execute(sql, params)
            total += max(cur.rowcount, 0)
        return Cursor(rowcount=total)

    def executescript(self, script):
        if self.in_transaction:
            self.commit()  # sqlite3.executescript 도 먼저 COMMIT 한다
        for statement in script.split(';'):
            if statement.strip():
                self.execute(statement)
        if self.in_transaction:
            self.commit()
        return Cursor()


atexit.register(close_pools)  # 인터프리터 종료 중에는 풀 스레드를 정리할 수 없으므로 그 전에 닫는다
