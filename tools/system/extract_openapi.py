#!/usr/bin/env python3
"""
OpenAPI Specification Extraction Tool

Extracts OpenAPI specification from a FastAPI application and exports to JSON or YAML.

Usage:
    poetry run python tools/system/extract_openapi.py main:app
    poetry run python tools/system/extract_openapi.py main:app --out openapi.json
    poetry run python tools/system/extract_openapi.py internal_assistant.launcher:app --out api-spec.yaml
"""

import argparse
import json
import sys
from pathlib import Path

import yaml
from uvicorn.importer import import_from_string


def extract_openapi_spec(
    app_string: str, output_file: str, app_dir: str = None
) -> None:
    """Extract and save OpenAPI specification from FastAPI app."""

    if app_dir:
        print(f"Adding {app_dir} to sys.path")
        sys.path.insert(0, app_dir)

    print(f"Importing app from {app_string}")
    app = import_from_string(app_string)
    openapi = app.openapi()
    version = openapi.get("openapi", "unknown version")

    print(f"Writing OpenAPI spec v{version}")
    output_path = Path(output_file)

    with open(output_path, "w") as f:
        if output_path.suffix == ".json":
            json.dump(openapi, f, indent=2)
        else:
            yaml.dump(openapi, f, sort_keys=False)

    print(f"Spec written to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract OpenAPI specification from FastAPI application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Extract from default app
    python extract_openapi.py main:app

    # Export to JSON
    python extract_openapi.py main:app --out openapi.json

    # Specify app directory
    python extract_openapi.py main:app --app-dir /path/to/app --out spec.yaml
        """,
    )

    parser.add_argument(
        "app",
        help='App import string (e.g., "main:app", "internal_assistant.launcher:app")',
        default="main:app",
    )
    parser.add_argument(
        "--app-dir",
        help="Directory containing the app (added to sys.path)",
        default=None,
    )
    parser.add_argument(
        "--out", help="Output file path (.json or .yaml)", default="openapi.yaml"
    )

    args = parser.parse_args()

    try:
        extract_openapi_spec(args.app, args.out, args.app_dir)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
