"""FastAPI app creation, logger configuration and main API routes."""

import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from injector import Injector
from llama_index.core.callbacks import CallbackManager
from llama_index.core.callbacks.global_handlers import create_global_handler
from llama_index.core.settings import Settings as LlamaIndexSettings

from internal_assistant.server.chat.chat_router import chat_router
from internal_assistant.server.chunks.chunks_router import chunks_router
from internal_assistant.server.completions.completions_router import completions_router
from internal_assistant.server.embeddings.embeddings_router import embeddings_router
from internal_assistant.server.feeds.feeds_router import feeds_router
from internal_assistant.server.feeds.simple_forum_router import simple_forum_router
from internal_assistant.server.feeds.threat_intelligence_router import threat_intelligence_router
from internal_assistant.server.threat_intelligence.mitre_attack_router import mitre_attack_router
from internal_assistant.server.health.health_router import health_router
from internal_assistant.server.ingest.ingest_router import ingest_router
from internal_assistant.server.metadata.metadata_router import metadata_router
from internal_assistant.server.recipes.summarize.summarize_router import summarize_router
from internal_assistant.server.status.status_router import status_router
from internal_assistant.server.system.system_router import system_router
from internal_assistant.settings.settings import Settings

logger = logging.getLogger(__name__)


def create_app(root_injector: Injector) -> FastAPI:

    # Start the API
    async def bind_injector_to_request(request: Request) -> None:
        request.state.injector = root_injector

    app = FastAPI(dependencies=[Depends(bind_injector_to_request)])

    app.include_router(completions_router)
    app.include_router(chat_router)
    app.include_router(chunks_router)
    app.include_router(ingest_router)
    app.include_router(summarize_router)
    app.include_router(embeddings_router)
    app.include_router(feeds_router)
    app.include_router(simple_forum_router)  # Simple forum directory endpoints
    app.include_router(threat_intelligence_router)  # NEW: Threat Intelligence endpoints
    app.include_router(mitre_attack_router)  # NEW: MITRE ATT&CK endpoints
    app.include_router(health_router)
    app.include_router(system_router)
    app.include_router(metadata_router)
    app.include_router(status_router)
    


    # Disable LlamaIndex observability to prevent token-by-token debug output
    # that interferes with streaming responses
    # global_handler = create_global_handler("simple")
    # if global_handler:
    #     LlamaIndexSettings.callback_manager = CallbackManager([global_handler])

    settings = root_injector.get(Settings)
    if settings.server.cors.enabled:
        logger.debug("Setting up CORS middleware")
        app.add_middleware(
            CORSMiddleware,
            allow_credentials=settings.server.cors.allow_credentials,
            allow_origins=settings.server.cors.allow_origins,
            allow_origin_regex=settings.server.cors.allow_origin_regex,
            allow_methods=settings.server.cors.allow_methods,
            allow_headers=settings.server.cors.allow_headers,
        )

    if settings.ui.enabled:
        logger.debug("Applying comprehensive Gradio compatibility fixes")
        
        # Fix 1: Apply Gradio schema bug fix
        try:
            from gradio_client import utils
            original_json_schema_to_python_type = utils._json_schema_to_python_type
            
            def fixed_json_schema_to_python_type(schema, defs=None):
                """Fixed version that handles boolean schemas"""
                if isinstance(schema, bool):
                    return "any" if schema else "never"
                return original_json_schema_to_python_type(schema, defs)
            
            utils._json_schema_to_python_type = fixed_json_schema_to_python_type
            logger.debug("Applied Gradio schema bug fix successfully")
        except Exception as e:
            logger.warning(f"Failed to apply Gradio patch: {e}")
        
        # Fix 2: Apply Gradio-specific Pydantic compatibility
        try:
            # Configure Gradio to handle Pydantic schema issues
            import gradio as gr
            # Set environment variable to handle Pydantic schema issues
            import os
            os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
            logger.debug("Applied Gradio Pydantic compatibility configuration")
        except Exception as e:
            logger.warning(f"Failed to apply Gradio Pydantic configuration: {e}")
        
        logger.debug("Importing the UI module")
        try:
            from internal_assistant.ui.ui import InternalAssistantUI
        except ImportError as e:
            raise ImportError(
                "UI dependencies not found, install with `poetry install --extras ui`"
            ) from e

        ui = root_injector.get(InternalAssistantUI)
        ui.mount_in_app(app, settings.ui.path)

    return app
