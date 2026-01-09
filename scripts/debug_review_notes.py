#!/usr/bin/env python3
"""
Debug script to test review_notes persistence in browser.

Run with: uv run python scripts/debug_review_notes.py
"""

import subprocess
import time
import sys
from playwright.sync_api import sync_playwright

def main():
    # Start server
    print("Starting server...")
    server = subprocess.Popen(
        ["uv", "run", "python", "mobile/run_server.py", "--port", "8090"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(5)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # Show browser
            page = browser.new_page()

            print("\n=== Step 1: Open app ===")
            page.goto("http://127.0.0.1:8090")
            page.wait_for_load_state("networkidle")
            print("App loaded")

            print("\n=== Step 2: Click first specimen ===")
            page.locator(".specimen-card").first.click()
            page.wait_for_load_state("networkidle")
            time.sleep(1)

            # Get specimen ID
            specimen_id = page.url.split("/")[-1] if "/" in page.url else "unknown"
            print(f"Opened specimen: {specimen_id}")

            print("\n=== Step 3: Check initial textarea values ===")
            # First textarea is Review Feedback, second is DwC Notes
            review_textarea = page.locator(".notes-section textarea").first
            dwc_textarea = page.locator(".notes-section textarea").nth(1)

            review_initial = review_textarea.input_value()
            dwc_initial = dwc_textarea.input_value()
            print(f"Review Feedback initial value: '{review_initial}'")
            print(f"DwC Notes initial value: '{dwc_initial}'")

            print("\n=== Step 4: Enter text in Review Feedback ===")
            test_value = f"Test review note {int(time.time())}"
            review_textarea.fill(test_value)
            print(f"Entered: '{test_value}'")

            print("\n=== Step 5: Trigger blur by clicking elsewhere ===")
            page.locator("h3").first.click()

            # Wait for toast
            try:
                toast = page.wait_for_selector(".toast", timeout=5000)
                toast_text = toast.text_content()
                print(f"Toast appeared: '{toast_text}'")
            except:
                print("WARNING: No toast appeared!")

            time.sleep(1)

            print("\n=== Step 6: Verify value still in textarea ===")
            current_value = review_textarea.input_value()
            print(f"Current value in textarea: '{current_value}'")

            print("\n=== Step 7: Navigate back to queue ===")
            page.locator("button:has-text('Back')").click()
            page.wait_for_load_state("networkidle")
            time.sleep(1)

            print("\n=== Step 8: Click same specimen again ===")
            page.locator(".specimen-card").first.click()
            page.wait_for_load_state("networkidle")
            time.sleep(1)

            print("\n=== Step 9: Check if value persisted ===")
            review_textarea = page.locator(".notes-section textarea").first
            final_value = review_textarea.input_value()
            print(f"Review Feedback after navigation: '{final_value}'")

            if final_value == test_value:
                print("\n✅ SUCCESS: Review notes persisted correctly!")
            else:
                print(f"\n❌ FAILURE: Expected '{test_value}', got '{final_value}'")

            print("\n=== Step 10: Refresh page ===")
            page.reload()
            page.wait_for_load_state("networkidle")
            page.locator(".specimen-card").first.click()
            page.wait_for_load_state("networkidle")
            time.sleep(1)

            review_textarea = page.locator(".notes-section textarea").first
            after_refresh = review_textarea.input_value()
            print(f"Review Feedback after refresh: '{after_refresh}'")

            if after_refresh == test_value:
                print("\n✅ SUCCESS: Review notes persisted after refresh!")
            else:
                print(f"\n❌ FAILURE: Expected '{test_value}', got '{after_refresh}'")

            print("\nPress Enter to close browser...")
            input()
            browser.close()

    finally:
        server.terminate()
        server.wait()
        print("Server stopped")

if __name__ == "__main__":
    main()
