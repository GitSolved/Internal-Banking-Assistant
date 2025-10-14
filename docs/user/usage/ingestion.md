# Ingesting & Managing Documents

The ingestion of documents can be done in different ways:

- Using the `/ingest` API
- Using the Gradio UI
- Using the Bulk Local Ingestion functionality

## Bulk Local Ingestion

You will need to activate `data.local_ingestion.enabled` in your setting file to use this feature. Additionally,
it is probably a good idea to set `data.local_ingestion.allow_ingest_from` to specify which folders are allowed to be ingested.

!!! warning "Security Warning"
    Be careful enabling this feature in a production environment, as it can be a security risk, as it allows users to
    ingest any local file with permissions.

When you are running Internal Assistant in a fully local setup, you can ingest a complete folder for convenience (containing
pdf, text files, etc.) and optionally watch changes on it with the command:

```bash
make ingest /path/to/folder -- --watch
```

To log the processed and failed files to an additional file, use:

```bash
make ingest /path/to/folder -- --watch --log-file /path/to/log/file.log
```

!!! note "Windows Users"
    Depending on your Windows version and whether you are using PowerShell to execute
    Internal Assistant API calls, you may need to include the parameter name before passing the folder path for consumption:

    ```bash
    make ingest arg=/path/to/folder -- --watch --log-file /path/to/log/file.log
    ```

After ingestion is complete, you should be able to chat with your documents
by navigating to http://localhost:8001 and using the option `Query documents`,
or using the completions / chat API.

## Ingestion Troubleshooting

### Running out of memory

To not run out of memory, you should ingest your documents without the LLM loaded in your (video) memory.
To do so, you should change your configuration to set `llm.mode: mock`.

You can also use the existing `PGPT_PROFILES=mock` that will set the following configuration for you:

```yaml
llm:
  mode: mock
embedding:
  mode: local
```

This configuration allows you to use hardware acceleration for creating embeddings while avoiding loading the full LLM into (video) memory.

Once your documents are ingested, you can set the `llm.mode` value back to `local` (or your previous custom value).

### Ingestion speed

The ingestion speed depends on the number of documents you are ingesting, and the size of each document.
To speed up the ingestion, you can change the ingestion mode in configuration.

The following ingestion modes exist:

- **`simple`**: historic behavior, ingest one document at a time, sequentially
- **`batch`**: read, parse, and embed multiple documents using batches (batch read, and then batch parse, and then batch embed)
- **`parallel`**: read, parse, and embed multiple documents in parallel. This is the fastest ingestion mode for local setup.
- **`pipeline`**: Alternative to parallel.

To change the ingestion mode, you can use the `embedding.ingest_mode` configuration value. The default value is `simple`.

To configure the number of workers used for parallel or batched ingestion, you can use
the `embedding.count_workers` configuration value. If you set this value too high, you might run out of
memory, so be mindful when setting this value. The default value is `2`.

For `batch` mode, you can easily set this value to your number of threads available on your CPU without
running out of memory. For `parallel` mode, you should be more careful, and set this value to a lower value.

The configuration below should be enough for users who want to stress more their hardware:

```yaml
embedding:
  ingest_mode: parallel
  count_workers: 4
```

If you have sufficient hardware resources and are loading large documents, you can increase the number of workers.
It is recommended to do your own tests to find the optimal value for your hardware.

If you have a `bash` shell, you can use this set of command to do your own benchmark:

```bash
# Wipe your local data, to put yourself in a clean state
# This will delete all your ingested documents
make wipe

time PGPT_PROFILES=mock python ./tools/data/ingest_folder.py ~/my-dir/to-ingest/
```

## Supported File Types

Internal Assistant supports a wide range of document formats:

### Text Files
- `.txt` - Plain text files
- `.md` - Markdown files
- `.rst` - reStructuredText files

### Office Documents
- `.pdf` - PDF documents
- `.docx` - Microsoft Word documents
- `.doc` - Legacy Word documents
- `.pptx` - PowerPoint presentations
- `.xlsx` - Excel spreadsheets

### Web Content
- `.html` - HTML files
- `.htm` - HTML files
- URLs - Direct web page ingestion

### Code Files
- `.py` - Python files
- `.js` - JavaScript files
- `.java` - Java files
- `.cpp` - C++ files
- `.c` - C files
- `.h` - Header files
- `.cs` - C# files
- `.php` - PHP files
- `.rb` - Ruby files
- `.go` - Go files
- `.rs` - Rust files
- `.swift` - Swift files
- `.kt` - Kotlin files
- `.scala` - Scala files

### Data Files
- `.csv` - Comma-separated values
- `.json` - JSON files
- `.xml` - XML files
- `.yaml` - YAML files
- `.yml` - YAML files

## Document Processing

### Text Extraction

Internal Assistant uses specialized libraries to extract text from different file formats:

- **PDF**: Uses PyPDF2 and pdfplumber for text extraction
- **Office Documents**: Uses python-docx, openpyxl, and python-pptx
- **Web Pages**: Uses requests and BeautifulSoup for HTML parsing
- **Code Files**: Direct text reading with syntax highlighting support

### Chunking Strategy

Documents are automatically split into chunks for optimal retrieval:

- **Default chunk size**: 512 tokens
- **Chunk overlap**: 50 tokens
- **Smart splitting**: Respects paragraph and section boundaries
- **Code preservation**: Maintains code structure and comments

### Metadata Extraction

Each document chunk includes metadata:

- **Source file**: Original filename and path
- **Chunk index**: Position within the document
- **File type**: Document format
- **Creation date**: When the document was ingested
- **Custom metadata**: User-defined tags and properties

## API Endpoints

### Single File Ingestion

```bash
curl -X POST "http://localhost:8001/v1/ingest/file" \
  -H "Authorization: Bearer your-api-key" \
  -F "file=@document.pdf"
```

### Multiple Files Ingestion

```bash
curl -X POST "http://localhost:8001/v1/ingest/files" \
  -H "Authorization: Bearer your-api-key" \
  -F "files=@file1.pdf" \
  -F "files=@file2.docx"
```

### URL Ingestion

```bash
curl -X POST "http://localhost:8001/v1/ingest/url" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/document"}'
```

### Document Deletion

```bash
# Delete specific document
curl -X DELETE "http://localhost:8001/v1/ingest/doc_id" \
  -H "Authorization: Bearer your-api-key"

# Delete all documents
curl -X DELETE "http://localhost:8001/v1/ingest" \
  -H "Authorization: Bearer your-api-key"
```

## Best Practices

### File Organization

- **Use descriptive filenames**: Clear, meaningful names help with document identification
- **Organize by topic**: Group related documents in folders
- **Avoid duplicates**: Remove duplicate files before ingestion
- **Check file quality**: Ensure documents are readable and complete

### Performance Optimization

- **Batch processing**: Use bulk ingestion for large document collections
- **Memory management**: Use mock LLM mode for ingestion on memory-constrained systems
- **Parallel processing**: Enable parallel ingestion for faster processing
- **Monitor resources**: Watch CPU and memory usage during ingestion

### Security Considerations

- **Validate file types**: Only ingest trusted document formats
- **Scan for malware**: Check files before ingestion in production environments
- **Limit access**: Restrict bulk ingestion to authorized users only
- **Audit trails**: Monitor ingestion activities for security compliance

## Troubleshooting

### Common Issues

**File not found errors**
- Check file paths and permissions
- Ensure files are accessible to the application
- Verify file format is supported

**Memory errors during ingestion**
- Reduce `count_workers` value
- Use mock LLM mode
- Process documents in smaller batches

**Slow ingestion speed**
- Enable parallel or batch mode
- Increase worker count (if memory allows)
- Use SSD storage for better I/O performance

**Text extraction failures**
- Check file corruption
- Verify file format support
- Try alternative extraction methods

### Getting Help

If you encounter issues with document ingestion:

1. Check the application logs for error messages
2. Verify your configuration settings
3. Test with a simple text file first
4. Consult the [troubleshooting guide](../installation/troubleshooting.md)
5. Open an issue on the project repository
