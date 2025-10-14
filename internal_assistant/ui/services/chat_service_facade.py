"""
Chat Service Facade

Provides clean abstraction for chat service interactions with optimized
streaming, error handling, and performance monitoring.
"""

import logging
import time
from typing import Iterable, List, Optional, Any, Dict
from llama_index.core.llms import ChatMessage

from internal_assistant.server.chat.chat_service import ChatService, CompletionGen
from internal_assistant.open_ai.extensions.context_filter import ContextFilter
from .service_facade import ServiceFacade, ServiceHealth

logger = logging.getLogger(__name__)


class ChatServiceFacade(ServiceFacade[ChatService]):
    """
    Facade for chat service with enhanced streaming capabilities,
    error recovery, and performance optimization.
    """

    def __init__(self, chat_service: ChatService):
        super().__init__(chat_service, "chat_service")
        self._active_streams = {}
        self._stream_counter = 0

    @ServiceFacade.with_retry(max_retries=3, base_delay=1.0)
    def stream_chat(
        self,
        messages: List[ChatMessage],
        use_context: bool = True,
        context_filter: Optional[ContextFilter] = None,
        stream_id: Optional[str] = None,
    ) -> CompletionGen:
        """
        Stream chat with retry logic and stream management.

        Args:
            messages: List of chat messages
            use_context: Whether to use document context
            context_filter: Optional context filter
            stream_id: Optional stream identifier for tracking

        Returns:
            CompletionGen with streaming response
        """
        try:
            # Generate stream ID if not provided
            if not stream_id:
                self._stream_counter += 1
                stream_id = f"stream_{self._stream_counter}"

            logger.info(
                f"Starting chat stream {stream_id} with {len(messages)} messages"
            )

            # Call underlying service
            completion_gen = self.service.stream_chat(
                messages=messages,
                use_context=use_context,
                context_filter=context_filter,
            )

            # Track active stream
            self._active_streams[stream_id] = {
                "start_time": time.time(),
                "message_count": len(messages),
                "use_context": use_context,
            }

            # Wrap the generator with monitoring
            wrapped_gen = self._wrap_stream_generator(completion_gen, stream_id)

            return CompletionGen(response=wrapped_gen, sources=completion_gen.sources)

        except Exception as e:
            logger.error(f"Failed to start chat stream: {e}")
            raise

    @ServiceFacade.with_retry(max_retries=2, base_delay=0.5)
    def complete_chat(
        self,
        messages: List[ChatMessage],
        use_context: bool = True,
        context_filter: Optional[ContextFilter] = None,
    ) -> str:
        """
        Non-streaming chat completion with retry logic.

        Args:
            messages: List of chat messages
            use_context: Whether to use document context
            context_filter: Optional context filter

        Returns:
            Complete response string
        """
        try:
            logger.info(f"Processing complete chat with {len(messages)} messages")

            completion_gen = self.service.stream_chat(
                messages=messages,
                use_context=use_context,
                context_filter=context_filter,
            )

            # Collect all streaming tokens
            response_parts = []
            for token in completion_gen.response:
                if isinstance(token, str):
                    response_parts.append(token)
                elif hasattr(token, "delta") and token.delta:
                    response_parts.append(token.delta)

            complete_response = "".join(response_parts)
            logger.info(
                f"Chat completion finished, {len(complete_response)} characters"
            )

            return complete_response

        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            raise

    def get_active_streams(self) -> Dict[str, Dict]:
        """Get information about active chat streams."""
        return self._active_streams.copy()

    def cancel_stream(self, stream_id: str) -> bool:
        """
        Cancel an active chat stream.

        Args:
            stream_id: ID of stream to cancel

        Returns:
            True if stream was found and cancelled
        """
        if stream_id in self._active_streams:
            del self._active_streams[stream_id]
            logger.info(f"Cancelled chat stream {stream_id}")
            return True
        return False

    def _wrap_stream_generator(
        self, completion_gen: CompletionGen, stream_id: str
    ) -> Iterable[Any]:
        """
        Wrap streaming generator with monitoring and error handling.

        Args:
            completion_gen: Original completion generator
            stream_id: Stream identifier

        Yields:
            Streaming tokens with monitoring
        """
        token_count = 0
        start_time = time.time()

        try:
            for token in completion_gen.response:
                token_count += 1
                yield token

                # Update stream metrics periodically
                if token_count % 50 == 0:
                    self._update_stream_metrics(stream_id, token_count, start_time)

        except Exception as e:
            logger.error(f"Stream {stream_id} failed at token {token_count}: {e}")
            self._cleanup_stream(stream_id, error=str(e))
            raise

        finally:
            # Final metrics update and cleanup
            self._update_stream_metrics(stream_id, token_count, start_time, final=True)
            self._cleanup_stream(stream_id)

    def _update_stream_metrics(
        self, stream_id: str, token_count: int, start_time: float, final: bool = False
    ):
        """Update metrics for active stream."""
        if stream_id in self._active_streams:
            duration = time.time() - start_time
            self._active_streams[stream_id].update(
                {
                    "token_count": token_count,
                    "duration": duration,
                    "tokens_per_second": token_count / duration if duration > 0 else 0,
                }
            )

            if final:
                logger.info(
                    f"Stream {stream_id} completed: {token_count} tokens in {duration:.2f}s"
                )

    def _cleanup_stream(self, stream_id: str, error: Optional[str] = None):
        """Clean up completed or failed stream."""
        if stream_id in self._active_streams:
            stream_info = self._active_streams[stream_id]
            if error:
                stream_info["error"] = error
                logger.error(f"Stream {stream_id} cleanup due to error: {error}")

            # Keep completed streams for a short time for metrics
            # They'll be cleaned up by the service orchestrator

    def _basic_health_check(self) -> bool:
        """Basic health check for chat service with timeout and circuit breaker."""
        from concurrent.futures import ThreadPoolExecutor, TimeoutError
        import platform

        # Check circuit breaker first
        if self._is_circuit_breaker_open():
            logger.debug(
                f"Health check skipped - circuit breaker open for {self.service_name}"
            )
            return False

        try:
            # Lightweight health check - just test LLM connectivity
            test_messages = [ChatMessage(role="user", content="ping")]

            # Use executor with timeout for cross-platform compatibility
            # No need for signal.SIGALRM which doesn't work on Windows
            with ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="health-check"
            ) as executor:
                future = executor.submit(self._perform_llm_ping, test_messages)
                try:
                    result = future.result(timeout=5)  # 5-second timeout
                    return result
                except TimeoutError:
                    logger.warning(f"Chat service health check timed out")
                    # Cancel the future if it's still running
                    future.cancel()
                    self._trigger_circuit_breaker()
                    return False

        except Exception as e:
            logger.warning(f"Chat service health check failed: {e}")
            self._trigger_circuit_breaker()
            return False

    def _perform_llm_ping(self, test_messages) -> bool:
        """Perform minimal LLM connectivity test."""
        try:
            completion_gen = self.service.stream_chat(
                messages=test_messages, use_context=False, context_filter=None
            )
            # Just check if we can get the first token quickly
            first_token = next(iter(completion_gen.response), None)
            return first_token is not None
        except Exception:
            return False

    def get_service_info(self) -> Dict[str, Any]:
        """Get comprehensive service information."""
        base_metrics = self.get_metrics()

        return {
            **base_metrics,
            "service_type": "chat",
            "active_streams": len(self._active_streams),
            "stream_details": self.get_active_streams(),
            "health": self._health.value,
            "capabilities": {
                "streaming": True,
                "context_aware": True,
                "retry_logic": True,
                "circuit_breaker": True,
            },
        }
