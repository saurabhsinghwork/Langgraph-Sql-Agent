"""Unit tests for SQL AST validator and security policy engine for MCA and GST."""

# [Library Import: pytest]: Testing framework
import pytest
# [Project-Defined Imports from src.validation.validator]: SQL AST validator and result dataclass
from src.validation.validator import SQLValidator, ValidationResult
# [Project-Defined Imports from src.database.schema_inspector]: Approved tables constants
from src.database.schema_inspector import APPROVED_MCA_TABLES, APPROVED_GST_TABLES


# [Library Decorator: pytest.fixture]: Test fixture providing a configured SQLValidator instance for MCA
@pytest.fixture
def mca_validator():
    """Create a SQLValidator configured for MCA database tables."""
    # [Project-Defined Class Instance: SQLValidator]: Initialized with max_rows=50, dialect='mysql', db_type='mca'
    return SQLValidator(max_rows=50, dialect="mysql", db_type="mca")


# [Library Decorator: pytest.fixture]: Test fixture providing a configured SQLValidator instance for GST
@pytest.fixture
def gst_validator():
    """Create a SQLValidator configured for GST database table."""
    # [Project-Defined Class Instance: SQLValidator]: Initialized with max_rows=50, dialect='mysql', db_type='gst'
    return SQLValidator(max_rows=50, dialect="mysql", db_type="gst")


# [Project-Defined Test Function]: Verifies valid simple SELECT queries on MCA pass validation
def test_valid_simple_select_mca(mca_validator):
    """Verify simple SELECT on MCA companies table passes AST validation."""
    sql = "SELECT cin_llpin, company_name, state FROM companies WHERE state = 'Telangana'"
    # [Project-Defined Method: SQLValidator.validate]
    res = mca_validator.validate(sql)
    assert res.is_valid is True
    assert res.error_message is None
    assert "LIMIT 50" in res.sanitized_sql.upper()
    assert "companies" in res.referenced_tables


# [Project-Defined Test Function]: Verifies valid multi-table join across approved MCA tables
def test_valid_multi_table_join_mca(mca_validator):
    """Verify JOIN between companies and directors is permitted on MCA validator."""
    sql = """
        SELECT c.company_name, d.director_name, d.din
        FROM companies c
        JOIN directors d ON c.cin_llpin = d.cin_llpin
        WHERE c.state = 'Andhra Pradesh'
    """
    res = mca_validator.validate(sql)
    assert res.is_valid is True
    assert set(res.referenced_tables) == {"companies", "directors"}


# [Project-Defined Test Function]: Verifies valid SELECT query on GST taxpayers
def test_valid_simple_select_gst(gst_validator):
    """Verify simple SELECT on GST taxpayers table passes AST validation."""
    sql = "SELECT gstin, legal_name, turnover_slab FROM taxpayers WHERE turnover_slab = '1.5 to 5 Cr'"
    res = gst_validator.validate(sql)
    assert res.is_valid is True
    assert res.error_message is None
    assert "LIMIT 50" in res.sanitized_sql.upper()
    assert "taxpayers" in res.referenced_tables


# [Project-Defined Test Function]: Verifies stacked multiple statements are blocked
def test_reject_multiple_statements(mca_validator):
    """Ensure multi-statement injection attempts are blocked."""
    sql = "SELECT * FROM companies; DROP TABLE directors;"
    res = mca_validator.validate(sql)
    assert res.is_valid is False
    assert "multiple statements" in res.error_message.lower()


# [Project-Defined Test Function]: Verifies INSERT DML is blocked
def test_reject_insert_dml(mca_validator):
    """Ensure INSERT mutation attempts are rejected."""
    sql = "INSERT INTO companies (cin_llpin, company_name) VALUES ('U12345', 'Malicious Corp')"
    res = mca_validator.validate(sql)
    assert res.is_valid is False
    assert "disallowed statement type" in res.error_message.lower()


# [Project-Defined Test Function]: Verifies DELETE DML is blocked
def test_reject_delete_dml(mca_validator):
    """Ensure DELETE mutation attempts are rejected."""
    sql = "DELETE FROM directors WHERE din = '01234567'"
    res = mca_validator.validate(sql)
    assert res.is_valid is False
    assert "disallowed statement type" in res.error_message.lower()


# [Project-Defined Test Function]: Verifies DROP DDL is blocked
def test_reject_drop_ddl(mca_validator):
    """Ensure DROP DDL attempts are rejected."""
    sql = "DROP TABLE companies"
    res = mca_validator.validate(sql)
    assert res.is_valid is False
    assert "disallowed statement type" in res.error_message.lower()


# [Project-Defined Test Function]: Verifies cross-database unapproved tables are blocked
def test_reject_unapproved_table(mca_validator):
    """Ensure querying taxpayers table or system table against MCA validator is rejected."""
    # Querying GST table against MCA validator must fail allowlist check
    sql = "SELECT * FROM taxpayers"
    res = mca_validator.validate(sql)
    assert res.is_valid is False
    assert "not allowed" in res.error_message.lower() or "prohibited" in res.error_message.lower()

    # Querying system table must fail
    res_sys = mca_validator.validate("SELECT * FROM mysql.user")
    assert res_sys.is_valid is False


# [Project-Defined Test Function]: Verifies dangerous functions (SLEEP, BENCHMARK) are blocked
def test_reject_dangerous_sleep_function(mca_validator):
    """Ensure SQL injection side-channel functions like SLEEP are blocked."""
    sql = "SELECT * FROM companies WHERE SLEEP(5) = 0"
    res = mca_validator.validate(sql)
    assert res.is_valid is False
    assert "sleep()" in res.error_message.lower()


# [Project-Defined Test Function]: Verifies file dump INTO OUTFILE clauses are blocked
def test_reject_into_outfile(mca_validator):
    """Ensure file exfiltration clauses like INTO OUTFILE are blocked."""
    sql = "SELECT * FROM companies INTO OUTFILE '/tmp/dump.txt'"
    res = mca_validator.validate(sql)
    assert res.is_valid is False
    assert "into" in res.error_message.lower()


# [Project-Defined Test Function]: Verifies LIMIT clause exceeds are automatically clamped to max_rows
def test_limit_clamping(mca_validator):
    """Ensure queries with excessively large LIMIT are clamped to max_rows."""
    sql = "SELECT * FROM companies LIMIT 500"
    res = mca_validator.validate(sql)
    assert res.is_valid is True
    assert "LIMIT 50" in res.sanitized_sql.upper()
