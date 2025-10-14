# Documentation Guidelines

## METADATA
- **document_type**: "development_guidelines"
- **purpose**: "documentation_creation_standards"
- **target_audience**: ["developers", "contributors", "documentation_writers"]
- **difficulty_level**: "intermediate"
- **estimated_time**: "10_minutes_read"
- **last_updated**: "current"
- **maintainer**: "documentation_team"

## PREREQUISITES
- **required_knowledge**: ["markdown_syntax", "project_structure", "git_basics"]
- **optional_knowledge**: ["mkdocs", "technical_writing", "user_experience"]
- **tools_needed**: ["text_editor", "git_client", "markdown_previewer"]

## DOCUMENTATION_STANDARDS

### WRITING_STYLE
- **tone**: "professional_and_clear"
- **audience**: "technical_but_accessible"
- **format**: "structured_and_scannable"
- **length**: "concise_but_complete"

### CONTENT_ORGANIZATION
- **structure**: "logical_hierarchy"
- **navigation**: "clear_progression"
- **cross_references**: "explicit_links"
- **examples**: "practical_and_relevant"

## AGENT_OPTIMIZATION_REQUIREMENT

### MANDATORY_TRANSFORMATION
- **requirement**: "ALL_NEW_DOCUMENTATION_MUST_BE_AGENT_OPTIMIZED"
- **prompt_location**: "docs/developer/guides/documentation-transformation-prompt.md"
- **transformation_command**: "transform {filename}"
- **validation**: "verify_agent_readability"

### TRANSFORMATION_PROCESS
1. **create_initial_draft**: "Write human-readable documentation"
2. **apply_transformation**: "Use docs/developer/guides/documentation-transformation-prompt.md"
3. **validate_output**: "Ensure machine_readability"
4. **finalize_document**: "Review_and_approve"

### TRANSFORMATION_INSTRUCTIONS
```
IMPORTANT: Before committing any new documentation file, you MUST:

1. Reference the documentation transformation prompt:
   File: docs/developer/guides/documentation-transformation-prompt.md
   
2. Apply the transformation by saying:
   "transform {filename}"
   
3. Verify the output follows the agent-optimized format with:
   - METADATA section
   - PREREQUISITES section
   - Structured content
   - Machine-readable formatting
   
4. Only commit documentation that has been transformed
```

## DOCUMENTATION_TYPES_AND_REQUIREMENTS

### USER_DOCUMENTATION
- **location**: "docs/user/"
- **audience**: "end_users"
- **format**: "step_by_step_guides"
- **required_sections**:
  - METADATA
  - PREREQUISITES
  - INSTALLATION_STEPS
  - CONFIGURATION_OPTIONS
  - TROUBLESHOOTING

### API_DOCUMENTATION
- **location**: "docs/api/"
- **audience**: "developers"
- **format**: "reference_documentation"
- **required_sections**:
  - METADATA
  - API_ENDPOINTS
  - REQUEST_FORMATS
  - RESPONSE_FORMATS
  - ERROR_CODES

### DEVELOPER_DOCUMENTATION
- **location**: "docs/developer/"
- **audience**: "contributors"
- **format**: "technical_guides"
- **required_sections**:
  - METADATA
  - PREREQUISITES
  - ARCHITECTURE_OVERVIEW
  - DEVELOPMENT_SETUP
  - CONTRIBUTION_GUIDELINES

## FILE_NAMING_CONVENTIONS

### NAMING_RULES
- **format**: "lowercase_with_hyphens.md"
- **descriptive**: "clear_purpose_indication"
- **consistent**: "follow_existing_patterns"
- **avoid**: "spaces_underscores_camelCase"

### EXAMPLES
- ✅ **good**: "installation-guide.md", "api-reference.md", "development-setup.md"
- ❌ **bad**: "Installation Guide.md", "api_reference.md", "DevelopmentSetup.md"

## CONTENT_STRUCTURE_REQUIREMENTS

### MANDATORY_SECTIONS
1. **METADATA** - Document properties and relationships
2. **PREREQUISITES** - Dependencies and requirements
3. **MAIN_CONTENT** - Primary information organized by topic
4. **NAVIGATION_STRUCTURE** - Links and relationships

### OPTIONAL_SECTIONS
- **TROUBLESHOOTING** - Common issues and solutions
- **EXAMPLES** - Practical usage examples
- **REFERENCES** - Related documentation and resources
- **CHANGELOG** - Version history and updates

## QUALITY_ASSURANCE

### PRE_COMMIT_CHECKS
- **agent_optimization**: "Documentation transformed using prompt"
- **formatting**: "Consistent markdown formatting"
- **links**: "All internal links valid"
- **spelling**: "No spelling errors"
- **grammar**: "Clear and professional language"

### REVIEW_CRITERIA
- **completeness**: "All necessary information included"
- **accuracy**: "Information is current and correct"
- **clarity**: "Easy to understand and follow"
- **usability**: "Practical and actionable content"

## WORKFLOW_PROCESS

### CREATION_WORKFLOW
1. **plan_content**: "Define purpose and audience"
2. **create_draft**: "Write initial human-readable version"
3. **apply_transformation**: "Use docs/developer/guides/documentation-transformation-prompt.md"
4. **review_output**: "Verify agent-optimized format"
5. **test_navigation**: "Ensure links and structure work"
6. **commit_changes**: "Add to version control"

### UPDATE_WORKFLOW
1. **identify_changes**: "Determine what needs updating"
2. **modify_content**: "Update the documentation"
3. **reapply_transformation**: "Ensure agent-optimization maintained"
4. **validate_consistency**: "Check with existing documentation"
5. **commit_updates**: "Version control changes"

## TOOLS_AND_RESOURCES

### REQUIRED_TOOLS
- **text_editor**: "VS Code, Sublime Text, or similar"
- **markdown_previewer**: "Built-in or extension"
- **git_client**: "For version control"
- **transformation_prompt**: "docs/developer/guides/documentation-transformation-prompt.md"

### HELPFUL_RESOURCES
- **markdown_guide**: "GitHub Markdown Guide"
- **mkdocs_docs**: "MkDocs Documentation"
- **style_guide**: "Project-specific conventions"
- **examples**: "Existing documentation files"

## COMMON_PITFALLS

### AVOID_THESE_MISTAKES
- **skipping_transformation**: "Always use the transformation prompt"
- **inconsistent_formatting**: "Follow established patterns"
- **broken_links**: "Verify all internal references"
- **outdated_information**: "Keep content current"
- **unclear_structure**: "Use logical organization"

### BEST_PRACTICES
- **start_with_outline**: "Plan structure before writing"
- **write_for_audience**: "Consider who will read this"
- **include_examples**: "Practical usage demonstrations"
- **test_navigation**: "Verify links and structure"
- **get_feedback**: "Review with team members"

## ENFORCEMENT

### COMPLIANCE_REQUIREMENTS
- **mandatory**: "All documentation must be agent-optimized"
- **validation**: "Automated checks for transformation compliance"
- **review**: "Peer review for quality assurance"
- **training**: "Team education on guidelines"

### MONITORING
- **regular_audits**: "Periodic documentation reviews"
- **quality_metrics**: "Track documentation effectiveness"
- **user_feedback**: "Collect reader input"
- **continuous_improvement**: "Update guidelines based on experience"

## SUPPORT_AND_CONTACT

### GETTING_HELP
- **documentation_team**: "Primary contact for questions"
- **transformation_issues**: "Reference docs/developer/guides/documentation-transformation-prompt.md"
- **formatting_questions**: "Check existing documentation examples"
- **technical_issues**: "Consult development team"

### FEEDBACK_CHANNELS
- **issue_tracker**: "Report documentation problems"
- **pull_requests**: "Suggest improvements"
- **team_meetings**: "Discuss documentation strategy"
- **user_surveys**: "Collect reader feedback"
