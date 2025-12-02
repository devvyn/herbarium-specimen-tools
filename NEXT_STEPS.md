# Next Steps for Herbarium Specimen Tools

**Created**: 2025-12-01
**Status**: Initial repository setup complete

---

## Completed ✅

- [x] Created repository structure
- [x] Extracted mobile PWA interface from private AAFC repo
- [x] Anonymized mobile interface (removed AAFC references)
- [x] Added MIT License
- [x] Created README.md with overview
- [x] Created CONTRIBUTING.md
- [x] Added requirements.txt
- [x] Initial commit

---

## TODO Before Publishing

### High Priority

- [ ] **Add sample data** (examples/sample_data/)
  - Create anonymized specimen JSONL examples
  - Find/create public domain herbarium images
  - Document data format

- [ ] **Test mobile interface** with sample data
  - Verify server starts correctly
  - Test on mobile device
  - Check all features work

- [ ] **Clean up mobile/** directory
  - Remove AAFC-specific docs (BRANCH_ASSESSMENT.md, PR_SUMMARY.md)
  - Review and anonymize any remaining institutional references
  - Keep only generic deployment docs

- [ ] **Create GitHub repository**
  - Create repo on GitHub: `herbarium-specimen-tools`
  - Push initial commit
  - Add description and topics
  - Enable Issues and Discussions

### Medium Priority

- [ ] **Extract analytics tools**
  - Copy analyze_with_duckdb.py from AAFC repo
  - Anonymize examples
  - Create docs/analytics.md guide

- [ ] **Create example workflows** (examples/workflows/)
  - Basic review workflow
  - Quality assessment pipeline
  - Field-based curation example

- [ ] **Improve documentation**
  - API reference (docs/api-reference.md)
  - Analytics guide (docs/analytics.md)
  - Deployment best practices
  - Troubleshooting guide

- [ ] **Add tests**
  - Unit tests for mobile API
  - Integration tests
  - Sample data validation tests

### Low Priority

- [ ] **Add badges to README**
  - CI/CD status (when set up)
  - Code coverage
  - Latest release

- [ ] **Set up GitHub Actions**
  - Linting (Ruff)
  - Testing (pytest)
  - Auto-formatting check

- [ ] **Create CODE_OF_CONDUCT.md**
  - Adopt standard code of conduct
  - Link from CONTRIBUTING.md

- [ ] **Add screenshots**
  - Mobile interface screenshots
  - Review queue
  - Specimen detail view
  - Add to README and mobile/README.md

- [ ] **Create CHANGELOG.md**
  - Version history
  - Release notes format

---

## Sample Data Requirements

### JSONL Format Example

```json
{
  "catalog_number": "EXAMPLE-001",
  "scientific_name": "Artemisia frigida Willd.",
  "confidence": 0.95,
  "event_date": "1969-08-14",
  "recorded_by": "Sample Collector",
  "locality": "Example Region",
  "state_province": "Example State",
  "country": "Example Country",
  "habitat": "Sample habitat description",
  "elevation": "450",
  "coordinates": {"lat": 50.0, "lon": -105.0},
  "image_sha256": "abc123...",
  "extraction_method": "gpt-4o-mini",
  "extraction_timestamp": "2025-01-15T10:30:00Z"
}
```

### Image Requirements

- Public domain or CC0 licensed
- Herbarium specimen labels (readable)
- Various quality levels (good, medium, poor)
- Different handwriting styles
- 5-10 sample images minimum

**Potential sources**:
- Biodiversity Heritage Library (BHL)
- iDigBio public specimens
- GBIF occurrence images with CC0 license
- Create synthetic examples with permission

---

## Cleanup Tasks

### Files to Remove from mobile/

- `BRANCH_ASSESSMENT.md` - AAFC-specific
- `PR_SUMMARY.md` - AAFC-specific
- `compare-branches.sh` - Development artifact
- Any other AAFC-specific docs

### Files to Review and Anonymize

- `AWS_DEPLOYMENT.md` - Check for institutional references
- `SECURITY.md` - Ensure generic
- `DESKTOP_VS_MOBILE.md` - Update references to desktop interface

---

## Publishing Checklist

Before making repository public:

- [ ] All AAFC references removed
- [ ] Sample data added and tested
- [ ] Mobile interface tested and working
- [ ] Documentation reviewed and complete
- [ ] LICENSE file present (MIT)
- [ ] README has clear quick start
- [ ] CONTRIBUTING guidelines clear
- [ ] No sensitive data or credentials
- [ ] All file paths are generic
- [ ] Screenshots added (optional but nice)

---

## GitHub Setup

### Repository Settings

**Name**: `herbarium-specimen-tools`
**Description**: Open-source tools for herbarium digitization workflows - mobile review interface and analytics utilities
**Website**: (optional - could host docs with GitHub Pages)
**Topics**: herbarium, digitization, darwin-core, biodiversity, gbif, specimen-management, pwa, mobile-interface, natural-history, museum-collections

**Settings**:
- Enable Issues
- Enable Discussions
- Enable Wiki (optional)
- Default branch: main
- License: MIT

### Initial Release

After testing and completing sample data:

1. Create GitHub release v0.1.0
2. Tag: `v0.1.0`
3. Title: "Initial Public Release"
4. Description: Highlight mobile PWA interface, link to docs
5. Attach any binary assets (if applicable)

---

## Integration with AAFC Repo

Once public repo is stable:

### In AAFC Repo (Private)

1. Remove mobile/ directory
2. Update README to reference public repo:
   ```markdown
   ## Mobile Interface

   For mobile specimen review, see the open-source
   [Herbarium Specimen Tools](https://github.com/devvyn/herbarium-specimen-tools)
   repository.
   ```
3. Can optionally use as Git submodule or pip dependency

### Benefits

- AAFC repo stays focused on production pipeline
- Mobile tools available to community
- Clear separation of private vs public
- Can accept community contributions to public repo

---

## Community Engagement

Once published:

- [ ] Announce on relevant forums/communities
- [ ] Share with herbarium digitization mailing lists
- [ ] Post on Twitter/social media with hashtags
- [ ] Submit to awesome lists (awesome-biodiversity, etc.)
- [ ] Create demo video (optional)
- [ ] Write blog post about the tools (optional)

---

## Maintenance Plan

**Regular tasks**:
- Respond to issues within 1-2 weeks
- Review and merge community PRs
- Update dependencies periodically
- Fix critical bugs promptly
- Add features based on community feedback

**Version strategy**:
- Semantic versioning (MAJOR.MINOR.PATCH)
- Breaking changes → major version bump
- New features → minor version bump
- Bug fixes → patch version bump

---

**Status**: Repository initialized, ready for cleanup and sample data
**Next Session**: Add sample data, clean up mobile/ directory, test interface
**Timeline**: 1-2 sessions to publication-ready
