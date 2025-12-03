# Development Guide

Guide for contributing to herbarium-specimen-tools.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Documentation](#documentation)
- [Contributing](#contributing)

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- Basic understanding of FastAPI and Darwin Core

### Quick Start

**Using uv (recommended)**:
```bash
# Clone repository
git clone https://github.com/devvyn/herbarium-specimen-tools.git
cd herbarium-specimen-tools

# Create virtual environment and install with dev dependencies
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Run tests
pytest

# Start development server
python mobile/run_mobile_server.py --dev
```

**Using pip (traditional)**:
```bash
# Clone repository
git clone https://github.com/devvyn/herbarium-specimen-tools.git
cd herbarium-specimen-tools

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Start development server
python mobile/run_mobile_server.py --dev
```

---

## Development Setup

### Using uv (Recommended)

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Or use uv to run commands directly (no activation needed)
uv run pytest
uv run python mobile/run_mobile_server.py --dev
```

### IDE Setup

#### VS Code

Recommended extensions:
- Python
- Pylance
- Ruff
- Better Comments

Settings (`.vscode/settings.json`):
```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "none",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": true,
      "source.organizeImports": true
    },
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"]
}
```

#### PyCharm

1. Open project
2. Configure Python interpreter → Use virtual environment
3. Enable pytest as test runner
4. Install Ruff plugin
5. Enable "Reformat code on save"

---

## Project Structure

```
herbarium-specimen-tools/
├── src/                        # Source code
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   └── review/                # Review module
│       ├── __init__.py
│       ├── engine.py          # ReviewEngine core
│       ├── mobile_api.py      # FastAPI application
│       └── validators.py      # GBIF validation
├── mobile/                     # Mobile PWA interface
│   ├── index.html             # Main HTML
│   ├── manifest.json          # PWA manifest
│   ├── sw.js                  # Service worker
│   ├── css/                   # Stylesheets
│   ├── js/                    # JavaScript
│   └── run_mobile_server.py  # Server launcher
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── test_engine.py         # Engine tests
│   ├── test_validators.py    # Validator tests
│   ├── test_mobile_api.py    # API tests
│   └── integration/           # Integration tests
├── examples/                   # Sample data
│   └── sample_data/
│       ├── raw.jsonl          # Sample specimens
│       └── README.md
├── docs/                       # Documentation
│   ├── api-reference.md
│   ├── deployment.md
│   └── development.md
├── .github/                    # GitHub configuration
│   └── workflows/
│       └── ci.yml             # CI/CD pipeline
├── requirements.txt            # Dependencies
├── pytest.ini                  # Pytest configuration
├── README.md                   # Project overview
└── CONTRIBUTING.md             # Contribution guidelines
```

---

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Follow coding standards (see [Code Quality](#code-quality)).

### 3. Run Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_engine.py

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test
pytest tests/test_engine.py::TestReviewEngine::test_load_extraction_results
```

### 4. Format and Lint

```bash
# Auto-format code
ruff format src/ tests/

# Lint and auto-fix
ruff check src/ tests/ --fix

# Type check
mypy src/ --ignore-missing-imports
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat: Add feature description"
```

Commit message format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions/changes
- `refactor:` Code refactoring
- `style:` Formatting changes
- `chore:` Maintenance tasks

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

---

## Testing

### Test Organization

- `tests/test_engine.py` - ReviewEngine unit tests
- `tests/test_validators.py` - GBIF validator tests (mocked)
- `tests/test_mobile_api.py` - API endpoint tests
- `tests/integration/` - Integration tests (real GBIF API)

### Writing Tests

```python
import pytest
from src.review.engine import ReviewEngine, SpecimenReview

@pytest.fixture
def engine():
    """Create ReviewEngine instance."""
    return ReviewEngine(gbif_validator=None)

def test_calculate_quality_score(engine):
    """Test quality score calculation."""
    review = SpecimenReview(
        specimen_id="TEST-001",
        completeness_score=80.0,
        confidence_score=90.0,
    )

    review.calculate_quality_score()

    assert review.quality_score == pytest.approx(84.0)
```

### Test Coverage

Target: ≥70% coverage for critical paths

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Open report
open htmlcov/index.html
```

### Mocking External Services

Always mock GBIF API calls in unit tests:

```python
from unittest.mock import patch

@patch("src.review.validators.species")
def test_verify_taxonomy(mock_species, validator):
    mock_species.name_backbone.return_value = {
        "usageKey": 123456,
        "scientificName": "Artemisia frigida Willd.",
        "confidence": 95,
        "matchType": "EXACT",
    }

    # Test code here
```

---

## Code Quality

### Style Guide

- Follow PEP 8
- Use type hints
- Write docstrings for all public functions/classes
- Keep functions focused (single responsibility)
- Limit line length to 100 characters

### Type Hints

```python
from typing import List, Optional, Dict

def process_specimen(
    specimen_id: str,
    corrections: Optional[Dict] = None,
) -> SpecimenReview:
    """
    Process specimen with optional corrections.

    Args:
        specimen_id: Unique specimen identifier
        corrections: Optional field corrections

    Returns:
        Updated SpecimenReview object
    """
    pass
```

### Docstring Format

```python
def calculate_quality_score(completeness: float, confidence: float) -> float:
    """
    Calculate overall quality score.

    Quality score is a weighted combination of completeness (60%) and
    confidence (40%) scores.

    Args:
        completeness: Completeness score (0-100)
        confidence: Confidence score (0-1)

    Returns:
        Combined quality score (0-100)

    Example:
        >>> calculate_quality_score(80.0, 0.90)
        84.0
    """
    return (completeness * 0.6) + (confidence * 100 * 0.4)
```

### Code Review Checklist

Before submitting PR:
- [ ] All tests pass
- [ ] Coverage ≥70% for new code
- [ ] Code formatted with ruff
- [ ] No linting errors
- [ ] Type hints added
- [ ] Docstrings added/updated
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)

---

## Documentation

### Updating Documentation

When adding features:
1. Update `docs/api-reference.md` for API changes
2. Update `README.md` if changing usage
3. Add examples to relevant sections
4. Update docstrings in code

### Documentation Build

Documentation is written in Markdown and rendered by GitHub.

Preview locally:
```bash
# Install markdown renderer (optional)
pip install grip

# Render README
grip README.md
```

---

## Contributing

### First-Time Contributors

1. Read `CONTRIBUTING.md`
2. Look for "good first issue" labels
3. Ask questions in issue comments
4. Start with small changes

### Pull Request Process

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Ensure CI passes
5. Update documentation
6. Submit PR with clear description

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How were these changes tested?

## Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Self-review completed
```

---

## Debugging

### Development Mode

```bash
# Start with debug logging
python mobile/run_mobile_server.py --dev

# Access API docs
open http://localhost:8000/docs
```

### Common Issues

**Import Errors**:
```bash
# Ensure src/ is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Test Failures**:
```bash
# Run with verbose output
pytest -vv

# Show print statements
pytest -s

# Stop on first failure
pytest -x
```

**Type Errors**:
```bash
# Check specific file
mypy src/review/engine.py

# Ignore missing imports
mypy src/ --ignore-missing-imports
```

---

## Performance Profiling

### API Performance

```bash
# Install profiling tools
pip install py-spy

# Profile running server
py-spy record -o profile.svg -- python mobile/run_mobile_server.py --dev

# View profile
open profile.svg
```

### Memory Profiling

```bash
# Install memory profiler
pip install memory-profiler

# Add @profile decorator to functions
python -m memory_profiler your_script.py
```

---

## Release Process

1. Update version in `src/__init__.py`
2. Update `CHANGELOG.md`
3. Run full test suite
4. Create release branch: `release/v1.0.0`
5. Tag release: `git tag v1.0.0`
6. Push tag: `git push origin v1.0.0`
7. Create GitHub release
8. Update documentation

---

## Getting Help

- **Documentation**: Check `docs/` directory
- **API Reference**: `docs/api-reference.md`
- **Issues**: https://github.com/devvyn/herbarium-specimen-tools/issues
- **Discussions**: https://github.com/devvyn/herbarium-specimen-tools/discussions

---

## Resources

### Python & FastAPI
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [pytest Documentation](https://docs.pytest.org/)

### Darwin Core & GBIF
- [Darwin Core Standard](https://dwc.tdwg.org/)
- [GBIF API Documentation](https://www.gbif.org/developer/summary)
- [pygbif Documentation](https://pygbif.readthedocs.io/)

### Tools
- [Ruff Linter](https://github.com/astral-sh/ruff)
- [uv Package Manager](https://github.com/astral-sh/uv)
- [mypy Type Checker](http://mypy-lang.org/)

---

**Happy coding!** 🎉
