# LLM Configuration

Internal Assistant supports multiple Large Language Model (LLM) providers and configurations to suit different use cases and environments.

## Supported LLM Modes

Internal Assistant supports the following LLM modes:

- **Local** - Run models locally on your hardware
- **OpenAI** - Use OpenAI's cloud-based models
- **OpenAI-Compatible** - Use any OpenAI-compatible API
- **Mock** - Use mock responses for testing

## Local LLM Configuration

Local mode runs both the LLM and embedding models on your local hardware, providing complete privacy and control.

### Prerequisites

Before using local LLMs, ensure you have:

1. **Sufficient hardware** - GPU recommended for optimal performance
2. **Model files** - Download the required model files
3. **Dependencies** - Install required packages

### Basic Configuration

```yaml
llm:
  mode: local
  max_new_tokens: 256
```

### Configuration Options

| Field | Description | Default |
|-------|-------------|---------|
| `mode` | LLM operation mode | `local` |
| `max_new_tokens` | Maximum tokens to generate | `256` |
| `context_window` | Context window size | Model-dependent |
| `temperature` | Response randomness (0.0-1.0) | `0.1` |
| `top_p` | Nucleus sampling parameter | `0.9` |
| `top_k` | Top-k sampling parameter | `40` |

### Advanced Configuration

For fine-tuning performance, you can customize additional parameters:

```yaml
llm:
  mode: local
  max_new_tokens: 512
  temperature: 0.2
  top_p: 0.95
  top_k: 50
  context_window: 4096
  repeat_penalty: 1.1
  frequency_penalty: 0.0
  presence_penalty: 0.0
```

### Model Selection

Internal Assistant supports various local models:

- **Llama 2** - Meta's open-source models
- **Mistral** - Open models
- **Code Llama** - Specialized for code generation
- **Custom models** - Any GGUF-compatible model

### Hardware Optimization

#### GPU Configuration

For optimal GPU performance:

```yaml
llm:
  mode: local
  gpu_layers: 35  # Number of layers to offload to GPU
  n_gpu_layers: 35  # Alternative parameter name
  n_ctx: 4096  # Context window size
```

#### Memory Management

If you encounter memory issues:

```yaml
llm:
  mode: local
  max_new_tokens: 128  # Reduce token generation
  n_ctx: 2048  # Reduce context window
  gpu_layers: 20  # Reduce GPU layers
```

### Running with Local Models

Start Internal Assistant with local models:

```bash
# Using default profile
PGPT_PROFILES=local make run

# Or directly
PGPT_PROFILES=local poetry run python -m internal_assistant
```

## OpenAI Configuration

OpenAI mode uses OpenAI's cloud-based models for high-quality responses without local hardware requirements.

### Configuration

Create a `settings-openai.yaml` profile:

```yaml
llm:
  mode: openai

openai:
  api_base: https://api.openai.com/v1
  api_key: your-openai-api-key
  model: gpt-3.5-turbo
  max_tokens: 1000
  temperature: 0.1
```

### Configuration Options

| Field | Description | Default |
|-------|-------------|---------|
| `api_base` | OpenAI API base URL | `https://api.openai.com/v1` |
| `api_key` | Your OpenAI API key | - |
| `model` | Model to use | `gpt-3.5-turbo` |
| `max_tokens` | Maximum tokens to generate | `1000` |
| `temperature` | Response randomness | `0.1` |

### Environment Variables

You can also set the API key via environment variable:

```bash
export OPENAI_API_KEY="your-api-key"
```

### Running with OpenAI

```bash
PGPT_PROFILES=openai make run
```

## OpenAI-Compatible Configuration

OpenAI-compatible mode allows you to use any service that implements the OpenAI API format, such as LocalAI, vLLM, or custom servers.

### Configuration

```yaml
llm:
  mode: openailike

openai:
  api_base: http://localhost:8000/v1
  api_key: your-api-key
  model: llama-2-7b-chat
```

### Supported Services

- **[LocalAI](https://localai.io/)** - Local model serving
- **[vLLM](https://docs.vllm.ai/)** - Inference server
- **[Ollama](https://ollama.ai/)** - Local model management
- **Custom servers** - Any OpenAI-compatible API

### vLLM Example

1. **Start vLLM server**:

```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b-chat-hf \
    --host 0.0.0.0 \
    --port 8000
```

2. **Configure Internal Assistant**:

```yaml
llm:
  mode: openailike

openai:
  api_base: http://localhost:8000/v1
  model: meta-llama/Llama-2-7b-chat-hf
```

3. **Run Internal Assistant**:

```bash
PGPT_PROFILES=vllm make run
```

## Mock Configuration

Mock mode provides simulated responses for testing and development without requiring actual models.

### Configuration

```yaml
llm:
  mode: mock
```

### Use Cases

- **Testing** - Verify application logic without model costs
- **Development** - Fast iteration without model loading
- **CI/CD** - Automated testing without hardware requirements
- **Documentation** - Generate examples without API keys

### Running in Mock Mode

```bash
PGPT_PROFILES=mock make run
```

## Model Performance Optimization

### Memory Management

**For GPU users:**
```yaml
llm:
  mode: local
  gpu_layers: 35
  n_ctx: 4096
  max_new_tokens: 256
```

**For CPU users:**
```yaml
llm:
  mode: local
  gpu_layers: 0
  n_ctx: 2048
  max_new_tokens: 128
```

### Response Quality

**For creative tasks:**
```yaml
llm:
  temperature: 0.7
  top_p: 0.9
  top_k: 50
```

**For factual tasks:**
```yaml
llm:
  temperature: 0.1
  top_p: 0.95
  top_k: 40
```

## Troubleshooting

For LLM-specific issues, see the [main troubleshooting guide](../installation/troubleshooting.md#llm-issues).

### Performance Tuning

**GPU Optimization**
```yaml
llm:
  mode: local
  gpu_layers: 35  # Adjust based on GPU memory
  n_ctx: 4096     # Adjust based on memory
  n_batch: 512    # Batch size for processing
```

**CPU Optimization**
```yaml
llm:
  mode: local
  gpu_layers: 0
  n_ctx: 2048
  n_threads: 8    # Number of CPU threads
```

## Security Considerations

### Local Models
- **Privacy**: Complete data privacy
- **Security**: No external API calls
- **Control**: Full model control

### Cloud Models
- **API Keys**: Secure key management
- **Data**: Review data handling policies
- **Rate Limits**: Monitor usage limits

### Best Practices
- Use environment variables for API keys
- Regularly rotate API keys
- Monitor API usage and costs
- Implement proper error handling

## Cost Optimization

### Local Models
- **Hardware**: One-time investment
- **Electricity**: Ongoing power costs
- **Maintenance**: Model updates and management

### Cloud Models
- **Pay-per-use**: Only pay for what you use
- **Scaling**: Can scale up/down
- **Maintenance**: Managed by provider

### Hybrid Approach
- Use local models for development
- Use cloud models for production
- Implement caching strategies

## Monitoring and Logging

### Performance Metrics
- Response time
- Token generation rate
- Memory usage
- GPU utilization

### Error Tracking
- Model loading errors
- API connection issues
- Memory errors
- Rate limit violations

### Logging Configuration
```yaml
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            file: local_data/logs/internal_assistant.log
```

For more information on specific models and configurations, see the [Model Documentation](../installation/concepts.md).
