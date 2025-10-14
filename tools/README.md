# Development Tools

Collection of utilities for system maintenance, configuration, and development tasks.

## Tool Categories

### 🧹 [Maintenance & Cleanup Tools](./maintenance/)
**Purpose**: System maintenance, cleanup, and optimization
- `analyze_models.py` - Analyzes and removes duplicate model files
- `cleanup_unused_models.py` - Removes unused model directories  
- `cleanup_qdrant.py` - Cleans up Qdrant database locks and stale processes
- `manage_logs.py` - Manages log files with cleanup strategies
- `logging_control.py` - Controls logging levels and log file management

### 🔧 [System Management & Configuration Tools](./system/)
**Purpose**: System configuration, monitoring, and management
- `manage_compatibility.py` - Manages dependency compatibility and version enforcement
- `generate_compatibility_docs.py` - Generates compatibility documentation
- `check_model.py` - Checks current model configuration and status
- `utils.py` - Database utilities (stats, wipe operations)

### 📥 [Data Processing Tools](./data/)
**Purpose**: Data ingestion and processing utilities
- `ingest_folder.py` - Ingests documents from folders into the system

### 🧪 [Development & Testing Tools](./development/)
**Purpose**: Development utilities and test execution
- `testing/run_tests.py` - Test execution utilities

### 📊 [Analysis Tools](./analysis/)
**Purpose**: Code and dependency analysis
- Analysis and diagnostic utilities for project health

### ⚡ [Performance Tools](./performance/)
**Purpose**: Performance profiling and optimization
- Performance measurement and benchmarking utilities

### 💾 [Storage Management Tools](./storage/)
**Purpose**: Storage administration and recovery
- `storage_admin.py` - Administrative access to storage recovery and management
- `direct_cleanup.py` - Direct storage cleanup operations

### 🎨 [JavaScript Integration](./Javascript/) **[PRODUCTION DEPENDENCY]**
**Purpose**: JavaScript module management for Gradio UI
- `js_manager.py` - JavaScript module loading and injection (imported in ui.py)
- `modules/*.js` - Client-side JavaScript modules for UI functionality

**⚠️ CRITICAL**: This directory is actively used in production code and cannot be deleted.

## Usage

All tools should be run from the project root using Poetry:

```bash
# General pattern
poetry run python tools/{category}/{tool_name}.py [arguments]

# Examples
poetry run python tools/maintenance/cleanup_qdrant.py
poetry run python tools/system/check_model.py
poetry run python tools/data/ingest_folder.py /path/to/documents
poetry run python tools/storage/storage_admin.py diagnose
poetry run python tools/development/testing/run_tests.py
```

## Organization Principles

- **Logical Grouping**: Tools are grouped by primary function
- **Minimal Overlap**: Each category serves a distinct purpose
- **Clear Naming**: Category names indicate the tool's purpose
- **Easy Navigation**: READMEs in each category provide detailed information

## Adding New Tools

When adding new development tools:

1. Determine the primary purpose:
   - **Maintenance**: Cleanup, log management, model optimization
   - **System**: Configuration, compatibility, monitoring
   - **Data**: Document ingestion, data processing
   - **Development**: Testing, debugging utilities
   - **Analysis**: Dependency analysis, code metrics
   - **Performance**: Profiling, benchmarking
   - **Storage**: Database admin, recovery operations
2. Place in the appropriate category directory
3. Update the category's README.md (if it exists)
4. Follow the existing naming conventions
5. Include proper docstrings and usage instructions
6. **Never modify Javascript/** - it's a production dependency imported by ui.py