# Workspace Boundary Specification

**Repository**: herbarium-specimen-tools
**Version**: 1.0.0
**Status**: Public Open Source Repository
**Last Updated**: 2025-12-01

---

## Workspace Classification

**Security Level**: PUBLISHED (Public GitHub Repository)
**Relationship**: Standalone public repository, extracted from AAFC private project
**Meta-Project Relationship**: Service provider (registered service)

---

## Authority Domain

### This Workspace Owns (herbarium-specimen-tools)

**Domain**: Generic herbarium digitization tools for community use

**Responsibilities**:
- Mobile PWA review interface (generic/reusable)
- Analytics utilities for specimen data (DuckDB-based)
- Example workflows (anonymized)
- Generic documentation and guides
- Community support and contributions
- Open source maintenance

**Contents**:
```
✅ mobile/ - PWA interface for specimen review
✅ scripts/ - Analytics and utility scripts
✅ examples/ - Sample data and workflows
✅ docs/ - Generic documentation
✅ tests/ - Test suite for generic tools
✅ README.md - Public project documentation
✅ LICENSE - MIT open source license
✅ CONTRIBUTING.md - Community guidelines
```

**Testing Authority**: This workspace
- Unit tests for mobile API
- Integration tests for PWA
- Sample data validation

**Documentation Authority**: This workspace
- Mobile interface documentation
- Analytics tool guides
- API reference
- Example workflows

### External Dependencies

**Consumes from Meta-Project**:
- None directly (standalone repository)
- Follows security patterns from meta-project knowledge base
- May reference coordination patterns in documentation

**Consumes from AAFC Project**:
- None (extracted and anonymized)
- Originally derived from AAFC private repo
- Now maintained independently

**Provides to Community**:
- Mobile PWA interface (open source)
- Analytics tools (open source)
- Example workflows
- Documentation and guides

---

## Security Boundaries

### Classification: PUBLISHED

**What This Means**:
- ✅ Safe for public GitHub (no private data)
- ✅ No credentials or API keys
- ✅ No institutional data
- ✅ All examples are anonymized
- ✅ Open source (MIT License)

### Data Handling Rules

**FORBIDDEN in this workspace**:
- ❌ Real specimen data (use anonymized samples only)
- ❌ Institutional credentials
- ❌ AAFC-specific configurations
- ❌ Real curator names or contact info
- ❌ Any SECRET or PRIVATE classified data

**ALLOWED in this workspace**:
- ✅ Generic code and utilities
- ✅ Anonymized sample data (EXAMPLE-001, etc.)
- ✅ Public domain herbarium images
- ✅ Generic documentation
- ✅ Community contributions

### Anonymization Rules

When creating examples:
```
Real Data               → Generic Example
-------------------------------------------
"AAFC Herbarium"       → "Example Herbarium"
"Saskatoon, SK"        → "Example City"
"Dr. Real Name"        → "Sample Curator"
Catalog "019121"       → "EXAMPLE-001"
Real images            → Public domain samples
```

---

## Service Registration

### Registered Services

**Service**: Mobile PWA Review Interface
- **Version**: 0.1.0
- **Status**: Active
- **Capabilities**:
  - Touch-optimized specimen review
  - Offline support (service workers)
  - Darwin Core field editing
  - GBIF validation display
  - Priority-based workflow
  - JWT authentication
- **Dependencies**: FastAPI, Vue.js 3, Python 3.11+
- **Documentation**: mobile/README.md

**Service**: Analytics Utilities
- **Version**: 0.1.0
- **Status**: Planned (to be added)
- **Capabilities**:
  - DuckDB-based data analysis
  - Field coverage statistics
  - Confidence distributions
  - Quality assessment
- **Dependencies**: DuckDB, Python 3.11+
- **Documentation**: docs/analytics.md (to be created)

### Registration with Meta-Project

**Registered in**: `~/devvyn-meta-project/SERVICE_REGISTRY.md`
- Service name: "Herbarium Mobile PWA Interface"
- Provider: herbarium-specimen-tools (public repo)
- Consumers: AAFC project (can optionally use), community

---

## File Ownership

### Exclusive Ownership

This workspace exclusively owns all files in:
```
~/Documents/GitHub/herbarium-specimen-tools/
```

**No overlaps** with:
- `~/devvyn-meta-project/` (meta-project)
- `~/Documents/pinned/active-projects/aafc-herbarium-dwc-extraction-2025/` (AAFC private)
- Any other sub-projects

**Exception**: WORKSPACE_BOUNDARIES.md (this file)
- Required for boundary compliance
- Must be unique per workspace
- Not shared/mirrored

---

## Tool Namespace

### Tools in This Workspace

**Scripts** (no conflicts with meta-project):
- `mobile/run_mobile_server.py` - Mobile API server
- `mobile/deploy-aws.sh` - AWS deployment
- `mobile/upload-data-to-s3.sh` - S3 data upload
- `mobile/generate_password_hash.py` - Password utility

**Future tools**:
- `scripts/analyze_specimens.py` - Analytics (planned)

**No naming conflicts** with meta-project tools:
- Meta-project: `bridge-*.sh`, `surface-*.sh`, `credential-*.sh`
- This repo: `run_*.py`, `deploy-*.sh`, `analyze_*.py`
- ✅ Clear separation

---

## Testing Responsibilities

### This Workspace Tests

**Owned code only**:
- Mobile PWA interface
- FastAPI backend
- Vue.js frontend
- Analytics utilities
- Example workflows

**Test location**: `tests/`
- Unit tests for Python code
- Integration tests for API
- Frontend tests (future)

**Not responsible for testing**:
- Meta-project coordination tools
- AAFC private pipeline
- External dependencies (FastAPI, Vue, etc.)

---

## Documentation Authority

### Single Source of Truth

**This workspace is authoritative for**:
| Concept | Authority | Location |
|---------|-----------|----------|
| Mobile PWA Interface | This repo | mobile/README.md |
| Mobile API | This repo | docs/api-reference.md |
| Analytics Tools | This repo | docs/analytics.md |
| Example Workflows | This repo | examples/workflows/ |
| Generic Herbarium Tools | This repo | README.md |

**Other workspaces are authoritative for**:
| Concept | Authority | Location |
|---------|-----------|----------|
| AAFC Pipeline | AAFC repo | aafc-herbarium-dwc-extraction-2025/README.md |
| Coordination Patterns | Meta-project | ~/devvyn-meta-project/knowledge-base/patterns/ |
| Bridge Protocol | Meta-project | ~/devvyn-meta-project/OPERATIONS_REFERENCE.md |

### Cross-References

**This repo may reference**:
- Meta-project patterns (read-only, link to source)
- AAFC project as example (anonymized case study)

**Other repos may reference**:
- This repo for mobile tools
- This repo for analytics utilities
- This repo for example workflows

---

## Pattern Contribution

### Upward Flow (This Repo → Meta-Project)

**May contribute**:
- Generic mobile PWA patterns
- FastAPI authentication patterns
- Offline-first design patterns
- Community contribution management

**Process**:
1. Identify reusable pattern in this repo
2. Document pattern locally
3. Propose extraction to meta-project
4. Meta-project generalizes and adds to knowledge base

### Downward Flow (Meta-Project → This Repo)

**May adopt**:
- Security patterns (credential management)
- Testing patterns
- Documentation standards
- Code quality practices

**Process**:
- This repo pulls patterns as needed
- Maintains autonomy
- Adapts patterns to public context

---

## Relationship to AAFC Repository

### Extraction History

**Origin**: Extracted from private AAFC herbarium digitization project
**Date**: 2025-12-01
**Reason**: Share generic tools with community while keeping AAFC data private

**What was extracted**:
- Mobile PWA interface (anonymized)
- Mobile API backend (generic)
- Analytics utilities (generic)
- Deployment scripts (generic)

**What remained private** (in AAFC repo):
- AAFC specimen data
- Institutional configurations
- Internal stakeholder communications
- Production pipeline specifics

### Current Relationship

**Independence**: Fully independent repositories
- This repo: Public, community-focused
- AAFC repo: Private, institution-specific

**Optional Integration**:
- AAFC repo MAY use this repo's tools
- Can install as dependency: `pip install git+https://github.com/devvyn/herbarium-specimen-tools.git`
- Can use as Git submodule
- Not required - AAFC has own desktop interface

**No Dependencies**:
- This repo does NOT depend on AAFC repo
- Standalone functionality
- Generic documentation
- Community contributions welcome

---

## Community Contributions

### Contribution Model

**Open Source**: MIT License
- Anyone can use, modify, distribute
- Commercial use allowed
- Attribution appreciated

**Accepting Contributions**:
- Bug reports via GitHub Issues
- Feature requests via GitHub Issues
- Pull requests welcome (see CONTRIBUTING.md)
- Community discussions

**Maintainer Authority**:
- @devvyn maintains repository
- Reviews and merges PRs
- Manages releases
- Moderates community

---

## Validation Checklist

**Before any commit, verify**:
- [ ] No AAFC-specific data included
- [ ] No credentials or API keys
- [ ] No institutional references (anonymized)
- [ ] Documentation is generic
- [ ] Examples use anonymized data
- [ ] No file path overlaps with meta-project or AAFC repo
- [ ] Code follows open source best practices
- [ ] Tests pass (when added)
- [ ] Linting passes (Ruff)

**Before publication**:
- [ ] All WORKSPACE_BOUNDARIES.md requirements met
- [ ] Service registered with meta-project
- [ ] AAFC repo updated to reference this repo
- [ ] Sample data is public domain or anonymized
- [ ] LICENSE file present (MIT)
- [ ] CONTRIBUTING.md complete
- [ ] README accurate and helpful

---

## Invariant Compliance

### INV-1: File Ownership Exclusivity
✅ No file exists in both this repo and meta-project or AAFC repo

### INV-2: Security Boundary Separation
✅ No SECRET data in this PUBLISHED workspace

### INV-3: Bidirectional References
⏳ Registered with meta-project (SERVICE_REGISTRY.md)
⏳ AAFC repo references this repo (to be updated)

### INV-4: Service Registration Protocol
⏳ Services registered with meta-project (in progress)

### INV-5: Tool Namespace Isolation
✅ No script name conflicts with meta-project tools

### INV-6: Testing Responsibility Clarity
✅ This workspace tests its own code

### INV-7: Documentation Authority
✅ Single source of truth for mobile tools and analytics

### INV-8: Pattern Contribution Flow
✅ Can contribute patterns upward to meta-project

### INV-9: Agent Session Isolation
✅ One agent session per workspace

---

## References

**Meta-Project**:
- [WORKSPACE_BOUNDARIES.md](~/devvyn-meta-project/WORKSPACE_BOUNDARIES.md)
- [SERVICE_REGISTRY.md](~/devvyn-meta-project/SERVICE_REGISTRY.md)

**AAFC Project**:
- [aafc-herbarium-dwc-extraction-2025](~/Documents/pinned/active-projects/aafc-herbarium-dwc-extraction-2025/)
- [REPO_SPLIT_STRATEGY.md](~/Documents/pinned/active-projects/aafc-herbarium-dwc-extraction-2025/REPO_SPLIT_STRATEGY.md)

**This Repository**:
- [README.md](./README.md) - Project overview
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Contribution guidelines
- [LICENSE](./LICENSE) - MIT License
- [mobile/README.md](./mobile/README.md) - Mobile interface guide

---

**Status**: Workspace boundaries defined, awaiting meta-project registration
**Compliance**: All invariants satisfied or in progress
**Security**: PUBLISHED - safe for public GitHub
