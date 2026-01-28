# Human-in-the-Loop Correction Workflow

**Purpose:** Combine automated pre-processing with human review for optimal accuracy and sustainability

---

## Why Human-in-the-Loop?

### Benefits Over Full Automation

1. **Faster Results**
   - Partial automation handles easy cases (60-70%)
   - Human reviews hard cases (30-40%)
   - Complete dataset ready in hours, not weeks

2. **Better Accuracy**
   - Human judgment for ambiguous cases
   - Domain expertise for scientific names
   - Catches edge cases automation would miss

3. **Creates Training Data**
   - Human corrections build reference database
   - Improves future automation
   - Iterative learning system

4. **Sustainable for User**
   - Mobile review: 5-10 minute sessions
   - Review during breaks, away from computer
   - Matches disability accommodation needs
   - No typing required (tap/select interface)

---

## Three-Tier Architecture

### Tier 1: Auto-Accept (High Confidence)

**Criteria:** Field confidence ≥ 0.85 AND passes validation

**Process:**
```python
if confidence >= 0.85 and passes_validation(field):
    → AUTO-ACCEPT to final dataset
    → No human review needed
```

**Example:**
- Catalog Number: "IES" (0.95 confidence) → ✅ Auto-accept
- Country: "CANADA" (0.90 confidence) → ✅ Auto-accept

### Tier 2: Auto-Correct with Confirmation (Medium Confidence)

**Criteria:** Field confidence 0.60-0.84 AND fuzzy match found

**Process:**
```python
if 0.60 <= confidence < 0.85:
    suggestion = find_best_match(field_value)
    if suggestion.similarity >= 0.80:
        → Queue for human confirmation
        → Show: "Did you mean [suggestion]?"
        → User: Tap ✓ or ✗
```

**Example:**
- Recorded By: "J. Looten" (0.65) → Suggest "J. Looman"
- Scientific Name: "Stipe viridula" (0.75) → Suggest "Stipa viridula"

### Tier 3: Human Correction (Low Confidence)

**Criteria:** Field confidence < 0.60 OR no auto-correction available

**Process:**
```python
if confidence < 0.60 or no_suggestion:
    → Queue for human data entry
    → Show: Original image + OCR text + field editor
    → User: Types or selects correct value
```

**Example:**
- Event Date: "" (0.0) → Human reviews image, enters "1969-08-11"
- Scientific Name: "lahlonbergla cuspi" (0.30) → Human reviews, searches GBIF

---

## Mobile Review Interface

### Screen Flow

**1. Review Queue Dashboard**
```
┌─────────────────────────────────────┐
│ Review Queue                   15   │
├─────────────────────────────────────┤
│ 🟢 Auto-Accept Ready           25   │
│ 🟡 Confirm Suggestions         10   │
│ 🔴 Manual Correction Needed     5   │
├─────────────────────────────────────┤
│ [Start Review] [View Stats]         │
└─────────────────────────────────────┘
```

**2. Confirmation Review (Tier 2)**
```
┌─────────────────────────────────────┐
│ Specimen 5/15                       │
├─────────────────────────────────────┤
│ [Image Thumbnail]                   │
├─────────────────────────────────────┤
│ Recorded By:                        │
│   OCR: "J. Looten" (conf: 0.65)    │
│   Suggest: "J. Looman"              │
│                                     │
│   [✓ Accept] [✗ Reject] [✏️ Edit]   │
├─────────────────────────────────────┤
│ Scientific Name:                    │
│   OCR: "denecio canua" (0.40)      │
│   GBIF: "Senecio canus" (85%)      │
│                                     │
│   [✓ Accept] [🔍 Search] [✏️ Edit]  │
└─────────────────────────────────────┘
```

**3. Manual Correction (Tier 3)**
```
┌─────────────────────────────────────┐
│ Specimen 12/15                      │
├─────────────────────────────────────┤
│ [Full Image Viewer - Pinch Zoom]   │
├─────────────────────────────────────┤
│ Event Date: (empty)                 │
│                                     │
│ Date on label: [Text field]        │
│   Suggestions:                      │
│   • 1969-08-11                      │
│   • 1969-08                         │
│   • 1969                            │
│                                     │
│   [Save] [Skip] [Flag Issue]       │
└─────────────────────────────────────┘
```

### Touch-Optimized Features

- **Large tap targets** (48x48px minimum)
- **Swipe gestures**: Left = skip, Right = accept
- **Voice input**: Dictate corrections (hands-free)
- **Autocomplete**: Search-as-you-type for scientific names
- **Recent selections**: Quick-pick from previously entered values
- **Offline support**: Review without internet connection

---

## Workflow Example: 40 AAFC Specimens

### Step 1: Automated Pre-Processing

```bash
# Run correction pipeline
python -m correction.pipeline \
  --input ~/aafc/production_run_dec2_batch1_*/raw.jsonl \
  --output ~/aafc/corrected/ \
  --enable-suggestions \
  --confidence-threshold 0.85
```

**Output:**
```
Processing 40 specimens...

✅ Auto-accepted (Tier 1):        12 specimens (30%)
🟡 Needs confirmation (Tier 2):   18 specimens (45%)
🔴 Needs correction (Tier 3):     10 specimens (25%)

Review queue created: corrected/review_queue.json
Total review items: 28 specimens
Estimated review time: 15-20 minutes
```

### Step 2: Mobile Review Session

**User opens mobile interface:**

```
Session 1 (10 minutes):
  - Reviewed 18 Tier 2 (confirmations)
  - Average: 30 seconds per specimen
  - Actions: 15 accepted, 2 edited, 1 skipped

Session 2 (15 minutes):
  - Reviewed 10 Tier 3 (corrections)
  - Average: 90 seconds per specimen
  - Actions: 8 corrected, 2 flagged for later

Total time: 25 minutes
Total specimens completed: 38/40 (95%)
```

### Step 3: Export Refined Data

```bash
# Generate final DwC-A with corrections
python -m correction.pipeline \
  --input ~/aafc/corrected/review_queue.json \
  --apply-corrections \
  --export-dwca \
  --output ~/aafc/final_dwca/
```

**Output:**
```
✅ Final Dataset Statistics:

Scientific Names:  38/40 complete (95%) - was 47%
Event Dates:       36/40 complete (90%) - was 0%
Recorded By:       39/40 complete (97%) - was 32%
Localities:        40/40 complete (100%) - was 45%

Corrections applied:
  - Auto-accepted:     12 specimens
  - Human confirmed:   15 corrections
  - Human corrected:    8 manual entries
  - Flagged for later:  2 specimens

Export: final_dwca/aafc-herbarium-v1.0.0.zip
Ready for Excel review!
```

---

## Implementation Priority

### Phase 1: Basic Review Interface (4-6 hours)

1. **Review Queue Generator** (`src/correction/review_queue.py`)
   - Load corrected data
   - Classify by confidence tier
   - Generate JSON queue for mobile interface

2. **Mobile API Endpoint** (`mobile/api/review.py`)
   - Serve review queue
   - Accept corrections from mobile
   - Update dataset with user input

3. **Mobile Review Screen** (`mobile/components/ReviewScreen.vue`)
   - Display specimen + suggestions
   - Accept/reject/edit controls
   - Progress tracking

### Phase 2: Feedback Loop (2-3 hours)

1. **Correction Database** (`src/correction/corrections.db`)
   - Store user corrections
   - Track suggestion acceptance rates
   - Build reference data

2. **Learning Module** (`src/correction/learn.py`)
   - Analyze correction patterns
   - Update fuzzy matching thresholds
   - Improve collector normalization

3. **Statistics Dashboard**
   - Show improvement over time
   - Identify remaining problem areas
   - Guide future automation

### Phase 3: Advanced Features (optional)

- Voice input for corrections
- Bulk operations (accept all suggestions)
- Collaborative review (multiple users)
- Confidence calibration (adjust thresholds)

---

## Benefits for User's Workflow

### Matches Disability Constraints

1. **Minimal Typing**
   - Tap to confirm suggestions (90% of reviews)
   - Voice input for corrections
   - Autocomplete for data entry

2. **Short Sessions**
   - 5-10 minute review bursts
   - Mobile: review away from desk
   - Pause/resume anytime

3. **Cognitive Load Management**
   - Simple yes/no decisions (Tier 2)
   - One field at a time (Tier 3)
   - Progress saved continuously

### Creates Sustainable Practice

- **Incremental progress**: 5 specimens per session = 40 done in 8 sessions
- **Flexibility**: Review on phone during bathroom breaks
- **Low pressure**: No "must finish today" deadline
- **Visible progress**: Dashboard shows completion %

---

## Success Metrics

### Quality Improvement

**Target vs. Current:**
- Scientific Names: 95% complete (from 47%)
- Event Dates: 90% complete (from 0%)
- Recorded By: 97% complete (from 32%)

**Achieved with:**
- 30% full automation (no review)
- 45% confirmation only (tap ✓)
- 25% manual correction (1-2 min each)

### Time Investment

**Total processing time: 40 specimens**
- Automated pre-processing: 5 minutes
- Human review (Tier 2): 10 minutes
- Human correction (Tier 3): 15 minutes
- **Total: 30 minutes** (vs. 2-3 hours fully manual)

---

## Next Steps

1. ✅ Field parser complete
2. **Build review queue generator** (1-2 hours)
3. **Add review endpoint to mobile API** (1-2 hours)
4. **Create review screen in mobile interface** (2-3 hours)
5. **Test with 40 AAFC specimens** (30 min review session)
6. **Iterate based on feedback**

---

**Bottom Line:** Human-in-the-loop is the OPTIMAL approach for:
- Your health constraints (mobile, short sessions)
- Data quality (human judgment for hard cases)
- Sustainability (training data for future automation)
- Speed (results in days, not weeks)
