# infrastructure/db/mysql/pool.py
import time
import threading
import pymysql
from utils.logger import get_logger

logger = get_logger("MySQLPool")


class Pool:
    """Простой потокобезопасный пул с pre_ping и recycle."""
    def __init__(self, create_instance, max_count=10, timeout=10.0, *, pre_ping=True, recycle=1800):
        assert create_instance is not None
        self._create = create_instance
        self._max = int(max_count)
        self._timeout = float(timeout)
        self._pre_ping = bool(pre_ping)
        self._recycle = int(recycle)

        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._free: list[pymysql.connections.Connection] = []
        self._in_use: set[pymysql.connections.Connection] = set()

    def _spawn(self) -> pymysql.connections.Connection:
        conn = self._create()
        conn._created_at = time.time()  # служебная метка для recycle
        logger.debug("Spawned new MySQL connection")
        return conn

    def _need_recycle(self, conn: pymysql.connections.Connection) -> bool:
        created = getattr(conn, "_created_at", None)
        return created is None or (time.time() - created) >= self._recycle

    def acquire(self) -> pymysql.connections.Connection:
        with self._lock:
            # есть свободные
            if self._free:
                conn = self._free.pop()
                self._in_use.add(conn)
            # можно создать новый
            elif len(self._in_use) < self._max:
                conn = self._spawn()
                self._in_use.add(conn)
            else:
                # ждём освобождения
                end = time.time() + self._timeout
                logger.debug("Pool exhausted; waiting for a free connection")
                while not self._free:
                    remain = end - time.time()
                    if remain <= 0:
                        logger.warning("Pool acquire timeout (max=%d, in_use=%d)", self._max, len(self._in_use))
                        raise TimeoutError("Pool acquire timeout")
                    self._cv.wait(remain)
                conn = self._free.pop()
                self._in_use.add(conn)

        try:
            if self._pre_ping:
                try:
                    conn.ping(reconnect=True)
                except Exception as e:
                    logger.warning("Pre-ping failed, recreating connection: %s", e)
                    try:
                        conn.close()
                    except Exception:
                        pass
                    conn = self._spawn()

            if self._need_recycle(conn):
                logger.debug("Recycling MySQL connection")
                try:
                    conn.close()
                except Exception:
                    pass
                conn = self._spawn()

            conn._last_used = time.time()
            return conn
        except Exception:
            self.release(conn)
            raise

    def release(self, conn: pymysql.connections.Connection):
        with self._lock:
            if conn in self._in_use:
                self._in_use.remove(conn)
                self._free.append(conn)
                self._cv.notify()

    def close_all(self):
        with self._lock:
            for conn in self._free:
                try:
                    conn.close()
                except Exception:
                    pass
            self._free.clear()
        logger.info("Closed all free MySQL connections in pool")
