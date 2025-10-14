# Data Lifecycle Management

## Overview

This document outlines the data management strategy for the Internal Assistant platform, covering data organization, lifecycle management, backup procedures, and cleanup operations.

## Data Organization

### Primary Data Locations

#### **`local_data/` - Main Application Data**
- **Purpose**: Primary runtime and persistent data storage
- **Structure**:
  ```
  local_data/
  ├── logs/                    # Application logs
  ├── internal_assistant/      # Vector database, app state
  ├── models/                  # AI model files (consolidated)
  └── cache/                   # Token encoding cache (consolidated)
  ```

#### **`data/` - Legacy Storage (Deprecated)**
- **Status**: LEGACY LOCATION - Migration in progress
- **Purpose**: Previously used for persistent user data
- **Action**: Migrate to `local_data/` structure

### Cache Management

#### **Token Encoding Cache**
- **Location**: `local_data/cache/` (consolidated from root `tiktoken_cache/`)
- **Purpose**: Stores tokenizer cache for improved performance
- **Configuration**: 
  - **Environment Variable**: `TIKTOKEN_CACHE_DIR=local_data/cache/`
  - **Default**: Automatically set to consolidated location
  - **Migration**: Completed - old root location removed

#### **Model Cache**
- **Location**: `local_data/models/cache/`
- **Purpose**: HuggingFace model cache and downloaded models
- **Size**: 5GB+ for Foundation-Sec-8B model

### Log Management

#### **Application Logs**
- **Location**: `local_data/logs/`
- **Types**:
  - Application logs
  - Error logs
  - Access logs
  - Debug logs
- **Retention**: Configurable via settings
- **Cleanup**: Automated via maintenance scripts

## Data Lifecycle

### 1. **Creation Phase**
- User uploads documents
- System processes and indexes content
- Vector embeddings generated
- Metadata stored

### 2. **Storage Phase**
- Data stored in `local_data/internal_assistant/`
- Vector database maintains embeddings
- Document metadata tracked
- Cache files generated for performance

### 3. **Access Phase**
- Users query the system
- Vector search performed
- Results returned with context
- Cache utilized for performance

### 4. **Maintenance Phase**
- Regular cleanup of old logs
- Cache optimization
- Database maintenance
- Performance monitoring

### 5. **Backup Phase**
- Regular backups of critical data
- Configuration backups
- Model file backups (if custom)

## Backup Strategy

### Critical Data to Backup
1. **Vector Database**: `local_data/internal_assistant/`
2. **Configuration**: `config/` directory
3. **Custom Models**: `local_data/models/` (if custom)
4. **User Documents**: `local_data/internal_assistant/documents/`

### Backup Frequency
- **Daily**: Vector database and configuration
- **Weekly**: Full system backup
- **Monthly**: Complete data archive

### Backup Commands
```bash
# Manual backup using standard tools
tar -czf backup-$(date +%Y%m%d).tar.gz local_data/ config/

# Or use rsync for incremental backups
rsync -av --progress local_data/ /path/to/backup/local_data/
rsync -av --progress config/ /path/to/backup/config/
```

## Cleanup Operations

### Available Maintenance Tools
```bash
# Manage application logs
poetry run python tools/maintenance/manage_logs.py --cleanup

# Control logging levels
poetry run python tools/maintenance/logging_control.py

# Analyze model files and storage
poetry run python tools/maintenance/analyze_models.py

# Clean up unused model files
poetry run python tools/maintenance/cleanup_unused_models.py
```

### Manual Cleanup
```bash
# Remove all cached data (if cache directory exists)
rm -rf local_data/cache/*

# Remove old logs
rm -rf local_data/logs/*.log

# Reset vector database (use with caution)
rm -rf local_data/internal_assistant/qdrant/

# Remove Qdrant lock files (if database won't start)
rm -f local_data/internal_assistant/qdrant/.lock
```

## Docker Deployment

### Data Persistence
```yaml
# docker-compose.yaml
volumes:
  - ./local_data:/app/local_data
  - ./config:/app/config
  - ./models:/app/local_data/models
```

### Environment Variables
```bash
# Data paths
TIKTOKEN_CACHE_DIR=/app/local_data/cache
PGPT_SETTINGS_FOLDER=/app/config
```

## Monitoring and Maintenance

### Health Checks
```bash
# Check application health
curl http://localhost:8001/health

# Check disk usage
du -sh local_data/*

# Analyze model files
poetry run python tools/maintenance/analyze_models.py

# Check logs
tail -f local_data/logs/*.log
```

### Performance Monitoring
- Monitor vector database size with `du -sh local_data/internal_assistant/qdrant/`
- Check log file growth with `ls -lh local_data/logs/`
- Analyze model storage with the analyze_models.py tool
- Use application health endpoint for system status

## Recovery Procedures

### Data Recovery
1. **Stop the application**
2. **Restore from backup**
3. **Verify data integrity**
4. **Restart application**

### Cache Recovery
```bash
# Clear and rebuild cache
rm -rf local_data/cache/*
poetry run python -m internal_assistant
```

### Database Recovery
```bash
# Reset vector database (Qdrant)
rm -rf local_data/internal_assistant/qdrant/
poetry run python -m internal_assistant
```

## Best Practices

### Data Management
- Regular backups of critical data
- Monitor disk space usage
- Implement log rotation
- Use appropriate file permissions

### Performance
- Keep cache directory on fast storage
- Regular cleanup of old data
- Monitor vector database size
- Optimize model storage

### Security
- Secure backup storage
- Encrypt sensitive data
- Regular security audits
- Access control for data directories

## Configuration Reference

### Environment Variables
```bash
# Data paths
TIKTOKEN_CACHE_DIR=local_data/cache/
PGPT_SETTINGS_FOLDER=config/
PGPT_DATA_FOLDER=local_data/

# Logging
PGPT_LOG_LEVEL=INFO
PGPT_LOG_FILE=local_data/logs/app.log

# Cache settings
PGPT_CACHE_TTL=3600
PGPT_MAX_CACHE_SIZE=1GB
```

### Settings Configuration
```yaml
# config/settings.yaml
data:
  local_data_folder: local_data/internal_assistant

# Vector store is managed by Qdrant
# Logs are in local_data/logs/
# Models are cached in local_data/models/cache/
```

## Troubleshooting

### Common Issues
1. **Disk Space**: Monitor and clean up old data
2. **Cache Corruption**: Clear and rebuild cache
3. **Database Locks**: Use cleanup scripts
4. **Permission Issues**: Check file permissions

### Diagnostic Commands
```bash
# Check data directory structure
find local_data -type d -maxdepth 3

# Check disk usage
du -sh local_data/*

# Check file permissions
ls -la local_data/

# Analyze models and storage
poetry run python tools/maintenance/analyze_models.py
```

---

**Note**: This document should be updated as the data management strategy evolves. Always test backup and recovery procedures in a safe environment before implementing in production.