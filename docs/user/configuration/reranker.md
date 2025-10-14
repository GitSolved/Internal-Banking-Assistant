# Reranker Configuration

Internal Assistant includes a document reranking feature that enhances response quality by filtering out irrelevant documents before generating answers. This can significantly improve both response relevance and generation speed.

## Overview

Document reranking works by:

1. **Initial Retrieval**: Retrieving a larger set of potentially relevant documents
2. **Reranking**: Using a cross-encoder model to score document relevance
3. **Filtering**: Selecting only the most relevant documents for answer generation

This two-stage approach provides better results than simple similarity search alone.

## Benefits

- **Improved Relevance**: More accurate document selection
- **Faster Responses**: Reduced processing time with fewer documents
- **Better Context**: Higher quality context for the LLM
- **Reduced Noise**: Filtering out irrelevant information

## Installation

Before using reranking, install the required dependencies:

```bash
poetry install --extras rerank-sentence-transformers
```

This installs the cross-encoder reranker from sentence-transformers, which is currently the only supported reranking method.

## Configuration

Enable and configure reranking in the `rag` section of your `settings.yaml` file:

```yaml
rag:
  similarity_top_k: 10  # Number of documents to retrieve initially
  rerank:
    enabled: true
    top_n: 3  # Number of top-ranked documents to use
```

### Configuration Options

| Field | Description | Default | Recommended |
|-------|-------------|---------|-------------|
| `similarity_top_k` | Number of documents to retrieve and consider for reranking | `10` | `10-20` |
| `rerank.enabled` | Enable/disable reranking feature | `false` | `true` |
| `rerank.top_n` | Number of top-ranked documents to use for answer generation | `3` | `3-5` |

### Advanced Configuration

For fine-tuning reranking performance:

```yaml
rag:
  similarity_top_k: 15
  rerank:
    enabled: true
    top_n: 4
    model: cross-encoder/ms-marco-MiniLM-L-6-v2  # Optional: specify model
    batch_size: 32  # Optional: batch size for processing
```

## How It Works

### Step 1: Initial Retrieval

The system retrieves `similarity_top_k` documents using vector similarity search:

```yaml
rag:
  similarity_top_k: 10  # Retrieve 10 documents
```

### Step 2: Reranking

A cross-encoder model scores each document's relevance to the query:

```yaml
rag:
  rerank:
    enabled: true
    # Uses cross-encoder to score relevance
```

### Step 3: Final Selection

Only the top `top_n` documents are used for answer generation:

```yaml
rag:
  rerank:
    top_n: 3  # Use only the 3 most relevant documents
```

## Performance Considerations

### Memory Usage

Reranking requires additional memory for the cross-encoder model:

- **Model Size**: ~100MB for default model
- **Batch Processing**: Memory scales with batch size
- **Document Length**: Longer documents use more memory

### Processing Time

Reranking adds processing time but improves quality:

- **Initial Retrieval**: Fast vector similarity search
- **Reranking**: Slower but more accurate scoring
- **Overall**: Usually faster due to fewer documents in final generation

### Optimization Tips

**For Speed:**
```yaml
rag:
  similarity_top_k: 8
  rerank:
    enabled: true
    top_n: 2
    batch_size: 64
```

**For Quality:**
```yaml
rag:
  similarity_top_k: 20
  rerank:
    enabled: true
    top_n: 5
    batch_size: 16
```

## Model Selection

### Default Model

The default cross-encoder model is optimized for general document retrieval:

- **Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Size**: ~100MB
- **Performance**: Good balance of speed and accuracy

### Alternative Models

You can specify different models for specific use cases:

```yaml
rag:
  rerank:
    enabled: true
    model: cross-encoder/ms-marco-MiniLM-L-12-v2  # Larger, more accurate
    # or
    model: cross-encoder/ms-marco-TinyBERT-L-6  # Smaller, faster
```

### Model Comparison

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| `ms-marco-MiniLM-L-6-v2` | ~100MB | Fast | Good | General purpose |
| `ms-marco-MiniLM-L-12-v2` | ~200MB | Medium | Better | High accuracy needed |
| `ms-marco-TinyBERT-L-6` | ~50MB | Very Fast | Adequate | Resource constrained |

## Use Cases

### General Document Q&A

```yaml
rag:
  similarity_top_k: 10
  rerank:
    enabled: true
    top_n: 3
```

### Technical Documentation

```yaml
rag:
  similarity_top_k: 15
  rerank:
    enabled: true
    top_n: 4
    model: cross-encoder/ms-marco-MiniLM-L-12-v2
```

### Large Document Collections

```yaml
rag:
  similarity_top_k: 20
  rerank:
    enabled: true
    top_n: 5
    batch_size: 32
```

### Resource-Constrained Environments

```yaml
rag:
  similarity_top_k: 8
  rerank:
    enabled: true
    top_n: 2
    model: cross-encoder/ms-marco-TinyBERT-L-6
    batch_size: 64
```

## Troubleshooting

For reranker-specific issues, see the [main troubleshooting guide](../installation/troubleshooting.md#reranker-issues).

### Performance Monitoring

Monitor these metrics when using reranking:

- **Retrieval Time**: Time to get initial documents
- **Reranking Time**: Time to score and rank documents
- **Memory Usage**: RAM usage during reranking
- **Response Quality**: Relevance of final answers

### Debugging

Enable debug logging to troubleshoot reranking:

```yaml
logging:
  level: DEBUG
  loggers:
    internal_assistant.components.rag: DEBUG
```

## Best Practices

### Configuration Guidelines

1. **Start with Defaults**: Use the default configuration first
2. **Adjust Based on Use Case**: Modify parameters for your specific needs
3. **Monitor Performance**: Track response time and quality
4. **Test Different Models**: Try different models for optimal results

### Optimization Strategy

1. **Set `similarity_top_k`**: 2-3x larger than `top_n`
2. **Choose `top_n`**: Based on desired context size
3. **Select Model**: Balance accuracy vs. performance
4. **Tune Batch Size**: Optimize for your hardware

### Quality vs. Speed Trade-offs

**For Maximum Quality:**
```yaml
rag:
  similarity_top_k: 20
  rerank:
    enabled: true
    top_n: 5
    model: cross-encoder/ms-marco-MiniLM-L-12-v2
```

**For Maximum Speed:**
```yaml
rag:
  similarity_top_k: 8
  rerank:
    enabled: true
    top_n: 2
    model: cross-encoder/ms-marco-TinyBERT-L-6
    batch_size: 64
```

## Integration with Other Features

### Embedding Models

Reranking works with all supported embedding models:

- **Local Models**: Sentence transformers, OpenAI embeddings
- **Cloud Models**: OpenAI, Azure, etc.
- **Custom Models**: Any compatible embedding model

### Vector Databases

Reranking is compatible with all vector database providers:

- **Qdrant**: Default vector database
- **Milvus**: Production vector database
- **Chroma**: Simple embedding database
- **PGVector**: PostgreSQL extension
- **ClickHouse**: Analytical database

### LLM Models

Reranking improves results with all LLM models:

- **Local Models**: Llama, Mistral, etc.
- **Cloud Models**: OpenAI, Azure, etc.
- **Custom Models**: Any compatible LLM

## Future Enhancements

Planned improvements to the reranking system:

- **Multiple Reranking Models**: Support for different reranking approaches
- **Custom Reranking**: User-defined reranking logic
- **Adaptive Reranking**: Automatic parameter optimization
- **Batch Processing**: Improved batch handling for large datasets

For more information on RAG configuration, see the [RAG Settings](settings.md) documentation.
