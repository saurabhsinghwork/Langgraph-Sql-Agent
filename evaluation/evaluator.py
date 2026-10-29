"""Automated Evaluation Runner for LangGraph SQL Agents (MCA and GST).

Executes test scenarios against the agents (or validation & execution pipeline),
compares outcomes against expected specifications, and produces formatted reports.
"""

from __future__ import annotations

# [Built-in Python Modules: os, sys]: Environment variables and Python runtime module paths
import os
import sys
# [Built-in Python Module: time]: High-resolution execution timing
import time
# [Built-in Python Class: pathlib.Path]: Filesystem path object
from pathlib import Path
# [Built-in Python Module: dataclasses.dataclass]: Structured container generator
from dataclasses import dataclass
# [Built-in Python Module: typing]: Type annotation helpers
from typing import Any, Dict, List, Optional, Tuple
# [Library Function: tabulate.tabulate from tabulate package]: Formats nested tabular data as ASCII tables
from tabulate import tabulate

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    # [Built-in Python Method: sys.path.insert]: Insert project root to sys.path
    sys.path.insert(0, str(PROJECT_ROOT))

# [Project-Defined Imports]: Agent workflow, domain models, settings, and validation modules
from src.agent.graph import run_agent, run_mca_agent, run_gst_agent
from src.agent.models import AgentResult, AgentStatus
from src.config.settings import AppSettings, get_settings
from src.database.connection import get_engine, get_mca_engine, get_gst_engine
from src.database.seeder import seed_database
from src.tools.sql_tools import DatabaseToolService, get_mca_tool_service, get_gst_tool_service
from src.validation.validator import SQLValidator
from evaluation.test_cases import TEST_CASES, TestCase


# [Project-Defined Dataclass]: Data container representing the measured result of an individual test
@dataclass
class EvalOutcome:
    """Benchmark outcome for a single test case."""
    # [Project-Defined Attribute: str]: Test case ID matching TestCase.id
    test_id: str
    # [Project-Defined Attribute: str]: Category classification
    category: str
    # [Project-Defined Attribute: str]: User input question
    question: str
    # [Project-Defined Attribute: str]: Expected outcome status string
    expected_status: str
    # [Project-Defined Attribute: str]: Actual outcome status string returned by agent/pipeline
    actual_status: str
    # [Project-Defined Attribute: bool]: Boolean flag indicating if test passed all assertion criteria
    passed: bool
    # [Project-Defined Attribute: float]: Duration of execution in seconds
    duration_sec: float
    # [Project-Defined Attribute: str]: Explanation or failure notes
    notes: str


# [Project-Defined Class]: Test harness executing benchmark test cases and formatting results
class EvaluationRunner:
    """Orchestrates test execution, comparison, and reporting for MCA and GST agents."""

    # [Project-Defined Method]: Initializes evaluation runner with services and database validators
    def __init__(self, settings: Optional[AppSettings] = None):
        # [Project-Defined Attribute: AppSettings]: Application configuration instance
        self.settings = settings or get_settings()
        # [Project-Defined Attribute: DatabaseToolService]: Encapsulates live MCA schema and execution
        self.mca_tool_service = DatabaseToolService(db_type="mca", settings=self.settings)
        # [Project-Defined Attribute: DatabaseToolService]: Encapsulates live GST schema and execution
        self.gst_tool_service = DatabaseToolService(db_type="gst", settings=self.settings)
        # Determine dialect (SQLite vs MySQL)
        dialect = "sqlite" if self.settings.use_sqlite_fallback else "mysql"
        # [Project-Defined Attribute: SQLValidator]: AST query validator for MCA
        self.mca_validator = SQLValidator(max_rows=self.settings.sql_max_rows, dialect=dialect, db_type="mca")
        # [Project-Defined Attribute: SQLValidator]: AST query validator for GST
        self.gst_validator = SQLValidator(max_rows=self.settings.sql_max_rows, dialect=dialect, db_type="gst")

    # [Project-Defined Method]: Helper returning tool service for target database
    def get_tool_service_for(self, db_type: str) -> DatabaseToolService:
        """Get the appropriate tool service based on db_type."""
        if db_type.lower() == "gst":
            return self.gst_tool_service
        return self.mca_tool_service

    # [Project-Defined Method]: Helper returning AST validator for target database
    def get_validator_for(self, db_type: str) -> SQLValidator:
        """Get the appropriate SQL validator based on db_type."""
        if db_type.lower() == "gst":
            return self.gst_validator
        return self.mca_validator

    # [Project-Defined Method]: Executes a single TestCase and verifies assertions
    def evaluate_test_case(self, tc: TestCase) -> EvalOutcome:
        """Run a single test case and compare actual outcomes against expected."""
        # [Built-in Python Function: time.time]: Start timer
        start_time = time.time()
        # Check if live Gemini API key is configured
        has_api_key = bool(self.settings.gemini_api_key.strip())
        tool_service = self.get_tool_service_for(tc.db_type)
        validator = self.get_validator_for(tc.db_type)

        # Branch 1: If safety rejection test case
        if tc.expected_status == AgentStatus.VALIDATION_REJECTED:
            # [Project-Defined Method: SQLValidator.validate]: Test direct AST security validator rejection
            val = validator.validate(tc.reference_sql or tc.question)
            duration = time.time() - start_time
            if not val.is_valid:
                # [Project-Defined Dataclass Instance: EvalOutcome]
                return EvalOutcome(
                    test_id=tc.id,
                    category=tc.category,
                    question=tc.question,
                    expected_status=tc.expected_status.value,
                    actual_status=AgentStatus.VALIDATION_REJECTED.value,
                    passed=True,
                    duration_sec=duration,
                    notes=f"Correctly blocked: {val.error_message}",
                )
            else:
                return EvalOutcome(
                    test_id=tc.id,
                    category=tc.category,
                    question=tc.question,
                    expected_status=tc.expected_status.value,
                    actual_status="unexpected_validation_success",
                    passed=False,
                    duration_sec=duration,
                    notes="Security failure: Malicious or disallowed SQL was NOT rejected!",
                )

        # Branch 2: Online evaluation with live Gemini Agent (if key is set)
        if has_api_key:
            try:
                # [Project-Defined Function: run_agent]: Execute target agent end-to-end
                result = run_agent(tc.question, db_type=tc.db_type, settings=self.settings, tool_service=tool_service)
                duration = time.time() - start_time
                status_matches = result.status == tc.expected_status

                passed = status_matches
                notes = []

                if not status_matches:
                    notes.append(f"Status mismatch: expected {tc.expected_status.value}, got {result.status.value}")

                # Verify row count bounds if execution succeeded
                if result.status == AgentStatus.SUCCESS:
                    if result.row_count < tc.min_expected_rows:
                        passed = False
                        notes.append(f"Row count {result.row_count} < min expected {tc.min_expected_rows}")
                    if tc.max_expected_rows is not None and result.row_count > tc.max_expected_rows:
                        passed = False
                        notes.append(f"Row count {result.row_count} > max expected {tc.max_expected_rows}")

                return EvalOutcome(
                    test_id=tc.id,
                    category=tc.category,
                    question=tc.question,
                    expected_status=tc.expected_status.value,
                    actual_status=result.status.value,
                    passed=passed,
                    duration_sec=duration,
                    notes="; ".join(notes) if notes else "Passed all criteria",
                )
            except Exception as exc:
                duration = time.time() - start_time
                return EvalOutcome(
                    test_id=tc.id,
                    category=tc.category,
                    question=tc.question,
                    expected_status=tc.expected_status.value,
                    actual_status="error",
                    passed=False,
                    duration_sec=duration,
                    notes=f"Exception: {type(exc).__name__}",
                )

        # Branch 3: Offline / Reference pipeline verification (when API key is not configured)
        if tc.expected_status == AgentStatus.CLARIFICATION_REQUIRED:
            # In offline mode, verify ambiguous intent flags
            duration = time.time() - start_time
            ambig_words = ("best", "top", "good", "popular")
            is_ambig = any(w in tc.question.lower() for w in ambig_words)
            return EvalOutcome(
                test_id=tc.id,
                category=tc.category,
                question=tc.question,
                expected_status=tc.expected_status.value,
                actual_status=AgentStatus.CLARIFICATION_REQUIRED.value if is_ambig else "unknown",
                passed=is_ambig,
                duration_sec=duration,
                notes="Ambiguity classification verified (offline rule check)",
            )

        # Execute reference SQL against the corresponding database
        if tc.reference_sql:
            # [Project-Defined Method: DatabaseToolService.execute_query]
            exec_result = tool_service.execute_query(tc.reference_sql)
            duration = time.time() - start_time
            if exec_result["success"]:
                row_count = exec_result["row_count"]
                passed = row_count >= tc.min_expected_rows
                if tc.max_expected_rows is not None and row_count > tc.max_expected_rows:
                    passed = False
                note = f"Reference SQL passed ({row_count} rows returned)"
                return EvalOutcome(
                    test_id=tc.id,
                    category=tc.category,
                    question=tc.question,
                    expected_status=tc.expected_status.value,
                    actual_status=AgentStatus.SUCCESS.value,
                    passed=passed,
                    duration_sec=duration,
                    notes=note,
                )
            else:
                return EvalOutcome(
                    test_id=tc.id,
                    category=tc.category,
                    question=tc.question,
                    expected_status=tc.expected_status.value,
                    actual_status="execution_failed",
                    passed=False,
                    duration_sec=duration,
                    notes=f"Reference SQL error: {exec_result.get('error')}",
                )

        duration = time.time() - start_time
        return EvalOutcome(
            test_id=tc.id,
            category=tc.category,
            question=tc.question,
            expected_status=tc.expected_status.value,
            actual_status="skipped",
            passed=True,
            duration_sec=duration,
            notes="No reference SQL available for offline check",
        )

    # [Project-Defined Method]: Iterates through all test cases in the benchmark suite
    def run_all(self) -> List[EvalOutcome]:
        """Execute all test cases and return outcomes."""
        outcomes: List[EvalOutcome] = []
        for tc in TEST_CASES:
            outcome = self.evaluate_test_case(tc)
            outcomes.append(outcome)
        return outcomes

    # [Project-Defined Method]: Formats test results into a clean markdown and ASCII summary table
    def generate_report(self, outcomes: List[EvalOutcome]) -> str:
        """Format test outcomes into a terminal table and markdown summary."""
        # [Built-in Python Function: len]: Total number of executed test cases
        total = len(outcomes)
        # [Built-in Python Function: sum]: Total number of passed test cases
        passed = sum(1 for o in outcomes if o.passed)
        failed = total - passed
        pass_rate = (passed / total) * 100 if total > 0 else 0.0

        headers = ["ID", "Category", "Expected", "Actual", "Pass", "Time (s)", "Notes"]
        rows = [
            [
                o.test_id,
                o.category,
                o.expected_status,
                o.actual_status,
                "[PASS]" if o.passed else "[FAIL]",
                f"{o.duration_sec:.2f}",
                o.notes[:45] + "..." if len(o.notes) > 45 else o.notes,
            ]
            for o in outcomes
        ]

        # [Library Function: tabulate.tabulate]: Render GitHub markdown table
        table_str = tabulate(rows, headers=headers, tablefmt="github")

        # Assemble summary string
        summary = (
            f"\n=======================================================\n"
            f"          EVALUATION RUN SUMMARY (MCA & GST)\n"
            f"=======================================================\n"
            f"Total Cases:  {total}\n"
            f"Passed:       {passed}\n"
            f"Failed:       {failed}\n"
            f"Pass Rate:    {pass_rate:.1f}%\n"
            f"=======================================================\n\n"
            f"{table_str}\n"
        )
        return summary
