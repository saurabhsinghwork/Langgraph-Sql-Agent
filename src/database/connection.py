"""Database connection management using SQLAlchemy for MCA and GST databases.

Manages SQLAlchemy engines, connection lifecycles, connection pooling,
and safe connection testing for both MCA and GST databases without exposing credentials.
"""

from __future__ import annotations

# [Built-in Python Module: logging]: Event logging framework
import logging
# [Built-in Python Module: typing]: Type annotation helpers (Tuple, Optional, Dict)
from typing import Tuple, Optional, Dict
# [Library Imports: sqlalchemy]: Database abstraction layer functions
from sqlalchemy import create_engine, text
# [Library Imports: sqlalchemy.engine.Engine]: Type definition for the connection pool engine
from sqlalchemy.engine import Engine
# [Library Imports: sqlalchemy.exc.SQLAlchemyError]: Base exception class for SQLAlchemy errors
from sqlalchemy.exc import SQLAlchemyError

# [Project-Defined Imports from src.config.settings]: Application settings class and singleton getter
from src.config.settings import AppSettings, get_settings

# [Library Instance: logging.Logger]: Logger for tracking connection lifecycle events
logger = logging.getLogger(__name__)

# [Project-Defined Global Variable: Dict[str, Engine]]: Cached singleton SQLAlchemy Engine instances keyed by db_type ('mca', 'gst')
_engine_instances: Dict[str, Engine] = {}


# [Project-Defined Function]: Factory managing singleton Engine lifecycle with dynamic reconnection per database
def get_engine(
    db_type: str = "mca",
    settings: Optional[AppSettings] = None,
    force_new: bool = False,
) -> Engine:
    """Get or create the SQLAlchemy database engine singleton for MCA or GST database.

    Automatically refreshes if connection URL has changed.

    Args:
        db_type: Target database ('mca' or 'gst').
        settings: Optional custom AppSettings. If None, loaded from environment.
        force_new: If True, creates a new engine instance instead of returning cached.

    Returns:
        SQLAlchemy Engine instance.
    """
    # [Built-in Python: global]: Declare global variable for caching
    global _engine_instances
    # [Project-Defined Function: get_settings]: Retrieve settings singleton if not passed
    if settings is None:
        settings = get_settings()

    # [Built-in Python Method: str.lower]: Normalize database type identifier
    norm_type = db_type.lower().strip()
    # [Project-Defined Method: AppSettings.get_sqlalchemy_url]: Compute database connection URL
    url = settings.get_sqlalchemy_url(db_type=norm_type)

    cached_engine = _engine_instances.get(norm_type)

    # Recreate engine if URL changed (e.g. switched to SQLite fallback or changed database)
    if cached_engine is not None and not force_new:
        # [Library Property: Engine.url]: Compare cached engine URL with current target URL
        if str(cached_engine.url) != url:
            try:
                # [Library Method: Engine.dispose]: Close all checked-in pooled DB connections
                cached_engine.dispose()
            except Exception:
                pass
            _engine_instances.pop(norm_type, None)
            cached_engine = None

    # Check if new engine instantiation is required
    if cached_engine is None or force_new:
        # [Variable: dict]: Keyword arguments passed to SQLAlchemy create_engine
        engine_kwargs = {
            # 'pool_pre_ping' sends a test ping query before issuing connection to caller
            "pool_pre_ping": True,
        }

        # For SQLite, add thread-safety argument
        if url.startswith("sqlite"):
            # 'check_same_thread=False' allows SQLite connection to be shared across threads
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        else:
            # PyMySQL connection parameters: recycle connections hourly and enforce timeouts
            engine_kwargs["pool_recycle"] = 3600
            engine_kwargs["connect_args"] = {
                "connect_timeout": settings.sql_query_timeout_seconds,
                "read_timeout": settings.sql_query_timeout_seconds,
                "write_timeout": settings.sql_query_timeout_seconds,
            }

        # [Library Function: sqlalchemy.create_engine]: Instantiate database connection engine
        new_engine = create_engine(url, **engine_kwargs)
        _engine_instances[norm_type] = new_engine
        # [Library Method: Logger.info]: Log sanitized target without exposing credentials
        logger.info(
            "Initialized SQLAlchemy engine for %s target: %s",
            norm_type.upper(),
            url.split("@")[-1] if "@" in url else url,
        )

    # Return active engine instance
    return _engine_instances[norm_type]


# [Project-Defined Function]: Shortcut acquiring MCA database engine
def get_mca_engine(settings: Optional[AppSettings] = None, force_new: bool = False) -> Engine:
    """Get SQLAlchemy engine for MCA database."""
    return get_engine(db_type="mca", settings=settings, force_new=force_new)


# [Project-Defined Function]: Shortcut acquiring GST database engine
def get_gst_engine(settings: Optional[AppSettings] = None, force_new: bool = False) -> Engine:
    """Get SQLAlchemy engine for GST database."""
    return get_engine(db_type="gst", settings=settings, force_new=force_new)


# [Project-Defined Function]: Validates database reachability using a non-destructive ping query
def test_connection(
    db_type: str = "mca",
    settings: Optional[AppSettings] = None,
) -> Tuple[bool, str]:
    """Test database connectivity with a lightweight ping query.

    Args:
        db_type: 'mca' or 'gst'.
        settings: Application settings.

    Returns:
        Tuple of (is_connected: bool, message: str).
        The message is safe to display to users and contains no credentials.
    """
    # [Project-Defined Function: get_settings]: Retrieve settings if omitted
    if settings is None:
        settings = get_settings()

    norm_type = db_type.lower().strip()
    db_name_label = "MCA Corporate" if norm_type == "mca" else "GST Taxpayer"

    try:
        # [Project-Defined Function: get_engine]: Obtain active SQLAlchemy Engine for db_type
        engine = get_engine(db_type=norm_type, settings=settings)
        # [Library Context Manager: Engine.connect]: Acquire connection from pool
        with engine.connect() as conn:
            # [Library Function: sqlalchemy.text]: Wrap raw SQL string into executable ClauseElement
            conn.execute(text("SELECT 1"))
        # [Variable: str]: Friendly human-readable target name
        if settings.use_sqlite_fallback:
            target_path = settings.gst_sqlite_db_path if norm_type == "gst" else settings.mca_sqlite_db_path
            target = f"Local SQLite ({target_path})"
        else:
            target_db = settings.gst_mysql_database if norm_type == "gst" else settings.mca_mysql_database
            target = f"MySQL ({settings.mysql_host}:{settings.mysql_port}/{target_db})"

        return True, f"Successfully connected to {db_name_label} [{target}]."
    # [Library Exception: sqlalchemy.exc.SQLAlchemyError]: Catch database-specific connection issues
    except SQLAlchemyError as exc:
        # [Library Method: Logger.error]: Log database failure
        logger.error("%s database connection failed: %s", db_name_label, type(exc).__name__)
        # [Built-in Python: type().__name__]: Get exact error class name
        err_type = type(exc).__name__
        if not settings.use_sqlite_fallback:
            target_db = settings.gst_mysql_database if norm_type == "gst" else settings.mca_mysql_database
            return (
                False,
                f"{db_name_label} MySQL connection failed ({err_type}) on {settings.mysql_host}:{settings.mysql_port}/{target_db}. "
                "Set USE_SQLITE_FALLBACK=true in .env to use the local SQLite database.",
            )
        target_path = settings.gst_sqlite_db_path if norm_type == "gst" else settings.mca_sqlite_db_path
        return False, f"{db_name_label} connection failed ({err_type}). Verify '{target_path}' exists and is readable."
    # [Built-in Python: Exception]: Catch unexpected errors
    except Exception as exc:
        logger.error("Unexpected error connecting to %s database: %s", db_name_label, type(exc).__name__)
        return False, f"Unexpected connection error for {db_name_label}: {type(exc).__name__}"


# [Project-Defined Function]: Tests connectivity for both MCA and GST databases simultaneously
def test_all_connections(settings: Optional[AppSettings] = None) -> Dict[str, Tuple[bool, str]]:
    """Test connectivity for both MCA and GST databases."""
    if settings is None:
        settings = get_settings()
    return {
        "mca": test_connection(db_type="mca", settings=settings),
        "gst": test_connection(db_type="gst", settings=settings),
    }
