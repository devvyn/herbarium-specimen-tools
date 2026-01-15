# Manual UI/UX Findings

User-reported issues discovered during real device testing.

## 2026-01-15

### ~~Zoom/Pan Interaction Issue~~ RESOLVED

**Severity**: Warning
**Category**: Interaction
**Device**: iPhone (physical)
**Reporter**: Devvyn
**Status**: FIXED (2026-01-15)

**Description**:
User cannot pan to view different parts of the image while zoomed in via the "Tap to zoom" feature. The zoomed view is static/centered.

**Resolution**:
Removed custom tap-to-zoom in favor of native pinch-to-zoom gestures:
- Deleted `toggleImageZoom()` method and `imageZoomed` state
- Changed hint from "Tap to zoom" to "Pinch to zoom"
- Added `touch-action: manipulation` CSS for optimal touch handling

Native pinch-to-zoom handles both zoom and pan correctly on all mobile devices.

---

## Automated Test Findings Summary

From `device_test_harness.py` run on 2026-01-15:

- **'Reject' button not visible**: Appears to be below fold on specimen detail view across all devices. Consider reordering action buttons or making them sticky.

- **iPad card width**: Cards only 360px wide on 768px viewport (47%). Should utilize more horizontal space on tablets.

- **Scroll performance**: ~100ms scroll lag detected. May be acceptable but worth monitoring.
