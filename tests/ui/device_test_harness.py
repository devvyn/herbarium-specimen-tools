"""
Device Testing Harness for Herbarium Review UI

Automated UI/UX testing across simulated mobile devices.
Captures screenshots, measures interactions, reports findings.

Usage:
    uv run python tests/ui/device_test_harness.py [--headed] [--report]

Findings are written to tests/ui/findings/ for knowledge sharing.
"""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Literal

from playwright.sync_api import sync_playwright, Page, Browser

# Common mobile device configurations
DEVICES = {
    "iphone_14": {
        "name": "iPhone 14",
        "viewport": {"width": 390, "height": 844},
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        "device_scale_factor": 3,
        "is_mobile": True,
        "has_touch": True,
    },
    "iphone_se": {
        "name": "iPhone SE",
        "viewport": {"width": 375, "height": 667},
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        "device_scale_factor": 2,
        "is_mobile": True,
        "has_touch": True,
    },
    "pixel_7": {
        "name": "Pixel 7",
        "viewport": {"width": 412, "height": 915},
        "user_agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36",
        "device_scale_factor": 2.625,
        "is_mobile": True,
        "has_touch": True,
    },
    "ipad_mini": {
        "name": "iPad Mini",
        "viewport": {"width": 768, "height": 1024},
        "user_agent": "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        "device_scale_factor": 2,
        "is_mobile": True,
        "has_touch": True,
    },
    "desktop": {
        "name": "Desktop Chrome",
        "viewport": {"width": 1280, "height": 800},
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False,
    },
}


@dataclass
class Finding:
    """A discovered UI/UX issue or observation."""
    severity: Literal["critical", "warning", "info"]
    category: str  # layout, interaction, performance, accessibility
    device: str
    description: str
    screenshot: str | None = None
    selector: str | None = None
    recommendation: str | None = None


@dataclass
class TestResult:
    """Result of a single test flow."""
    device: str
    flow: str
    passed: bool
    duration_ms: int
    findings: list[Finding] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)


@dataclass
class TestReport:
    """Complete test report across all devices."""
    timestamp: str
    base_url: str
    devices_tested: list[str]
    results: list[TestResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def add_result(self, result: TestResult):
        self.results.append(result)

    def generate_summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        findings_by_severity = {"critical": 0, "warning": 0, "info": 0}

        for result in self.results:
            for finding in result.findings:
                findings_by_severity[finding.severity] += 1

        self.summary = {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": f"{passed/total*100:.1f}%" if total > 0 else "N/A",
            "findings": findings_by_severity,
        }


class DeviceTestHarness:
    """Runs UI tests across multiple device configurations."""

    def __init__(self, base_url: str = "http://localhost:8080", headed: bool = False):
        self.base_url = base_url
        self.headed = headed
        self.output_dir = Path(__file__).parent / "findings"
        self.output_dir.mkdir(exist_ok=True)
        self.screenshots_dir = self.output_dir / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)

    def run_all_devices(self, devices: list[str] | None = None) -> TestReport:
        """Run test suite on specified devices (or all)."""
        devices = devices or list(DEVICES.keys())

        report = TestReport(
            timestamp=datetime.now().isoformat(),
            base_url=self.base_url,
            devices_tested=devices,
        )

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not self.headed)

            for device_id in devices:
                device = DEVICES[device_id]
                print(f"\n{'='*60}")
                print(f"Testing: {device['name']}")
                print(f"{'='*60}")

                context = browser.new_context(
                    viewport=device["viewport"],
                    user_agent=device["user_agent"],
                    device_scale_factor=device["device_scale_factor"],
                    is_mobile=device["is_mobile"],
                    has_touch=device["has_touch"],
                )
                page = context.new_page()

                # Run test flows
                report.add_result(self._test_login_flow(page, device_id))
                report.add_result(self._test_queue_view(page, device_id))
                report.add_result(self._test_specimen_detail(page, device_id))
                report.add_result(self._test_touch_interactions(page, device_id))

                context.close()

            browser.close()

        report.generate_summary()
        self._save_report(report)
        return report

    def _screenshot(self, page: Page, device_id: str, name: str) -> str:
        """Take screenshot and return path."""
        filename = f"{device_id}_{name}_{int(time.time())}.png"
        path = self.screenshots_dir / filename
        page.screenshot(path=str(path))
        return str(path)

    def _test_login_flow(self, page: Page, device_id: str) -> TestResult:
        """Test the login/name entry flow."""
        start = time.time()
        findings = []
        screenshots = []
        passed = True

        try:
            # Clear state and load
            page.goto(self.base_url)
            page.evaluate("localStorage.clear()")
            page.reload()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(500)

            screenshots.append(self._screenshot(page, device_id, "login_screen"))

            # Check login form visibility
            username_input = page.query_selector("#login-username")
            if not username_input:
                findings.append(Finding(
                    severity="critical",
                    category="layout",
                    device=device_id,
                    description="Login username input not found",
                    recommendation="Check if login form renders correctly",
                ))
                passed = False
            else:
                # Check if input is visible and usable
                box = username_input.bounding_box()
                if box:
                    if box["width"] < 200:
                        findings.append(Finding(
                            severity="warning",
                            category="layout",
                            device=device_id,
                            description=f"Username input narrow ({box['width']}px)",
                            recommendation="Input should be at least 200px on mobile",
                        ))

                    # Test input interaction
                    username_input.fill("TestUser")

                    # Find and click submit
                    submit_btn = page.query_selector("button[type='submit']")
                    if submit_btn:
                        submit_btn.click()
                        page.wait_for_timeout(2000)

                        # Verify login succeeded
                        if page.query_selector(".specimen-card"):
                            findings.append(Finding(
                                severity="info",
                                category="interaction",
                                device=device_id,
                                description="Login flow completed successfully",
                            ))
                        else:
                            findings.append(Finding(
                                severity="warning",
                                category="interaction",
                                device=device_id,
                                description="Queue not visible after login",
                            ))

            screenshots.append(self._screenshot(page, device_id, "after_login"))

        except Exception as e:
            findings.append(Finding(
                severity="critical",
                category="interaction",
                device=device_id,
                description=f"Login flow error: {str(e)}",
            ))
            passed = False

        return TestResult(
            device=device_id,
            flow="login",
            passed=passed,
            duration_ms=int((time.time() - start) * 1000),
            findings=findings,
            screenshots=screenshots,
        )

    def _test_queue_view(self, page: Page, device_id: str) -> TestResult:
        """Test the queue view layout and scrolling."""
        start = time.time()
        findings = []
        screenshots = []
        passed = True

        try:
            # Should already be on queue from login test
            page.wait_for_timeout(1000)

            # Check specimen cards
            cards = page.query_selector_all(".specimen-card")
            if len(cards) == 0:
                findings.append(Finding(
                    severity="critical",
                    category="layout",
                    device=device_id,
                    description="No specimen cards found in queue",
                ))
                passed = False
            else:
                findings.append(Finding(
                    severity="info",
                    category="layout",
                    device=device_id,
                    description=f"Found {len(cards)} specimen cards",
                ))

                # Check card dimensions
                first_card = cards[0]
                box = first_card.bounding_box()
                if box:
                    viewport = DEVICES[device_id]["viewport"]

                    # Card should be nearly full width on mobile
                    if DEVICES[device_id]["is_mobile"] and box["width"] < viewport["width"] * 0.85:
                        findings.append(Finding(
                            severity="warning",
                            category="layout",
                            device=device_id,
                            description=f"Card width ({box['width']}px) not utilizing mobile viewport",
                            recommendation="Cards should be ~90% viewport width on mobile",
                        ))

            # Test scroll performance
            scroll_start = time.time()
            page.evaluate("window.scrollBy(0, 500)")
            page.wait_for_timeout(100)
            scroll_time = (time.time() - scroll_start) * 1000

            if scroll_time > 100:
                findings.append(Finding(
                    severity="warning",
                    category="performance",
                    device=device_id,
                    description=f"Scroll feels sluggish ({scroll_time:.0f}ms)",
                ))

            screenshots.append(self._screenshot(page, device_id, "queue_scrolled"))

            # Check filter dropdowns
            filters = page.query_selector_all("select")
            if len(filters) < 2:
                findings.append(Finding(
                    severity="warning",
                    category="layout",
                    device=device_id,
                    description="Expected 2 filter dropdowns (priority, status)",
                ))

        except Exception as e:
            findings.append(Finding(
                severity="critical",
                category="interaction",
                device=device_id,
                description=f"Queue view error: {str(e)}",
            ))
            passed = False

        return TestResult(
            device=device_id,
            flow="queue_view",
            passed=passed,
            duration_ms=int((time.time() - start) * 1000),
            findings=findings,
            screenshots=screenshots,
        )

    def _test_specimen_detail(self, page: Page, device_id: str) -> TestResult:
        """Test specimen detail view and image loading."""
        start = time.time()
        findings = []
        screenshots = []
        passed = True

        try:
            # Scroll back to top and click first card
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(300)

            first_card = page.query_selector(".specimen-card")
            if first_card:
                first_card.click()
                page.wait_for_timeout(3000)  # Wait for image load

                screenshots.append(self._screenshot(page, device_id, "specimen_detail"))

                # Check image loaded
                img = page.query_selector("img")
                if img:
                    natural_width = page.evaluate("el => el.naturalWidth", img)
                    if natural_width > 0:
                        findings.append(Finding(
                            severity="info",
                            category="interaction",
                            device=device_id,
                            description=f"Image loaded successfully ({natural_width}px wide)",
                        ))
                    else:
                        findings.append(Finding(
                            severity="critical",
                            category="interaction",
                            device=device_id,
                            description="Image failed to load (naturalWidth=0)",
                        ))
                        passed = False

                # Check action buttons
                buttons = page.query_selector_all("button")
                button_texts = [b.inner_text() for b in buttons[:5]]

                expected_actions = ["Approve", "Flag", "Reject"]
                for action in expected_actions:
                    if not any(action.lower() in t.lower() for t in button_texts):
                        findings.append(Finding(
                            severity="warning",
                            category="layout",
                            device=device_id,
                            description=f"'{action}' button not visible",
                        ))

                # Check button tap targets (44px minimum for mobile)
                if DEVICES[device_id]["is_mobile"]:
                    for btn in buttons[:4]:
                        box = btn.bounding_box()
                        if box and (box["height"] < 44 or box["width"] < 44):
                            findings.append(Finding(
                                severity="warning",
                                category="accessibility",
                                device=device_id,
                                description=f"Button tap target too small ({box['width']:.0f}x{box['height']:.0f}px)",
                                recommendation="Minimum 44x44px for mobile tap targets",
                            ))
                            break

                # Go back
                back_btn = page.query_selector("text=Back")
                if back_btn:
                    back_btn.click()
                    page.wait_for_timeout(500)

        except Exception as e:
            findings.append(Finding(
                severity="critical",
                category="interaction",
                device=device_id,
                description=f"Specimen detail error: {str(e)}",
            ))
            passed = False

        return TestResult(
            device=device_id,
            flow="specimen_detail",
            passed=passed,
            duration_ms=int((time.time() - start) * 1000),
            findings=findings,
            screenshots=screenshots,
        )

    def _test_touch_interactions(self, page: Page, device_id: str) -> TestResult:
        """Test touch-specific interactions (mobile only)."""
        start = time.time()
        findings = []
        screenshots = []
        passed = True

        if not DEVICES[device_id]["is_mobile"]:
            return TestResult(
                device=device_id,
                flow="touch_interactions",
                passed=True,
                duration_ms=0,
                findings=[Finding(
                    severity="info",
                    category="interaction",
                    device=device_id,
                    description="Skipped - desktop device",
                )],
            )

        try:
            # Test swipe gestures if implemented
            page.wait_for_timeout(500)

            # Check for touch-friendly spacing
            clickables = page.query_selector_all("button, a, .specimen-card")
            too_close = 0

            boxes = []
            for el in clickables[:10]:
                box = el.bounding_box()
                if box:
                    boxes.append(box)

            # Check spacing between adjacent elements
            for i in range(len(boxes) - 1):
                b1, b2 = boxes[i], boxes[i + 1]
                # Vertical gap
                gap = b2["y"] - (b1["y"] + b1["height"])
                if 0 < gap < 8:
                    too_close += 1

            if too_close > 2:
                findings.append(Finding(
                    severity="warning",
                    category="accessibility",
                    device=device_id,
                    description=f"{too_close} clickable elements with <8px spacing",
                    recommendation="Increase spacing between touch targets",
                ))

            findings.append(Finding(
                severity="info",
                category="interaction",
                device=device_id,
                description="Touch interaction test completed",
            ))

        except Exception as e:
            findings.append(Finding(
                severity="warning",
                category="interaction",
                device=device_id,
                description=f"Touch test error: {str(e)}",
            ))

        return TestResult(
            device=device_id,
            flow="touch_interactions",
            passed=passed,
            duration_ms=int((time.time() - start) * 1000),
            findings=findings,
            screenshots=screenshots,
        )

    def _save_report(self, report: TestReport):
        """Save report to JSON for knowledge sharing."""
        report_path = self.output_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # Convert to dict for JSON serialization
        report_dict = {
            "timestamp": report.timestamp,
            "base_url": report.base_url,
            "devices_tested": report.devices_tested,
            "summary": report.summary,
            "results": [
                {
                    "device": r.device,
                    "flow": r.flow,
                    "passed": r.passed,
                    "duration_ms": r.duration_ms,
                    "findings": [asdict(f) for f in r.findings],
                    "screenshots": r.screenshots,
                }
                for r in report.results
            ],
        }

        with open(report_path, "w") as f:
            json.dump(report_dict, f, indent=2)

        print(f"\nReport saved: {report_path}")

        # Also save latest findings summary as markdown for easy reading
        summary_path = self.output_dir / "LATEST_FINDINGS.md"
        self._write_markdown_summary(report, summary_path)

    def _write_markdown_summary(self, report: TestReport, path: Path):
        """Write human-readable summary."""
        lines = [
            "# UI Test Findings",
            f"\n**Generated**: {report.timestamp}",
            f"**URL**: {report.base_url}",
            f"\n## Summary",
            f"- Tests: {report.summary['total_tests']}",
            f"- Passed: {report.summary['passed']}",
            f"- Failed: {report.summary['failed']}",
            f"- Pass Rate: {report.summary['pass_rate']}",
            f"\n### Findings by Severity",
            f"- Critical: {report.summary['findings']['critical']}",
            f"- Warning: {report.summary['findings']['warning']}",
            f"- Info: {report.summary['findings']['info']}",
            "\n## Details by Device\n",
        ]

        for device_id in report.devices_tested:
            device_results = [r for r in report.results if r.device == device_id]
            device_name = DEVICES[device_id]["name"]

            lines.append(f"### {device_name}")

            for result in device_results:
                status = "PASS" if result.passed else "FAIL"
                lines.append(f"\n**{result.flow}**: {status} ({result.duration_ms}ms)")

                for finding in result.findings:
                    icon = {"critical": "!!!", "warning": "!", "info": "-"}[finding.severity]
                    lines.append(f"  {icon} [{finding.category}] {finding.description}")
                    if finding.recommendation:
                        lines.append(f"      -> {finding.recommendation}")

            lines.append("")

        with open(path, "w") as f:
            f.write("\n".join(lines))

        print(f"Summary saved: {path}")


def main():
    import sys

    headed = "--headed" in sys.argv

    print("=" * 60)
    print("Herbarium Review - Device Test Harness")
    print("=" * 60)

    harness = DeviceTestHarness(headed=headed)
    report = harness.run_all_devices()

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Pass Rate: {report.summary['pass_rate']}")
    print(f"Critical Issues: {report.summary['findings']['critical']}")
    print(f"Warnings: {report.summary['findings']['warning']}")
    print(f"\nDetailed findings in: tests/ui/findings/")


if __name__ == "__main__":
    main()
