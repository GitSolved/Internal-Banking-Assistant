# Configuration Directory

This directory contains all configuration files for the Internal Assistant project, organized by purpose for better maintainability.

## Directory Structure

```
config/
├── app/                    # Core application settings
│   ├── settings.yaml       # Main application configuration
│   └── settings_backup.yaml # Backup of previous settings
├── model-configs/          # Model-specific configurations
│   ├── ollama.yaml         # Ollama integration settings (Llama 3.1 70B)
│   ├── openai.yaml         # OpenAI API settings
│   └── ...                 # Other model configs
├── environments/           # Environment-specific configs
│   ├── local.yaml          # Local development settings
│   ├── test.yaml           # Testing environment settings
│   └── docker.yaml         # Docker deployment settings
├── deployment/             # Deployment configurations
│   ├── docker/             # Docker-related files
│   │   ├── docker-compose.yaml
│   │   ├── Dockerfile.ollama
│   │   ├── Dockerfile.llamacpp-cpu
│   │   └── Modelfile
│   └── development/        # Development tools
│       └── pre-commit-config.yaml
└── organization_report.txt # Audit trail of file organization
```

## Configuration Loading

The application loads configuration files in the following order:

1. **Default Profile**: `config/settings.yaml` (always loaded)
2. **Environment Profile**: Based on `PGPT_PROFILES` environment variable
   - `config/environments/{profile}.yaml` (if exists)
   - `config/model-configs/{profile}.yaml` (if exists)
   - `config/settings-{profile}.yaml` (fallback for backward compatibility)

## Environment Variables

- `PGPT_PROFILES`: Comma-separated list of profiles to load
- `PGPT_SETTINGS_FOLDER`: Override the config directory path (default: `config/`)

## Examples

### Local Development
```bash
PGPT_PROFILES=local poetry run make run
```
Loads: `config/settings.yaml` + `config/environments/local.yaml`

### Testing
```bash
PGPT_PROFILES=test poetry run make test
```
Loads: `config/settings.yaml` + `config/environments/test.yaml`

### Docker Deployment
```bash
PGPT_PROFILES=docker poetry run make run
```
Loads: `config/settings.yaml` + `config/environments/docker.yaml`

## File Organization History

This structure was created during Phase 2A of the repository restructure:

- **Before**: Scattered configs in `configs/` directory
- **After**: Organized structure in `config/` with logical grouping
- **Stability**: Critical `internal_assistant/settings/` module left untouched
- **Compatibility**: All existing functionality preserved

## Notes

- The `internal_assistant/settings/` Python module remains in its original location to maintain import compatibility
- All configuration paths have been updated throughout the codebase
- The application automatically looks for `config/settings.yaml` as the main configuration file
- Model configurations are in `config/model-configs/` to avoid confusion with actual model files
