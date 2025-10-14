# Event Flow Diagrams

## Chat Message Flow

```mermaid
sequenceDiagram
    participant User
    participant GradioUI as Gradio UI
    participant ChatBuilder as ChatEventBuilder
    participant ChatHandler as ChatEventHandler
    participant ChatService as Chat Service
    participant LLM as LLM Service
    participant VectorDB as Vector Database
    
    User->>GradioUI: Enter message & click submit
    GradioUI->>ChatBuilder: create_submit_handler()
    ChatBuilder->>ChatHandler: handle_submit(message, history, mode)
    
    alt RAG Mode
        ChatHandler->>VectorDB: Query relevant documents
        VectorDB-->>ChatHandler: Return documents
        ChatHandler->>ChatService: Process with context
    else General Mode
        ChatHandler->>ChatService: Process without context
    end
    
    ChatService->>LLM: Generate response
    LLM-->>ChatService: Return response
    ChatService-->>ChatHandler: Format response
    ChatHandler-->>GradioUI: Update chat display
    GradioUI-->>User: Show response
```

## Document Upload Flow

```mermaid
sequenceDiagram
    participant User
    participant GradioUI as Gradio UI
    participant DocBuilder as DocumentEventBuilder
    participant DocHandler as DocumentEventHandler
    participant IngestService as Ingestion Service
    participant VectorStore as Vector Store
    participant FileSystem as File System
    
    User->>GradioUI: Select files & upload
    GradioUI->>DocBuilder: upload_and_refresh()
    DocBuilder->>DocHandler: process_upload(files)
    DocHandler->>IngestService: ingest_files(files)
    
    loop For each file
        IngestService->>FileSystem: Save file
        IngestService->>IngestService: Parse content
        IngestService->>VectorStore: Create embeddings
        VectorStore-->>IngestService: Store vectors
    end
    
    IngestService-->>DocHandler: Return ingestion results
    DocHandler->>DocHandler: Update document list
    DocHandler-->>GradioUI: Return (dataset, status, library)
    GradioUI-->>User: Show updated library
```

## Settings Update Flow

```mermaid
sequenceDiagram
    participant User
    participant GradioUI as Gradio UI
    participant SettingsBuilder as SettingsEventBuilder
    participant SettingsHandler as SettingsEventHandler
    participant ConfigService as Config Service
    participant StateManager as State Manager
    
    User->>GradioUI: Change setting value
    GradioUI->>SettingsBuilder: create_template_handler()
    SettingsBuilder->>SettingsHandler: apply_template(template_name)
    
    SettingsHandler->>ConfigService: Get template config
    ConfigService-->>SettingsHandler: Return config
    
    SettingsHandler->>StateManager: Update state
    StateManager-->>SettingsHandler: Confirm update
    
    SettingsHandler->>SettingsHandler: Format UI update
    SettingsHandler-->>GradioUI: Return gr.update(value=new_value)
    GradioUI-->>User: Show updated setting
```

## Feeds Refresh Flow

```mermaid
sequenceDiagram
    participant User
    participant GradioUI as Gradio UI
    participant FeedsBuilder as FeedsEventBuilder
    participant FeedsHandler as FeedsEventHandler
    participant FeedService as Feed Service
    participant ExternalAPI as External APIs
    
    User->>GradioUI: Click refresh button
    GradioUI->>FeedsBuilder: create_refresh_mitre_handler()
    FeedsBuilder->>FeedsHandler: refresh_mitre_data()
    
    FeedsHandler->>FeedService: fetch_mitre_updates()
    FeedService->>ExternalAPI: GET /mitre/attack
    ExternalAPI-->>FeedService: Return MITRE data
    
    FeedService->>FeedService: Parse & format data
    FeedService-->>FeedsHandler: Return formatted HTML
    
    FeedsHandler->>FeedsHandler: Create status message
    FeedsHandler-->>GradioUI: Return (status, html_content)
    GradioUI-->>User: Display updated feed
```

## Error Handling Flow

```mermaid
flowchart TB
    Start([User Action]) --> Handler[Event Handler Called]
    Handler --> Try{Try Block}
    
    Try -->|Success| Process[Process Request]
    Process --> Service[Call Service Layer]
    Service -->|Success| Format[Format Response]
    Format --> Return1[Return gr.update]
    Return1 --> Update1[Update UI]
    Update1 --> End1([Success])
    
    Try -->|Exception| Catch{Catch Block}
    Service -->|Exception| Catch
    
    Catch --> Log[Log Error]
    Log --> CheckType{Error Type?}
    
    CheckType -->|Validation| UserMsg1[User-friendly validation message]
    CheckType -->|Service| UserMsg2[Service unavailable message]
    CheckType -->|Unknown| UserMsg3[Generic error message]
    
    UserMsg1 --> Return2[Return gr.update with error]
    UserMsg2 --> Return2
    UserMsg3 --> Return2
    
    Return2 --> Update2[Show error in UI]
    Update2 --> End2([Graceful Failure])
```

## Component Interaction Overview

```mermaid
graph TB
    subgraph "UI Layer (ui.py)"
        UI[Gradio Components]
        Bindings[Event Bindings]
    end
    
    subgraph "Event Layer"
        ChatBuilder[ChatEventBuilder]
        DocBuilder[DocumentEventBuilder]
        SettingsBuilder[SettingsEventBuilder]
        FeedsBuilder[FeedsEventBuilder]
        
        ChatHandler[ChatEventHandler]
        DocHandler[DocumentEventHandler]
        SettingsHandler[SettingsEventHandler]
        FeedsHandler[FeedsEventHandler]
    end
    
    subgraph "Service Layer"
        ChatService[Chat Service]
        IngestService[Ingestion Service]
        ConfigService[Config Service]
        FeedService[Feed Service]
    end
    
    subgraph "Data Layer"
        LLM[LLM Service]
        VectorDB[Vector Database]
        FileSystem[File System]
        ExternalAPIs[External APIs]
    end
    
    UI --> Bindings
    Bindings --> ChatBuilder
    Bindings --> DocBuilder
    Bindings --> SettingsBuilder
    Bindings --> FeedsBuilder
    
    ChatBuilder --> ChatHandler
    DocBuilder --> DocHandler
    SettingsBuilder --> SettingsHandler
    FeedsBuilder --> FeedsHandler
    
    ChatHandler --> ChatService
    DocHandler --> IngestService
    SettingsHandler --> ConfigService
    FeedsHandler --> FeedService
    
    ChatService --> LLM
    ChatService --> VectorDB
    IngestService --> VectorDB
    IngestService --> FileSystem
    FeedService --> ExternalAPIs
    ConfigService --> FileSystem
```

## State Management Flow

```mermaid
stateDiagram-v2
    [*] --> Idle: Initialize UI
    
    Idle --> Processing: User Action
    Processing --> Validating: Input Received
    
    Validating --> Error: Invalid Input
    Validating --> Executing: Valid Input
    
    Error --> Idle: Show Error
    
    Executing --> Updating: Process Complete
    Updating --> Idle: UI Updated
    
    state Executing {
        [*] --> ServiceCall
        ServiceCall --> DataFetch
        DataFetch --> Transform
        Transform --> [*]
    }
    
    state Updating {
        [*] --> StateUpdate
        StateUpdate --> UIRefresh
        UIRefresh --> [*]
    }
```

## Event Registration Flow

```mermaid
flowchart LR
    subgraph "Initialization"
        Start([UI Startup]) --> Create[Create Event Builders]
        Create --> Inject[Inject Dependencies]
        Inject --> Register[Register Handlers]
    end
    
    subgraph "Registration"
        Register --> Chat[Register Chat Events]
        Register --> Doc[Register Doc Events]
        Register --> Settings[Register Settings Events]
        Register --> Feeds[Register Feeds Events]
        
        Chat --> Bind1[Bind to UI Components]
        Doc --> Bind2[Bind to UI Components]
        Settings --> Bind3[Bind to UI Components]
        Feeds --> Bind4[Bind to UI Components]
    end
    
    subgraph "Runtime"
        Bind1 --> Ready[UI Ready]
        Bind2 --> Ready
        Bind3 --> Ready
        Bind4 --> Ready
        Ready --> Listen[Listen for Events]
    end
```

## Async Operation Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as Gradio UI
    participant Handler as Event Handler
    participant Service as Async Service
    participant Background as Background Task
    
    User->>UI: Trigger long operation
    UI->>Handler: Call async handler
    Handler->>Handler: Show loading state
    Handler-->>UI: Update UI (loading)
    UI-->>User: Show spinner
    
    Handler->>Service: Start async operation
    Service->>Background: Queue task
    
    Background->>Background: Process task
    Background-->>Service: Complete
    Service-->>Handler: Return result
    
    Handler->>Handler: Format result
    Handler-->>UI: Update UI (complete)
    UI-->>User: Show result
```

## Event Handler Lifecycle

```mermaid
flowchart TB
    Start([Component Load]) --> Init[Initialize Builder]
    Init --> Create[Create Handler Instance]
    Create --> Config[Configure Dependencies]
    Config --> Ready[Handler Ready]
    
    Ready --> Wait[Wait for Event]
    Wait --> Trigger{Event Triggered}
    
    Trigger -->|Yes| Validate[Validate Input]
    Trigger -->|No| Wait
    
    Validate -->|Valid| Execute[Execute Handler]
    Validate -->|Invalid| ErrorResponse[Return Error]
    
    Execute --> Process[Process Logic]
    Process --> Format[Format Response]
    Format --> Return[Return to UI]
    
    Return --> Wait
    ErrorResponse --> Wait
    
    Wait -->|Shutdown| Cleanup[Cleanup Resources]
    Cleanup --> End([Component Unload])
```

## Testing Flow

```mermaid
graph LR
    subgraph "Test Setup"
        Mock[Mock Services] --> Builder[Create Builder]
        Builder --> Handler[Create Handler]
    end
    
    subgraph "Test Execution"
        Handler --> Input[Provide Test Input]
        Input --> Call[Call Handler Method]
        Call --> Verify[Verify Output]
    end
    
    subgraph "Test Types"
        Verify --> Unit[Unit Tests]
        Verify --> Integration[Integration Tests]
        Verify --> E2E[End-to-End Tests]
    end
    
    subgraph "Assertions"
        Unit --> Assert1[Assert Return Value]
        Integration --> Assert2[Assert Service Calls]
        E2E --> Assert3[Assert UI Updates]
    end
```

## Key Insights

1. **Separation of Concerns**: Each layer has distinct responsibilities
2. **Unidirectional Data Flow**: Events flow from UI → Handler → Service → Data
3. **Error Boundaries**: Errors handled at each layer to prevent cascading failures
4. **Async Support**: Long operations handled asynchronously
5. **State Management**: Clear state transitions and updates
6. **Testability**: Each component can be tested in isolation

These diagrams illustrate the clean architecture achieved through the event handler refactoring, showing how user interactions flow through the system in a predictable, maintainable way.