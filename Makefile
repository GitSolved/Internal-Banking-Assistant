# Internal Assistant Makefile
# Poetry 2.0+ - Use 'poetry run make <target>' or 'poetry env activate' + 'make <target>'

args = `arg="$(filter-out $@,$(MAKECMDGOALS))" && echo $${arg:-${1}}`

########################################################################################################################
# Quality & Testing
########################################################################################################################

.PHONY: test dev
test:
	poetry run pytest tests

test-coverage:
	poetry run pytest tests --cov internal_assistant --cov-report term --cov-report=html --cov-report xml --junit-xml=tests-results.xml

format:
	poetry run black .
	poetry run ruff check internal_assistant tests --fix

mypy:
	poetry run mypy internal_assistant

check:
	make format
	make mypy
	make compatibility-check

compatibility-check:
	@echo "🔍 Checking dependency compatibility..."
	poetry run python tools/system/manage_compatibility.py --check

########################################################################################################################
# Run
########################################################################################################################

log-cleanup:
	@poetry run python tools/maintenance/manage_logs.py --auto --keep-sessions 7

run: log-cleanup
	poetry run python -m internal_assistant

dev:
	poetry run python -m uvicorn internal_assistant.main:app --reload --reload-exclude="models/cache/*" --port 8001

dev-windows: dev

production:
	@echo "🚀 Starting production mode (secure, debug disabled, port 8000)"
	PGPT_PROFILES=production poetry run python -m uvicorn internal_assistant.main:app --host 0.0.0.0 --port 8000

########################################################################################################################
# Utilities
########################################################################################################################

health-check:
	@curl -f http://localhost:8001/health || echo "❌ Health check failed"

backup:
	@mkdir -p backups/$(shell date +%Y%m%d_%H%M%S)
	@cp -r local_data/internal_assistant backups/$(shell date +%Y%m%d_%H%M%S)/data
	@echo "✅ Backup created"

api-docs:
	PGPT_PROFILES=mock poetry run python tools/system/extract_openapi.py internal_assistant.main:app --out docs/api/openapi.json

ingest:
	poetry run python tools/data/ingest_folder.py $(call args)

stats:
	poetry run python tools/system/utils.py stats

analyze-models:
	poetry run python tools/maintenance/analyze_models.py

wipe:
	@echo "⚠️  DESTRUCTIVE: Will remove all documents, embeddings, chat history"
	@echo "Type 'CONFIRM-WIPE' to proceed:"
	@read -p "Confirmation: " confirm && [ "$$confirm" = "CONFIRM-WIPE" ] || exit 1
	poetry run python tools/system/utils.py wipe

list:
	@echo "Available Commands:"
	@echo ""
	@echo "Development & Testing:"
	@echo "  run              : Start application"
	@echo "  dev              : Development mode with auto-reload"
	@echo "  production       : Production mode (secure, port 8000)"
	@echo "  test             : Run all tests"
	@echo "  test-coverage    : Run tests with coverage"
	@echo "  format           : Format code (black + ruff)"
	@echo "  mypy             : Type checking"
	@echo "  check            : Full quality check"
	@echo "  compatibility-check : Check dependency versions"
	@echo ""
	@echo "Data Management:"
	@echo "  ingest          : Ingest documents"
	@echo "  stats           : Database statistics"
	@echo "  analyze-models  : Analyze model files"
	@echo "  wipe            : ⚠️  Delete all data (requires confirmation)"
	@echo ""
	@echo "Utilities:"
	@echo "  api-docs        : Generate API documentation"
	@echo "  health-check    : Check system health"
	@echo "  backup          : Create data backup"
	@echo "  log-cleanup     : Clean old logs (keeps 7)"
	@echo ""
