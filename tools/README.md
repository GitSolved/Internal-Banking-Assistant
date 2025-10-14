# Development Tools

Collection of utilities for system maintenance, configuration, and development tasks.

## Tool Categories

### 🧹 [Maintenance](./maintenance/)
**Purpose**: System maintenance, cleanup, and optimization
- `analyze_models.py` - Analyzes and removes duplicate model files
- `cleanup_unused_models.py` - Removes unused model directories
- `manage_logs.py` - Unified log file management (status, interactive, auto cleanup)
- `logging_control.py` - Controls logging levels and log file operations

### 🔧 [System Management](./system/)
**Purpose**: System configuration, monitoring, and management
- `manage_compatibility.py` - Dependency compatibility management (check, enforce, fix)
- `generate_compatibility_docs.py` - Generates compatibility documentation
- `check_model.py` - Checks current model configuration and status
- `extract_openapi.py` - Extracts OpenAPI specification from FastAPI app
- `utils.py` - Database utilities (stats, wipe operations for vector/node stores)

### 📥 [Data Processing](./data/)
**Purpose**: Data ingestion and processing utilities
- `ingest_folder.py` - Bulk document ingestion with retry logic and checkpointing

### 💾 [Storage Management](./storage/)
**Purpose**: Storage administration and recovery
- `storage_admin.py` - Storage diagnosis, consistency checking, backup/restore operations

### 🧪 [Development & Testing](./development/)
**Purpose**: Development utilities and test execution
- `testing/run_tests.py` - Poetry-enforced test runner

### 🎨 [JavaScript Integration](./Javascript/) **[PRODUCTION DEPENDENCY]**
**Purpose**: JavaScript module management for Gradio UI
- `js_manager.py` - JavaScript module loading and injection (imported by ui.py)
- `modules/*.js` - Client-side JavaScript modules for UI functionality

**⚠️ CRITICAL**: This directory is actively used in production and cannot be modified.

## Usage

**IMPORTANT**: Always prefer Makefile commands when available:
```bash
# Use Makefile commands (recommended)
make compatibility-check    # Instead of manage_compatibility.py --check
make log-cleanup           # Instead of manage_logs.py --auto
make test                  # Instead of run_tests.py
make format                # Black + ruff formatting
```

For tools without Makefile equivalents, run from project root using Poetry:
```bash
# Maintenance
poetry run python tools/maintenance/analyze_models.py
poetry run python tools/maintenance/cleanup_unused_models.py
poetry run python tools/maintenance/manage_logs.py --status

# System
poetry run python tools/system/check_model.py
poetry run python tools/system/extract_openapi.py internal_assistant.launcher:app
poetry run python tools/system/utils.py stats

# Data & Storage
poetry run python tools/data/ingest_folder.py /path/to/documents
poetry run python tools/storage/storage_admin.py diagnose

# Development
poetry run python tools/development/testing/run_tests.py
```

## Organization Principles

- **Logical Grouping**: Tools are grouped by primary function
- **Minimal Overlap**: Each category serves a distinct purpose
- **Clear Naming**: Category names indicate the tool's purpose
- **Easy Navigation**: READMEs in each category provide detailed information

## Adding New Tools

When adding new tools:

1. **Check if a Makefile command would be more appropriate** - prefer Makefile for common operations
2. Determine the category:
   - **Maintenance**: Cleanup, log management, model optimization
   - **System**: Configuration, compatibility, monitoring
   - **Data**: Document ingestion, data processing
   - **Storage**: Database admin, recovery operations
   - **Development**: Testing, debugging utilities
3. Place in the appropriate category directory
4. Follow naming conventions (snake_case)
5. Include comprehensive docstring with:
   - Purpose description
   - Usage examples with `poetry run python tools/...` commands
6. Add proper error handling and clear output messages
7. **Never modify Javascript/** - production dependency used by ui.py

## Best Practices

- Always use absolute imports: `from internal_assistant.xxx import yyy`
- Add `#!/usr/bin/env python3` shebang to all scripts
- Use argparse with clear help messages and examples
- Include descriptive error messages
- Log important operations
- Support dry-run mode for destructive operations
- Return appropriate exit codes (0 for success, non-zero for errors)