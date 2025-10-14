# Document Ingestion

Ingest and manage documents in Internal Assistant.

## Ingestion Methods

### 1. Web UI Upload

1. Navigate to http://localhost:8001
2. Go to "Documents" tab
3. Click "Upload Documents"
4. Select files and upload

### 2. API Upload

**Single file:**
```bash
curl -X POST "http://localhost:8001/v1/ingest/file" \
  -F "file=@document.pdf"
```

**Multiple files:**
```bash
curl -X POST "http://localhost:8001/v1/ingest/files" \
  -F "files=@file1.pdf" \
  -F "files=@file2.docx"
```

### 3. Bulk Local Ingestion

For local setups, ingest entire folders:

```bash
poetry run make ingest /path/to/folder
```

**With file watching:**
```bash
poetry run make ingest /path/to/folder -- --watch
```

**Important**: Enable in settings first:
```yaml
data:
  local_ingestion:
    enabled: true
    allow_ingest_from: ["/path/to/folder"]
```

## Supported File Types

- **Documents**: PDF, DOCX, HWDOC, EPUB
- **Text**: TXT, MD
- **Presentations**: PPTX, PPT, PPTM
- **Data**: CSV, JSON
- **Code**: IPYNB
- **Media**: JPG, PNG, JPEG, MP3, MP4
- **Email**: MBOX

## Performance Optimization

### Ingestion Modes

Configure in `config/settings.yaml`:

```yaml
embedding:
  ingest_mode: parallel    # Options: simple, batch, parallel, pipeline
  count_workers: 4         # Number of parallel workers
```

**Mode comparison:**
- `simple`: Sequential, slowest but most stable
- `batch`: Batch processing, moderate speed
- `parallel`: Parallel processing, fastest for local
- `pipeline`: Alternative to parallel

### Memory Management

**If running out of memory during ingestion:**

Use mock LLM mode (disables LLM during ingestion):

```bash
PGPT_PROFILES=mock poetry run make ingest /path/to/folder
```

Configuration:
```yaml
llm:
  mode: mock
embedding:
  mode: local    # Keep embeddings active
```

## Document Management

### List Documents

```bash
curl -X GET "http://localhost:8001/v1/ingest/list"
```

### Delete Specific Document

```bash
curl -X DELETE "http://localhost:8001/v1/ingest/{doc_id}"
```

### Delete All Documents

```bash
curl -X DELETE "http://localhost:8001/v1/ingest"
```

Or use the command:
```bash
poetry run make wipe
```

## Troubleshooting

### Memory Errors
- Use `PGPT_PROFILES=mock` during ingestion
- Reduce `count_workers` in settings
- Process documents in smaller batches

### Slow Ingestion
- Increase `count_workers` (if memory allows)
- Use `parallel` or `batch` mode
- Ensure using SSD storage

### File Not Found
- Check file paths and permissions
- Verify file format is supported
- Ensure `local_ingestion.enabled: true` in settings

### Text Extraction Failures
- Check file corruption
- Try alternative file format
- Review ingestion logs in `local_data/logs/`

## Best Practices

- **Organize files** by topic before ingesting
- **Remove duplicates** to avoid redundancy
- **Use batch processing** for large document sets
- **Monitor resources** during ingestion
- **Validate results** after ingestion completes

## Next Steps

- [Reset Documents](./ingestion-reset.md) - Clear all ingested documents
- [Summarization](./summarize.md) - Summarize ingested documents
- [Configuration](../configuration/settings.md) - Adjust ingestion settings
