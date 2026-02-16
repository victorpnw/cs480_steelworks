"""
Database Connection and Session Management

This module manages database connectivity, session lifecycle, and engine configuration.
It provides a centralized place to initialize and manage SQLAlchemy connections.

Resource Management:
  - Sessions are properly closed via context managers to prevent connection leaks
  - Connection pooling is configured to manage connection limits
  - Scoped sessions are used for thread-safe access in multi-threaded environments

Time Complexity: 
  - get_engine(): O(1) - returns cached engine (initialized once at startup)
  - get_session(): O(1) - creates/returns session from pool
  
Space Complexity: O(c) where c is the connection pool size (default 5)
"""

import os
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class DatabaseConfig:
    """
    Configuration class for database connection settings.
    
    Attributes:
        DATABASE_URL (str): PostgreSQL connection string from environment or default
        POOL_SIZE (int): Number of connections to maintain in the pool
        MAX_OVERFLOW (int): Maximum overflow connections beyond pool size
        POOL_TIMEOUT (int): Timeout in seconds for getting a connection from the pool
        ECHO_SQL (bool): Whether to log all SQL statements (debugging)
    
    Environment Variables (set in .env file):
        - DATABASE_URL: format "postgresql://user:password@host:port/database"
        - DB_POOL_SIZE: default 5
        - DB_MAX_OVERFLOW: default 10
        - DB_POOL_TIMEOUT: default 30
        - DB_ECHO_SQL: default False
    """
    
    # Default values - override via environment variables
    DEFAULT_DATABASE_URL = (
        "postgresql://postgres:postgres@localhost:5432/steelworks"
    )
    
    def __init__(self):
        """Initialize database configuration from environment variables"""
        self.DATABASE_URL = os.getenv("DATABASE_URL", self.DEFAULT_DATABASE_URL)
        self.POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 5))
        self.MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", 10))
        self.POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", 30))
        self.ECHO_SQL = os.getenv("DB_ECHO_SQL", "False").lower() == "true"


# Global database configuration instance
_db_config = DatabaseConfig()

# Global engine and session factory (initialized once)
_engine = None
_SessionLocal = None
_SessionScoped = None


def get_engine():
    """
    Get or create the SQLAlchemy engine.
    
    The engine is created once and cached. It manages the connection pool and
    is responsible for all database interactions.
    
    Returns:
        sqlalchemy.engine.Engine: Database engine configured with connection pooling
    
    Connection Pooling:
        - pool_size: Number of connections to keep ready (AC1 performance critical)
        - max_overflow: Additional connections for surge demands
        - pool_timeout: Wait time for connection availability
        - poolclass: QueuePool for fast connection retrieval
    
    Resource Management:
        - Connections are automatically returned to the pool when sessions close
        - Echo SQL can be enabled for debugging via DB_ECHO_SQL environment variable
    """
    global _engine
    if _engine is None:
        _engine = create_engine(
            _db_config.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=_db_config.POOL_SIZE,
            max_overflow=_db_config.MAX_OVERFLOW,
            pool_timeout=_db_config.POOL_TIMEOUT,
            echo=_db_config.ECHO_SQL,
        )
    return _engine


def get_session_factory():
    """
    Get or create the SQLAlchemy session factory.
    
    The session factory is used to create new Session instances. Each session
    represents a unit of work with the database.
    
    Returns:
        sqlalchemy.orm.sessionmaker: Factory for creating new Session objects
    """
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def get_session() -> Session:
    """
    Get a new database session.
    
    Each call creates a new Session instance. Sessions should be used with
    context managers to ensure proper cleanup.
    
    Returns:
        sqlalchemy.orm.Session: New database session
    
    Usage (Recommended):
        >>> with get_session() as session:
        ...     users = session.query(User).all()
        ...     # Session is automatically closed and connection returned to pool
    
    Time Complexity: O(1) - connection acquisition from pool
    Space Complexity: O(1) - constant session overhead
    """
    SessionLocal = get_session_factory()
    return SessionLocal()


def get_scoped_session():
    """
    Get the thread-scoped session (for multi-threaded environments).
    
    Scoped sessions ensure thread safety in multi-threaded applications.
    Each thread gets its own session instance.
    
    Returns:
        sqlalchemy.orm.scoped_session: Thread-local session registry
    """
    global _SessionScoped
    if _SessionScoped is None:
        SessionLocal = get_session_factory()
        _SessionScoped = scoped_session(SessionLocal)
    return _SessionScoped


def init_db():
    """
    Initialize the database by creating all tables defined in ORM models.
    
    This function should be called once at application startup to ensure
    all tables exist. It uses the declarative_base from orm_models.
    
    Usage:
        >>> from src.models.orm_models import Base
        >>> init_db()
    
    Note: This is idempotent - calling multiple times is safe (CREATE TABLE IF NOT EXISTS)
    """
    from src.models.orm_models import Base
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def session_generator() -> Generator[Session, None, None]:
    """
    Generator function for dependency injection of sessions.
    
    Useful for frameworks that support dependency injection (e.g., FastAPI, Starlette).
    Yields a session and ensures cleanup happens in the finally block.
    
    Yield:
        sqlalchemy.orm.Session: Database session for the operation
    
    Resource Management:
        - Session is properly closed in finally block regardless of exceptions
        - Prevents connection leaks in long-running applications
    
    Usage (with FastAPI):
        >>> @app.get("/defects")
        ... def list_defects(session: Session = Depends(session_generator)):
        ...     return session.query(DefectORM).all()
    """
    session = get_session()
    try:
        yield session
    finally:
        session.close()


def close_all_sessions():
    """
    Close all active sessions and dispose of the engine.
    
    This should be called at application shutdown to clean up resources.
    Useful for testing and graceful application termination.
    
    Resource Cleanup:
        - Closes the scoped session registry if exists
        - Disposes of the engine (closes all pooled connections)
    
    Time Complexity: O(n) where n is number of active connections
    Space Complexity: O(1) - resources are deallocated
    """
    global _SessionScoped, _engine
    
    if _SessionScoped is not None:
        _SessionScoped.remove()
        _SessionScoped = None
    
    if _engine is not None:
        _engine.dispose()
        _engine = None
