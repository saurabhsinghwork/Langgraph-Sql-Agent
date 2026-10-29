"""Database setup and seeding utility for MCA and GST datasets.

Loads and adapts data from MCA-Data-Sample.xlsx and GST-Data-Sample.xlsx,
constructing relational schemas with primary and foreign keys:
- MCA Database: 'companies' (134 records) and 'directors' (300 records)
- GST Database: 'taxpayers' (200 records)
"""

from __future__ import annotations

# [Built-in Python Module: os]: Operating system directory operations
import os
# [Built-in Python Module: sys]: System path management
import sys
# [Built-in Python Class: pathlib.Path]: Filesystem path object
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# [Built-in Python Module: logging]: Event logging framework
import logging
# [Built-in Python Module: typing]: Type annotation primitives
from typing import Optional, Tuple, Dict, Any
# [Library Import: pandas as pd]: Data ingestion from Excel and tabular transformation
import pandas as pd
# [Library Function: sqlalchemy.text]: Wrap raw SQL string into executable ClauseElement
from sqlalchemy import text
# [Library Class: sqlalchemy.engine.Engine]: Type definition for SQLAlchemy connection engine
from sqlalchemy.engine import Engine

# [Project-Defined Imports from src.database.connection]: Connection engine getters
from src.database.connection import get_engine, get_mca_engine, get_gst_engine
# [Project-Defined Imports from src.config.settings]: AppSettings class and singleton helper
from src.config.settings import AppSettings, get_settings

# [Library Instance: logging.Logger]: Logger for tracking database seeding operations
logger = logging.getLogger(__name__)


# [Project-Defined Function]: Resolves filesystem location of dataset files (checking data/ then Downloads)
def resolve_data_file(filename: str) -> Path:
    """Resolve data file path looking in project 'data/' folder first, then User Downloads."""
    # [Built-in Python Class: pathlib.Path]: Project root directory
    project_root = Path(__file__).resolve().parent.parent.parent
    local_path = project_root / "data" / filename
    if local_path.exists():
        return local_path
    downloads_path = Path("C:/Users/Admin/Downloads") / filename
    if downloads_path.exists():
        return downloads_path
    return local_path


# [Project-Defined Function]: Ingests MCA Excel data and populates 'companies' and 'directors' tables
def seed_mca_database(
    engine: Optional[Engine] = None,
    settings: Optional[AppSettings] = None,
) -> Tuple[bool, str]:
    """Seed MCA database with companies (134) and directors (300).

    Args:
        engine: Optional SQLAlchemy engine targeting MCA database.
        settings: Optional custom AppSettings.

    Returns:
        Tuple of (success: bool, status_message: str).
    """
    # [Project-Defined Function: get_settings]: Retrieve settings singleton
    if settings is None:
        settings = get_settings()
    # [Project-Defined Function: get_mca_engine]: Retrieve SQLAlchemy Engine for MCA
    if engine is None:
        engine = get_mca_engine(settings=settings)

    # [Project-Defined Function: resolve_data_file]: Locate MCA Excel dataset
    mca_file = resolve_data_file("MCA-Data-Sample.xlsx")
    if not mca_file.exists():
        return False, f"MCA data file not found at '{mca_file}'."

    try:
        # [Library Function: pandas.read_excel]: Ingest MCA Excel spreadsheet
        mca_df = pd.read_excel(mca_file)

        # Extract unique companies
        company_cols = [
            'Company Name', 'CIN / LLPIN', 'Entity Type', 'Registration Date', 'State',
            'City / District', 'Pincode', 'ROC', 'Activity Code', 'Activity Description',
            'Class', 'Category', 'Subcategory', 'Authorized Capital', 'Paid-up Capital',
            'Registered Address'
        ]
        # [Library Method: DataFrame.drop_duplicates]: Deduplicate companies by CIN / LLPIN
        companies = mca_df[company_cols].drop_duplicates(subset=['CIN / LLPIN']).copy()
        companies.columns = [
            'company_name', 'cin_llpin', 'entity_type', 'registration_date', 'state',
            'city_district', 'pincode', 'roc', 'activity_code', 'activity_description',
            'class', 'category', 'subcategory', 'authorized_capital', 'paid_up_capital',
            'registered_address'
        ]

        # Extract directors with foreign key link to company CIN / LLPIN
        director_cols = [
            'DIN', 'CIN / LLPIN', 'Director Name', 'Designation', 'Director DOB',
            'Gender', 'Director Email', 'Director Mobile'
        ]
        # [Library Method: DataFrame.drop_duplicates]: Deduplicate directors by DIN
        directors = mca_df[director_cols].drop_duplicates(subset=['DIN']).copy()
        directors.columns = [
            'din', 'cin_llpin', 'director_name', 'designation', 'director_dob',
            'gender', 'director_email', 'director_mobile'
        ]

        # Convert date columns to ISO strings
        companies['registration_date'] = companies['registration_date'].astype(str).str.split().str[0]

        # [Library Context Manager: Engine.begin]: Open transactional connection
        with engine.begin() as conn:
            # For SQLite, enforce foreign keys
            if str(engine.url).startswith("sqlite"):
                conn.execute(text("PRAGMA foreign_keys = ON;"))

            # [Library Method: DataFrame.to_sql]: Export pandas DataFrames into SQL tables
            companies.to_sql('companies', conn, if_exists='replace', index=False)
            directors.to_sql('directors', conn, if_exists='replace', index=False)

            # [Built-in Python: if]: Initialize FTS5 full-text search virtual tables for SQLite
            if str(engine.url).startswith("sqlite"):
                init_mca_fts_tables(conn)

        # Verification count
        with engine.connect() as conn:
            c_count = conn.execute(text("SELECT COUNT(*) FROM companies")).scalar() or 0
            d_count = conn.execute(text("SELECT COUNT(*) FROM directors")).scalar() or 0

        msg = (
            f"Successfully seeded MCA database from '{mca_file.name}': "
            f"{c_count} companies, {d_count} directors."
        )
        logger.info(msg)
        return True, msg

    except Exception as exc:
        err_msg = f"Failed to seed MCA database: {type(exc).__name__}: {str(exc)}"
        logger.error(err_msg)
        return False, err_msg


# [Project-Defined Function]: Initializes SQLite FTS5 virtual tables for MCA corporate data
def init_mca_fts_tables(conn: Any) -> None:
    """Create and synchronize SQLite FTS5 search indexes for MCA companies and directors."""
    # [Library Method: Connection.execute]: Recreate companies_fts virtual table for multi-column search
    conn.execute(text("DROP TABLE IF EXISTS companies_fts;"))
    conn.execute(text("""
        CREATE VIRTUAL TABLE companies_fts USING fts5(
            cin_llpin UNINDEXED,
            company_name,
            entity_type,
            state,
            city_district,
            activity_description,
            registered_address,
            category,
            subcategory,
            class
        );
    """))
    # [Library Method: Connection.execute]: Synchronize content from base companies table
    conn.execute(text("""
        INSERT INTO companies_fts(
            cin_llpin, company_name, entity_type, state, city_district,
            activity_description, registered_address, category, subcategory, class
        )
        SELECT 
            cin_llpin, company_name, entity_type, state, city_district,
            activity_description, registered_address, category, subcategory, class
        FROM companies;
    """))
    # [Library Method: Connection.execute]: Recreate directors_fts virtual table
    conn.execute(text("DROP TABLE IF EXISTS directors_fts;"))
    conn.execute(text("""
        CREATE VIRTUAL TABLE directors_fts USING fts5(
            din UNINDEXED,
            cin_llpin UNINDEXED,
            director_name,
            designation,
            director_email
        );
    """))
    conn.execute(text("""
        INSERT INTO directors_fts(din, cin_llpin, director_name, designation, director_email)
        SELECT din, cin_llpin, director_name, designation, director_email
        FROM directors;
    """))


# [Project-Defined Function]: Ingests GST Excel data and populates 'taxpayers' table
def seed_gst_database(
    engine: Optional[Engine] = None,
    settings: Optional[AppSettings] = None,
) -> Tuple[bool, str]:
    """Seed GST database with taxpayers (200).

    Args:
        engine: Optional SQLAlchemy engine targeting GST database.
        settings: Optional custom AppSettings.

    Returns:
        Tuple of (success: bool, status_message: str).
    """
    if settings is None:
        settings = get_settings()
    if engine is None:
        engine = get_gst_engine(settings=settings)

    gst_file = resolve_data_file("GST-Data-Sample.xlsx")
    if not gst_file.exists():
        return False, f"GST data file not found at '{gst_file}'."

    try:
        # [Library Function: pandas.read_excel]: Ingest GST spreadsheet
        gst_df = pd.read_excel(gst_file)
        gst_df.columns = [
            'gstin', 'legal_name', 'trade_name', 'constitution', 'taxpayer_type',
            'nature_of_business', 'turnover_slab', 'turnover_fy', 'registration_date',
            'status', 'pan', 'mobile', 'email', 'address', 'city', 'state'
        ]
        # Normalize date format
        gst_df['registration_date'] = gst_df['registration_date'].astype(str).str.split().str[0]

        # [Library Context Manager: Engine.begin]: Open transactional connection
        with engine.begin() as conn:
            gst_df.to_sql('taxpayers', conn, if_exists='replace', index=False)

            # [Built-in Python: if]: Initialize FTS5 full-text search virtual tables for SQLite
            if str(engine.url).startswith("sqlite"):
                init_gst_fts_tables(conn)

        # Verification count
        with engine.connect() as conn:
            t_count = conn.execute(text("SELECT COUNT(*) FROM taxpayers")).scalar() or 0

        msg = (
            f"Successfully seeded GST database from '{gst_file.name}': "
            f"{t_count} taxpayers."
        )
        logger.info(msg)
        return True, msg

    except Exception as exc:
        err_msg = f"Failed to seed GST database: {type(exc).__name__}: {str(exc)}"
        logger.error(err_msg)
        return False, err_msg


# [Project-Defined Function]: Initializes SQLite FTS5 virtual table for GST taxpayer data
def init_gst_fts_tables(conn: Any) -> None:
    """Create and synchronize SQLite FTS5 search index for GST taxpayers."""
    # [Library Method: Connection.execute]: Recreate taxpayers_fts virtual table for multi-column search
    conn.execute(text("DROP TABLE IF EXISTS taxpayers_fts;"))
    conn.execute(text("""
        CREATE VIRTUAL TABLE taxpayers_fts USING fts5(
            gstin UNINDEXED,
            legal_name,
            trade_name,
            constitution,
            taxpayer_type,
            nature_of_business,
            address,
            city,
            state
        );
    """))
    # [Library Method: Connection.execute]: Synchronize content from base taxpayers table
    conn.execute(text("""
        INSERT INTO taxpayers_fts(
            gstin, legal_name, trade_name, constitution,
            taxpayer_type, nature_of_business, address, city, state
        )
        SELECT 
            gstin, legal_name, trade_name, constitution,
            taxpayer_type, nature_of_business, address, city, state
        FROM taxpayers;
    """))


# [Project-Defined Function]: Ensures FTS5 virtual tables exist and are synchronized on demand
def ensure_fts_tables(engine: Engine, db_type: str = "mca") -> None:
    """Ensure SQLite FTS5 virtual tables exist and are populated without full re-seed."""
    # [Built-in Python: if]: Only applicable for SQLite database engine
    if not str(engine.url).startswith("sqlite"):
        return
    norm_type = db_type.lower().strip()
    with engine.begin() as conn:
        if norm_type == "gst":
            init_gst_fts_tables(conn)
        else:
            init_mca_fts_tables(conn)


# [Project-Defined Function]: Master seeder seeding both MCA and GST databases
def seed_database(
    target: str = "all",
    settings: Optional[AppSettings] = None,
) -> Tuple[bool, str]:
    """Seed one or both databases.

    Args:
        target: 'mca', 'gst', or 'all'.
        settings: Application settings.

    Returns:
        Tuple of (success: bool, status_message: str).
    """
    if settings is None:
        settings = get_settings()

    norm_target = target.lower().strip()
    if norm_target == "mca":
        return seed_mca_database(settings=settings)
    elif norm_target == "gst":
        return seed_gst_database(settings=settings)
    else:
        # Seed both
        ok_mca, msg_mca = seed_mca_database(settings=settings)
        ok_gst, msg_gst = seed_gst_database(settings=settings)
        overall_ok = ok_mca and ok_gst
        combined_msg = f"{msg_mca} | {msg_gst}"
        return overall_ok, combined_msg


# [Built-in Python: __name__ check]: Allow executing seeder directly from CLI
if __name__ == "__main__":
    # [Built-in Python Function: logging.basicConfig]: Initialize console logger
    logging.basicConfig(level=logging.INFO)
    print("Seeding MCA and GST databases...")
    success, message = seed_database(target="all")
    print(f"Result: {message}")
