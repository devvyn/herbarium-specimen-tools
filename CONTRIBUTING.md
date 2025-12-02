# Contributing to Herbarium Specimen Tools

Thank you for your interest in contributing! This project aims to provide generic, reusable tools for herbarium digitization workflows.

## Ways to Contribute

### 🐛 Report Bugs

Found a bug? Please [open an issue](https://github.com/devvyn/herbarium-specimen-tools/issues) with:
- Clear description of the problem
- Steps to reproduce
- Expected vs. actual behavior
- Your environment (OS, Python version, browser for mobile interface)

### 💡 Suggest Features

Have an idea? [Open an issue](https://github.com/devvyn/herbarium-specimen-tools/issues) with:
- Description of the feature
- Use case / why it's valuable
- Proposed implementation (if you have ideas)

### 📝 Improve Documentation

Documentation improvements are always welcome:
- Fix typos or unclear explanations
- Add examples or tutorials
- Improve API documentation
- Share your herbarium workflow

### 🔧 Code Contributions

**Before starting work on a feature:**
1. Check existing issues and PRs to avoid duplicates
2. For large features, open an issue first to discuss the approach
3. Fork the repository and create a feature branch

**Contribution workflow:**

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/herbarium-specimen-tools.git
cd herbarium-specimen-tools

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes
# ...

# Test your changes
python -m pytest tests/
ruff check .
ruff format .

# Commit
git add .
git commit -m "feat: Add your feature"

# Push
git push origin feature/your-feature-name

# Open pull request on GitHub
```

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- Modern web browser (for testing mobile interface)

### Local Setup

```bash
# Clone repository
git clone https://github.com/devvyn/herbarium-specimen-tools.git
cd herbarium-specimen-tools

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest ruff
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_mobile_api.py

# Run with coverage
pytest --cov=.
```

### Code Quality

We use Ruff for linting and formatting:

```bash
# Check code
ruff check .

# Fix auto-fixable issues
ruff check . --fix

# Format code
ruff format .
```

## Code Style

- Follow PEP 8 (enforced by Ruff)
- Use type hints where reasonable
- Write docstrings for public functions and classes
- Keep functions focused and testable
- Add tests for new features

### Example:

```python
def extract_darwin_core_field(
    specimen_data: dict,
    field_name: str,
    confidence_threshold: float = 0.7
) -> tuple[str | None, float]:
    """Extract a Darwin Core field from specimen data.

    Args:
        specimen_data: Raw specimen extraction data
        field_name: Darwin Core field name (e.g., 'scientificName')
        confidence_threshold: Minimum confidence to accept value

    Returns:
        Tuple of (field_value, confidence_score)
    """
    # Implementation...
    pass
```

## Pull Request Guidelines

### PR Title

Use conventional commits format:
- `feat: Add new feature`
- `fix: Fix bug in mobile interface`
- `docs: Update README`
- `test: Add tests for analytics`
- `refactor: Improve code structure`
- `chore: Update dependencies`

### PR Description

Include:
- What the PR does
- Why the change is needed
- How to test it
- Screenshots (for UI changes)
- Breaking changes (if any)

### Example PR:

```markdown
## Description
Add batch approval feature to mobile interface

## Motivation
Curators requested ability to approve multiple specimens at once for efficiency.

## Changes
- Added checkbox selection to review queue
- Added "Approve Selected" button
- Updated mobile API with batch endpoint
- Added tests for batch operations

## Testing
1. Start mobile server with sample data
2. Select multiple specimens
3. Click "Approve Selected"
4. Verify all selected specimens change to APPROVED status

## Screenshots
[Include screenshots]

## Breaking Changes
None
```

## Community Guidelines

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn
- Focus on the code, not the person
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md)

## Questions?

- Open a [GitHub Discussion](https://github.com/devvyn/herbarium-specimen-tools/discussions)
- Check existing issues and documentation
- Ask in your PR if unclear

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to the herbarium digitization community! 🌿
