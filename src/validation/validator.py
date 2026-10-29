"""SQL Validation Engine using SQLGlot AST analysis for MCA and GST databases.

Enforces strict read-only query policies:
1. Rejects multiple statements (SQL injection mitigation).
2. Allows only SELECT statements (and UNION of SELECTs).
3. Restricts all referenced tables to the approved allowlist for the database:
   - MCA Database: 'companies', 'directors'
   - GST Database: 'taxpayers'
4. Rejects dangerous functions, system variables, file operations, and DDL/DML.
5. Injects or clamps row LIMIT clauses to enforce SQL_MAX_ROWS bound.
"""

from __future__ import annotations

# [Built-in Python Module: logging]: Event logging framework
import logging
# [Built-in Python Module: dataclasses.dataclass]: Decorator generating boilerplate for structured data containers
from dataclasses import dataclass
# [Built-in Python Module: typing]: Type annotation helpers
from typing import List, Optional, Set, Tuple, Union
# [Library Imports: sqlglot]: SQL parser, transpiler, and Abstract Syntax Tree (AST) analyzer
import sqlglot
# [Library Imports: sqlglot.exp]: Module defining SQL AST expression nodes
from sqlglot import exp

# [Project-Defined Imports from src.database.schema_inspector]: Authorized table names tuples
from src.database.schema_inspector import APPROVED_TABLES, APPROVED_MCA_TABLES, APPROVED_GST_TABLES

# [Library Instance: logging.Logger]: Logger for tracking query validation events
logger = logging.getLogger(__name__)

# [Project-Defined Constant: Set[str]]: Dangerous SQL functions and keywords that must be blocked
DISALLOWED_FUNCTIONS: Set[str] = {
    "benchmark",
    "sleep",
    "load_file",
    "sys_eval",
    "sys_exec",
    "system",
    "schema",
    "database",
    "user",
    "current_user",
    "session_user",
    "version",
}

# [Project-Defined Constant: Set[str]]: Universal fallback table allowlist
ALLOWED_TABLE_SET: Set[str] = set(APPROVED_TABLES)


# [Project-Defined Dataclass]: Encapsulates outcome of SQLGlot AST validation
@dataclass
class ValidationResult:
    """Result of SQL AST validation."""

    # [Project-Defined Attribute: bool]: Flag indicating if query passed all security checks
    is_valid: bool
    # [Project-Defined Attribute: Optional[str]]: Sanitized SQL statement with clamped LIMIT clause
    sanitized_sql: Optional[str] = None
    # [Project-Defined Attribute: Optional[str]]: Detailed error description if validation failed
    error_message: Optional[str] = None
    # [Project-Defined Attribute: List[str]]: Extracted table names referenced in query
    referenced_tables: List[str] = None

    # [Built-in Python Dataclass Method: __post_init__]: Default mutable list initialization
    def __post_init__(self):
        if self.referenced_tables is None:
            self.referenced_tables = []


# [Project-Defined Class]: Security engine performing AST validation on SQL queries for MCA and GST
class SQLValidator:
    """AST-based SQL validator enforcing read-only safety policies."""

    # [Project-Defined Method]: Initializes validator with row limit ceiling, dialect, and database-specific table allowlist
    def __init__(
        self,
        max_rows: int = 50,
        dialect: str = "mysql",
        allowed_tables: Optional[Union[Set[str], Tuple[str, ...], List[str]]] = None,
        db_type: str = "mca",
    ):
        # [Project-Defined Attribute: int]: Maximum permitted rows (SQL_MAX_ROWS)
        self.max_rows = max_rows
        # [Project-Defined Attribute: str]: SQL dialect ('mysql' or 'sqlite')
        self.dialect = dialect
        # [Project-Defined Attribute: str]: Database type identifier ('mca' or 'gst')
        self.db_type = db_type.lower().strip()

        # Set allowed tables allowlist for this validator
        if allowed_tables is not None:
            self.allowed_tables = set(tbl.lower() for tbl in allowed_tables)
        elif self.db_type == "gst":
            self.allowed_tables = set(APPROVED_GST_TABLES)
        elif self.db_type == "mca":
            self.allowed_tables = set(APPROVED_MCA_TABLES)
        else:
            self.allowed_tables = ALLOWED_TABLE_SET

    # [Project-Defined Method]: Validates and sanitizes a candidate SQL query string
    def validate(self, sql_query: str) -> ValidationResult:
        """Validate a candidate SQL query against security and policy rules.

        Args:
            sql_query: Raw SQL query string proposed by the LLM.

        Returns:
            ValidationResult with sanitized SQL or specific error message.
        """
        # Guard against blank queries
        if not sql_query or not sql_query.strip():
            # [Project-Defined Dataclass Instance: ValidationResult]
            return ValidationResult(
                is_valid=False,
                error_message="Validation error: SQL query is empty.",
            )

        # [Built-in Python Method: str.strip]: Strip whitespace
        cleaned_sql = sql_query.strip()
        # Remove trailing semicolons for consistent AST parsing
        while cleaned_sql.endswith(";"):
            cleaned_sql = cleaned_sql[:-1].strip()

        # Step 1: Parse SQL into AST expressions
        try:
            # [Library Function: sqlglot.parse]: Parse raw string into AST expression nodes
            expressions = sqlglot.parse(cleaned_sql, read=self.dialect)
        except Exception as exc:
            # [Library Method: Logger.warning]: Log parser failure
            logger.warning("SQL syntax parse error: %s", exc)
            return ValidationResult(
                is_valid=False,
                error_message=f"SQL syntax error: Unable to parse query. Details: {str(exc)}",
            )

        # Step 2: Reject multiple statements (mitigates SQL injection via statement stacking)
        # [Built-in Python Function: len]: Count parsed statements
        if len(expressions) == 0:
            return ValidationResult(
                is_valid=False,
                error_message="Validation error: No valid SQL statement found.",
            )
        if len(expressions) > 1:
            return ValidationResult(
                is_valid=False,
                error_message="Validation rejected: Multiple statements are not permitted (detected potential SQL injection or multiple queries).",
            )

        # [Variable: exp.Expression]: Extract root AST node of the single statement
        ast = expressions[0]

        # Step 3: Enforce statement type is strictly SELECT (or Union of Selects)
        # [Library Classes: sqlglot.exp.Select, sqlglot.exp.Union]
        if not isinstance(ast, (exp.Select, exp.Union)):
            # [Built-in Python: type().__name__]: Get statement type name
            stmt_type = type(ast).__name__.upper()
            return ValidationResult(
                is_valid=False,
                error_message=(
                    f"Validation rejected: Disallowed statement type '{stmt_type}'. "
                    "Only read-only SELECT queries are permitted."
                ),
            )

        # Step 4: Disallow file exports (INTO OUTFILE / DUMPFILE / INTO VARIABLE)
        # [Library Method: Expression.find_all]: Traverse AST for exp.Into nodes
        # [Library Class: sqlglot.exp.Into]
        for into_node in ast.find_all(exp.Into):
            return ValidationResult(
                is_valid=False,
                error_message="Validation rejected: 'INTO' clause (OUTFILE/DUMPFILE/VARIABLES) is prohibited.",
            )

        # Step 5: Check all referenced tables against approved table allowlist
        # [Variable: List[str]]: Accumulate valid table names found in the AST
        referenced_tables: List[str] = []
        # [Library Method: Expression.find_all]: Traverse AST for exp.Table nodes
        # [Library Class: sqlglot.exp.Table]
        for table_node in ast.find_all(exp.Table):
            # [Variable: str]: Normalize table name
            table_name = table_node.name.lower().strip()
            # If the table has a db qualification, e.g. mysql.user, reject it
            if table_node.db:
                return ValidationResult(
                    is_valid=False,
                    # [Library Method: Expression.sql]: Render node back to SQL string
                    error_message=f"Validation rejected: Schema-qualified table reference '{table_node.sql()}' is prohibited.",
                )
            # Enforce that table is within the allowed tables for this database
            if table_name and table_name not in self.allowed_tables:
                return ValidationResult(
                    is_valid=False,
                    error_message=(
                        f"Validation rejected: Table '{table_name}' is not allowed in {self.db_type.upper()} database. "
                        f"Permitted tables are: {', '.join(sorted(self.allowed_tables))}."
                    ),
                    referenced_tables=referenced_tables,
                )
            if table_name and table_name not in referenced_tables:
                referenced_tables.append(table_name)

        # Guard: Query must reference at least one approved table
        if not referenced_tables:
            return ValidationResult(
                is_valid=False,
                error_message=f"Validation rejected: Query does not reference any approved tables in {self.db_type.upper()} database.",
            )

        # Step 6: Check for disallowed functions (SLEEP, BENCHMARK, etc.)
        # [Library Classes: sqlglot.exp.Anonymous, sqlglot.exp.Func]
        for func_node in ast.find_all(exp.Anonymous, exp.Func):
            # [Built-in Python: hasattr]: Safely extract function identifier
            func_name = func_node.name.lower().strip() if hasattr(func_node, "name") else ""
            if func_name in DISALLOWED_FUNCTIONS:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Validation rejected: Function '{func_name}()' is prohibited for security reasons.",
                    referenced_tables=referenced_tables,
                )

        # Step 7: Enforce and clamp LIMIT clause to SQL_MAX_ROWS
        # [Library Method: Expression.find]: Search for existing exp.Limit node
        # [Library Class: sqlglot.exp.Limit]
        limit_node = ast.find(exp.Limit)
        if limit_node and limit_node.expression:
            try:
                # [Built-in Python: int()]: Parse numeric value of current LIMIT
                curr_limit = int(limit_node.expression.sql())
                if curr_limit > self.max_rows:
                    # [Library Method: Expression.set]: Clamp limit AST node to max_rows
                    # [Library Class Method: sqlglot.exp.Literal.number]
                    limit_node.set("expression", exp.Literal.number(self.max_rows))
            except (ValueError, TypeError):
                limit_node.set("expression", exp.Literal.number(self.max_rows))
        else:
            # [Library Method: Expression.limit]: Append LIMIT clause if omitted by model
            ast = ast.limit(self.max_rows)

        # [Library Method: Expression.sql]: Transpile AST into canonical SQL query string
        sanitized_sql = ast.sql(dialect=self.dialect)

        # Return successful validation result
        return ValidationResult(
            is_valid=True,
            sanitized_sql=sanitized_sql,
            referenced_tables=referenced_tables,
        )
