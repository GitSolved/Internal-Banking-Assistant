# Documentation Guidelines

Standards for creating and maintaining documentation.

## Writing Style

- **Tone**: Professional and clear
- **Audience**: Technical but accessible
- **Format**: Structured and scannable
- **Length**: Concise but complete

## Documentation Types

### User Documentation (`docs/user/`)

**Purpose**: End-user guides for installation, configuration, and usage

**Required Sections**:
- Overview
- Prerequisites
- Step-by-step instructions
- Troubleshooting
- Examples

**Example**: [Installation Guide](../../user/installation/installation.md)

### API Documentation (`docs/api/`)

**Purpose**: Technical reference for developers

**Required Sections**:
- Endpoint descriptions
- Request/response formats
- Authentication
- Error codes
- Examples

**Example**: [API Reference](../../api/reference/api-reference.md)

### Developer Documentation (`docs/developer/`)

**Purpose**: Guides for contributors

**Required Sections**:
- Architecture overview
- Setup instructions
- Coding standards
- Testing guidelines
- Contribution process

**Example**: [Development Setup](setup.md)

## File Naming

Use lowercase with hyphens: `installation-guide.md`, `api-reference.md`

**Good**: `installation-guide.md`, `quick-start.md`

**Bad**: `Installation Guide.md`, `quick_start.md`, `QuickStart.md`

## Content Structure

### Required Sections

1. **Title** - Clear, descriptive heading
2. **Overview** - Brief introduction (1-2 paragraphs)
3. **Main Content** - Organized by topic with clear headings
4. **Related Links** - Cross-references to related docs

### Optional Sections

- **Prerequisites** - Required knowledge or setup
- **Examples** - Practical demonstrations
- **Troubleshooting** - Common issues and solutions
- **Next Steps** - Where to go after this guide

## Markdown Standards

### Headers

Use ATX-style headers (`#`, `##`, `###`):

```markdown
# Main Title
## Section
### Subsection
```

### Code Blocks

Always specify language for syntax highlighting:

````markdown
```python
def example():
    return "Hello"
```

```bash
poetry run make test
```
````

### Links

Use descriptive link text:

**Good**: See the [Installation Guide](../../user/installation/installation.md)

**Bad**: Click [here](../../user/installation/installation.md)

### Lists

Use `-` for unordered lists, `1.` for ordered:

```markdown
- Item one
- Item two

1. First step
2. Second step
```

## MkDocs Integration

### Building Documentation

```bash
# Local development server
poetry run mkdocs serve

# Build static site
poetry run mkdocs build
```

### Navigation

Edit `mkdocs.yml` to add pages to navigation:

```yaml
nav:
  - Home: index.md
  - User Guide:
    - Installation: user/installation/installation.md
    - Configuration: user/configuration/settings.md
```

### Material Theme Features

- **Admonitions**: Notes, warnings, tips
  ```markdown
  !!! note "Title"
      Content here

  !!! warning
      Important warning
  ```

- **Code Copy Buttons**: Automatic for all code blocks
- **Search**: Full-text search enabled by default
- **Dark Mode**: Theme switcher included

## Quality Checklist

Before committing documentation:

- ✅ All links work (no broken references)
- ✅ Code examples tested and working
- ✅ Spelling and grammar checked
- ✅ Follows style guidelines
- ✅ Builds without errors (`mkdocs build`)
- ✅ Cross-references added where appropriate
- ✅ Examples relevant to Internal Assistant

## Common Pitfalls

### Avoid

- Broken links to non-existent files
- Outdated information
- Excessive verbosity
- Inconsistent formatting
- Missing code block language tags
- Relative links that don't work in MkDocs

### Best Practices

- Start with an outline
- Write for your audience
- Include practical examples
- Test all commands and code
- Link to related documentation
- Keep content current

## Review Process

1. **Self-review**: Check against guidelines
2. **Build test**: Run `mkdocs build --strict`
3. **Peer review**: Get feedback from team
4. **Update**: Address review comments
5. **Commit**: Push to repository

## Tools

### Recommended

- **Editor**: VS Code with Markdown extensions
- **Preview**: Built-in markdown preview or MkDocs serve
- **Spell check**: VS Code extension or grammarly
- **Link checker**: `mkdocs build --strict`

### MkDocs Commands

```bash
# Start development server
poetry run mkdocs serve

# Build static site
poetry run mkdocs build

# Build with warnings as errors
poetry run mkdocs build --strict

# Deploy to GitHub Pages
poetry run mkdocs gh-deploy
```

## Examples

### Good Documentation Example

```markdown
# Installing Internal Assistant

Internal Assistant requires Python 3.11.9 and Poetry 2.0+.

## Prerequisites

- Python 3.11.9 installed
- Poetry installed
- Git installed

## Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/GitSolved/Internal-Banking-Assistant
   cd internal-assistant
   ```

2. Install dependencies:
   ```bash
   poetry install --extras "ui llms-ollama embeddings-huggingface vector-stores-qdrant"
   ```

3. Run the application:
   ```bash
   poetry run make run
   ```

## Next Steps

- [Configuration Guide](../configuration/settings.md)
- [Quick Start](../usage/quickstart.md)
```

## Getting Help

- **Questions**: Ask in project discussions
- **Issues**: Report documentation problems via GitHub issues
- **Improvements**: Submit pull requests with fixes

## References

- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [Markdown Guide](https://www.markdownguide.org/)
