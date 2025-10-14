# Package Structure and Import Conventions

This guide explains the project structure and import patterns for Internal Assistant.

**Related Documentation:**
- [System Architecture Overview](../architecture/overview.md) - High-level architecture
- [Development Setup](setup.md) - Environment setup guide

## Package Structure

### Key Directories
- `internal_assistant/` - Main Python package (renamed from 'src')
- `tests/` - Test suite
- `config/` - Configuration files
- `docs/` - Documentation
- `tools/` - Development utilities

## Import Conventions

### ✅ Correct Import Patterns

Always use the full package name for imports:

```python
# ✅ Correct - Use full package name
from internal_assistant.components.vector_store.vector_store_component import VectorStoreComponent
from internal_assistant.paths import local_data_path
from internal_assistant.settings.settings import settings
from internal_assistant.server.feeds.feeds_service import RSSFeedService
from internal_assistant.ui.ui import InternalAssistantUI
```

### ❌ Incorrect Import Patterns

Never use relative imports or the old 'src' reference:

```python
# ❌ Wrong - Don't use relative imports
from ..components.vector_store.vector_store_component import VectorStoreComponent

# ❌ Wrong - Don't use old 'src' reference
from src.components.vector_store.vector_store_component import VectorStoreComponent

# ❌ Wrong - Don't use direct file imports
from internal_assistant.components.vector_store import vector_store_component
```

## Package Configuration

The package is configured in `pyproject.toml`:

```toml
[tool.poetry]
name = "internal-assistant"
version = "0.6.2"
packages = [
    { include = "internal_assistant" }  # Maps internal_assistant/ directory
]
```

## Running the Application

### Development Mode
```bash
# Using Makefile (recommended)
make dev

# Direct command
poetry run python -m uvicorn internal_assistant.main:app --reload --port 8001
```

### Production Mode
```bash
# Using Makefile
make production

# Direct command
poetry run python -m uvicorn internal_assistant.main:app --host 0.0.0.0 --port 8000
```

### Module Execution
```bash
# Run as module
poetry run python -m internal_assistant

# Run specific script
poetry run python internal_assistant/main.py
```

## Testing

Tests should import using the full package name:

```python
# ✅ Correct test imports
from internal_assistant.server.feeds.feeds_service import RSSFeedService
from internal_assistant.ui.ui import InternalAssistantUI
from internal_assistant.di import create_application_injector
```

## Tools and Scripts

Tools in the `tools/` directory should import using the full package name:

```python
# ✅ Correct tool imports
from internal_assistant.paths import local_data_path
from internal_assistant.settings.settings import settings
from internal_assistant.utils.version_check import validate_dependency_versions
```

## Common Issues and Solutions

### Issue: "No module named 'internal_assistant'"
**Cause**: Package not properly installed or PYTHONPATH not set
**Solution**: 
```bash
# Reinstall package
poetry install

# Or run from project root
cd /path/to/internal-assistant
poetry run python -m internal_assistant
```

### Issue: "No module named 'src'"
**Cause**: Using old import patterns
**Solution**: Update imports to use `internal_assistant` instead of `src`

### Issue: Import errors in tests
**Cause**: Test configuration not recognizing package structure
**Solution**: Ensure tests use full package imports and run with `--import-mode=importlib`

## Migration Guide

If you encounter old import patterns, here's how to fix them:

### Before (Old Pattern)
```python
from src.components.vector_store.vector_store_component import VectorStoreComponent
from src.paths import local_data_path
from src.settings.settings import settings
```

### After (New Pattern)
```python
from internal_assistant.components.vector_store.vector_store_component import VectorStoreComponent
from internal_assistant.paths import local_data_path
from internal_assistant.settings.settings import settings
```

## File Path References

When referencing file paths in code, use the correct directory structure:

### Before (Old Pattern)
```python
ui_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'ui', 'ui.py')
```

### After (New Pattern)
```python
ui_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'internal_assistant', 'ui', 'ui.py')
```

## Best Practices

1. **Always use full package imports** - Never use relative imports
2. **Use the Makefile** - It contains the correct commands for running the application
3. **Test imports work** - Run `poetry run make test` to verify imports are correct
4. **Update documentation** - When changing import patterns, update this guide
5. **Use IDE features** - Configure your IDE to recognize the `internal_assistant` package

## Verification Commands

To verify the package structure is correct:

```bash
# Check if package can be imported
poetry run python -c "import internal_assistant; print('✅ Package imports correctly')"

# Run tests to verify all imports work
poetry run make test

# Check package structure
poetry run python -c "from internal_assistant import main; print('✅ Main module accessible')"
```

## Troubleshooting

If you encounter import issues:

1. **Check pyproject.toml** - Ensure package configuration is correct
2. **Verify directory structure** - Ensure `internal_assistant/` directory exists
3. **Reinstall package** - Run `poetry install` to refresh package installation
4. **Check PYTHONPATH** - Ensure you're running from the project root
5. **Update imports** - Replace any remaining `src` references with `internal_assistant`

## Related Documentation

- [Development Setup](setup.md)
- [Testing Guide](../testing/)
- [Configuration Guide](../configuration/)
- [API Documentation](../api/)

---

**Note**: This document should be updated whenever the package structure changes to prevent future import issues.
