# Architecture Overview

Internal Assistant is a cybersecurity intelligence platform built on FastAPI and LlamaIndex, designed for local, privacy-focused threat analysis.

**Related Documentation:**
- [Package Structure Guide](../development/package-structure.md) - Code organization and imports
- [Data Lifecycle](data-lifecycle.md) - Data management strategy
- [Development Setup](../development/setup.md) - Getting started with development

## System Architecture

Internal Assistant is a cybersecurity intelligence platform evolved from open-source RAG technology, designed for secure, local document processing and threat intelligence analysis.

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Internal Assistant                       │
├─────────────────────────────────────────────────────────────┤
│  Web Interface (Gradio)                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Chat UI   │  │  Document   │  │   Threat    │         │
│  │             │  │  Upload     │  │ Intelligence│         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│  API Layer (FastAPI)                                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Chat      │  │  Ingest     │  │   Feeds     │         │
│  │   API       │  │  API        │  │   API       │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│  Core Services                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   LLM       │  │ Embeddings  │  │ Vector Store│         │
│  │ (Ollama)    │  │(HuggingFace)│  │  (Qdrant)   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Models    │  │   Storage   │  │    Logs     │         │
│  │ (Local)     │  │  (Local)    │  │  (Local)    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Web Interface (Gradio)
- **Purpose**: Web interface for interaction
- **Technology**: Gradio with custom cybersecurity theme
- **Features**: Chat interface, document upload, threat intelligence dashboard

### 2. API Layer (FastAPI)
- **Purpose**: RESTful API for programmatic access
- **Technology**: FastAPI with automatic OpenAPI documentation
- **Endpoints**: Chat, ingestion, feeds, health, metadata

### 3. Core Services

#### LLM Service (Ollama)
- **Model**: Llama 3.1 70B Instruct (llama31-70b-m3max, ~42GB)
- **Alternative**: Foundation-Sec-8B-q4_k_m.gguf (4.7GB, cybersecurity-specialized)
- **Purpose**: Enterprise-grade language model with banking compliance expertise
- **Integration**: LlamaIndex LLM component

#### Embeddings Service (HuggingFace)
- **Model**: nomic-embed-text-v1.5
- **Purpose**: Document vectorization for similarity search
- **Integration**: LlamaIndex embeddings component

#### Vector Store (Qdrant)
- **Purpose**: Vector database
- **Features**: Similarity search, metadata filtering
- **Storage**: Local Qdrant instance

### 4. Data Layer

#### Models
- **Location**: Ollama manages models in `~/.ollama/models/`
- **Primary**: Llama 3.1 70B Instruct (~42GB)
- **Alternative**: Foundation-Sec-8B (~4.7GB, cybersecurity-specialized)
- **Management**: Ollama handles model storage and loading

#### Storage
- **Location**: `local_data/internal_assistant/`
- **Content**: Vector embeddings, document metadata
- **Technology**: Qdrant database files

#### Logs
- **Location**: `local_data/logs/`
- **Content**: Application logs, session logs
- **Management**: Automatic cleanup via `make log-cleanup`

## Data Flow

### Document Processing
```
1. Document Upload → 2. Text Extraction → 3. Chunking → 4. Embedding → 5. Vector Storage
```

### Query Processing
```
1. User Query → 2. Embedding → 3. Vector Search → 4. Context Retrieval → 5. LLM Response
```

### Threat Intelligence
```
1. RSS/Forum Feeds → 2. Content Parsing → 3. Threat Analysis → 4. Intelligence Dashboard
```

## Security Features

### Privacy-First Design
- **Local Processing**: All data processed locally
- **No External APIs**: No data sent to external services
- **Encrypted Storage**: Local data encryption
- **Access Control**: Configurable authentication

### Data Isolation
- **Separate Environments**: Development, testing, production
- **Configurable Storage**: Local file system or database
- **Log Management**: Automatic cleanup and rotation

## Configuration Management

### Configuration Files (Phase 2A Structure)
- **Base**: `config/settings.yaml` (always loaded)
- **Model-specific**: `config/model-configs/foundation-sec.yaml`, `ollama.yaml`
- **Environment**: `config/environments/local.yaml`, `test.yaml`, `docker.yaml`
- **Deployment**: `config/deployment/docker/docker-compose.yaml`

## Performance Characteristics

### Current Setup
- **LLM**: Llama 3.1 70B Instruct (~42GB, enterprise-grade) or Foundation-Sec-8B (4.7GB, cybersecurity-specialized alternative)
- **Embeddings**: nomic-embed-text-v1.5 (high-quality text embeddings)
- **Vector Store**: Qdrant (vector similarity search)
- **Storage**: Local file system (fast access, no network latency)

### Scalability Considerations
- **Horizontal Scaling**: API layer can be scaled independently
- **Vertical Scaling**: Model performance scales with hardware
- **Storage Scaling**: Vector store can be moved to external database

## Development Architecture

### Code Organization
```
internal_assistant/
├── components/           # Core components (LLM, embeddings, etc.)
├── server/              # API endpoints and services
├── ui/                  # Gradio interface components
├── settings/            # Configuration management
└── utils/               # Utility functions
```

### Testing Strategy
- **Unit Tests**: Component-level testing
- **Integration Tests**: API endpoint testing
- **UI Tests**: Interface functionality testing
- **Performance Tests**: Load and stress testing

## Future Enhancements

- **Multi-agent Collaboration**: Distributed threat analysis
- **Enhanced Intelligence**: Advanced pattern detection
- **Real-time Updates**: Live threat intelligence streaming
- **Cloud Integration**: Optional hybrid deployment
- **Advanced Analytics**: ML-based threat prediction
