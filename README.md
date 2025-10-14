# Internal Assistant - Cybersecurity Intelligence Platform

## ⚠️ Dependency Requirements

**Required Versions:**
- **Python**: 3.11.9 (exact)
- **FastAPI**: >=0.108.0,<0.115.0
- **Pydantic**: >=2.8.0,<2.9.0
- **Gradio**: >=4.15.0,<4.39.0

Versions are automatically validated on startup.

## Quick Start

```bash
# 1. Verify Python version
python --version  # Should show 3.11.9

# 2. Install dependencies
poetry install --extras "ui llms-ollama embeddings-huggingface vector-stores-qdrant"

# 3. Run the application
make run
```

**Documentation:** See [Installation Guide](docs/user/installation/installation.md) for detailed setup instructions.

![Internal Assistant UI](/docs/assets/ui.png?raw=true)

**Internal Assistant** is a privacy-focused cybersecurity intelligence platform for threat analysis and security research.

## 🎯 Key Features

- **🔒 100% Private:** All AI operations run locally on your infrastructure
- **🛡️ Cybersecurity Specialization:** Foundation-Sec-8B model, MITRE ATT&CK, CVE databases, threat intelligence feeds
- **⚡ Optimized Performance:** q4_k_m quantization, 6-20 second response times, 5.06 GB model size
- **📊 Threat Intelligence:** RSS feeds, security news, regulatory compliance tracking

## 🚀 Installation

**System Requirements:** Python 3.11.9, 8GB+ RAM, 10GB+ storage

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/SecureYourGear/internal-assistant.git
cd internal-assistant/config/deployment/docker

# Start with Ollama (CPU)
docker-compose --profile ollama-cpu up

# OR with GPU support
docker-compose --profile ollama-cuda up
```

Access UI at http://localhost:8001

### Option 2: Poetry (Development)

```bash
git clone https://github.com/SecureYourGear/internal-assistant.git
cd internal-assistant

# Install dependencies
poetry install --extras "ui llms-ollama vector-stores-qdrant embeddings-huggingface"

# Set up Ollama and Foundation-Sec-8B model
# See: https://huggingface.co/Foundation-Sec/Foundation-Sec-8B

# Run application
make run
```

Access UI at http://localhost:8001

## 🔧 Usage

- **General LLM Mode:** Fast queries and threat assessments (6-12 seconds)
- **RAG Mode:** Document-based analysis and compliance research (12-20 seconds)

## 🛡️ Cybersecurity Features

- RSS feeds for real-time security news
- CVE database tracking
- MITRE ATT&CK framework integration
- Regulatory compliance monitoring

## 🏗️ Architecture

- **Modular UI:** Refactored from 6,258 lines to modular components (44% reduction)
- **Dependency Injection:** Clean service layer with FastAPI
- **Privacy-Focused:** Local processing, no external data transmission
- **Secure Storage:** Local vector database with encryption support

## 📁 Storage

- **`local_data/`** - Ephemeral runtime data (regenerable): logs, session data, vector DB cache
- **`data/`** - Persistent user data (must preserve): models, documents, processed content

## 🔧 Configuration

**Active Components:**
- LLM: Ollama with Foundation-Sec-8B
- Embeddings: HuggingFace nomic-embed-text-v1.5
- Vector Store: Qdrant (disk-based)
- UI: Gradio web interface

**Configuration:** See `config/settings.yaml` for full settings

## 🚨 Troubleshooting

```bash
# Verify Ollama and model
ollama list

# Reinstall dependencies
poetry install --extras "ui llms-ollama vector-stores-qdrant embeddings-huggingface"

# Check compatibility
make compatibility-check
```

See [Troubleshooting Guide](docs/user/installation/troubleshooting.md) for detailed solutions.

## 🧪 Development

```bash
# Testing
make test                # Run all tests
make test-coverage       # Run with coverage

# Code Quality
make format              # Format code (black + ruff)
make mypy                # Type checking
make check               # Full quality check
```

## 🤝 Contributing

Contributions welcome! Please:
1. Run `make check` before submitting
2. Add tests for new features
3. Update documentation

```bash
# Development setup
poetry install --with dev
poetry run make dev
```

**Note:** This project uses Poetry 2.0+. Use `poetry run` or `poetry env activate` instead of deprecated `poetry shell`.

## 📄 Documentation

```bash
# Serve documentation locally
poetry run mkdocs serve  # Access at http://localhost:8000

# Build static site
poetry run mkdocs build
```

**Features:** Full-text search, Material Design theme, mobile responsive

**Guides:**
- [Installation](docs/user/installation/installation.md)
- [Architecture](docs/developer/architecture/overview.md)
- [Development Setup](docs/developer/development/setup.md)

## 🏗️ Built With

- [LlamaIndex](https://www.llamaindex.ai/) - RAG pipeline
- [Qdrant](https://qdrant.tech/) - Vector database
- [Ollama](https://ollama.ai/) - Local LLM management
- [Foundation-Sec-8B](https://huggingface.co/Foundation-Sec/Foundation-Sec-8B) - Cybersecurity AI model
- [Gradio](https://gradio.app/) - Web interface

## 📄 License

Apache 2.0 License - see [LICENSE](LICENSE) file

This project is based on [PrivateGPT](https://github.com/zylon-ai/private-gpt) and has been heavily customized for cybersecurity workflows.

## 🆘 Support

- [GitHub Issues](https://github.com/SecureYourGear/internal-assistant/issues)
- [Documentation](https://secureyourgear.github.io/internal-assistant/)
