# Internal Assistant Makefile
#
# MODERN POETRY APPROACH (Poetry 2.0+)
# =====================================
# This project uses the modern Poetry approach with 'poetry run' commands.
# 
# ✅ RECOMMENDED USAGE:
#   poetry run make run          # Start the application
#   poetry run make dev          # Development mode
#   poetry run make test         # Run tests
# 
# ❌ DEPRECATED (Poetry < 2.0):
#   poetry shell                 # No longer available in Poetry 2.0+
#   make run                     # Won't work without poetry run
# 
# For interactive development sessions:
#   poetry env activate          # Activate environment
#   make run                     # Run commands
#   deactivate                   # Deactivate when done
# =====================================

# Any args passed to the make script, use with $(call args, default_value)
args = `arg="$(filter-out $@,$(MAKECMDGOALS))" && echo $${arg:-${1}}`

########################################################################################################################
# Quality checks
########################################################################################################################

.PHONY: test
test:
	poetry run pytest tests

test-coverage:
	poetry run pytest tests --cov src --cov-report term --cov-report=html --cov-report xml --junit-xml=tests-results.xml

black:
	poetry run black . --check

ruff:
	poetry run ruff check src tests

format:
	poetry run black .
	poetry run ruff check src tests --fix

mypy:
	poetry run mypy src

check:
	make format
	make mypy
	make compatibility-check

compatibility-check:
	@echo "🔍 Checking dependency compatibility..."
	poetry run python tools/system/manage_compatibility.py --check

version-enforce:
	@echo "🔒 Enforcing version requirements..."
	poetry run python tools/system/manage_compatibility.py --enforce

log-cleanup:
	@echo "🧹 Cleaning up old log files..."
	poetry run python tools/maintenance/manage_logs.py --auto --keep-sessions 7

# Manual cleanup command (run when needed)
cleanup-logs: log-cleanup

log-cleanup-dry-run:
	@echo "🔍 Checking what logs would be cleaned up..."
	poetry run python tools/maintenance/manage_logs.py --auto --keep-sessions 7 --dry-run

pre-run: log-cleanup
	@echo "Pre-run checks completed"

########################################################################################################################
# Run
########################################################################################################################

run: pre-run
	poetry run python -m internal_assistant

dev-windows:
	poetry run python -m uvicorn internal_assistant.main:app --reload --reload-exclude="models/cache/*" --port 8001

.PHONY: dev
dev:
	poetry run python -m uvicorn internal_assistant.main:app --reload --reload-exclude="models/cache/*" --port 8001

########################################################################################################################
# Security & Production
########################################################################################################################

security-check:
	@echo "🔒 Running security validation..."
	poetry run python -c "import ssl; print('SSL: Available')"
	poetry run python -c "import cryptography; print('Cryptography: Available')"
	@echo "✅ Basic security modules validated"

backup:
	@echo "💾 Creating backup of cybersecurity data..."
	@mkdir -p backups/$(shell date +%Y%m%d_%H%M%S)
	cp -r local_data/internal_assistant backups/$(shell date +%Y%m%d_%H%M%S)/data
	@echo "✅ Backup created in backups/$(shell date +%Y%m%d_%H%M%S)/"

health-check:
	@echo "🏥 Running health check..."
	curl -f http://localhost:8001/health || echo "❌ Health check failed"
	@echo "✅ Health check completed"

production:
	@echo "🚀 Starting production mode..."
	@echo "⚠️  Security features enabled"
	@echo "⚠️  Debug mode disabled"
	@echo "⚠️  Standard port 8000"
	PGPT_PROFILES=production poetry run python -m uvicorn internal_assistant.main:app --host 0.0.0.0 --port 8000

########################################################################################################################
# Misc
########################################################################################################################

api-docs:
	@echo "📚 Generating API documentation..."
	PGPT_PROFILES=mock poetry run python tools/system/extract_openapi.py internal_assistant.main:app --out docs/api/openapi.json

ingest:
	@echo "📥 Running folder ingestion..."
	@poetry run python tools/data/ingest_folder.py $(call args)

stats:
	@echo "📊 Showing database statistics..."
	poetry run python tools/system/utils.py stats

wipe:
	@echo "🗑️  Wiping all data..."
	@echo "This action is IRREVERSIBLE and will remove:"
	@echo "  - All ingested documents"
	@echo "  - Vector embeddings"
	@echo "  - Chat history"
	@echo "  - Configuration data"
	@echo ""
	@echo "Type 'CONFIRM-WIPE' to proceed:"
	@read -p "Confirmation: " confirm && [ "$$confirm" = "CONFIRM-WIPE" ] || exit 1
	poetry run python tools/system/utils.py wipe

setup:
	@echo "🔧 Running setup..."
	poetry run python tools/system/setup

setup-logging:
	@echo "📋 Setting up logging configuration..."
	@echo "Available log levels: CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET"
	@echo "Current log files:"
	poetry run python tools/maintenance/logging_control.py show
	@echo ""
	@echo "To set log level, use: make log-level <LEVEL>"
	@echo "Example: make log-level DEBUG"

cleanup-logs:
	@echo "Cleaning up old log files..."
	@echo "Keeping the 7 most recent log files..."
	@echo "Use 'make cleanup-logs-dry-run' to preview what will be removed"
	poetry run python tools/maintenance/manage_logs.py --interactive --keep-count 7

cleanup-logs-dry-run:
	@echo "DRY RUN - Previewing log cleanup..."
	@echo "Keeping the 7 most recent log files..."
	poetry run python tools/maintenance/manage_logs.py --auto --keep-sessions 7 --dry-run

check-model:
	@echo "🔍 Checking current model configuration..."
	poetry run python tools/maintenance/check_model.py

analyze-models:
	@echo "🔍 Analyzing model files for duplicates..."
	poetry run python tools/maintenance/analyze_models.py

cleanup-models:
	@echo "🧹 Cleaning up duplicate models..."
	@echo "⚠️  This will remove duplicate files to save disk space"
	@echo "Type 'CONFIRM-CLEANUP' to proceed:"
	@read -p "Confirmation: " confirm && [ "$$confirm" = "CONFIRM-CLEANUP" ] || exit 1
	poetry run python tools/maintenance/analyze_models.py --cleanup

cleanup-unused-models:
	@echo "🗑️  Removing unused model directories..."
	@echo "⚠️  This will remove completely unused model directories"
	@echo "Type 'CONFIRM-REMOVE-UNUSED' to proceed:"
	@read -p "Confirmation: " confirm && [ "$$confirm" = "CONFIRM-REMOVE-UNUSED" ] || exit 1
	poetry run python tools/maintenance/cleanup_unused_models.py --cleanup

full-model-cleanup:
	@echo "🧹 FULL MODEL CLEANUP - Duplicates + Unused Directories..."
	@echo "⚠️  This will remove duplicates AND unused model directories"
	@echo "Type 'CONFIRM-FULL-CLEANUP' to proceed:"
	@read -p "Confirmation: " confirm && [ "$$confirm" = "CONFIRM-FULL-CLEANUP" ] || exit 1
	@echo "Step 1: Removing duplicate files..."
	poetry run python tools/maintenance/analyze_models.py --cleanup
	@echo "Step 2: Removing unused directories..."
	poetry run python tools/maintenance/cleanup_unused_models.py --cleanup

log-level:
	poetry run python tools/maintenance/logging_control.py set-level $(call args,INFO)

show-logs:
	poetry run python tools/maintenance/logging_control.py show

tail-logs:
	poetry run python tools/maintenance/logging_control.py tail --lines $(call args,20)

cleanup-old-logs:
	@echo "Cleaning up old log files..."
	@echo "Keeping the $(call args,7) most recent log files..."
	poetry run python tools/maintenance/manage_logs.py --interactive --keep-count $(call args,7)

list:
	@echo "🔒 CYBERSECURITY PLATFORM - Available Commands:"
	@echo ""
	@echo "🛡️  SECURITY & PRODUCTION:"
	@echo "  security-check  : Validate security modules and configuration"
	@echo "  production      : Start production mode (secure, no debug)"
	@echo "  backup          : Create backup of cybersecurity data"
	@echo "  health-check    : Verify system health and connectivity"
	@echo ""
	@echo "🧪 DEVELOPMENT & TESTING:"
	@echo "  test            : Run tests using pytest"
	@echo "  test-coverage   : Run tests with coverage report"
	@echo "  black           : Check code format with black"
	@echo "  ruff            : Check code with ruff"
	@echo "  format          : Format code with black and ruff"
	@echo "  mypy            : Run mypy for type checking"
	@echo "  check           : Run format and mypy commands"
	@echo ""
	@echo "🚀 RUNTIME:"
	@echo "  run             : Run the application (standard mode)"
	@echo "  dev-windows     : Run in development mode on Windows ⚠️ DEBUG ENABLED"
	@echo "  dev             : Run in development mode ⚠️ DEBUG ENABLED"
	@echo ""
	@echo "📚 DOCUMENTATION:"
	@echo "  api-docs        : Generate API documentation"
	@echo ""
	@echo "📊 DATA MANAGEMENT:"
	@echo "  ingest          : Ingest cybersecurity documents"
	@echo "  stats           : Show data statistics"
	@echo "  wipe            : ⚠️ DESTRUCTIVE: Delete all data (requires confirmation)"
	@echo ""
	@echo "🔧 UTILITIES:"
	@echo "  setup           : Setup the application"
	@echo "  setup-logging   : Setup enhanced logging configuration"
	@echo "  cleanup-logs    : Clean up old log files (keeps 7 most recent)"
	@echo "  cleanup-logs-dry-run: Preview log cleanup without removing files"
	@echo "  check-model        : Check current model configuration"
	@echo "  analyze-models     : Analyze model files for duplicates"
	@echo "  cleanup-models     : Remove duplicate model files (requires confirmation)"
	@echo "  cleanup-unused-models: Remove unused model directories (requires confirmation)"
	@echo "  full-model-cleanup : Complete cleanup (duplicates + unused directories)"
	@echo "  log-level       : Set logging level (default: INFO)"
	@echo "  show-logs       : Display current logs"
	@echo "  tail-logs       : Show recent log lines (default: 20)"
	@echo "  cleanup-old-logs: Clean old logs (default: 7 days)"
	@echo ""
	@echo "⚠️  SECURITY NOTES:"
	@echo "  - Development mode exposes debug information"
	@echo "  - Use 'production' for secure deployments"
	@echo "  - 'wipe' command requires explicit confirmation"
	@echo "  - Always backup before destructive operations"
