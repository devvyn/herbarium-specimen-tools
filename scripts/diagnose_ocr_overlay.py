#!/usr/bin/env python3
"""
Interactive Playwright diagnostic for OCR overlay.

Supports both headless automation and interactive debugging with rich telemetry
collection for human-machine collaborative debugging.

Usage:
    # Headless (CI/automated)
    uv run python scripts/diagnose_ocr_overlay.py

    # Interactive with visible browser
    uv run python scripts/diagnose_ocr_overlay.py --interactive

    # Interactive with slow motion for observation
    uv run python scripts/diagnose_ocr_overlay.py --interactive --slowmo 500

    # Step-by-step mode (pauses at each checkpoint)
    uv run python scripts/diagnose_ocr_overlay.py --interactive --step
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright, Page, ConsoleMessage, Request, Response


@dataclass
class TelemetryEvent:
    """Single telemetry event."""
    timestamp: str
    event_type: str
    data: Dict[str, Any]
    duration_ms: Optional[float] = None


@dataclass
class Checkpoint:
    """Diagnostic checkpoint with captured state."""
    name: str
    timestamp: str
    screenshot_path: Optional[str] = None
    vue_state: Optional[Dict[str, Any]] = None
    dom_metrics: Optional[Dict[str, Any]] = None
    notes: List[str] = field(default_factory=list)
    passed: bool = True


@dataclass
class DiagnosticSession:
    """Full diagnostic session with all telemetry."""
    session_id: str
    started_at: str
    ended_at: Optional[str] = None
    mode: str = "headless"
    base_url: str = "http://127.0.0.1:8080"

    # Telemetry collections
    console_logs: List[TelemetryEvent] = field(default_factory=list)
    network_requests: List[TelemetryEvent] = field(default_factory=list)
    checkpoints: List[Checkpoint] = field(default_factory=list)
    errors: List[TelemetryEvent] = field(default_factory=list)

    # Summary metrics
    total_duration_ms: Optional[float] = None
    tests_passed: int = 0
    tests_failed: int = 0


class DiagnosticRunner:
    """Interactive diagnostic runner with telemetry collection."""

    def __init__(
        self,
        interactive: bool = False,
        slowmo: int = 0,
        step_mode: bool = False,
        base_url: str = "http://127.0.0.1:8080",
    ):
        self.interactive = interactive
        self.slowmo = slowmo
        self.step_mode = step_mode
        self.base_url = base_url

        # Session setup
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(__file__).parent.parent / "test_output" / f"session_{self.session_id}"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.session = DiagnosticSession(
            session_id=self.session_id,
            started_at=datetime.now().isoformat(),
            mode="interactive" if interactive else "headless",
            base_url=base_url,
        )

        self.page: Optional[Page] = None
        self._start_time: Optional[float] = None

    def _timestamp(self) -> str:
        return datetime.now().isoformat()

    def _elapsed_ms(self) -> float:
        if self._start_time:
            return (asyncio.get_event_loop().time() - self._start_time) * 1000
        return 0

    async def _capture_console(self, msg: ConsoleMessage):
        """Capture console messages."""
        event = TelemetryEvent(
            timestamp=self._timestamp(),
            event_type=f"console.{msg.type}",
            data={
                "text": msg.text,
                "location": str(msg.location) if msg.location else None,
                "args": [str(a) for a in msg.args],
            },
            duration_ms=self._elapsed_ms(),
        )
        self.session.console_logs.append(event)

        # Print errors immediately
        if msg.type in ("error", "warning"):
            print(f"  [{msg.type.upper()}] {msg.text}")

    async def _capture_request(self, request: Request):
        """Capture network requests."""
        event = TelemetryEvent(
            timestamp=self._timestamp(),
            event_type="network.request",
            data={
                "url": request.url,
                "method": request.method,
                "resource_type": request.resource_type,
                "headers": dict(request.headers),
            },
            duration_ms=self._elapsed_ms(),
        )
        self.session.network_requests.append(event)

    async def _capture_response(self, response: Response):
        """Capture network responses."""
        event = TelemetryEvent(
            timestamp=self._timestamp(),
            event_type="network.response",
            data={
                "url": response.url,
                "status": response.status,
                "ok": response.ok,
            },
            duration_ms=self._elapsed_ms(),
        )
        self.session.network_requests.append(event)

        if not response.ok:
            print(f"  [HTTP {response.status}] {response.url}")

    async def _get_vue_state(self) -> Optional[Dict[str, Any]]:
        """Extract Vue application state."""
        try:
            return await self.page.evaluate("""() => {
                const app = document.querySelector('#app')?.__vue_app__;
                if (!app) return null;

                const state = app._instance?.proxy;
                if (!state) return null;

                return {
                    // UI State
                    currentView: state.currentView,
                    loading: state.loading,
                    imageZoomed: state.imageZoomed,
                    imageLoaded: state.imageLoaded,

                    // OCR State
                    showOcrRegions: state.showOcrRegions,
                    hasOcrRegions: state.hasOcrRegions,
                    regionSelectionMode: state.regionSelectionMode,
                    selectedRegionIndices: state.selectedRegionIndices,
                    showRegionMenu: state.showRegionMenu,

                    // Image dimensions
                    imageWidth: state.imageWidth,
                    imageHeight: state.imageHeight,

                    // Specimen data
                    currentSpecimenId: state.currentSpecimen?.id,
                    ocrRegionsCount: state.currentSpecimen?.ocr_regions?.length || 0,
                    fieldsCount: Object.keys(state.currentSpecimen?.fields || {}).length,

                    // Queue
                    queueLength: state.queue?.length || 0,
                };
            }""")
        except Exception as e:
            self.session.errors.append(TelemetryEvent(
                timestamp=self._timestamp(),
                event_type="error.vue_state",
                data={"error": str(e)},
            ))
            return None

    async def _get_dom_metrics(self) -> Dict[str, Any]:
        """Get DOM element metrics."""
        metrics = {}

        selectors = {
            "image_container": ".image-container",
            "specimen_image": ".specimen-image",
            "ocr_overlay": ".ocr-overlay",
            "ocr_regions": ".ocr-region",
            "ocr_toggle": ".ocr-toggle",
            "action_menu": ".ocr-action-menu",
        }

        for name, selector in selectors.items():
            try:
                locator = self.page.locator(selector)
                count = await locator.count()

                if count > 0:
                    first = locator.first
                    box = await first.bounding_box()
                    visible = await first.is_visible()

                    metrics[name] = {
                        "count": count,
                        "visible": visible,
                        "bounding_box": box,
                    }

                    # For regions, get all boxes
                    if name == "ocr_regions" and count > 0:
                        all_boxes = []
                        for i in range(min(count, 10)):  # Limit to 10
                            b = await locator.nth(i).bounding_box()
                            if b:
                                all_boxes.append(b)
                        metrics[name]["sample_boxes"] = all_boxes
                else:
                    metrics[name] = {"count": 0, "visible": False}
            except Exception as e:
                metrics[name] = {"error": str(e)}

        return metrics

    async def checkpoint(
        self,
        name: str,
        screenshot: bool = True,
        capture_state: bool = True,
        notes: Optional[List[str]] = None,
    ) -> Checkpoint:
        """Create a diagnostic checkpoint."""
        print(f"\n{'='*60}")
        print(f"CHECKPOINT: {name}")
        print(f"{'='*60}")

        cp = Checkpoint(
            name=name,
            timestamp=self._timestamp(),
            notes=notes or [],
        )

        # Screenshot
        if screenshot:
            screenshot_name = f"{len(self.session.checkpoints):02d}_{name.lower().replace(' ', '_')}.png"
            screenshot_path = self.output_dir / screenshot_name
            await self.page.screenshot(path=str(screenshot_path))
            cp.screenshot_path = str(screenshot_path)
            print(f"  Screenshot: {screenshot_path.name}")

        # Capture Vue state
        if capture_state:
            cp.vue_state = await self._get_vue_state()
            if cp.vue_state:
                print(f"  Vue state captured: {len(cp.vue_state)} properties")

        # Capture DOM metrics
        cp.dom_metrics = await self._get_dom_metrics()
        print(f"  DOM metrics: {len(cp.dom_metrics)} elements")

        self.session.checkpoints.append(cp)

        # Step mode - wait for user
        if self.step_mode and self.interactive:
            input("\n  Press Enter to continue...")

        return cp

    async def test(self, name: str, condition: bool, note: str = "") -> bool:
        """Record a test result."""
        status = "PASS" if condition else "FAIL"
        symbol = "✓" if condition else "✗"

        print(f"  [{symbol}] {name}" + (f" - {note}" if note else ""))

        if condition:
            self.session.tests_passed += 1
        else:
            self.session.tests_failed += 1

        return condition

    async def run(self):
        """Run the full diagnostic session."""
        self._start_time = asyncio.get_event_loop().time()

        print(f"\n{'#'*60}")
        print(f"# OCR OVERLAY DIAGNOSTIC SESSION")
        print(f"# ID: {self.session_id}")
        print(f"# Mode: {self.session.mode}")
        print(f"# Output: {self.output_dir}")
        print(f"{'#'*60}\n")

        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=not self.interactive,
                slow_mo=self.slowmo if self.interactive else 0,
            )

            self.page = await browser.new_page(viewport={"width": 1200, "height": 900})

            # Set up telemetry listeners
            self.page.on("console", self._capture_console)
            self.page.on("request", self._capture_request)
            self.page.on("response", self._capture_response)

            try:
                await self._run_diagnostics()
            except Exception as e:
                self.session.errors.append(TelemetryEvent(
                    timestamp=self._timestamp(),
                    event_type="error.fatal",
                    data={"error": str(e), "type": type(e).__name__},
                ))
                print(f"\n[FATAL ERROR] {e}")
            finally:
                await browser.close()

        # Finalize session
        self.session.ended_at = self._timestamp()
        self.session.total_duration_ms = self._elapsed_ms()

        # Generate outputs
        await self._generate_outputs()

        return self.session

    async def _run_diagnostics(self):
        """Core diagnostic flow."""

        # === LOAD APPLICATION ===
        print("\nLoading review application...")
        await self.page.goto(self.base_url)
        await self.page.wait_for_load_state("networkidle")

        await self.checkpoint("Queue View", notes=["Initial application load"])

        # Check queue loaded
        cards = self.page.locator(".specimen-card")
        card_count = await cards.count()
        await self.test("Queue loads specimens", card_count > 0, f"{card_count} specimens")

        if card_count == 0:
            print("  [ABORT] No specimens to test")
            return

        # === OPEN SPECIMEN ===
        print("\nOpening first specimen...")
        await cards.first.click()
        await self.page.wait_for_load_state("networkidle")
        await self.page.wait_for_timeout(1500)  # Wait for image

        await self.checkpoint("Specimen View", notes=["Before OCR overlay"])

        # Check image loaded
        vue = await self._get_vue_state()
        await self.test("Image loads", vue and vue.get("imageLoaded", False))
        await self.test("Has OCR regions", vue and vue.get("hasOcrRegions", False))

        # === ENABLE OCR OVERLAY ===
        print("\nEnabling OCR overlay...")
        ocr_toggle = self.page.locator(".ocr-toggle").first

        if await ocr_toggle.count() == 0:
            print("  [ABORT] No OCR toggle found")
            return

        await ocr_toggle.click()
        await self.page.wait_for_timeout(500)

        cp = await self.checkpoint("OCR Overlay Enabled")

        # === ALIGNMENT ANALYSIS ===
        print("\nAnalyzing overlay alignment...")

        metrics = cp.dom_metrics
        image_box = metrics.get("specimen_image", {}).get("bounding_box")
        svg_box = metrics.get("ocr_overlay", {}).get("bounding_box")

        if image_box and svg_box:
            x_diff = abs(image_box['x'] - svg_box['x'])
            y_diff = abs(image_box['y'] - svg_box['y'])
            w_diff = abs(image_box['width'] - svg_box['width'])
            h_diff = abs(image_box['height'] - svg_box['height'])

            await self.test("X alignment", x_diff < 2, f"{x_diff:.1f}px offset")
            await self.test("Y alignment", y_diff < 2, f"{y_diff:.1f}px offset")
            await self.test("Width match", w_diff < 2, f"{w_diff:.1f}px diff")
            await self.test("Height match", h_diff < 2, f"{h_diff:.1f}px diff")

        # === ACCESSIBILITY AUDIT ===
        print("\nAccessibility audit...")

        region_count = metrics.get("ocr_regions", {}).get("count", 0)
        aria_count = await self.page.locator(".ocr-region[aria-label]").count()
        tabindex_count = await self.page.locator(".ocr-region[tabindex]").count()

        await self.test("ARIA labels", aria_count == region_count, f"{aria_count}/{region_count}")
        await self.test("Keyboard navigation", tabindex_count == region_count, f"{tabindex_count}/{region_count}")

        # === INTERACTION TESTS ===
        print("\nInteraction tests...")

        regions = self.page.locator(".ocr-region")
        if await regions.count() > 0:
            # Test click to open action menu
            # Use force=True because SVG elements inside scroll containers
            # can have pointer-events intercepted by the scroll container
            await regions.first.click(force=True)
            await self.page.wait_for_timeout(500)

            menu_visible = await self.page.locator(".ocr-action-menu").is_visible()
            await self.test("Action menu opens on click", menu_visible)

            if menu_visible:
                await self.checkpoint("Action Menu Open")

                # Test copy button exists
                copy_btn = self.page.locator(".ocr-menu-btn", has_text="Copy")
                await self.test("Copy button present", await copy_btn.count() > 0)

                # Close menu
                await self.page.locator(".ocr-menu-backdrop").click()
                await self.page.wait_for_timeout(300)

            # Test keyboard navigation
            await regions.first.focus()
            await self.page.wait_for_timeout(200)

            # Check focus state
            focused = await self.page.evaluate("""() => {
                const active = document.activeElement;
                return active?.classList?.contains('ocr-region');
            }""")
            await self.test("Keyboard focus works", focused)

            await self.checkpoint("Keyboard Focus Test")

        # === SELECTION MODE ===
        print("\nSelection mode test...")

        select_btn = self.page.locator(".ocr-toggle", has_text="Select")
        if await select_btn.count() > 0:
            await select_btn.click()
            await self.page.wait_for_timeout(300)

            vue = await self._get_vue_state()
            await self.test("Selection mode activates", vue and vue.get("regionSelectionMode"))

            # Select a region
            if await regions.count() > 0:
                await regions.first.click(force=True)
                await self.page.wait_for_timeout(300)

                selected = await self.page.locator(".ocr-region.selected").count()
                await self.test("Region selection works", selected > 0)

                await self.checkpoint("Selection Mode")

        # === EXTRACT CLIENT TELEMETRY ===
        print("\nExtracting client-side telemetry...")

        client_telemetry = await self.page.evaluate("""() => {
            if (window.herbariumTracker) {
                return {
                    errors: window.herbariumTracker.exportErrors(),
                    telemetry: window.herbariumTracker.exportTelemetry(),
                    stats: window.herbariumTracker.stats(),
                    context: window.herbariumTracker.getContext()
                };
            }
            return null;
        }""")

        if client_telemetry:
            self.session.errors.extend([
                TelemetryEvent(
                    timestamp=e.get('timestamp', ''),
                    event_type=f"client.{e.get('type', 'error')}",
                    data=e
                ) for e in client_telemetry.get('errors', [])
            ])
            print(f"  Client errors: {client_telemetry['stats'].get('errorCount', 0)}")
            print(f"  Client telemetry events: {client_telemetry['stats'].get('telemetryCount', 0)}")
        else:
            print("  Client telemetry not available (herbariumTracker not loaded)")

        # === FINAL STATE ===
        await self.checkpoint("Final State", notes=["End of diagnostic run"])

    async def _generate_outputs(self):
        """Generate human and machine readable outputs."""

        # === TELEMETRY JSON ===
        telemetry_path = self.output_dir / "telemetry.json"

        # Convert dataclasses to dicts
        session_dict = {
            "session_id": self.session.session_id,
            "started_at": self.session.started_at,
            "ended_at": self.session.ended_at,
            "mode": self.session.mode,
            "base_url": self.session.base_url,
            "total_duration_ms": self.session.total_duration_ms,
            "tests_passed": self.session.tests_passed,
            "tests_failed": self.session.tests_failed,
            "console_logs": [asdict(e) for e in self.session.console_logs],
            "network_requests": [asdict(e) for e in self.session.network_requests],
            "checkpoints": [asdict(c) for c in self.session.checkpoints],
            "errors": [asdict(e) for e in self.session.errors],
        }

        with open(telemetry_path, "w") as f:
            json.dump(session_dict, f, indent=2, default=str)

        print(f"\nTelemetry saved: {telemetry_path}")

        # === HUMAN REPORT ===
        report_path = self.output_dir / "report.md"

        report = [
            f"# OCR Overlay Diagnostic Report",
            f"",
            f"**Session ID:** {self.session.session_id}",
            f"**Mode:** {self.session.mode}",
            f"**Started:** {self.session.started_at}",
            f"**Duration:** {self.session.total_duration_ms:.0f}ms" if self.session.total_duration_ms else "",
            f"",
            f"## Summary",
            f"",
            f"- Tests Passed: {self.session.tests_passed}",
            f"- Tests Failed: {self.session.tests_failed}",
            f"- Console Errors: {len([l for l in self.session.console_logs if 'error' in l.event_type])}",
            f"- Network Errors: {len([r for r in self.session.network_requests if r.event_type == 'network.response' and not r.data.get('ok', True)])}",
            f"",
            f"## Checkpoints",
            f"",
        ]

        for cp in self.session.checkpoints:
            report.append(f"### {cp.name}")
            report.append(f"")
            if cp.screenshot_path:
                report.append(f"![{cp.name}]({Path(cp.screenshot_path).name})")
                report.append(f"")
            if cp.notes:
                for note in cp.notes:
                    report.append(f"- {note}")
                report.append(f"")
            if cp.vue_state:
                report.append(f"**Vue State:**")
                report.append(f"```json")
                report.append(json.dumps(cp.vue_state, indent=2))
                report.append(f"```")
                report.append(f"")

        if self.session.errors:
            report.append(f"## Errors")
            report.append(f"")
            for err in self.session.errors:
                report.append(f"- [{err.event_type}] {err.data}")
            report.append(f"")

        with open(report_path, "w") as f:
            f.write("\n".join(report))

        print(f"Report saved: {report_path}")

        # === SUMMARY ===
        print(f"\n{'='*60}")
        print(f"DIAGNOSTIC COMPLETE")
        print(f"{'='*60}")
        print(f"  Tests: {self.session.tests_passed} passed, {self.session.tests_failed} failed")
        print(f"  Duration: {self.session.total_duration_ms:.0f}ms" if self.session.total_duration_ms else "")
        print(f"  Output: {self.output_dir}")
        print(f"{'='*60}\n")


async def main():
    parser = argparse.ArgumentParser(
        description="Interactive OCR overlay diagnostic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run with visible browser (not headless)",
    )
    parser.add_argument(
        "--slowmo",
        type=int,
        default=0,
        help="Slow down actions by N milliseconds (useful for observation)",
    )
    parser.add_argument(
        "--step", "-s",
        action="store_true",
        help="Step mode: pause at each checkpoint (requires --interactive)",
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8080",
        help="Base URL of review app (default: http://127.0.0.1:8080)",
    )

    args = parser.parse_args()

    if args.step and not args.interactive:
        print("Warning: --step requires --interactive, enabling interactive mode")
        args.interactive = True

    runner = DiagnosticRunner(
        interactive=args.interactive,
        slowmo=args.slowmo,
        step_mode=args.step,
        base_url=args.url,
    )

    session = await runner.run()

    # Exit with failure code if tests failed
    sys.exit(1 if session.tests_failed > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
