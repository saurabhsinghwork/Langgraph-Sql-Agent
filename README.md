# LangGraph SQL Agent

A production-grade natural-language interface for querying an e-commerce database using Gemini Flash-Lite and LangGraph tool calling.

## Project Status: Fully Implemented & Tested

All modules are implemented for direct use with zero placeholders, scaffolds, or dummy logic:
- **Security & Safety Gate**: AST-based parsing with SQLGlot, table allowlisting (`customers`, `products`, `orders`, `order_items`), multiple statement rejection, row clamping, and read-only enforcement.
- **LangGraph Agent**: Gemini Flash-Lite tool calling with live schema reflection, bounded error-correction retries with mandatory revalidation, ambiguity clarification handling, and strict single-turn question independence.
- **Streamlit Web UI**: Glassmorphism dark-theme interface with question submission, metric pills, interactive result tables, CSV export, expandable generated SQL, and guided clarification resolution.
- **Evaluation Suite**: 15 test cases covering filters, joins, aggregations, ambiguity, empty results, and malicious query rejections with 100% pass rate.
- **Automated Tests**: 20 unit and integration tests passing via `pytest`.

---

## Repository Layout

```text
langgraph-sql-agent/
├── antigravity/               # Product, architecture, and requirements documents
│   ├── PRD.md
│   ├── TRD.md
│   ├── SPECS.md
│   ├── ARCHITECTURE.md
│   └── IMPLEMENTATION_PLAN.md
├── src/
│   ├── agent/                 # LangGraph state graph, models, and prompts
│   │   ├── graph.py
│   │   ├── models.py
│   │   └── prompts.py
│   ├── config/                # Pydantic Settings, .env parser, secret masking
│   │   └── settings.py
│   ├── database/              # SQLAlchemy engine, schema reflection, and seeder
│   │   ├── connection.py
│   │   ├── schema_inspector.py
│   │   └── seeder.py
│   ├── tools/                 # Tool calling implementations for the agent
│   │   └── sql_tools.py
│   ├── ui/                    # Modern Streamlit web application
│   │   └── app.py
│   └── validation/            # SQLGlot AST validation engine
│       └── validator.py
├── evaluation/                # 15 scenario evaluation suite and CLI runner
│   ├── eval_report.md
│   ├── evaluator.py
│   ├── run_eval.py
│   └── test_cases.py
├── tests/                     # 20 pytest unit and integration tests
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_tools.py
│   └── test_validation.py
├── sql/                       # DDL schema, seed data, and user permissions
│   ├── create_readonly_user.sql
│   ├── schema.sql
│   └── seed_data.sql
├── docs/                      # Database schema and business rules documentation
│   └── schema.md
├── .env.example               # Template environment configuration
├── pyproject.toml             # Project metadata and dependencies
├── requirements.txt           # Pinned production requirements
└── README.md
```

---

## Quick Start Guide

### 1. Environment Setup

Create and activate a Python 3.11+ virtual environment (Python 3.12 recommended):

```bash
# Windows
py -3.12 -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)

Copy `.env.example` to `.env` and fill in your Gemini API key:

```bash
cp .env.example .env
```

Edit `.env`:
```ini
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL_ID=gemini-2.0-flash-lite

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=ecommerce_db
MYSQL_USER=readonly_agent
MYSQL_PASSWORD=AgentSecurePassword123!

SQL_CORRECTION_MAX_RETRIES=2
SQL_MAX_ROWS=50
SQL_QUERY_TIMEOUT_SECONDS=10

# Note: If local MySQL is offline, the app automatically supports local SQLite fallback.
USE_SQLITE_FALLBACK=false
```

### 3. Database Initialization

Run the automated seeder to create tables and insert sample records:

```bash
python -m src.database.seeder
```

If you are setting up local MySQL directly:
1. Run `sql/schema.sql` and `sql/seed_data.sql` using an administrative account.
2. Execute `sql/create_readonly_user.sql` to configure the read-only runtime user.

---

## Running the Application

### Launch Streamlit UI
```bash
streamlit run src/ui/app.py
```
Open your browser to the URL displayed (typically `http://localhost:8501`).

### Run Automated Unit and Integration Tests
```bash
pytest -v
```

### Run the Evaluation Suite
```bash
python -m evaluation.run_eval
```

---

## SQL Safety Policy

1. **AST-Based Parser**: Queries are parsed into an Abstract Syntax Tree using `sqlglot`.
2. **Read-Only Enforced**: Only single-statement `SELECT` (or `UNION` of selects) queries are allowed. Any `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, or `INTO OUTFILE` query is rejected before execution.
3. **Table Allowlist**: References are strictly restricted to `customers`, `products`, `orders`, and `order_items`. System catalogs (`mysql.*`, `information_schema.*`) are prohibited.
4. **Row Clamping**: Queries without a `LIMIT` clause are clamped to `SQL_MAX_ROWS` (default: 50).
5. **Defense-in-Depth**: At runtime, MySQL database accounts should be granted `SELECT` privileges only.
