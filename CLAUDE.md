# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Internal Assistant is a cybersecurity intelligence platform built on PrivateGPT technology. It provides local, privacy-focused AI for threat analysis and security research using the Foundation-Sec-8B model via Ollama.

## Essential Commands

**Note:** This project uses Poetry 2.0+ with modern `poetry run` execution. The deprecated `poetry shell` command is no longer available.

### Development
```bash
# Start the application
poetry run make run

# Development mode with auto-reload
poetry run make dev
poetry run make dev-windows  # Windows-specific development mode

# Interactive development (alternative)
poetry env activate          # Activate environment
make run                     # Run commands directly
deactivate                   # Deactivate when done

# Run tests
poetry run make test

# Run specific test file
poetry run pytest tests/path/to/test_file.py -v

# Run specific test directory
poetry run pytest tests/ui/

# Run tests with coverage
poetry run make test-coverage

# Run a single test by name
poetry run pytest -k "test_name" -v
```

### Code Quality
```bash
# Format code (black + ruff)
poetry run make format

# Type checking
poetry run make mypy

# Full quality check (format + mypy + compatibility)
poetry run make check

# Check dependency compatibility
poetry run make compatibility-check

# Security validation
poetry run make security-check
```

### Utilities
```bash
# Clean up old logs (keeps 7 most recent)
poetry run make log-cleanup

# Analyze model files for duplicates
poetry run make analyze-models

# Generate API documentation
poetry run make api-docs

# Database statistics
poetry run make stats

# Production mode (secure, no debug)
poetry run make production
```

## Critical Dependency Constraints

This project has **strict version requirements** that are automatically validated on startup:

- **Python**: 3.11.9 (exact version)
- **FastAPI**: >=0.108.0,<0.115.0
- **Pydantic**: >=2.8.0,<2.9.0
- **Gradio**: >=4.15.0,<4.39.0

**Never modify these version constraints** without comprehensive testing. Violations will cause Pydantic schema generation errors and FastAPI integration issues.

## Architecture Overview

### Project Structure
```
internal_assistant/
├── components/       # Core AI components (LLM, embeddings, vector store)
├── server/          # FastAPI routers and services
│   ├── chat/        # Chat endpoint and service
│   ├── feeds/       # RSS and threat intelligence feeds
│   ├── ingest/      # Document ingestion
│   └── threat_intelligence/  # MITRE ATT&CK integration
├── ui/              # Gradio web interface
│   ├── components/  # Modular UI components (Phase 1+ refactoring)
│   ├── core/        # Core UI utilities
│   └── services/    # UI service layer
├── settings/        # Configuration management
└── utils/           # Shared utilities

config/              # Configuration files (Phase 2A restructure)
├── app/            # Core settings (settings.yaml, settings_backup.yaml)
├── environments/   # Environment-specific configs (local.yaml, test.yaml, docker.yaml)
├── model-configs/  # Model-specific configurations (ollama.yaml, foundation-sec.yaml, etc.)
└── deployment/     # Deployment configs (docker/, development/)

tests/              # Test suite
├── fixtures/       # Test fixtures and helpers
├── server/         # API endpoint tests
└── ui/             # UI component tests
```

### Feed & Threat Intelligence Architecture
Understanding the feed system requires reading multiple files:

**Feed Processing Pipeline:**
1. **Feed Storage & Parsing** (`feeds_service.py`): RSS parsing, feed storage, metadata management
2. **Background Updates** (`background_refresh.py`): Scheduled feed refreshing using FastAPI BackgroundTasks
3. **Forum Scraping** (`forum_parser.py`): Custom parser for security forums (handles non-standard RSS)
4. **Directory Service** (`forum_directory_service.py`): Forum feed discovery and management

**Threat Intelligence Integration:**
- **MITRE ATT&CK Service** (`mitre_attack_service.py`): ATT&CK framework API integration
- **Threat Analyzer** (`threat_analyzer.py`): Cross-references threats with MITRE tactics/techniques
- **Routers**: Separate FastAPI routers for feeds, forums, and threat intelligence endpoints

**Key Integration Point:** The `background_refresh_service()` in `background_refresh.py` orchestrates all automated feed updates.

### Key Components

**LLM Stack:**

**REQUIRED (Always Installed):**
- ✅ LLM: `llama-index-llms-ollama` with Foundation-Sec-8B-q4_k_m.gguf
- ✅ Embeddings: `llama-index-embeddings-huggingface` with nomic-embed-text-v1.5
- ✅ Vector Store: `llama-index-vector-stores-qdrant` (local disk-based)
- ✅ UI: `gradio` web interface (v4.15.0-4.39.0)

**USED BUT OPTIONAL:**
- `llama-index-llms-llama-cpp`: Model file management and settings
- `llama-index-llms-openai-like`: OpenAI-compatible API support

**NOT USED (Available but not configured):**
- Other vector stores: Chroma, PostgreSQL, ClickHouse, Milvus
- Other LLMs: OpenAI, Azure OpenAI, Google Gemini, AWS Sagemaker
- Other embeddings: OpenAI, Azure, Gemini, Sagemaker, Ollama embeddings
- PostgreSQL nodestore (using simple nodestore instead)
- Reranking: Disabled in settings.yaml for performance

**Installation Command:**
```bash
poetry install --extras "ui llms-ollama embeddings-huggingface vector-stores-qdrant"
```

**High-Level Architecture:**
The application follows a layered architecture with dependency injection:

1. **FastAPI Layer** ([internal_assistant/launcher.py](internal_assistant/launcher.py)): Creates the app, registers all routers
   - Application created via `create_app(root_injector)` function
   - **Lifecycle management** (launcher.py:44-73):
     - `@asynccontextmanager` lifespan function controls startup/shutdown
     - Startup: Initializes BackgroundRefreshService for RSS feeds (60-minute interval)
     - Shutdown: Gracefully stops background service
   - All routers registered in launcher.py:80-93
   - Injector attached to each request via `request.state.injector` (launcher.py:75-76)
   - **Gradio compatibility patches** applied automatically (launcher.py:113-144):
     - Boolean schema handling fix for gradio_client
     - Pydantic compatibility configuration
     - GRADIO_ANALYTICS_ENABLED set to "False"

2. **Router Layer** ([internal_assistant/server/*/](internal_assistant/server/)): Each module has its own router defining API endpoints
   - All routers registered in launcher.py:80-93
   - Core: completions, chat, chunks, ingest, embeddings, summarize
   - Intelligence: feeds, simple_forum, threat_intelligence, mitre_attack
   - System: health, system, metadata, status
   - Example: [chat_router.py](internal_assistant/server/chat/chat_router.py), [feeds_router.py](internal_assistant/server/feeds/feeds_router.py)
   - Health endpoint: [health_router.py](internal_assistant/server/health/health_router.py) provides `/health` for monitoring

3. **Service Layer** ([internal_assistant/server/*/*_service.py](internal_assistant/server/)): Business logic, injected as singletons
   - Services implement core business logic and are bound in di.py
   - Singletons: RSSFeedService, SimpleForumDirectoryService (maintain cache across requests)
   - Example: [chat_service.py](internal_assistant/server/chat/chat_service.py), [ingest_service.py](internal_assistant/server/ingest/ingest_service.py)

4. **Component Layer** ([internal_assistant/components/](internal_assistant/components/)): Core AI components (LLM, embeddings, vector store)

5. **UI Layer** ([internal_assistant/ui/](internal_assistant/ui/)): Gradio interface that interacts with the FastAPI backend
   - Created via dependency injection: `root_injector.get(InternalAssistantUI)` (launcher.py:154)
   - Mounted at `settings.ui.path` when `settings.ui.enabled` is true (launcher.py:159)
   - Gradio compatibility patches applied automatically (launcher.py:113-143)

**Dependency Injection Flow:**
- Container: [internal_assistant/di.py](internal_assistant/di.py) creates the global injector
- Services are bound as singletons (e.g., RSSFeedService, SimpleForumDirectoryService)
- The injector is attached to each request via `request.state.injector` in launcher.py
- Access injector in routers: `injector = request.state.injector`

**Configuration System:**
- **Primary config**: [config/settings.yaml](config/settings.yaml) (default profile at root of config/)
- Settings class: [internal_assistant/settings/settings.py](internal_assistant/settings/settings.py)
- Loader: [internal_assistant/settings/settings_loader.py](internal_assistant/settings/settings_loader.py)
- Override via `PGPT_PROFILES` env var (e.g., `PGPT_PROFILES=local,test`)
- Phase 2A restructure: Additional specialized configs in subdirectories
  - [config/environments/](config/environments/): local.yaml, test.yaml, docker.yaml
  - [config/model-configs/](config/model-configs/): ollama.yaml, foundation-sec.yaml, openai.yaml, gemini.yaml, etc.
  - [config/deployment/](config/deployment/): docker/, development/
  - [config/app/](config/app/): settings_backup.yaml

**Important Configuration Values:**
- RAG settings: `similarity_top_k: 8`, `similarity_value: 0.1` (optimized for document coverage)
- LLM settings: `max_new_tokens: 1000`, `context_window: 8192` (optimized for large responses)
- These values are optimized for cybersecurity intelligence workflows
- Always check `config/settings.yaml` for current values before troubleshooting

## Important Patterns

### Package Imports
Always use absolute imports from the `internal_assistant` package:
```python
# Correct
from internal_assistant.components.llm import LLMComponent
from internal_assistant.server.chat.chat_service import ChatService

# Incorrect
from components.llm import LLMComponent
from ..server.chat import ChatService
```

### Testing
- Tests use `pytest` with async support (`asyncio_mode = "auto"`)
- Fixtures in `tests/fixtures/` provide mock injectors and helpers
- Use `tests/fixtures/mock_injector.py` for dependency injection in tests
- Test environment automatically uses `test` profile from `config/environments/test.yaml`

### Configuration
**File Structure (Phase 2A completed):**
```
config/
├── settings.yaml              # ⭐ PRIMARY config file (default profile, at root)
├── app/                       # Core application settings
│   └── settings_backup.yaml   # Backup copy
├── environments/              # Environment-specific configs
│   ├── local.yaml             # Local development overrides
│   ├── test.yaml              # Test environment
│   └── docker.yaml            # Docker deployment
├── model-configs/             # Model-specific configurations
│   ├── ollama.yaml            # Ollama settings
│   ├── foundation-sec.yaml    # Foundation-Sec model config
│   ├── openai.yaml            # OpenAI config (not currently used)
│   ├── gemini.yaml            # Gemini config (not currently used)
│   └── sagemaker.yaml         # Sagemaker config (not currently used)
└── deployment/                # Deployment configs
    ├── docker/                # Docker configuration
    │   └── docker-compose.yaml
    └── development/           # Development-specific
        └── pre-commit-config.yaml
```

**Python Module:**
- Settings class: `internal_assistant/settings/settings.py` (untouched for stability)
- Config loading: `internal_assistant/settings/settings_loader.py`

**Environment Variables:**
- Prefixed with `PGPT_` (e.g., `PGPT_PROFILES`, `PGPT_LOG_LEVEL`)
- `HF_TOKEN`: HuggingFace token for embedding models (optional but recommended)
- `GRADIO_ANALYTICS_ENABLED`: Set to "False" by default (launcher.py:141)
- Example: `PGPT_PROFILES=local,test` to merge multiple profiles

### Logging
- Session-based logs in `local_data/logs/SessionLogN.log`
- Automatic cleanup keeps 7 most recent sessions
- Log level: Controlled by `PGPT_LOG_LEVEL` env var (default: INFO)

### UI Refactoring (Phase 1-3 Substantially Complete)
The UI has been successfully modularized from a monolithic `ui.py` file:
- **Phase 1A**: ✅ Chat interface extraction (completed)
- **Phase 1B**: ✅ Document management extraction (1,963 lines, completed)
- **Phase 1C**: ✅ Feed handlers extraction (completed)
- **Phase 1D**: ✅ Settings, sidebar, and core utilities (completed)

**Progress Summary:**
- Original `ui.py`: ~6,258 lines
- Current `ui.py`: **3,515 lines** (44% reduction achieved!)
- Components extracted: Chat, Documents, Feeds, Settings, Sidebar
- All extracted components: <600 lines each for maintainability

**⚠️ Important: Working with UI Code**
- Prefer working with modular components in `internal_assistant/ui/components/` when available
- Use `Read` with specific line ranges when reading `ui.py`: `offset` and `limit` parameters
- Use `Grep` to find specific patterns/functions before reading
- Each modular component is <600 lines and follows the builder pattern

When working on UI code:
1. Check `internal_assistant/ui/components/` for existing modular components
2. Follow the builder pattern used in existing components
3. Create strategic backups before major changes if refactoring further

## Storage Structure

Two distinct storage directories with different purposes:

**`local_data/`** - Ephemeral application runtime data (regenerable):
- Logs, session data, vector database cache
- Can be safely deleted and regenerated

**`data/`** - Critical persistent user data (must preserve):
- Models, documents, processed content
- Expensive to recreate, requires backup

## Development Workflows

### Adding a New API Endpoint
1. Create router in `internal_assistant/server/<module>/<module>_router.py`
2. Create service in `internal_assistant/server/<module>/<module>_service.py`
3. Bind service in `internal_assistant/di.py` if it needs singleton scope
4. Register router in `internal_assistant/launcher.py:79-92`
5. Add tests in `tests/server/<module>/`

### Adding a New UI Component
1. Create component in `internal_assistant/ui/components/<category>/`
2. Follow the builder pattern (see chat/chat_component.py or documents/)
3. Import and integrate in `internal_assistant/ui/ui.py`
4. Add tests in `tests/ui/`

### Running with Different Profiles
```bash
# Use local environment config
PGPT_PROFILES=local poetry run make run

# Use multiple profiles (merged in order)
PGPT_PROFILES=default,local poetry run make run
```

## Tools Directory

The `tools/` directory contains maintenance and utility scripts organized by category. See [tools/README.md](tools/README.md) for complete documentation.

**Categories:**
- **Maintenance** (`tools/maintenance/`): Cleanup, log management, model optimization
- **System** (`tools/system/`): Configuration, compatibility checking, monitoring
- **Data** (`tools/data/`): Document ingestion and data processing
- **Development** (`tools/development/`): Testing and debugging utilities
- **Analysis** (`tools/analysis/`): Dependency analysis, code metrics
- **Performance** (`tools/performance/`): Profiling and benchmarking
- **Storage** (`tools/storage/`): Database admin and recovery operations
- **Javascript** (`tools/Javascript/`): **[PRODUCTION DEPENDENCY]** - UI module management

**⚠️ Important**: The `Javascript/` directory is imported by `ui.py` and cannot be modified without breaking the UI.

**Usage Pattern:**
```bash
# 1. ALWAYS prefer Makefile commands when available (most common case)
make compatibility-check    # ✅ Use this (cleaner, validated)
make log-cleanup           # ✅ Use this (automatic, safe)
make test                  # ✅ Use this (configured correctly)
make format                # ✅ Use this (black + ruff)

# 2. Direct tool usage ONLY when:
#    - No Makefile equivalent exists
#    - You need specific tool arguments not exposed in Makefile
#    - You're debugging a specific tool
poetry run python tools/<category>/<script>.py

# Examples of direct tool usage:
poetry run python tools/storage/storage_admin.py diagnose       # Storage diagnostics
poetry run python tools/data/ingest_folder.py /path/to/docs    # Custom ingestion
poetry run python tools/maintenance/manage_logs.py --interactive  # Interactive mode

# 3. Check available Makefile commands first
make list                  # Shows all available commands
```

**Common Makefile Commands:**
- `make run`: Start application (includes automatic log cleanup)
- `make test`: Run test suite
- `make format`: Format code (black + ruff)
- `make check`: Full quality check (format + mypy + compatibility)
- `make compatibility-check`: Verify dependency versions
- `make log-cleanup`: Clean old logs (keeps 7 most recent)
- `make analyze-models`: Check for duplicate model files
- `make production`: Start in production mode (secure)

## Troubleshooting

### Common Issues

**Pydantic/FastAPI schema errors:**
- Verify dependency versions match constraints in `pyproject.toml`
- The application includes automatic Gradio compatibility patches (launcher.py:113-143)
- Patches applied: boolean schema handling fix + Pydantic compatibility configuration

**Import errors:**
- Ensure using absolute imports from `internal_assistant` package
- Never use relative imports like `from ..server.chat import ChatService`

**Test failures:**
- Check that test environment is properly configured with `config/environments/test.yaml`
- Verify pytest is using `asyncio_mode = "auto"` (configured in pyproject.toml)

**UI not loading:**
- Verify Gradio is installed: `poetry install --extras ui`
- Check logs for Gradio compatibility patch status
- Ensure `settings.ui.enabled: true` in config/settings.yaml

**Model not found:**
- Ensure Ollama is running: `ollama list`
- Verify Foundation-Sec-8B model exists: should show `foundation-sec-q4km:latest`
- Check model file path in config: `ollama.llm_model: foundation-sec-q4km:latest`

**Windows-specific:**
- Use `poetry run make dev-windows` for development mode
- Path separators are handled automatically by Python pathlib

**Feed refresh not working:**
- Background service starts during app lifespan (launcher.py:44-71)
- Verify `RSSFeedService` is bound as singleton in di.py:13
- Check logs for "🚀 Starting background RSS feed refresh service" entries
- Default refresh interval: 60 minutes (configurable in launcher.py:54)

**Document not appearing after upload:**
Two storage systems must both be updated:
1. **Qdrant vector store**: Check `local_data/internal_assistant/qdrant/` directory exists
2. **DocStore index**: Check logs for "ingest_service.py" entries showing successful indexing
3. **Debug path**: Read `ingest_service.py:ingest()` method to see where process fails

**"Clear All Documents" connection errors:** Three potential causes and fixes:

1. **Missing Qdrant collection**: If document deletion fails with "Collection not found":
   ```bash
   # Recreate collection by adding a test document
   curl -X POST http://localhost:8001/v1/ingest/text \
     -H "Content-Type: application/json" \
     -d '{"file_name": "test.txt", "text": "test"}'
   ```

2. **SIGALRM health check failures on Windows**: Fixed in `chat_service_facade.py` by replacing Unix-specific signal handling with `ThreadPoolExecutor` timeout.

3. **Gradio queue 422 errors**: Caused by malformed JavaScript event handlers. Use standard Gradio event binding without custom JS confirmation dialogs.

**Health check timeouts:** The application uses cross-platform timeout mechanisms. If you see "Chat service health check timed out", this is normal and doesn't affect functionality.

**MITRE ATT&CK data not loading:**
- Service fetches from public MITRE ATT&CK API (requires internet connection)
- Check `mitre_attack_service.py` for API endpoint configuration
- Verify no firewall blocking https://raw.githubusercontent.com (MITRE data source)
- Check logs for "mitre_attack" entries to see connection errors

**Test failures with embedding dimension errors:**
- **Symptom**: `ValueError: could not broadcast input array from shape (384,) into shape (768,)`
- **Root cause**: Mock embeddings were hardcoded to 384 dimensions while production uses 768 (nomic-embed-text-v1.5)
- **Fixed in**: `internal_assistant/components/embedding/embedding_component.py:148-152`
- **Solution**: Mock embeddings now dynamically use `settings.embedding.embed_dim` from config
- **Impact**: If you change `embed_dim` in `config/settings.yaml`, tests automatically adjust to match
- **Regression test**: `tests/components/test_embedding_dimension.py` validates mock matches config
- **Validation**: All ingestion tests now pass without dimension mismatch errors

**Supported File Formats:**
The system supports the following file formats for document ingestion:
- **Text**: .txt, .md
- **Documents**: .pdf, .docx, .hwp, .epub
- **Presentations**: .pptx, .ppt, .pptm
- **Data**: .csv, .json
- **Code**: .ipynb
- **Media**: .jpg, .png, .jpeg, .mp3, .mp4
- **Email**: .mbox

**Configuration**: `internal_assistant/components/ingest/ingest_helper.py:FILE_READER_CLS` (lines 56-71)
**Validation**: `tests/server/ingest/test_txt_support.py` ensures .txt files are properly handled

**Test assertion patterns:**
- **Best practice**: Use `assert` statements with descriptive error messages, not `return True/False`
- **Pytest convention**: Test functions should return `None`, not boolean values
- **Example conversion**:
  ```python
  # Incorrect (pytest warning)
  def test_something():
      if condition:
          return False
      return True

  # Correct (proper assertion)
  def test_something():
      assert condition, "Descriptive error message explaining what failed"
  ```
- **Benefit**: Assertions provide detailed failure information and expose hidden bugs that `return False` would silently ignore
- **Reference**: `tests/ui/test_ui_feeds_isolated.py` shows proper assertion-based testing pattern

## Documentation

Full documentation is built with **MkDocs** and available in [docs/](docs/):
- User guides: [docs/user/](docs/user/)
- Architecture: [docs/developer/architecture/](docs/developer/architecture/)
- Development guides: [docs/developer/development/](docs/developer/development/)
- API reference: [docs/api/](docs/api/)

### Building Documentation
```bash
# Serve docs locally with auto-reload (recommended for development)
poetry run mkdocs serve
# Access at http://localhost:8000

# Build static site (generates site/ folder)
poetry run mkdocs build

# View built site
start site/index.html  # Windows
open site/index.html   # macOS/Linux
```

### Documentation Features
- **Full-text search** with 25 language support (powered by lunr.js)
- **Material Design** theme with dark/light mode toggle
- **Navigation** with automatic breadcrumbs and tabs
- **Mobile responsive** design
- **Fast build** (4-5 seconds for complete site, 21 pages, ~3.7MB)
- **Git integration** (automatic creation/modification dates)

### Documentation Guidelines
When adding documentation:
- Follow existing structure in [docs/](docs/) directory
- Use Markdown with [Material for MkDocs extensions](https://squidfunk.github.io/mkdocs-material/)
- Test locally with `mkdocs serve` before committing
- Configuration: [mkdocs.yml](mkdocs.yml)
- See [docs/developer/development/documentation-guidelines.md](docs/developer/development/documentation-guidelines.md) for detailed guidelines

### Key Documentation Files
- **Architecture**: [overview.md](docs/developer/architecture/overview.md), [refactoring-guide.md](docs/developer/architecture/refactoring-guide.md)
- **Development**: [setup.md](docs/developer/development/setup.md), [package-structure.md](docs/developer/development/package-structure.md)
- **Installation**: [installation.md](docs/user/installation/installation.md), [troubleshooting.md](docs/user/installation/troubleshooting.md)
- **Configuration**: [settings.md](docs/user/configuration/settings.md), [llms.md](docs/user/configuration/llms.md)