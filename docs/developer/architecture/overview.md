# Architecture Overview

This document provides an overview of the Internal Assistant architecture.

**Related Documentation:**
- [Package Structure Guide](../development/package-structure.md) - Implementation details
- [Refactoring Guide](refactoring-guide.md) - Detailed codebase analysis and improvement plan
- [Document Categorization](document-categorization.md) - System feature documentation

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
- **Model**: Foundation-Sec-8B-q4_k_m.gguf (4.7GB)
- **Purpose**: Cybersecurity-focused language model
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
- **Location**: `models/` directory
- **Content**: Foundation-Sec-8B model file (4.7GB)
- **Future**: Will move to `data/models/files/`

#### Storage
- **Location**: `data/persistent/storage/`
- **Content**: Vector embeddings, document metadata
- **Technology**: Qdrant database files

#### Logs
- **Location**: `local_data/logs/`
- **Content**: Application logs, session logs
- **Management**: Automatic cleanup (keep last 7 sessions)

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

### Environment-Based Configuration
- **Local Development**: `config/environments/local.yaml`
- **Testing**: `config/environments/test.yaml`
- **Production**: `config/environments/docker.yaml`

### Model Configuration
- **LLM Settings**: `config/model-configs/foundation-sec.yaml`
- **Embedding Settings**: `config/model-configs/ollama.yaml`
- **Vector Store**: `config/model-configs/qdrant.yaml`

## Performance Characteristics

### Current Setup
- **LLM**: Foundation-Sec-8B (4.7GB, optimized for cybersecurity)
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

## Future Architecture

### Planned Improvements
- **Modular UI**: Refactor monolithic ui.py (8,618 lines) - IN PROGRESS (49 lines extracted in Phase 1A.1)
- **AI Agent Collaboration**: Multi-agent system for threat analysis
- **Enhanced Intelligence**: Advanced threat detection algorithms
- **Real-time Feeds**: Live threat intelligence updates

### Scalability Roadmap
- **Distributed Processing**: Multi-node deployment
- **Cloud Integration**: Optional cloud-based components
- **Advanced Analytics**: Machine learning threat detection
- **API Ecosystem**: Third-party integrations
