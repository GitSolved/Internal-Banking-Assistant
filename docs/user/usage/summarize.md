# Document Summarization

Generate concise summaries from ingested documents or text.

## Overview

The Summarize feature extracts key information from documents, saving time and improving comprehension of large content volumes.

**Use Cases:**
- Research papers - Extract findings and conclusions
- Business reports - Get executive summaries
- Legal documents - Identify key clauses
- Technical documentation - Understand main concepts
- Security reports - Highlight critical threats

## Usage

### Web UI

1. Navigate to http://localhost:8001
2. Click "Summarize" tab
3. Choose input source:
   - **Direct Text**: Paste content directly
   - **Ingested Document**: Select from document library
4. Configure options:
   - Summary length (short, medium, long)
   - Custom instructions
   - Summary style
5. Click "Generate Summary"
6. Copy or download results

### API

**Basic Summarization:**
```bash
curl -X POST "http://localhost:8001/v1/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your document text here...",
    "max_length": 200
  }'
```

**With Custom Instructions:**
```bash
curl -X POST "http://localhost:8001/v1/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your document text here...",
    "max_length": 300,
    "instructions": "Focus on technical details and key findings",
    "style": "technical"
  }'
```

**Streaming Mode:**
```bash
curl -X POST "http://localhost:8001/v1/summarize/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your document text here...",
    "max_length": 200
  }'
```

## Configuration Options

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `text` | string | Text to summarize | Required |
| `max_length` | integer | Maximum summary length (words) | 200 |
| `instructions` | string | Custom instructions | - |
| `style` | string | Summary style (technical, executive, academic) | "general" |

## Summary Styles

**Technical:**
```json
{
  "style": "technical",
  "instructions": "Focus on technical details, methodologies, and quantitative results"
}
```

**Executive:**
```json
{
  "style": "executive",
  "instructions": "High-level overview with key business implications"
}
```

**Academic:**
```json
{
  "style": "academic",
  "instructions": "Emphasize research methodology, findings, and conclusions"
}
```

**Security-Focused (for threat reports):**
```json
{
  "style": "security",
  "instructions": "Highlight threats, vulnerabilities, indicators of compromise, and recommended actions"
}
```

## Examples

### Security Report Summary

**Input:** CVE vulnerability report

**Configuration:**
```json
{
  "max_length": 250,
  "style": "security",
  "instructions": "Focus on vulnerability severity, affected systems, and mitigation steps"
}
```

**Output:** "CVE-2024-1234 is a critical remote code execution vulnerability in Apache Framework 2.x affecting versions 2.0-2.8. CVSS score 9.8. Attackers can exploit via crafted HTTP requests to gain unauthorized system access. Affects approximately 50,000 internet-exposed servers. Immediate patching to version 2.9 required. No workarounds available."

## Best Practices

### Content Preparation
- Remove formatting artifacts
- Ensure logical text flow
- Consider breaking very long documents into sections

### Configuration
- Match summary length to use case
- Be specific in instructions
- Choose appropriate style for audience

### Quality Control
- Always review generated summaries
- Cross-check with original content
- Iterate on parameters for better results

## Troubleshooting

### Poor Summary Quality
- Increase `max_length` for more detail
- Provide more specific `instructions`
- Check input text quality

### Slow Performance
- Reduce `max_length`
- Use streaming mode for large documents
- Break documents into smaller sections

### Memory Issues
- Process documents in smaller batches
- Use streaming mode
- Monitor system resources

## Integration

**With Document Ingestion:**
- Automatically summarize documents after ingestion
- Create summary metadata for search
- Index summaries for quick retrieval

**With Chat:**
- Use summaries as context for responses
- Generate on-demand summaries during conversations
- Include summary references in chat responses

## Next Steps

- [Document Ingestion](./ingestion.md) - Upload documents to summarize
- [Configuration](../configuration/settings.md) - Adjust summarization settings
- [API Reference](../../api/reference/api-reference.md) - Full API documentation
