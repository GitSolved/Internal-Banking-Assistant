# Development Setup Guide

This guide covers setting up the Internal Assistant project for development.

## Prerequisites

- **Python 3.11.9** (required for all dependencies)
- **Poetry 2.0+** (dependency management)
- **Git** (version control)

## Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd internal-assistant
```

### 2. Install Dependencies
```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
```

### 3. Setup Environment
```bash
# Copy environment template (if needed)
cp .env.example .env

# Install pre-commit hooks
poetry run pre-commit install
```

### 4. Run the Application
```bash
# Start the application
poetry run make run

# Or development mode with auto-reload
poetry run make dev
```

## Modern Poetry Workflow

This project uses Poetry 2.0+ with modern execution approach:

### Recommended Commands
```bash
# Start application (recommended)
poetry run make run

# Development mode
poetry run make dev

# Run tests
poetry run make test

# Interactive development
poetry env activate
make run
deactivate
```

### Deprecated Commands
- ❌ `poetry shell` (removed in Poetry 2.0+)
- ❌ `make run` without `poetry run` (won't work)

## Project Structure

```
internal-assistant/
├── internal_assistant/     # Main application code
├── config/                # Configuration files
│   ├── app/              # Core settings
│   ├── model-configs/    # Model configurations
│   ├── environments/     # Environment-specific configs
│   └── deployment/       # Deployment configs
├── data/                 # Application data
│   ├── runtime/          # Logs, cache, temp
│   ├── persistent/       # Storage, documents
│   └── models/           # Model files (future)
├── tools/                # Development tools
│   ├── maintenance/      # Maintenance scripts
│   └── system/           # System utilities
├── tests/                # Test suite
└── docs/                 # Documentation
```

## Configuration

### Environment Variables
- `PGPT_PROFILES`: Comma-separated list of profiles to load
- `PGPT_SETTINGS_FOLDER`: Override config directory path

### Local Development
```bash
PGPT_PROFILES=local poetry run make run
```

## Testing

### Run All Tests
```bash
poetry run make test
```

### Run Specific Tests
```bash
# Run server tests
poetry run pytest tests/server/

# Run UI tests
poetry run pytest tests/ui/

# Run with coverage
poetry run pytest --cov=internal_assistant
```

## Development Tools

### Code Quality
```bash
# Format code
poetry run black .

# Lint code
poetry run ruff check .

# Type checking
poetry run mypy internal_assistant/
```

### Pre-commit Hooks
The project uses pre-commit hooks for code quality:
- **Black**: Code formatting
- **Ruff**: Linting and import sorting
- **MyPy**: Type checking

### Utility Scripts
```bash
# Check compatibility
poetry run make compatibility-check

# Clean up logs
poetry run make log-cleanup

# Analyze models
poetry run make analyze-models
```

## Documentation Development

### MkDocs Local Development

The project uses **MkDocs** with Material theme for all documentation.

#### **Quick Start**
```bash
# Install docs dependencies (if not already installed)
poetry install --with docs

# Start live development server
poetry run mkdocs serve
# → Serves at http://localhost:8000
# → Auto-reloads on file changes
```

#### **Documentation Commands**
```bash
# Development server (recommended for editing)
poetry run mkdocs serve
# → Live preview with hot reload
# → Automatically rebuilds on save
# → Shows warnings and errors

# Build static site
poetry run mkdocs build
# → Generates site/ folder (3.7MB)
# → 21 HTML pages from markdown source
# → Full-text search index
# → Optimized assets

# Serve built site locally
poetry run mkdocs serve --dev-addr=8001
# → Test the built version
```

#### **Documentation Structure**
```
docs/                    # Source files (markdown)
├── user/               # User documentation
├── developer/          # Developer documentation  
├── api/                # API reference
└── assets/             # Images, logos

site/                   # Built website (git-ignored)
├── search/             # Search functionality (3MB index)
├── assets/             # Optimized CSS/JS/images  
└── *.html              # Generated HTML pages
```

#### **Writing Documentation**
```bash
# 1. Edit markdown files in docs/
vim docs/user/new-guide.md

# 2. Preview changes live
poetry run mkdocs serve

# 3. Add to navigation in mkdocs.yml
# 4. Build to verify
poetry run mkdocs build
```

#### **Documentation Features Available**
- **Material Design** theme with dark/light mode
- **Full-text search** with 25 language support
- **Code highlighting** with copy buttons
- **Mermaid diagrams** support
- **Admonitions** (notes, warnings, tips)
- **Tabs and collapsible sections**
- **Auto-generated navigation**

#### **Common Documentation Tasks**
```bash
# Check for broken links
poetry run mkdocs build 2>&1 | grep -i warning

# Verify all pages build correctly
poetry run mkdocs build --strict

# Check documentation size
du -sh site/

# Verify search index
ls -la site/search/search_index.json
```

#### **Important Notes**
- **site/ folder is git-ignored** - don't commit build output
- **Build time: ~4-5 seconds** for complete site
- **Search index: ~3MB** - enables fast full-text search
- **21 markdown files → 21 HTML pages** - perfect 1:1 conversion

## Troubleshooting

### Common Issues

#### Poetry Environment Issues
```bash
# Recreate virtual environment
poetry env remove python
poetry install
```

#### Dependency Conflicts
```bash
# Update dependencies
poetry update

# Check compatibility
poetry run make compatibility-check
```

#### Qdrant Lock Issues
```bash
# Clean up Qdrant locks
poetry run python tools/maintenance/cleanup_qdrant.py
```

### Getting Help

1. Check the [troubleshooting guide](../../user/installation/troubleshooting.md)
2. Review [configuration documentation](../../user/configuration/settings.md)
3. See the [architecture overview](../architecture/overview.md)

## Next Steps

- Review [architecture documentation](../architecture/overview.md)
- Explore [package structure](package-structure.md)
- Read [documentation guidelines](documentation-guidelines.md)
