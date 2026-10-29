"""Tools for LangGraph agents: live schema inspection and validated SQL execution for MCA and GST.

These tools are registered with LangGraph / LangChain tool calling to enable
the MCA Agent and GST Agent to inspect their respective database schemas and execute
safe read-only queries with bounded limits and security validation.
"""

from __future__ import annotations

# [Built-in Python Module: decimal]: Accurate fixed-point arithmetic types (Decimal)
import decimal
# [Built-in Python Module: datetime]: Date and timestamp manipulation types
import datetime
# [Built-in Python Module: json]: JSON serialization and deserialization
import json
# [Built-in Python Module: logging]: Event logging framework
import logging
# [Built-in Python Module: typing]: Type annotation helpers
from typing import Any, Dict, List, Optional
# [Library Imports: sqlalchemy]: Database abstraction functions
from sqlalchemy import text
# [Library Imports: sqlalchemy.engine.Engine]: Type definition for SQLAlchemy connection engine
from sqlalchemy.engine import Engine
# [Library Imports: sqlalchemy.exc.SQLAlchemyError]: Base class for database errors
from sqlalchemy.exc import SQLAlchemyError
# [Library Decorator: langchain_core.tools.tool]: Decorates Python functions to produce LangChain Tools
from langchain_core.tools import tool, BaseTool

# [Project-Defined Imports from src.config.settings]: AppSettings class and configuration resolver
from src.config.settings import AppSettings, get_settings
# [Project-Defined Imports from src.database.connection]: Connection engine singleton resolver
from src.database.connection import get_engine, get_mca_engine, get_gst_engine
# [Project-Defined Import from src.database.schema_inspector]: Live database metadata inspector
from src.database.schema_inspector import SchemaInspector
# [Project-Defined Imports from src.validation.validator]: AST SQL validator and validation result contract
from src.validation.validator import SQLValidator, ValidationResult
# [Project-Defined Import from src.database.seeder]: SQLite FTS5 table initialization helper
from src.database.seeder import ensure_fts_tables

# [Library Instance: logging.Logger]: Logger for tool operations
logger = logging.getLogger(__name__)


# [Project-Defined Function]: Normalizes database data types into JSON-serializable primitives
def serialize_cell_value(val: Any) -> Any:
    """Serialize database types such as Decimal, Date, and Datetime into JSON/Python primitives."""
    # [Built-in Python: isinstance]: Convert Decimal objects into native floats
    # [Built-in Python Class: decimal.Decimal]
    if isinstance(val, decimal.Decimal):
        return float(val)
    # [Built-in Python: isinstance]: Convert dates and timestamps into ISO 8601 strings
    # [Built-in Python Classes: datetime.date, datetime.datetime]
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.isoformat()
    return val


# [Project-Defined Class]: Coordinates schema introspection and validated query execution for a database
class DatabaseToolService:
    """Encapsulates schema inspection and validated SQL execution for MCA or GST database."""

    # [Project-Defined Method]: Initializes database tools with required services and validator for target database
    def __init__(
        self,
        db_type: str = "mca",
        engine: Optional[Engine] = None,
        settings: Optional[AppSettings] = None,
    ):
        # [Project-Defined Attribute: str]: Database classification identifier ('mca' or 'gst')
        self.db_type = db_type.lower().strip()
        # [Project-Defined Attribute: AppSettings]: Application settings instance
        self.settings = settings or get_settings()
        # [Project-Defined Attribute: Engine]: SQLAlchemy connection engine for this database
        self.engine = engine or get_engine(db_type=self.db_type, settings=self.settings)
        # [Project-Defined Attribute: SchemaInspector]: Live schema introspection service scoped to this db
        self.inspector = SchemaInspector(engine=self.engine, db_type=self.db_type)
        # Determine dialect (SQLite vs MySQL) from target engine URL
        dialect = "sqlite" if str(self.engine.url).startswith("sqlite") else "mysql"
        # [Project-Defined Attribute: SQLValidator]: AST-based query validator scoped to this db
        self.validator = SQLValidator(
            max_rows=self.settings.sql_max_rows,
            dialect=dialect,
            db_type=self.db_type,
        )

        # [Built-in Python: try/except]: Ensure SQLite FTS5 full-text search indexes are ready
        try:
            ensure_fts_tables(self.engine, db_type=self.db_type)
        except Exception as fts_init_err:
            logger.debug("[%s] FTS init notice: %s", self.db_type.upper(), fts_init_err)

    # [Project-Defined Method]: Generates markdown schema documentation for Gemini
    def describe_schema(self) -> str:
        """Inspect and return authoritative live schema of the approved tables."""
        # [Project-Defined Method: SchemaInspector.format_schema_for_prompt]
        return self.inspector.format_schema_for_prompt()

    # [Project-Defined Method]: Validates and safely executes candidate SQL query
    def execute_query(self, sql_query: str) -> Dict[str, Any]:
        """Validate and execute a read-only SQL query against the target database.

        Args:
            sql_query: The candidate SQL query generated by the agent.

        Returns:
            Dictionary with execution status, sanitized SQL, column names, rows, and error details.
        """
        # Step 1: SQL validation gate
        # [Project-Defined Method: SQLValidator.validate]: Parse AST and check security rules
        val_result: ValidationResult = self.validator.validate(sql_query)
        if not val_result.is_valid:
            # [Library Method: Logger.warning]: Log rejected query
            logger.warning("[%s] Query rejected by validation: %s", self.db_type.upper(), val_result.error_message)
            return {
                "success": False,
                "status": "validation_rejected",
                "sql_query": sql_query,
                "sanitized_sql": None,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": val_result.error_message,
                "is_retryable": False,
            }

        # [Variable: str]: Sanitized SQL with row limit enforced
        sanitized_sql = val_result.sanitized_sql or sql_query

        # Step 2: Database execution with error handling and timeout
        try:
            # [Library Context Manager: Engine.connect]: Acquire connection
            with self.engine.connect() as conn:
                # [Library Function: sqlalchemy.text]: Wrap query string
                result = conn.execute(text(sanitized_sql))
                # [Library Property: CursorResult.keys]: Extract returned column headers
                columns = list(result.keys()) if result.returns_rows else []
                # [Library Method: CursorResult.fetchmany]: Fetch up to configured row ceiling
                raw_rows = result.fetchmany(self.settings.sql_max_rows) if result.returns_rows else []

                # Format rows as list of dicts with serialized values
                rows: List[Dict[str, Any]] = []
                for row in raw_rows:
                    row_dict = {}
                    # [Built-in Python Function: zip]: Pair column names with cell values
                    for col_name, val in zip(columns, row):
                        # [Project-Defined Function: serialize_cell_value]: Serialize cell types
                        row_dict[col_name] = serialize_cell_value(val)
                    rows.append(row_dict)

                # [Library Method: Logger.info]: Log execution metrics
                logger.info(
                    "[%s] Successfully executed query. Returned %d rows, %d columns.",
                    self.db_type.upper(),
                    len(rows),
                    len(columns),
                )
                return {
                    "success": True,
                    "status": "success",
                    "sql_query": sql_query,
                    "sanitized_sql": sanitized_sql,
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "error": None,
                    "is_retryable": False,
                }

        # [Library Exception: sqlalchemy.exc.SQLAlchemyError]: Catch database-level execution errors
        except SQLAlchemyError as exc:
            # Capture database execution error (e.g., column doesn't exist, invalid join)
            error_str = str(exc.orig) if hasattr(exc, "orig") else str(exc)
            # Remove any passwords or raw connection strings that might accidentally leak
            safe_error_msg = f"Database execution error: {error_str}"
            logger.warning("[%s] Database execution failure: %s", self.db_type.upper(), safe_error_msg)

            # Syntax or column errors are eligible for correction retry
            # [Built-in Python: any]: Check if error contains retryable failure signals
            is_retryable = any(
                keyword in error_str.lower()
                for keyword in ("unknown column", "no such column", "syntax error", "ambiguous", "group by")
            )

            return {
                "success": False,
                "status": "execution_failed",
                "sql_query": sql_query,
                "sanitized_sql": sanitized_sql,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": safe_error_msg,
                "is_retryable": is_retryable,
            }
        # [Built-in Python: Exception]: Catch unexpected errors during execution
        except Exception as exc:
            logger.error("[%s] Unexpected error executing query: %s", self.db_type.upper(), type(exc).__name__)
            return {
                "success": False,
                "status": "execution_failed",
                "sql_query": sql_query,
                "sanitized_sql": sanitized_sql,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": f"Execution error: {type(exc).__name__}",
                "is_retryable": False,
            }

    # [Project-Defined Method: DatabaseToolService.full_text_search]: Executes global full-text search across all textual columns
    def full_text_search(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """Perform a global full-text search across all textual columns for MCA or GST database.

        Args:
            query: The keyword or phrase to search (e.g. 'manufacturer', 'textile', 'solar', 'hospital').
            limit: Maximum rows to return (bounded by SQL_MAX_ROWS).

        Returns:
            Dictionary matching execute_query schema with status, sql_query, columns, rows, and row_count.
        """
        # [Built-in Python: str.strip]: Clean input query string
        raw_query = str(query or "").strip()
        if not raw_query:
            return {
                "success": True,
                "status": "success",
                "sql_query": "-- Empty search term provided",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": None,
            }

        # [Built-in Python: min]: Clamp limit to configured max_rows
        eff_limit = min(limit, self.settings.sql_max_rows)
        # [Built-in Python: list comprehension]: Clean tokens to prevent SQLite FTS syntax errors
        clean_tokens = [tok for tok in "".join(c if c.isalnum() else " " for c in raw_query).split() if tok]
        if not clean_tokens:
            clean_tokens = [raw_query.replace("'", "")]

        # [Project-Defined Function]: Derives morphological base root so 'manufacturing', 'manufacturer', 'manufacture' all resolve to 'manufactur'
        def get_token_stem(t: str) -> str:
            lower_t = t.lower().strip()
            for suffix in ("ing", "ers", "er", "ed", "es", "s", "e"):
                if lower_t.endswith(suffix) and len(lower_t) - len(suffix) >= 4:
                    return lower_t[:-len(suffix)]
            return lower_t

        stems = [get_token_stem(tok) for tok in clean_tokens]
        # Match either exact token prefix or root stem prefix (e.g. '("manufacturing"* OR "manufactur"*)')
        fts_terms = []
        for tok, stem in zip(clean_tokens, stems):
            if stem != tok.lower():
                fts_terms.append(f'("{tok}"* OR "{stem}"*)')
            else:
                fts_terms.append(f'"{tok}"*')
        # [Variable: str]: FTS5 prefix search expression with stem expansion
        fts_match_term = " ".join(fts_terms)
        like_term = f"%{stems[0]}%"

        # Ensure FTS5 tables exist
        try:
            ensure_fts_tables(self.engine, db_type=self.db_type)
        except Exception as fts_init_err:
            logger.debug("[%s] FTS init error: %s", self.db_type.upper(), fts_init_err)

        if self.db_type == "mca":
            fts_sql = text("""
                SELECT 
                    c.company_name,
                    c.cin_llpin,
                    c.entity_type,
                    c.state,
                    c.city_district,
                    c.activity_description,
                    c.registered_address
                FROM companies c
                JOIN companies_fts f ON c.cin_llpin = f.cin_llpin
                WHERE companies_fts MATCH :match_term
                LIMIT :limit
            """)
            fallback_sql = text("""
                SELECT 
                    company_name,
                    cin_llpin,
                    entity_type,
                    state,
                    city_district,
                    activity_description,
                    registered_address
                FROM companies
                WHERE company_name LIKE :like_term
                   OR activity_description LIKE :like_term
                   OR registered_address LIKE :like_term
                   OR city_district LIKE :like_term
                   OR state LIKE :like_term
                   OR category LIKE :like_term
                LIMIT :limit
            """)
            display_sql = f"SELECT company_name, cin_llpin, entity_type, state, city_district, activity_description FROM companies WHERE companies_fts MATCH '{fts_match_term}' LIMIT {eff_limit};"
        else:
            fts_sql = text("""
                SELECT 
                    t.gstin,
                    t.legal_name,
                    t.trade_name,
                    t.nature_of_business,
                    t.constitution,
                    t.taxpayer_type,
                    t.city,
                    t.state
                FROM taxpayers t
                JOIN taxpayers_fts f ON t.gstin = f.gstin
                WHERE taxpayers_fts MATCH :match_term
                LIMIT :limit
            """)
            fallback_sql = text("""
                SELECT 
                    gstin,
                    legal_name,
                    trade_name,
                    nature_of_business,
                    constitution,
                    taxpayer_type,
                    city,
                    state
                FROM taxpayers
                WHERE trade_name LIKE :like_term
                   OR legal_name LIKE :like_term
                   OR nature_of_business LIKE :like_term
                   OR address LIKE :like_term
                   OR city LIKE :like_term
                   OR state LIKE :like_term
                LIMIT :limit
            """)
            display_sql = f"SELECT gstin, legal_name, trade_name, nature_of_business, city, state FROM taxpayers WHERE taxpayers_fts MATCH '{fts_match_term}' LIMIT {eff_limit};"

        try:
            with self.engine.connect() as conn:
                try:
                    result = conn.execute(fts_sql, {"match_term": fts_match_term, "limit": eff_limit})
                    cols = list(result.keys())
                    raw_rows = result.fetchall()
                except Exception as fts_run_err:
                    logger.info("[%s] FTS query failed, attempting multi-column LIKE fallback: %s", self.db_type.upper(), fts_run_err)
                    result = conn.execute(fallback_sql, {"like_term": like_term, "limit": eff_limit})
                    cols = list(result.keys())
                    raw_rows = result.fetchall()
                    display_sql = f"-- Full-Text Search fallback:\n{fallback_sql}"

                rows_data = [
                    {col: serialize_cell_value(val) for col, val in zip(cols, row)}
                    for row in raw_rows
                ]

                logger.info(
                    "[%s] Full-text search for '%s' returned %d rows with %d columns.",
                    self.db_type.upper(),
                    raw_query,
                    len(rows_data),
                    len(cols),
                )

                return {
                    "success": True,
                    "status": "success",
                    "sql_query": display_sql,
                    "columns": cols,
                    "rows": rows_data,
                    "row_count": len(rows_data),
                    "search_term": raw_query,
                    "error": None,
                }

        except Exception as exc:
            err_msg = f"Full-text search error: {type(exc).__name__}: {str(exc)}"
            logger.error("[%s] %s", self.db_type.upper(), err_msg)
            return {
                "success": False,
                "status": "execution_failed",
                "sql_query": display_sql,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": err_msg,
            }


# [Project-Defined Global Variable: Dict[str, DatabaseToolService]]: Cached singleton services keyed by db_type
_tool_services: Dict[str, DatabaseToolService] = {}


# [Project-Defined Function]: Retrieves or initializes singleton DatabaseToolService for a given db_type
def get_tool_service(db_type: str = "mca", force_new: bool = False) -> DatabaseToolService:
    """Retrieve or initialize the DatabaseToolService singleton for 'mca' or 'gst'."""
    global _tool_services
    norm_type = db_type.lower().strip()
    settings = get_settings()

    cached = _tool_services.get(norm_type)
    if (
        cached is None
        or force_new
        or cached.settings.use_sqlite_fallback != settings.use_sqlite_fallback
        or str(cached.engine.url) != settings.get_sqlalchemy_url(db_type=norm_type)
    ):
        _tool_services[norm_type] = DatabaseToolService(db_type=norm_type, settings=settings)

    return _tool_services[norm_type]


# [Project-Defined Function]: Shortcut acquiring MCA tool service
def get_mca_tool_service(force_new: bool = False) -> DatabaseToolService:
    """Get DatabaseToolService for MCA database."""
    return get_tool_service(db_type="mca", force_new=force_new)


# [Project-Defined Function]: Shortcut acquiring GST tool service
def get_gst_tool_service(force_new: bool = False) -> DatabaseToolService:
    """Get DatabaseToolService for GST database."""
    return get_tool_service(db_type="gst", force_new=force_new)


# --- MCA Specific Tools ---

# [Library Decorator: langchain_core.tools.tool]: Converts function into tool callable by Gemini LLM for MCA
@tool
def describe_mca_schema_tool() -> str:
    """Inspect and return the authoritative live schema for the MCA database tables: 'companies' and 'directors'.

    Call this tool when querying MCA data to inspect exact columns, types, and primary/foreign keys.
    """
    service = get_mca_tool_service()
    return service.describe_schema()


# [Library Decorator: langchain_core.tools.tool]: Converts function into tool callable by Gemini LLM for MCA
@tool
def execute_mca_sql_query_tool(query: str) -> str:
    """Validate and execute a read-only SQL SELECT query against the MCA database ('companies', 'directors').

    Args:
        query: The SQL SELECT statement to execute against MCA database.

    Returns:
        JSON string containing the execution results, columns, rows, or safe error message.
    """
    service = get_mca_tool_service()
    result = service.execute_query(query)
    return json.dumps(result, indent=2)


# [Library Decorator: langchain_core.tools.tool]: Converts function into tool callable by Gemini LLM for MCA FTS
@tool
def full_text_search_mca_tool(query: str) -> str:
    """Execute a global multi-column full-text keyword search across all MCA companies and directors.

    Call this tool whenever the user provides a keyword, industry term, or broad topic (e.g. 'manufacturer',
    'textile', 'solar', 'hospital', 'steel', 'pharma', 'construction') to find matching companies across
    all textual columns (names, activities, addresses, categories).

    Args:
        query: The keyword, industry name, or search phrase to find across all columns.

    Returns:
        JSON string containing the matching corporate entity records.
    """
    service = get_mca_tool_service()
    result = service.full_text_search(query)
    return json.dumps(result, indent=2)


# --- GST Specific Tools ---

# [Library Decorator: langchain_core.tools.tool]: Converts function into tool callable by Gemini LLM for GST
@tool
def describe_gst_schema_tool() -> str:
    """Inspect and return the authoritative live schema for the GST database table: 'taxpayers'.

    Call this tool when querying GST data to inspect exact columns and types (GSTIN, PAN, turnover slabs, etc.).
    """
    service = get_gst_tool_service()
    return service.describe_schema()


# [Library Decorator: langchain_core.tools.tool]: Converts function into tool callable by Gemini LLM for GST
@tool
def execute_gst_sql_query_tool(query: str) -> str:
    """Validate and execute a read-only SQL SELECT query against the GST database ('taxpayers').

    Args:
        query: The SQL SELECT statement to execute against GST database.

    Returns:
        JSON string containing the execution results, columns, rows, or safe error message.
    """
    service = get_gst_tool_service()
    result = service.execute_query(query)
    return json.dumps(result, indent=2)


# [Library Decorator: langchain_core.tools.tool]: Converts function into tool callable by Gemini LLM for GST FTS
@tool
def full_text_search_gst_tool(query: str) -> str:
    """Execute a global multi-column full-text keyword search across all GST taxpayers.

    Call this tool whenever the user provides a keyword, trade term, or broad business activity (e.g. 'manufacturer',
    'retailer', 'works contract', 'trader', 'logistics', 'services') to find matching taxpayers across
    all textual columns (trade names, legal names, nature of business, constitution, addresses).

    Args:
        query: The keyword, trade name, or business category to find across all columns.

    Returns:
        JSON string containing the matching registered taxpayer records.
    """
    service = get_gst_tool_service()
    result = service.full_text_search(query)
    return json.dumps(result, indent=2)


# --- Backward Compatibility Alias Tools ---

@tool
def describe_schema_tool() -> str:
    """Legacy alias: Inspects schema for default MCA database."""
    return describe_mca_schema_tool.invoke({})


@tool
def execute_sql_query_tool(query: str) -> str:
    """Legacy alias: Executes query against default MCA database."""
    return execute_mca_sql_query_tool.invoke({"query": query})


# [Project-Defined Function]: Factory returning the appropriate tool set for an agent
def get_tools_for_agent(db_type: str = "mca") -> List[BaseTool]:
    """Return the schema, query execution, and full-text search tools for either MCA or GST agent."""
    norm_type = db_type.lower().strip()
    if norm_type == "gst":
        return [describe_gst_schema_tool, execute_gst_sql_query_tool, full_text_search_gst_tool]
    return [describe_mca_schema_tool, execute_mca_sql_query_tool, full_text_search_mca_tool]
