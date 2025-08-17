"""FastAPI app creation, logger configuration and main API routes."""

import logging
from internal_assistant.di import global_injector
from internal_assistant.launcher import create_app
from internal_assistant.utils.version_check import log_version_info

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log version information on startup
log_version_info()

app = create_app(global_injector)
