"""Universal Database Search Service for MCA Corporate and GST Taxpayer Data.

Provides a unified 'Ctrl + F' search across all textual columns in MySQL using
a consolidated search_document column with native FULLTEXT indexing, combined
with semantic keyword expansion.
"""

# [Library Import: typing]: Standard type annotations
from typing import Any, Dict, List, Optional, Tuple
# [Library Import: re]: Regular expression operations for token extraction and sanitization
import re
# [Library Import: logging]: Structured logging
import logging
# [Library Import: sqlalchemy]: Database engine, text execution, and error handling
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

# [Project-Defined Import: AppSettings]: Application settings contract
from src.config.settings import AppSettings, get_settings

# [Project-Defined Logger]: Module-level logger instance
logger = logging.getLogger("langgraph_sql_agent.search_service")


# [Project-Defined Function]: Cleans and normalizes raw cell values for JSON serialization
def serialize_cell_value(val: Any) -> Any:
    """Format and serialize raw database values safely."""
    if val is None:
        return None
    # [Built-in Python: hasattr]: Convert Decimal, date, or complex types to string/float
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val) if not isinstance(val, (int, float, bool)) else val


# [Project-Defined Class]: Dedicated Universal Search Service
class UniversalSearchService:
    """Universal multi-column database search service.
    
    Acts like 'Ctrl + F' across all attributes of corporate companies and
    registered taxpayers using MySQL FULLTEXT indexing on a consolidated search_document.
    """

    # [Project-Defined Method: __init__]: Constructor initializing engine and configuration
    def __init__(self, engine: Engine, db_type: str = "mca", settings: Optional[AppSettings] = None):
        """Initialize the search service.
        
        Args:
            engine: SQLAlchemy database engine instance.
            db_type: Target database type ('mca' or 'gst').
            settings: Optional AppSettings instance.
        """
        # [Instance Attribute: Engine]: Active database connection engine
        self.engine = engine
        # [Instance Attribute: str]: Normalized database identifier
        self.db_type = db_type.lower().strip()
        # [Instance Attribute: AppSettings]: Application runtime settings
        self.settings = settings or get_settings()

    # [Project-Defined Method]: Generates sanitized tokens and MySQL boolean mode query string
    def build_mysql_boolean_query(
        self,
        raw_query: str,
        expanded_terms: Optional[List[str]] = None,
    ) -> Tuple[str, List[str]]:
        """Construct a safe MySQL BOOLEAN MODE full-text match expression.
        
        Args:
            raw_query: The original search term provided by user.
            expanded_terms: Optional list of LLM-expanded synonyms, roots, and spelling variations.
            
        Returns:
            Tuple of (formatted_against_clause: str, unique_tokens_to_highlight: List[str]).
        """
        # [Built-in Python: list]: Aggregate all candidate search tokens
        candidates: List[str] = []
        if raw_query:
            candidates.extend(re.findall(r"[A-Za-z0-9_]+", raw_query))
        if expanded_terms:
            for term in expanded_terms:
                candidates.extend(re.findall(r"[A-Za-z0-9_]+", term))

        # [Built-in Python: set]: Common stop words excluded from boolean search
        stop_words = {"the", "a", "an", "of", "in", "and", "or", "to", "for", "with", "on", "at", "by", "is", "are"}

        # [Variable: List[str]]: Cleaned unique tokens
        unique_tokens: List[str] = []
        seen = set()
        for cand in candidates:
            c_lower = cand.lower().strip()
            if len(c_lower) >= 2 and c_lower not in stop_words and c_lower not in seen:
                seen.add(c_lower)
                unique_tokens.append(c_lower)

        if not unique_tokens:
            return "", []

        # In MySQL BOOLEAN MODE:
        # A list of words separated by space behaves like an OR search (ranks by relevance)
        # Adding '*' at the end of root tokens allows prefix matching (e.g. 'manufactur*')
        boolean_terms: List[str] = []
        for t in unique_tokens:
            # If word is long enough, add prefix wildcard for morphological variations
            if len(t) >= 4 and not t.endswith("*"):
                boolean_terms.append(f"{t}*")
            else:
                boolean_terms.append(t)

        # [Built-in Python: str.join]: Build MySQL AGAINST expression
        against_clause = " ".join(boolean_terms)
        return against_clause, unique_tokens

    # [Project-Defined Method]: Ensures the search_document column and FULLTEXT index exist in MySQL
    def ensure_search_document_indexed(self) -> bool:
        """Verify and dynamically ensure the consolidated search_document and FULLTEXT index exist."""
        # [Library Property: Engine.url]: Check database dialect
        is_sqlite = str(self.engine.url).startswith("sqlite")
        if is_sqlite:
            # SQLite uses virtual FTS5 tables instead of MySQL generated columns
            return True

        table_name = "companies" if self.db_type == "mca" else "taxpayers"

        try:
            with self.engine.connect() as conn:
                # Check if search_document column already exists in table
                chk_sql = text("""
                    SELECT COLUMN_NAME 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = :tbl AND COLUMN_NAME = 'search_document'
                """)
                res = conn.execute(chk_sql, {"tbl": table_name}).fetchone()

                if not res:
                    logger.info("[%s] Adding consolidated search_document column to %s...", self.db_type.upper(), table_name)
                    if self.db_type == "mca":
                        add_col_sql = text("""
                            ALTER TABLE companies 
                            ADD COLUMN search_document TEXT GENERATED ALWAYS AS (
                                CONCAT_WS(' ', 
                                    COALESCE(company_name, ''),
                                    COALESCE(cin_llpin, ''),
                                    COALESCE(entity_type, ''),
                                    COALESCE(activity_description, ''),
                                    COALESCE(category, ''),
                                    COALESCE(subcategory, ''),
                                    COALESCE(class, ''),
                                    COALESCE(state, ''),
                                    COALESCE(city_district, ''),
                                    COALESCE(registered_address, '')
                                )
                            ) STORED
                        """)
                    else:
                        add_col_sql = text("""
                            ALTER TABLE taxpayers 
                            ADD COLUMN search_document TEXT GENERATED ALWAYS AS (
                                CONCAT_WS(' ', 
                                    COALESCE(trade_name, ''),
                                    COALESCE(legal_name, ''),
                                    COALESCE(gstin, ''),
                                    COALESCE(nature_of_business, ''),
                                    COALESCE(constitution, ''),
                                    COALESCE(taxpayer_type, ''),
                                    COALESCE(address, ''),
                                    COALESCE(city, ''),
                                    COALESCE(state, '')
                                )
                            ) STORED
                        """)
                    conn.execute(add_col_sql)
                    conn.commit()

                    # Add MySQL FULLTEXT index
                    idx_name = f"idx_{table_name}_search_doc"
                    add_idx_sql = text(f"CREATE FULLTEXT INDEX {idx_name} ON {table_name}(search_document)")
                    conn.execute(add_idx_sql)
                    conn.commit()
                    logger.info("[%s] FULLTEXT index created successfully on %s(search_document).", self.db_type.upper(), table_name)

            return True
        except Exception as exc:
            logger.warning("[%s] Schema index verification note: %s", self.db_type.upper(), exc)
            return False

    # [Project-Defined Method]: Core search execution method
    def execute_search(
        self,
        query: str,
        expanded_terms: Optional[List[str]] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Execute universal 'Ctrl + F' multi-column search across companies or taxpayers.
        
        Args:
            query: The core user search term (e.g. 'jewellers', 'manufacture', 'textile').
            expanded_terms: Optional list of semantically expanded words/synonyms from the LLM.
            limit: Maximum records to return (clamped by sql_max_rows).
            
        Returns:
            Dictionary containing columns, rows, row_count, sql_query, and highlight tokens.
        """
        raw_query = str(query or "").strip()
        if not raw_query:
            return {
                "success": True,
                "status": "success",
                "sql_query": "-- Universal Search: No search term provided",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "search_term": "",
                "highlight_tokens": [],
                "error": None,
            }

        eff_limit = min(limit, self.settings.sql_max_rows)
        against_clause, tokens_to_highlight = self.build_mysql_boolean_query(raw_query, expanded_terms)

        is_sqlite = str(self.engine.url).startswith("sqlite")

        if is_sqlite:
            # SQLite FTS5 Compatibility Fallback
            return self._execute_sqlite_fts(raw_query, tokens_to_highlight, eff_limit)

        # Ensure MySQL FULLTEXT indexing is ready
        self.ensure_search_document_indexed()

        # Build MySQL Universal Search SQL
        if self.db_type == "mca":
            search_sql = text("""
                SELECT 
                    company_name,
                    cin_llpin,
                    entity_type,
                    state,
                    city_district,
                    activity_description,
                    registered_address,
                    MATCH(search_document) AGAINST(:against_clause IN BOOLEAN MODE) AS relevance_score
                FROM companies
                WHERE MATCH(search_document) AGAINST(:against_clause IN BOOLEAN MODE)
                ORDER BY relevance_score DESC
                LIMIT :limit
            """)
            display_sql = f"SELECT company_name, cin_llpin, entity_type, state, city_district, activity_description FROM companies WHERE MATCH(search_document) AGAINST('{against_clause}' IN BOOLEAN MODE) ORDER BY MATCH(search_document) AGAINST('{against_clause}' IN BOOLEAN MODE) DESC LIMIT {eff_limit};"
        else:
            search_sql = text("""
                SELECT 
                    gstin,
                    legal_name,
                    trade_name,
                    nature_of_business,
                    constitution,
                    taxpayer_type,
                    city,
                    state,
                    MATCH(search_document) AGAINST(:against_clause IN BOOLEAN MODE) AS relevance_score
                FROM taxpayers
                WHERE MATCH(search_document) AGAINST(:against_clause IN BOOLEAN MODE)
                ORDER BY relevance_score DESC
                LIMIT :limit
            """)
            display_sql = f"SELECT gstin, legal_name, trade_name, nature_of_business, city, state FROM taxpayers WHERE MATCH(search_document) AGAINST('{against_clause}' IN BOOLEAN MODE) ORDER BY MATCH(search_document) AGAINST('{against_clause}' IN BOOLEAN MODE) DESC LIMIT {eff_limit};"

        try:
            with self.engine.connect() as conn:
                result = conn.execute(search_sql, {"against_clause": against_clause, "limit": eff_limit})
                raw_cols = list(result.keys())
                # Exclude internal technical column 'relevance_score' from user table
                cols = [c for c in raw_cols if c != "relevance_score"]
                raw_rows = result.fetchall()

                rows_data = [
                    {col: serialize_cell_value(row._mapping[col]) for col in cols}
                    for row in raw_rows
                ]

                logger.info(
                    "[%s] MySQL Universal Search for '%s' returned %d rows.",
                    self.db_type.upper(),
                    raw_query,
                    len(rows_data),
                )

                return {
                    "success": True,
                    "status": "success",
                    "sql_query": display_sql,
                    "columns": cols,
                    "rows": rows_data,
                    "row_count": len(rows_data),
                    "search_term": raw_query,
                    "highlight_tokens": tokens_to_highlight,
                    "error": None,
                }

        except SQLAlchemyError as exc:
            logger.warning("[%s] MySQL Fulltext query exception: %s. Using multi-column fallback...", self.db_type.upper(), exc)
            return self._execute_mysql_like_fallback(raw_query, tokens_to_highlight, eff_limit)

    # [Project-Defined Helper]: Fallback for SQLite FTS5 during transition
    def _execute_sqlite_fts(self, raw_query: str, tokens: List[str], limit: int) -> Dict[str, Any]:
        """Execute search using SQLite FTS5 index during local transition."""
        fts_match_tokens = [f'"{t}"*' for t in tokens] if tokens else [f'"{raw_query}"*']
        fts_match_clause = " OR ".join(fts_match_tokens)

        if self.db_type == "mca":
            sql = text("""
                SELECT c.company_name, c.cin_llpin, c.entity_type, c.state, c.city_district, c.activity_description
                FROM companies c
                JOIN companies_fts f ON c.cin_llpin = f.cin_llpin
                WHERE companies_fts MATCH :match_term
                LIMIT :limit
            """)
            display_sql = f"SELECT company_name, cin_llpin, entity_type, state, city_district, activity_description FROM companies WHERE companies_fts MATCH '({fts_match_clause})' LIMIT {limit};"
        else:
            sql = text("""
                SELECT t.gstin, t.legal_name, t.trade_name, t.nature_of_business, t.city, t.state
                FROM taxpayers t
                JOIN taxpayers_fts f ON t.gstin = f.gstin
                WHERE taxpayers_fts MATCH :match_term
                LIMIT :limit
            """)
            display_sql = f"SELECT gstin, legal_name, trade_name, nature_of_business, city, state FROM taxpayers WHERE taxpayers_fts MATCH '({fts_match_clause})' LIMIT {limit};"

        try:
            with self.engine.connect() as conn:
                result = conn.execute(sql, {"match_term": fts_match_clause, "limit": limit})
                cols = list(result.keys())
                raw_rows = result.fetchall()
                rows_data = [
                    {col: serialize_cell_value(val) for col, val in zip(cols, row)}
                    for row in raw_rows
                ]
                return {
                    "success": True,
                    "status": "success",
                    "sql_query": display_sql,
                    "columns": cols,
                    "rows": rows_data,
                    "row_count": len(rows_data),
                    "search_term": raw_query,
                    "highlight_tokens": tokens,
                    "error": None,
                }
        except Exception as exc:
            logger.error("[%s] SQLite FTS execution error: %s", self.db_type.upper(), exc)
            return {
                "success": False,
                "status": "execution_failed",
                "sql_query": display_sql,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "search_term": raw_query,
                "highlight_tokens": tokens,
                "error": str(exc),
            }

    # [Project-Defined Helper]: Resilient LIKE fallback across all columns
    def _execute_mysql_like_fallback(self, raw_query: str, tokens: List[str], limit: int) -> Dict[str, Any]:
        """Multi-column LIKE fallback if FULLTEXT index is temporarily rebuilding."""
        like_exprs = [f"%{t}%" for t in (tokens or [raw_query])]
        # Construct multi-column OR conditions
        if self.db_type == "mca":
            conditions = " OR ".join(
                f"(company_name LIKE :t{i} OR activity_description LIKE :t{i} OR registered_address LIKE :t{i} OR city_district LIKE :t{i} OR state LIKE :t{i})"
                for i in range(len(like_exprs))
            )
            sql = text(f"""
                SELECT company_name, cin_llpin, entity_type, state, city_district, activity_description
                FROM companies
                WHERE {conditions}
                LIMIT :limit
            """)
            display_sql = f"SELECT company_name, cin_llpin, entity_type, state, city_district, activity_description FROM companies WHERE ({conditions}) LIMIT {limit};"
        else:
            conditions = " OR ".join(
                f"(trade_name LIKE :t{i} OR legal_name LIKE :t{i} OR nature_of_business LIKE :t{i} OR address LIKE :t{i} OR city LIKE :t{i} OR state LIKE :t{i})"
                for i in range(len(like_exprs))
            )
            sql = text(f"""
                SELECT gstin, legal_name, trade_name, nature_of_business, city, state
                FROM taxpayers
                WHERE {conditions}
                LIMIT :limit
            """)
            display_sql = f"SELECT gstin, legal_name, trade_name, nature_of_business, city, state FROM taxpayers WHERE ({conditions}) LIMIT {limit};"

        params = {f"t{i}": expr for i, expr in enumerate(like_exprs)}
        params["limit"] = limit

        try:
            with self.engine.connect() as conn:
                result = conn.execute(sql, params)
                cols = list(result.keys())
                raw_rows = result.fetchall()
                rows_data = [
                    {col: serialize_cell_value(val) for col, val in zip(cols, row)}
                    for row in raw_rows
                ]
                return {
                    "success": True,
                    "status": "success",
                    "sql_query": display_sql,
                    "columns": cols,
                    "rows": rows_data,
                    "row_count": len(rows_data),
                    "search_term": raw_query,
                    "highlight_tokens": tokens,
                    "error": None,
                }
        except Exception as exc:
            return {
                "success": False,
                "status": "execution_failed",
                "sql_query": display_sql,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "search_term": raw_query,
                "highlight_tokens": tokens,
                "error": str(exc),
            }
