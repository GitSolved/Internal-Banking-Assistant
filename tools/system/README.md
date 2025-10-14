# 🔧 System Management & Configuration Tools

System configuration, monitoring, and management utilities.

## Available Tools

### Compatibility Management
- **`manage_compatibility.py`** - Manages dependency compatibility and version enforcement
- **`generate_compatibility_docs.py`** - Generates compatibility documentation

### System Monitoring
- **`check_model.py`** - Checks current model configuration and status

### Database Utilities
- **`utils.py`** - Database utilities (stats, wipe operations)

## Usage

All scripts can be run from the project root:

```bash
# Check current model status
poetry run python tools/system/check_model.py

# Generate compatibility documentation
poetry run python tools/system/generate_compatibility_docs.py

# Manage dependency compatibility
poetry run python tools/system/manage_compatibility.py
```

## Purpose

These tools help manage system settings and compatibility by:
- Monitoring system configuration and status
- Enforcing dependency compatibility requirements
- Generating system documentation
- Providing database management utilities