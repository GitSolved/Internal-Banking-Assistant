# LLM Configuration

Configure the Large Language Model (LLM) provider for Internal Assistant.

## Supported Providers

- **Local** - Ollama or LlamaCPP for local execution
- **OpenAI** - OpenAI cloud models
- **Azure OpenAI** - Microsoft Azure OpenAI service
- **Google Gemini** - Google's Gemini models
- **AWS Sagemaker** - Amazon Sagemaker endpoints
- **Mock** - Testing mode with simulated responses

## Local LLM Configuration

Run models locally for complete privacy and control.

### Basic Configuration

Edit `config/model-configs/ollama.yaml`:

```yaml
llm:
  mode: local
  max_new_tokens: 1000
  temperature: 0.1
  context_window: 8192
```

### Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `mode` | LLM provider | `local` |
| `max_new_tokens` | Maximum response length | `1000` |
| `temperature` | Creativity (0.0-1.0) | `0.1` |
| `context_window` | Input context size | `8192` |
| `top_p` | Nucleus sampling | `0.9` |
| `top_k` | Top-k sampling | `40` |

### GPU Configuration

**For GPU users:**
```yaml
llm:
  gpu_layers: 35    # Offload layers to GPU
  n_ctx: 8192       # Context window
```

**For CPU users:**
```yaml
llm:
  gpu_layers: 0     # Use CPU only
  n_ctx: 4096       # Smaller context for CPU
```

### Supported Models

- **Llama 3.1 70B Instruct** - Enterprise-grade, banking compliance focused (recommended)
- **Llama 2/3** - General purpose
- **Mistral** - High performance
- **Custom GGUF models** - Any compatible model

### Running

```bash
PGPT_PROFILES=ollama make run
```

## OpenAI Configuration

Use OpenAI's cloud models. Note: data will be sent to OpenAI.

Edit `config/model-configs/openai.yaml`:

```yaml
llm:
  mode: openai

openai:
  api_key: ${OPENAI_API_KEY}
  model: gpt-4
  max_tokens: 1000
```

**Set API key:**
```bash
export OPENAI_API_KEY="your-key"
PGPT_PROFILES=openai make run
```

## OpenAI-Compatible APIs

Use any service that implements the OpenAI API format (LocalAI, vLLM, etc.):

```yaml
llm:
  mode: openailike

openai:
  api_base: http://localhost:8000/v1
  model: your-model-name
```

## Mock Mode (Testing)

Use simulated responses for testing without models:

```yaml
llm:
  mode: mock
```

**Use for**: Testing, CI/CD, development without GPU

```bash
PGPT_PROFILES=mock make run
```

## Performance Tuning

### Response Quality

**Factual responses (recommended for cybersecurity):**
```yaml
llm:
  temperature: 0.1
  top_p: 0.95
  top_k: 40
```

**Creative responses:**
```yaml
llm:
  temperature: 0.7
  top_p: 0.9
  top_k: 50
```

### Memory Optimization

**Reduce memory usage:**
```yaml
llm:
  max_new_tokens: 512    # Smaller responses
  n_ctx: 4096            # Smaller context
  gpu_layers: 20         # Fewer GPU layers
```

## Troubleshooting

See the [Troubleshooting Guide](../installation/troubleshooting.md#llm-issues) for common LLM issues.
