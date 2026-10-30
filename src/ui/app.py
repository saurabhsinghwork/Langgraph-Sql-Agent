"""Streamlit Web Interface for Dual LangGraph SQL Agents (MCA and GST).

Features:
- Dual-agent orchestration: MCA Corporate Agent and GST Taxpayer Agent.
- Premium modern UI with custom glassmorphism and styled status badges.
- Tabbed interface supporting MCA Search, GST Search, and Unified Cross-Database Search.
- Natural language answer presentation.
- Interactive results table with pandas and CSV download.
- Generated SQL query inside an expandable inspector.
- Guided clarification handling for ambiguous questions.
- Real-time dual database health checks and schema diagnostic sidebar.
- Single-keystroke Enter execution for all search inputs (no Ctrl+Enter required).
- Interactive quick example query chips with automatic execution.
- Collision-free scoped widget keys preventing duplicate element errors.
"""

from __future__ import annotations

# [Built-in Python Module: os]: Operating system interfaces
import os
# [Built-in Python Module: re]: Regular expression matching for search keyword tokenization and text highlighting
import re
# [Built-in Python Module: sys]: System-specific parameters and module path manipulation
import sys
# [Built-in Python Module: typing]: Type annotations
from typing import Any, List, Optional
# [Built-in Python Class: pathlib.Path]: Filesystem path object
from pathlib import Path

# Ensure project root is in sys.path
# [Variable: Path]: Absolute path to repository root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
# [Built-in Python: if]: Prepend project root to sys.path if missing
if str(PROJECT_ROOT) not in sys.path:
    # [Built-in Python Method: sys.path.insert]
    sys.path.insert(0, str(PROJECT_ROOT))

# [Built-in Python Module: importlib]: Dynamic module loading and hot-reloading
import importlib
# [Library Import: pandas as pd]: Data manipulation and tabular representation library
import pandas as pd
# [Library Import: streamlit as st]: Web application framework for Python
import streamlit as st

# [Project-Defined Modules]: Local package submodules
import src.config.settings
import src.database.connection
import src.database.schema_inspector
import src.database.seeder
import src.tools.sql_tools
import src.agent.graph

# Force reload submodules so changes in .env or code take effect immediately in running Streamlit
# [Built-in Python Function: importlib.reload]: Invalidates cache and re-imports modules from disk
importlib.reload(src.config.settings)
importlib.reload(src.database.connection)
importlib.reload(src.database.schema_inspector)
importlib.reload(src.database.seeder)
importlib.reload(src.tools.sql_tools)
importlib.reload(src.agent.graph)

# [Project-Defined Imports]: Orchestration, models, configuration, and database components
from src.agent.graph import run_agent, run_mca_agent, run_gst_agent
from src.agent.models import AgentResult, AgentStatus
from src.config.settings import get_settings
from src.database.connection import test_connection, test_all_connections, get_engine
from src.database.schema_inspector import SchemaInspector, APPROVED_MCA_TABLES, APPROVED_GST_TABLES
from src.database.seeder import seed_database, seed_mca_database, seed_gst_database

# [Library Function: streamlit.set_page_config]: Configure browser tab title, favicon, and wide layout
st.set_page_config(
    page_title="MCA & GST SQL Agents",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for rich aesthetics
# [Library Function: streamlit.markdown]: Inject custom CSS stylesheet with glassmorphism aesthetics and strict zero-overlap layout constraints
st.markdown(
    """
    <style>
    /* Global box-sizing to strictly prevent width blowouts and overlapping */
    *, *::before, *::after {
        box-sizing: border-box !important;
    }

    /* Main container styling */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Strict Streamlit column containment: prevents side-by-side elements from painting over each other */
    [data-testid="column"], [data-testid="stColumn"], .stColumn {
        min-width: 0 !important;
        max-width: 100% !important;
        overflow-x: auto !important;
        overflow-y: visible !important;
        contain: paint !important;
        box-sizing: border-box !important;
        flex-shrink: 1 !important;
    }

    /* Horizontal blocks spacing and boundary constraint */
    [data-testid="stHorizontalBlock"] {
        gap: 20px !important;
        width: 100% !important;
        max-width: 100% !important;
        overflow: visible !important;
        box-sizing: border-box !important;
    }

    /* Vertical block within columns must not overflow horizontally */
    [data-testid="stVerticalBlock"] {
        max-width: 100% !important;
        min-width: 0 !important;
        box-sizing: border-box !important;
    }

    /* Dataframe container: guarantees full width without bleeding past column borders */
    [data-testid="stDataFrame"], .stDataFrame, .stDataFrameContainer {
        width: 100% !important;
        max-width: 100% !important;
        overflow-x: auto !important;
        overflow-y: hidden !important;
        box-sizing: border-box !important;
        display: block !important;
        position: relative !important;
    }

    [data-testid="stDataFrame"] > div {
        max-width: 100% !important;
        box-sizing: border-box !important;
    }

    /* Canvas containment inside Glide Data Grid */
    [data-testid="stDataFrame"] canvas {
        max-width: 100% !important;
    }

    /* Header card */
    .header-card {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        padding: 24px 32px;
        border-radius: 12px;
        border: 1px solid #374151;
        margin-bottom: 24px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
        clear: both !important;
    }
    .header-title {
        font-size: 28px;
        font-weight: 700;
        color: #f3f4f6;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .header-sub {
        font-size: 14px;
        color: #9ca3af;
        margin-top: 8px;
    }

    /* Badges */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 12px;
    }
    .badge-success { background-color: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #059669; }
    .badge-clarify { background-color: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #d97706; }
    .badge-reject { background-color: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #dc2626; }
    .badge-config { background-color: rgba(139, 92, 246, 0.2); color: #c084fc; border: 1px solid #7c3aed; }

    /* Result Box: strictly bounded to 100% width with wrapping to avoid overlap */
    .explanation-box {
        background-color: #161b22;
        border-left: 4px solid #38bdf8;
        padding: 16px 20px;
        border-radius: 6px;
        font-size: 15px;
        line-height: 1.6;
        margin-bottom: 18px;
        color: #f0f6fc;
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
        word-break: break-word !important;
        overflow-wrap: break-word !important;
        white-space: normal !important;
        clear: both !important;
        position: relative !important;
    }
    
    /* Clarification box */
    .clarification-box {
        background-color: #1e1b12;
        border-left: 4px solid #f59e0b;
        padding: 16px 20px;
        border-radius: 6px;
        font-size: 15px;
        line-height: 1.6;
        margin-bottom: 18px;
        color: #fef3c7;
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
        word-break: break-word !important;
        overflow-wrap: break-word !important;
        white-space: normal !important;
        clear: both !important;
        position: relative !important;
    }

    /* Metric pill container and pills */
    .metric-container {
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 10px !important;
        margin-bottom: 16px !important;
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
    }
    .metric-pill {
        display: inline-flex !important;
        align-items: center !important;
        gap: 8px !important;
        background: #21262d !important;
        padding: 6px 14px !important;
        border-radius: 8px !important;
        font-size: 13px !important;
        color: #8b949e !important;
        border: 1px solid #30363d !important;
        margin: 0 !important;
        white-space: nowrap !important;
        flex-shrink: 0 !important;
    }
    .metric-val {
        color: #58a6ff;
        font-weight: 600;
    }

    /* Full-Text Search Keyword Highlighting */
    .keyword-highlight {
        background-color: rgba(234, 179, 8, 0.35) !important;
        color: #fef08a !important;
        padding: 1px 6px !important;
        border-radius: 4px !important;
        font-weight: 700 !important;
        border: 1px solid rgba(234, 179, 8, 0.6) !important;
        display: inline !important;
    }
    .keyword-pill {
        background: rgba(234, 179, 8, 0.16) !important;
        border: 1px solid #eab308 !important;
        color: #fde047 !important;
    }

    /* Responsive HTML Table with Word-Level Highlighting */
    .table-container {
        width: 100% !important;
        max-width: 100% !important;
        max-height: 480px !important;
        overflow-x: auto !important;
        overflow-y: auto !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        background: #0d1117 !important;
        margin-top: 8px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
    }
    .result-table {
        width: 100% !important;
        border-collapse: collapse !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        font-size: 13px !important;
        line-height: 1.5 !important;
        text-align: left !important;
    }
    .result-table thead {
        position: sticky !important;
        top: 0 !important;
        background: #161b22 !important;
        z-index: 2 !important;
    }
    .result-table th {
        padding: 10px 14px !important;
        color: #8b949e !important;
        font-weight: 600 !important;
        font-size: 12px !important;
        border-bottom: 2px solid #30363d !important;
        white-space: nowrap !important;
        background: #161b22 !important;
        letter-spacing: 0.3px !important;
    }
    .result-table td {
        padding: 9px 14px !important;
        color: #c9d1d9 !important;
        border-bottom: 1px solid #21262d !important;
        white-space: normal !important;
        word-break: break-word !important;
    }
    .result-table tr:hover td {
        background-color: rgba(56, 189, 248, 0.05) !important;
    }
    .result-table .idx-col {
        color: #58a6ff !important;
        font-weight: 600 !important;
        text-align: center !important;
        width: 45px !important;
        min-width: 45px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# [Project-Defined Function]: Renders the collapsible sidebar with dual-database health and schema details
def render_sidebar():
    """Render configuration status, schema health, and database controls in sidebar."""
    # [Library Context Manager: streamlit.sidebar]: Scope UI elements inside Streamlit sidebar drawer
    with st.sidebar:
        st.markdown("### ⚙️ System Settings")
        # [Project-Defined Function: get_settings]: Retrieve settings with hot reload
        settings = get_settings(reload=True)

        # Dual database health check
        mca_conn, mca_msg = test_connection(db_type="mca", settings=settings)
        gst_conn, gst_msg = test_connection(db_type="gst", settings=settings)

        # MCA Connection card
        st.markdown("#### 🏛️ MCA Database")
        if mca_conn:
            st.success(f"🟢 Connected\n\n`{mca_msg}`")
        else:
            st.error(f"🔴 Offline\n\n`{mca_msg}`")

        # GST Connection card
        st.markdown("#### 🧾 GST Database")
        if gst_conn:
            st.success(f"🟢 Connected\n\n`{gst_msg}`")
        else:
            st.error(f"🔴 Offline\n\n`{gst_msg}`")

        # LLM status
        has_api_key = bool(settings.gemini_api_key.strip())
        if has_api_key:
            st.info(f"🤖 Model: `{settings.gemini_model_id}`\n\nAPI Key: `Configured ✓`")
        else:
            st.warning("⚠️ Gemini API Key not set in `.env`.")

        st.markdown("---")
        st.markdown("### 🗄️ Database Tools")
        col_seed1, col_seed2 = st.columns(2)
        with col_seed1:
            if st.button("🌱 Re-seed MCA", use_container_width=True, key="sidebar_seed_mca"):
                with st.spinner("Seeding MCA..."):
                    ok, msg = seed_mca_database(settings=settings)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        with col_seed2:
            if st.button("🌱 Re-seed GST", use_container_width=True, key="sidebar_seed_gst"):
                with st.spinner("Seeding GST..."):
                    ok, msg = seed_gst_database(settings=settings)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        if st.button("🔄 Re-seed Both Databases", use_container_width=True, key="sidebar_seed_both"):
            with st.spinner("Seeding both databases..."):
                ok, msg = seed_database(target="all", settings=settings)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        st.markdown("---")
        st.markdown("### 📋 MCA Approved Tables")
        try:
            mca_inspector = SchemaInspector(engine=get_engine(db_type="mca", settings=settings), db_type="mca")
            for tbl in mca_inspector.get_live_tables():
                with st.expander(f"📁 MCA: {tbl}"):
                    details = mca_inspector.get_table_details(tbl)
                    cols_df = pd.DataFrame([
                        {
                            "Column": c["name"],
                            "Type": c["type"],
                            "PK": "✓" if c["is_primary_key"] else "",
                        }
                        for c in details["columns"]
                    ])
                    st.dataframe(cols_df, hide_index=True, use_container_width=True)
        except Exception as exc:
            st.caption(f"MCA inspection error: {type(exc).__name__}")

        st.markdown("### 📋 GST Approved Tables")
        try:
            gst_inspector = SchemaInspector(engine=get_engine(db_type="gst", settings=settings), db_type="gst")
            for tbl in gst_inspector.get_live_tables():
                with st.expander(f"📁 GST: {tbl}"):
                    details = gst_inspector.get_table_details(tbl)
                    cols_df = pd.DataFrame([
                        {
                            "Column": c["name"],
                            "Type": c["type"],
                            "PK": "✓" if c["is_primary_key"] else "",
                        }
                        for c in details["columns"]
                    ])
                    st.dataframe(cols_df, hide_index=True, use_container_width=True)
        except Exception as exc:
            st.caption(f"GST inspection error: {type(exc).__name__}")

        st.markdown("---")
        st.caption("Dual LangGraph SQL Agents • MCA & GST v2.0")


# [Project-Defined Function]: Renders the application banner header
def render_header():
    """Render top page header."""
    st.markdown(
        """
        <div class="header-card">
            <h1 class="header-title">🏛️ Dual LangGraph SQL Agents</h1>
            <p class="header-sub">
                Natural-language querying for <strong>Ministry of Corporate Affairs (MCA)</strong> companies & directors, 
                and <strong>Goods & Services Tax (GST)</strong> registered taxpayers using Gemini Flash-Lite and AST security validation.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# [Project-Defined Function]: Extracts search keyword tokens and word roots strictly during FTS keyword search
def get_search_tokens(result: AgentResult) -> List[str]:
    """Extract cleaned search keyword tokens and word roots ONLY when a full-text search (FTS) is active."""
    # [Built-in Python: Optional[str]]: Detect FTS candidate keyword
    fts_candidate: Optional[str] = getattr(result, "search_term", None)

    # If search_term was not explicitly set on result, check if SQL executed against an FTS table using MATCH
    if not fts_candidate and result.sql_query:
        # Strictly verify that an FTS MATCH statement was executed
        if re.search(r'\b(?:MATCH|_fts)\b', result.sql_query, flags=re.IGNORECASE):
            # [Library Function: re.findall]: Extract FTS MATCH clause content
            match_fts = re.findall(r'MATCH\s+[\'"](.*?)[\'"]', result.sql_query, flags=re.IGNORECASE)
            for m in match_fts:
                # Strip wildcards, quotes, boolean operators, and parentheses from FTS expression
                cleaned = re.sub(r'["*()]', '', m)
                cleaned = re.sub(r'\b(?:OR|AND|NOT)\b', ' ', cleaned, flags=re.IGNORECASE).strip()
                if cleaned:
                    fts_candidate = cleaned
                    break

    # If NOT an FTS keyword search, return empty list (NO highlighting on standard SQL queries)
    if not fts_candidate or not str(fts_candidate).strip():
        return []

    # Common stop words excluded from highlighting
    stop_words = {"the", "a", "an", "of", "in", "and", "or", "to", "for", "with", "on", "at", "by", "is", "are"}

    raw_term = str(fts_candidate).strip()
    # [Variable: List[str]]: Output list of normalized lowercase tokens and stems
    tokens: List[str] = []
    words = [
        w.lower()
        for w in "".join(c if c.isalnum() else " " for c in raw_term).split()
        if len(w) > 2 and w.lower() not in stop_words
    ]
    for w in words:
        if w not in tokens:
            tokens.append(w)
        # Add word stem for morphological variations (e.g., 'manufactur' matches 'manufacturing', 'manufacture', and 'manufacturers')
        for suffix in ("ing", "ers", "er", "ed", "es", "s", "e"):
            if w.endswith(suffix) and len(w) - len(suffix) >= 4:
                stem = w[:-len(suffix)]
                if stem not in tokens:
                    tokens.append(stem)

    return tokens


# [Project-Defined Function]: Builds compiled regex pattern matching whole words containing any search token
def get_whole_word_pattern(tokens: List[str]) -> Optional[re.Pattern]:
    """Compile regex pattern matching the entire word containing any search token."""
    if not tokens:
        return None
    # [Built-in Python: sorted]: Sort tokens by length descending so longer roots match first
    sorted_tokens = sorted(tokens, key=len, reverse=True)
    # Match entire word containing token using word boundary and word characters: \b\w*(?:token1|token2)\w*\b
    token_group = "|".join(re.escape(t) for t in sorted_tokens)
    # [Library Function: re.compile]: Case-insensitive word-level regex pattern
    return re.compile(r"\b\w*(?:" + token_group + r")\w*\b", flags=re.IGNORECASE)


# [Project-Defined Function]: Highlights search keyword tokens in explanation text (full words only)
def highlight_explanation_keywords(text: str, tokens: List[str]) -> str:
    """Wrap entire words containing search keyword tokens in HTML mark tag for prominent visibility."""
    if not tokens or not text:
        return text
    # [Project-Defined Function: get_whole_word_pattern]: Acquire whole word pattern
    pattern = get_whole_word_pattern(tokens)
    if not pattern:
        return text
    # [Library Method: Pattern.sub]: Highlight entire word with styled mark tag (never leaving letters behind)
    return pattern.sub(r'<mark class="keyword-highlight" style="background-color: #facc15 !important; color: #000000 !important; padding: 2px 6px !important; border-radius: 4px !important; font-weight: 700 !important; display: inline;">\g<0></mark>', text)


# [Project-Defined Function]: Renders styled HTML table with inline word-level keyword highlighting
def render_highlighted_table_html(df: pd.DataFrame, tokens: List[str]) -> str:
    """Render DataFrame as an HTML table with keyword highlighting applied strictly to matching words."""
    # [Project-Defined Function: get_whole_word_pattern]: Compile whole word regex
    pattern = get_whole_word_pattern(tokens)
    # [Built-in Python: list]: Column names
    cols = list(df.columns)
    # [Built-in Python: str.join]: Build table header HTML
    header_html = "".join(f"<th>{col}</th>" for col in ["#"] + cols)

    # [Variable: List[str]]: Table row strings
    html_rows: List[str] = []
    for idx, row in df.iterrows():
        cells = [f'<td class="idx-col">{idx}</td>']
        for col in cols:
            val = row[col]
            # Convert cell to clean string representation
            val_str = "" if val is None or pd.isna(val) else str(val)
            if pattern and val_str:
                # Highlight ONLY the matching word within the cell text (whole word, not entire cell background)
                val_str = pattern.sub(r'<mark class="keyword-highlight" style="background-color: #facc15 !important; color: #000000 !important; padding: 2px 6px !important; border-radius: 4px !important; font-weight: 700 !important; display: inline;">\g<0></mark>', val_str)
            cells.append(f"<td>{val_str}</td>")
        html_rows.append(f"<tr>{''.join(cells)}</tr>")

    # Assemble scrollable table container
    return f"""
    <div class="table-container">
        <table class="result-table">
            <thead>
                <tr>{header_html}</tr>
            </thead>
            <tbody>
                {''.join(html_rows)}
            </tbody>
        </table>
    </div>
    """


# [Project-Defined Function]: Renders execution status badges, natural language answer, and data table
def render_result(result: AgentResult, label: str = "", scope: str = "main"):
    """Render query execution results, explanation, metrics, and expandable SQL with unique scoped keys."""
    # Status Badge CSS class mapping
    badge_class = {
        AgentStatus.SUCCESS: "badge-success",
        AgentStatus.CLARIFICATION_REQUIRED: "badge-clarify",
        AgentStatus.VALIDATION_REJECTED: "badge-reject",
        AgentStatus.EXECUTION_FAILED: "badge-reject",
        AgentStatus.RETRY_EXHAUSTED: "badge-reject",
        AgentStatus.CONFIGURATION_ERROR: "badge-config",
    }.get(result.status, "badge-config")

    badge_label = f"[{label}] " if label else ""
    st.markdown(
        f'<span class="status-badge {badge_class}">{badge_label}Status: {result.status.value.replace("_", " ")}</span>',
        unsafe_allow_html=True,
    )

    # Explanation Card
    if result.status == AgentStatus.CLARIFICATION_REQUIRED:
        st.markdown(
            f'<div class="clarification-box">\n\n🤔 <strong>Clarification Needed:</strong><br>{result.explanation}\n\n</div>',
            unsafe_allow_html=True,
        )
    elif result.explanation:
        # Extract search tokens and highlight occurrences in natural language explanation
        search_tokens = get_search_tokens(result)
        formatted_exp = highlight_explanation_keywords(result.explanation, search_tokens)
        st.markdown(
            f'<div class="explanation-box">\n\n{formatted_exp}\n\n</div>',
            unsafe_allow_html=True,
        )

    # Metric pills
    if result.status == AgentStatus.SUCCESS:
        search_pill_html = ""
        matched_term = getattr(result, "search_term", None)
        if matched_term:
            search_pill_html = f'<div class="metric-pill keyword-pill">🔍 Highlighted Keyword: <span style="color: #fde047; font-weight: 700;">"{matched_term}"</span></div>'
        st.markdown(
            f"""
            <div class="metric-container">
                <div class="metric-pill">Rows returned: <span class="metric-val">{result.row_count}</span></div>
                <div class="metric-pill">Columns: <span class="metric-val">{len(result.columns)}</span></div>
                <div class="metric-pill">Correction retries: <span class="metric-val">{result.retry_count}</span></div>
                {search_pill_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Error message if any
    if result.error_message:
        st.error(f"**Error Details**: {result.error_message}")

    # Data Table
    if result.rows:
        # [Library Class: pandas.DataFrame]: Create DataFrame from row dictionaries
        df = pd.DataFrame(result.rows)
        # [Library Class: pandas.RangeIndex]: Shift 0-based index to start at 1 (1, 2, 3...) for human-friendly table presentation
        df.index = pd.RangeIndex(start=1, stop=len(df) + 1, name="#")

        # Extract search keywords to highlight matching cells
        search_tokens = get_search_tokens(result)

        if search_tokens:
            highlight_label = getattr(result, "search_term", None) or search_tokens[0]
            st.caption(f"✨ Matching keyword: **'{highlight_label}'** highlighted in table below.")

            # Render HTML table with word-level highlight (highlighting ONLY the matching words, not the whole cell)
            table_html = render_highlighted_table_html(df, search_tokens)
            st.markdown(table_html, unsafe_allow_html=True)
        else:
            st.dataframe(df, use_container_width=True)

        # Download CSV option with collision-free scoped key
        csv = df.to_csv(index=False).encode("utf-8")
        # [Built-in Python: abs, hash]: Generate deterministic unique key incorporating scope, label, and content hash
        dl_btn_key = f"dl_csv_{scope}_{label}_{abs(hash(result.question or ''))}_{abs(hash(result.sql_query or ''))}"
        st.download_button(
            label=f"📥 Download CSV ({len(df)} rows)",
            data=csv,
            file_name=f"{label.lower() or 'query'}_results.csv",
            mime="text/csv",
            key=dl_btn_key,
        )
    elif result.status == AgentStatus.SUCCESS and not result.rows:
        st.info("Query executed successfully, but no matching records were found in the database.")

    # Expandable Generated SQL
    if result.sql_query:
        with st.expander(f"🔍 View Generated SQL Query ({label or 'SQL'})", expanded=False):
            st.code(result.sql_query, language="sql")


# [Project-Defined Function]: Renders search interface for a specific agent (MCA or GST)
def render_agent_tab(db_type: str, title: str, subtitle: str, example_queries: list[tuple[str, str]]):
    """Render search UI for either MCA or GST agent with instant Enter submission and interactive example chips."""
    norm_type = db_type.lower().strip()
    st.markdown(f"### {title}")
    st.caption(subtitle)

    # Session state key names
    input_key = f"input_{norm_type}"
    state_key = f"{norm_type}_result"
    trigger_key = f"{norm_type}_trigger_run"
    last_query_key = f"{norm_type}_last_searched"

    # Initialize session state variables if not already initialized
    if input_key not in st.session_state:
        st.session_state[input_key] = ""
    if trigger_key not in st.session_state:
        st.session_state[trigger_key] = False
    if last_query_key not in st.session_state:
        st.session_state[last_query_key] = ""

    # Interactive example query chips
    st.markdown("##### 💡 Try an example query:")
    cols = st.columns(len(example_queries))
    for idx, (btn_label, query_text) in enumerate(example_queries):
        with cols[idx]:
            # [Library Function: streamlit.button]: Clicking instantly loads the query and triggers immediate execution
            if st.button(btn_label, use_container_width=True, key=f"ex_{norm_type}_{idx}"):
                st.session_state[input_key] = query_text
                st.session_state[trigger_key] = True
                st.rerun()

    # Search bar layout with single-line text input (submits directly on Enter!)
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        user_input = st.text_input(
            f"Ask a question to the {norm_type.upper()} database (Press Enter to search):",
            value=st.session_state[input_key],
            placeholder=f"e.g., {example_queries[0][1]}",
            key=input_key,
            label_visibility="collapsed",
        )
    with col_btn:
        search_clicked = st.button(f"🚀 Search", use_container_width=True, key=f"btn_search_{norm_type}")

    # Determine if search should run
    # Runs when:
    # 1. An example button was clicked (trigger_key is True)
    # 2. Search button was clicked and input is non-empty
    # 3. User pressed Enter with new or updated text
    should_run = False
    query_to_execute = user_input.strip()

    if st.session_state.get(trigger_key, False):
        st.session_state[trigger_key] = False
        should_run = True
    elif search_clicked and query_to_execute:
        should_run = True
    elif query_to_execute and query_to_execute != st.session_state.get(last_query_key, ""):
        should_run = True

    # Execution workflow
    if should_run and query_to_execute:
        st.session_state[last_query_key] = query_to_execute
        with st.spinner(f"Analyzing question with {norm_type.upper()} Agent, generating SQL, and executing..."):
            settings = get_settings(reload=True)
            result = run_agent(question=query_to_execute, db_type=norm_type, settings=settings)
            st.session_state[state_key] = result

    # Display result if present in session state
    if state_key in st.session_state and st.session_state[state_key] is not None:
        st.markdown("---")
        st.markdown(f"#### 📋 {norm_type.upper()} Results")
        render_result(st.session_state[state_key], label=norm_type.upper(), scope=f"{norm_type}_tab")


# [Project-Defined Function]: Main Streamlit execution lifecycle function
def main():
    """Main application loop."""
    render_sidebar()
    render_header()

    # Pre-configure example queries for MCA corporate data returning rich entity records
    mca_examples = [
        ("📍 Andhra Pradesh Companies", "List all companies registered in Andhra Pradesh with their company name, CIN, and city."),
        ("💰 Highest Authorized Capital", "Show the top 5 companies with the highest authorized capital. Display company name, CIN, and authorized capital."),
        ("👥 Directors of YRC PROJECTS", "Find all directors for 'YRC PROJECTS INDIA PRIVATE LIMITED'. Show director name, designation, and DIN."),
        ("🏢 Maharashtra Companies", "List registered companies in Maharashtra with their company name, CIN, and registration date."),
    ]

    # Pre-configure example queries for GST taxpayer data returning rich entity records
    gst_examples = [
        ("✅ Active Taxpayers", "List all active taxpayers with status 'ACT' or 'Active'. Show GSTIN, legal name, and state limit 10."),
        ("📍 Delhi Taxpayers", "Find taxpayers located in Delhi with their legal name, trade name, and GSTIN."),
        ("📈 Turnover Slab 0-40L", "Show taxpayers who have the turnover slab 'Rs. 0 to 40 lakhs' with their trade name, legal name, and state limit 10."),
        ("🔍 Lookup GSTIN 35AMMPP5720A2Z8", "Show full details for taxpayer with GSTIN '35AMMPP5720A2Z8'."),
    ]

    # Pre-configure example queries for Unified Dual Search returning records from both databases
    dual_examples = [
        ("📍 Maharashtra Entities", "Show companies and taxpayers registered in Maharashtra with their names and identification numbers."),
        ("🏛️ Andhra Pradesh Registrations", "List registered companies and taxpayers in Andhra Pradesh."),
        ("🏢 Active Business Overview", "Show active companies and taxpayers registered in 2026."),
    ]

    # Tabs for Dual-Agent Search
    tab_mca, tab_gst, tab_unified = st.tabs([
        "🏛️ MCA Corporate Agent",
        "🧾 GST Taxpayer Agent",
        "🔄 Unified Dual Search",
    ])

    # Tab 1: MCA Agent
    with tab_mca:
        render_agent_tab(
            db_type="mca",
            title="🏛️ Ministry of Corporate Affairs (MCA) Agent",
            subtitle="Search 134 companies and 300 directors, CIN, DIN, ROC, authorized capital, and corporate registrations.",
            example_queries=mca_examples,
        )

    # Tab 2: GST Agent
    with tab_gst:
        render_agent_tab(
            db_type="gst",
            title="🧾 Goods & Services Tax (GST) Agent",
            subtitle="Search 200 registered taxpayers, GSTIN, PAN, turnover slabs, trade names, and taxpayer categories.",
            example_queries=gst_examples,
        )

    # Tab 3: Unified Dual Search
    with tab_unified:
        st.markdown("### 🔄 Unified Cross-Database Search")
        st.caption("Ask a single question and search both MCA Corporate and GST Taxpayer databases in parallel.")

        dual_input_key = "unified_input"
        dual_trigger_key = "dual_trigger_run"
        dual_last_query_key = "dual_last_searched"

        if dual_input_key not in st.session_state:
            st.session_state[dual_input_key] = ""
        if dual_trigger_key not in st.session_state:
            st.session_state[dual_trigger_key] = False
        if dual_last_query_key not in st.session_state:
            st.session_state[dual_last_query_key] = ""

        # Interactive dual example chips
        st.markdown("##### 💡 Try a cross-database example query:")
        dual_cols = st.columns(len(dual_examples))
        for idx, (btn_label, query_text) in enumerate(dual_examples):
            with dual_cols[idx]:
                if st.button(btn_label, use_container_width=True, key=f"ex_dual_{idx}"):
                    st.session_state[dual_input_key] = query_text
                    st.session_state[dual_trigger_key] = True
                    st.rerun()

        # Dual search bar layout with single-line text input (submits directly on Enter!)
        dual_col_input, dual_col_btn = st.columns([5, 1])
        with dual_col_input:
            unified_query = st.text_input(
                "Enter search question to execute across both MCA and GST (Press Enter to search):",
                value=st.session_state[dual_input_key],
                placeholder="e.g., Show businesses, companies, and taxpayers in Andaman and Nicobar Islands",
                key=dual_input_key,
                label_visibility="collapsed",
            )
        with dual_col_btn:
            dual_search_clicked = st.button("🚀 Dual Search", use_container_width=True, key="btn_dual_search")

        dual_should_run = False
        dual_query_to_execute = unified_query.strip()

        if st.session_state.get(dual_trigger_key, False):
            st.session_state[dual_trigger_key] = False
            dual_should_run = True
        elif dual_search_clicked and dual_query_to_execute:
            dual_should_run = True
        elif dual_query_to_execute and dual_query_to_execute != st.session_state.get(dual_last_query_key, ""):
            dual_should_run = True

        if dual_should_run and dual_query_to_execute:
            st.session_state[dual_last_query_key] = dual_query_to_execute
            settings = get_settings(reload=True)

            with st.spinner("Executing MCA Agent..."):
                mca_res = run_mca_agent(dual_query_to_execute, settings=settings)
                st.session_state["unified_mca_res"] = mca_res

            with st.spinner("Executing GST Agent..."):
                gst_res = run_gst_agent(dual_query_to_execute, settings=settings)
                st.session_state["unified_gst_res"] = gst_res

        # Display dual search results side-by-side or stacked without overlap
        if "unified_mca_res" in st.session_state and "unified_gst_res" in st.session_state:
            st.markdown("---")

            # Layout control: Stacked View (Both Tables Visible) vs Tabbed View (Switch Tabs)
            layout_options = ("📜 Stacked View (Both Tables Visible)", "📑 Tabbed View (Switch Tabs)")
            # [Library Function: streamlit.columns]: Header and layout selector columns
            layout_header_col, layout_choice_col = st.columns([3, 2])
            with layout_header_col:
                # [Library Function: streamlit.markdown]: Results section heading
                st.markdown("### 📋 Dual Search Results")
            with layout_choice_col:
                # [Library Function: streamlit.radio]: Default to Stacked View so both tables are visible simultaneously
                dual_layout = st.radio(
                    "Layout Mode:",
                    options=layout_options,
                    index=0,
                    horizontal=True,
                    key="dual_layout_choice",
                )

            if dual_layout == "📜 Stacked View (Both Tables Visible)":
                # Stacked view: gives each table 100% of screen width sequentially with both tables visible simultaneously!
                # [Library Function: streamlit.markdown]: MCA Corporate Result section heading
                st.markdown("#### 🏛️ MCA Corporate Result")
                # [Project-Defined Function: render_result]: Render MCA results in full width
                render_result(st.session_state["unified_mca_res"], label="MCA", scope="dual_mca")

                # [Library Function: streamlit.markdown]: Horizontal rule separator
                st.markdown("---")
                # [Library Function: streamlit.markdown]: GST Taxpayer Result section heading
                st.markdown("#### 🧾 GST Taxpayer Result")
                # [Project-Defined Function: render_result]: Render GST results in full width
                render_result(st.session_state["unified_gst_res"], label="GST", scope="dual_gst")

            else:
                # Tabbed view: separates results into two dedicated full-width tabs
                # [Library Function: streamlit.tabs]: Create two dedicated sub-tabs for MCA and GST results
                res_tab_mca, res_tab_gst = st.tabs([
                    "🏛️ MCA Corporate Results",
                    "🧾 GST Taxpayer Results",
                ])

                with res_tab_mca:
                    # [Project-Defined Function: render_result]: Render MCA results within its own tab
                    render_result(st.session_state["unified_mca_res"], label="MCA", scope="dual_mca")

                with res_tab_gst:
                    # [Project-Defined Function: render_result]: Render GST results within its own tab
                    render_result(st.session_state["unified_gst_res"], label="GST", scope="dual_gst")


# [Built-in Python: __name__ check]: Standard entrypoint for script execution
if __name__ == "__main__":
    main()
