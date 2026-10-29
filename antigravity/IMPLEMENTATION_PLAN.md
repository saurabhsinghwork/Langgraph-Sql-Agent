# Implementation Plan
## LangGraph SQL Agent

**Status:** Proposed build sequence  
**Version:** 1.0

## 1. Working rules

- Do not start application logic until the repository and decisions are reviewed.
- Keep changes small and explain new concepts in beginner-friendly language.
- Explain a complete file or function before breaking down its important lines.
- Add comments that explain meaningful behavior and why it exists; avoid meaningless comments on every obvious token.
- Do not add unapproved infrastructure or features.
- No Docker.
- Keep each user question independent from previous conversation context.
- The initial repository contains documentation and a scaffold only.

## 2. Phase 0 — Review decisions and close open items

Before implementation, decide:
- Exact Gemini Flash-Lite model ID supported by the selected API.
- Compatible package versions and supported Python version.
- Exact schema columns, types, keys, constraints, and relationships.
- Seed data size and representative records.
- Exact SQL grammar allowed by the validator.
- SQL correction retry limit.
- Maximum result rows and query timeout.
- Clarification request/response behavior under independent-question mode.
- Evaluation result-comparison rules.

**Exit criteria:** No unresolved choice blocks the first implementation step.

## 3. Phase 1 — Repository and local environment

Tasks:
1. Review the repository structure and documentation.
2. Create a Python `venv`.
3. Select and install compatible dependencies.
4. Copy `.env.example` to `.env` and configure local values.
5. Confirm `.env` is ignored by Git.
6. Add a minimal configuration loader and clear missing-setting errors.

**Exit criteria:** Python environment is isolated and configuration can be loaded without printing secrets.

## 4. Phase 2 — MySQL schema and credentials

Tasks:
1. Define the four selected tables: `customers`, `orders`, `order_items`, and `products`.
2. Decide columns and relationships.
3. Write a setup SQL file for schema creation and sample data.
4. Create a dedicated read-only runtime account.
5. Verify the runtime account can read the required tables but cannot modify records.
6. Document local setup steps.

**Exit criteria:** Sample data exists and read-only permissions have been verified.

## 5. Phase 3 — Database connectivity and schema inspection

Tasks:
1. Create the SQLAlchemy engine from local configuration.
2. Add a simple connection check.
3. Implement live table/column inspection.
4. Compare live schema metadata with the documented schema where useful.
5. Ensure schema output excludes credentials and unrelated metadata.

**Exit criteria:** Python can connect to MySQL and return the actual approved schema.

## 6. Phase 4 — SQL validation and execution tools

Tasks:
1. Select and configure the SQL parser.
2. Define the supported read-only SQL grammar.
3. Implement multiple-statement rejection.
4. Implement table allowlisting.
5. Define handling for joins, subqueries, CTEs, functions, comments, and qualified names.
6. Enforce query timeout and row cap.
7. Implement validated query execution.
8. Return column names, bounded rows, and safe error messages.
9. Verify every rejected query is stopped before execution.

**Exit criteria:** Allowed read queries work; disallowed queries are rejected; runtime database permissions are read-only.

## 7. Phase 5 — LangGraph agent and Gemini tool calling

Tasks:
1. Configure the selected Gemini Flash-Lite model ID.
2. Define the request state for a single question.
3. Register the schema-inspection and read-only SQL tools.
4. Configure the LangGraph tool-calling agent.
5. Write concise model instructions for schema-grounded SQL generation.
6. Route tool calls and tool results through the agent loop.
7. Implement bounded correction attempts for eligible execution errors.
8. Ensure every corrected query goes through validation.
9. Implement clarification outcomes for ambiguous questions.
10. Ensure previous user turns are not included in the model context.

**Exit criteria:** A single question can result in a validated query, a result, and a grounded explanation—or a clarification/safe failure.

## 8. Phase 6 — Streamlit interface

Tasks:
1. Add a question input and submit behavior.
2. Display the current request's natural-language answer.
3. Display returned rows in a table.
4. Put generated SQL inside an expander.
5. Display clarification requests and failures distinctly.
6. Keep the visible transcript separate from agent context.
7. Avoid displaying secrets, raw stack traces, or sensitive connection details.

**Exit criteria:** The app supports the approved user journey locally.

## 9. Phase 7 — Accuracy evaluation

Tasks:
1. Create 10–20 questions with expected outcomes.
2. Cover filtering, sorting, joins, aggregations, empty results, ambiguity, and safety rejections.
3. Add a runner that executes each question independently.
4. Compare actual results against expected results using the agreed comparison rules.
5. Report per-case outcomes and aggregate pass/fail counts.
6. Investigate SQL-generation, execution, and answer-explanation errors separately.

**Exit criteria:** The evaluation suite runs and produces a readable report.

## 10. Phase 8 — Documentation and handoff

Tasks:
1. Add setup and run commands to the README.
2. Explain each module and the agent/tool loop.
3. Document configuration variables without real secrets.
4. Document the SQL safety policy and its limitations.
5. Document evaluation results and known limitations.
6. Confirm no Docker or unapproved infrastructure was added.

**Exit criteria:** Another beginner can set up the project and explain its core flow from the documentation.

## 11. Manual verification scenarios

- Simple filter: customers from a selected city.
- Join: customers and their orders.
- Aggregation: total quantity sold per product.
- Ranking: top products by revenue, using a clearly defined revenue rule.
- Empty result: a filter with no matching records.
- Invalid column: correction flow may recover within the configured retry count.
- Disallowed table: query rejected before execution.
- Write statement: query rejected and runtime database account also lacks permission.
- Ambiguous request: clarification is requested.
- Independent question: previous visible chat content does not affect the next answer.
- Large result: row cap is enforced.
- Missing configuration: clear error without leaking secrets.
- Evaluation run: expected results are compared and reported.

## 12. Definition of done

The project meets the agreed product requirements, passes the manual verification scenarios, runs the 10–20-case evaluation set, and includes the five project documents in `antigravity/`. Any deviation from the agreed scope must be discussed and approved before implementation.
