import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager

from config import get_settings

logger = logging.getLogger(__name__)

_pool: SimpleConnectionPool | None = None


def _get_pool() -> SimpleConnectionPool:
    """Lazy-initialize the connection pool."""
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=settings.database_url,
        )
        logger.info("PostgreSQL connection pool initialized")
    return _pool


@contextmanager
def get_db_connection():
    """Get a database connection from the pool."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


@contextmanager
def get_db_cursor(cursor_factory=RealDictCursor):
    """Get a cursor with automatic commit/rollback."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def init_schema() -> None:
    """Initialize database schema from schema.sql."""
    import pathlib

    schema_path = pathlib.Path(__file__).parent / "schema.sql"
    with open(schema_path, "r") as f:
        sql = f.read()

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            conn.commit()
        logger.info("Database schema initialized")


def health_check() -> bool:
    """Check database connectivity."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
