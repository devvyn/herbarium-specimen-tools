# Herbarium Specimen Tools

**Open-source tools for herbarium digitization workflows**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/devvyn/herbarium-specimen-tools/workflows/CI/badge.svg)](https://github.com/devvyn/herbarium-specimen-tools/actions)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## Overview

Generic, reusable tools for reviewing and analyzing digitized herbarium specimens. Built to work with Darwin Core data from any herbarium digitization project.

**Tools Included**:
- 📱 **Mobile PWA Review Interface** - Touch-optimized specimen review for tablets and phones
- 📊 **Analytics Utilities** - DuckDB-based analysis for specimen data
- 📝 **Example Workflows** - Sample pipelines and usage patterns

---

## Features

### Mobile Review Interface

Progressive Web App for reviewing specimen extractions on mobile devices.

**Key Features**:
- Touch-optimized UI for tablets and phones
- Offline support for field work
- Darwin Core field editing
- GBIF validation display
- Priority-based workflow
- Image viewer with pinch-zoom
- JWT authentication with rate limiting
- Structured logging and request tracking

**Use Cases**:
- Field curation on tablets
- Mobile review during collection visits
- Remote specimen validation
- Offline data refinement

### Analytics Tools

DuckDB-based analysis for extracted specimen data.

**Key Features**:
- Field coverage analysis
- Confidence score distributions
- Quality assessment
- Bulk data exploration
- SQL-based queries over JSONL

**Use Cases**:
- Quality assessment of extraction runs
- Identifying low-confidence records
- Coverage analysis by field
- Model performance comparison

---

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/devvyn/herbarium-specimen-tools.git
cd herbarium-specimen-tools

# Install dependencies
pip install -r requirements.txt
# OR with uv (recommended):
# uv pip install -r requirements.txt
```

### Try with Sample Data

```bash
# Start mobile review server with included sample data
python mobile/run_mobile_server.py --dev

# Access the mobile interface
# Open http://localhost:8000 in your browser
# Default credentials (development only):
#   Username: testuser
#   Password: testpass123
```

**Note**: Sample data is included in `examples/sample_data/` but does not include images. The server will start successfully, but image viewing will fail until you add your own specimen images.

### Mobile Interface with Your Data

```bash
# Start mobile review server with your own data
python mobile/run_mobile_server.py \
  --extraction-dir path/to/extractions \
  --image-dir path/to/images \
  --port 8000

# Access from phone/tablet
# http://YOUR_IP:8000
```

See [mobile/README.md](mobile/README.md) for detailed setup.

### Analytics

```bash
# Run analysis on extraction data
python scripts/analyze_specimens.py \
  --input extractions/raw.jsonl \
  --analysis coverage

# Available analyses:
# - coverage: Field coverage statistics
# - confidence: Confidence score distributions
# - quality: Quality issue detection
```

See [docs/analytics.md](docs/analytics.md) for examples.

---

## Documentation

- **[Mobile Interface Guide](mobile/README.md)** - Setup and usage
- **[Analytics Guide](docs/analytics.md)** - Data analysis examples
- **[Example Workflows](examples/workflows/)** - Sample pipelines
- **[API Reference](docs/api-reference.md)** - Developer documentation

---

## Requirements

- Python 3.11 or higher
- Modern web browser (for mobile PWA)
- Optional: DuckDB for analytics (installed via pip)

---

## Use Cases

### Herbarium Digitization Projects

Use these tools to:
- Review extracted specimen data on mobile devices
- Analyze extraction quality and coverage
- Validate Darwin Core field mapping
- Refine data in the field

### Research Workflows

- Field data validation during collection trips
- Quality assessment of batch extractions
- Coverage analysis for publication planning
- Confidence-based prioritization

---

## Examples

### Sample Data

The `examples/sample_data/` directory includes anonymized sample specimens for testing:

```bash
# Test mobile interface with samples
python mobile/run_mobile_server.py \
  --extraction-dir examples/sample_data \
  --image-dir examples/sample_data/images

# Test analytics with samples
python scripts/analyze_specimens.py \
  --input examples/sample_data/raw.jsonl
```

### Workflows

See `examples/workflows/` for:
- Basic review workflow
- Quality assessment pipeline
- Field-based curation example

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Ways to Contribute**:
- Report bugs and request features via [GitHub Issues](https://github.com/devvyn/herbarium-specimen-tools/issues)
- Submit pull requests for improvements
- Share your herbarium digitization workflows
- Improve documentation

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

**In short**: Free to use, modify, and distribute. Commercial use allowed. Attribution appreciated.

---

## Related Projects

This toolkit was extracted from a production herbarium digitization project and generalized for community use. The tools have been used successfully for reviewing thousands of specimen extractions.

**Other Herbarium Tools**:
- [GBIF IPT](https://www.gbif.org/ipt) - Data publication platform
- [Symbiota](https://symbiota.org/) - Collection management
- [iNaturalist](https://www.inaturalist.org/) - Field identification

---

## Support

- **Issues**: [GitHub Issues](https://github.com/devvyn/herbarium-specimen-tools/issues)
- **Discussions**: [GitHub Discussions](https://github.com/devvyn/herbarium-specimen-tools/discussions)
- **Documentation**: [docs/](docs/)

---

## Acknowledgments

These tools were developed during a herbarium digitization project at a regional research institution. Anonymized and released as open source to benefit the wider herbarium community.

**Technologies Used**:
- FastAPI - Mobile API backend
- Vue.js - Mobile UI framework
- DuckDB - Analytics engine
- Darwin Core - Data standard

---

**Status**: Active Development
**Version**: 0.1.0 (Initial Release)
**Maintained by**: [@devvyn](https://github.com/devvyn)
