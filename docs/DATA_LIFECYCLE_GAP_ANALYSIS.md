# Data Lifecycle Gap Analysis

**Date**: 2025-12-03
**Status**: 🟡 Partial Implementation - Missing Critical Workflow Tracking

## Question

> How complete is the data? Are we tracking raw vs corrected draft vs approved by entrant draft vs exported drafts, etc?

## Current State: What We're Tracking ✅

### 1. Extraction Provenance (Comprehensive)
**File**: `src/extraction/provenance.py`

```python
@dataclass
class FieldProvenance:
    value: str
    confidence: float
    model: str              # Which AI model
    provider: str           # openai, anthropic, apple
    extraction_method: str  # direct, ocr_text, confidence_routing
    timestamp: str
    processing_time_ms: float
    estimated_cost_usd: float

    # Re-extraction tracking
    original_confidence: Optional[float]
    original_model: Optional[str]
    improvement: Optional[float]

    # Validation
    gbif_validated: bool
    gbif_cache_hit: bool

    # Version control
    code_version: Optional[str]  # Git commit hash
    prompt_version: Optional[str]
```

**What this captures**: Complete extraction history - every AI call, every re-extraction, every validation.

### 2. Review Workflow (Basic)
**File**: `src/review/engine.py`

```python
class ReviewStatus(Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"

@dataclass
class SpecimenReview:
    # Original extraction
    dwc_fields: Dict              # RAW extracted data

    # Quality metrics
    completeness_score: float
    confidence_score: float
    quality_score: float

    # Review state
    status: ReviewStatus
    reviewed_by: Optional[str]
    reviewed_at: Optional[str]
    corrections: Dict             # User corrections
    notes: Optional[str]

    # Provenance
    extraction_timestamp: str
    model: str
    provider: str
    extraction_method: str
    provenance_history: List[dict]
```

**What this captures**: Basic workflow state, user corrections, review metadata.

## Critical Gaps: What We're NOT Tracking ❌

### 1. ❌ Raw vs Corrected Data Distinction

**Problem**: We have `dwc_fields` and `corrections` but no clear versioning.

**Missing**:
- Which fields are "raw" (untouched AI output)?
- Which fields are "corrected" (user-modified)?
- What was the original value before correction?
- Who made the correction and when?

**Example scenario**:
```json
{
  "dwc_fields": {
    "scientificName": "Setaria viridis"  // Is this raw AI or corrected?
  },
  "corrections": {
    "locality": "Field 23B"  // This is clearly corrected, but what about scientificName?
  }
}
```

**Cannot answer**:
- "Show me all specimens with uncorrected fields"
- "What percentage of AI extractions required correction?"
- "Which fields have the lowest accuracy (most corrections)?"

### 2. ❌ Draft vs Approved by Entrant

**Problem**: No distinction between "curator reviewed" vs "entrant approved" vs "final".

**Missing states**:
- `DRAFT_CORRECTED` - Curator made corrections but not finalized
- `ENTRANT_REVIEW` - Sent to data entrant for approval
- `ENTRANT_APPROVED` - Data entrant signed off
- `READY_FOR_EXPORT` - Final pre-export state

**Current workflow**:
```
PENDING → IN_REVIEW → APPROVED
```

**Should be**:
```
PENDING → IN_REVIEW → DRAFT_CORRECTED → ENTRANT_REVIEW → ENTRANT_APPROVED → READY_FOR_EXPORT → EXPORTED
```

**Use case we can't handle**:
- Collaborative workflow where field tech corrects, then supervisor approves
- "Show me all specimens awaiting entrant approval"
- "Which entrant has the most pending approvals?"

### 3. ❌ Export Tracking

**Problem**: No record of what's been exported, when, in what format.

**Missing**:
- Export timestamp
- Export format (DwC-A, CSV, GBIF)
- Export destination (S3, local, GBIF portal)
- Export version number
- Exported by whom
- Can specimen be re-exported?

**Cannot answer**:
- "Has this specimen been exported to GBIF?"
- "When was the last export run?"
- "Which specimens changed since last export?"
- "Generate delta export (only changed records)"

### 4. ❌ Field-Level Change History

**Problem**: We track that corrections exist, but not the full audit trail.

**Missing**:
- Who changed each field
- When each field was changed
- What the previous value was
- Why it was changed (correction reason/notes)
- Chain of changes (field corrected 3 times)

**Example**: Cannot reconstruct this history:
```
scientificName:
  2025-12-01 10:00 - AI extracted "Setaria Viridis" (0.75 confidence)
  2025-12-01 14:30 - User A corrected to "Setaria viridis" (capitalization)
  2025-12-02 09:15 - User B corrected to "Setaria viridis (L.) Beauv." (added authority)
  2025-12-02 11:00 - Supervisor approved final value
```

### 5. ❌ Version Snapshots

**Problem**: No ability to rollback or compare versions.

**Missing**:
- Version numbers for each specimen record
- Snapshot of data at each stage (raw, draft, approved, exported)
- Ability to rollback to previous version
- Diff between versions

**Cannot do**:
- "Restore specimen to pre-correction state"
- "Show me what changed between draft and approved"
- "Export version 2 of this specimen (before last edit)"

### 6. ❌ Batch Export Sessions

**Problem**: No concept of export "runs" or "batches".

**Missing**:
- Export session ID
- Which specimens were in which export
- Export validation results
- Re-export tracking (same specimen exported twice)

**Cannot answer**:
- "Which specimens were in the 2025-Q1 GBIF submission?"
- "How many specimens have been exported more than once?"
- "Generate export manifest for audit purposes"

### 7. ❌ Entrant/Curator Identity Tracking

**Problem**: `reviewed_by` is optional string, no formal user model.

**Missing**:
- User roles (curator, entrant, supervisor, admin)
- User permissions (who can approve vs export)
- User activity logs
- User assignment (specimen assigned to specific curator)

**Cannot do**:
- "Show me all specimens assigned to curator John"
- "Track productivity: specimens reviewed per curator"
- "Enforce permissions: only supervisors can export"

## Impact Assessment

### High Impact (Data Integrity)
1. **Raw vs Corrected Tracking**: Critical for measuring AI accuracy
2. **Field-Level Change History**: Essential for scientific reproducibility
3. **Version Snapshots**: Required for data recovery and auditing

### Medium Impact (Workflow)
4. **Entrant Approval Stage**: Needed for collaborative workflows
5. **Export Tracking**: Important for GBIF compliance and data governance

### Low Impact (Nice to Have)
6. **Batch Export Sessions**: Useful for reporting but not critical
7. **Formal User Model**: Can use external auth system

## Recommended Solution: Enhanced Data Model

### Option A: Minimal Fix (Quick)
**Timeline**: 1-2 hours

Add simple tracking to existing model:

```python
@dataclass
class SpecimenReview:
    # ... existing fields ...

    # NEW: Track what's raw vs corrected
    raw_dwc_fields: Dict  # Original AI output (immutable)
    corrected_dwc_fields: Dict  # Current working version

    # NEW: Export tracking
    export_status: Optional[str] = None  # "not_exported", "exported", "re_export_needed"
    last_exported_at: Optional[str] = None
    export_version: int = 0
```

**Pros**: Fast, minimal code changes
**Cons**: Still missing field-level history, no version snapshots

### Option B: Intermediate (Recommended)
**Timeline**: 4-6 hours

Add comprehensive versioning:

```python
@dataclass
class FieldVersion:
    """Track changes to a single field over time."""
    field_name: str
    value: str
    confidence: float
    changed_by: str
    changed_at: str
    change_reason: Optional[str]
    version: int

@dataclass
class SpecimenVersion:
    """Snapshot of specimen at a point in time."""
    version: int
    timestamp: str
    dwc_fields: Dict
    status: str
    changed_by: str
    change_summary: str

@dataclass
class SpecimenReview:
    # ... existing fields ...

    # NEW: Version tracking
    current_version: int = 1
    versions: List[SpecimenVersion] = field(default_factory=list)
    field_history: Dict[str, List[FieldVersion]] = field(default_factory=dict)

    # NEW: Export tracking
    export_history: List[dict] = field(default_factory=list)
    export_status: str = "not_exported"

    # NEW: Enhanced workflow
    entrant_status: Optional[str] = None  # "pending", "approved", "rejected"
    entrant_approved_by: Optional[str] = None
    entrant_approved_at: Optional[str] = None
```

**Pros**: Solves most gaps, good audit trail
**Cons**: More storage overhead, migration needed

### Option C: Full Solution (Production-Grade)
**Timeline**: 2-3 days

Separate database tables for full relational tracking:

```sql
-- Core specimen record
specimens (
    id, sha256_hash, created_at, updated_at
)

-- Version history
specimen_versions (
    id, specimen_id, version, snapshot_json, created_at, created_by
)

-- Field change audit
field_changes (
    id, specimen_id, field_name, old_value, new_value,
    changed_by, changed_at, reason
)

-- Export tracking
exports (
    id, export_date, format, destination, exported_by, status
)

export_specimens (
    export_id, specimen_id, specimen_version, validation_status
)

-- User management
users (
    id, username, role, email, permissions
)

-- Workflow state machine
workflow_states (
    specimen_id, state, entered_at, entered_by, notes
)
```

**Pros**: Full audit capability, scalable, enterprise-grade
**Cons**: Significant development time, database migration complexity

## Immediate Recommendation

### Phase 1: Quick Fix (TODAY - 2 hours)

Add to `SpecimenReview`:

```python
# Track original extraction (immutable)
raw_extraction: Dict = None  # Set once, never modified

# Track export state
export_status: str = "not_exported"  # "not_exported", "exported", "modified_after_export"
last_export_timestamp: Optional[str] = None
export_count: int = 0

def apply_correction(self, field: str, new_value: str, corrected_by: str):
    """Apply correction and track change."""
    # Store in corrections dict
    self.corrections[field] = {
        "value": new_value,
        "corrected_by": corrected_by,
        "corrected_at": datetime.utcnow().isoformat(),
        "original_value": self.dwc_fields.get(field),
        "was_ai_extracted": field in self.raw_extraction if self.raw_extraction else False
    }

    # Update main fields
    self.dwc_fields[field] = new_value

    # Mark as needing re-export
    if self.export_status == "exported":
        self.export_status = "modified_after_export"
```

**This solves**:
- ✅ Raw vs corrected distinction
- ✅ Basic export tracking
- ✅ Change attribution (who/when)
- ✅ Modified-after-export detection

### Phase 2: Entrant Workflow (TOMORROW - 4 hours)

Add entrant approval stage:

```python
class ReviewStatus(Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    NEEDS_CORRECTION = "needs_correction"
    CORRECTED_DRAFT = "corrected_draft"      # NEW
    ENTRANT_REVIEW = "entrant_review"        # NEW
    ENTRANT_APPROVED = "entrant_approved"    # NEW
    READY_FOR_EXPORT = "ready_for_export"    # NEW
    EXPORTED = "exported"                    # NEW
    APPROVED = "approved"  # Legacy, keep for compatibility
    REJECTED = "rejected"

@dataclass
class SpecimenReview:
    # ... existing ...

    # NEW: Entrant tracking
    assigned_to: Optional[str] = None
    entrant_reviewed_by: Optional[str] = None
    entrant_reviewed_at: Optional[str] = None
    entrant_notes: Optional[str] = None
```

**This solves**:
- ✅ Multi-stage review workflow
- ✅ Curator vs entrant distinction
- ✅ Assignment tracking

### Phase 3: Full Audit Trail (NEXT WEEK - 2 days)

Implement version snapshots and field history (Option B above).

## Questions for Decision

1. **Export frequency**: Daily? Weekly? On-demand?
2. **Re-export policy**: Can specimens be exported multiple times? Only if changed?
3. **User roles**: How many? (curator, entrant, supervisor, admin?)
4. **Approval authority**: Who can approve vs who can only review?
5. **GBIF requirements**: What metadata do they require for exports?

## Conclusion

**Current Status**: 🟡 **40% Complete**

We have excellent **extraction provenance** but weak **workflow tracking**.

**Missing Critical Features**:
- Raw vs corrected data distinction
- Entrant approval workflow
- Export history
- Field-level audit trail

**Recommended Action**: Implement Phase 1 (2 hours) TODAY to get to 70% complete, then Phase 2 (4 hours) for full workflow support.
