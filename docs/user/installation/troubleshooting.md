# Troubleshooting

## Downloading Gated and Private Models
Many models are gated or private, requiring special access to use them. Follow these steps to gain access and set up your environment for using these models.

### Accessing Gated Models
1. **Request Access:**
   Follow the instructions provided [here](https://huggingface.co/docs/hub/en/models-gated) to request access to the gated model.
2. **Generate a Token:**
   Once you have access, generate a token by following the instructions [here](https://huggingface.co/docs/hub/en/security-tokens).
3. **Set the Token:**
   Add the generated token to your `settings.yaml` file:
   ```yaml
   huggingface:
     access_token: <your-token>
   ```
   Alternatively, set the `HF_TOKEN` environment variable:
   ```bash
   export HF_TOKEN=<your-token>
   ```

## Tokenizer Setup
Internal Assistant uses the `AutoTokenizer` library to tokenize input text accurately. It connects to HuggingFace's API to download the appropriate tokenizer for the specified model.

### Configuring the Tokenizer
1. **Specify the Model:**
   In your `settings.yaml` file, specify the model you want to use:
   ```yaml
   llm:
     # tokenizer: local/Llama-3.1-70B  # Optional: specify custom tokenizer
   ```
2. **Set Access Token for Gated Models:**
   If you are using a gated model, ensure the `access_token` is set as mentioned in the previous section.

This configuration ensures that Internal Assistant can download and use the correct tokenizer for the model you are working with.

## Embedding dimensions mismatch
If you encounter an error message like `Embedding dimensions mismatch`, it is likely due to the embedding model and
current vector dimension mismatch. To resolve this issue, ensure that the model and the input data have the same vector dimensions.

By default, Internal Assistant uses `nomic-embed-text` embeddings, which have a vector dimension of 768.
If you are using a different embedding model, ensure that the vector dimensions match the model's output.

!!! warning "Version Compatibility"
    In versions below to 0.6.0, the default embedding model was `BAAI/bge-small-en-v1.5` in `huggingface` setup.
    If you plan to reuse the old generated embeddings, you need to update the `settings.yaml` file to use the correct embedding model:
    ```yaml
    huggingface:
      embedding_hf_model_name: BAAI/bge-small-en-v1.5
    embedding:
      embed_dim: 384
    ```

## Building Llama-cpp with NVIDIA GPU support

### Out-of-memory error

If you encounter an out-of-memory error while running `llama-cpp` with CUDA, you can try the following steps to resolve the issue:
1. **Set the next environment:**
    ```bash
    TOKENIZERS_PARALLELISM=true
    ```
2. **Run Internal Assistant:**
    ```bash
    poetry run python -m internal_assistant
    ```

!!! note "Credits"
    Give thanks to [MarioRossiGithub](https://github.com/MarioRossiGithub) for providing the following solution.

## Troubleshooting C++ Compiler

If you encounter issues with C++ compilation when installing llama-cpp-python, ensure you have a valid C++ compiler installed:

### Linux
```bash
sudo apt-get install build-essential
```

### macOS
```bash
xcode-select --install
```

### Windows
Install Visual Studio Build Tools or use WSL (Windows Subsystem for Linux).

## LLM Issues {#llm-issues}

### Common LLM Problems

**Out of Memory Errors**
- Reduce `gpu_layers` or `n_ctx` in settings
- Use a smaller model
- Close other applications
- Use CPU-only mode

**Slow Response Times**
- Increase `gpu_layers` for GPU users
- Use a GPU with more memory
- Reduce `max_new_tokens`
- Consider cloud-based models

**Model Loading Errors**
- Verify model file integrity
- Check model format compatibility
- Ensure sufficient disk space
- Update llama-cpp-python

**API Connection Issues**
- Verify API key and base URL
- Check network connectivity
- Ensure service is running
- Verify rate limits

## Vector Database Issues {#vector-database-issues}

### Common Vector Database Problems

**Qdrant Connection Errors**
- Check if Qdrant server is running
- Verify port configuration
- Check firewall settings

**Milvus Connection Issues**
- Ensure Milvus server is accessible
- Verify API key for cloud deployments
- Check collection permissions

**PGVector Extension Errors**
- Ensure PGVector extension is installed
- Verify PostgreSQL version compatibility
- Check database permissions

**Memory Issues**
- Reduce batch sizes for large datasets
- Use disk-based storage instead of in-memory
- Consider using a more scalable vector database

## Node Store Issues {#node-store-issues}

### Common Node Store Problems

**File Permission Errors**
- Check write permissions for `local_data/` directory
- Ensure the application has access to create and modify files

**Data Corruption**
- Check for disk space issues
- Verify file integrity of JSON files
- Restore from backup if necessary

**PostgreSQL Connection Errors**
- Verify PostgreSQL service is running
- Check host, port, and credentials
- Ensure database and schema exist

**Performance Issues**
- Monitor memory usage for large datasets
- Consider migrating to PostgreSQL for better performance

## Reranker Issues {#reranker-issues}

### Common Reranker Problems

**Memory Errors**
- Reduce `similarity_top_k` or `batch_size`
- Use a smaller reranking model
- Close other applications

**Slow Performance**
- Increase `batch_size` for faster processing
- Use a smaller model
- Reduce `similarity_top_k`

**Poor Quality Results**
- Increase `similarity_top_k` for more candidates
- Use a larger, more accurate model
- Adjust `top_n` based on your needs
