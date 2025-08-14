# infrastructure/db/mysql/base.py
import os
from typing import Any, Iterable, Optional, Sequence
from infrastructure.db.mysql.pool import Pool
from utils.logger import get_logger  # <-- твой логгер

import pymysql
from pymysql import err as pymysql_err

logger = get_logger("SyncDatabase")


class SyncDatabase:
    def __init__(self, host, port, user, password, db):
        self._db_params = {
            "host": host,
            "port": int(port),
            "user": user,
            "password": password,
            "db": db,
            "autocommit": True,
            "charset": "utf8mb4",
            "cursorclass": pymysql.cursors.DictCursor}

        self._pool = Pool(create_instance=lambda: pymysql.connect(**self._db_params),
                            max_count=int(os.getenv("MYSQL_POOL_SIZE", "10")),
                            timeout=float(os.getenv("MYSQL_POOL_GET_TIMEOUT", "10")),
                            pre_ping=True,
                            recycle=int(os.getenv("MYSQL_POOL_RECYCLE", "1800")))

    def _run_with_retry(self, fn):
        try:
            conn = self._pool.acquire()
            try:
                return fn(conn)
            finally:
                self._pool.release(conn)
        except (pymysql_err.InterfaceError, pymysql_err.OperationalError) as e:
            logger.warning(f"MySQL interface/operational error '{e}'. Retrying once...")
            conn = self._pool.acquire()
            try:
                return fn(conn)
            finally:
                self._pool.release(conn)

    def execute_query(self, query: str, params: Optional[Sequence[Any] | dict] = None):
        def _do(conn):
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        return self._run_with_retry(_do)

    def execute_scalar(self, query: str, params: Optional[Sequence[Any] | dict] = None):
        rows = self.execute_query(query, params)
        return next(iter(rows[0].values())) if rows else None

    def execute_non_query(self, query: str, params: Optional[Sequence[Any] | dict] = None):
        def _do(conn):
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return {"rowcount": cursor.rowcount, "lastrowid": getattr(cursor, "lastrowid", None)}
            
        return self._run_with_retry(_do)

    def execute_many(self, query: str, param_list: Iterable[Sequence[Any] | dict]):
        plist = list(param_list)
        if not plist:
            return 0

        def _do(conn):
            with conn.cursor() as cursor:
                cursor.executemany(query, plist)
                return cursor.rowcount
        return self._run_with_retry(_do)

    def close(self):
        self._pool.close_all()
