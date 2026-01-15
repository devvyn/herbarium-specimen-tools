# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-01-15

### Added
- **Device Testing Harness** - Automated UI/UX testing across simulated devices
  - Tests iPhone 14, iPhone SE, Pixel 7, iPad Mini, Desktop Chrome
  - Captures screenshots, measures performance, checks accessibility
  - Generates JSON reports + markdown summaries in `tests/ui/findings/`
- **Image Scale Controls** - Segmented toolbar for image viewing
  - "Fit" mode: Scale to fit view
  - "1:1" mode: Native pixel resolution with scroll/pan
  - "⛶" Fullscreen mode with iOS pseudo-fullscreen fallback
- **Dataset Run Documentation** - Metrics from 2,885 specimen processing run
  - Quality distribution analysis
  - Priority classification breakdown
  - Lessons learned documented in `docs/DATASET_RUN_METRICS.md`

### Changed
- **Simplified Authentication** - Username-only auth with auto-login
  - Removed password requirement (network trust model for local/Tailscale)
  - Username saved to localStorage for session persistence
  - Reduces friction for curator workflows
- **Unified Server** - Mobile PWA now served from API server
  - Single port (8080) for both API and frontend
  - Added `start_review_server.sh` convenience script
- **Image Viewing UX** - Native mobile gestures
  - Replaced custom tap-to-zoom with native pinch gestures
  - Fixed image path resolution for filenames with extensions

### Fixed
- Image loading 401 errors - removed auth requirement from image endpoints
- bcrypt compatibility with Python 3.14 - replaced passlib with direct bcrypt
- Quality score formula - confidence now properly scaled from 0-1 to 0-100
- JWT error handling - use `jwt.InvalidTokenError` instead of `jwt.JWTError`
- Test suite stabilization - 52 tests passing

### Security
- Network trust model: Authentication simplified for local/Tailscale deployments
- Image endpoints no longer require JWT (appropriate for trusted networks)

## [0.1.0] - 2025-12-02

### Added

#### Phase 1: Functional Backend
- Complete backend implementation extracted from AAFC private repo
- `src/review/engine.py` - ReviewEngine for specimen workflow management
- `src/review/mobile_api.py` - FastAPI REST API with JWT authentication
- `src/review/validators.py` - GBIF validation using pygbif library
- `src/config.py` - Centralized configuration management
- Sample data (5 anonymized specimens) in `examples/sample_data/`
- Mobile PWA interface for touch-optimized review
- Security features: JWT auth, rate limiting, CORS, security headers

#### Phase 2: Essential Tooling
- Comprehensive test suite (870+ lines, ≥70% coverage target)
  - `tests/test_engine.py` - ReviewEngine unit tests
  - `tests/test_validators.py` - GBIF validation tests
  - `tests/test_mobile_api.py` - API endpoint tests
- CI/CD pipeline (`.github/workflows/ci.yml`)
  - Automated testing on every push/PR
  - Linting with ruff
  - Type checking with mypy
  - Multi-version Python support (3.11, 3.12)
- Complete documentation (1,460 lines)
  - `docs/api-reference.md` - API endpoint documentation
  - `docs/deployment.md` - Production deployment guide
  - `docs/development.md` - Contributor development guide
- `pytest.ini` - Test configuration with coverage requirements

#### Phase 3: Production Quality
- `SECURITY.md` - Comprehensive security policy
- `src/logging_config.py` - Structured JSON logging
- `src/middleware.py` - Request tracking and monitoring
- `.env.example` - Environment configuration template
- `CHANGELOG.md` - Version history tracking

### Changed
- Updated `requirements.txt` with all dependencies
- Enhanced README with project overview and quickstart

### Security
- JWT authentication with bcrypt password hashing
- Rate limiting on authentication endpoints
- Security headers (HSTS, XSS protection, frame options)
- Environment-based secret management
- CORS and trusted host configuration

## Project Milestones

### Phase 1: Make It Work (2025-12-02)
- **Goal**: Transform from "beautiful UI with no backend" to "actually functional"
- **Outcome**: Fully functional backend with mobile API
- **Added**: 1,618 lines of production code

### Phase 2: Essential Tooling (2025-12-02)
- **Goal**: Add tests, CI/CD, and documentation for production readiness
- **Outcome**: Comprehensive testing and documentation infrastructure
- **Added**: 870 lines of tests, 1,460 lines of documentation

### Phase 3: Production Quality (2025-12-02)
- **Goal**: Security hardening and observability
- **Outcome**: Enterprise-grade security and monitoring
- **Added**: Security policy, structured logging, request tracking

## Development Roadmap

### Completed
- [x] Phase 1: Functional Backend
- [x] Phase 2: Essential Tooling (Tests, CI/CD, Docs)
- [x] Phase 3: Production Quality (Security, Observability)

### Planned
- [ ] Phase 4: Community Excellence (Advanced docs, polish, v1.0.0 release)
- [ ] Sample images for examples
- [ ] Analytics module (DuckDB-based)
- [ ] Thumbnail generation
- [ ] Redis-based session storage
- [ ] Prometheus metrics endpoint
- [ ] Docker Hub image publication

## Version History

- **0.1.0** (2025-12-02): Initial public release
  - Complete backend implementation
  - Comprehensive test suite
  - Production-ready security
  - Full documentation

---

[Unreleased]: https://github.com/devvyn/herbarium-specimen-tools/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/devvyn/herbarium-specimen-tools/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/devvyn/herbarium-specimen-tools/releases/tag/v0.1.0
