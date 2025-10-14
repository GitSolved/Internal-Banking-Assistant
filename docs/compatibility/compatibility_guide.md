# Internal Assistant - Compatibility Guide

## Overview

This document provides compatibility information for Internal Assistant.
All version requirements are validated by the version check system in `internal_assistant/utils/version_check.py`.

## Application Version

- **Current Version**: 0.6.2

## Python Version

- **Required**: 3.11.9 (exact)
- **Status**: ✅ Compatible

## Critical Dependencies

These packages are essential for the application to function:

### fastapi
- **Required Range**: >=0.108.0, <0.115.0
- **Status**: ✅ Compatible

### pydantic
- **Required Range**: >=2.8.0, <2.9.0
- **Status**: ✅ Compatible

### llama-index-core
- **Required Range**: >=0.11.2, <0.12.0
- **Status**: ✅ Compatible

### gradio
- **Required Range**: >=4.15.0, <4.39.0
- **Status**: ✅ Compatible

### transformers
- **Required Range**: >=4.44.2, <5.0.0
- **Status**: ✅ Compatible

## All Dependencies

Complete list of all dependencies and their compatibility status:

### Core Dependencies
- **fastapi**: >=0.108.0, <0.115.0 ✅
- **pydantic**: >=2.8.0, <2.9.0 ✅
- **gradio**: >=4.15.0, <4.39.0 ✅
- **llama-index-core**: >=0.11.2, <0.12.0 ✅
- **transformers**: >=4.44.2, <5.0.0 ✅

### LLM & Embeddings
- **llama-index-llms-ollama**: Any version ✅
- **llama-index-llms-openai-like**: Any version ✅
- **llama-index-embeddings-huggingface**: Any version ✅
- **sentence-transformers**: >=3.1.1, <4.0.0 ✅

### Storage & Data
- **llama-index-vector-stores-qdrant**: Any version ✅
- **feedparser**: >=6.0.10, <7.0.0 ✅
- **aiohttp**: >=3.9.0, <4.0.0 ✅
- **beautifulsoup4**: >=4.12.0, <5.0.0 ✅

### Utilities
- **cryptography**: >=3.1, <4.0.0 ✅
- **python-multipart**: >=0.0.10, <1.0.0 ✅
- **docx2txt**: >=0.8, <1.0.0 ✅
- **psutil**: >=7.0.0, <8.0.0 ✅
- **watchdog**: >=4.0.1, <5.0.0 ✅

### Development Tools
- **pytest**: >=8.0.0, <9.0.0 ✅
- **black**: >=24.0.0, <25.0.0 ✅
- **ruff**: >=0.0.0, <1.0.0 ✅

## System Requirements

- **RAM**: 8GB+ recommended
- **Storage**: 10GB+ for models and data
- **Python**: 3.11.9 (exact version required)


## Validation Commands

To check compatibility:

```bash
# Check dependency compatibility
make compatibility-check

# Or directly with poetry
poetry run python tools/system/manage_compatibility.py --check
```

## Installation

Install with all required dependencies:

```bash
poetry install --extras "ui llms-ollama embeddings-huggingface vector-stores-qdrant"
```

## Notes

- All version constraints are defined in `internal_assistant/utils/version_check.py`
- The version check system validates these constraints at startup
- Critical packages are marked for immediate attention if incompatible
- Wildcard versions indicate any version is acceptable
- See `pyproject.toml` for complete dependency specifications
