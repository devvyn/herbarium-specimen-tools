# UI Test Findings

**Generated**: 2026-01-15T11:25:36.841764
**URL**: http://localhost:8080

## Summary
- Tests: 20
- Passed: 20
- Failed: 0
- Pass Rate: 100.0%

### Findings by Severity
- Critical: 0
- Warning: 11
- Info: 20

## Details by Device

### iPhone 14

**login**: PASS (4965ms)
  - [interaction] Login flow completed successfully

**queue_view**: PASS (1228ms)
  - [layout] Found 50 specimen cards
  ! [performance] Scroll feels sluggish (103ms)

**specimen_detail**: PASS (4105ms)
  - [interaction] Image loaded successfully (1068px wide)
  ! [layout] 'Reject' button not visible

**touch_interactions**: PASS (553ms)
  - [interaction] Touch interaction test completed

### iPhone SE

**login**: PASS (3697ms)
  - [interaction] Login flow completed successfully

**queue_view**: PASS (1187ms)
  - [layout] Found 50 specimen cards
  ! [performance] Scroll feels sluggish (102ms)

**specimen_detail**: PASS (3994ms)
  - [interaction] Image loaded successfully (1068px wide)
  ! [layout] 'Reject' button not visible

**touch_interactions**: PASS (534ms)
  - [interaction] Touch interaction test completed

### Pixel 7

**login**: PASS (4097ms)
  - [interaction] Login flow completed successfully

**queue_view**: PASS (1226ms)
  - [layout] Found 50 specimen cards
  ! [performance] Scroll feels sluggish (102ms)

**specimen_detail**: PASS (4315ms)
  - [interaction] Image loaded successfully (1068px wide)
  ! [layout] 'Reject' button not visible

**touch_interactions**: PASS (550ms)
  - [interaction] Touch interaction test completed

### iPad Mini

**login**: PASS (3823ms)
  - [interaction] Login flow completed successfully

**queue_view**: PASS (1243ms)
  - [layout] Found 50 specimen cards
  ! [layout] Card width (360px) not utilizing mobile viewport
      -> Cards should be ~90% viewport width on mobile
  ! [performance] Scroll feels sluggish (103ms)

**specimen_detail**: PASS (4093ms)
  - [interaction] Image loaded successfully (1068px wide)
  ! [layout] 'Reject' button not visible

**touch_interactions**: PASS (541ms)
  - [interaction] Touch interaction test completed

### Desktop Chrome

**login**: PASS (3625ms)
  - [interaction] Login flow completed successfully

**queue_view**: PASS (1176ms)
  - [layout] Found 50 specimen cards
  ! [performance] Scroll feels sluggish (105ms)

**specimen_detail**: PASS (3957ms)
  - [interaction] Image loaded successfully (1068px wide)
  ! [layout] 'Reject' button not visible

**touch_interactions**: PASS (0ms)
  - [interaction] Skipped - desktop device
