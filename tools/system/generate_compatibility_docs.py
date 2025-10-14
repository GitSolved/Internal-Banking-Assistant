#!/usr/bin/env python3
"""
Generate comprehensive compatibility documentation for Internal Assistant.
This script creates documentation that future processes can use to understand
version requirements and ensure compatibility.
"""

import json
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from internal_assistant.utils.version_check import (
    REQUIRED_VERSIONS,
    REQUIRED_PYTHON,
    CRITICAL_PACKAGES,
    generate_compatibility_report,
    export_version_constraints,
)


def generate_markdown_docs():
    """Generate comprehensive markdown documentation."""
    report = generate_compatibility_report()

    md_content = f"""# Internal Assistant - Compatibility Guide

## Overview
This document provides comprehensive compatibility information for Internal Assistant.
All version requirements are validated by the version check system in `src/utils/version_check.py`.

## Application Version
- **Current Version**: {report['application_version']}

## Python Version
- **Required**: {REQUIRED_PYTHON}
- **Current**: {report['python_version']['current']}
- **Compatible**: {'👾✅ Yes' if report['python_version']['compatible'] else '❌ No'}

## Critical Dependencies
These packages are essential for the application to function:

"""

    for package, info in report["critical_packages"].items():
        status = "👾✅ Compatible" if info["compatible"] else "❌ Incompatible"
        md_content += f"""### {package}
- **Current Version**: {info['current_version']}
- **Required Range**: {info['required_min']} to {info['required_max']}
- **Status**: {status}

"""

    md_content += """## All Dependencies
Complete list of all dependencies and their compatibility status:

"""

    for package, info in report["all_packages"].items():
        status = "👾✅" if info["compatible"] else "❌"
        md_content += f"- {status} **{package}**: {info['current_version']} (required: {info['required_min']} to {info['required_max']})\n"

    md_content += f"""

## System Requirements
- **Memory**: {report['system_resources'].get('memory', {}).get('total_gb', 'Unknown')} GB {'👾✅ Sufficient' if report['system_resources'].get('memory', {}).get('sufficient', False) else '❌ Insufficient'}
- **Disk Space**: {report['system_resources'].get('disk', {}).get('free_gb', 'Unknown')} GB free {'👾✅ Sufficient' if report['system_resources'].get('disk', {}).get('sufficient', False) else '❌ Insufficient'}

## Recommendations
"""

    if report["recommendations"]:
        for rec in report["recommendations"]:
            md_content += f"- {rec}\n"
    else:
        md_content += "- All systems are compatible! 🎉\n"

    md_content += f"""

## Version Constraints for pyproject.toml
When updating dependencies, use these exact constraints to ensure compatibility:

```toml
{export_version_constraints()}
```

## Validation Commands
To check compatibility:
```bash
# Run version check
poetry run python -c "from internal_assistant.utils.version_check import validate_dependency_versions; validate_dependency_versions()"

# Generate compatibility report
poetry run python -c "from internal_assistant.utils.version_check import generate_compatibility_report; import json; print(json.dumps(generate_compatibility_report(), indent=2))"
```

## Notes
- All version constraints are defined in `src/utils/version_check.py`
- The version check system validates these constraints at startup
- Critical packages are marked for immediate attention if incompatible
- Wildcard versions (*) indicate any version is acceptable
- This document is auto-generated and should be updated when dependencies change
"""

    return md_content


def generate_json_report():
    """Generate JSON compatibility report."""
    report = generate_compatibility_report()
    return json.dumps(report, indent=2)


def main():
    """Main function to generate all compatibility documentation."""
    output_dir = project_root / "docs" / "compatibility"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate markdown documentation
    md_content = generate_markdown_docs()
    md_file = output_dir / "compatibility_guide.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md_content)

    # Generate JSON report
    json_content = generate_json_report()
    json_file = output_dir / "compatibility_report.json"
    with open(json_file, "w", encoding="utf-8") as f:
        f.write(json_content)

    # Generate pyproject.toml constraints
    constraints = export_version_constraints()
    print(f"👾✅ Generated compatibility documentation:")
    print(f"   📄 {md_file}")
    print(f"   📊 {json_file}")
    print(f"\n📖 View the compatibility guide at: {md_file}")


if __name__ == "__main__":
    main()
