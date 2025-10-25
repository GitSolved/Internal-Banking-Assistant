# Docker Deployment Guide

This guide covers deploying Internal Assistant using Docker and Docker Compose.

## Quick Start

### Prerequisites

- Docker Engine 20.10+ or Docker Desktop
- Docker Compose 2.0+
- 8GB+ RAM (16GB recommended)
- 20GB+ free disk space

### Basic Deployment

```bash
# Navigate to Docker directory
cd config/deployment/docker

# Start with Ollama CPU (recommended for most users)
docker-compose --profile ollama-cpu up -d

# Access the application
open http://localhost:8001
```

## Deployment Profiles

Internal Assistant supports three deployment profiles:

### 1. Ollama CPU Mode (Recommended)
**Best for:** Most users, servers without GPU

```bash
docker-compose --profile ollama-cpu up -d
```

**Features:**
- ✅ Foundation-Sec-8B model via Ollama
- ✅ CPU-only operation
- ✅ Lower resource requirements
- ✅ Easy setup

### 2. Ollama CUDA Mode (GPU Acceleration)
**Best for:** Systems with NVIDIA GPU

```bash
docker-compose --profile ollama-cuda up -d
```

**Requirements:**
- NVIDIA GPU with CUDA support
- NVIDIA Container Toolkit installed
- Docker GPU runtime configured

**Features:**
- ⚡ GPU-accelerated inference
- ⚡ Faster response times
- ⚡ Handle larger context windows

### 3. LlamaCPP CPU Mode
**Best for:** Direct model file execution

```bash
docker-compose --profile llamacpp-cpu up -d
```

**Features:**
- 🔧 Direct GGUF model loading
- 🔧 More control over model parameters
- ⚠️ Linux Docker only (segfaults on macOS Docker)

## Configuration

### Environment Variables

Create a `.env` file in `config/deployment/docker/`:

```bash
# Application Settings
PGPT_TAG=0.6.2
PGPT_MODE=ollama
PGPT_PROFILES=docker

# HuggingFace Token (optional, for private models)
HF_TOKEN=your_huggingface_token_here

# Ollama Settings
PGPT_OLLAMA_LLM_MODEL=foundation-sec-q4km:latest
PGPT_OLLAMA_API_BASE=http://ollama:11434

# Logging
PGPT_LOG_LEVEL=INFO
```

### Volume Mounts

Data is persisted in the following directories:

```
project-root/
├── local_data/          # Application runtime data
│   ├── logs/           # Session logs
│   ├── internal_assistant/
│   │   └── qdrant/     # Vector database
│   └── cache/          # Model caches
│
└── models/             # Ollama models
    └── .ollama/        # Model files
```

**⚠️ Important:** These directories are mounted from the host and persist between container restarts.

## Port Configuration

| Service | Port | Purpose |
|---------|------|---------|
| Internal Assistant | 8001 | Web UI and API |
| Ollama API | 11434 | LLM inference |
| Traefik Dashboard | 8080 | Service monitoring (optional) |

### Changing Ports

Edit `docker-compose.yaml`:

```yaml
ports:
  - "9000:8001"  # Change 9000 to your preferred port
```

## Model Management

### Using Ollama Models

The Ollama service automatically pulls required models on first run:

```yaml
environment:
  PGPT_OLLAMA_AUTOPULL_MODELS: "true"
```

**Required Models:**
- `foundation-sec-q4km:latest` - Primary LLM
- `nomic-embed-text` - Embedding model

### Manual Model Installation

```bash
# Enter Ollama container
docker-compose exec ollama-cpu bash

# Pull Foundation-Sec model
ollama pull foundation-sec-q4km:latest

# Verify installation
ollama list
```

### Using Custom Models

Place GGUF files in `models/` directory:

```bash
models/
└── Foundation-Sec-8B-q4_k_m.gguf
```

Update environment:

```yaml
environment:
  PGPT_HF_REPO_ID: local/Foundation-Sec-8B
  PGPT_HF_MODEL_FILE: Foundation-Sec-8B-q4_k_m.gguf
```

## Advanced Configuration

### Resource Limits

Add resource constraints to prevent memory issues:

```yaml
# docker-compose.yaml
services:
  internal-assistant-ollama:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

### GPU Configuration (CUDA)

Ensure NVIDIA Container Toolkit is installed:

```bash
# Install NVIDIA Container Toolkit (Ubuntu/Debian)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

Verify GPU access:

```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Health Checks

Monitor service health:

```bash
# Check all services
docker-compose ps

# Check Ollama health
curl http://localhost:11434/api/version

# Check Internal Assistant health
curl http://localhost:8001/health
```

### Custom Network Configuration

For advanced networking:

```yaml
networks:
  internal-assistant-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16

services:
  internal-assistant-ollama:
    networks:
      internal-assistant-net:
        ipv4_address: 172.28.0.10
```

## Maintenance

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f internal-assistant-ollama

# Last 100 lines
docker-compose logs --tail=100 internal-assistant-ollama
```

### Updating

```bash
# Pull latest images
docker-compose pull

# Rebuild and restart
docker-compose --profile ollama-cpu up -d --build

# Verify version
curl http://localhost:8001/health | jq '.version'
```

### Backup

```bash
# Backup local_data
tar -czf backup-$(date +%Y%m%d).tar.gz local_data/

# Backup models
tar -czf models-backup-$(date +%Y%m%d).tar.gz models/
```

### Cleanup

```bash
# Stop services
docker-compose down

# Remove volumes (⚠️ deletes all data)
docker-compose down -v

# Remove unused images
docker image prune -a
```

## Troubleshooting

### Service Won't Start

**Check logs:**
```bash
docker-compose logs internal-assistant-ollama
```

**Common issues:**
- Port already in use → Change port in docker-compose.yaml
- Out of memory → Add resource limits or increase Docker memory
- Permission denied → Check volume mount permissions

### Ollama Connection Failed

**Verify Ollama is running:**
```bash
docker-compose ps ollama-cpu
curl http://localhost:11434/api/version
```

**Check network:**
```bash
docker-compose exec internal-assistant-ollama ping ollama
```

**Restart Ollama:**
```bash
docker-compose restart ollama-cpu
```

### Model Not Found

**Check installed models:**
```bash
docker-compose exec ollama-cpu ollama list
```

**Pull missing model:**
```bash
docker-compose exec ollama-cpu ollama pull foundation-sec-q4km:latest
```

### Slow Performance

**Check resource usage:**
```bash
docker stats
```

**Optimization tips:**
- Increase memory allocation
- Use GPU acceleration (ollama-cuda profile)
- Reduce `max_new_tokens` in config
- Close unused containers

### Permission Errors

**Fix volume permissions:**
```bash
# From project root
sudo chown -R $(id -u):$(id -g) local_data/ models/
```

### Container Crashes on Mac (LlamaCPP)

**Known issue:** LlamaCPP mode segfaults on macOS Docker

**Solution:** Use Ollama mode instead:
```bash
docker-compose --profile ollama-cpu up -d
```

## Production Deployment

### Security Checklist

- [ ] Use Docker secrets for `HF_TOKEN`
- [ ] Enable TLS/SSL with reverse proxy (Nginx, Traefik)
- [ ] Restrict network access with firewall rules
- [ ] Set `GRADIO_ANALYTICS_ENABLED=False` (already configured)
- [ ] Use non-root user (already configured)
- [ ] Keep Docker images updated
- [ ] Monitor logs for security events

### Reverse Proxy Example (Nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name internal-assistant.example.com;

    ssl_certificate /etc/ssl/certs/internal-assistant.crt;
    ssl_certificate_key /etc/ssl/private/internal-assistant.key;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support for Gradio
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Docker Compose Override

Create `docker-compose.override.yaml` for production:

```yaml
services:
  internal-assistant-ollama:
    restart: always
    deploy:
      resources:
        limits:
          cpus: '8'
          memory: 16G
    environment:
      PGPT_LOG_LEVEL: WARNING
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Monitoring

**Prometheus metrics endpoint:**
```bash
curl http://localhost:8001/metrics
```

**Docker stats:**
```bash
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
```

## Support

- **Documentation:** [Main README](../../../README.md)
- **Issues:** [GitHub Issues](https://github.com/GitSolved/Internal-Banking-Assistant/issues)
- **Configuration:** [CLAUDE.md](../../../CLAUDE.md)

## Version Information

- Docker Compose: v2.0+
- Application: v0.6.2
- Python: 3.11.9
- Ollama: latest
- Foundation-Sec: 8B-q4_k_m

---

**Last Updated:** 2025-10-14
**Maintainer:** GitSolved
