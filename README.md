# LangGraph SQL Agent - MCA Corporate & GST Taxpayer Intelligence

> A production-grade multi-agent natural language SQL system built with **LangGraph**, **Google Gemini**, and **Streamlit** for querying and cross-database analytics across Ministry of Corporate Affairs (MCA) corporate entities and Goods & Services Tax (GST) registered taxpayers.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/orchestration-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Gemini 2.0](https://img.shields.io/badge/model-Gemini--2.0--Flash--Lite-green.svg)](https://ai.google.dev/)
[![Streamlit](https://img.shields.io/badge/frontend-Streamlit-red.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Key Highlights

- **Specialized Dual Agents**:
  - **🏛️ MCA Corporate Agent**: Queries 134 registered companies and 300 directors, tracking CIN, DIN, ROC, authorized capital, paid-up capital, entity categories, and registration dates.
  - **🧾 GST Taxpayer Agent**: Queries 200 registered taxpayers, GSTIN, PAN, business constitutions, turnover slabs, trade names, and taxpayer registration statuses.
- **🔄 Unified Dual Cross-Database Search**: Parallel search that queries both MCA and GST databases simultaneously with structured overviews and interactive data tables.
- **🔍 Full-Text Search (FTS5) with Morphological Stemming**: Powered by SQLite FTS5 virtual tables (`companies_fts`, `taxpayers_fts`) with morphological root expansion (e.g., `manufacturer`, `manufacture`, `manufacturing`).
- **✨ Visual Word-Level Keyword Highlighting**: Precision word-boundary highlighting in bold amber yellow (`#facc15`) applied exclusively during FTS searches across both the natural language summary table and the interactive data grid.
- **🛡️ AST-Level SQL Security Gate**: `SQLGlot`-powered Abstract Syntax Tree validator enforcing strict read-only SELECT queries, table allowlisting, multi-statement blocking, and row clamping.
- **🔁 Self-Correcting LangGraph Workflow**: StateGraph stateful execution with live schema reflection, bounded correction retries (up to 2 retries), and ambiguity clarification detection.
- **💻 Glassmorphism Dark-Themed Web UI**: Streamlit interface with instant Enter-to-search, one-click interactive query chips, CSV export, and live SQL inspection.

---

## Repository Layout

```text
langgraph-sql-agent/
├── antigravity/               # Architecture, PRD, and implementation specifications
│   ├── ARCHITECTURE.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── PRD.md
│   ├── SPECS.md
│   └── TRD.md
├── data/                      # Sample corporate and tax datasets
│   ├── GST-Data-Sample.xlsx   # Source GST taxpayer records
│   ├── MCA-Data-Sample.xlsx   # Source MCA corporate & director records
│   ├── gst.db                 # SQLite GST database with FTS5 virtual index
│   └── mca.db                 # SQLite MCA database with FTS5 virtual index
├── src/
│   ├── agent/                 # LangGraph workflow, system prompts, and state models
│   │   ├── graph.py           # StateGraph workflow with validation & retry loops
│   │   ├── models.py          # Pydantic data contracts (AgentResult, AgentState)
│   │   └── prompts.py         # Domain system prompts for MCA and GST agents
│   ├── config/                # Environment configuration and Pydantic settings
│   │   └── settings.py
│   ├── database/              # SQLAlchemy engines, schema inspection, and seeders
│   │   ├── connection.py
│   │   ├── schema_inspector.py
│   │   └── seeder.py
│   ├── tools/                 # Tool calling implementations & FTS5 search service
│   │   └── sql_tools.py
│   ├── ui/                    # Streamlit web application & keyword highlighting
│   │   └── app.py
│   └── validation/            # SQLGlot AST validation and safety gate
│       └── validator.py
├── tests/                     # Test suite (unit, integration, and UI interactive tests)
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_tools.py
│   ├── test_ui_interactive.py
│   └── test_validation.py
├── evaluation/                # Performance evaluation benchmarks and scenarios
│   ├── eval_report.md
│   ├── evaluator.py
│   └── test_cases.py
├── requirements.txt           # Pinned production dependencies
├── pyproject.toml             # Project metadata
└── README.md                  # Project documentation
```

---

## Quick Start Guide

### 1. Prerequisites & Environment Setup

Python 3.11+ is required (Python 3.12 recommended):

```bash
# Clone the repository
git clone https://github.com/saurabhsinghwork/Langgraph-Sql-Agent.git
cd Langgraph-Sql-Agent

# Create and activate virtual environment
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)

Copy `.env.example` to `.env` and insert your Google Gemini API key:

```bash
cp .env.example .env
```

Edit `.env`:
```ini
# Google Gemini LLM API Configuration
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL_ID=gemini-2.0-flash-lite

# Database Configuration (Uses local SQLite with FTS5 by default)
USE_SQLITE_FALLBACK=true
SQLITE_MCA_PATH=data/mca.db
SQLITE_GST_PATH=data/gst.db

# Agent Execution Limits
SQL_CORRECTION_MAX_RETRIES=2
SQL_MAX_ROWS=50
SQL_QUERY_TIMEOUT_SECONDS=10
```

### 3. Launch the Application

Start the Streamlit user interface:

```bash
streamlit run src/ui/app.py
```

Open your browser at **`http://localhost:8501`**.

---

## Security Policy

The agent enforces multi-layered defense-in-depth security:
1. **AST Validation**: Every generated query is parsed with `sqlglot` before execution.
2. **Strictly Read-Only**: Only single `SELECT` statements are permitted. `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, and file operations are rejected immediately.
3. **Table Allowlisting**: Queries may only reference approved tables:
   - MCA: `companies`, `directors`, and `companies_fts`
   - GST: `taxpayers` and `taxpayers_fts`
4. **Row Clamping**: All queries are automatically capped to 50 rows maximum to prevent memory exhaustion.
5. **No Hallucination**: Schema grounding inspects live table schemas before generating SQL statements.

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.
