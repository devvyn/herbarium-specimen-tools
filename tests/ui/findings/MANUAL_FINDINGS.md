# Manual UI/UX Findings

User-reported issues discovered during real device testing.

## 2026-01-15

### Zoom/Pan Interaction Issue

**Severity**: Warning
**Category**: Interaction
**Device**: iPhone (physical)
**Reporter**: Devvyn

**Description**:
User cannot pan to view different parts of the image while zoomed in via the "Tap to zoom" feature. The zoomed view is static/centered.

**Workaround**:
Native device affordances (two-finger pinch-to-zoom) work correctly and allow panning.

**Recommendation**:
Either:
1. Implement touch-drag panning when zoomed in via tap
2. Remove custom "tap to zoom" and rely on native gestures
3. Add visual hint that pinch-to-zoom is preferred

**Technical Notes**:
The tap-to-zoom likely uses CSS transform scale without implementing touch move handlers for pan offset. Native gestures bypass this by operating at the browser/OS level.

---

## Automated Test Findings Summary

From `device_test_harness.py` run on 2026-01-15:

- **'Reject' button not visible**: Appears to be below fold on specimen detail view across all devices. Consider reordering action buttons or making them sticky.

- **iPad card width**: Cards only 360px wide on 768px viewport (47%). Should utilize more horizontal space on tablets.

- **Scroll performance**: ~100ms scroll lag detected. May be acceptable but worth monitoring.
