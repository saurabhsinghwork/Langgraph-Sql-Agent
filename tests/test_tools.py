"""Tests for tool service, schema inspection tool, and execution tools for MCA and GST."""

# [Built-in Python Module: json]: JSON serialization helpers
import json
# [Library Import: pytest]: Testing framework
import pytest
# [Library Function: sqlalchemy.create_engine]: SQLAlchemy engine constructor
from sqlalchemy import create_engine
# [Project-Defined Imports from src.database.seeder]: Database seeding functions
from src.database.seeder import seed_mca_database, seed_gst_database
# [Project-Defined Import from src.tools.sql_tools]: Tool execution service
from src.tools.sql_tools import DatabaseToolService
# [Project-Defined Import from src.config.settings]: Application settings class
from src.config.settings import AppSettings


# [Library Decorator: pytest.fixture]: Test fixture providing a pre-seeded MCA DatabaseToolService
@pytest.fixture(scope="module")
def mca_tool_service():
    """Create in-memory SQLite database and tool service for MCA."""
    engine = create_engine("sqlite:///:memory:")
    # [Project-Defined Function: seed_mca_database]: Seed companies and directors tables in-memory
    seed_mca_database(engine=engine)
    # [Project-Defined Class Instance: AppSettings]: Configuration settings
    settings = AppSettings(use_sqlite_fallback=True, sql_max_rows=25)
    # [Project-Defined Class Instance: DatabaseToolService]: MCA tool service
    return DatabaseToolService(engine=engine, settings=settings, db_type="mca")


# [Library Decorator: pytest.fixture]: Test fixture providing a pre-seeded GST DatabaseToolService
@pytest.fixture(scope="module")
def gst_tool_service():
    """Create in-memory SQLite database and tool service for GST."""
    engine = create_engine("sqlite:///:memory:")
    # [Project-Defined Function: seed_gst_database]: Seed taxpayers table in-memory
    seed_gst_database(engine=engine)
    # [Project-Defined Class Instance: AppSettings]: Configuration settings
    settings = AppSettings(use_sqlite_fallback=True, sql_max_rows=25)
    # [Project-Defined Class Instance: DatabaseToolService]: GST tool service
    return DatabaseToolService(engine=engine, settings=settings, db_type="gst")


# [Project-Defined Test Function]: Verifies MCA schema inspection output
def test_describe_mca_schema(mca_tool_service):
    """Verify MCA schema introspection reports companies and directors tables."""
    # [Project-Defined Method: DatabaseToolService.describe_schema]
    schema_text = mca_tool_service.describe_schema()
    assert "Table: `companies`" in schema_text
    assert "Table: `directors`" in schema_text


# [Project-Defined Test Function]: Verifies GST schema inspection output
def test_describe_gst_schema(gst_tool_service):
    """Verify GST schema introspection reports taxpayers table."""
    # [Project-Defined Method: DatabaseToolService.describe_schema]
    schema_text = gst_tool_service.describe_schema()
    assert "Table: `taxpayers`" in schema_text


# [Project-Defined Test Function]: Verifies successful execution of valid MCA SQL query
def test_execute_valid_mca_query(mca_tool_service):
    """Verify execution of valid SELECT on MCA database."""
    # [Project-Defined Method: DatabaseToolService.execute_query]
    res = mca_tool_service.execute_query("SELECT cin_llpin, company_name, state FROM companies LIMIT 5")
    assert res["success"] is True
    assert res["status"] == "success"
    assert res["row_count"] >= 1
    assert "company_name" in res["columns"]


# [Project-Defined Test Function]: Verifies successful execution of valid GST SQL query
def test_execute_valid_gst_query(gst_tool_service):
    """Verify execution of valid SELECT on GST database."""
    # [Project-Defined Method: DatabaseToolService.execute_query]
    res = gst_tool_service.execute_query("SELECT gstin, legal_name, pan FROM taxpayers LIMIT 5")
    assert res["success"] is True
    assert res["status"] == "success"
    assert res["row_count"] >= 1
    assert "gstin" in res["columns"]


# [Project-Defined Test Function]: Verifies non-SELECT queries are rejected by validation
def test_execute_rejected_query(mca_tool_service):
    """Attempt prohibited DDL statement against MCA tool service."""
    res = mca_tool_service.execute_query("DROP TABLE companies")
    assert res["success"] is False
    assert res["status"] == "validation_rejected"
    assert "Disallowed statement" in res["error"]
    assert res["row_count"] == 0


# [Project-Defined Test Function]: Verifies nonexistent columns fail gracefully without crash
def test_execute_unknown_column_fails_gracefully(mca_tool_service):
    """Verify database syntax or column errors are handled gracefully."""
    res = mca_tool_service.execute_query("SELECT non_existent_column FROM companies")
    assert res["success"] is False
    assert res["status"] == "execution_failed"
    assert "Database execution error" in res["error"]
