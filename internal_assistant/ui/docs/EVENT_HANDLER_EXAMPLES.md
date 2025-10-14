# Event Handler Usage Examples

## Table of Contents
1. [Creating a New Event Handler](#creating-a-new-event-handler)
2. [Adding Event Handlers to Existing Modules](#adding-event-handlers-to-existing-modules)
3. [Error Handling Patterns](#error-handling-patterns)
4. [Multi-Output Handlers](#multi-output-handlers)
5. [Async Event Handlers](#async-event-handlers)
6. [Testing Event Handlers](#testing-event-handlers)
7. [Common Patterns](#common-patterns)

## Creating a New Event Handler

### Step 1: Create the Event Handler Class

```python
# internal_assistant/ui/components/custom/custom_events.py
import logging
import gradio as gr
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

class CustomEventHandler:
    """
    Event handler for custom functionality.
    """
    
    def __init__(self, custom_service: Any, config_service: Any):
        """
        Initialize with required services.
        
        Args:
            custom_service: Service for custom operations
            config_service: Service for configuration
        """
        self.custom_service = custom_service
        self.config_service = config_service
    
    async def process_custom_action(self, input_data: str) -> str:
        """
        Process a custom action.
        
        Args:
            input_data: Input from the user
            
        Returns:
            Processed result as HTML string
        """
        try:
            # Validate input
            if not input_data:
                return "<div class='error'>No input provided</div>"
            
            # Process with service
            result = await self.custom_service.process(input_data)
            
            # Format response
            return f"""
            <div class='custom-result'>
                <h3>Processing Complete</h3>
                <p>{result}</p>
            </div>
            """
        except Exception as e:
            logger.error(f"Custom action failed: {e}")
            return f"<div class='error'>Processing failed: {str(e)}</div>"
```

### Step 2: Create the Event Builder

```python
class CustomEventHandlerBuilder:
    """
    Builder for creating custom event handlers.
    """
    
    def __init__(self, custom_service: Any, config_service: Any):
        """Initialize builder with services."""
        self.custom_service = custom_service
        self.config_service = config_service
        self._handler = None
    
    def get_handler(self) -> CustomEventHandler:
        """Get or create the event handler instance."""
        if not self._handler:
            self._handler = CustomEventHandler(
                self.custom_service,
                self.config_service
            )
        return self._handler
    
    def create_action_handler(self):
        """Create handler for custom action."""
        async def wrapper(input_data):
            result = await self.get_handler().process_custom_action(input_data)
            return gr.update(value=result)
        return wrapper
```

### Step 3: Integrate in UI

```python
# In ui.py
class ModernInternalAssistant:
    def __init__(self):
        # Initialize services
        self.custom_service = CustomService()
        self.config_service = ConfigService()
        
        # Create event builder
        self._custom_event_builder = CustomEventHandlerBuilder(
            self.custom_service,
            self.config_service
        )
    
    def _build_ui_blocks(self):
        # Create UI components
        custom_input = gr.Textbox(label="Custom Input")
        custom_output = gr.HTML(label="Result")
        custom_button = gr.Button("Process")
        
        # Bind event handler
        custom_button.click(
            self._custom_event_builder.create_action_handler(),
            inputs=[custom_input],
            outputs=[custom_output]
        )
```

## Adding Event Handlers to Existing Modules

### Adding to Chat Module

```python
# In chat_events.py
class ChatEventHandler:
    # ... existing code ...
    
    async def export_chat_history(self, history: list) -> Tuple[str, str]:
        """
        Export chat history to file.
        
        Args:
            history: Chat history list
            
        Returns:
            Tuple of (status_message, file_path)
        """
        try:
            # Create export
            file_path = await self.chat_service.export_history(history)
            status = f"Chat exported to {file_path}"
            return status, file_path
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return f"Export failed: {str(e)}", ""

# In ChatEventHandlerBuilder
def create_export_handler(self):
    """Create handler for exporting chat."""
    async def wrapper(history):
        status, file_path = await self.get_handler().export_chat_history(history)
        return gr.update(value=status), gr.update(value=file_path)
    return wrapper
```

## Error Handling Patterns

### Pattern 1: Graceful Degradation

```python
async def safe_handler(self, input_data: str) -> str:
    """Handler with graceful degradation."""
    try:
        # Try primary service
        result = await self.primary_service.process(input_data)
        return self._format_success(result)
    except ServiceUnavailable:
        try:
            # Fall back to secondary service
            logger.warning("Primary service unavailable, using fallback")
            result = await self.fallback_service.process(input_data)
            return self._format_fallback(result)
        except Exception as e:
            # Return cached or default response
            logger.error(f"All services failed: {e}")
            return self._format_default_response()
```

### Pattern 2: Validation with Specific Errors

```python
async def validated_handler(self, input_data: str, options: dict) -> str:
    """Handler with input validation."""
    try:
        # Validate inputs
        errors = []
        
        if not input_data:
            errors.append("Input is required")
        
        if len(input_data) > 1000:
            errors.append("Input too long (max 1000 characters)")
        
        if not options.get('mode'):
            errors.append("Mode must be selected")
        
        if errors:
            return self._format_validation_errors(errors)
        
        # Process valid input
        result = await self.service.process(input_data, options)
        return self._format_result(result)
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return self._format_error(e)
```

### Pattern 3: Retry Logic

```python
async def handler_with_retry(self, input_data: str, max_retries: int = 3) -> str:
    """Handler with automatic retry."""
    last_error = None
    
    for attempt in range(max_retries):
        try:
            result = await self.service.process(input_data)
            return self._format_success(result)
        except TemporaryError as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                logger.warning(f"Attempt {attempt + 1} failed, retrying...")
            continue
        except PermanentError as e:
            # Don't retry permanent errors
            return self._format_error(e)
    
    # All retries failed
    return self._format_error(last_error)
```

## Multi-Output Handlers

### Pattern 1: Multiple UI Updates

```python
async def multi_update_handler(self, input_data: str) -> Tuple[str, str, dict]:
    """
    Handler that updates multiple UI components.
    
    Returns:
        Tuple of (status_html, result_html, chart_data)
    """
    try:
        # Process input
        result = await self.service.process(input_data)
        
        # Generate multiple outputs
        status_html = f"<div class='status'>Processed {len(result)} items</div>"
        result_html = self._format_results(result)
        chart_data = self._generate_chart_data(result)
        
        return status_html, result_html, chart_data
        
    except Exception as e:
        error_html = f"<div class='error'>{str(e)}</div>"
        return error_html, "", {}

# In builder
def create_multi_handler(self):
    """Create multi-output handler."""
    async def wrapper(input_data):
        status, result, chart = await self.get_handler().multi_update_handler(input_data)
        return (
            gr.update(value=status),
            gr.update(value=result),
            gr.update(value=chart)
        )
    return wrapper
```

### Pattern 2: Conditional Outputs

```python
async def conditional_handler(self, mode: str, input_data: str) -> Tuple[Any, ...]:
    """
    Handler with conditional outputs based on mode.
    """
    try:
        if mode == "simple":
            result = await self.simple_process(input_data)
            return gr.update(value=result), gr.update(visible=False)
        elif mode == "advanced":
            result, details = await self.advanced_process(input_data)
            return gr.update(value=result), gr.update(value=details, visible=True)
        else:
            return gr.update(value="Invalid mode"), gr.update(visible=False)
    except Exception as e:
        return gr.update(value=f"Error: {e}"), gr.update(visible=False)
```

## Async Event Handlers

### Pattern 1: Background Processing

```python
async def background_handler(self, input_data: str, task_id: str) -> str:
    """
    Handler for long-running background tasks.
    """
    try:
        # Start background task
        await self.task_service.start_task(task_id, input_data)
        
        # Return immediate response
        return f"""
        <div class='task-started'>
            <p>Task {task_id} started</p>
            <p>Processing in background...</p>
        </div>
        """
    except Exception as e:
        return f"<div class='error'>Failed to start task: {e}</div>"

async def check_status_handler(self, task_id: str) -> Tuple[str, bool]:
    """
    Check status of background task.
    
    Returns:
        Tuple of (status_html, is_complete)
    """
    try:
        status = await self.task_service.get_status(task_id)
        
        if status.is_complete:
            result_html = self._format_complete(status.result)
            return result_html, True
        else:
            progress_html = self._format_progress(status.progress)
            return progress_html, False
    except Exception as e:
        return f"<div class='error'>{e}</div>", True
```

### Pattern 2: Streaming Response

```python
async def streaming_handler(self, input_data: str):
    """
    Handler with streaming response.
    """
    try:
        async for chunk in self.service.stream_process(input_data):
            yield self._format_chunk(chunk)
    except Exception as e:
        yield f"<div class='error'>Stream error: {e}</div>"
```

## Testing Event Handlers

### Unit Test Example

```python
# test_custom_events.py
import pytest
from unittest.mock import Mock, AsyncMock
from internal_assistant.ui.components.custom.custom_events import CustomEventHandler

@pytest.fixture
def mock_services():
    """Create mock services."""
    custom_service = Mock()
    custom_service.process = AsyncMock(return_value="Processed result")
    
    config_service = Mock()
    config_service.get_config = Mock(return_value={"key": "value"})
    
    return custom_service, config_service

@pytest.fixture
def handler(mock_services):
    """Create handler with mock services."""
    custom_service, config_service = mock_services
    return CustomEventHandler(custom_service, config_service)

@pytest.mark.asyncio
async def test_process_custom_action_success(handler, mock_services):
    """Test successful processing."""
    result = await handler.process_custom_action("test input")
    
    assert "Processing Complete" in result
    assert "Processed result" in result
    mock_services[0].process.assert_called_once_with("test input")

@pytest.mark.asyncio
async def test_process_custom_action_empty_input(handler):
    """Test empty input validation."""
    result = await handler.process_custom_action("")
    
    assert "No input provided" in result
    assert "error" in result

@pytest.mark.asyncio
async def test_process_custom_action_error(handler, mock_services):
    """Test error handling."""
    mock_services[0].process.side_effect = Exception("Service error")
    
    result = await handler.process_custom_action("test input")
    
    assert "Processing failed" in result
    assert "Service error" in result
```

### Integration Test Example

```python
@pytest.mark.integration
async def test_handler_with_real_service():
    """Test handler with real service."""
    # Create real services
    custom_service = CustomService()
    config_service = ConfigService()
    
    # Create handler
    handler = CustomEventHandler(custom_service, config_service)
    
    # Test processing
    result = await handler.process_custom_action("integration test")
    
    assert result is not None
    assert "error" not in result.lower()
```

## Common Patterns

### Pattern 1: Caching Results

```python
class CachedEventHandler:
    def __init__(self, service):
        self.service = service
        self._cache = {}
    
    async def cached_handler(self, input_key: str) -> str:
        """Handler with result caching."""
        if input_key in self._cache:
            logger.info(f"Cache hit for {input_key}")
            return self._cache[input_key]
        
        result = await self.service.process(input_key)
        self._cache[input_key] = result
        return result
```

### Pattern 2: Rate Limiting

```python
class RateLimitedEventHandler:
    def __init__(self, service):
        self.service = service
        self._last_call = {}
        self._min_interval = 1.0  # seconds
    
    async def rate_limited_handler(self, user_id: str, input_data: str) -> str:
        """Handler with rate limiting."""
        now = time.time()
        last = self._last_call.get(user_id, 0)
        
        if now - last < self._min_interval:
            wait_time = self._min_interval - (now - last)
            return f"Please wait {wait_time:.1f} seconds before next request"
        
        self._last_call[user_id] = now
        return await self.service.process(input_data)
```

### Pattern 3: Batch Processing

```python
class BatchEventHandler:
    def __init__(self, service):
        self.service = service
        self._batch = []
        self._batch_size = 10
    
    async def batch_handler(self, item: str) -> str:
        """Handler that batches requests."""
        self._batch.append(item)
        
        if len(self._batch) >= self._batch_size:
            # Process batch
            results = await self.service.batch_process(self._batch)
            self._batch = []
            return self._format_batch_results(results)
        else:
            remaining = self._batch_size - len(self._batch)
            return f"Added to batch ({remaining} more needed)"
```

## Best Practices

1. **Always use try-catch blocks** for error handling
2. **Log errors with context** for debugging
3. **Return user-friendly messages** for errors
4. **Validate inputs** before processing
5. **Use type hints** for better IDE support
6. **Keep handlers focused** on single responsibility
7. **Test handlers thoroughly** with mocks and real services
8. **Document expected inputs/outputs** in docstrings
9. **Use async/await** for I/O operations
10. **Implement graceful degradation** where possible

## Migration Guide

When migrating existing inline handlers:

1. **Identify the handler logic** in ui.py
2. **Extract to appropriate event module**
3. **Create handler method** with proper signature
4. **Add to event builder** as creation method
5. **Replace inline logic** with builder call
6. **Test thoroughly** to ensure functionality preserved

Example migration:
```python
# Before (in ui.py)
def handle_click(input_text):
    result = process_text(input_text)
    return gr.update(value=result)

button.click(handle_click, inputs=[text_input], outputs=[text_output])

# After (in ui.py)
button.click(
    self._event_builder.create_click_handler(),
    inputs=[text_input],
    outputs=[text_output]
)

# In event handler module
async def process_click(self, input_text: str) -> str:
    result = await self.service.process_text(input_text)
    return result

# In event builder
def create_click_handler(self):
    async def wrapper(input_text):
        result = await self.get_handler().process_click(input_text)
        return gr.update(value=result)
    return wrapper
```

This completes the event handler usage examples documentation.