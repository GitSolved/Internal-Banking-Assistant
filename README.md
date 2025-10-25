# Internal Banking Assistant

**AI-Powered Cybersecurity Intelligence Platform for Financial Institutions**

Privacy-first RAG platform built for banking, compliance, and security teams to automate threat monitoring, streamline regulatory research, and analyze vulnerabilities—100% locally with no external API dependencies.

---

## 🎯 Overview

**Internal Banking Assistant** empowers financial institutions to:
- 🛡️ Monitor real-time cybersecurity threats and vulnerabilities
- 📋 Automate regulatory compliance research (FDIC, SEC, NY DFS, FFIEC)
- 📄 Process and analyze security documents with AI-powered RAG
- 🔒 Operate completely offline for maximum privacy and regulatory safety

**Built on**: [Foundation-Sec-8B](https://huggingface.co/Foundation-Sec/Foundation-Sec-8B) cybersecurity AI model + [PrivateGPT](https://github.com/zylon-ai/private-gpt) RAG framework

---

## ✨ Key Features

### Core Capabilities
- **🤖 Cybersecurity-Trained AI**: Foundation-Sec-8B model specialized for threat analysis
- **📚 Document RAG**: Ingest PDFs, DOCX, and text files for intelligent search
- **📡 Threat Intelligence**: 14+ RSS feeds (CISA KEV, US-CERT, SANS ISC, NVD, etc.)
- **🔍 CVE Tracking**: Real-time vulnerability monitoring with severity filtering
- **⚖️ Compliance Automation**: FDIC, SEC, NY DFS regulatory update tracking
- **🔐 100% Private**: All processing happens locally—zero external API calls

### Advanced Features
- **🤝 Multi-Agent Support**: AutoGen integration for collaborative AI analysis ([guide](docs/developer/autogen-integration.md))
- **🔄 Parallel Development**: Multi-session workflow for team collaboration ([guide](docs/developer/parallel-sessions.md))
- **📊 MITRE ATT&CK**: Automated technique detection and threat categorization
- **⚡ Fast Performance**: 6-12s general queries, 12-20s RAG retrieval

---

## 🚀 Quick Start

### System Requirements
- **Python**: 3.11.9 - 3.11.x (any patch version)
- **RAM**: 8GB minimum (16GB+ recommended)
- **Storage**: 10GB+ free space
- **LLM Runtime**: [Ollama](https://ollama.ai/) (for local AI inference)

### Installation

#### Option 1: Poetry (Recommended)

```bash
# Clone repository
git clone https://github.com/GitSolved/Internal-Banking-Assistant.git
cd Internal-Banking-Assistant

# Install dependencies with Poetry 2.0+
poetry install --extras "ui llms-ollama embeddings-huggingface vector-stores-qdrant"

# Pull AI model via Ollama
ollama pull foundation-sec-8b-q4_k_m

# Start application
poetry run make run
# Or with Poetry shell activated:
# poetry shell
# make run
```

**Access**: Open http://localhost:8001 in your browser

#### Option 2: Docker

```bash
git clone https://github.com/GitSolved/Internal-Banking-Assistant.git
cd Internal-Banking-Assistant/config/deployment/docker
docker-compose up -d
```

**Access**: Open http://localhost:8001

### First Steps

1. **Upload Documents**: Click "Documents" tab → Upload PDFs/DOCX for RAG
2. **Monitor Threats**: Click "Feeds" tab → View real-time security intelligence
3. **Ask Questions**: Use chat interface for threat analysis or compliance queries
4. **Configure Settings**: Adjust models, profiles, and API settings as needed

---

## 📚 Documentation

### User Documentation
- 📘 **[Full Documentation Site](https://gitsolved.github.io/Internal-Banking-Assistant/)** - Complete user guide
- 🚀 **[Quick Start Guide](docs/user/usage/quickstart.md)** - Get started in 5 minutes
- ⚙️ **[Installation Guide](docs/user/installation/installation.md)** - Detailed setup instructions
- 🔧 **[Configuration](docs/user/configuration/settings.md)** - Settings and profiles
- 🆘 **[Troubleshooting](docs/user/installation/troubleshooting.md)** - Common issues and solutions

### Developer Documentation
- 👨‍💻 **[CLAUDE.md](CLAUDE.md)** - Comprehensive developer guide (21KB)
- 🏗️ **[Architecture Overview](docs/developer/architecture/overview.md)** - System design
- 🧪 **[Testing Guide](TEST_PARALLEL_SESSIONS.md)** - Hands-on testing procedures
- 🤖 **[AutoGen Integration](docs/developer/autogen-integration.md)** - Multi-agent AI setup
- 🔄 **[Parallel Sessions](docs/developer/parallel-sessions.md)** - Multi-developer workflow
- 📦 **[Package Structure](docs/developer/development/package-structure.md)** - Code organization

### API Documentation
- 🔌 **[API Reference](docs/api/reference/api-reference.md)** - REST API endpoints

---

## 💻 Usage Examples

### Threat Analysis
```
User: "Analyze CVE-2025-1234 for banking sector impact"

AI: "CVE-2025-1234 is a critical remote code execution vulnerability (CVSS 9.8)
     affecting CoreBanking Suite v12.x-14.3. Banking sector impact is HIGH:
     - Affects customer transaction processing systems
     - Enables unauthorized fund transfers
     - Compromises PII and financial data
     - SEC disclosure required within 4 business days (Regulation S-K Item 1.05)
     - Immediate patching to v14.4+ recommended"
```

### Compliance Research
```
User: "What are the latest NY DFS cybersecurity requirements for 2025?"
AI: [Searches RAG knowledge base + latest feeds]
    "NY DFS 23 NYCRR 500 updates for 2025 include:
     - Enhanced incident reporting (72-hour timeline)
     - Multi-factor authentication mandate for privileged accounts
     - Third-party vendor risk assessments..."
```

### Document Analysis
```
User: "Summarize the key points from this SEC filing"
AI: [Analyzes uploaded PDF]
    "Key findings from SEC Form 10-K:
     - Cybersecurity incident occurred Q3 2024
     - $2.3M remediation costs
     - No material impact on operations
     - Enhanced controls implemented..."
```

---

## 🛠️ Development

### Common Commands

```bash
# Running
make run              # Start application (port 8001)
make dev              # Development mode with auto-reload
make production       # Production mode (port 8000, secure)

# Testing
make test             # Run all tests
make test-coverage    # Generate coverage report

# Code Quality
make format           # Format code (black + ruff)
make mypy             # Type checking
make check            # Full quality check

# Data Management
make ingest path/to/docs  # Ingest documents into RAG
make stats            # Show database statistics
make wipe             # Delete all data (with confirmation)

# Parallel Development
make new-session name=feature-name component=server  # Create new dev session
make list-sessions    # View active work sessions
```

### Project Structure

```
Internal-Banking-Assistant/
├── internal_assistant/      # Main application package
│   ├── components/          # Core components (LLM, embeddings, vector store)
│   ├── server/              # FastAPI API endpoints
│   ├── ui/                  # Gradio web interface
│   └── settings/            # Configuration management
├── config/                  # YAML configuration files
├── docs/                    # Documentation (MkDocs)
├── tests/                   # Test suite
├── examples/                # Example code (AutoGen POC)
├── scripts/                 # Utility scripts
├── CLAUDE.md                # Developer guide for Claude Code
└── pyproject.toml           # Poetry dependencies
```

### Testing

```bash
# Run all tests
poetry run pytest tests -v

# Run specific test file
poetry run pytest tests/server/feeds/test_feeds_service.py -v

# Run with coverage
poetry run pytest tests --cov=internal_assistant --cov-report=html
```

### Contributing

We welcome contributions! To get started:

1. **Read** [CLAUDE.md](CLAUDE.md) for development guidelines
2. **Create** a feature branch: `git checkout -b feature/your-feature`
3. **Follow** code quality standards: `make format && make mypy`
4. **Test** your changes: `make test`
5. **Submit** a pull request

For parallel development with multiple contributors, see [Parallel Sessions Guide](docs/developer/parallel-sessions.md).

---

## 🏗️ Architecture

### Component Stack

```
┌─────────────────────────────────────────────┐
│           Gradio Web Interface              │  User-facing UI
├─────────────────────────────────────────────┤
│           FastAPI REST API                  │  API layer + endpoints
├─────────────────────────────────────────────┤
│    LlamaIndex RAG Pipeline                  │  Query processing
│    ├─ Foundation-Sec-8B (via Ollama)       │  LLM inference
│    ├─ nomic-embed-text-v1.5                │  Embeddings
│    └─ Qdrant Vector Store                   │  Vector search
├─────────────────────────────────────────────┤
│    Threat Intelligence Layer                │  RSS feeds + CVE tracking
│    ├─ 14+ Security Feeds                   │  Real-time updates
│    ├─ MITRE ATT&CK Integration             │  Technique mapping
│    └─ Compliance Monitoring                 │  FDIC/SEC/NY DFS
└─────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **LLM** | Foundation-Sec-8B (q4_k_m, 5.06GB) | Cybersecurity-trained AI |
| **LLM Runtime** | Ollama | Local model inference |
| **Embeddings** | nomic-embed-text-v1.5 (HuggingFace) | Document vectorization |
| **Vector DB** | Qdrant (embedded) | Similarity search |
| **API Framework** | FastAPI | REST API + async |
| **Web UI** | Gradio 4.15.0 | Interactive interface |
| **RAG Framework** | LlamaIndex 0.11.2 | Query processing |
| **Language** | Python 3.11.9+ | Core implementation |

### Data Flow

1. **User Query** → Gradio UI → FastAPI endpoint
2. **Query Embedding** → nomic-embed-text-v1.5 → Vector
3. **Vector Search** → Qdrant → Top-K relevant documents
4. **Context Assembly** → LlamaIndex → Prompt with context
5. **LLM Inference** → Foundation-Sec-8B via Ollama → Response
6. **Response** → FastAPI → Gradio UI → User

---

## 📊 Project Stats

- **Version**: 0.6.2
- **Python**: 3.11.9 - 3.11.x
- **Lines of Code**: 36,420 (Python)
- **License**: Apache 2.0
- **Based On**: [PrivateGPT](https://github.com/zylon-ai/private-gpt) (~30-40% code overlap)
- **Custom Code**: ~48,000+ lines for cybersecurity features
- **Security Feeds**: 14+ sources (CISA, US-CERT, SANS ISC, NVD, etc.)
- **Test Coverage**: Comprehensive test suite with pytest

---

## ⚖️ License & Attribution

### License
This project is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) for details.

### Attribution
**Internal Banking Assistant** is built on the [PrivateGPT](https://github.com/zylon-ai/private-gpt) RAG framework by [Zylon AI](https://github.com/zylon-ai), extensively specialized for cybersecurity intelligence workflows.

### What's Different from PrivateGPT

While sharing the foundational RAG infrastructure (~30-40% code overlap), Internal Banking Assistant adds:

- ✅ **Foundation-Sec-8B** cybersecurity-trained AI model (8B params)
- ✅ **14+ security RSS feeds** (CISA KEV, US-CERT, SANS ISC, NVD, etc.)
- ✅ **MITRE ATT&CK framework** integration with automated technique detection
- ✅ **CVE tracking and monitoring** with real-time vulnerability alerts
- ✅ **Threat intelligence analysis** with security recommendations
- ✅ **Compliance automation** (FDIC, SEC, NY DFS regulatory monitoring)
- ✅ **Custom security-focused UI** with threat dashboards
- ✅ **Banking-specific features** for financial sector use cases
- ✅ **AutoGen multi-agent support** for collaborative AI analysis
- ✅ **Parallel development workflow** for team collaboration
- ✅ **~48,000+ lines of custom code** for cybersecurity features

**Original Project**: [PrivateGPT by Zylon AI](https://github.com/zylon-ai/private-gpt)  
**Our Modifications**: Cybersecurity specialization, banking sector focus, custom features

---

## 🔗 Links

- **📘 Documentation**: [https://gitsolved.github.io/Internal-Banking-Assistant/](https://gitsolved.github.io/Internal-Banking-Assistant/)
- **🐙 Repository**: [https://github.com/GitSolved/Internal-Banking-Assistant](https://github.com/GitSolved/Internal-Banking-Assistant)
- **🐛 Issues**: [https://github.com/GitSolved/Internal-Banking-Assistant/issues](https://github.com/GitSolved/Internal-Banking-Assistant/issues)
- **📋 Releases**: [https://github.com/GitSolved/Internal-Banking-Assistant/releases](https://github.com/GitSolved/Internal-Banking-Assistant/releases)
- **👨‍💻 Developer Guide**: [CLAUDE.md](CLAUDE.md)
- **🤖 AutoGen Integration**: [docs/developer/autogen-integration.md](docs/developer/autogen-integration.md)

---

## 🙏 Acknowledgments

- **PrivateGPT** by [Zylon AI](https://github.com/zylon-ai) - Foundation RAG framework
- **Foundation-Sec-8B** by [Foundation Security](https://huggingface.co/Foundation-Sec) - Cybersecurity AI model
- **LlamaIndex** - RAG orchestration framework
- **Ollama** - Local LLM runtime
- **FastAPI** - Modern Python web framework
- **Gradio** - Interactive ML interfaces

---

## 📞 Support

- **Documentation**: Check [docs](https://gitsolved.github.io/Internal-Banking-Assistant/) first
- **Issues**: Open an [issue](https://github.com/GitSolved/Internal-Banking-Assistant/issues)
- **Discussions**: Start a [discussion](https://github.com/GitSolved/Internal-Banking-Assistant/discussions)
- **Security**: For security issues, see [SECURITY.md](SECURITY.md)

---

## 🗺️ Roadmap

### Planned Features
- [ ] Enhanced MITRE ATT&CK technique mapping
- [ ] Additional regulatory feed integrations (FinCEN, OCC)
- [ ] Advanced threat correlation across feeds
- [ ] Custom alert rules and notifications
- [ ] Multi-language support for documents
- [ ] Enhanced reporting and export features
- [ ] Kubernetes deployment manifests
- [ ] Integration with SIEM platforms

### In Progress
- [x] AutoGen multi-agent support (POC complete)
- [x] Parallel development workflow
- [x] GitHub Pages documentation
- [x] Python 3.11.x version range support

---

**Built with ❤️ for banking security teams**
