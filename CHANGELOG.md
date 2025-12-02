# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Structured logging with JSON format support
- Request tracking middleware with unique request IDs
- Enhanced observability features

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

[Unreleased]: https://github.com/devvyn/herbarium-specimen-tools/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/devvyn/herbarium-specimen-tools/releases/tag/v0.1.0
