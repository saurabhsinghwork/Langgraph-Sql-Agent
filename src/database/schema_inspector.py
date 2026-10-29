"""Live schema inspector for approved MCA and GST database tables.

Inspects live database metadata using SQLAlchemy, restricts discovery
strictly to the approved tables for MCA ('companies', 'directors') or GST ('taxpayers'),
and formats a schema representation grounded for the corresponding agent.
"""

from __future__ import annotations

# [Built-in Python Module: logging]: Event logging framework
import logging
# [Built-in Python Module: typing]: Type annotation helpers
from typing import Any, Dict, List, Optional, Tuple
# [Library Function: sqlalchemy.inspect]: Introspects database schemas, tables, and constraints
from sqlalchemy import inspect
# [Library Class: sqlalchemy.engine.Engine]: Type definition for SQLAlchemy connection engine
from sqlalchemy.engine import Engine

# [Project-Defined Import from src.database.connection]: Engine singleton resolver
from src.database.connection import get_engine

# [Library Instance: logging.Logger]: Logger for tracking schema inspection events
logger = logging.getLogger(__name__)

# [Project-Defined Constant: tuple[str, ...]]: Strict allowlist of authorized MCA tables (including full-text search indexes)
APPROVED_MCA_TABLES = ("companies", "directors", "companies_fts", "directors_fts")
# [Project-Defined Constant: tuple[str, ...]]: Strict allowlist of authorized GST tables (including full-text search index)
APPROVED_GST_TABLES = ("taxpayers", "taxpayers_fts")
# [Project-Defined Constant: tuple[str, ...]]: Combined authorized tables across both databases
APPROVED_TABLES = ("companies", "directors", "taxpayers", "companies_fts", "directors_fts", "taxpayers_fts")


# [Project-Defined Class]: Encapsulates dynamic database schema introspection & formatting for MCA/GST
class SchemaInspector:
    """Inspects and formats schema details for the approved database tables."""

    # [Project-Defined Method]: Initializes inspector with active SQLAlchemy Engine and approved table allowlist
    def __init__(
        self,
        engine: Optional[Engine] = None,
        approved_tables: Optional[Tuple[str, ...]] = None,
        db_type: str = "mca",
    ):
        # [Project-Defined Attribute: str]: Database classification identifier ('mca' or 'gst')
        self.db_type = db_type.lower().strip()
        # [Project-Defined Attribute: Engine]: Store provided engine or acquire singleton for db_type
        self.engine = engine or get_engine(db_type=self.db_type)
        # [Project-Defined Attribute: tuple[str, ...]]: Authorized table allowlist for this inspector instance
        if approved_tables is not None:
            self.approved_tables = approved_tables
        elif self.db_type == "gst":
            self.approved_tables = APPROVED_GST_TABLES
        else:
            self.approved_tables = APPROVED_MCA_TABLES

    # [Project-Defined Method]: Returns tables currently present in database that match allowlist
    def get_live_tables(self) -> List[str]:
        """Return the list of approved tables present in the live database."""
        # [Library Function: sqlalchemy.inspect]: Create Inspector object for the engine
        inspector = inspect(self.engine)
        # [Library Method: Inspector.get_table_names]: Retrieve all table names in target DB
        all_tables = inspector.get_table_names()
        # [Built-in Python: list comprehension]: Filter strictly to approved tables (case-insensitive)
        approved_found = [tbl for tbl in all_tables if tbl.lower() in self.approved_tables]
        return approved_found

    # [Project-Defined Method]: Introspects column types, keys, and foreign relations for one table
    def get_table_details(self, table_name: str) -> Dict[str, Any]:
        """Get column and foreign key metadata for a specific approved table."""
        # [Built-in Python Method: str.lower, str.strip]: Normalize table name
        tbl_lower = table_name.lower().strip()
        # Enforce security boundary against querying unapproved tables
        if tbl_lower not in self.approved_tables:
            # [Built-in Python Exception: ValueError]: Reject unauthorized table introspection
            raise ValueError(
                f"Access denied: Table '{table_name}' is not in the approved tables list {self.approved_tables}."
            )

        # [Library Function: sqlalchemy.inspect]: Instantiate inspector
        inspector = inspect(self.engine)
        # [Library Method: Inspector.get_columns]: Returns list of column metadata dicts
        columns_raw = inspector.get_columns(tbl_lower)
        # [Library Method: Inspector.get_foreign_keys]: Returns list of foreign key dictionaries
        fks_raw = inspector.get_foreign_keys(tbl_lower)
        # [Library Method: Inspector.get_pk_constraint]: Returns primary key constraint details
        pk_constraint = inspector.get_pk_constraint(tbl_lower)
        # [Variable: list]: Extract primary key column names
        pk_columns = pk_constraint.get("constrained_columns", []) if pk_constraint else []

        # [Variable: list]: Build structured column definitions
        columns = []
        for col in columns_raw:
            columns.append({
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
                "is_primary_key": col["name"] in pk_columns,
                "default": str(col.get("default", "")) if col.get("default") else None,
            })

        # [Variable: list]: Build structured foreign key relation definitions
        foreign_keys = []
        for fk in fks_raw:
            foreign_keys.append({
                "constrained_columns": fk.get("constrained_columns", []),
                "referred_table": fk.get("referred_table", ""),
                "referred_columns": fk.get("referred_columns", []),
            })

        # Return table schema specification dictionary
        return {
            "table_name": tbl_lower,
            "columns": columns,
            "foreign_keys": foreign_keys,
            "primary_key": pk_columns,
        }

    # [Project-Defined Method]: Aggregates full metadata across all live approved tables
    def get_full_schema_summary(self) -> Dict[str, Any]:
        """Retrieve live metadata for all approved tables."""
        live_tables = self.get_live_tables()
        schema: Dict[str, Any] = {}
        for tbl in live_tables:
            schema[tbl] = self.get_table_details(tbl)
        return schema

    # [Project-Defined Method]: Converts live schema into concise markdown for Gemini prompt
    def format_schema_for_prompt(self) -> str:
        """Format live schema metadata into a concise, clear string for the LLM prompt."""
        live_tables = self.get_live_tables()
        # Guard against unseeded or empty database
        if not live_tables:
            return (
                f"WARNING: No approved tables found in the {self.db_type.upper()} database. "
                f"Approved tables are: {', '.join(self.approved_tables)}. "
                "Ensure database seeding scripts have been executed."
            )

        # [Variable: List[str]]: Line buffer for formatted markdown
        db_label = "MCA Corporate" if self.db_type == "mca" else "GST Taxpayer"
        lines: List[str] = [
            f"### Approved {db_label} Tables and Columns (authoritative live schema):\n"
        ]

        for tbl_name in self.approved_tables:
            if tbl_name not in live_tables:
                continue

            details = self.get_table_details(tbl_name)
            lines.append(f"Table: `{tbl_name}`")

            col_parts: List[str] = []
            for col in details["columns"]:
                pk_flag = " [PK]" if col["is_primary_key"] else ""
                col_parts.append(f"  - `{col['name']}` ({col['type']}){pk_flag}")
            lines.extend(col_parts)

            # Append foreign key relationships if present
            if details["foreign_keys"]:
                lines.append("  Foreign Keys:")
                for fk in details["foreign_keys"]:
                    c_cols = ", ".join(fk["constrained_columns"])
                    r_cols = ", ".join(fk["referred_columns"])
                    lines.append(
                        f"    - (`{c_cols}`) -> `{fk['referred_table']}`(`{r_cols}`)"
                    )
            lines.append("")

        # [Built-in Python Method: str.join]: Assemble full prompt section
        return "\n".join(lines)

    # [Project-Defined Method]: Healthcheck verifying presence of required tables
    def verify_schema_integrity(self) -> Tuple[bool, List[str]]:
        """Verify that all approved tables exist in this database.

        Returns:
            Tuple of (is_valid: bool, issues: list of error descriptions).
        """
        # [Variable: List[str]]: Collect missing table warning messages
        issues: List[str] = []
        live_tables = self.get_live_tables()

        for approved in self.approved_tables:
            if approved not in live_tables:
                issues.append(f"Missing required table in {self.db_type.upper()} DB: '{approved}'")

        # Return boolean validity flag and issues list
        return len(issues) == 0, issues
