# Core Concepts

Internal Assistant is a cybersecurity intelligence platform that provides a private, secure AI system for threat analysis and security research. It wraps RAG (Retrieval Augmented Generation) capabilities in a complete API framework.

The platform uses FastAPI for the API layer and LlamaIndex as the core RAG framework. It supports multiple LLM providers, embedding models, and vector stores that can be configured without code changes.

## Configurable Components

Internal Assistant has three main configurable components:

- **LLM**: The large language model used for inference. Can be local (Ollama, LlamaCPP) or cloud-based (OpenAI, Azure, Gemini, Sagemaker).
- **Embeddings**: The model used to encode documents and queries. Can be local (HuggingFace, Ollama) or cloud-based.
- **Vector Store**: The database used to index and retrieve documents (Qdrant, Milvus, Chroma, PostgreSQL, ClickHouse).

An optional **Gradio web UI** is available for easy interaction with the platform through a web interface.

## Dependencies and Installation

Internal Assistant uses Poetry for dependency management. Install only the components you need using extras:

```bash
poetry install --extras "ui vector-stores-qdrant llms-ollama embeddings-huggingface"
```

See the [Installation Guide](./installation.md) for recommended setup combinations.

## Configuration

Configuration is managed through YAML files in the `config/` directory. The system supports multiple profiles that can be loaded using the `PGPT_PROFILES` environment variable.

**Example:**
```bash
PGPT_PROFILES=ollama make run
```

This loads:
1. `config/settings.yaml` - Base configuration (always loaded)
2. `config/model-configs/ollama.yaml` - Ollama-specific settings

Profile-specific settings override base settings.

## Fully Local Setup

For a completely local, privacy-focused deployment:

### LLM Options

**Ollama (Recommended)**
- Simplifies local model management
- Handles GPU acceleration automatically
- Install: `poetry install --extras "llms-ollama"`

**LlamaCPP**
- Direct model file execution
- Best for macOS with Metal GPU
- May require GPU-specific configuration on Linux/Windows
- Install: `poetry install --extras "llms-llama-cpp"`

For LlamaCPP, download models using:
```bash
poetry run python tools/system/manage_compatibility.py --check
```

### Embeddings Options

**HuggingFace (Recommended for local)**
- Local embeddings with no external API calls
- Install: `poetry install --extras "embeddings-huggingface"`

**Ollama**
- If using Ollama for LLM, can also handle embeddings
- Install: `poetry install --extras "embeddings-ollama"`

### Vector Stores

All supported vector stores (Qdrant, Milvus, Chroma, PostgreSQL) can run locally. Qdrant is the recommended default.
