# API Reference

The API is divided in two logical blocks:

1. **High-level API**, abstracting all the complexity of a RAG (Retrieval Augmented Generation) pipeline implementation:
    - **Ingestion of documents**: internally managing document parsing, splitting, metadata extraction,
      embedding generation and storage.
    - **Chat & Completions** using context from ingested documents: abstracting the retrieval of context, the prompt
      engineering and the response generation.

2. **Low-level API**, allowing advanced users to implement their own complex pipelines:
    - **Embeddings generation**: based on a piece of text.
    - **Contextual chunks retrieval**: given a query, returns the most relevant chunks of text from the ingested
      documents.

## API Endpoints

### High-Level API

#### Chat Endpoints
- `POST /v1/chat/completions` - Generate chat completions with context from ingested documents
- `POST /v1/chat/completions/stream` - Stream chat completions

#### Ingestion Endpoints
- `POST /v1/ingest/file` - Ingest a single file
- `POST /v1/ingest/files` - Ingest multiple files
- `POST /v1/ingest/url` - Ingest content from a URL
- `DELETE /v1/ingest/{doc_id}` - Delete a specific document
- `DELETE /v1/ingest` - Delete all documents

### Low-Level API

#### Embeddings
- `POST /v1/embeddings` - Generate embeddings for text

#### Chunks
- `GET /v1/chunks` - Retrieve contextual chunks based on query

## Authentication

The API uses API key authentication. Include your API key in the request headers:

```bash
Authorization: Bearer your-api-key-here
```

## Rate Limits

Rate limits can be configured in the settings file based on your deployment requirements.

## Error Handling

The API returns standard HTTP status codes:

- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Rate Limited
- `500` - Internal Server Error

## Response Format

All successful responses follow this format:

```json
{
  "data": {
    // Response data
  },
  "meta": {
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "req_123456789"
  }
}
```

## Client Libraries

Use any OpenAI-compatible client library to interact with the API. The API follows OpenAI's specification for compatibility.

## Examples

### Chat Completion

```python
import requests

response = requests.post(
    "http://localhost:8001/v1/chat/completions",
    headers={
        "Authorization": "Bearer your-api-key",
        "Content-Type": "application/json"
    },
    json={
        "messages": [
            {"role": "user", "content": "What are the main features of Internal Assistant?"}
        ],
        "stream": False
    }
)

print(response.json())
```

### Document Ingestion

```python
import requests

with open("document.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post(
        "http://localhost:8001/v1/ingest/file",
        headers={"Authorization": "Bearer your-api-key"},
        files=files
    )

print(response.json())
```

## Additional Resources

- [Quick Start Guide](../../user/usage/quickstart.md) - Get started with Internal Assistant
- [Configuration](../../user/configuration/settings.md) - Configure the API
- [Developer Setup](../../developer/development/setup.md) - Set up development environment
