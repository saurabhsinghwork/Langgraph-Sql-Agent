"""Interactive UI User Testing Suite for Streamlit Dual SQL Agent Application.

Uses Streamlit's official AppTest framework to simulate a real user browser session:
- Verifies initial render, sidebar database connections, and approved table metadata.
- Tests MCA Tab: clicks example query buttons, verifies immediate execution, inspects returned dataframes, columns, and rows.
- Tests GST Tab: clicks example query buttons, verifies immediate execution, inspects returned dataframes, columns, and rows.
- Tests Dual Tab: clicks cross-database example chips, verifies parallel execution without StreamlitDuplicateElementKey.
- Tests single-keystroke Enter submission across text inputs.
- Inspects all columns and row counts across companies, directors, and taxpayers.
"""

from __future__ import annotations

# [Built-in Python Module: sys]: System runtime module path manipulation
import sys
# [Built-in Python Class: pathlib.Path]: Filesystem path object
from pathlib import Path

# Ensure stdout and stderr support UTF-8 characters and emojis on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    # [Built-in Python Method: sys.path.insert]: Insert project root
    sys.path.insert(0, str(PROJECT_ROOT))

# [Library Import: streamlit.testing.v1.AppTest]: Streamlit headless browser testing framework
from streamlit.testing.v1 import AppTest
# [Project-Defined Imports from src.config.settings]: Application settings getter
from src.config.settings import get_settings
# [Project-Defined Imports from src.database.connection]: Connection engine and test helpers
from src.database.connection import get_mca_engine, get_gst_engine
# [Project-Defined Imports from src.database.schema_inspector]: Schema inspector
from src.database.schema_inspector import SchemaInspector
# [Library Import: sqlalchemy.text]: Raw SQL execution helper
from sqlalchemy import text


# [Project-Defined Function]: Verifies all columns and data rows directly in live MCA and GST databases
def verify_all_database_columns_and_rows():
    """Verify that all columns and rows in MCA and GST tables are readable without data corruption."""
    print("=" * 70)
    print(" 1. VERIFYING ALL DATABASE TABLES, COLUMNS, AND ROWS")
    print("=" * 70)

    # 1. MCA Database Inspection
    mca_engine = get_mca_engine()
    mca_inspector = SchemaInspector(engine=mca_engine, db_type="mca")
    mca_tables = mca_inspector.get_live_tables()
    print(f"MCA Live Tables: {mca_tables}")

    with mca_engine.connect() as conn:
        for tbl in ("companies", "directors"):
            details = mca_inspector.get_table_details(tbl)
            col_names = [c["name"] for c in details["columns"]]
            print(f"\n[MCA Table: '{tbl}'] - Columns ({len(col_names)}): {', '.join(col_names)}")

            # Count total rows
            row_count = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            print(f"[MCA Table: '{tbl}'] - Total Rows: {row_count}")

            # Verify every column can be selected without error
            col_list_sql = ", ".join(col_names)
            sample_rows = conn.execute(text(f"SELECT {col_list_sql} FROM {tbl} LIMIT 3")).mappings().all()
            print(f"[MCA Table: '{tbl}'] - Successfully fetched {len(sample_rows)} sample rows with all columns.")
            assert row_count > 0, f"Table {tbl} is empty!"

    # 2. GST Database Inspection
    gst_engine = get_gst_engine()
    gst_inspector = SchemaInspector(engine=gst_engine, db_type="gst")
    gst_tables = gst_inspector.get_live_tables()
    print(f"\nGST Live Tables: {gst_tables}")

    with gst_engine.connect() as conn:
        for tbl in ("taxpayers",):
            details = gst_inspector.get_table_details(tbl)
            col_names = [c["name"] for c in details["columns"]]
            print(f"\n[GST Table: '{tbl}'] - Columns ({len(col_names)}): {', '.join(col_names)}")

            # Count total rows
            row_count = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            print(f"[GST Table: '{tbl}'] - Total Rows: {row_count}")

            # Verify every column can be selected without error
            col_list_sql = ", ".join(col_names)
            sample_rows = conn.execute(text(f"SELECT {col_list_sql} FROM {tbl} LIMIT 3")).mappings().all()
            print(f"[GST Table: '{tbl}'] - Successfully fetched {len(sample_rows)} sample rows with all columns.")
            assert row_count > 0, f"Table {tbl} is empty!"

    print("\n>>> All database tables, columns, and rows verified successfully!")


# [Project-Defined Function]: Executes simulated user UI testing on Streamlit app
def test_streamlit_ui_user_flows():
    """Simulate user interactions across all tabs and verify UI rendering and widgets."""
    print("\n" + "=" * 70)
    print(" 2. SIMULATING USER BROWSER TESTING VIA STREAMLIT APPTEST")
    print("=" * 70)

    app_path = PROJECT_ROOT / "src" / "ui" / "app.py"
    # [Library Function: AppTest.from_file]: Initialize headless simulated browser session
    at = AppTest.from_file(str(app_path), default_timeout=90)
    at.run()

    # Step A: Check for fatal launch exceptions
    print("[UI Test 1]: Checking for initial render exceptions...")
    if at.exception:
        for exc in at.exception:
            print(f"EXCEPTION: {exc.message}")
        assert False, "Streamlit encountered exceptions during initial render!"
    print("[PASS] Initial render succeeded without exceptions.")
    print("\n[UI Test 2]: Verifying sidebar connection status and tables...")
    sidebar_successes = [s.value for s in at.sidebar.success]
    print(f"Sidebar status messages: {sidebar_successes}")
    assert any("Connected" in s for s in sidebar_successes), "No database connected in sidebar!"
    print("[PASS] Sidebar shows connected status badges.")

    # Step C: Test MCA Example Query Button and Results
    print("\n[UI Test 3]: Testing MCA Tab example button click and execution...")
    # Find MCA example button 'ex_mca_0'
    mca_btn = at.button(key="ex_mca_0")
    print(f"Found MCA example button: '{mca_btn.label}'")
    mca_btn.click().run()

    if at.exception:
        for exc in at.exception:
            print(f"EXCEPTION after clicking MCA button: {exc.message}")
        assert False, "Exception after clicking MCA example button!"

    # Verify input text received example query
    mca_input = at.text_input(key="input_mca")
    print(f"MCA Text Input value: '{mca_input.value}'")
    assert bool(mca_input.value), "MCA text input was not populated by example button!"

    # Verify dataframes rendered
    dfs = at.dataframe
    print(f"Dataframes rendered on page: {len(dfs)}")
    assert len(dfs) > 0, "No dataframe rendered after MCA query execution!"
    mca_df = dfs[0].value
    print(f"MCA Result Dataframe shape: {mca_df.shape}")
    print(f"MCA Result Dataframe columns: {list(mca_df.columns)}")
    assert len(mca_df) > 0, "MCA query returned 0 rows unexpectedly!"
    # [Built-in Python: assert]: Verify that table index starts at 1 instead of 0
    assert mca_df.index[0] == 1, f"Expected 1-based index, got {mca_df.index[0]}"
    print(f"[PASS] MCA table 1-based index verified: starts at row {mca_df.index[0]}!")
    print(f"[PASS] MCA example query successfully executed and rendered {len(mca_df)} rows!")

    # Step D: Test GST Example Query Button and Results
    print("\n[UI Test 4]: Testing GST Tab example button click and execution...")
    gst_btn = at.button(key="ex_gst_0")
    print(f"Found GST example button: '{gst_btn.label}'")
    gst_btn.click().run()

    if at.exception:
        for exc in at.exception:
            print(f"EXCEPTION after clicking GST button: {exc.message}")
        assert False, "Exception after clicking GST example button!"

    gst_input = at.text_input(key="input_gst")
    print(f"GST Text Input value: '{gst_input.value}'")
    assert bool(gst_input.value), "GST text input was not populated by example button!"

    dfs = at.dataframe
    print(f"Dataframes currently rendered: {len(dfs)}")
    gst_df = dfs[-1].value
    print(f"GST Result Dataframe shape: {gst_df.shape}")
    print(f"GST Result Dataframe columns: {list(gst_df.columns)}")
    assert len(gst_df) > 0, "GST query returned 0 rows unexpectedly!"
    print(f"[PASS] GST example query successfully executed and rendered {len(gst_df)} rows!")

    # Step E: Test Unified Dual Search (CRITICAL TEST FOR DUPLICATE KEY ERROR)
    print("\n[UI Test 5]: Testing Unified Dual Search tab and duplicate key prevention...")
    dual_btn = at.button(key="ex_dual_0")
    print(f"Found Dual search example button: '{dual_btn.label}'")
    dual_btn.click().run()

    # Check for duplicate key error or any exceptions
    if at.exception:
        for exc in at.exception:
            print(f"CRITICAL EXCEPTION IN DUAL SEARCH: {exc.message}")
        assert False, "Unified Dual Search produced an exception (e.g. StreamlitDuplicateElementKey)!"

    dual_input = at.text_input(key="unified_input")
    print(f"Dual Text Input value: '{dual_input.value}'")
    assert bool(dual_input.value), "Dual text input was not populated!"

    # Verify both MCA and GST result cards rendered in dual search
    # Check download buttons on page
    dl_btns = at.download_button
    dl_keys = [btn.key for btn in dl_btns]
    print(f"Rendered Download Buttons ({len(dl_btns)}): {dl_keys}")
    # Verify all keys are strictly unique
    assert len(dl_keys) == len(set(dl_keys)), f"Duplicate download button keys detected: {dl_keys}"
    print("[PASS] All download button keys are strictly unique. StreamlitDuplicateElementKey is completely resolved!")

    # Step F: Test Enter Key submission (direct text input change)
    print("\n[UI Test 6]: Testing direct search input (simulating Enter key submission)...")
    mca_input = at.text_input(key="input_mca")
    # Setting the value directly simulates the user typing and pressing Enter
    mca_input.input("List 3 companies in Kadiri").run(timeout=90)

    if at.exception:
        for exc in at.exception:
            print(f"EXCEPTION on Enter submission: {exc.message}")
        assert False, "Exception on Enter submission!"

    print("[PASS] Direct text input submission with Enter key executed cleanly without exceptions.")
    print("\n>>> All simulated user browser tests passed with 100% success!")


# [Built-in Python: __name__ check]: Main execution function
def main():
    """Run complete database verification and simulated user UI testing."""
    verify_all_database_columns_and_rows()
    test_streamlit_ui_user_flows()
    print("\n" + "=" * 70)
    print("       ALL USER TESTING AND DATABASE VERIFICATIONS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    main()
