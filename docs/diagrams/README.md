# Architecture Diagrams

Visual documentation for the Herbarium Specimen Tools system architecture and workflows.

## Diagram Index

### Architecture

| Diagram | Description |
|---------|-------------|
| [System Overview](architecture/system-overview.md) | High-level architecture showing Mobile PWA, FastAPI backend, and data flow |
| [API Endpoints](architecture/api-endpoints.md) | REST API structure with authentication and HTMX partials |

### Modules

| Diagram | Description |
|---------|-------------|
| [Review Workflow](modules/review-workflow.md) | Complete review state machine including entrant workflow |
| [Mobile PWA](modules/mobile-pwa.md) | Progressive Web App architecture with offline sync |

## Diagram Conventions

### Status Colors

- **Green**: Completed/Approved states
- **Blue**: In-progress states
- **Yellow/Orange**: Pending/Warning states
- **Red**: Error/Rejected states

### Shape Conventions

- **Rectangles**: Processing components
- **Rounded rectangles**: User interface elements
- **Cylinders**: Data storage
- **Diamonds**: Decision points

## Rendering

These diagrams use [Mermaid](https://mermaid.js.org/) syntax. They render natively in:

- GitHub (README files, issues, PRs)
- VS Code (with Mermaid extension)
- Many documentation platforms (GitBook, Notion, etc.)

For local preview:
```bash
# Using mermaid-cli
npm install -g @mermaid-js/mermaid-cli
mmdc -i diagram.md -o diagram.png
```

## Related Documentation

- [API Reference](../api-reference.md) - Detailed endpoint documentation
- [Development Guide](../development.md) - Setup and contribution guidelines
- [Deployment Guide](../deployment.md) - Production deployment instructions
