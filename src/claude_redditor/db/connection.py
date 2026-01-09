"""MariaDB/MySQL connection pool using SQLAlchemy."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
import logging

Base = declarative_base()
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    MariaDB/MySQL connection pool using SQLAlchemy.

    Features:
    - Connection pooling (5 permanent, 10 overflow)
    - Auto-reconnect if connection is lost
    - Context manager for sessions
    """

    def __init__(self, config):
        """
        Initialize database connection pool.

        Args:
            config: Settings object with MySQL configuration
        """
        # Build connection string
        connection_string = (
            f"mysql+pymysql://{config.mysql_user}:{config.mysql_password}"
            f"@{config.mysql_host}:{config.mysql_port}/{config.mysql_database}"
            f"?charset=utf8mb4"
        )

        # Create engine with connection pool
        self.engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=5,                    # 5 permanent connections
            max_overflow=10,                # 10 extra on spike
            pool_timeout=30,                # 30s timeout waiting for connection
            pool_recycle=3600,              # Recycle every 1h (avoid timeouts)
            pool_pre_ping=True,             # Verify connection before use
            echo=config.debug,              # Log SQL queries if debug=True
        )

        # Session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        logger.info(f"Database connection pool initialized: {config.mysql_host}:{config.mysql_port}")

    @contextmanager
    def get_session(self) -> Generator:
        """
        Context manager to get a session.

        Usage:
            with db.get_session() as session:
                session.query(Model).all()

        Auto-commit on success, auto-rollback on exception.
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    def init_db(self):
        """
        Create all tables defined in models.py.
        Idempotent: does not fail if tables already exist.
        """
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database schema initialized")

    def test_connection(self) -> bool:
        """Basic connectivity test."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection test: OK")
            return True
        except Exception as e:
            logger.error(f"Database connection test FAILED: {e}")
            return False
