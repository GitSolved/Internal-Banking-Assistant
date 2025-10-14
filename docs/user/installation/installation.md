# Installation

It is important that you review the [Main Concepts](./concepts.md) section to understand the different components of Internal Assistant and how they interact with each other.

## Base requirements to run Internal Assistant

### 1. Clone the Internal Assistant Repository
Clone the repository and navigate to it:
```bash
git clone https://github.com/your-org/internal-assistant
cd internal-assistant
```

### 2. Install Python 3.11
If you do not have Python 3.11 installed, install it using a Python version manager like `pyenv`. Earlier Python versions are not supported.
#### macOS/Linux
Install and set Python 3.11 using [pyenv](https://github.com/pyenv/pyenv):
```bash
pyenv install 3.11
pyenv local 3.11
```
#### Windows
Install and set Python 3.11 using [pyenv-win](https://github.com/pyenv-win/pyenv-win):
```bash
pyenv install 3.11
pyenv local 3.11
```

### 3. Install `Poetry`
Install [Poetry](https://python-poetry.org/docs/#installing-with-the-official-installer) for dependency management:
Follow the instructions on the official Poetry website to install it.

!!! warning "Poetry Version"
    A bug exists in Poetry versions 1.7.0 and earlier. We strongly recommend upgrading to a tested version.
    To upgrade Poetry to latest tested version, run `poetry self update 1.8.3` after installing it.

### 4. Optional: Install `make`
To run various scripts, you need to install `make`. Follow the instructions for your operating system:
#### macOS
(Using Homebrew):
```bash
brew install make
```
#### Windows
(Using Chocolatey):
```bash
choco install make
```

## Install and Run Your Desired Setup

Internal Assistant allows customization of the setup, from fully local to cloud-based, by deciding the modules to use. To install only the required dependencies, Internal Assistant offers different `extras` that can be combined during the installation process:

```bash
poetry install --extras "<extra1> <extra2>..."
```
Where `<extra>` can be any of the following options described below.

### Available Modules

You need to choose one option per category (LLM, Embeddings, Vector Stores, UI). Below are the tables listing the available options for each category.

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

| **Option**   | **Description**                          | **Extra** |
|--------------|------------------------------------------|-----------|
| Gradio       | Adds support for UI using Gradio         | ui        |

!!! warning "UI Client"
    A working **Gradio UI client** is provided to test the API, together with a set of useful tools such as bulk
    model download script, ingestion script, documents folder watch, etc. Please refer to the [User Guide](../usage/quickstart.md) page for more information.

## Recommended Setups

There are just some examples of recommended setups. You can mix and match the different options to fit your needs.
You'll find more information in the Manual section of the documentation.

!!! important "Windows Users"
    In the examples below or how to run Internal Assistant with `make run`, `PGPT_PROFILES` env var is being set inline following Unix command line syntax (works on MacOS and Linux).
    If you are using Windows, you'll need to set the env var in a different way, for example:

    ```powershell
    # Powershell
    $env:PGPT_PROFILES="ollama"
    make run
    ```

    or

    ```cmd
    # CMD
    set PGPT_PROFILES=ollama
    make run
    ```

Refer to the [troubleshooting](./troubleshooting.md) section for specific issues you might encounter.

### Local, Ollama-powered setup - RECOMMENDED

**To run Internal Assistant fully locally**, use Ollama for the LLM. Ollama provides local LLM and Embeddings with GPU support abstraction. It's the recommended setup for local development.

Go to [ollama.ai](https://ollama.ai/) and follow the instructions to install Ollama on your machine.

After the installation, make sure the Ollama desktop app is closed.

Now, start Ollama service (it will start a local inference server, serving both the LLM and the Embeddings):
```bash
ollama serve
```

Install the models to be used, the default settings-ollama.yaml is configured to use Foundation-Sec-8B LLM (~5GB) and nomic-embed-text Embeddings (~275MB)

By default, PGPT will automatically pull models as needed. This behavior can be changed by modifying the `ollama.autopull_models` property.

In any case, if you want to manually pull models, run the following commands:

```bash
ollama pull foundation-sec:8b
ollama pull nomic-embed-text
```

Once done, on a different terminal, you can install Internal Assistant with the following command:
```bash
poetry install --extras "ui llms-ollama embeddings-ollama vector-stores-qdrant"
```

Once installed, you can run Internal Assistant. Make sure you have a working Ollama running locally before running the following command.

```bash
PGPT_PROFILES=ollama make run
```

Internal Assistant will use the already existing `settings-ollama.yaml` settings file, which is already configured to use Ollama LLM and Embeddings, and Qdrant. Review it and adapt it to your needs (different models, different Ollama port, etc.)

The UI will be available at http://localhost:8001

### Private, Sagemaker-powered setup

If you need more performance, you can run a version of Internal Assistant that uses AWS Sagemaker machines to serve the LLM and Embeddings.

You need to have access to sagemaker inference endpoints for the LLM and / or the embeddings, and have AWS credentials properly configured.

Edit the `settings-sagemaker.yaml` file to include the correct Sagemaker endpoints.

Then, install Internal Assistant with the following command:
```bash
poetry install --extras "ui llms-sagemaker embeddings-sagemaker vector-stores-qdrant"
```

Once installed, you can run Internal Assistant. Make sure you have a working Ollama running locally before running the following command.

```bash
PGPT_PROFILES=sagemaker make run
```

Internal Assistant will use the already existing `settings-sagemaker.yaml` settings file, which is already configured to use Sagemaker LLM and Embeddings endpoints, and Qdrant.

The UI will be available at http://localhost:8001

### Non-Private, OpenAI-powered test setup

If you want to test Internal Assistant with OpenAI's LLM and Embeddings -taking into account your data is going to OpenAI!- you can run the following command:

You need an OPENAI API key to run this setup.

Edit the `settings-openai.yaml` file to include the correct API KEY. Never commit it! It's a secret! As an alternative to editing `settings-openai.yaml`, you can just set the env var OPENAI_API_KEY.

Then, install Internal Assistant with the following command:
```bash
poetry install --extras "ui llms-openai embeddings-openai vector-stores-qdrant"
```

Once installed, you can run Internal Assistant.

```bash
PGPT_PROFILES=openai make run
```

Internal Assistant will use the already existing `settings-openai.yaml` settings file, which is already configured to use OpenAI LLM and Embeddings endpoints, and Qdrant.

The UI will be available at http://localhost:8001

### Non-Private, Azure OpenAI-powered test setup

If you want to test Internal Assistant with Azure OpenAI's LLM and Embeddings -taking into account your data is going to Azure OpenAI!- you can run the following command:

You need to have access to Azure OpenAI inference endpoints for the LLM and / or the embeddings, and have Azure OpenAI credentials properly configured.

Edit the `settings-azopenai.yaml` file to include the correct Azure OpenAI endpoints.

Then, install Internal Assistant with the following command:
```bash
poetry install --extras "ui llms-azopenai embeddings-azopenai vector-stores-qdrant"
```

Once installed, you can run Internal Assistant.

```bash
PGPT_PROFILES=azopenai make run
```

Internal Assistant will use the already existing `settings-azopenai.yaml` settings file, which is already configured to use Azure OpenAI LLM and Embeddings endpoints, and Qdrant.

The UI will be available at http://localhost:8001

### Local, Llama-CPP powered setup

If you want to run Internal Assistant fully locally without relying on Ollama, you can run the following command:

```bash
poetry install --extras "ui llms-llama-cpp embeddings-huggingface vector-stores-qdrant"
```

In order for local LLM and embeddings to work, you need to download the models to the `local_data/models` folder. You can do so by running the compatibility check:
```bash
poetry run python tools/system/manage_compatibility.py --check
```

Once installed, you can run Internal Assistant with the following command:

```bash
PGPT_PROFILES=local make run
```

Internal Assistant will load the already existing `settings-local.yaml` file, which is already configured to use LlamaCPP LLM, HuggingFace embeddings and Qdrant.

The UI will be available at http://localhost:8001

#### Llama-CPP support

For Internal Assistant to run fully locally without Ollama, Llama.cpp is required and in
particular [llama-cpp-python](https://github.com/abetlen/llama-cpp-python)
is used.

You'll need to have a valid C++ compiler like gcc installed. See [Troubleshooting: C++ Compiler](./troubleshooting.md#troubleshooting-c-compiler) for more details.

!!! note "Documentation"
    It's highly encouraged that you fully read llama-cpp and llama-cpp-python documentation relevant to your platform.
    Running into installation issues is very likely, and you'll need to troubleshoot them yourself.

##### Llama-CPP OSX GPU support

You will need to build [llama.cpp](https://github.com/ggerganov/llama.cpp) with metal support.

To do that, you need to install `llama.cpp` python's binding `llama-cpp-python` through pip, with the compilation flag
that activate metal support.
