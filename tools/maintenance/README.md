# 🧹 Maintenance & Cleanup Tools

System maintenance, cleanup, and optimization utilities.

## Available Tools

### Model Management
- **`analyze_models.py`** - Analyzes and removes duplicate model files
- **`cleanup_unused_models.py`** - Removes unused model directories

### Database Management  
- **`cleanup_qdrant.py`** - Cleans up Qdrant database locks and stale processes

### Log Management
- **`manage_logs.py`** - Manages log files with cleanup strategies
- **`logging_control.py`** - Controls logging levels and log file management

## Usage

All scripts can be run from the project root:

```bash
# Clean up Qdrant issues
poetry run python tools/maintenance/cleanup_qdrant.py

# Analyze model files for duplicates
poetry run python tools/maintenance/analyze_models.py

# Manage log files
poetry run python tools/maintenance/manage_logs.py
```

## Purpose

These tools help keep the system clean and optimized by:
- Removing duplicate or unused files
- Cleaning up database locks and stale processes
- Managing log file growth and retention
- Optimizing storage usage