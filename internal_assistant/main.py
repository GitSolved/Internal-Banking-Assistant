"""FastAPI app creation, logger configuration and main API routes."""

import logging
from internal_assistant.di import global_injector
from internal_assistant.launcher import create_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app(global_injector)
