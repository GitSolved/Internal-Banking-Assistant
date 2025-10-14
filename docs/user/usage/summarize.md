# Document Summarization

The Summarize feature provides a method to extract concise summaries from ingested documents or text using Internal Assistant. This tool is particularly useful for quickly understanding large volumes of information by distilling key points and main ideas.

## Overview

Document summarization helps you:

- **Extract Key Information**: Get the main points from lengthy documents
- **Save Time**: Quickly understand content without reading entire texts
- **Customize Output**: Control summary length and focus areas
- **Stream Processing**: Get real-time summaries for large documents

## Use Cases

The Summarize tool is ideal for:

- **Research Papers**: Extract key findings and conclusions
- **News Articles**: Get main points and developments
- **Business Reports**: Understand executive summaries and recommendations
- **Legal Documents**: Identify key clauses and requirements
- **Technical Documentation**: Extract important concepts and procedures
- **Academic Papers**: Summarize methodology and results

## Key Features

### 1. Ingestion-Compatible
Summarize works with both:
- **Direct Text Input**: Paste text directly for summarization
- **Ingested Documents**: Summarize documents already in your knowledge base

### 2. Customizable Summaries
Control summary generation with:
- **Instructions**: Guide the model on summary focus
- **Prompts**: Custom prompts for specific summary types
- **Length Control**: Specify desired summary length
- **Style Options**: Technical, casual, or formal summaries

### 3. Streaming Support
- **Real-time Generation**: Get summaries as they're generated
- **Large Document Handling**: Process lengthy documents efficiently
- **Immediate Feedback**: See progress during summarization

## Usage

### Via Web UI

1. **Navigate to Summarize Tab**:
   - Go to http://localhost:8001
   - Click on the "Summarize" tab

2. **Select Content Source**:
   - **Direct Input**: Paste text in the input field
   - **Ingested Documents**: Select from your document library

3. **Configure Summary Options**:
   - Set summary length (short, medium, long)
   - Add custom instructions
   - Choose summary style

4. **Generate Summary**:
   - Click "Generate Summary"
   - View real-time progress
   - Copy or download the result

### Via API

#### Basic Summarization

```bash
curl -X POST "http://localhost:8001/v1/summarize" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your document text here...",
    "max_length": 200
  }'
```

#### Advanced Summarization

```bash
curl -X POST "http://localhost:8001/v1/summarize" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your document text here...",
    "max_length": 300,
    "instructions": "Focus on technical details and key findings",
    "style": "technical"
  }'
```

#### Streaming Summarization

```bash
curl -X POST "http://localhost:8001/v1/summarize/stream" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your document text here...",
    "max_length": 200
  }'
```

## Configuration Options

### Summary Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `text` | string | Text to summarize | Required |
| `max_length` | integer | Maximum summary length in words | 200 |
| `instructions` | string | Custom instructions for summarization | - |
| `style` | string | Summary style (technical, casual, formal) | "general" |
| `focus_areas` | array | Specific areas to focus on | - |

### Summary Styles

#### Technical Style
```json
{
  "style": "technical",
  "instructions": "Focus on technical details, methodologies, and quantitative results"
}
```

#### Executive Style
```json
{
  "style": "executive",
  "instructions": "Provide high-level overview with key business implications"
}
```

#### Academic Style
```json
{
  "style": "academic",
  "instructions": "Emphasize research methodology, findings, and conclusions"
}
```

## Examples

### Research Paper Summary

**Input**: Long research paper on machine learning

**Configuration**:
```json
{
  "max_length": 300,
  "style": "academic",
  "instructions": "Focus on methodology, key findings, and implications"
}
```

**Output**: "This study investigates the effectiveness of transformer-based models for natural language processing tasks. The research employed a comparative analysis of BERT, GPT, and T5 models on benchmark datasets. Key findings include a 15% improvement in accuracy using fine-tuned BERT models and significant performance gains with larger model sizes. The study concludes that transformer architectures show promising results for NLP applications."

### Business Report Summary

**Input**: Quarterly business report

**Configuration**:
```json
{
  "max_length": 200,
  "style": "executive",
  "instructions": "Highlight financial performance, key metrics, and strategic initiatives"
}
```

**Output**: "Q3 2024 showed strong revenue growth of 23% year-over-year, driven by increased market share in the cloud services segment. Key achievements include launching three new product features and expanding to two new markets. Strategic initiatives focus on AI integration and customer experience improvements."

## Best Practices

### 1. Content Preparation

- **Clean Text**: Remove formatting artifacts before summarization
- **Structure**: Maintain logical flow in input text
- **Length**: Consider breaking very long documents into sections

### 2. Summary Configuration

- **Length**: Match summary length to use case
- **Style**: Choose appropriate style for your audience
- **Instructions**: Be specific about what to focus on

### 3. Quality Control

- **Review**: Always review generated summaries
- **Iterate**: Adjust parameters for better results
- **Validate**: Cross-check with original content

### 4. Performance Optimization

- **Batch Processing**: Summarize multiple documents efficiently
- **Caching**: Cache summaries for frequently accessed content
- **Streaming**: Use streaming for large documents

## Advanced Features

### Multi-Document Summarization

Summarize multiple documents together:

```bash
curl -X POST "http://localhost:8001/v1/summarize/batch" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {"id": "doc1", "text": "First document..."},
      {"id": "doc2", "text": "Second document..."}
    ],
    "max_length": 400,
    "instructions": "Create a complete summary covering all documents"
  }'
```

### Comparative Summarization

Compare multiple documents:

```bash
curl -X POST "http://localhost:8001/v1/summarize/compare" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {"id": "doc1", "text": "Document A..."},
      {"id": "doc2", "text": "Document B..."}
    ],
    "instructions": "Highlight similarities and differences between documents"
  }'
```

## Troubleshooting

### Common Issues

**Poor Summary Quality**
- Increase `max_length` for more detailed summaries
- Provide more specific `instructions`
- Check input text quality and structure

**Slow Performance**
- Reduce `max_length` for faster processing
- Use streaming for large documents
- Consider breaking documents into smaller sections

**Memory Issues**
- Process documents in smaller batches
- Use streaming mode for large texts
- Monitor system resources

### Error Handling

**API Errors**
```json
{
  "error": "Text too long for summarization",
  "max_supported_length": 50000,
  "provided_length": 75000
}
```

**Solutions**
- Break text into smaller sections
- Use document-level summarization
- Implement progressive summarization

## Integration

### With Other Features

**Document Ingestion**
- Summarize documents after ingestion
- Create summary metadata for documents
- Index summaries for search

**Chat Integration**
- Use summaries as context for chat responses
- Generate summaries on-demand during conversations
- Include summary references in responses

**API Integration**
- Integrate summarization into your applications
- Build custom summarization workflows
- Create automated summary generation

## Contributing

If you have ideas for improving the Summarize feature or want to add new capabilities, we welcome contributions!

### Ways to Contribute

1. **Feature Requests**: Submit ideas for new summarization features
2. **Bug Reports**: Report issues and suggest improvements
3. **Code Contributions**: Submit pull requests with enhancements
4. **Documentation**: Help improve documentation and examples

### Getting Started

1. **Fork the Repository**: [GitHub Repository](https://github.com/your-org/internal-assistant)
2. **Create Feature Branch**: `git checkout -b feature/summarize-enhancement`
3. **Make Changes**: Implement your improvements
4. **Submit Pull Request**: Create a PR with detailed description

For more information on contributing, see the [Development Guide](../../developer/development/setup.md).
