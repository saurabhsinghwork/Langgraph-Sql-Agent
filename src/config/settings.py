"""Configuration module for LangGraph SQL Agent supporting MCA and GST databases.

Loads environment variables from `.env` using Pydantic Settings,
validates required fields, enforces safe bounds on retries/row limits,
and manages connection targets for both MCA and GST databases.
"""

from __future__ import annotations

# [Built-in Python Module: os]: Access to operating system environment variables
import os
# [Built-in Python Module: pathlib.Path]: Object-oriented filesystem path manipulation
from pathlib import Path
# [Built-in Python Module: typing]: Type hinting primitives
from typing import Any, Optional
# [Library Imports: pydantic]: Field descriptor and validation decorator for schema definitions
from pydantic import Field, field_validator
# [Library Imports: pydantic_settings]: Base class for environment-driven settings configuration
from pydantic_settings import BaseSettings, SettingsConfigDict


# [Project-Defined Class]: Inherits from pydantic_settings.BaseSettings
# Defines strongly-typed configuration schema populated automatically from .env or environment
class AppSettings(BaseSettings):
    """Application settings with environment variable loading and validation for MCA and GST databases."""

    # [Library Class Instance: SettingsConfigDict from pydantic_settings]
    # Configures Pydantic to read '.env' in UTF-8 encoding and ignore unmapped extra keys
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Gemini LLM Configuration ---
    # [Project-Defined Attribute: str]: API key for Google Gemini LLM
    # [Library Function: pydantic.Field]: Declares field metadata and default value
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key used for LangGraph model calls.",
    )
    # [Project-Defined Attribute: str]: Model family string identifier
    gemini_model_id: str = Field(
        default="gemini-3.5-flash-lite",
        description="Gemini model identifier (must be from the Flash-Lite family).",
    )

    # --- Database Server Configuration (MySQL) ---
    # [Project-Defined Attribute: str]: Hostname or IP of the MySQL server
    mysql_host: str = Field(
        default="127.0.0.1",
        description="Hostname or IP address of the MySQL server.",
    )
    # [Project-Defined Attribute: int]: MySQL port number
    mysql_port: int = Field(
        default=3306,
        description="TCP port of the MySQL server.",
    )
    # [Project-Defined Attribute: str]: Database user with restricted read-only permissions
    mysql_user: str = Field(
        default="readonly_agent",
        description="Dedicated read-only MySQL user name.",
    )
    # [Project-Defined Attribute: str]: Database password
    mysql_password: str = Field(
        default="",
        description="Password for the read-only MySQL user.",
    )

    # --- Dual Database Target Configurations ---
    # [Project-Defined Attribute: str]: MySQL database name for MCA data
    mca_mysql_database: str = Field(
        default="mca_db",
        description="Target MySQL database name containing MCA companies and directors tables.",
    )
    # [Project-Defined Attribute: str]: MySQL database name for GST data
    gst_mysql_database: str = Field(
        default="gst_db",
        description="Target MySQL database name containing GST taxpayers table.",
    )
    # [Project-Defined Attribute: str]: Legacy database name alias
    mysql_database: str = Field(
        default="mca_db",
        description="Default fallback MySQL database name.",
    )

    # --- SQL Execution Safety Bounds ---
    # [Project-Defined Attribute: int]: Maximum auto-correction attempts (bounded between 0 and 5)
    sql_correction_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum correction attempts for eligible SQL execution errors.",
    )
    # [Project-Defined Attribute: int]: Maximum allowed row count in query results (clamped 1 to 500)
    sql_max_rows: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of rows returned by query execution.",
    )
    # [Project-Defined Attribute: int]: SQL execution timeout in seconds
    sql_query_timeout_seconds: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Query execution timeout in seconds.",
    )

    # --- Fallback Configuration for Local Offline Execution ---
    # [Project-Defined Attribute: bool]: Boolean flag switching database backend to local SQLite
    use_sqlite_fallback: bool = Field(
        default=True,
        description="When True or when MySQL is unreachable, use local SQLite databases.",
    )
    # [Project-Defined Attribute: str]: Path to local SQLite MCA database
    mca_sqlite_db_path: str = Field(
        default="data/mca.db",
        description="Path to local SQLite MCA database.",
    )
    # [Project-Defined Attribute: str]: Path to local SQLite GST database
    gst_sqlite_db_path: str = Field(
        default="data/gst.db",
        description="Path to local SQLite GST database.",
    )
    # [Project-Defined Attribute: str]: Legacy alias path
    sqlite_db_path: str = Field(
        default="data/mca.db",
        description="Default SQLite path alias.",
    )

    # [Library Decorator: pydantic.field_validator]: Intercepts and sanitizes gemini_model_id
    @field_validator("gemini_model_id")
    @classmethod
    # [Project-Defined Class Method]: Validates model string isn't blank
    def validate_gemini_model(cls, v: str) -> str:
        # [Built-in Python Method: str.strip]: Strip whitespace
        v_clean = v.strip()
        if not v_clean:
            return "gemini-3.5-flash-lite"
        return v_clean

    # [Project-Defined Method]: Generates standard RFC-compliant SQLAlchemy database URL for a given target database
    def get_sqlalchemy_url(self, db_type: str = "mca") -> str:
        """Construct the SQLAlchemy connection URL for either 'mca' or 'gst' database.

        Args:
            db_type: 'mca' for MCA Corporate database, 'gst' for GST Taxpayer database.

        Returns:
            Formatted SQLAlchemy connection URL string.
        """
        # [Built-in Python Method: str.lower]: Normalize database type identifier
        norm_type = db_type.lower().strip()

        # [Built-in Python: if]: Check if local SQLite fallback mode is active
        if self.use_sqlite_fallback:
            # [Built-in Python Class: pathlib.Path]: Resolve workspace root directory dynamically
            project_root = Path(__file__).resolve().parent.parent.parent
            # Select target database path
            raw_path = self.gst_sqlite_db_path if norm_type == "gst" else self.mca_sqlite_db_path
            db_path = Path(raw_path)
            if not db_path.is_absolute():
                db_path = project_root / db_path
            # [Built-in Python Method: str.replace]: Convert Windows backslashes to forward slashes for URI
            normalized = str(db_path.resolve()).replace("\\", "/")
            return f"sqlite:///{normalized}"

        # [Built-in Python Module: urllib.parse]: Percent-encode special characters in credentials
        import urllib.parse
        # [Built-in Python Function: urllib.parse.quote_plus]: Escapes special characters
        encoded_user = urllib.parse.quote_plus(self.mysql_user)
        encoded_pass = urllib.parse.quote_plus(self.mysql_password)
        target_db = self.gst_mysql_database if norm_type == "gst" else self.mca_mysql_database
        encoded_db = urllib.parse.quote_plus(target_db)
        # Return MySQL PyMySQL dialect connection string
        return (
            f"mysql+pymysql://{encoded_user}:{encoded_pass}"
            f"@{self.mysql_host}:{self.mysql_port}/{encoded_db}?charset=utf8mb4"
        )

    # [Project-Defined Method]: Shortcut returning MCA SQLAlchemy connection URL
    def get_mca_sqlalchemy_url(self) -> str:
        """Get SQLAlchemy URL for MCA database."""
        return self.get_sqlalchemy_url(db_type="mca")

    # [Project-Defined Method]: Shortcut returning GST SQLAlchemy connection URL
    def get_gst_sqlalchemy_url(self) -> str:
        """Get SQLAlchemy URL for GST database."""
        return self.get_sqlalchemy_url(db_type="gst")

    # [Project-Defined Method]: Exports settings to dictionary with masked secrets for safe UI display
    def to_safe_dict(self) -> dict[str, Any]:
        """Return configuration as a dictionary with sensitive credentials masked."""
        # [Built-in Python: dict]: Return safe sanitized representation
        return {
            "gemini_model_id": self.gemini_model_id,
            # [Built-in Python: bool]: Mask key to boolean indicator
            "has_gemini_api_key": bool(self.gemini_api_key.strip()),
            "mysql_host": self.mysql_host,
            "mysql_port": self.mysql_port,
            "mca_mysql_database": self.mca_mysql_database,
            "gst_mysql_database": self.gst_mysql_database,
            "mysql_user": self.mysql_user,
            # [Built-in Python: bool]: Mask password to boolean indicator
            "has_mysql_password": bool(self.mysql_password),
            "sql_correction_max_retries": self.sql_correction_max_retries,
            "sql_max_rows": self.sql_max_rows,
            "sql_query_timeout_seconds": self.sql_query_timeout_seconds,
            "use_sqlite_fallback": self.use_sqlite_fallback,
            "mca_sqlite_db_path": self.mca_sqlite_db_path,
            "gst_sqlite_db_path": self.gst_sqlite_db_path,
        }

    # [Project-Defined Method]: Validates whether environment has all required credentials
    def validate_runtime_readiness(self) -> list[str]:
        """Check whether all necessary credentials and configs are ready for runtime execution.

        Returns a list of missing configuration warnings or errors.
        """
        # [Variable: list[str]]: Collects human-readable validation issue strings
        issues: list[str] = []
        # Check API key presence
        if not self.gemini_api_key.strip():
            # [Built-in Python Function: os.getenv]: Fallback check against OS environment
            env_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not env_key:
                issues.append("Missing GEMINI_API_KEY: Set GEMINI_API_KEY in .env or environment.")
        # Check database configuration presence if not using SQLite fallback
        if not self.use_sqlite_fallback:
            if not self.mca_mysql_database:
                issues.append("Missing MCA_MYSQL_DATABASE: Set MCA_MYSQL_DATABASE in .env.")
            if not self.gst_mysql_database:
                issues.append("Missing GST_MYSQL_DATABASE: Set GST_MYSQL_DATABASE in .env.")
        return issues


# [Project-Defined Global Variable: Optional[AppSettings]]: Singleton instance cached in memory
_settings_instance: Optional[AppSettings] = None
# [Project-Defined Global Variable: float]: Timestamp tracking last modification of .env file
_env_last_mtime: float = 0.0


# [Project-Defined Function]: Factory function returning cached singleton AppSettings
# Automatically reloads configuration if the `.env` file on disk has changed
def get_settings(reload: bool = False) -> AppSettings:
    """Retrieve or initialize the cached AppSettings instance.

    Automatically reloads whenever the `.env` file on disk is modified.
    """
    # [Built-in Python: global]: Declare global scope variables for singleton management
    global _settings_instance, _env_last_mtime

    # [Built-in Python Class: pathlib.Path]: Check disk modification time of .env
    env_path = Path(".env")
    # [Built-in Python: stat().st_mtime]: Read modification timestamp
    current_mtime = env_path.stat().st_mtime if env_path.exists() else 0.0

    # Determine whether cache is uninitialized, forced reload requested, or file was modified
    if _settings_instance is None or reload or current_mtime != _env_last_mtime:
        # [Project-Defined Class Instance]: Instantiate AppSettings
        _settings_instance = AppSettings()
        _env_last_mtime = current_mtime
        # Fallback to os.getenv if Pydantic didn't pick up key from environment
        if not _settings_instance.gemini_api_key:
            _settings_instance.gemini_api_key = (
                os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
            )
    return _settings_instance
