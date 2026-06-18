import os
import time
import logging
import re
from functools import wraps
from typing import Optional, Any
from contextlib import contextmanager
from extensions import db
import psycopg2
import psycopg2.extras

class RowWrapper:
    def __init__(self, row):
        self._row = row
        if hasattr(row, '_mapping'):
            self._mapping = row._mapping
        elif hasattr(row, 'keys'):
            try:
                self._mapping = {k: row[k] for k in row.keys()}
            except Exception:
                self._mapping = {}
        else:
            self._mapping = {}

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._row[key]
        if self._mapping and key in self._mapping:
            return self._mapping[key]
        try:
            return self._row[key]
        except Exception:
            if isinstance(key, str) and key.isdigit():
                try:
                    return self._row[int(key)]
                except Exception:
                    pass
            raise KeyError(key)

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        try:
            return getattr(self._row, name)
        except AttributeError:
            if self._mapping and name in self._mapping:
                return self._mapping[name]
            try:
                return self._row[name]
            except Exception:
                raise AttributeError(name)

    def __len__(self):
        return len(self._row)

    def __iter__(self):
        return iter(self._row)

    def keys(self):
        return self._mapping.keys()

    def values(self):
        return self._mapping.values()

    def items(self):
        return self._mapping.items()

    def get(self, key, default=None):
        return self._mapping.get(key, default)


SLOW_QUERY_THRESHOLD = 1.0  # seconds
MAX_RETRIES = 3
INITIAL_BACKOFF = 0.5  # seconds

logger = logging.getLogger("db_performance")

def _configure_connection_row_factory(conn):
    """Ensure SQLite row_factory returns dictionary-like rows for test environment."""
    try:
        if hasattr(conn, 'dbapi_connection'):
            dbapi_conn = conn.dbapi_connection
            import sqlite3
            if isinstance(dbapi_conn, sqlite3.Connection):
                dbapi_conn.row_factory = sqlite3.Row
    except Exception:
        pass

def _prepare_query_and_params(sql: str, params: Any, is_postgres: bool):
    """
    Translates parameter syntax between PostgreSQL (%s / %(name)s) and SQLite (? / :name).
    Also strips escaped double-colons introduced by SQLAlchemy text parser.
    """
    # FIX: Translate Postgres-specific syntax to SQLite compatible syntax during testing
    if not is_postgres:
        sql = sql.replace('\\:\\:', '::')
        
        # Replace TO_CHAR(..., 'Mon YYYY') -> strftime('%m-%Y', ...)
        sql = re.sub(r"TO_CHAR\((.*?),\s*['\"]Mon YYYY['\"]\)", r"strftime('%m-%Y', \1)", sql, flags=re.IGNORECASE)
        
        # Replace TO_CHAR(..., 'Mon DD') -> strftime('%m-%d', ...)
        sql = re.sub(r"TO_CHAR\((.*?),\s*['\"]Mon DD['\"]\)", r"strftime('%m-%d', \1)", sql, flags=re.IGNORECASE)
        
        # Replace DATE_TRUNC('month', ...) -> strftime('%Y-%m-01', ...)
        sql = re.sub(r"DATE_TRUNC\(['\"]month['\"],\s*(.*?)\)", r"strftime('%Y-%m-01', \1)", sql, flags=re.IGNORECASE)
        
        # Replace double-colon casts, e.g., expression::type -> CAST(expression AS type)
        # Handle simple expressions/function calls (e.g., column::text or SUM(...)::float)
        sql = re.sub(r"(\b[a-zA-Z0-9_\.\*]+(?:\([^()]*\))?)::([a-zA-Z_]+)", r"CAST(\1 AS \2)", sql)
        # Handle parenthesized expressions without nesting (e.g., (a+b)::float)
        sql = re.sub(r"\(([^()]+)\)::([a-zA-Z_]+)", r"CAST(\1 AS \2)", sql)
    else:
        sql = sql.replace('\\:\\:', '::')

    if params is None:
        return sql, None
        
    if isinstance(params, (list, tuple)):
        if is_postgres:
            return sql, params
        else:
            # SQLite positional placeholder is '?'
            new_sql = sql.replace('%s', '?')
            return new_sql, params
            
    elif isinstance(params, dict):
        if is_postgres:
            # Postgres/psycopg2 named parameter format is %(name)s
            # Find :name and convert to %(name)s, avoiding double-colon casts (e.g., ::TEXT)
            pattern = re.compile(r'(?<!:):([a-zA-Z_][a-zA-Z0-9_]*)')
            new_sql = pattern.sub(r'%(\1)s', sql)
            return new_sql, params
        else:
            # SQLite natively supports :name format
            return sql, params
            
    return sql, params

@contextmanager
def get_public_db():
    """Opens a connection scoped to the shared public schema."""
    from flask import current_app
    is_testing = False
    try:
        if current_app and current_app.config.get("TESTING"):
            is_testing = True
    except RuntimeError:
        pass

    if is_testing:
        conn = db.session.connection().connection
        _configure_connection_row_factory(conn)
        cur = conn.cursor()
        try:
            yield cur
        finally:
            cur.close()
    else:
        conn = db.engine.raw_connection()
        _configure_connection_row_factory(conn)
        try:
            is_postgres = db.engine.dialect.name == 'postgresql'
            if is_postgres:
                cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                cur.execute("SET search_path TO public")
            else:
                cur = conn.cursor()
            yield cur
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

@contextmanager
def get_tenant_db():
    """Opens a connection scoped to the current active tenant schema."""
    try:
        from utils.tenant_context import get_tenant_schema
        schema = get_tenant_schema()
    except Exception:
        schema = 'public'
        
    from flask import current_app
    is_testing = False
    try:
        if current_app and current_app.config.get("TESTING"):
            is_testing = True
    except RuntimeError:
        pass

    if is_testing:
        conn = db.session.connection().connection
        _configure_connection_row_factory(conn)
        cur = conn.cursor()
        try:
            yield cur
        finally:
            cur.close()
    else:
        conn = db.engine.raw_connection()
        _configure_connection_row_factory(conn)
        try:
            is_postgres = db.engine.dialect.name == 'postgresql'
            if is_postgres:
                cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                cur.execute(f"SET search_path TO {schema}, public")
            else:
                cur = conn.cursor()
            yield cur
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()


def get_db():
    """Returns a connection wrapper for backward compatibility with manual connection management."""
    try:
        from utils.tenant_context import get_tenant_schema
        schema = get_tenant_schema()
    except Exception:
        schema = 'public'
        
    conn = db.engine.raw_connection()
    _configure_connection_row_factory(conn)
    is_postgres = db.engine.dialect.name == 'postgresql'
    
    if is_postgres:
        cur = conn.cursor()
        cur.execute(f"SET search_path TO {schema}, public")
        cur.close()
        
    class RawConnectionWrapper:
        def __init__(self, raw_conn, is_pg):
            self.raw_conn = raw_conn
            self.is_pg = is_pg
            self._active_cursors = []

        def execute(self, sql, params=None):
            sql, params = _prepare_query_and_params(sql, params, self.is_pg)
            if self.is_pg:
                cur = self.raw_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            else:
                cur = self.raw_conn.cursor()
            # FIX: Avoid passing None as parameters to SQLite cursor.execute()
            if params is not None:
                cur.execute(sql, params)
            else:
                cur.execute(sql)
            self._active_cursors.append(cur)
            return cur

        def cursor(self, *args, **kwargs):
            if self.is_pg and 'cursor_factory' not in kwargs:
                kwargs['cursor_factory'] = psycopg2.extras.DictCursor
            cur = self.raw_conn.cursor(*args, **kwargs)
            self._active_cursors.append(cur)
            return cur

        def commit(self):
            self.raw_conn.commit()

        def rollback(self):
            self.raw_conn.rollback()

        def close(self):
            for cur in self._active_cursors:
                try:
                    cur.close()
                except Exception:
                    pass
            self.raw_conn.close()

    return RawConnectionWrapper(conn, is_postgres)



def transactional(f):
    """Decorator to wrap a function in a database transaction."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            db.session.commit()
            return result
        except Exception as e:
            db.session.rollback()
            logger.error(f"Transaction failed: {str(e)}")
            raise e
    return decorated_function


# Scoped Database Accessors (Automatic context retrieval)
def qry(sql, params=None, timeout=30):
    is_postgres = db.engine.dialect.name == 'postgresql'
    sql, params = _prepare_query_and_params(sql, params, is_postgres)
    
    start_time = time.time()
    with get_tenant_db() as cur:
        # FIX: Avoid passing None as parameters to SQLite cursor.execute()
        if params is not None:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        res = cur.fetchall()
        
        duration = time.time() - start_time
        if duration > SLOW_QUERY_THRESHOLD:
            logger.warning(f"SLOW QUERY ({duration:.2f}s): {sql} | Params: {params}")
            
        return [RowWrapper(r) for r in res]

def qone(sql, params=None, timeout=30):
    is_postgres = db.engine.dialect.name == 'postgresql'
    sql, params = _prepare_query_and_params(sql, params, is_postgres)
    
    start_time = time.time()
    with get_tenant_db() as cur:
        # FIX: Avoid passing None as parameters to SQLite cursor.execute()
        if params is not None:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        res = cur.fetchone()
        
        duration = time.time() - start_time
        if duration > SLOW_QUERY_THRESHOLD:
            logger.warning(f"SLOW QUERY ({duration:.2f}s): {sql} | Params: {params}")
            
        return RowWrapper(res) if res is not None else None

def exe(sql, params=None, timeout=30):
    is_postgres = db.engine.dialect.name == 'postgresql'
    sql, params = _prepare_query_and_params(sql, params, is_postgres)
    
    start_time = time.time()
    with get_tenant_db() as cur:
        # FIX: Avoid passing None as parameters to SQLite cursor.execute()
        if params is not None:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        
        duration = time.time() - start_time
        if duration > SLOW_QUERY_THRESHOLD:
            logger.warning(f"SLOW QUERY ({duration:.2f}s): {sql} | Params: {params}")
            
        return cur


# Replica Connection & Routing Layer
replica_engine = None

def get_replica_engine():
    global replica_engine
    if replica_engine is None:
        replica_url = os.environ.get("REPLICA_DATABASE_URL")
        if replica_url:
            from sqlalchemy import create_engine
            replica_engine = create_engine(
                replica_url,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=1800
            )
        else:
            replica_engine = db.engine
    return replica_engine

@contextmanager
def get_tenant_read_db():
    """Opens a connection to the replica database scoped to the current tenant schema."""
    try:
        from utils.tenant_context import get_tenant_schema
        schema = get_tenant_schema()
    except Exception:
        schema = 'public'
        
    engine = get_replica_engine()
    conn = engine.raw_connection()
    _configure_connection_row_factory(conn)
    try:
        is_postgres = engine.dialect.name == 'postgresql'
        if is_postgres:
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute(f"SET search_path TO {schema}, public")
        else:
            cur = conn.cursor()
        yield cur
    finally:
        conn.close()

def qry_read(sql, params=None, timeout=30):
    is_postgres = get_replica_engine().dialect.name == 'postgresql'
    sql, params = _prepare_query_and_params(sql, params, is_postgres)
    
    start_time = time.time()
    with get_tenant_read_db() as cur:
        # FIX: Avoid passing None as parameters to SQLite cursor.execute()
        if params is not None:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        res = cur.fetchall()
        
        duration = time.time() - start_time
        if duration > SLOW_QUERY_THRESHOLD:
            logger.warning(f"SLOW REPLICA QUERY ({duration:.2f}s): {sql} | Params: {params}")
            
        return [RowWrapper(r) for r in res]

def qone_read(sql, params=None, timeout=30):
    is_postgres = get_replica_engine().dialect.name == 'postgresql'
    sql, params = _prepare_query_and_params(sql, params, is_postgres)
    
    start_time = time.time()
    with get_tenant_read_db() as cur:
        # FIX: Avoid passing None as parameters to SQLite cursor.execute()
        if params is not None:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        res = cur.fetchone()
        
        duration = time.time() - start_time
        if duration > SLOW_QUERY_THRESHOLD:
            logger.warning(f"SLOW REPLICA QUERY ({duration:.2f}s): {sql} | Params: {params}")
            
        return RowWrapper(res) if res is not None else None
