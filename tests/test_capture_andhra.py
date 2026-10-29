"""Capture screenshot of Andhra Pradesh query verifying full MCA and GST data tables."""

import sys
import time
from pathlib import Path

# [Built-in Python: sys.stdout]: UTF-8 reconfiguration
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# [Library Import: playwright.sync_api]: Browser automation
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
screenshots_dir = PROJECT_ROOT / "screenshots"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 1100})
    page.goto("http://localhost:8501", timeout=60000)
    page.wait_for_selector(".header-card", timeout=30000)
    time.sleep(2)

    # Click Unified Dual Search tab
    tabs = page.locator("[data-baseweb='tab'], [role='tab']")
    tabs.filter(has_text="Unified Dual Search").first.click()
    time.sleep(1)

    # Enter query into text input and press Enter
    dual_input = page.locator("[data-testid='stTextInput'] input").nth(2)
    dual_input.click()
    dual_input.fill("Show entities in Andhra Pradesh")
    dual_input.press("Enter")
    print("Submitted search...")
    time.sleep(8)

    # Wait for MCA status badge to be visible
    page.locator(".status-badge").filter(has_text="MCA").last.wait_for(state="visible", timeout=90000)
    # [Built-in Python: time.sleep]: Wait for Streamlit rendering to complete
    time.sleep(3)

    # [Library Method: Page.evaluate]: Scroll window smoothly to bring data tables into view
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(2)

    # [Variable: int]: Count number of rendered interactive DataFrames on screen
    mca_df_count = page.locator("[data-testid='stDataFrame']").count()
    print(f"MCA tab DataFrame count: {mca_df_count}")

    # [Library Method: Page.screenshot]: Take full page screenshot of MCA result tab
    page.screenshot(path=str(screenshots_dir / "11_mca_andhra_pradesh_full_table.png"), full_page=True)
    print("Saved 11_mca_andhra_pradesh_full_table.png (full_page)")

    # Click GST tab and capture it too
    gst_tab = page.locator("[data-baseweb='tab'], [role='tab']").filter(has_text="GST Taxpayer Results")
    if gst_tab.count() > 0:
        gst_tab.first.click()
        time.sleep(2)
        gst_df_count = page.locator("[data-testid='stDataFrame']").count()
        print(f"GST tab DataFrame count: {gst_df_count}")
        page.screenshot(path=str(screenshots_dir / "12_gst_andhra_pradesh_full_table.png"), full_page=True)
        print("Saved 12_gst_andhra_pradesh_full_table.png (full_page)")

    browser.close()
