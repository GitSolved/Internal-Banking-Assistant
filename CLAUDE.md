# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Internal Banking Risk & Compliance Assistant** (package name: `internal-assistant`) is a privacy-focused risk & compliance platform built on FastAPI and LlamaIndex. It runs 100% locally with no external API dependencies, designed for banking compliance officers, risk managers, and IT security teams to automate regulatory research, streamline compliance monitoring, and analyze security frameworks using the Llama 3.1 70B model.

**Note**: Repository is named `Internal-Banking-Assistant` but the Python package is `internal_assistant` (with underscore).

**Key Technologies:**
- Python 3.11.9+ (3.11.9 through 3.11.x supported)
- FastAPI (API layer)
- LlamaIndex (RAG pipeline)
- Gradio (Web UI)
- Ollama (LLM management) with Foundation-Sec-8B-q4_k_m
- HuggingFace (embeddings) with nomic-embed-text-v1.5
- Qdrant (vector store)

## Quick Reference

### Most Common Commands
```bash
# Run & Development
make run                    # Start app (port 8001) - auto-cleans logs
make dev                    # Dev mode with auto-reload
poetry run pytest tests/server/feeds/test_feeds_service.py::test_parse_feed -v  # Run single test

# Code Quality
make format                 # Format + lint (black, ruff)
make check                  # Full check: format + mypy + compatibility

# Data
make ingest path/to/docs   # Ingest documents
make stats                  # Database stats
```

### Full Command Reference

**Running:**
```bash
make run              # Start application (port 8001, auto log cleanup)
make dev              # Development mode with auto-reload
make production       # Production mode (port 8000, PGPT_PROFILES=production)
```

**Testing:**
```bash
make test                          # Run all tests
make test-coverage                 # Generate coverage report
poetry run pytest tests/ui/ -v    # Test specific directory
poetry run pytest tests/ui/test_ui.py::test_ui_creation -v  # Single test
poetry run pytest -m "not integration"  # Skip integration tests (CI default)
```

**Code Quality:**
```bash
make format           # Auto-format (black + ruff)
make mypy             # Type checking (strict mode, excludes tests)
make check            # Full quality check before commit
make compatibility-check  # Verify dependency versions
```

**Data Management:**
```bash
make ingest path/to/docs  # Ingest documents into RAG
make stats            # Database statistics
make analyze-models   # Analyze model files in models/
make wipe             # ⚠️ Delete all data (requires CONFIRM-WIPE)
```

**Documentation:**
```bash
poetry run mkdocs serve   # Serve docs at http://localhost:8000
make api-docs             # Generate OpenAPI spec
```

**Troubleshooting:**
```bash
poetry run verify-env              # Check Python version
make health-check                  # curl http://localhost:8001/health
ollama list                        # Verify models
poetry run python tools/maintenance/manage_logs.py --auto --keep-sessions 7
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
**14+ Security Feeds**: CISA KEV, US-CERT, NIST NVD, The Hacker News, Dark Reading, Bleeping Computer, Krebs on Security, SANS ISC, Talos Intelligence, Packet Storm

**Feed Architecture:**
- `RSSFeedService` - Singleton service bound in [di.py:13](internal_assistant/di.py#L13) (maintains feed cache)
- `BackgroundRefreshService` - Manages 60-minute refresh cycle via asyncio task
- Lifecycle managed in [launcher.py:41-75](internal_assistant/launcher.py#L41-L75) lifespan events
- API endpoints: [feeds_router.py](internal_assistant/server/feeds/feeds_router.py), [threat_intelligence_router.py](internal_assistant/server/threat_intelligence/threat_intelligence_router.py)

**Critical Design Pattern:**
The feed service MUST be a singleton to maintain cache consistency across requests. It's started during FastAPI lifespan startup, not at module import.

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

## Testing Architecture

### Test Organization & Fixtures
**Fixture System** ([conftest.py:14](tests/conftest.py#L14)):
- Auto-discovers fixtures from `tests/fixtures/[!_]*.py`
- Converts to pytest plugins dynamically
- Key fixtures:
  - `mock_injector` - Mocked dependency injection for isolated testing
  - `auto_close_qdrant` - Automatic Qdrant cleanup after tests
  - `ingest_helper` - Document ingestion utilities
  - `fast_api_test_client` - FastAPI test client with injector

**Test Structure:**
```
tests/
├── conftest.py              # Auto-discovery of fixtures
├── fixtures/                # Reusable test fixtures
├── server/                  # API endpoint tests (use mock_injector)
│   ├── feeds/              # Feed service tests
│   └── ingest/             # Ingestion tests
├── ui/                      # UI component tests (use ComponentRegistry mocks)
├── integration/             # Full stack tests (marked with @pytest.mark.integration)
└── components/              # Unit tests for core components
```

### Test Configuration
**Pytest settings** ([pyproject.toml:270-285](pyproject.toml#L270-L285)):
- `asyncio_mode = "auto"` - Auto-detects and runs async tests
- `--import-mode=importlib` - Resolves import issues with package structure
- Integration tests skipped by default in CI: `addopts = "-m 'not integration'"`
- Logs: `local_data/logs/pytest.log` (auto-rotated)

**Running Tests:**
```bash
poetry run pytest tests/server/feeds/test_feeds_service.py::test_parse_feed -v  # Single test
poetry run pytest tests/ui/ -v                          # Directory
poetry run pytest -m integration                        # Only integration tests
poetry run pytest --cov=internal_assistant --cov-report=html  # With coverage
```

## UI Architecture

### Modular UI System (44% code reduction from refactoring)
The UI uses a component-based architecture centered around three key systems:

**1. Component Registry Pattern** (`internal_assistant/ui/core/component_registry.py`)
- Centralized singleton registry manages all UI components
- Components register themselves on creation: `ComponentRegistry.register(name, component)`
- Access via `ComponentRegistry.get(name)` - enables loose coupling
- Lifecycle management: Components can be retrieved, replaced, or cleared

**2. Event Router Pattern** (`internal_assistant/ui/core/event_router.py`)
- Pub/sub event system for inter-component communication
- Subscribe: `EventRouter.subscribe(event_name, callback_function)`
- Publish: `EventRouter.publish(event_name, data)`
- Prevents tight coupling - components don't need direct references to each other
- Example: `ChatComponent` publishes "message_sent" event, `FeedComponent` subscribes to update context

**3. Service Facade Pattern** (`internal_assistant/ui/services/`)
- Clean abstraction layer between UI and FastAPI backend
- Each service class wraps API endpoints with simple methods
- Services handle HTTP requests, error handling, and response parsing
- Example: `FeedService.get_feeds()` wraps `/api/v1/feeds` endpoint

**UI Component Structure:**
```
internal_assistant/ui/
├── components/          # UI components
│   ├── chat/           # ChatComponent - inherits UIComponent
│   ├── documents/      # DocumentComponent
│   ├── feeds/          # FeedComponent
│   ├── sidebar/        # SidebarComponent
│   └── settings/       # SettingsComponent
├── core/               # Core infrastructure
│   ├── component_registry.py  # Singleton registry
│   ├── event_router.py         # Pub/sub events
│   └── base.py                 # UIComponent base class
├── services/           # API facades
│   ├── chat_service.py
│   ├── feed_service.py
│   └── ingest_service.py
└── ui.py              # Main UI assembly
```

**Component Lifecycle:**
1. Component inherits from `UIComponent` base class
2. Component builds Gradio UI in `build()` method
3. Component registers itself: `ComponentRegistry.register("chat", self)`
4. Component subscribes to events: `EventRouter.subscribe("feed_updated", self.refresh)`
5. Main UI (`ui.py`) retrieves components from registry and assembles layout

## Key Architectural Patterns

### Adding a New API Endpoint
**Pattern**: Router → Service → Dependency Injection
```python
# 1. Create service (internal_assistant/server/<feature>/<feature>_service.py)
class MyService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def do_work(self) -> Result:
        return process()

# 2. Create router (internal_assistant/server/<feature>/<feature>_router.py)
my_router = APIRouter(prefix="/api/v1/my-feature")

@my_router.get("/endpoint")
def my_endpoint(request: Request) -> Response:
    service = request.state.injector.get(MyService)
    return service.do_work()

# 3. Register in launcher.py
app.include_router(my_router)

# 4. Service auto-binds via injector (di.py) - no manual binding needed unless singleton required
```

### Adding a New UI Component
**Pattern**: Inherit UIComponent → Register → Subscribe to Events → Publish Events
```python
# internal_assistant/ui/components/myfeature/my_component.py
from internal_assistant.ui.core.base import UIComponent
from internal_assistant.ui.core.component_registry import ComponentRegistry
from internal_assistant.ui.core.event_router import EventRouter

class MyComponent(UIComponent):
    def build(self):
        # Subscribe to events from other components
        EventRouter.subscribe("data_updated", self._on_data_updated)

        # Build Gradio UI
        with gr.Column():
            self.output = gr.Textbox()
            self.button = gr.Button("Action")
            self.button.click(self._on_click, outputs=[self.output])

        # Register component
        ComponentRegistry.register("my_component", self)

    def _on_click(self):
        result = self._do_work()
        # Publish event for other components
        EventRouter.publish("my_event", {"data": result})
        return result
```

### Background Service Lifecycle Pattern
**RSS Feed Background Refresh** (60-minute intervals):
```python
# launcher.py lifespan pattern
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize singleton service from DI container
    feed_service = root_injector.get(RSSFeedService)  # Singleton bound in di.py
    background_service = BackgroundRefreshService(feed_service, refresh_interval_minutes=60)
    await background_service.start()  # Starts asyncio task

    yield  # App runs

    # Shutdown: Clean stop
    await background_service.stop()
```

**Key Points:**
- `RSSFeedService` is bound as singleton in `di.py` (maintains cache across requests)
- `BackgroundRefreshService` manages asyncio task lifecycle
- Service started in lifespan event, not at import time
- Graceful shutdown via asyncio task cancellation

### Configuration Override Pattern
**Three-Layer Configuration System:**
```
config/settings.yaml              # Base (always loaded)
↓
config/environments/local.yaml    # Environment override (via PGPT_PROFILES=local)
↓
config/model-configs/ollama.yaml  # Model-specific override
```

**Making Changes:**
1. Modify `config/settings.yaml` for base changes
2. Use `config/environments/{env}.yaml` for environment-specific overrides
3. Update `internal_assistant/settings/settings.py` schema if adding new fields
4. Restart app - configuration loaded once at startup

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
- **Why needed**: Gradio 4.15-4.38 has compatibility issues with Pydantic v2 (used by LlamaIndex)
- No manual intervention needed - patches applied silently on app startup

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

## Parallel Development Coordination

### Multi-Session Workflow
When multiple Claude Code sessions work in parallel, use branch-based isolation:

**Branch Strategy (Recommended):**
```bash
# Each session gets own branch
git checkout -b feature/add-authentication    # Session 1
git checkout -b fix/feed-parsing             # Session 2
git checkout -b docs/api-updates             # Session 3
```

**Component Isolation:**
- Session A: `internal_assistant/server/` (Backend)
- Session B: `internal_assistant/ui/` (Frontend)
- Session C: `tests/` (Testing)
- Session D: `docs/` (Documentation)

**Port Allocation for Parallel Testing:**
```bash
make run                              # Default port 8001
UVICORN_PORT=8002 poetry run python -m internal_assistant  # Session 2
UVICORN_PORT=8003 poetry run python -m internal_assistant  # Session 3
```

**Environment Isolation:**
```bash
PGPT_PROFILES=local poetry run make run   # Production data
PGPT_PROFILES=test poetry run make run    # Test data
PGPT_PROFILES=docker poetry run make run  # Docker environment
```

**Session Startup Checklist:**
1. `git pull origin main` - Sync with latest
2. `git checkout -b <feature-name>` - Create feature branch
3. `lsof -i :8001` - Check port availability
4. Document work in branch name or `WORK_LOG.md`

**Merge Strategy:**
```bash
git checkout main && git pull origin main
git checkout feature/your-feature
git rebase main  # Rebase on latest
git push origin feature/your-feature
gh pr create --title "Feature X" --body "Description"
```

**Critical Rules:**
- ✅ Use feature branches + PRs (not direct main commits)
- ✅ Divide work by components to avoid file conflicts
- ✅ Use `UVICORN_PORT` for parallel servers
- ✅ Use `PGPT_PROFILES` for data isolation
- ❌ Never share `local_data/` between sessions with different configs

## Security Notes

- **100% Local Processing**: No data sent to external services
- **Authentication**: Configurable via `server.auth.enabled` in settings.yaml
- **CORS**: Configured via `server.cors.*` settings
- **Privacy-First Design**: All models and data stored locally
- **Banking/Compliance Focus**: Designed for regulated environments (FDIC, SEC, NY DFS monitoring)
