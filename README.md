# Internal Assistant - Cybersecurity Intelligence Platform

## ⚠️ Important: Dependency Compatibility

This project has **specific version constraints** to ensure compatibility and prevent the Pydantic schema generation error. The application will automatically validate these on startup.

### Required Versions (Enforced by Design)
- **Python**: 3.11.9 (exact version required)
- **FastAPI**: >=0.108.0,<0.115.0 (avoids Pydantic schema generation issues)
- **Pydantic**: >=2.8.0,<2.9.0 (compatible with LlamaIndex)
- **Gradio**: >=4.15.0,<4.39.0 (avoids FastAPI integration issues)

### Installation & Setup

For detailed installation instructions, see the [Installation Guide](docs/user/installation/installation.md).

**⚠️ Important: Package Structure**
This project uses the `internal_assistant` package structure. For import conventions and troubleshooting, see the [Package Structure Guide](docs/developer/development/package-structure.md).

**Quick Start:**
```bash
# 1. Ensure Python 3.11.9 is installed
python --version  # Should show 3.11.9

# 2. Install dependencies
poetry install --extras "ui llms-ollama embeddings-huggingface vector-stores-qdrant"

# 3. Run the application
make run
```

### 🔧 **Poetry-Enforced Scripts (Recommended)**

To ensure proper dependency isolation and prevent environment issues, use these Poetry-aware scripts:

```bash
# Quick environment verification
python verify.py                    # Basic check
python verify.py --full             # Detailed report
python verify.py --tests            # Verify all tests pass
python verify.py --component fastapi # Check specific component

# Run the application
python run_app.py                   # Production mode
python run_app.py --dev             # Development mode
python run_app.py --check           # Environment check only

# Run tests
python run_tests.py                 # All tests
python run_tests.py tests/ui/       # Specific test directory
python run_tests.py tests/ui/test_ui_integration.py # Specific test file

# Master verification (replaces old PowerShell scripts)
python master_verify.py             # Complete verification
python master_verify.py --quick     # Quick environment check
python master_verify.py --tests-only # Tests only
python master_verify.py --component fastapi # Check specific component
```

**Why use these scripts?**
- ✅ Automatic Poetry environment detection and usage
- ✅ Environment validation before execution
- ✅ Clear error messages for dependency issues
- ✅ Fallback support for different environments

### Environment Variables
The application uses environment variables for configuration. You can set them directly:

**Common Variables:**
- `HF_TOKEN`: HuggingFace token for embedding models (optional)
- `PGPT_PROFILES`: Configuration profile (default: "default")
- `PGPT_LOG_LEVEL`: Logging level (default: "INFO")

**Example:**
```bash
# Linux/Mac
export HF_TOKEN=your_token_here
export PGPT_PROFILES=local
make run

# Windows PowerShell
$env:HF_TOKEN="your_token_here"
$env:PGPT_PROFILES="local"
make run
```

### ✅ Installation Commands

For complete installation options, see the [Installation Guide](docs/user/installation/installation.md).

**Recommended:**
```bash
poetry install --extras "ui llms-ollama embeddings-huggingface vector-stores-qdrant"
```

### Compatibility Checks
- **Manual check**: `make compatibility-check`
- **Version enforcement**: `make version-enforce`
- **Comprehensive documentation**: `poetry run python dev/scripts/generate_compatibility_docs.py`
- **Auto-generated guide**: See [docs/compatibility/compatibility_guide.md](docs/compatibility/compatibility_guide.md)

### Log Management
- **Auto cleanup**: `make log-cleanup` (runs automatically before startup)
- **Check cleanup**: `make log-cleanup-dry-run` (see what would be removed)
- **Manual cleanup**: `poetry run python tools/maintenance/manage_logs.py --interactive`

**Note**: The application will automatically validate versions on startup and clean up old logs.

[![Tests](https://github.com/zylon-ai/private-gpt/actions/workflows/tests.yml/badge.svg)](https://github.com/zylon-ai/private-gpt/actions/workflows/tests.yml?query=branch%3Amain)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue)](https://your-org.github.io/internal-assistant/)
[![Internal Assistant](https://img.shields.io/badge/Internal%20Assistant-Cybersecurity%20AI-blue)](https://github.com/your-org/internal-assistant)

![Internal Assistant UI](/docs/assets/ui.png?raw=true)

**Internal Assistant** is an internal cybersecurity intelligence tool for threat analysis and security research. It provides a privacy-focused AI workspace for cybersecurity professionals.

## 🎯 Key Features

### **🔒 Privacy-First Architecture**
- **100% Private:** No data leaves your execution environment
- **Local Processing:** All AI operations run on your infrastructure
- **Secure by Design:** Built for sensitive cybersecurity data

### **🛡️ Cybersecurity Specialization**
- **Foundation-Sec-8B Model:** Specialized cybersecurity-trained AI model
- **Threat Intelligence:** RSS feeds, CVE databases, MITRE ATT&CK framework
- **Regulatory Compliance:** Enhanced content display for compliance documents
- **Security Research:** Optimized for security analysis workflows

### **⚡ Performance Configuration**
- **Quantization:** q4_k_m quantization for improved inference speed
- **Memory Optimized:** Reduced memory usage while maintaining quality
- **Response Times:** 6-20 seconds for most queries
- **Model:** Foundation-Sec-8B-q4_k_m.gguf (5.06 GB)

## 🚀 Quick Start

### **System Requirements**
- **Python:** 3.11+ (required)
- **RAM:** 8GB+ (recommended)
- **Storage:** 10GB+ for models and data
- **OS:** Windows, macOS, or Linux

### **Installation**

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-repo/internal-assistant.git
   cd internal-assistant
   ```

2. **Install with Poetry:**
   ```bash
   # Install base dependencies
   poetry install
   
   # Install with UI and cybersecurity optimizations
   poetry install --extras "ui llms-ollama vector-stores-qdrant embeddings-huggingface"
   ```

3. **Set up Ollama (required for Foundation-Sec-8B):**
   ```bash
   # Install Ollama from https://ollama.ai/
   
   # Download the Foundation-Sec-8B model file:
   # Download from: https://huggingface.co/Foundation-Sec/Foundation-Sec-8B
   # File: Foundation-Sec-8B-q4_k_m.gguf (5.06 GB)
   
   # Create the Ollama model:
   ollama create foundation-sec-q4km
   
   # Configure the model to use the downloaded file
   # Edit: ~/.ollama/models/foundation-sec-q4km/Modelfile
   # Add: FROM /path/to/Foundation-Sec-8B-q4_k_m.gguf
   ```

4. **Run the application:**
   ```bash
   make run
   # or
   poetry run python -m internal_assistant
   ```

5. **Access the UI:**
   - Open your browser to http://localhost:8001
   - The cybersecurity intelligence interface will be available

## 🔧 Operating Modes

### **General LLM Mode** (Default)
- **Purpose:** Fast general queries and cybersecurity analysis
- **Performance:** 6-12 seconds response time
- **Use Case:** Quick threat assessments, security questions, general analysis

### **RAG Mode** (Document-Based)
- **Purpose:** Document-based threat analysis and compliance research
- **Performance:** 12-20 seconds response time
- **Use Case:** Analyzing security documents, compliance reports, threat intelligence feeds

## 📊 Performance Metrics

### **Model Performance**
- **Model:** Foundation-Sec-8B-q4_k_m.gguf (5.06 GB)
- **Quantization:** q4_k_m quantization
- **Memory Usage:** ~4.5 GB (optimized single model load)
- **Quality:** Excellent - maintains high quality with optimization

### **Response Times**
- **Simple Math:** 8-10 seconds
- **General Questions:** 6-12 seconds
- **Document Queries:** 12-20 seconds
- **Cybersecurity Analysis:** 10-15 seconds

### **Optimizations**
- **System Prompts:** 10-20 tokens (optimized processing)
- **LLM Parameters:** Optimized for speed (max_new_tokens: 100)
- **RAG Settings:** Speed-optimized (similarity_top_k: 2)
- **Memory Management:** Single model operation for efficiency

## 🛡️ Cybersecurity Features

### **Threat Intelligence Integration**
- **RSS Feeds:** Real-time security news and threat updates
- **CVE Database:** Common Vulnerabilities and Exposures tracking
- **MITRE ATT&CK:** Adversary tactics, techniques, and procedures
- **Regulatory Feeds:** Compliance and regulatory information

### **Enhanced UI Features**
- **Horizontal Scrolling:** Optimized for regulatory information display
- **Content Enhancement:** Longer titles (120 chars) and summaries (200 chars)
- **Custom Styling:** Blue gradient theme
- **Compact Interface:** Reduced button heights for better UX

## 🏗️ Architecture & Development

### **UI Refactoring Progress**
- **Phase 1A:** ✅ Complete - Chat interface modularization
  - **Phase 1B:** ✅ Complete - Document management system (1,963 lines extracted)
    - DocumentUtilityBuilder (236 lines)
    - DocumentLibraryBuilder (492 lines)
    - DocumentEventHandlerBuilder (356 lines)
    - DocumentStateManager (527 lines)
    - FeedsDisplayBuilder (352 lines)
- **Phase 1C:** 🔄 In Progress - Feed event handlers extraction
- **Phase 1D:** 📋 Planned - Advanced UI componentization

### **Modular Architecture**
  - **Main UI:** 6,258 lines (down from 6,346 lines - 1.4% reduction)
  - **Component System:** 5 specialized components (1,963 total lines)
  - **Extraction Rate:** 30.9% of original code extracted to modular components
- **Service Integration:** Clean dependency injection patterns
- **Builder Pattern:** Consistent component creation methodology

### **Backup & Recovery**
- **Strategic Backups:** Complete backup system in `backup/` folder
- **Rollback Procedures:** Safe recovery procedures for each phase
- **Risk Mitigation:** Backup strategy for refactoring safety
- **Audit Trail:** Historical record of all refactoring changes

### **Security-Focused Configuration**
- **Privacy:** No data transmission to external services
- **Local Processing:** All AI operations on your infrastructure
- **Secure Storage:** Local vector database with encryption support
- **Audit Trail:** Logging for compliance requirements

## 📁 Storage Structure

The application uses two main storage directories with distinct purposes:

### `local_data/` - Application Runtime Data
- **Purpose**: Ephemeral data generated during application operation
- **Contents**: Logs, session data, vector database cache
- **Lifecycle**: Can be safely deleted and regenerated
- **Backup**: Optional - regenerable data

### `data/` - User Persistent Data  
- **Purpose**: Critical data that must be preserved
- **Contents**: Models, documents, processed content
- **Lifecycle**: Permanent - expensive to recreate
- **Backup**: Required - contains user data and large model files

```
├── local_data/          # Application runtime (regenerable)
│   ├── logs/           # Application and session logs
│   └── internal_assistant/  # Vector DB, app state
└── data/               # User persistent data (critical)
    ├── models/         # Model files, embeddings, caches
    ├── persistent/     # Documents, processed content
    └── runtime/        # Temporary caches
```

See `local_data/README.md` and `data/README.md` for detailed information.

## 🔧 Configuration

### **Current Dependencies Status**
Based on the `pyproject.toml` configuration:

#### **✅ ACTIVE COMPONENTS (Currently Used):**
- **LLM:** `llama-index-llms-ollama` - Foundation-Sec-8B via Ollama
- **Embeddings:** `llama-index-embeddings-huggingface` - nomic-embed-text-v1.5
- **Vector Store:** `llama-index-vector-stores-qdrant` - Qdrant disk-based storage
- **UI:** `gradio` + `ffmpy` - Web interface and media processing
- **Storage:** Simple nodestore (built into llama-index)

#### **🔧 USED BUT NOT PRIMARY:**
- **`llama-index-llms-llama-cpp`** - Model file management and settings
- **`llama-index-llms-openai-like`** - OpenAI-compatible API support

#### **📦 AVAILABLE BUT NOT USED:**
- **Vector Stores:** Chroma, PostgreSQL, ClickHouse, Milvus
- **LLMs:** OpenAI, Azure OpenAI, Google Gemini, AWS Sagemaker
- **Embeddings:** OpenAI, Azure, Gemini, Sagemaker, Ollama embeddings
- **Storage:** PostgreSQL nodestore
- **Reranking:** Sentence transformers (disabled for performance)

### **Model Configuration**
```yaml
# Primary model for cybersecurity analysis
llm:
  mode: ollama
  prompt_style: "llama2"
  max_new_tokens: 100
  context_window: 2048
  temperature: 0.1

ollama:
  llm_model: foundation-sec-q4km:latest
  embedding_model: nomic-embed-text
  api_base: http://localhost:11434

# Embedding model for document processing
embedding:
  mode: huggingface
  embed_dim: 768
  batch_size: 256
  max_length: 256

huggingface:
  embedding_hf_model_name: nomic-ai/nomic-embed-text-v1.5

# Vector storage for document indexing
vectorstore:
  database: qdrant

qdrant:
  path: local_data/internal_assistant/qdrant
```

### **Performance Settings**
```yaml
# RAG optimization for speed
rag:
  similarity_top_k: 2
  similarity_value: 0.3
  rerank:
    enabled: false  # Disabled for optimal performance

# LLM optimization
llm:
  max_new_tokens: 100
  context_window: 2048
  temperature: 0.1

# Embedding optimization
embedding:
  batch_size: 256
  max_length: 256
```

## 🚨 Troubleshooting

### **Ollama Model Issues**
If you encounter model loading errors:
```bash
# Verify Ollama installation
ollama --version

# Check model status
ollama list

# Recreate model if needed
ollama rm foundation-sec-q4km
ollama create foundation-sec-q4km
```

### **Performance Issues**
For slow response times:
1. **Check RAM usage:** Ensure 8GB+ available
2. **Verify model:** Confirm Foundation-Sec-8B is loaded
3. **Optimize settings:** Use recommended performance parameters
4. **Monitor resources:** Check CPU and memory utilization

### **UI Loading Issues**
If the interface doesn't load:
```bash
# Reinstall UI dependencies
poetry install --extras "ui llms-ollama vector-stores-qdrant embeddings-huggingface"

# Check Gradio version (should be 4.38.1)
poetry show gradio

# Clear cache and restart
rm -rf .pytest_cache/
make run
```

## 🧩 Architecture

Internal Assistant is built on a robust, privacy-focused architecture:

### **Core Components**
- **API Layer:** FastAPI with OpenAI-compatible endpoints
- **RAG Pipeline:** LlamaIndex-based document processing
- **Vector Store:** Qdrant for efficient document retrieval
- **UI Interface:** Gradio-based cybersecurity intelligence interface
- **Model Management:** llama-cpp integration for model file handling
- **API Compatibility:** openai-like layer for external API support

### **Security Features**
- **Dependency Injection:** Decoupled components for security
- **Local Processing:** No external API calls for AI operations
- **Encrypted Storage:** Secure document and model storage
- **Audit Logging:** Complete activity tracking

### **Performance Optimizations**
- **Single Model Operation:** Optimized for Foundation-Sec-8B
- **q4_k_m Quantization:** 25-35% speed improvement
- **Memory Management:** Efficient resource utilization
- **Caching:** Intelligent caching for repeated queries

## 🧪 Testing

### **Run Tests**
```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test categories
pytest tests/ui/ -v
pytest tests/server/ -v
```

### **Code Quality**
```bash
# Format code
make format

# Type checking
make mypy

# Linting
make ruff

# Full quality check
make check
```

## 🤝 Contributing

We welcome contributions to Internal Assistant! Please ensure:

1. **Code Quality:** Run `make check` before submitting
2. **Testing:** Add tests for new features
3. **Documentation:** Update docs for any changes
4. **Security:** Follow security best practices

### **Development Setup**
```bash
# Install development dependencies
poetry install --with dev

# Run in development mode
poetry run make dev

# Set up pre-commit hooks
pre-commit install
```

### **Modern Poetry Workflow**
This project uses Poetry 2.0+ with modern execution approach:

```bash
# Start application (recommended)
poetry run make run

# Development mode
poetry run make dev

# Run tests
poetry run make test

# Interactive development
poetry env activate
make run
deactivate
```

**Note:** `poetry shell` is deprecated in Poetry 2.0+. Use `poetry run` or `poetry env activate` instead.

## 📄 Documentation

The project uses **MkDocs** for documentation with full local control.

### **📋 Documentation Guidelines**
- **For Contributors**: See [Documentation Guidelines](docs/developer/development/documentation-guidelines.md) for creating new documentation
- **Agent Optimization**: All documentation must be transformed using [Documentation Transformation Prompt](docs/developer/guides/documentation-transformation-prompt.md)
- **Quality Standards**: Follow the established format and structure requirements

### **📚 Documentation Structure**
```
docs/                    # Source documentation (markdown)
├── user/               # User guides and configuration
├── developer/          # Architecture and development
│   ├── architecture/   # System design and planning
│   │   ├── overview.md # System architecture overview
│   │   ├── refactoring-guide.md # Comprehensive refactoring plan
│   │   └── document-categorization.md # Document categorization system
│   ├── development/    # Developer guides and tools
│   │   ├── setup.md    # Development environment setup
│   │   ├── package-structure.md # Package import conventions
│   │   └── import-quick-reference.md # Quick import reference
│   └── reports/        # Project status and audit reports
│       ├── folder-status-report.md # Project structure analysis
│       ├── documentation-cleanup.md # Documentation maintenance log
│       └── documentation-strategy.md # Documentation system overview
├── api/                # API reference  
└── assets/             # Images and logos

site/                   # Generated website (git-ignored)
├── index.html          # Built documentation site
├── search/             # Full-text search functionality
└── assets/             # Optimized CSS/JS/images
```

### **📖 Documentation Commands**
```bash
# Live development server with auto-reload
poetry run mkdocs serve

# Build static site (generates site/ folder)
poetry run mkdocs build

# View built documentation
open site/index.html    # macOS
start site/index.html   # Windows
```

### **🌐 Available Documentation**
- **Local:** `poetry run mkdocs serve` → http://localhost:8000
- **Built Site:** `site/index.html` (3.7MB, 21 pages, full search)
- **Source Files:** `docs/` directory (markdown format)

### **📝 Documentation Features**
- **Full-text search** with 25 language support
- **Material Design** theme with dark/light mode
- **Navigation** with automatic breadcrumbs
- **Mobile responsive** design
- **Fast build** (4-5 seconds for complete site)

## 🏗️ Built On

Internal Assistant is built on the solid foundation of:
- **[Advanced AI Framework](https://github.com/your-org/internal-assistant)** - Privacy-focused AI framework
- **[LlamaIndex](https://www.llamaindex.ai/)** - RAG pipeline framework
- **[Qdrant](https://qdrant.tech/)** - Vector database
- **[Ollama](https://ollama.ai/)** - Local LLM management
- **[Foundation-Sec-8B](https://huggingface.co/Foundation-Sec/Foundation-Sec-8B)** - Cybersecurity-trained model
- **[llama-cpp](https://github.com/ggerganov/llama.cpp)** - Model file management
- **[nomic-embed-text-v1.5](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5)** - Embedding model

## 📄 License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Discord:** [Join our community](https://discord.gg/bK6mRVpErU)
- **Issues:** [GitHub Issues](https://github.com/your-repo/internal-assistant/issues)
- **Documentation:** [Full documentation](https://your-org.github.io/internal-assistant/)

---

**Internal Assistant** - Empowering cybersecurity professionals with privacy-focused AI intelligence.
