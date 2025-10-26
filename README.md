# Internal-Banking-Assistant

**AI-Powered Risk & Compliance Platform for Financial Institutions**

Privacy-first RAG platform built for banking compliance officers, risk managers, and IT security teams to automate regulatory research, streamline compliance monitoring, and analyze security frameworks—100% locally with no external API dependencies.

---

## 🎯 Overview

**Internal Banking Assistant** empowers NYC-regulated financial institutions to:
- ⚖️ Automate regulatory compliance research (NY DFS, FDIC, SEC, FFIEC, OCC)
- 📋 Streamline IT security framework implementation (NIST, ISO 27001, SOC 2)
- 📄 Process and analyze policy documents, audits, and regulatory guidance with AI-powered RAG
- 🔒 Operate completely offline for maximum privacy and regulatory safety
- 🏢 Support cross-departmental workflows: Compliance, IT Security, Risk, Legal, Audit

**Built on**: [Llama 3.1 70B Instruct](https://huggingface.co/meta-llama/Llama-3.1-70B-Instruct) enterprise AI model + [PrivateGPT](https://github.com/zylon-ai/private-gpt) RAG framework

---

## ✨ Key Features

### Core Capabilities
- **🤖 Enterprise AI**: Llama 3.1 70B Instruct trained for banking compliance and IT security
- **📚 Document Intelligence**: Ingest and analyze policies, audits, regulations (PDFs, DOCX, text)
- **⚖️ Regulatory Monitoring**: 14+ feeds for NY DFS, FDIC, SEC, OCC, FFIEC, FinCEN updates
- **🛡️ IT Security Frameworks**: NIST CSF, ISO 27001, SOC 2, PCI DSS implementation guidance
- **📋 Compliance Automation**: Automated tracking of regulatory changes and requirements
- **🔐 100% Private**: All processing happens locally—zero external API calls

### Advanced Features
- **🤝 Multi-Agent Support**: AutoGen integration for collaborative compliance analysis ([guide](docs/developer/autogen-integration.md))
- **🔄 Cross-Departmental**: Shared knowledge base for Compliance, IT Security, Risk, Legal, Audit
- **📊 Policy Management**: Centralized repository for policies, procedures, and control documentation
- **⚡ Apple M3 Max Optimized**: GPU-accelerated inference on Apple Silicon (40 GPU cores)

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
ollama pull llama3.1:70b-instruct-q4_K_M

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

### Regulatory Compliance Research
```
User: "What are the NY DFS cybersecurity requirements for third-party risk management?"

AI: [Searches RAG knowledge base + NY DFS feeds]
    "NY DFS 23 NYCRR 500.11 requires covered entities to implement policies for:
     - Due diligence of third-party service providers accessing nonpublic information
     - Minimum cybersecurity practices required of service providers
     - Periodic assessment of service provider security controls
     - Annual certification of third-party vendor compliance (23 NYCRR 500.17)"
```

### IT Security Framework Implementation
```
User: "How do we implement NIST CSF Identify function for our organization?"
AI: [Analyzes uploaded NIST CSF guidance + internal policies]
    "NIST CSF Identify function implementation approach:
     - Asset Management (ID.AM): Create inventory of systems, data, personnel
     - Business Environment (ID.BE): Document mission, objectives, stakeholders
     - Governance (ID.GV): Establish policies, procedures, compliance requirements
     - Risk Assessment (ID.RA): Conduct enterprise risk assessment
     - Recommended timeline: 90 days for initial implementation"
```

### Policy and Audit Analysis
```
User: "Analyze our information security policy for NY DFS compliance gaps"
AI: [Analyzes uploaded policy document]
    "Gap analysis of Information Security Policy vs 23 NYCRR 500:
     ✅ Compliant: Access controls, encryption requirements (§500.15)
     ⚠️  Gap: Missing qualified CISO designation (§500.04)
     ⚠️  Gap: Incident response testing frequency undefined (§500.16)
     ⚠️  Gap: No penetration testing schedule specified (§500.05)
     Recommended actions: Update policy sections 4.2, 6.1, and 7.3"
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
│    ├─ Llama 3.1 70B Instruct (Ollama)     │  LLM inference
│    ├─ nomic-embed-text-v1.5                │  Embeddings
│    └─ Qdrant Vector Store                   │  Vector search
├─────────────────────────────────────────────┤
│    Regulatory & Compliance Feed Layer       │  Real-time monitoring
│    ├─ NY DFS 23 NYCRR 500                  │  NYS Banking Dept
│    ├─ FDIC Regulatory Updates              │  Federal Deposit Insurance
│    ├─ OCC Bulletins & Alerts               │  Office of Comptroller
│    ├─ FFIEC IT Examination Handbooks       │  Federal IT Standards
│    ├─ SEC Cyber Risk Management            │  Securities & Exchange
│    ├─ FinCEN AML/BSA Guidance              │  Anti-Money Laundering
│    ├─ Federal Reserve SR Letters           │  Fed guidance
│    ├─ NIST Cybersecurity Publications      │  Security frameworks
│    └─ CVE/NVD Vulnerability Feeds          │  IT security patches
└─────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **LLM** | Llama 3.1 70B Instruct (q4_K_M, ~40GB) | Enterprise banking AI |
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
5. **LLM Inference** → Llama 3.1 70B via Ollama → Response
6. **Response** → FastAPI → Gradio UI → User

---

## 📊 Project Stats

- **Version**: 0.6.2
- **Python**: 3.11.9 - 3.11.x
- **Lines of Code**: 36,420 (Python)
- **License**: Apache 2.0
- **Based On**: [PrivateGPT](https://github.com/zylon-ai/private-gpt) (~30-40% code overlap)
- **Custom Code**: ~48,000+ lines for banking compliance and IT security
- **Regulatory Feeds**: 16+ sources (NY DFS, FDIC, OCC, FFIEC, SEC, FinCEN, Fed, NIST, CVE/NVD)
- **Target Users**: Compliance Officers, IT Security Teams, Risk Managers, Legal, Audit
- **Test Coverage**: Comprehensive test suite with pytest

---

## ⚖️ License & Attribution

### License
This project is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) for details.

### Attribution
**Internal Banking Assistant** is built on the [PrivateGPT](https://github.com/zylon-ai/private-gpt) RAG framework by [Zylon AI](https://github.com/zylon-ai), extensively specialized for banking compliance and IT security workflows.

### What's Different from PrivateGPT

While sharing the foundational RAG infrastructure (~30-40% code overlap), Internal Banking Assistant adds:

- ✅ **Llama 3.1 70B Instruct** enterprise AI for banking compliance (70B params)
- ✅ **16+ regulatory feeds** (NY DFS, FDIC, OCC, FFIEC, SEC, FinCEN, Federal Reserve, NIST, CVE/NVD)
- ✅ **Banking compliance automation** (NY DFS 23 NYCRR 500, FDIC requirements, SEC guidance)
- ✅ **IT security framework support** (NIST CSF, ISO 27001, SOC 2, PCI DSS)
- ✅ **AML/BSA compliance** (FinCEN guidance, Bank Secrecy Act monitoring)
- ✅ **Policy and audit analysis** - gap analysis, control assessment, documentation review
- ✅ **Regulatory change tracking** - automatic monitoring of NY DFS, Federal Reserve, OCC bulletins
- ✅ **Cross-departmental workflows** - Compliance, IT Security, Risk, Legal, Audit
- ✅ **Custom banking UI** with regulatory dashboards and policy repositories
- ✅ **AutoGen multi-agent support** for collaborative compliance analysis
- ✅ **Apple M3 Max GPU acceleration** for optimized inference on Apple Silicon
- ✅ **~48,000+ lines of custom code** for banking compliance and IT security

**Original Project**: [PrivateGPT by Zylon AI](https://github.com/zylon-ai/private-gpt)
**Our Modifications**: Banking compliance specialization, NYC-regulated institution focus, regulatory automation

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
- **Llama 3.1** by [Meta AI](https://huggingface.co/meta-llama) - Enterprise language model
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
