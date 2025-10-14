# SDKs

API integration examples for popular programming languages.

!!! note "Integration Examples"
    These are example implementations for API integration. Actual SDK packages are not provided.

## Integration Examples

### Python Integration

**Status**: Example implementation  
**Usage**: Direct HTTP requests or requests library

```bash
# Use requests library for HTTP calls
pip install requests
```

```python
from pgpt import InternalAssistant

client = InternalAssistant(
    base_url="http://localhost:8001",
    api_key="your-api-key"
)

# Chat completion
response = client.chat.completions.create(
    messages=[
        {"role": "user", "content": "What are the main features?"}
    ]
)

print(response.choices[0].message.content)
```

### TypeScript/JavaScript Integration {#javascript}

**Status**: Example implementation  
**Usage**: Fetch API or axios

```bash
# Use fetch API (built-in) or install axios
npm install axios  # optional
```

```typescript
import { InternalAssistant } from '@internal-assistant/sdk';

const client = new InternalAssistant({
  baseUrl: 'http://localhost:8001',
  apiKey: 'your-api-key'
});

// Chat completion
const response = await client.chat.completions.create({
  messages: [
    { role: 'user', content: 'What are the main features?' }
  ]
});

console.log(response.choices[0].message.content);
```

### Go Integration

**Status**: Example implementation  
**Usage**: net/http package

```bash
# Use standard library net/http package
# No external dependencies required
```

```go
package main

import (
    "context"
    "fmt"
    "log"
    
    "github.com/your-org/internal-assistant-go"
)

func main() {
    client := internalassistant.NewClient("http://localhost:8001", "your-api-key")
    
    resp, err := client.Chat.CreateCompletion(context.Background(), internalassistant.ChatCompletionRequest{
        Messages: []internalassistant.Message{
            {Role: "user", Content: "What are the main features?"},
        },
    })
    
    if err != nil {
        log.Fatal(err)
    }
    
    fmt.Println(resp.Choices[0].Message.Content)
}
```

### Java Integration

**Status**: Example implementation  
**Usage**: HttpClient or OkHttp

### Rust Integration {#rust}

**Status**: Example implementation  
**Usage**: reqwest or hyper

```toml
[dependencies]
internal-assistant = "0.1.0"
```

```rust
use internal_assistant::{InternalAssistant, ChatCompletionRequest, Message};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = InternalAssistant::new("http://localhost:8001", "your-api-key");
    
    let request = ChatCompletionRequest {
        messages: vec![
            Message {
                role: "user".to_string(),
                content: "What are the main features?".to_string(),
            }
        ],
    };
    
    let response = client.chat().create_completion(request).await?;
    println!("{}", response.choices[0].message.content);
    
    Ok(())
}
```

```xml
<dependency>
    <groupId>com.internalassistant</groupId>
    <artifactId>sdk</artifactId>
    <version>0.1.0</version>
</dependency>
```

```java
import com.internalassistant.InternalAssistant;
import com.internalassistant.models.ChatCompletionRequest;
import com.internalassistant.models.Message;

InternalAssistant client = new InternalAssistant("http://localhost:8001", "your-api-key");

ChatCompletionRequest request = ChatCompletionRequest.builder()
    .messages(Arrays.asList(
        new Message("user", "What are the main features?")
    ))
    .build();

ChatCompletionResponse response = client.chat().createCompletion(request);
System.out.println(response.getChoices().get(0).getMessage().getContent());
```

## SDK Features

All SDKs provide:

- **Type Safety**: Full type definitions for all API endpoints
- **Authentication**: Built-in API key management
- **Error Handling**: Complete error handling and retry logic
- **Streaming**: Support for streaming responses
- **File Upload**: Document ingestion
- **Async Support**: Non-blocking operations where applicable

## Installation

### Python

```bash
# Use requests library for HTTP calls
pip install requests
```

### Node.js

```bash
npm install @internal-assistant/sdk
# or
yarn add @internal-assistant/sdk
```

### Go

```bash
# Use standard library net/http package
# No external dependencies required
```

## Configuration

All SDKs support configuration through environment variables:

```bash
# API Configuration
INTERNAL_ASSISTANT_BASE_URL=http://localhost:8001
INTERNAL_ASSISTANT_API_KEY=your-api-key

# Optional: Timeout settings
INTERNAL_ASSISTANT_TIMEOUT=30
INTERNAL_ASSISTANT_MAX_RETRIES=3
```

## Examples

### Document Ingestion

```python
# Python
with open("document.pdf", "rb") as f:
    response = client.ingest.upload_file(f)
    print(f"Document ID: {response.doc_id}")
```

```typescript
// TypeScript
const file = fs.readFileSync("document.pdf");
const response = await client.ingest.uploadFile(file);
console.log(`Document ID: ${response.docId}`);
```

### Streaming Chat

```python
# Python
stream = client.chat.completions.create(
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

```typescript
// TypeScript
const stream = await client.chat.completions.create({
  messages: [{ role: "user", content: "Tell me a story" }],
  stream: true
});

for await (const chunk of stream) {
  if (chunk.choices[0].delta.content) {
    process.stdout.write(chunk.choices[0].delta.content);
  }
}
```

## Contributing

We welcome contributions to our SDKs! Please see the individual repository README files for contribution guidelines.

## Support

For SDK-specific issues:

- **Python**: [pgpt-python issues](https://github.com/your-org/pgpt-python/issues)
- **TypeScript**: [internal-assistant-ts issues](https://github.com/your-org/internal-assistant-ts/issues)
- **Go**: [internal-assistant-go issues](https://github.com/your-org/internal-assistant-go/issues)
- **Java**: [internal-assistant-java issues](https://github.com/your-org/internal-assistant-java/issues)

For general API questions, see our [API Reference](api-reference.md).
