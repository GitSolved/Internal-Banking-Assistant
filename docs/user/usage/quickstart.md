# Quickstart Guide

This guide provides a quick start for running Internal Assistant using different profiles and setups. We'll cover Docker Compose setups for various environments and local installation options.

## Overview

Internal Assistant can be run in several ways:

- **Docker Compose** - Setup with pre-built images
- **Local Installation** - Direct installation on your system
- **Development Setup** - For contributors and developers

## Prerequisites

### For Docker Setup
- **Docker and Docker Compose**: Ensure both are installed on your system
  - [Docker Installation Guide](https://docs.docker.com/get-docker/)
  - [Docker Compose Installation Guide](https://docs.docker.com/compose/install/)

### For Local Setup
- **Python 3.9+**: Latest Python version recommended
- **Git**: For cloning the repository
- **Hardware**: GPU recommended for optimal performance

## Quick Start with Docker

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/internal-assistant.git
cd internal-assistant
```

### 2. Choose Your Profile

Internal Assistant provides several Docker Compose profiles for different environments:

#### CPU Profile (Default)
```bash
docker-compose up
```

#### GPU Profile (CUDA)
```bash
docker-compose --profile gpu up
```

#### MacOS Profile
```bash
docker-compose --profile macos up
```

#### Ollama Integration
```bash
docker-compose --profile ollama up
```

### 3. Access the Application

Once the services are running:

- **Web UI**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

## Quick Start with Local Installation

### 1. Clone and Setup

```bash
git clone https://github.com/your-org/internal-assistant.git
cd internal-assistant
```

### 2. Install Dependencies

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
```

### 3. Download Models

```bash
# Download default models
poetry run python scripts/download_models.py
```

### 4. Run the Application

```bash
# Activate virtual environment
poetry shell

# Run with default settings
make run
```

## Configuration Profiles

Internal Assistant supports multiple configuration profiles for different use cases:

### Local Profile (Default)
```bash
PGPT_PROFILES=local make run
```

### Mock Profile (Testing)
```bash
PGPT_PROFILES=mock make run
```

### OpenAI Profile
```bash
PGPT_PROFILES=openai make run
```

### Custom Profile
Create your own `settings-custom.yaml` and run:
```bash
PGPT_PROFILES=custom make run
```

## First Steps

### 1. Ingest Documents

Once the application is running, you can ingest documents:

**Via Web UI:**
1. Navigate to http://localhost:8001
2. Click "Upload Documents"
3. Select your files and upload

**Via API:**
```bash
curl -X POST "http://localhost:8001/v1/ingest/file" \
  -H "Authorization: Bearer your-api-key" \
  -F "file=@your-document.pdf"
```

### 2. Start Chatting

**Via Web UI:**
1. Go to the "Chat" tab
2. Type your question
3. Get AI-powered responses based on your documents

**Via API:**
```bash
curl -X POST "http://localhost:8001/v1/chat/completions" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is this document about?"}
    ]
  }'
```

## Docker Compose Profiles

### CPU Profile
Suitable for development and testing without GPU acceleration:

```yaml
# docker-compose.yml
services:
  internal-assistant:
    image: internal-assistant:latest
    profiles:
      - cpu
    environment:
      - PGPT_PROFILES=local
```

### GPU Profile
For systems with NVIDIA GPUs and CUDA support:

```yaml
# docker-compose.yml
services:
  internal-assistant:
    image: internal-assistant:gpu
    profiles:
      - gpu
    environment:
      - PGPT_PROFILES=local
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### MacOS Profile
Optimized for Apple Silicon and Intel Macs:

```yaml
# docker-compose.yml
services:
  internal-assistant:
    image: internal-assistant:macos
    profiles:
      - macos
    environment:
      - PGPT_PROFILES=local
```

### Ollama Profile
Integration with Ollama for local model management:

```yaml
# docker-compose.yml
services:
  internal-assistant:
    image: internal-assistant:latest
    profiles:
      - ollama
    environment:
      - PGPT_PROFILES=ollama
    depends_on:
      - ollama
  
  ollama:
    image: ollama/ollama:latest
    profiles:
      - ollama
    ports:
      - "11434:11434"
```

## Building Docker Images Locally

If you prefer to build images locally instead of using pre-built ones:

### 1. Build Base Image
```bash
docker build -t internal-assistant:base -f docker/Dockerfile.base .
```

### 2. Build Application Image
```bash
docker build -t internal-assistant:latest -f docker/Dockerfile .
```

### 3. Build GPU Image
```bash
docker build -t internal-assistant:gpu -f docker/Dockerfile.gpu .
```

### 4. Build MacOS Image
```bash
docker build -t internal-assistant:macos -f docker/Dockerfile.macos .
```

## Environment Variables

Configure the application using environment variables:

```bash
# API Configuration
export PGPT_API_KEY="your-api-key"
export PGPT_HOST="0.0.0.0"
export PGPT_PORT="8001"

# Model Configuration
export PGPT_MODEL_PATH="/models/llama-2-7b-chat.gguf"
export PGPT_EMBEDDING_MODEL="nomic-embed-text-v1.5"

# Database Configuration
export PGPT_VECTOR_DB="qdrant"
export PGPT_NODE_STORE="simple"

# Logging
export PGPT_LOG_LEVEL="INFO"
```

## Troubleshooting

### Common Issues

**Docker Issues:**
- Ensure Docker and Docker Compose are properly installed
- Check available disk space
- Verify port 8001 is not in use

**Local Installation Issues:**
- Ensure Python 3.9+ is installed
- Check Poetry installation
- Verify model files are downloaded

**Model Issues:**
- Ensure sufficient disk space for models
- Check model file integrity
- Verify GPU drivers (if using GPU)

### Getting Help

If you encounter issues:

1. Check the [Troubleshooting Guide](../installation/troubleshooting.md)
2. Review the [Configuration Documentation](../configuration/settings.md)
3. Open an issue on the project repository
4. Check the application logs for error messages

## Next Steps

After getting Internal Assistant running:

1. **Read the Documentation**: Explore the [User Guide](../usage/ingestion.md)
2. **Configure Settings**: Customize your [Configuration](../configuration/settings.md)
3. **Learn the API**: Review the [API Reference](../../api/reference/api-reference.md)
4. **Join the Community**: Connect with other users and contributors

For more detailed installation instructions, see the [Installation Guide](../installation/installation.md).
