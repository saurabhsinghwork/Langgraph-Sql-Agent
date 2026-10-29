# Product Requirements Document (PRD)
## LangGraph SQL Agent

**Status:** Draft for implementation planning  
**Document owner:** Project owner  
**Version:** 1.0

## 1. Product summary

The LangGraph SQL Agent is a small learning application that lets a user ask questions in natural language about a local MySQL e-commerce database. Gemini Flash-Lite interprets each question and dynamically generates SQL through a LangGraph tool-calling workflow. The application validates the SQL, executes approved read-only queries, and presents the database results in Streamlit.

The primary goal is educational: make the agent, tool-calling, database interaction, validation, and evaluation workflow easy to inspect and explain.

## 2. Problem statement

Users who know what information they want may not know SQL. This project demonstrates how an LLM-based agent can translate a natural-language question into a database query while using explicit application and database safeguards.

## 3. Goals

- Accept natural-language questions through a Streamlit chat interface.
- Query a local MySQL e-commerce database.
- Use Gemini Flash-Lite through LangGraph tool calling.
- Generate SQL dynamically instead of relying on a fixed query-template library.
- Use documented schema information and verify it against the live database.
- Reject disallowed SQL before execution and use a read-only MySQL account.
- Attempt a bounded correction when a SQL execution error is recoverable.
- Display results as a table with a natural-language explanation.
- Show the generated SQL in an expandable section.
- Evaluate correctness with 10–20 questions and known expected results.
- Keep the implementation understandable to a beginner.

## 4. Non-goals

The initial version will not include:
- Docker or Docker Compose.
- A separate FastAPI backend.
- Multi-agent orchestration.
- Persistent agent memory or conversation context.
- Vector databases, embeddings, or RAG.
- Write operations such as INSERT, UPDATE, or DELETE through the agent.
- Production-scale authentication, multi-tenancy, or deployment infrastructure.
- A general-purpose SQL administration interface.

## 5. Intended user journey

1. The user opens the Streamlit application.
2. The user enters one question.
3. The agent processes that question independently; prior chat turns are not sent as context.
4. The agent obtains the live schema information it needs.
5. Gemini generates a SQL tool call.
6. The application validates the query and the read-only database account limits database permissions.
7. The SQL tool returns rows or a safe error.
8. If execution fails and the error is eligible for correction, the agent may retry within the configured limit. Every retry is validated again.
9. The UI displays a result table and natural-language explanation. The generated SQL is available in an expandable section.
10. The evaluation script separately checks known questions against expected results.

## 6. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Accept a natural-language question in Streamlit. | Must |
| FR-02 | Process each question without sending prior conversation turns to the agent. | Must |
| FR-03 | Use Gemini Flash-Lite as the configured LLM. | Must |
| FR-04 | Use LangGraph tool calling to orchestrate the SQL workflow. | Must |
| FR-05 | Generate SQL dynamically from the question and available schema context. | Must |
| FR-06 | Inspect the live MySQL schema and maintain separate documented schema notes. | Must |
| FR-07 | Validate SQL with a parser and restrict access to approved tables/constructs. | Must |
| FR-08 | Connect to MySQL using a dedicated read-only account. | Must |
| FR-09 | Return query rows to the agent and produce a natural-language explanation. | Must |
| FR-10 | Display result rows in a Streamlit table. | Must |
| FR-11 | Display generated SQL in an expandable section. | Must |
| FR-12 | Support bounded correction attempts for eligible SQL execution errors. | Must |
| FR-13 | Revalidate every corrected query before execution. | Must |
| FR-14 | Ask for clarification when the request is materially ambiguous. | Must |
| FR-15 | Provide safe, user-friendly errors when a query cannot be completed. | Must |
| FR-16 | Provide an evaluation set of 10–20 questions with expected results. | Must |
| FR-17 | Load secrets and local connection settings from `.env`, excluded from Git. | Must |

## 7. User experience requirements

- Keep the chat interface simple and uncluttered.
- Show results in a readable table.
- Show the generated SQL only inside an expandable section.
- Distinguish successful results from clarification requests and failures.
- Do not imply a query succeeded if execution failed.
- Do not expose credentials, stack traces, or sensitive internal connection details.

## 8. Success criteria

The project is considered complete when:
- A user can ask supported questions and see real MySQL-backed results.
- The agent can inspect the actual schema before generating SQL.
- Disallowed queries are rejected before execution.
- The database account cannot modify data.
- Correction attempts are bounded and cannot bypass validation.
- Ambiguous questions result in a clarification request rather than a silent guess.
- The evaluation set runs and reports outcomes against expected results.
- The project owner can explain the main graph, tool calls, SQL checks, and evaluation approach.

## 9. Assumptions and decisions still open

Approved: local MySQL, Python `venv`, Gemini Flash-Lite family, LangGraph tool-calling agent, Streamlit, four e-commerce tables, dynamic SQL, bounded error correction, parser plus table allowlist plus read-only account, independent questions, schema documentation plus live verification, clarification for ambiguous requests, `.env`, result table plus explanation, expandable SQL, and 10–20 evaluation questions.

Still TBD and must not be silently chosen:
- Exact Gemini model ID.
- Exact package versions.
- Exact table columns, constraints, indexes, and sample data.
- SQL correction retry count.
- Maximum returned row count.
- How clarification is represented in the request flow while keeping each question independent.
- Exact supported SQL grammar and whether joins/subqueries/CTEs are allowed.
- Evaluation comparison method and thresholds.
