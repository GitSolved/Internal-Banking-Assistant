# Quick Start Guide

Get started with Internal Assistant quickly.

## Prerequisites

- Python 3.11.9 installed
- Poetry 2.0+ installed
- Git installed

See the [Installation Guide](../installation/installation.md) for detailed setup instructions.

## Quick Install

**1. Clone and Install**

```bash
git clone https://github.com/GitSolved/Internal-Banking-Assistant
cd internal-assistant
poetry install --extras "ui llms-ollama embeddings-huggingface vector-stores-qdrant"
```

**2. Install Ollama**

Visit [ollama.ai](https://ollama.ai/) and install Ollama, then start the service:

```bash
ollama serve
```

**3. Verify the Model**

```bash
ollama list  # Verify llama31-70b-m3max is available
```

**4. Run Internal Assistant**

```bash
poetry run make run
```

Access the UI at **http://localhost:8001**

## First Steps

### 1. Upload Documents

**Via Web UI:**
1. Navigate to http://localhost:8001
2. Go to the "Documents" tab
3. Click "Upload Documents"
4. Select your files (PDF, TXT, DOCX, etc.)
5. Click "Upload" and wait for processing

**Via API:**
```bash
curl -X POST "http://localhost:8001/v1/ingest/file" \
  -F "file=@your-document.pdf"
```

### 2. Chat with Your Documents

**Via Web UI:**
1. Go to the "Chat" tab
2. Select "Query documents" mode
3. Ask questions about your uploaded documents
4. Get AI-powered responses with source citations

**Via API:**
```bash
curl -X POST "http://localhost:8001/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What are the main security findings in the documents?"}
    ],
    "use_context": true
  }'
```

### 3. Threat Intelligence Feeds

1. Navigate to the "Feeds" tab
2. Browse available security RSS feeds
3. Click "Add Feed" to subscribe to threat intelligence sources
4. View latest security updates and alerts

## Configuration Profiles

Run Internal Assistant with different configurations:

**Default (Ollama):**
```bash
poetry run make run
```

**Mock Mode (Testing):**
```bash
PGPT_PROFILES=mock poetry run make run
```

**Development Mode:**
```bash
poetry run make dev
```

## Common Tasks

### Clear All Documents

```bash
poetry run make wipe
```

### View Logs

```bash
tail -f local_data/logs/SessionLog*.log
```

### Run Tests

```bash
poetry run make test
```

### Check Compatibility

```bash
poetry run make compatibility-check
```

## Troubleshooting

**Service won't start:**
- Ensure Ollama is running: `ollama list`
- Check port 8001 is available
- Review logs in `local_data/logs/`

**Document upload fails:**
- Check file format is supported
- Ensure sufficient disk space
- Review ingestion logs

**Model not found:**
- Verify the model: `ollama list` (should show llama31-70b-m3max)
- Verify Ollama is running: `ollama list`

For more issues, see the [Troubleshooting Guide](../installation/troubleshooting.md).

## Next Steps

- **Document Management**: Learn more about [Document Ingestion](./ingestion.md)
- **Configuration**: Customize your [Settings](../configuration/settings.md)
- **LLM Options**: Explore different [LLM Providers](../configuration/llms.md)
- **API Reference**: Use the [API Documentation](../../api/reference/api-reference.md)
