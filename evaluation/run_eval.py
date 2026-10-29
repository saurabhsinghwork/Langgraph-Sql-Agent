"""CLI entry point to execute evaluation tests for MCA and GST agents."""

from __future__ import annotations

# [Built-in Python Module: sys]: System-specific parameters and exit status control
import sys
# [Built-in Python Class: pathlib.Path]: Filesystem path object
from pathlib import Path

# Ensure project root is in sys.path
# [Variable: Path]: Path to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    # [Built-in Python Method: sys.path.insert]: Insert project root
    sys.path.insert(0, str(PROJECT_ROOT))

# [Project-Defined Import from evaluation.evaluator]: Evaluation harness runner
from evaluation.evaluator import EvaluationRunner
# [Project-Defined Imports from src.database.connection]: Connection engine and health testers
from src.database.connection import get_engine, test_connection, test_all_connections
# [Project-Defined Import from src.database.seeder]: Database schema seeder
from src.database.seeder import seed_database
# [Project-Defined Import from src.config.settings]: AppSettings getter
from src.config.settings import get_settings


# [Project-Defined Function]: CLI runner orchestrating pre-flight checks, seeding, test execution, and reporting
def main():
    """Execute evaluation benchmark across 15 real-world scenarios for MCA and GST."""
    print("=" * 60)
    print("      LangGraph SQL Agents - Evaluation Suite (MCA & GST)")
    print("=" * 60)

    # [Project-Defined Function: get_settings]: Load configuration
    settings = get_settings()
    # [Project-Defined Function: test_all_connections]: Test connectivity to both MCA and GST databases
    conn_statuses = test_all_connections(settings)
    for db_type, (is_conn, conn_msg) in conn_statuses.items():
        print(f"[{db_type.upper()} Database Status]: {conn_msg}")

    # Fall back to SQLite if MySQL is offline
    all_connected = all(status[0] for status in conn_statuses.values())
    if not all_connected and not settings.use_sqlite_fallback:
        print("[NOTICE]: Local MySQL server is not currently reachable. Enabling local database fallback for evaluation run...")
        settings.use_sqlite_fallback = True

    # Ensure database is seeded before running evaluations
    print("Verifying database schema and seeding for MCA and GST...")
    # [Project-Defined Function: seed_database]: Verify or seed all tables
    seed_ok, seed_msg = seed_database(settings=settings, target="all")
    print(f"Database setup: {seed_msg}\n")

    # [Project-Defined Class Instance: EvaluationRunner]: Instantiate benchmark runner
    runner = EvaluationRunner(settings=settings)
    print("Running evaluation suite across 15 scenarios (MCA & GST)...")
    # [Project-Defined Method: EvaluationRunner.run_all]: Execute all 15 test cases
    outcomes = runner.run_all()
    # [Project-Defined Method: EvaluationRunner.generate_report]: Format results table
    report = runner.generate_report(outcomes)
    print(report)

    # Save report to evaluation/eval_report.md
    report_file = PROJECT_ROOT / "evaluation" / "eval_report.md"
    # [Built-in Python Method: Path.write_text]: Write markdown report to disk
    report_file.write_text(report, encoding="utf-8")
    print(f"Report saved to: {report_file}")

    # [Built-in Python: all()]: Check if every test case passed
    all_passed = all(o.passed for o in outcomes)
    # [Built-in Python Function: sys.exit]: Return exit code 0 for success, 1 for failure
    sys.exit(0 if all_passed else 1)


# [Built-in Python: __name__ check]: Standard CLI entrypoint
if __name__ == "__main__":
    main()
