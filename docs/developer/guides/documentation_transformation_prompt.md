# Agent Optimization Prompt

## METADATA
- **document_type**: "prompt_template"
- **purpose**: "documentation_transformation_tool"
- **target_audience**: ["AI_agents", "documentation_engineers", "automation_systems"]
- **difficulty_level**: "intermediate"
- **estimated_time**: "5_minutes_per_document"
- **last_updated**: "current"
- **maintainer**: "documentation_team"

## PREREQUISITES
- **input_requirements**: ["markdown_document", "human_readable_format"]
- **output_requirements**: ["structured_data", "machine_readable_format"]
- **processing_capabilities**: ["text_parsing", "structure_analysis", "metadata_extraction"]
- **knowledge_base**: ["documentation_standards", "markdown_syntax", "data_structuring"]

## PROMPT_DESCRIPTION
- **name**: "Agent Optimization Prompt"
- **type**: "documentation_transformation_template"
- **function**: "convert_human_readable_to_agent_optimized"
- **input_format**: "narrative_markdown"
- **output_format**: "structured_markdown"
- **optimization_target**: "machine_readability"

## CONVERSION_RULES

### STRUCTURE_REQUIREMENTS
- **action**: "convert_to_structured_format"
  - **requirement**: "machine_readable_structures"
  - **format**: "key_value_pairs"
  - **hierarchy**: "logical_patterns"
- **action**: "remove_narrative_elements"
  - **targets**: ["storytelling", "emotional_language", "descriptive_text"]
  - **replacement**: "categorical_data"
- **action**: "organize_information"
  - **pattern**: "predictable_hierarchy"
  - **structure**: "explicit_relationships"

### METADATA_EXTRACTION
- **action**: "extract_implicit_information"
  - **targets**: ["file_relationships", "dependencies", "prerequisites"]
  - **output**: "explicit_metadata"
- **action**: "create_metadata_sections"
  - **components**: ["version_info", "timestamps", "authorship"]
  - **format**: "structured_parameters"

### ACTIONABLE_INFORMATION
- **action**: "convert_instructions"
  - **input**: "explanatory_text"
  - **output**: "executable_commands"
- **action**: "transform_examples"
  - **input**: "narrative_examples"
  - **output**: "structured_data_formats"
- **action**: "convert_use_cases"
  - **input**: "descriptive_cases"
  - **output**: "requirement_specifications"

### NAVIGATION_OPTIMIZATION
- **action**: "create_navigation_structures"
  - **type**: "explicit_relationships"
  - **format**: "categorized_references"
- **action**: "add_breadcrumb_navigation"
  - **components**: ["dependency_chains", "cross_references"]
  - **output**: "machine_readable_relationships"

### CONTENT_TRANSFORMATION
- **action**: "replace_paragraphs"
  - **input**: "narrative_paragraphs"
  - **output**: "bulleted_lists"
- **action**: "convert_tables"
  - **input**: "human_readable_tables"
  - **output**: "machine_readable_formats"
- **action**: "transform_code_examples"
  - **input**: "explanatory_code"
  - **output**: "executable_command_blocks"

## OUTPUT_FORMAT_REQUIREMENTS

### REQUIRED_SECTIONS
1. **METADATA** - Document properties and relationships
2. **PREREQUISITES** - Dependencies and requirements
3. **INSTALLATION_STEPS** - Sequential, executable procedures
4. **CONFIGURATION_OPTIONS** - All settings and parameters
5. **API_ENDPOINTS** - Service interfaces and methods
6. **FILE_FORMATS_SUPPORTED** - Input/output specifications
7. **TROUBLESHOOTING** - Error mappings and solutions
8. **DEPENDENCIES_TREE** - System architecture and relationships
9. **NAVIGATION_STRUCTURE** - Document organization and links

### FORMATTING_STANDARDS
- **headers**: "UPPERCASE"
- **indentation**: "consistent_hierarchy"
- **data_types**: "explicit_constraints"
- **validation**: "rules_and_expected_outputs"
- **separators**: "machine_readable_delimiters"

## TRANSFORMATION_EXAMPLES

### NARRATIVE_TO_STRUCTURED
- **input**: "Internal Assistant is a powerful tool that helps you manage documents. It's easy to use and very secure."
- **output**:
  ```
  PROJECT_DESCRIPTION:
    name: "Internal Assistant"
    purpose: "document_management"
    security_level: "high"
    complexity: "low"
    target_audience: ["end_users", "developers"]
  ```

### INSTRUCTION_TO_COMMAND
- **input**: "To install, run the following command in your terminal: `poetry install`"
- **output**:
  ```
  INSTALLATION_STEP:
    action: "install_dependencies"
    command: "poetry install"
    working_directory: "project_root"
    expected_output: "Dependencies installed successfully"
    error_codes:
      - code: "E001"
        description: "Poetry not found"
        solution: "Install poetry: pip install poetry"
  ```

## QUALITY_CHECKS
- **completeness_check**: "all_source_information_captured"
- **structure_check**: "follows_required_format"
- **actionability_check**: "every_instruction_executable"
- **searchability_check**: "all_content_machine_indexable"
- **relationships_check**: "all_dependencies_explicit"
- **validation_check**: "all_parameters_constrained"

## USAGE_INSTRUCTIONS

### SINGLE_FILE_TRANSFORMATION
- **command**: "agent_optimized_prompt: file = {path/to/file.md}"
- **example**: "agent_optimized_prompt: file = docs/index.md"
- **output**: "transformed_agent_optimized_document"

### FOLDER_TRANSFORMATION
- **command**: "agent_optimized_prompt: folder = {path/to/folder}"
- **example**: "agent_optimized_prompt: folder = docs/"
- **output**: "multiple_transformed_documents"

### SPECIFIC_DOCUMENTATION_TYPES
- **installation_guide**: "agent_optimized_prompt: file = docs/user/installation/installation.md"
- **api_reference**: "agent_optimized_prompt: file = docs/api/reference/api-reference.md"
- **architecture_doc**: "agent_optimized_prompt: file = docs/developer/architecture/overview.md"

## EXPECTED_OUTPUT_STRUCTURE
```
# [Document Title]

## METADATA
- **document_type**: "installation_guide"
- **target_audience**: ["users", "developers"]
- **difficulty_level**: "beginner"
- **estimated_time**: "10_minutes"

## PREREQUISITES
- **python_version**: ">=3.9"
- **system_requirements**: ["8GB_RAM", "2GB_disk_space"]
- **dependencies**: ["poetry", "git"]

## INSTALLATION_STEPS
1. **action**: "clone_repository"
   - **command**: "git clone [url]"
   - **expected_output**: "Repository cloned successfully"

## CONFIGURATION_OPTIONS
- **setting_name**: "llm_provider"
- **valid_values**: ["ollama", "openai", "azure"]
- **default_value**: "ollama"

## API_ENDPOINTS
- **base_url**: "http://localhost:8000"
- **endpoints**:
  - **chat**: "/api/v1/chat"
  - **health**: "/health"

## FILE_FORMATS_SUPPORTED
- **documents**: [".pdf", ".docx", ".txt"]
- **images**: [".jpg", ".png"]

## TROUBLESHOOTING
- **error_code**: "E001"
- **description**: "Port already in use"
- **solution**: "Change port in settings.yaml"

## DEPENDENCIES_TREE
```
project/
├── core/
├── api/
└── ui/
```

## NAVIGATION_STRUCTURE
- **parent**: "/docs/"
- **children**: ["installation", "configuration", "usage"]
- **related**: ["api_reference", "architecture"]
```

## OPTIMIZATION_PRINCIPLES
- **machine_readability**: "prioritize_over_human_narrative"
- **structured_data**: "prioritize_over_descriptive_text"
- **explicit_relationships**: "prioritize_over_implicit_connections"
- **actionable_commands**: "prioritize_over_explanations"
- **searchable_content**: "prioritize_over_storytelling"

## TRANSFORMATION_WORKFLOW
1. **analyze_source**: "identify_content_structure"
2. **extract_metadata**: "capture_implicit_information"
3. **structure_content**: "organize_into_required_sections"
4. **optimize_navigation**: "create_explicit_relationships"
5. **validate_output**: "ensure_quality_standards"
6. **finalize_document**: "apply_formatting_standards"

## ERROR_HANDLING
- **missing_sections**: "add_placeholder_with_metadata"
- **unclear_structure**: "apply_default_hierarchy"
- **incomplete_information**: "mark_as_requires_review"
- **format_violations**: "apply_correction_rules"

## PERFORMANCE_METRICS
- **transformation_speed**: "5_minutes_per_document"
- **accuracy_rate**: "95%_information_preservation"
- **completeness_score**: "all_sections_populated"
- **machine_readability**: "100%_structured_format"

--- Reference: 

## PARAMETER DEFINITIONS

### METADATA Section Parameters:
- **document_type**: The category of document (e.g., "user_guide", "api_reference", "development_guide", "installation_guide", "troubleshooting")
- **purpose**: The specific function this document serves (e.g., "step_by_step_instructions", "reference_material", "configuration_guide")
- **target_audience**: Who this document is written for (e.g., ["end_users", "developers", "system_administrators", "contributors"])
- **difficulty_level**: How complex the content is for the target audience ("beginner", "intermediate", "advanced")
- **estimated_time**: How long it takes to read/complete the content (e.g., "5_minutes", "15_minutes", "30_minutes")
- **last_updated**: When the document was last modified ("current" or specific date)
- **maintainer**: Who is responsible for keeping this document current ("documentation_team", "development_team", specific person)

### PREREQUISITES Section Parameters:
- **required_knowledge**: What the reader needs to know before starting (e.g., ["basic_command_line", "python_fundamentals", "http_basics"])
- **optional_knowledge**: Helpful but not required background (e.g., ["docker", "api_development", "machine_learning"])
- **tools_needed**: Software or tools required to follow the document (e.g., ["text_editor", "git_client", "web_browser"])
- **system_requirements**: Hardware or system specifications needed (e.g., ["8GB_RAM", "python_3.9+", "internet_connection"])

### INSTALLATION_STEPS Section Parameters:
- **action**: What step is being performed (e.g., "install_dependencies", "configure_settings", "start_service")
- **command**: The exact command to run (e.g., "poetry install", "git clone [url]")
- **working_directory**: Where to run the command (e.g., "project_root", "docs/", "config/")
- **expected_output**: What success looks like (e.g., "Dependencies installed successfully", "Server running on http://localhost:8000")
- **error_codes**: Common errors and their solutions (e.g., "E001: Poetry not found → Install poetry: pip install poetry")

### CONFIGURATION_OPTIONS Section Parameters:
- **setting_name**: The name of the configuration option (e.g., "llm_provider", "port", "log_level")
- **valid_values**: Acceptable values for the setting (e.g., ["ollama", "openai", "azure"])
- **default_value**: What the setting is if not changed (e.g., "ollama", "8000", "INFO")
- **description**: What the setting controls (e.g., "Language model provider for AI responses")

### API_ENDPOINTS Section Parameters:
- **base_url**: The root URL for the API (e.g., "http://localhost:8000")
- **api_version**: The version of the API (e.g., "v1", "v2")
- **endpoints**: List of available API endpoints with their HTTP methods (e.g., "GET /health", "POST /api/v1/chat")

### FILE_FORMATS_SUPPORTED Section Parameters:
- **documents**: Supported document file extensions (e.g., [".pdf", ".docx", ".txt", ".md"])
- **images**: Supported image file extensions (e.g., [".jpg", ".png", ".gif"])
- **data**: Supported data file extensions (e.g., [".csv", ".json", ".xml"])
- **archives**: Supported archive file extensions (e.g., [".zip", ".tar.gz"])

### TROUBLESHOOTING Section Parameters:
- **error_code**: Unique identifier for the error (e.g., "E001", "E002")
- **description**: What the error means (e.g., "Port 8000 already in use")
- **solution**: How to fix the error (e.g., "Change port in settings.yaml or kill existing process")
- **prevention**: How to avoid this error in the future (e.g., "Check port availability before starting")

### NAVIGATION_STRUCTURE Section Parameters:
- **parent**: The parent document or section (e.g., "/docs/", "/docs/user/")
- **children**: Related documents that are more specific (e.g., ["installation", "configuration", "usage"])
- **related**: Documents that are similar or complementary (e.g., ["api_reference", "architecture"])
- **breadcrumbs**: The path to this document (e.g., "docs > user > installation > installation.md")

### DEPENDENCIES_TREE Section Parameters:
- **file_structure**: Hierarchical view of related files and folders
- **dependencies**: What other files this document depends on
- **dependents**: What files depend on this document

### PERFORMANCE_METRICS Section Parameters:
- **response_time**: How long operations typically take (e.g., "< 2_seconds_average")
- **memory_usage**: How much memory is typically used (e.g., "configurable_limits")
- **scalability**: How well the system handles increased load (e.g., "horizontal_scaling_supported")

### SECURITY_FEATURES Section Parameters:
- **data_privacy**: How data privacy is handled (e.g., "on_premise_deployment")
- **authentication**: How users are authenticated (e.g., "configurable_auth_system")
- **encryption**: How data is encrypted (e.g., "data_at_rest_and_transit")
- **access_control**: How access is controlled (e.g., "role_based_permissions")