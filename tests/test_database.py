"""Integration tests for MCA and GST database seeding and live schema inspection."""

# [Library Import: pytest]: Testing framework providing fixtures, assertions, and test parameterization
import pytest
# [Library Function: sqlalchemy.create_engine]: Factory creating SQLAlchemy Engine instance for database access
from sqlalchemy import create_engine
# [Project-Defined Imports from src.database.seeder]: Seeder functions for MCA, GST, and unified seeding
from src.database.seeder import seed_database, seed_mca_database, seed_gst_database
# [Project-Defined Imports from src.database.schema_inspector]: Schema inspector and approved tables constants
from src.database.schema_inspector import (
    # [Project-Defined Class]: Live database metadata introspection service
    SchemaInspector,
    # [Project-Defined Constant: Tuple[str, ...]]: Approved tables for corporate MCA database
    APPROVED_MCA_TABLES,
    # [Project-Defined Constant: Tuple[str, ...]]: Approved tables for GST taxpayer database
    APPROVED_GST_TABLES,
)


# [Library Decorator: pytest.fixture]: Reusable test fixture providing an in-memory SQLite database for MCA
@pytest.fixture(scope="module")
def mca_engine():
    """Create and seed an in-memory SQLite database with MCA tables ('companies' and 'directors')."""
    # [Library Function: sqlalchemy.create_engine]: In-memory SQLite instance for MCA testing
    engine = create_engine("sqlite:///:memory:")
    # [Project-Defined Function: seed_mca_database]: Seed companies and directors tables
    seed_mca_database(engine=engine)
    return engine


# [Library Decorator: pytest.fixture]: Reusable test fixture providing an in-memory SQLite database for GST
@pytest.fixture(scope="module")
def gst_engine():
    """Create and seed an in-memory SQLite database with GST table ('taxpayers')."""
    # [Library Function: sqlalchemy.create_engine]: In-memory SQLite instance for GST testing
    engine = create_engine("sqlite:///:memory:")
    # [Project-Defined Function: seed_gst_database]: Seed taxpayers table
    seed_gst_database(engine=engine)
    return engine


# [Project-Defined Test Function]: Verifies MCA seeding creates both 'companies' and 'directors'
def test_mca_seeding_creates_all_tables(mca_engine):
    """Verify that MCA database seeding creates 'companies' and 'directors' tables."""
    # [Project-Defined Class Instance: SchemaInspector]: Introspect live MCA tables
    inspector = SchemaInspector(engine=mca_engine, db_type="mca")
    # [Project-Defined Method: SchemaInspector.get_live_tables]: Retrieve table names
    tables = inspector.get_live_tables()
    for approved in APPROVED_MCA_TABLES:
        # [Built-in Python: assert]: Check each approved MCA table is present in live database
        assert approved in tables


# [Project-Defined Test Function]: Verifies GST seeding creates 'taxpayers' table
def test_gst_seeding_creates_all_tables(gst_engine):
    """Verify that GST database seeding creates 'taxpayers' table."""
    # [Project-Defined Class Instance: SchemaInspector]: Introspect live GST tables
    inspector = SchemaInspector(engine=gst_engine, db_type="gst")
    # [Project-Defined Method: SchemaInspector.get_live_tables]: Retrieve table names
    tables = inspector.get_live_tables()
    for approved in APPROVED_GST_TABLES:
        # [Built-in Python: assert]: Check each approved GST table is present in live database
        assert approved in tables


# [Project-Defined Test Function]: Verifies MCA table columns contain expected keys
def test_mca_table_details_contain_expected_columns(mca_engine):
    """Verify column metadata extraction for MCA companies and directors."""
    inspector = SchemaInspector(engine=mca_engine, db_type="mca")
    # [Project-Defined Method: SchemaInspector.get_table_details]: Details for 'companies'
    comp_details = inspector.get_table_details("companies")
    comp_cols = [c["name"] for c in comp_details["columns"]]
    # [Built-in Python: assert]: Confirm primary keys and core columns
    assert "cin_llpin" in comp_cols
    assert "company_name" in comp_cols
    assert "city_district" in comp_cols
    assert "state" in comp_cols

    # [Project-Defined Method: SchemaInspector.get_table_details]: Details for 'directors'
    dir_details = inspector.get_table_details("directors")
    dir_cols = [c["name"] for c in dir_details["columns"]]
    assert "din" in dir_cols
    assert "director_name" in dir_cols
    assert "cin_llpin" in dir_cols


# [Project-Defined Test Function]: Verifies GST table columns contain expected keys
def test_gst_table_details_contain_expected_columns(gst_engine):
    """Verify column metadata extraction for GST taxpayers."""
    inspector = SchemaInspector(engine=gst_engine, db_type="gst")
    # [Project-Defined Method: SchemaInspector.get_table_details]: Details for 'taxpayers'
    tax_details = inspector.get_table_details("taxpayers")
    tax_cols = [c["name"] for c in tax_details["columns"]]
    # [Built-in Python: assert]: Confirm primary keys and core columns
    assert "gstin" in tax_cols
    assert "legal_name" in tax_cols
    assert "pan" in tax_cols
    assert "turnover_slab" in tax_cols


# [Project-Defined Test Function]: Verifies querying unapproved tables raises a ValueError
def test_unapproved_table_rejected_by_inspector(mca_engine):
    """Ensure SchemaInspector rejects any table not on the database allowlist."""
    inspector = SchemaInspector(engine=mca_engine, db_type="mca")
    # [Library Context Manager: pytest.raises]: Assert ValueError is raised when querying unapproved table
    with pytest.raises(ValueError, match="not in the approved tables list"):
        inspector.get_table_details("taxpayers")


# [Project-Defined Test Function]: Verifies markdown prompt formatting includes approved tables
def test_format_schema_for_prompt(mca_engine, gst_engine):
    """Verify markdown schema generation includes table declarations for both agents."""
    mca_inspector = SchemaInspector(engine=mca_engine, db_type="mca")
    mca_prompt_str = mca_inspector.format_schema_for_prompt()
    # [Built-in Python: assert]: Verify MCA tables in schema prompt
    assert "Table: `companies`" in mca_prompt_str
    assert "Table: `directors`" in mca_prompt_str

    gst_inspector = SchemaInspector(engine=gst_engine, db_type="gst")
    gst_prompt_str = gst_inspector.format_schema_for_prompt()
    # [Built-in Python: assert]: Verify GST tables in schema prompt
    assert "Table: `taxpayers`" in gst_prompt_str
