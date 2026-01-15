"""
End-to-end test for review notes persistence using Playwright.

This tests the actual browser behavior to verify review_notes save and load correctly.
"""

import subprocess
import time
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

# Test data directory
PROJECT_ROOT = Path(__file__).parent.parent
STATE_FILE = PROJECT_ROOT / "data" / "review_state.json"


@pytest.fixture(scope="module")
def server():
    """Start the local server for testing."""
    # Start server in background
    proc = subprocess.Popen(
        ["uv", "run", "python", "mobile/run_server.py", "--port", "8081"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start
    time.sleep(3)

    yield "http://127.0.0.1:8081"

    # Cleanup
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture
def clean_state():
    """Backup and restore review state for clean tests."""
    backup = None
    if STATE_FILE.exists():
        backup = STATE_FILE.read_text()

    yield

    # Restore original state
    if backup:
        STATE_FILE.write_text(backup)
    elif STATE_FILE.exists():
        STATE_FILE.unlink()


class TestReviewNotesE2E:
    """End-to-end tests for review notes functionality."""

    def test_review_notes_save_and_display(self, server: str, page: Page, clean_state):
        """
        Test that review_notes can be saved and are displayed after page reload.

        This is the exact user flow that was reported as broken:
        1. Open a specimen
        2. Enter text in Review Feedback textarea
        3. Click away (blur) to trigger save
        4. Refresh page
        5. Verify text is still there
        """
        # Open the app
        page.goto(server)
        page.wait_for_load_state("networkidle")

        # Click on first specimen in queue
        page.locator(".specimen-card").first.click()
        page.wait_for_load_state("networkidle")

        # Find the Review Feedback textarea
        review_textarea = page.locator("textarea").first  # First textarea is review_notes

        # Get the specimen ID from the current URL or page content
        specimen_id = page.url.split("/")[-1] if "/" in page.url else None

        # Clear and enter test text
        test_text = f"E2E test note - {time.time()}"
        review_textarea.fill(test_text)

        # Trigger blur by clicking elsewhere
        page.locator("h3").first.click()

        # Wait for save toast
        page.wait_for_selector(".toast", timeout=5000)

        # Refresh the page
        page.reload()
        page.wait_for_load_state("networkidle")

        # The page should redirect to queue, click the same specimen
        page.locator(".specimen-card").first.click()
        page.wait_for_load_state("networkidle")

        # Verify the review notes textarea contains our text
        review_textarea = page.locator("textarea").first
        expect(review_textarea).to_have_value(test_text)

    def test_dwc_notes_save_and_display(self, server: str, page: Page, clean_state):
        """Test that DwC notes save and display correctly."""
        page.goto(server)
        page.wait_for_load_state("networkidle")

        # Click on first specimen
        page.locator(".specimen-card").first.click()
        page.wait_for_load_state("networkidle")

        # Find the DwC Notes textarea (second textarea)
        dwc_textarea = page.locator("textarea").nth(1)

        # Enter test text
        test_text = f"DwC note test - {time.time()}"
        dwc_textarea.fill(test_text)

        # Trigger blur
        page.locator("h3").first.click()

        # Wait for save
        page.wait_for_selector(".toast", timeout=5000)

        # Refresh and verify
        page.reload()
        page.wait_for_load_state("networkidle")
        page.locator(".specimen-card").first.click()
        page.wait_for_load_state("networkidle")

        dwc_textarea = page.locator("textarea").nth(1)
        expect(dwc_textarea).to_have_value(test_text)

    def test_both_notes_persist_independently(self, server: str, page: Page, clean_state):
        """Test that review_notes and notes can be set independently."""
        page.goto(server)
        page.wait_for_load_state("networkidle")

        page.locator(".specimen-card").first.click()
        page.wait_for_load_state("networkidle")

        review_text = f"Review feedback - {time.time()}"
        dwc_text = f"DwC canonical - {time.time()}"

        # Set review notes
        review_textarea = page.locator("textarea").first
        review_textarea.fill(review_text)
        page.locator("h3").first.click()
        page.wait_for_selector(".toast", timeout=5000)

        # Set DwC notes
        dwc_textarea = page.locator("textarea").nth(1)
        dwc_textarea.fill(dwc_text)
        page.locator("h3").first.click()
        page.wait_for_selector(".toast", timeout=5000)

        # Refresh and verify both
        page.reload()
        page.wait_for_load_state("networkidle")
        page.locator(".specimen-card").first.click()
        page.wait_for_load_state("networkidle")

        expect(page.locator("textarea").first).to_have_value(review_text)
        expect(page.locator("textarea").nth(1)).to_have_value(dwc_text)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--headed"])
