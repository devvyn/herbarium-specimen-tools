# Review Workflow

Complete state machine for specimen review, including the multi-role entrant workflow for institutional digitization projects.

## Review Status State Machine

```mermaid
stateDiagram-v2
    [*] --> PENDING: Extraction Complete

    PENDING --> IN_REVIEW: Curator Opens

    IN_REVIEW --> NEEDS_CORRECTION: Issues Found
    IN_REVIEW --> APPROVED: Quick Approve
    IN_REVIEW --> REJECTED: Reject

    NEEDS_CORRECTION --> DRAFT_CORRECTED: Curator Corrects
    NEEDS_CORRECTION --> PENDING: Request Re-extraction

    DRAFT_CORRECTED --> ENTRANT_REVIEW: Assign to Entrant

    ENTRANT_REVIEW --> ENTRANT_APPROVED: Entrant Approves
    ENTRANT_REVIEW --> NEEDS_CORRECTION: Entrant Rejects

    ENTRANT_APPROVED --> READY_FOR_EXPORT: Supervisor Approves
    ENTRANT_APPROVED --> NEEDS_CORRECTION: Supervisor Rejects

    READY_FOR_EXPORT --> EXPORTED: Export Complete

    APPROVED --> [*]: Simple Workflow End
    REJECTED --> [*]: Rejected End
    EXPORTED --> [*]: Full Workflow End
```

## Review Priority Levels

```mermaid
graph LR
    subgraph "Priority Calculation"
        CRITICAL[CRITICAL<br/>Value: 1]
        HIGH[HIGH<br/>Value: 2]
        MEDIUM[MEDIUM<br/>Value: 3]
        LOW[LOW<br/>Value: 4]
        MINIMAL[MINIMAL<br/>Value: 5]
    end

    subgraph "Triggers"
        T1[Critical Issues<br/>or No DwC Fields] --> CRITICAL
        T2[Quality < 50%<br/>or GBIF Issues] --> HIGH
        T3[Quality < 75%] --> MEDIUM
        T4[Warnings Present] --> LOW
        T5[Excellent Quality] --> MINIMAL
    end

    style CRITICAL fill:#ff6b6b
    style HIGH fill:#ffa94d
    style MEDIUM fill:#ffd43b
    style LOW fill:#69db7c
    style MINIMAL fill:#38d9a9
```

## Entrant Workflow Detail

```mermaid
sequenceDiagram
    participant EXT as Extraction
    participant CUR as Curator
    participant ENT as Data Entrant
    participant SUP as Supervisor
    participant EXP as Export

    EXT->>CUR: New specimen (PENDING)
    CUR->>CUR: Review & Identify Issues

    alt No Issues
        CUR->>EXP: Quick Approve (APPROVED)
    else Issues Found
        CUR->>CUR: NEEDS_CORRECTION
        CUR->>CUR: Make Corrections
        CUR->>ENT: DRAFT_CORRECTED -> ENTRANT_REVIEW

        alt Entrant Approves
            ENT->>SUP: ENTRANT_APPROVED

            alt Supervisor Approves
                SUP->>EXP: READY_FOR_EXPORT -> EXPORTED
            else Supervisor Rejects
                SUP->>CUR: Back to NEEDS_CORRECTION
            end
        else Entrant Rejects
            ENT->>CUR: Back to NEEDS_CORRECTION
        end
    end
```

## Correction Tracking Flow

```mermaid
graph TD
    subgraph "Original Extraction"
        RAW[raw_extraction<br/>Immutable AI Output]
    end

    subgraph "Correction Process"
        FIELD[Field Correction<br/>apply_correction]
        AUDIT[Correction Record<br/>value, corrected_by,<br/>corrected_at, original,<br/>was_ai_extracted, reason]
    end

    subgraph "Tracking"
        DWC[dwc_fields<br/>Updated Values]
        CORR[corrections Dict<br/>Field-level History]
        EXPORT[export_status<br/>modified_after_export]
    end

    RAW --> FIELD
    FIELD --> AUDIT
    AUDIT --> DWC
    AUDIT --> CORR
    DWC --> EXPORT
```

## Flag vs Status (Orthogonal Concepts)

```mermaid
graph TD
    subgraph "Status (Mutually Exclusive)"
        S1[PENDING]
        S2[IN_REVIEW]
        S3[NEEDS_CORRECTION]
        S4[APPROVED]
        S5[REJECTED]
    end

    subgraph "Flag (Independent)"
        F1[flagged: true<br/>Needs Curator Attention]
        F2[flagged: false<br/>Normal Processing]
    end

    subgraph "Combined View"
        C1[PENDING + Flagged<br/>Priority curator review]
        C2[IN_REVIEW + Flagged<br/>Expert attention needed]
        C3[APPROVED + Flagged<br/>Approved but noted]
    end

    S1 --- F1 --> C1
    S2 --- F1 --> C2
    S4 --- F1 --> C3
```

## Quality Score Calculation

```mermaid
graph LR
    subgraph "Inputs"
        COMP[Completeness Score<br/>0-100%]
        CONF[Confidence Score<br/>0-1]
    end

    subgraph "Calculation"
        CALC["quality_score =<br/>(completeness * 0.6) +<br/>(confidence * 100 * 0.4)"]
    end

    subgraph "Output"
        QUALITY[Quality Score<br/>0-100]
        PRIORITY[Priority Level<br/>CRITICAL-MINIMAL]
    end

    COMP --> CALC
    CONF --> CALC
    CALC --> QUALITY
    QUALITY --> PRIORITY
```

## Components Table

| Component | Location | Description |
|-----------|----------|-------------|
| ReviewStatus Enum | `/src/review/engine.py:26-39` | Status values and lifecycle states |
| ReviewPriority Enum | `/src/review/engine.py:42-48` | Priority levels (1-5) |
| SpecimenReview Dataclass | `/src/review/engine.py:51-215` | Complete specimen review record |
| apply_correction() | `/src/review/engine.py:146-173` | Apply field correction with audit |
| assign_to_entrant() | `/src/review/engine.py:216-227` | Assign specimen to data entrant |
| entrant_approve() | `/src/review/engine.py:229-241` | Entrant approval workflow |
| entrant_reject() | `/src/review/engine.py:243-255` | Entrant rejection workflow |
| supervisor_approve() | `/src/review/engine.py:257-266` | Final supervisor approval |
| calculate_quality_score() | `/src/review/engine.py:117-126` | Quality calculation |
| determine_priority() | `/src/review/engine.py:128-144` | Priority assignment |

## Status Transitions

| From | To | Trigger | Actor |
|------|-----|---------|-------|
| - | PENDING | Extraction complete | System |
| PENDING | IN_REVIEW | Curator opens | Curator |
| IN_REVIEW | APPROVED | Quick approve | Curator |
| IN_REVIEW | REJECTED | Quick reject | Curator |
| IN_REVIEW | NEEDS_CORRECTION | Issues found | Curator |
| NEEDS_CORRECTION | DRAFT_CORRECTED | Corrections made | Curator |
| NEEDS_CORRECTION | PENDING | Re-extraction requested | Curator |
| DRAFT_CORRECTED | ENTRANT_REVIEW | Assignment | Curator |
| ENTRANT_REVIEW | ENTRANT_APPROVED | Entrant accepts | Entrant |
| ENTRANT_REVIEW | NEEDS_CORRECTION | Entrant rejects | Entrant |
| ENTRANT_APPROVED | READY_FOR_EXPORT | Supervisor accepts | Supervisor |
| ENTRANT_APPROVED | NEEDS_CORRECTION | Supervisor rejects | Supervisor |
| READY_FOR_EXPORT | EXPORTED | Export complete | System |

## See Also

- [System Overview](../architecture/system-overview.md) - High-level architecture
- [API Endpoints](../architecture/api-endpoints.md) - REST API structure
- [Entrant Workflow Documentation](/docs/ENTRANT_WORKFLOW_IMPLEMENTATION.md) - Detailed implementation guide
