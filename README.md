# Internal Assistant - Cybersecurity Intelligence Platform

**Internal AI RAG with Cybersecurity Sources**

A specialized cybersecurity intelligence platform built on RAG technology, designed for threat analysis and security research. Runs 100% locally with Foundation-Sec-8B model, MITRE ATT&CK integration, and real-time threat intelligence feeds.

![Internal Assistant UI](/docs/assets/ui.png?raw=true)

---

## 🎯 What Makes Internal Assistant Different

Internal Assistant transforms the RAG framework into a **cybersecurity-focused platform** with:

- **🛡️ Foundation-Sec-8B Model:** Cybersecurity-trained AI (q4_k_m quantization, 5.06 GB)
- **📡 14+ Security Feeds:** CISA KEV, US-CERT, SANS ISC, NIST NVD, The Hacker News, Dark Reading, and more
- **🎯 MITRE ATT&CK Integration:** Automated threat pattern detection and technique mapping
- **🔍 CVE Tracking:** Real-time vulnerability monitoring with severity filtering
- **🚨 Threat Intelligence:** Automated threat analysis, security recommendations, APT tracking
- **🔒 100% Private:** All processing happens locally—no data leaves your infrastructure

### Key Capabilities

| Feature | Description | Response Time |
|---------|-------------|---------------|
| **General LLM Mode** | Fast threat assessments and security queries | 6-12 seconds |
| **RAG Mode** | Document-based compliance research and analysis | 12-20 seconds |
| **Feed Monitoring** | Real-time security news and vulnerability tracking | Auto-refresh (60min) |
| **MITRE Analysis** | Threat technique identification and attack chain mapping | On-demand |

---

## 🚀 Quick Start

### System Requirements
- Python 3.11.9 (exact version required)
- 8GB+ RAM
- 10GB+ storage
- Ollama (for Foundation-Sec-8B model)

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/SecureYourGear/internal-assistant.git
cd internal-assistant/config/deployment/docker

# CPU-only
docker-compose --profile ollama-cpu up

# GPU support
docker-compose --profile ollama-cuda up
```

Access at **http://localhost:8001**

### Option 2: Local Development

```bash
git clone https://github.com/SecureYourGear/internal-assistant.git
cd internal-assistant

# Install dependencies
poetry install --extras "ui llms-ollama embeddings-huggingface vector-stores-qdrant"

# Set up Foundation-Sec-8B model
# See: https://huggingface.co/Foundation-Sec/Foundation-Sec-8B

# Run application
make run
```

Access at **http://localhost:8001**

**Documentation:** [Installation Guide](docs/user/installation/installation.md)

---

## 🛡️ Cybersecurity Features

### Threat Intelligence Feeds (14+ Sources)

**Government & Research:**
- 🏛️ US-CERT: Critical government cyber alerts
- 🚨 CISA KEV: Known exploited vulnerabilities catalog
- 🔬 SANS ISC: Security research and analysis
- 📊 NIST NVD: National vulnerability database

**Cybersecurity News:**
- 📰 The Hacker News
- 🌐 Dark Reading
- 💻 BleepingComputer

**Threat Intelligence:**
- 🦠 ThreatFox: Malware intelligence
- 🔐 AI Security: ML security research

**Regulatory & Financial:**
- 🏦 Federal Reserve
- 📑 SEC Filings

### MITRE ATT&CK Integration

- Automated technique extraction from threat reports
- Attack chain visualization
- Security recommendations by phase (Initial Access → Impact)
- Mitigation strategy suggestions

### CVE Tracking Panel

- Real-time vulnerability monitoring
- Severity filtering (Critical, High, Medium, Low)
- Vendor-specific filtering
- Time-based filtering (24h, 7d, 30d, 90d)
- MITRE technique mapping for vulnerabilities

---

## 🏗️ Architecture

### Technology Stack

- **LLM:** Ollama with Foundation-Sec-8B (cybersecurity-tuned model)
- **Embeddings:** HuggingFace nomic-embed-text-v1.5
- **Vector Store:** Qdrant (local, disk-based)
- **UI:** Gradio web interface (custom cybersecurity theme)
- **RAG Framework:** LlamaIndex
- **API:** FastAPI with dependency injection

### Design Principles

- **Privacy-First:** Local processing, no external data transmission
- **Modular Architecture:** 44% code reduction from refactoring (6,258 → 3,500 lines)
- **Event-Driven UI:** Decoupled components with clean event routing
- **Secure Storage:** Local vector database with encryption support

### Storage Structure

- **`local_data/`** - Ephemeral runtime data: logs, session data, vector DB cache
- **`data/`** - Persistent user data: models, documents, processed content

---

## 🔧 Configuration

### Core Settings (`config/settings.yaml`)

```yaml
llm:
  mode: ollama
  model: foundation-sec-q4km:latest
  temperature: 0.1  # Low for consistent security analysis

embedding:
  mode: huggingface
  model: nomic-ai/nomic-embed-text-v1.5

vectorstore:
  database: qdrant
  path: local_data/internal_assistant/qdrant

rag:
  similarity_top_k: 8
  rerank.enabled: false  # Disabled for performance
```

### Environment-Specific Configs

- `config/environments/local.yaml` - Local development
- `config/environments/docker.yaml` - Docker deployment
- `config/environments/test.yaml` - Testing environment

---

## 🧪 Development

### Testing

```bash
make test                # Run all tests
make test-coverage       # Run with coverage report

# Run specific tests
poetry run pytest tests/server/feeds/
poetry run pytest tests/ui/test_ui.py::test_name
```

### Code Quality

```bash
make format              # Format code (black + ruff)
make mypy                # Type checking
make check               # Full quality check (format + mypy + compatibility)
make compatibility-check # Verify dependency versions
```

### Development Commands

```bash
make run                 # Start application (production mode)
make dev                 # Development mode with auto-reload
make ingest path/to/docs # Ingest documents into RAG
make stats               # Database statistics
make wipe                # Delete all data (requires confirmation)
```

---

## 📄 Documentation

### Serve Locally

```bash
poetry run mkdocs serve  # Access at http://localhost:8000
poetry run mkdocs build  # Build static site
```

### Guides

- **User Documentation:**
  - [Installation Guide](docs/user/installation/installation.md)
  - [Configuration](docs/user/configuration/llms.md)
  - [Ingestion](docs/user/usage/ingestion.md)
  - [Quick Start](docs/user/usage/quickstart.md)

- **Developer Documentation:**
  - [Architecture Overview](docs/developer/architecture/overview.md)
  - [Development Setup](docs/developer/development/setup.md)
  - [Package Structure](docs/developer/development/package-structure.md)

---

## 🚨 Troubleshooting

### Common Issues

```bash
# Verify Ollama and model
ollama list

# Reinstall dependencies
poetry install --extras "ui llms-ollama vector-stores-qdrant embeddings-huggingface"

# Check compatibility
make compatibility-check

# Health check
make health-check
```

See [Troubleshooting Guide](docs/user/installation/troubleshooting.md) for detailed solutions.

---

## 🤝 Contributing

Contributions welcome! Please:
1. Run `make check` before submitting
2. Add tests for new features
3. Update documentation

### Development Setup

```bash
# Install with dev dependencies
poetry install --with dev

# Run development server
poetry run make dev
```

**Note:** This project uses Poetry 2.0+. Use `poetry run <command>` or `poetry env activate` instead of deprecated `poetry shell`.

---

## 📦 Built With

- [LlamaIndex](https://www.llamaindex.ai/) - RAG pipeline framework
- [Qdrant](https://qdrant.tech/) - Vector database
- [Ollama](https://ollama.ai/) - Local LLM management
- [Foundation-Sec-8B](https://huggingface.co/Foundation-Sec/Foundation-Sec-8B) - Cybersecurity AI model
- [Gradio](https://gradio.app/) - Web interface
- [FastAPI](https://fastapi.tiangolo.com/) - API framework

---

## ⚖️ Attribution & License

**Internal Assistant** is built on the [PrivateGPT](https://github.com/zylon-ai/private-gpt) RAG framework and has been extensively specialized for cybersecurity intelligence workflows.

### What's Different from PrivateGPT

While sharing the foundational RAG infrastructure (~30-40% code overlap), Internal Assistant adds:

- **Foundation-Sec-8B** cybersecurity-trained AI model
- **14+ security RSS feeds** (CISA KEV, US-CERT, SANS ISC, etc.)
- **MITRE ATT&CK framework** integration with automated technique detection
- **CVE tracking and monitoring** with real-time vulnerability alerts
- **Threat intelligence analysis** with security recommendations
- **Custom security-focused UI** with threat dashboards
- **~48,000+ lines of custom code** for cybersecurity features

**Original Project:** [PrivateGPT by Zylon AI](https://github.com/zylon-ai/private-gpt)
**License:** Apache 2.0 (maintained from original)
**Copyright:** See [LICENSE](LICENSE) file

---

This project is based on [PrivateGPT](https://github.com/zylon-ai/private-gpt) and has been heavily customized for cybersecurity workflows.

## 🆘 Support

- **Issues:** [GitHub Issues](https://github.com/SecureYourGear/internal-assistant/issues)
- **Documentation:** [https://secureyourgear.github.io/internal-assistant/](https://secureyourgear.github.io/internal-assistant/)

---

## 📊 Project Stats

- **Version:** 0.6.2
- **Python:** 3.11.9 (required)
- **License:** Apache 2.0
- **Repository:** [SecureYourGear/internal-assistant](https://github.com/SecureYourGear/internal-assistant)
