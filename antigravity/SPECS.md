# Functional and Non-functional Specifications
## LangGraph SQL Agent

**Status:** Draft for implementation  
**Version:** 1.0

## 1. Scope

This specification defines the behavior expected from the initial learning version. It does not define implementation details that have not yet been approved.

## 2. Functional specifications

### FS-01: Accept a natural-language question
**Input:** A non-empty question entered in Streamlit.  
**Expected behavior:** Pass the current question to the agent as an independent request.  
**Failure behavior:** Empty input should not trigger a model call.

### FS-02: Independent request processing
**Expected behavior:** Previous chat messages may remain visible in the UI, but must not be included in the model's request context.  
**Acceptance check:** A follow-up such as “only show electronics” must not rely on an earlier question unless the user restates the needed context.

### FS-03: Schema context
**Expected behavior:** The application maintains human-readable schema documentation and retrieves the actual schema from MySQL.  
**Acceptance check:** Generated SQL must use real table and column names from the live schema.

### FS-04: Dynamic SQL generation
**Expected behavior:** Gemini generates a query for the user's question using available schema context.  
**Acceptance check:** The application does not rely solely on a predefined query-template list.

### FS-05: SQL validation
**Expected behavior:** Candidate SQL is parsed and checked against the approved query policy and table allowlist.  
**Acceptance check:** A disallowed statement or reference to an unapproved table is rejected before database execution.

### FS-06: Read-only database access
**Expected behavior:** Runtime database connections use a dedicated account without data-modification privileges.  
**Acceptance check:** Attempts to modify records fail at the database permission layer.

### FS-07: Execute validated SQL
**Expected behavior:** Only a validated query is executed. The result includes column names and bounded rows.  
**Acceptance check:** A valid query returns the matching database records.

### FS-08: Correct eligible SQL errors
**Expected behavior:** An eligible execution error can be returned to Gemini for a correction attempt, subject to a configured retry maximum.  
**Acceptance check:** Retry count is bounded, and each new query passes the full validation path again.

### FS-09: Clarify ambiguous requests
**Expected behavior:** Ask the user for clarification when the intended database operation cannot be inferred safely.  
**Acceptance check:** “Show me the best products” should not silently assume a metric if no agreed meaning exists.  
**Constraint:** Because requests are independent, clarification handling must preserve enough context explicitly for the clarified request.

### FS-10: Display successful results
**Expected behavior:** Display a result table and a natural-language explanation.  
**Acceptance check:** Table columns and rows correspond to the SQL tool output.

### FS-11: Display SQL
**Expected behavior:** Display the generated SQL inside an expandable UI section.  
**Acceptance check:** The query is visible for inspection without dominating the main chat response.

### FS-12: Safe error messages
**Expected behavior:** Display friendly messages for validation failures, exhausted retries, and database errors.  
**Acceptance check:** No API key, password, full connection string, or raw stack trace is shown to the user.

### FS-13: Evaluation dataset
**Expected behavior:** Provide 10–20 test questions with known expected outcomes.  
**Acceptance check:** Evaluation reports pass/fail outcomes using a documented comparison rule.

## 3. Non-functional specifications

### NFS-01: Understandability
Files, functions, and important logic should have clear beginner-friendly explanations and comments where they add value.

### NFS-02: Separation of concerns
UI, agent orchestration, database connectivity, SQL tools, validation, configuration, and evaluation should be separated into appropriate modules.

### NFS-03: Security
Secrets must be kept out of source control. Runtime database access must be read-only. SQL must be validated before execution.

### NFS-04: Bounded behavior
SQL retries, query runtime, and returned result size must have explicit limits. Exact retry and row-limit values remain TBD.

### NFS-05: Observability
The application should provide enough non-sensitive diagnostic information to understand whether a request was clarified, validated, executed, corrected, or failed.

### NFS-06: Correctness transparency
Successful execution must not be represented as proof of semantic correctness. The evaluation dataset should be used to assess known scenarios.

### NFS-07: Local setup
The project must run locally using Python `venv` and installed MySQL. Docker is out of scope.

## 4. Result and status model (conceptual)

The application should distinguish at least these outcomes:
- `success`: SQL executed and rows were returned (including a valid empty result).
- `clarification_required`: the user must clarify intent.
- `validation_rejected`: SQL did not pass policy checks.
- `execution_failed`: MySQL could not execute the query.
- `retry_exhausted`: eligible correction attempts were exhausted.
- `configuration_error`: required local configuration is missing or invalid.

These are conceptual statuses; final names and types can be selected during implementation without changing the required behavior.

## 5. Evaluation specification

The evaluation set should contain 10–20 independent natural-language questions covering:
- Simple filtering.
- Sorting and limiting.
- Joins across approved relationships.
- Aggregations such as counts and sums.
- Grouping and ranking.
- Empty-result questions.
- At least one ambiguous question expected to request clarification.
- At least one invalid or disallowed query scenario for safety checks.

Each case should record:
- Test ID.
- Natural-language question.
- Expected outcome/status.
- Expected rows or expected semantic result.
- Optional reference SQL for debugging.

Result comparison should account for row order only when order is part of the expected query behavior. Numeric comparisons may need a documented tolerance where appropriate.

## 6. Acceptance checklist

- [ ] App starts with valid local configuration.
- [ ] MySQL connection succeeds.
- [ ] Live schema inspection returns only required schema metadata.
- [ ] Dynamic SQL generation works for supported questions.
- [ ] Disallowed SQL is rejected before execution.
- [ ] Runtime account cannot modify database records.
- [ ] Every correction attempt is revalidated.
- [ ] Retry and row limits are enforced.
- [ ] Ambiguous questions ask for clarification.
- [ ] Results appear in a table with an explanation.
- [ ] Generated SQL appears in an expander.
- [ ] Secrets and stack traces are not exposed.
- [ ] Evaluation set runs and produces a report.
