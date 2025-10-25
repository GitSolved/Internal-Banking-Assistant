# Installation Guide

Before starting, review the [Core Concepts](./concepts.md) to understand Internal Assistant's architecture and components.

## Prerequisites

### 1. Clone the Repository

```bash
git clone https://github.com/GitSolved/Internal-Banking-Assistant
cd internal-assistant
```

### 2. Install Python 3.11.9

Internal Assistant requires Python 3.11.9 (exact version). Install using a version manager:

**macOS/Linux (using pyenv):**
```bash
pyenv install 3.11.9
pyenv local 3.11.9
```

**Windows (using pyenv-win):**
```bash
pyenv install 3.11.9
pyenv local 3.11.9
```

### 3. Install Poetry

Install Poetry for dependency management:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

**Required Version**: Poetry 2.0+ (older versions are not compatible)

To upgrade:
```bash
poetry self update
```

### 4. Install Make (Optional but Recommended)

**macOS:**
```bash
brew install make
```

**Windows:**
```bash
choco install make
```

## Installation Options

Install only the components you need by selecting extras during installation:

```bash
poetry install --extras "<extra1> <extra2>..."
```

### Available Components

Choose one option per category:

#### LLM

| **Option**   | **Description**                                                        | **Extra**           |
|--------------|------------------------------------------------------------------------|---------------------|
| **ollama**   | Adds support for Ollama LLM, requires Ollama running locally           | llms-ollama         |
| llama-cpp    | Adds support for local LLM using LlamaCPP                              | llms-llama-cpp      |
| sagemaker    | Adds support for Amazon Sagemaker LLM, requires Sagemaker endpoints    | llms-sagemaker      |
| openai       | Adds support for OpenAI LLM, requires OpenAI API key                   | llms-openai         |
| openailike   | Adds support for 3rd party LLM providers compatible with OpenAI's API  | llms-openai-like    |
| azopenai     | Adds support for Azure OpenAI LLM, requires Azure endpoints            | llms-azopenai       |
| gemini       | Adds support for Gemini LLM, requires Gemini API key                   | llms-gemini         |

#### Embeddings

| **Option**       | **Description**                                                                | **Extra**               |
|------------------|--------------------------------------------------------------------------------|-------------------------|
| **ollama**       | Adds support for Ollama Embeddings, requires Ollama running locally            | embeddings-ollama       |
| huggingface      | Adds support for local Embeddings using HuggingFace                            | embeddings-huggingface  |
| openai           | Adds support for OpenAI Embeddings, requires OpenAI API key                    | embeddings-openai       |
| sagemaker        | Adds support for Amazon Sagemaker Embeddings, requires Sagemaker endpoints     | embeddings-sagemaker    |
| azopenai         | Adds support for Azure OpenAI Embeddings, requires Azure endpoints             | embeddings-azopenai     |
| gemini           | Adds support for Gemini Embeddings, requires Gemini API key                    | embeddings-gemini       |

#### Vector Stores

| **Option**       | **Description**                         | **Extra**               |
|------------------|-----------------------------------------|-------------------------|
| **qdrant**       | Adds support for Qdrant vector store    | vector-stores-qdrant    |
| milvus           | Adds support for Milvus vector store    | vector-stores-milvus    |
| chroma           | Adds support for Chroma DB vector store | vector-stores-chroma    |
| postgres         | Adds support for Postgres vector store  | vector-stores-postgres  |
| clickhouse       | Adds support for Clickhouse vector store| vector-stores-clickhouse|

#### UI

| **Option** | **Description**                   | **Extra** |
|------------|-----------------------------------|-----------|
| Gradio     | Web interface for the platform    | ui        |

## Recommended Setups

Below are tested setup combinations. Choose based on your requirements.

**Windows Users Note**: Set environment variables using PowerShell or CMD syntax:

```powershell
# PowerShell
$env:PGPT_PROFILES="ollama"
make run
```

```cmd
# CMD
set PGPT_PROFILES=ollama
make run
```

### Local Setup with Ollama (Recommended)

This is the recommended setup for fully local operation with Foundation-Sec-8B cybersecurity model.

**1. Install Ollama**

Visit [ollama.ai](https://ollama.ai/) and install Ollama for your platform.

**2. Start Ollama Service**

```bash
ollama serve
```

**3. Pull Models**

Internal Assistant automatically pulls models when needed, or pull manually:

```bash
ollama pull foundation-sec-q4km:latest    # ~4.7GB cybersecurity LLM
ollama pull nomic-embed-text             # ~275MB embeddings
```

**4. Install Internal Assistant**

```bash
poetry install --extras "ui llms-ollama embeddings-huggingface vector-stores-qdrant"
```

**5. Run the Application**

```bash
PGPT_PROFILES=ollama make run
```

The UI will be available at **http://localhost:8001**

Configuration is in `config/model-configs/foundation-sec.yaml` and `config/model-configs/ollama.yaml`.

### Cloud-Based Setups

For cloud-based deployments, Internal Assistant supports various providers. Note that data will be sent to external services.

**AWS Sagemaker**
```bash
poetry install --extras "ui llms-sagemaker embeddings-sagemaker vector-stores-qdrant"
# Configure endpoints in config/model-configs/sagemaker.yaml
PGPT_PROFILES=sagemaker make run
```

**OpenAI**
```bash
poetry install --extras "ui llms-openai embeddings-openai vector-stores-qdrant"
# Set OPENAI_API_KEY environment variable
PGPT_PROFILES=openai make run
```

**Azure OpenAI**
```bash
poetry install --extras "ui llms-azopenai embeddings-azopenai vector-stores-qdrant"
# Configure endpoints in config/model-configs/azure-openai.yaml
PGPT_PROFILES=azopenai make run
```

**Google Gemini**
```bash
poetry install --extras "ui llms-gemini embeddings-gemini vector-stores-qdrant"
# Configure in config/model-configs/gemini.yaml
PGPT_PROFILES=gemini make run
```

### Alternative Local Setup with LlamaCPP

For advanced users who prefer direct model file execution without Ollama:

```bash
poetry install --extras "ui llms-llama-cpp embeddings-huggingface vector-stores-qdrant"
```

**Download Models**
```bash
poetry run python tools/system/manage_compatibility.py --check
```

**Run**
```bash
PGPT_PROFILES=local make run
```

**Requirements:**
- C++ compiler (gcc, clang, or MSVC)
- See [Troubleshooting](./troubleshooting.md#troubleshooting-c-compiler) for compiler setup
- macOS users: Metal GPU support requires specific compilation flags
- Consult [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) documentation for platform-specific instructions
