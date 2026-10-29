# Technical Requirements Document (TRD)
## LangGraph SQL Agent

**Status:** Draft for implementation planning  
**Version:** 1.0

## 1. Technical overview

The application is a local Python application with a Streamlit UI, a LangGraph tool-calling agent, a SQL validation boundary, and a local MySQL database. Gemini Flash-Lite is accessed through its supported API integration.

No Docker is used. Python dependencies are installed in a local `venv`.

## 2. Proposed technology responsibilities

| Technology | Responsibility |
|---|---|
| Python | Application language |
| Streamlit | Chat input, result table, answer text, expandable SQL |
| LangGraph | Agent state and tool-call routing |
| Gemini Flash-Lite | Natural-language interpretation, SQL generation/tool selection, answer formulation |
| SQLAlchemy | Managed MySQL connectivity and query execution integration |
| MySQL Connector/Python or another compatible SQLAlchemy driver | MySQL wire-protocol driver; exact driver TBD |
| SQLGlot or another selected SQL parser | Parse and inspect generated SQL before execution; final library TBD |
| `python-dotenv` | Load local `.env` configuration |
| Evaluation script | Run known questions and compare actual outcomes with expected results |

Dependency names and versions are proposals where noted, not final package-lock decisions. Verify current compatibility before installation.

## 3. Runtime requirements

- A supported local Python version; the repository currently declares Python 3.11 or newer as a placeholder baseline.
- MySQL installed and running locally.
- A database and the four approved tables created before application use.
- A dedicated MySQL account with only the minimum SELECT permissions needed.
- A Gemini API key and a currently supported Flash-Lite model ID with required tool-calling support.
- A local `.env` file excluded from version control.
- A local Python virtual environment (`venv`).
- No Docker or container runtime requirement.

## 4. Logical components

### 4.1 Streamlit UI
Responsibilities:
- Accept a question.
- Display the answer and result table.
- Display generated SQL in an expander.
- Display clarification prompts and safe failure messages.
- Keep visible chat history separate from agent input context.

### 4.2 Agent orchestration
Responsibilities:
- Receive one independent request.
- Make the available schema/tool information available to the model.
- Use LangGraph tool-calling behavior.
- Route tool calls and tool results.
- Stop after a final response or bounded failure path.
- Support a clarification response without treating prior turns as implicit context.

### 4.3 Schema service
Responsibilities:
- Read actual database table/column metadata.
- Compare live metadata with the documented schema where useful.
- Return only relevant, safe schema details to the agent.
- Never return credentials or unrelated database metadata.

### 4.4 SQL validation
Responsibilities:
- Parse candidate SQL before execution.
- Reject multiple statements.
- Restrict statements to approved read-only query forms.
- Restrict referenced tables to `customers`, `orders`, `order_items`, and `products`.
- Reject unsupported or unsafe constructs according to the finalized SQL policy.
- Enforce a row cap and execution timeout at the appropriate layers.
- Re-run validation for every correction attempt.

A keyword check alone is insufficient. A parsed AST should be inspected. The MySQL read-only account remains an independent safeguard.

### 4.5 SQL execution tool
Responsibilities:
- Accept only validated SQL.
- Execute through SQLAlchemy against the configured MySQL database.
- Return bounded rows and column labels.
- Convert database exceptions into concise, safe error information for the agent.
- Avoid returning credentials, full connection strings, or unnecessary stack traces.

### 4.6 Evaluation
Responsibilities:
- Store 10–20 questions and expected results.
- Run the same questions through the agent.
- Compare returned data with expected results using a documented comparison rule.
- Report pass/fail and enough context to diagnose failures without leaking secrets.

## 5. Configuration

`.env` contains local settings such as:
- `GEMINI_API_KEY`
- `GEMINI_MODEL_ID`
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_DATABASE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `SQL_CORRECTION_MAX_RETRIES` (value TBD)
- `SQL_MAX_ROWS` (value TBD)

`.env.example` documents variable names without real credentials. The actual `.env` must never be committed.

Configuration should fail early with a clear message if required values are missing. Secrets must not be printed in logs or shown in the UI.

## 6. Database requirements

The selected logical entities are:
- `customers`
- `orders`
- `order_items`
- `products`

Exact columns and relationship constraints remain TBD and must be finalized before writing seed data or prompts. The design should support common beginner SQL patterns: filtering, ordering, aggregation, and joins across the approved relationships.

The application should use a dedicated read-only MySQL account. Database creation and seed-data setup should use an administrative account separately; the runtime agent account must not receive schema-modification or data-modification privileges.

## 7. SQL safety policy

Required controls:
1. Parse SQL into a structured representation.
2. Permit only the finalized read-only query grammar.
3. Reject multiple statements.
4. Check all referenced tables against the explicit allowlist.
5. Reject disallowed operations and unsafe constructs.
6. Enforce query timeout and row limits.
7. Execute only after validation succeeds.
8. Use a read-only database account as defense in depth.
9. Validate every corrected query again.
10. Return safe errors and do not expose internal secrets.

The exact treatment of CTEs, subqueries, joins, comments, functions, and schema-qualified names must be documented when the SQL policy is finalized. Do not assume every construct is allowed.

## 8. Agent and error behavior

- Every user question is independent; previous turns are not passed to the agent.
- If a request is materially ambiguous, the agent asks for clarification.
- The clarification flow must be designed so the clarified request is self-contained or explicitly combined with the original request for that one operation. It must not depend on implicit conversational memory.
- If execution fails with a correctable SQL error, the agent may attempt correction up to a configured maximum.
- Validation failures are not bypassed by retry logic.
- If retries are exhausted, return a friendly failure.
- No infinite loops.

## 9. Result contract

A successful query result should carry, at minimum:
- Generated SQL text.
- Column names.
- Bounded row data.
- Row count returned.
- A status indicating success.

A failed or clarification response should carry a distinct status and a user-safe message. Exact Python types and schema are TBD during detailed design.

The UI displays the rows in a table, a natural-language explanation, and SQL in an expander. The row cap is not yet selected.

## 10. Reliability and limitations

- LLM-generated SQL can be syntactically valid but semantically incorrect.
- A read-only query can still be expensive; use timeouts and result caps.
- SQL validation reduces risk but does not guarantee semantic correctness.
- Expected-result evaluation helps detect errors but cannot prove correctness for all possible questions.
- The agent must not claim an answer is verified merely because the query executed successfully.

## 11. Local development workflow

1. Create and activate `venv`.
2. Install the selected compatible dependencies.
3. Create the database schema and sample records using a setup/admin account.
4. Create the runtime read-only account.
5. Copy `.env.example` to `.env` and fill in local values.
6. Run the Streamlit application.
7. Run the evaluation script independently.
8. Keep `.env` and local-only artifacts out of Git.

Exact commands will be added after package versions and entry points are finalized.
