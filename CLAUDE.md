# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Internal Banking Assistant** (package name: `internal-assistant`) is a privacy-focused cybersecurity intelligence platform built on FastAPI and LlamaIndex. It runs 100% locally with no external API dependencies, designed for banking, compliance, and security teams to automate risk monitoring, track vulnerabilities, and streamline regulatory research using the Foundation-Sec-8B model.

**Note**: Repository is named `Internal-Banking-Assistant` but the Python package is `internal_assistant` (with underscore).

**Key Technologies:**
- Python 3.11.9+ (3.11.9 through 3.11.x supported)
- FastAPI (API layer)
- LlamaIndex (RAG pipeline)
- Gradio (Web UI)
- Ollama (LLM management) with Foundation-Sec-8B-q4_k_m
- HuggingFace (embeddings) with nomic-embed-text-v1.5
- Qdrant (vector store)

## Essential Commands

### Running the Application
```bash
make run              # Start application (port 8001)
make dev              # Development mode with auto-reload
make production       # Production mode (port 8000, secure)
```

### Testing
```bash
make test             # Run all tests
make test-coverage    # Run tests with coverage report
poetry run pytest tests/server/feeds/  # Run specific test directory
poetry run pytest tests/ui/test_ui.py::test_name  # Run single test
```

### Code Quality
```bash
make format           # Format code (black + ruff)
make mypy             # Type checking
make check            # Full quality check (format + mypy + compatibility)
make compatibility-check  # Check dependency versions
```

### Data Management
```bash
make ingest path/to/docs  # Ingest documents into RAG
make stats            # Show database statistics
make analyze-models   # Analyze model files
make wipe             # Delete all data (requires confirmation)
```

### Documentation
```bash
poetry run mkdocs serve   # Serve docs at http://localhost:8000
poetry run mkdocs build   # Build static docs site
make api-docs         # Generate OpenAPI documentation
```

### Utility Tools
```bash
# Environment verification
poetry run verify-env        # Check Python version and dependencies

# Testing utilities
poetry run verify-tests      # Verify test fixes
poetry run test-safe         # Safe test runner

# Maintenance
poetry run python tools/maintenance/manage_logs.py --auto --keep-sessions 7
poetry run python tools/system/manage_compatibility.py --check
poetry run python tools/maintenance/analyze_models.py

# Data management
poetry run python tools/data/ingest_folder.py <path>
poetry run python tools/system/utils.py stats
poetry run python tools/system/utils.py wipe
```

## Architecture Overview

### Component Structure
```
internal_assistant/
├── components/       # Core components (LLM, embeddings, vector store)
│   ├── embedding/   # Embedding model implementations
│   ├── llm/         # LLM implementations
│   ├── vector_store/ # Vector store implementations
│   ├── node_store/  # Node storage implementations
│   └── ingest/      # Document ingestion pipeline
├── server/          # FastAPI API endpoints
│   ├── chat/        # Chat endpoints
│   ├── feeds/       # RSS/threat intelligence feeds
│   ├── ingest/      # Document ingestion API
│   ├── health/      # Health check endpoints
│   └── ...
├── ui/              # Gradio web interface
│   ├── components/  # UI components (chat, documents, feeds, sidebar, settings)
│   ├── core/        # Core UI infrastructure (component registry, event router)
│   ├── layout/      # Theme and layout management
│   ├── services/    # Service facades for API interaction
│   └── ui.py        # Main UI application
├── settings/        # Configuration management
└── di.py           # Dependency injection setup
```

### Dependency Injection Pattern
The application uses **Injector** for dependency injection:
- Global injector created in `di.py` via `create_application_injector()`
- All services bound as singletons (e.g., `RSSFeedService`)
- Request-scoped injector available via `request.state.injector`
- Access services in endpoints: `service = request.state.injector.get(ServiceClass)`

### Application Lifecycle
1. `internal_assistant/main.py` - Entry point that imports `app` from `launcher.py`
2. `internal_assistant/launcher.py` - Creates FastAPI app with `create_app(global_injector)`
3. `internal_assistant/di.py` - Sets up dependency injection container
4. Lifespan events manage background services (RSS feed refresh runs every 60min)
5. API routers and UI mounted via FastAPI

### Data Flow
- **Document Ingestion**: Upload → Text Extraction → Chunking → Embedding → Vector Storage (Qdrant)
- **Query Processing**: User Query → Embedding → Vector Search → Context Retrieval → LLM Response
- **Threat Intelligence**: RSS/Forum Feeds → Content Parsing → Threat Analysis → Dashboard

### RSS Feed Management
The application monitors 14+ security feeds including:
- **Government Sources**: CISA KEV, US-CERT, NIST NVD
- **Security News**: The Hacker News, Dark Reading, Bleeping Computer, Krebs on Security
- **Technical Sources**: SANS ISC, Talos Intelligence, Packet Storm

Feed service (`RSSFeedService`):
- Bound as singleton in dependency injection container
- Background refresh runs every 60 minutes via `BackgroundRefreshService`
- Managed in application lifespan events ([launcher.py:41-75](internal_assistant/launcher.py#L41-L75))
- Endpoints in [feeds_router.py](internal_assistant/server/feeds/feeds_router.py) and [threat_intelligence_router.py](internal_assistant/server/threat_intelligence/threat_intelligence_router.py)

## Import Conventions

**CRITICAL**: Always use full package imports. Never use relative imports or the old 'src' reference.

```python
# ✅ CORRECT
from internal_assistant.components.vector_store.vector_store_component import VectorStoreComponent
from internal_assistant.server.feeds.feeds_service import RSSFeedService
from internal_assistant.settings.settings import Settings
from internal_assistant.paths import local_data_path
from internal_assistant.di import global_injector

# ❌ WRONG - Don't use these patterns
from ..components.vector_store.vector_store_component import VectorStoreComponent  # No relative imports
from src.components.vector_store import VectorStoreComponent  # No 'src' reference
```

Package configuration in `pyproject.toml`:
```toml
packages = [{ include = "internal_assistant" }]
```

## Configuration Management

### Configuration Structure (Phase 2A)
```
config/
├── settings.yaml              # Base configuration (always loaded)
├── model-configs/
│   ├── foundation-sec.yaml   # Foundation-Sec model config
│   └── ollama.yaml           # Ollama-specific settings
├── environments/
│   ├── local.yaml            # Local development
│   ├── test.yaml             # Testing environment
│   └── docker.yaml           # Docker deployment
└── deployment/
    └── docker/               # Docker configs
```

**Active Configuration**:
- LLM: `llm.mode = ollama` (Foundation-Sec-8B-q4_k_m)
- Embeddings: `embedding.mode = huggingface` (nomic-embed-text-v1.5)
- Vector Store: `vectorstore.database = qdrant`
- Node Store: `nodestore.database = simple`
- Reranking: `rag.rerank.enabled = false` (disabled for performance)

Configuration loaded via `internal_assistant/settings/settings.py` using YAML files.

### Profile-Based Configuration
Use `PGPT_PROFILES` environment variable to load environment-specific configs:
```bash
# Local development
PGPT_PROFILES=local make run

# Testing
PGPT_PROFILES=test make test

# Production
PGPT_PROFILES=production make production

# Docker deployment
PGPT_PROFILES=docker docker-compose up
```

Loading order: `config/settings.yaml` → `config/environments/{profile}.yaml` → `config/model-configs/{profile}.yaml`

## Storage Directories

### Ephemeral Data (regenerable, safe to delete)
- `local_data/` - Runtime data: logs, session data, vector DB cache
  - `local_data/internal_assistant/qdrant/` - Vector database files
  - `local_data/logs/` - Application logs (auto-cleanup via `make log-cleanup`)

### Persistent Data (must preserve)
- `data/` - User data: models, documents, processed content
- `models/cache/` - Cached HuggingFace models

## Dependency Management

**Critical Version Requirements**:
- Python: >=3.11.9,<3.12.0 (3.11.9 through 3.11.x supported, validated on startup)
- FastAPI: >=0.108.0,<0.115.0 (Pydantic compatibility)
- Pydantic: >=2.8.0,<2.9.0 (LlamaIndex compatibility)
- Gradio: >=4.15.0,<4.39.0 (FastAPI integration compatibility)

**Poetry 2.0+ Usage**:
```bash
poetry install --extras "ui llms-ollama embeddings-huggingface vector-stores-qdrant"
poetry run <command>          # Run commands in virtual environment
```

**Active Dependencies** (currently used):
- `llama-index-llms-ollama` - LLM integration (Foundation-Sec via Ollama)
- `llama-index-embeddings-huggingface` - Embeddings (nomic-embed-text-v1.5)
- `llama-index-vector-stores-qdrant` - Vector storage
- `gradio` - Web UI framework
- `feedparser`, `aiohttp`, `beautifulsoup4` - RSS feed processing

## Testing Strategy

### Test Organization
```
tests/
├── conftest.py              # Pytest configuration
├── fixtures/                # Shared test fixtures
│   ├── mock_injector.py    # Mock dependency injection
│   ├── auto_close_qdrant.py # Qdrant cleanup
│   └── ingest_helper.py    # Ingestion test helpers
├── server/                  # API endpoint tests
│   ├── feeds/              # Feed service tests
│   ├── ingest/             # Ingestion tests
│   └── ...
├── ui/                      # UI component tests
├── integration/             # Full integration tests
└── components/              # Component unit tests
```

### Test Execution
```bash
# Run all tests
poetry run pytest tests -v

# Run specific test file
poetry run pytest tests/server/feeds/test_feeds_service.py -v

# Run single test function
poetry run pytest tests/ui/test_ui.py::test_ui_creation -v

# Run with coverage
poetry run pytest tests --cov=internal_assistant --cov-report=html
```

### Test Configuration (`pytest.ini_options` in `pyproject.toml`)
- Async mode: `asyncio_mode = "auto"`
- Import mode: `--import-mode=importlib`
- Logs saved to: `local_data/logs/pytest.log`

## UI Architecture

### Modular UI System (44% code reduction from refactoring)
The UI uses a component-based architecture with:
- **Component Registry**: Centralized component management
- **Event Router**: Decoupled event handling between components
- **Service Facades**: Clean API abstraction layer
- **Layout Manager**: Theme and layout configuration

### Key UI Components
- `ChatComponent` - Chat interface and message handling
- `DocumentComponent` - Document upload and management
- `FeedComponent` - RSS feed display and threat intelligence
- `SidebarComponent` - Navigation and settings
- `SettingsComponent` - Application configuration

### UI Development Pattern
Components inherit from `UIComponent` base class and register via `ComponentRegistry`. Events flow through `EventRouter` for loose coupling.

## Common Development Tasks

### Adding a New API Endpoint
1. Create router in `internal_assistant/server/<feature>/<feature>_router.py`
2. Define service in `internal_assistant/server/<feature>/<feature>_service.py`
3. Register router in `internal_assistant/launcher.py` via `app.include_router()`
4. Add tests in `tests/server/<feature>/`

### Adding a New UI Component
1. Create component in `internal_assistant/ui/components/<name>/`
2. Inherit from `UIComponent` base class
3. Register in `ComponentRegistry`
4. Wire events through `EventRouter`
5. Add tests in `tests/ui/`

### Modifying Configuration
1. Update base config in `config/settings.yaml`
2. Update settings schema in `internal_assistant/settings/settings.py`
3. Environment-specific overrides in `config/environments/<env>.yaml`
4. Restart application for changes to take effect

### Running Single Tests During Development
```bash
# Run specific test with verbose output
poetry run pytest tests/server/feeds/test_feeds_service.py::test_parse_feed -v -s

# Run all tests in a directory
poetry run pytest tests/ui/ -v

# Run with coverage for specific module
poetry run pytest tests/server/feeds/ --cov=internal_assistant.server.feeds
```

## Troubleshooting

### Common Issues

**"No module named 'internal_assistant'"**
```bash
poetry install  # Reinstall package
cd /path/to/internal-assistant && poetry run python -m internal_assistant
```

**Version mismatch errors on startup**
```bash
make compatibility-check  # Verify dependency versions
poetry install --sync     # Sync dependencies to pyproject.toml
```

**Qdrant lock file issues**
```bash
# Windows
cmd /c if exist "local_data\internal_assistant\qdrant\.lock" del /F "local_data\internal_assistant\qdrant\.lock"

# Linux/Mac
rm -f local_data/internal_assistant/qdrant/.lock
```

**Gradio/Pydantic schema errors**
The application automatically applies Gradio 4.x compatibility patches at startup:
- Patches `gradio.Blocks.recover_kwargs` to handle Pydantic v2 models
- Located in [launcher.py:115-142](internal_assistant/launcher.py#L115-L142)
- Applied automatically during FastAPI app creation
- No manual intervention needed

### Health Checks
```bash
make health-check  # Check if app is running (curl http://localhost:8001/health)
ollama list        # Verify Ollama models
make stats         # Check database statistics
```

## Code Quality Standards

### Formatting and Linting
- **Black**: Code formatting (target-version = py311)
- **Ruff**: Linting (pycodestyle, flake8, pydocstyle)
- **MyPy**: Type checking (strict mode, exclude tests)

### Conventions
- Use Google-style docstrings
- Type hints required (mypy strict mode)
- Absolute imports only (no relative imports)
- Ban relative imports via ruff configuration

### Pre-commit Workflow
```bash
make format  # Auto-format code
make mypy    # Type check
make test    # Run tests
make check   # Full quality check before commit
```

## CI/CD Pipeline

### GitHub Workflows
- **tests.yml** - Runs pytest on push/PR, enforces code quality
- **docs.yml** - Auto-deploys documentation to GitHub Pages on main branch
- **release-please.yml** - Automated version management and releases
- **stale.yml** - Manages stale issues and PRs

### Test Markers
Use pytest markers to categorize tests:
```bash
# Run only non-integration tests (default CI behavior)
poetry run pytest -m "not integration"

# Run integration tests (requires local Ollama, Qdrant)
poetry run pytest -m integration

# Run all tests
poetry run pytest tests
```

Integration tests are skipped in CI by default (`pytest.ini_options.addopts` in [pyproject.toml:270-272](pyproject.toml#L270-L272)).

## Key Files Reference

- `internal_assistant/main.py` - Application entry point
- `internal_assistant/launcher.py` - FastAPI app factory
- `internal_assistant/di.py` - Dependency injection setup
- `internal_assistant/settings/settings.py` - Configuration schema
- `config/settings.yaml` - Base configuration file
- `pyproject.toml` - Project metadata, dependencies, tool configs
- `Makefile` - Development commands
- `tests/conftest.py` - Pytest configuration

## Project History

### PrivateGPT Foundation
This project is built on the [PrivateGPT](https://github.com/zylon-ai/private-gpt) RAG framework (~30-40% code overlap) with extensive cybersecurity specialization:
- **Original License**: Apache 2.0 (maintained)
- **Original Authors**: Zylon AI
- **Custom Features**: ~48,000+ lines of cybersecurity-specific code including:
  - Foundation-Sec-8B integration
  - 14+ security RSS feeds with threat intelligence
  - MITRE ATT&CK framework integration
  - CVE tracking and monitoring
  - Custom security-focused UI

**Important**: When working with core RAG infrastructure (vector stores, embeddings, LLM components), be aware of the PrivateGPT foundation. Security features and threat intelligence are custom additions.

## Deployment

### Docker Deployment
```bash
cd config/deployment/docker
docker-compose up -d
```

Docker configurations:
- [Dockerfile.ollama](config/deployment/docker/Dockerfile.ollama) - Ollama-based deployment
- [Dockerfile.llamacpp-cpu](config/deployment/docker/Dockerfile.llamacpp-cpu) - CPU-only deployment
- [docker-compose.yaml](config/deployment/docker/docker-compose.yaml) - Multi-service orchestration
- [Modelfile](config/deployment/docker/Modelfile) - Ollama model configuration

Use `PGPT_PROFILES=docker` for Docker-specific settings.

## Security Notes

- **100% Local Processing**: No data sent to external services
- **Authentication**: Configurable via `server.auth.enabled` in settings.yaml
- **CORS**: Configured via `server.cors.*` settings
- **Privacy-First Design**: All models and data stored locally
- **Banking/Compliance Focus**: Designed for regulated environments (FDIC, SEC, NY DFS monitoring)
