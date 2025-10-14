# Tools Purpose Guide - Internal Assistant

**Complete explanation of all tools in the `/tools` directory**

---

## Overview

The `/tools` directory contains **18 Python scripts** and **7 JavaScript modules** organized into specialized categories for system maintenance, development, and operational tasks.

---

## 📂 Category 1: Analysis Tools (`tools/analysis/`)

### 🔍 ui-dependency-analyzer.py (396 lines)

**Purpose:** Comprehensive dependency analysis for UI refactoring

**What it does:**
- Parses the monolithic `ui.py` file using Python's AST (Abstract Syntax Tree)
- Identifies function dependencies and coupling patterns
- Tracks variable usage across functions
- Maps Gradio component interactions
- Calculates complexity and coupling scores
- Generates extraction risk assessments

**When to use:**
- Planning UI component extraction
- Identifying tightly coupled functions
- Understanding refactoring complexity
- Generating dependency graphs

**Example usage:**
```bash
poetry run python tools/analysis/ui-dependency-analyzer.py
# Outputs: dependency analysis JSON with coupling scores
```

**Output:** Generates JSON with:
- Total functions analyzed
- High coupling functions (complexity > threshold)
- Dependency maps between functions
- Gradio component usage patterns
- Recommended extraction order

**Created for:** UI refactoring project to break down 6,357-line ui.py file

---

## 📂 Category 2: Data Processing (`tools/data/`)

### 📄 extract_openapi.py (34 lines)

**Purpose:** Generate OpenAPI specification from FastAPI application

**What it does:**
- Starts the FastAPI application
- Extracts the OpenAPI JSON schema
- Saves to `fern/openapi/openapi.json`
- Enables automatic API documentation

**When to use:**
- After adding/modifying API endpoints
- Generating API documentation
- Updating SDK specifications
- CI/CD documentation pipelines

**Example usage:**
```bash
poetry run python tools/data/extract_openapi.py
# Also available as: make api-docs
```

**Output:** `fern/openapi/openapi.json` with complete API specification

---

### 📁 ingest_folder.py (288 lines)

**Purpose:** Bulk document ingestion from filesystem folders

**What it does:**
- Scans specified folder for documents
- Validates file formats (PDF, TXT, DOCX, etc.)
- Ingests documents into the vector store
- Updates document index
- Reports ingestion statistics

**When to use:**
- Initial system setup with document corpus
- Bulk importing security reports
- Migrating documents from other systems
- Testing with large document sets

**Example usage:**
```bash
poetry run python tools/data/ingest_folder.py /path/to/documents
# Ingests all supported documents from folder
```

**Supported formats:**
- Text: .txt, .md
- Documents: .pdf, .docx, .hwp, .epub
- Presentations: .pptx, .ppt
- Data: .csv, .json
- And more (see ingest_helper.py)

---

## 📂 Category 3: Development (`tools/development/`)

### 🧪 testing/run_tests.py (106 lines)

**Purpose:** Test runner with environment validation

**What it does:**
- Validates test environment before running
- Executes pytest with proper configuration
- Reports test results
- Handles test failures gracefully

**When to use:**
- Running test suites
- CI/CD test execution
- Pre-commit test validation

**Example usage:**
```bash
poetry run python tools/development/testing/run_tests.py
poetry run python tools/development/testing/run_tests.py tests/ui/
```

---

## 📂 Category 4: JavaScript Management (`tools/Javascript/`) ⚠️ PRODUCTION CODE

**⚠️ CRITICAL: This is not optional - actively used in production**

### 🎨 js_manager.py (106 lines) **[IMPORTED IN ui.py]**

**Purpose:** JavaScript module loading and injection for Gradio UI

**What it does:**
- Loads JavaScript modules from `modules/` directory
- Caches JavaScript content for performance
- Generates HTML script tags for Gradio
- Provides inline script injection
- Manages JS dependencies

**When to use:**
- **Automatically used** when UI starts
- UI initialization requires this module
- DO NOT delete or modify without testing UI

**Import location:**
```python
# internal_assistant/ui/ui.py line 76
from tools.Javascript.js_manager import JSManager
```

**Methods:**
- `load_module(name)` - Load specific JS file
- `get_script_tags()` - Generate HTML script tags
- `get_inline_scripts()` - Get combined JavaScript
- `clear_cache()` - Clear JS cache

---

### 📦 JavaScript Modules (`tools/Javascript/modules/`) - 7 files

**Purpose:** Client-side UI functionality for Gradio interface

#### 1. ui_common.js (1.9KB)
**Purpose:** Shared utility functions
- DOM helpers (ready, querySelector)
- Logging utilities
- Debounce function
- Common UI helpers

#### 2. ai_controls.js (3.2KB)
**Purpose:** AI control interfaces
- Model parameter controls
- Temperature sliders
- System prompt management
- AI configuration UI

#### 3. collapsible.js (7.5KB)
**Purpose:** Collapsible sections functionality
- Toggle individual sections
- Expand/collapse all sections
- Document organization
- Accordion behavior

#### 4. document_management.js (12KB)
**Purpose:** Document operations
- File upload handlers
- Document selection
- Batch operations
- Document list management

#### 5. mode_selector.js (14KB)
**Purpose:** Mode switching interface
- RAG vs General mode toggle
- Button color updates
- Mode state management
- UI mode synchronization

#### 6. resize_handlers.js (17KB)
**Purpose:** UI resizing functionality
- Responsive layout adjustments
- Drag-to-resize panels
- Window resize handlers
- Layout persistence

#### 7. threat_display.js (5.9KB)
**Purpose:** Threat intelligence display
- MITRE ATT&CK visualization
- Threat level indicators
- CVE information display
- Security feed formatting

**Why these exist:**
- Extracted from monolithic ui.py (originally ~1,850 lines of embedded JavaScript)
- Improved maintainability
- Better separation of concerns
- Easier to debug and test

---

## 📂 Category 5: Maintenance Tools (`tools/maintenance/`)

### 🗂️ analyze_models.py (199 lines)

**Purpose:** Detect and remove duplicate model files

**What it does:**
- Scans model directories for duplicates
- Compares file hashes (MD5/SHA256)
- Identifies identical model files
- Reports potential space savings
- Optionally removes duplicates

**When to use:**
- After downloading multiple model versions
- Optimizing storage space
- Cleaning up model cache
- Before model migration

**Example usage:**
```bash
poetry run python tools/maintenance/analyze_models.py
# Also available as: make analyze-models
```

**Output:**
- List of duplicate files
- Storage space wasted
- Recommendations for cleanup

---

### 🗑️ cleanup_unused_models.py (194 lines)

**Purpose:** Remove unused model directories

**What it does:**
- Scans for model directories
- Checks if models are configured
- Identifies unused/orphaned models
- Safely removes unused directories
- Reports freed space

**When to use:**
- After switching models
- Storage optimization
- Cleaning up test models
- Model directory maintenance

**Example usage:**
```bash
poetry run python tools/maintenance/cleanup_unused_models.py
```

---

### 🔒 cleanup_qdrant.py (92 lines)

**Purpose:** Clean up Qdrant database locks and stale processes

**What it does:**
- Detects stale Qdrant lock files
- Removes orphaned lock files
- Cleans up crashed process remnants
- Verifies Qdrant health
- Restarts Qdrant if needed

**When to use:**
- Qdrant won't start (lock file exists)
- After application crashes
- Database connection errors
- Before major operations

**Example usage:**
```bash
poetry run python tools/maintenance/cleanup_qdrant.py
```

**Common scenarios:**
- Error: "Collection is locked"
- Error: "Qdrant is already running"
- Stale `.lock` files in `local_data/`

---

### 📝 logging_control.py (200 lines)

**Purpose:** Runtime control of logging levels and log management

**What it does:**
- Change logging levels dynamically
- Configure log output formats
- Manage log file rotation
- Filter log messages
- Debug logging issues

**When to use:**
- Debugging production issues
- Reducing log verbosity
- Troubleshooting specific components
- Performance optimization

**Example usage:**
```bash
poetry run python tools/maintenance/logging_control.py --level DEBUG
poetry run python tools/maintenance/logging_control.py --module ingest --level INFO
```

---

### 🧹 manage_logs.py (472 lines)

**Purpose:** Log file cleanup and retention management

**What it does:**
- Scans log directories
- Applies retention policies
- Archives old logs
- Compresses historical logs
- Reports log disk usage
- Implements cleanup strategies

**When to use:**
- Disk space running low
- Regular maintenance (automated)
- Before system backup
- Log rotation management

**Example usage:**
```bash
poetry run python tools/maintenance/manage_logs.py
# Also available as: make log-cleanup
```

**Retention policy:**
- Keeps 7 most recent session logs
- Archives logs older than 30 days
- Compresses logs older than 7 days
- Reports space freed

---

## 📂 Category 6: Performance (`tools/performance/`)

### ⚡ baseline-measurement.py (498 lines)

**Purpose:** Measure performance baselines before/after refactoring

**What it does:**
- Measures UI load time (cold start)
- Tracks memory usage during operations
- Times component rendering
- Measures Gradio blocks creation
- Generates performance reports
- Compares before/after metrics

**When to use:**
- Before major refactoring
- After optimization changes
- Performance regression testing
- Benchmarking improvements

**Example usage:**
```bash
poetry run python tools/performance/baseline-measurement.py
# Outputs: baseline-results.json with metrics
```

**Metrics measured:**
- UI load time: How long UI takes to initialize
- Memory usage: Peak and average memory
- Component render times: Individual component performance
- Gradio build time: Framework initialization time

**Created for:** Validating UI refactoring doesn't degrade performance

---

## 📂 Category 7: Storage Management (`tools/storage/`)

### 🔧 direct_cleanup.py (284 lines)

**Purpose:** Direct storage cleanup operations

**What it does:**
- Bypasses normal cleanup procedures
- Performs low-level storage operations
- Removes corrupted index entries
- Rebuilds storage indexes
- Emergency recovery operations

**When to use:**
- Storage corruption detected
- Normal cleanup fails
- Emergency recovery needed
- Database inconsistencies

**Example usage:**
```bash
poetry run python tools/storage/direct_cleanup.py
```

**⚠️ Warning:** Use with caution - bypasses safety checks

---

### 🛠️ storage_admin.py (296 lines)

**Purpose:** Administrative interface for storage management

**What it does:**
- Comprehensive storage diagnosis
- Health checks for all storage components
- Consistency verification
- Recovery operations
- Storage statistics
- Administrative commands

**When to use:**
- Troubleshooting storage issues
- Verifying storage health
- Running diagnostics
- Administrative maintenance

**Example usage:**
```bash
poetry run python tools/storage/storage_admin.py diagnose
poetry run python tools/storage/storage_admin.py verify
poetry run python tools/storage/storage_admin.py repair
```

**Commands:**
- `diagnose` - Run comprehensive health check
- `verify` - Verify storage consistency
- `repair` - Attempt automatic repair
- `stats` - Show storage statistics
- `clean` - Clean up orphaned data

**Integrates with:**
- `StorageManagementService`
- `StorageConsistencyService`
- `IngestService`

---

## 📂 Category 8: System Utilities (`tools/system/`)

### 🔍 check_model.py (78 lines)

**Purpose:** Check current model configuration and status

**What it does:**
- Displays current LLM model
- Shows embedding model
- Reports model locations
- Verifies model files exist
- Shows model configuration
- Reports model sizes

**When to use:**
- Verifying model setup
- Troubleshooting model issues
- Before switching models
- Documentation generation

**Example usage:**
```bash
poetry run python tools/system/check_model.py
```

**Output:**
```
LLM Model: Foundation-Sec-8B-q4_k_m.gguf
Embedding Model: nomic-embed-text-v1.5
Model Location: /path/to/models/
Model Size: 5.06 GB
Status: ✓ Loaded and ready
```

---

### 📋 generate_compatibility_docs.py (143 lines)

**Purpose:** Generate dependency compatibility documentation

**What it does:**
- Reads `pyproject.toml` dependencies
- Extracts version constraints
- Generates markdown documentation
- Creates compatibility matrices
- Documents known issues
- Produces compatibility guide

**When to use:**
- After dependency updates
- Generating documentation
- Onboarding new developers
- Troubleshooting dependency conflicts

**Example usage:**
```bash
poetry run python tools/system/generate_compatibility_docs.py
```

**Output:** `docs/compatibility/compatibility_guide.md`

---

### ⚙️ manage_compatibility.py (445 lines)

**Purpose:** Enforce dependency compatibility and version requirements

**What it does:**
- Validates Python version (must be 3.11.9)
- Checks FastAPI version (0.108.0-0.115.0)
- Validates Pydantic version (2.8.0-2.9.0)
- Checks Gradio version (4.15.0-4.39.0)
- Reports version violations
- Enforces compatibility requirements

**When to use:**
- **Automatically run** on application startup
- Before dependency updates
- CI/CD version validation
- Troubleshooting startup errors

**Example usage:**
```bash
poetry run python tools/system/manage_compatibility.py
# Also available as: make compatibility-check
```

**Why this exists:**
The project has **strict version constraints** due to:
- Pydantic schema generation issues with newer FastAPI
- Gradio compatibility with specific Pydantic versions
- LlamaIndex version dependencies

**Critical versions:**
- Python: Exactly 3.11.9
- FastAPI: 0.108.0 ≤ version < 0.115.0
- Pydantic: 2.8.0 ≤ version < 2.9.0
- Gradio: 4.15.0 ≤ version < 4.39.0

---

### 🗄️ utils.py (184 lines)

**Purpose:** Database utilities and operations

**What it does:**
- **Database statistics:** Show collection sizes, document counts, vector counts
- **Database wipe:** Clean database operations (⚠️ destructive)
- **Health checks:** Verify database connectivity
- **Index operations:** Rebuild, optimize indexes
- **Query utilities:** Helper functions for database queries

**When to use:**
- Checking database statistics
- Development/testing cleanup
- Database maintenance
- Troubleshooting database issues

**Example usage:**
```bash
poetry run python tools/system/utils.py stats
# Also available as: make stats
```

**Commands:**
- `stats` - Show database statistics
- `wipe` - Clean database (⚠️ deletes all data)
- `health` - Check database health
- `optimize` - Optimize database indexes

**⚠️ Warning:** `wipe` command is **destructive** - use only in development

---

## Summary of Tool Categories

### By Frequency of Use

**Daily Operations:**
- `manage_logs.py` - Automated log cleanup
- `manage_compatibility.py` - Startup validation

**Weekly Maintenance:**
- `analyze_models.py` - Model cleanup
- `cleanup_qdrant.py` - Database maintenance
- `utils.py` - Database statistics

**As Needed:**
- `ingest_folder.py` - Bulk document ingestion
- `extract_openapi.py` - API documentation
- `check_model.py` - Model verification
- `storage_admin.py` - Storage troubleshooting

**Development:**
- `ui-dependency-analyzer.py` - Refactoring analysis
- `baseline-measurement.py` - Performance testing
- `run_tests.py` - Test execution

**Production (Automatic):**
- `js_manager.py` - **Required for UI** (imported in code)
- All JavaScript modules - **Required for UI functionality**

---

## Tool Dependencies

### Tools That Import Project Code
(Require application environment)

1. `storage_admin.py` - Uses IngestService, StorageManagementService
2. `direct_cleanup.py` - Uses storage_context
3. `check_model.py` - Uses settings module
4. `manage_compatibility.py` - Uses dependency resolution
5. `utils.py` - Uses database services
6. `ingest_folder.py` - Uses IngestService

### Standalone Tools
(Can run independently)

1. `analyze_models.py` - File system operations
2. `cleanup_unused_models.py` - File system operations
3. `cleanup_qdrant.py` - Process/file management
4. `manage_logs.py` - File system operations
5. `logging_control.py` - Logging configuration
6. `ui-dependency-analyzer.py` - AST parsing
7. `baseline-measurement.py` - System metrics
8. `generate_compatibility_docs.py` - File parsing
9. `extract_openapi.py` - FastAPI introspection

---

## Makefile Integration

Many tools are integrated into the Makefile for easy access:

```bash
make api-docs              # extract_openapi.py
make log-cleanup           # manage_logs.py
make analyze-models        # analyze_models.py
make compatibility-check   # manage_compatibility.py
make stats                 # utils.py stats
```

See `Makefile` or `CLAUDE.md` for complete list.

---

## Best Practices

### When to Use Tools

**Before starting work:**
- `make compatibility-check` - Verify environment
- `check_model.py` - Confirm model setup

**During development:**
- `run_tests.py` - Run tests frequently
- `ui-dependency-analyzer.py` - Plan refactoring
- `baseline-measurement.py` - Measure performance

**Maintenance:**
- `make log-cleanup` - Regular log cleanup (automated)
- `analyze_models.py` - Monthly model cleanup
- `cleanup_qdrant.py` - After crashes

**Troubleshooting:**
- `storage_admin.py diagnose` - Storage issues
- `check_model.py` - Model problems
- `utils.py stats` - Database inspection

**Production:**
- Never use `utils.py wipe` in production
- Never modify JavaScript modules without testing UI
- Never delete `tools/Javascript/` - it's required

---

## Critical: Do Not Delete

**Production Dependencies:**
- ✅ `tools/Javascript/js_manager.py` - **Imported in ui.py**
- ✅ `tools/Javascript/modules/*.js` - **Required for UI**

**System Critical:**
- ✅ `manage_compatibility.py` - Version enforcement
- ✅ `manage_logs.py` - Prevent disk full
- ✅ `cleanup_qdrant.py` - Database recovery

**Development Essential:**
- ✅ `ingest_folder.py` - Bulk operations
- ✅ `extract_openapi.py` - API docs
- ✅ `utils.py` - Database management

---

## Conclusion

The `tools/` directory provides a comprehensive suite of utilities for:
- 🧹 **Maintenance** - Cleanup, optimization, health checks
- 🔧 **System Management** - Configuration, monitoring, compatibility
- 📊 **Analysis** - Dependency analysis, performance measurement
- 💾 **Storage** - Administrative tools, recovery operations
- 🚀 **Development** - Testing, documentation, refactoring
- 🎨 **UI** - JavaScript management (production dependency)

All tools are well-documented, follow consistent patterns, and integrate with the project's Makefile for easy access.

---

**End of Guide**
