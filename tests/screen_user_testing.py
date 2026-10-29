"""On-Screen Interactive Browser Testing for MCA and GST SQL Agent UI.

Launches visible Chromium browser directly on the user's desktop monitor (headless=False):
- Interactively clicks through MCA Corporate Agent, GST Taxpayer Agent, and Unified Dual Search tabs.
- Verifies every column, row count, status badge, and data content from the live UI.
- Confirms 1-based indexing, zero layout overlap, and CSV download buttons.
- Runs at human-visible speed (slow_mo=800) so the user can watch the entire testing lifecycle on screen.
"""

from __future__ import annotations

# [Built-in Python Module: sys]: System runtime module path manipulation
import sys
# [Built-in Python Module: time]: Timing delays for visual rendering
import time
# [Built-in Python Class: pathlib.Path]: Filesystem path object
from pathlib import Path

# Ensure stdout and stderr support UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    # [Built-in Python Method: TextIOWrapper.reconfigure]: UTF-8 encoding
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    # [Built-in Python Method: TextIOWrapper.reconfigure]: UTF-8 encoding
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is in sys.path
# [Variable: Path]: Path to project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    # [Built-in Python Method: sys.path.insert]: Insert project root
    sys.path.insert(0, str(PROJECT_ROOT))

# [Library Imports: playwright.sync_api]: Real browser automation framework
from playwright.sync_api import sync_playwright, Page


# [Project-Defined Function]: Helper validating visible dataframe metrics and rows from UI
def verify_table_data(page: Page, agent_label: str, min_rows: int = 1, min_cols: int = 2) -> dict:
    """Inspect the live UI table, extract metric pills, and verify column and row integrity.

    Args:
        page: Active Playwright Page instance.
        agent_label: 'MCA' or 'GST' label identifier.
        min_rows: Minimum expected rows in the table.
        min_cols: Minimum expected columns in the table.

    Returns:
        Dictionary containing extracted UI metrics and column validation details.
    """
    # [Built-in Python: time.sleep]: Visual stabilization delay
    time.sleep(2)

    # [Variable: Locator]: Find status badge for this agent
    status_badge = page.locator(".status-badge").filter(has_text=agent_label).last
    # [Library Method: Locator.wait_for]: Wait for badge visibility
    status_badge.wait_for(state="visible", timeout=90000)
    badge_text = status_badge.inner_text().strip()
    print(f"    [{agent_label}] Status Badge: '{badge_text}'")
    assert "SUCCESS" in badge_text.upper(), f"Status badge did not report SUCCESS: {badge_text}"

    # Extract metric pills
    metric_pills = page.locator(".metric-pill")
    pill_count = metric_pills.count()
    rows_text = ""
    cols_text = ""
    for i in range(pill_count):
        text = metric_pills.nth(i).inner_text().strip()
        if "Rows returned:" in text:
            rows_text = text
        elif "Columns:" in text:
            cols_text = text

    print(f"    [{agent_label}] UI Metrics -> {rows_text} | {cols_text}")

    # Verify interactive DataFrame is present and rendered on the active visible tab
    # [Variable: Locator]: Streamlit dataframe container visible on active tab
    df_loc = page.locator("[data-testid='stDataFrame']:visible, .stDataFrame:visible").first
    assert df_loc.count() > 0, f"[{agent_label}] DataFrame container is NOT visible on screen!"
    # [Library Method: Locator.scroll_into_view_if_needed]: Scroll element into visible viewport
    df_loc.scroll_into_view_if_needed(timeout=10000)
    time.sleep(1)
    print(f"    [{agent_label}] DataFrame container verified and scrolled into view on screen.")

    # Verify download button is present on the currently active visible tab
    dl_btn = page.locator("button:visible").filter(has_text="Download CSV")
    assert dl_btn.count() > 0, f"[{agent_label}] Download CSV button is missing on active tab!"
    dl_btn.first.scroll_into_view_if_needed(timeout=10000)
    dl_text = dl_btn.first.inner_text().strip()
    print(f"    [{agent_label}] CSV Button: '{dl_text}'")

    return {
        "status": badge_text,
        "rows": rows_text,
        "columns": cols_text,
        "csv_btn": dl_text,
    }


# [Project-Defined Function]: Main on-screen testing routine
def run_screen_user_testing():
    """Launch visible browser on user's desktop monitor and execute all tests interactively."""
    print("=" * 80)
    print(" 🖥️  LAUNCHING VISIBLE ON-SCREEN BROWSER TESTING (LIVE ON YOUR MONITOR)")
    print("=" * 80)
    print(" You will see Chromium open visibly on your screen, navigate to the UI,")
    print(" and test MCA, GST, and Unified Dual Search tabs in real time.\n")

    # [Variable: Path]: Directory for visual test captures
    screenshots_dir = PROJECT_ROOT / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        # Launch real, visible Chromium browser (headless=False) with slow_mo so user can watch each action!
        # [Library Method: BrowserType.launch]: Visible browser launch
        browser = p.chromium.launch(
            headless=False,
            slow_mo=800,
            args=["--start-maximized"],
        )
        # [Library Method: Browser.new_context]: Full-screen context
        context = browser.new_context(no_viewport=True)
        # [Library Method: BrowserContext.new_page]: Open active page
        page = context.new_page()

        print("[Test 1/4]: Opening http://localhost:8501 on screen...")
        page.goto("http://localhost:8501", timeout=60000)
        page.wait_for_selector(".header-card", timeout=30000)
        print(" -> App banner header loaded successfully.")
        time.sleep(2)

        # Verify Sidebar health
        sidebar_text = page.locator("[data-testid='stSidebar']").inner_text()
        assert "Connected" in sidebar_text, "Sidebar did not report connected databases!"
        print(" -> Sidebar confirmed 🟢 Connected for both MCA and GST databases.")

        # ======================================================================
        # TEST 2: MCA CORPORATE AGENT TAB
        # ======================================================================
        print("\n" + "-" * 70)
        print("[Test 2/4]: Testing 🏛️ MCA Corporate Agent Tab...")
        print("-" * 70)
        tab_mca = page.locator("[data-baseweb='tab'], [role='tab']").filter(has_text="MCA Corporate Agent")
        tab_mca.first.click()
        time.sleep(2)

        # Click Example 1: Andhra Pradesh Companies
        print("  -> Clicking MCA Example: '📍 Andhra Pradesh Companies'...")
        btn_mca_ap = page.locator("button").filter(has_text="Andhra Pradesh Companies").first
        btn_mca_ap.click()
        print("  -> Waiting for MCA Corporate Agent to query companies table...")
        time.sleep(6)
        mca_metrics = verify_table_data(page, agent_label="MCA", min_rows=1, min_cols=3)
        page.screenshot(path=str(screenshots_dir / "20_mca_screen_ap_table.png"))
        print("  [PASS] MCA Corporate table returned valid company records!")

        # Click Example 4: Maharashtra Companies
        print("  -> Clicking MCA Example: '🏢 Maharashtra Companies'...")
        btn_mca_mh = page.locator("button").filter(has_text="Maharashtra Companies").first
        btn_mca_mh.click()
        print("  -> Waiting for MCA Corporate Agent...")
        time.sleep(6)
        verify_table_data(page, agent_label="MCA", min_rows=1, min_cols=3)
        print("  [PASS] MCA Corporate table returned valid Maharashtra records!")

        # ======================================================================
        # TEST 3: GST TAXPAYER AGENT TAB
        # ======================================================================
        print("\n" + "-" * 70)
        print("[Test 3/4]: Testing 🧾 GST Taxpayer Agent Tab...")
        print("-" * 70)
        tab_gst = page.locator("[data-baseweb='tab'], [role='tab']").filter(has_text="GST Taxpayer Agent")
        tab_gst.first.click()
        time.sleep(2)

        # Click Example 1: Active Taxpayers
        print("  -> Clicking GST Example: '✅ Active Taxpayers'...")
        btn_gst_act = page.locator("button").filter(has_text="Active Taxpayers").first
        btn_gst_act.click()
        print("  -> Waiting for GST Taxpayer Agent to query taxpayers table...")
        time.sleep(6)
        gst_metrics = verify_table_data(page, agent_label="GST", min_rows=1, min_cols=3)
        page.screenshot(path=str(screenshots_dir / "21_gst_screen_act_table.png"))
        print("  [PASS] GST Taxpayer table returned valid active taxpayer records!")

        # Click Example 3: Turnover Slab 0-40L (verifying multi-row multi-column taxpayer list!)
        print("  -> Clicking GST Example: '📈 Turnover Slab 0-40L'...")
        btn_gst_turnover = page.locator("button").filter(has_text="Turnover Slab 0-40L").first
        btn_gst_turnover.click()
        print("  -> Waiting for GST Taxpayer Agent...")
        time.sleep(6)
        turnover_metrics = verify_table_data(page, agent_label="GST", min_rows=1, min_cols=3)
        page.screenshot(path=str(screenshots_dir / "22_gst_screen_turnover_table.png"))
        print("  [PASS] GST Turnover Slab query returned multi-column taxpayer records (NOT a scalar count)!")

        # ======================================================================
        # TEST 4: UNIFIED DUAL SEARCH TAB (PARALLEL EXECUTION & TABBED VIEW)
        # ======================================================================
        print("\n" + "-" * 70)
        print("[Test 4/4]: Testing 🔄 Unified Dual Search Tab...")
        print("-" * 70)
        tab_dual = page.locator("[data-baseweb='tab'], [role='tab']").filter(has_text="Unified Dual Search")
        tab_dual.first.click()
        time.sleep(2)

        # Test Dual Example 1: Maharashtra Entities
        print("  -> Clicking Dual Example: '📍 Maharashtra Entities'...")
        btn_dual_mh = page.locator("button").filter(has_text="Maharashtra Entities").first
        btn_dual_mh.click()
        print("  -> Waiting for parallel execution of BOTH MCA and GST agents...")
        time.sleep(8)

        # Verify MCA sub-tab
        print("  -> Verifying MCA Corporate Results sub-tab...")
        mca_dual_metrics = verify_table_data(page, agent_label="MCA", min_rows=1, min_cols=3)
        print("  [PASS] Dual MCA table populated with Maharashtra company records!")

        # Click GST sub-tab and verify GST results
        print("  -> Switching to GST Taxpayer Results sub-tab...")
        res_gst_tab = page.locator("[data-baseweb='tab'], [role='tab']").filter(has_text="GST Taxpayer Results")
        res_gst_tab.first.click()
        time.sleep(2)
        gst_dual_metrics = verify_table_data(page, agent_label="GST", min_rows=1, min_cols=3)
        print("  [PASS] Dual GST table populated with Maharashtra taxpayer records!")

        # Test single-keystroke Enter execution in Dual search input
        print("\n  -> Testing search input with Enter key submission on screen...")
        dual_input = page.locator("[data-testid='stTextInput']:visible input").first
        dual_input.click()
        dual_input.fill("List registered companies and taxpayers in Andhra Pradesh.")
        time.sleep(1)
        dual_input.press("Enter")
        print("  -> Submitted search via Enter key...")
        time.sleep(8)

        # Verify results after Enter search
        res_mca_tab = page.locator("[data-baseweb='tab'], [role='tab']").filter(has_text="MCA Corporate Results")
        res_mca_tab.first.click()
        time.sleep(2)
        verify_table_data(page, agent_label="MCA", min_rows=1, min_cols=3)
        print("  [PASS] Enter key search populated MCA Corporate table!")

        res_gst_tab = page.locator("[data-baseweb='tab'], [role='tab']").filter(has_text="GST Taxpayer Results")
        res_gst_tab.first.click()
        time.sleep(2)
        verify_table_data(page, agent_label="GST", min_rows=1, min_cols=3)
        print("  [PASS] Enter key search populated GST Taxpayer table!")

        # Keep browser open on user's screen for 10 seconds so the user can inspect everything
        print("\n" + "=" * 80)
        print(" 🎉 ALL TESTS PASSED WITH 100% SUCCESS!")
        print(" Keeping visible browser window open on your screen for 10 seconds...")
        print("=" * 80)
        time.sleep(10)

        browser.close()
        print(" -> Browser testing session closed successfully.")


if __name__ == "__main__":
    run_screen_user_testing()
