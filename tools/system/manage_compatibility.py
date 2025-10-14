#!/usr/bin/env python3
"""
Compatibility Management Utility for Internal Assistant

This unified script manages dependency compatibility with multiple modes:
- Check mode: Analyze current dependency versions for compatibility issues
- Enforce mode: Verify versions against strict requirements and pyproject.toml
- Fix mode: Auto-fix compatibility issues where possible

Replaces: check_compatibility.py + enforce_versions.py
"""

import sys
import subprocess
import pkg_resources
from pathlib import Path
import argparse
from typing import Dict, List, Tuple, Optional


# Required version constraints
COMPATIBILITY_CONSTRAINTS = {
    "fastapi": {
        "min": "0.108.0",
        "max": "0.115.0",
        "range": ">=0.108.0,<0.115.0",
        "issue": "Pydantic schema generation error with Gradio",
    },
    "pydantic": {
        "min": "2.8.0",
        "max": "2.9.0",
        "range": ">=2.8.0,<2.9.0",
        "issue": "LlamaIndex import compatibility",
    },
    "gradio": {
        "min": "4.15.0",
        "max": "4.39.0",
        "range": ">=4.15.0,<4.39.0",
        "issue": "FastAPI integration issues",
    },
}

# Python version requirement
REQUIRED_PYTHON = "3.11.9"


def get_installed_version_pip(package_name: str) -> Optional[str]:
    """Get installed version of a package using pip show."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package_name],
            capture_output=True,
            text=True,
            check=True,
        )
        for line in result.stdout.split("\\n"):
            if line.startswith("Version:"):
                return line.split(":")[1].strip()
    except subprocess.CalledProcessError:
        return None
    return None


def get_installed_version_pkg_resources(package_name: str) -> Optional[str]:
    """Get installed version of a package using pkg_resources."""
    try:
        return pkg_resources.get_distribution(package_name).version
    except pkg_resources.DistributionNotFound:
        return None


def check_version_constraint(version: str, min_version: str, max_version: str) -> bool:
    """Check if a version meets the constraint requirements."""
    try:
        current = pkg_resources.parse_version(version)
        min_ver = pkg_resources.parse_version(min_version)
        max_ver = pkg_resources.parse_version(max_version)

        return min_ver <= current < max_ver
    except Exception:
        return False


def check_python_version() -> Tuple[bool, str]:
    """Check if the current Python version matches requirements."""
    current_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )

    if current_version != REQUIRED_PYTHON:
        return False, f"Python {current_version} (required: {REQUIRED_PYTHON})"

    return True, f"Python {current_version}"


def check_compatibility_mode() -> Dict[str, any]:
    """Check mode: Analyze current versions for compatibility issues."""
    print("Checking Internal Assistant dependency compatibility...")
    print("=" * 60)

    issues = []
    warnings = []
    successes = []

    # Check Python version
    python_ok, python_msg = check_python_version()
    if python_ok:
        successes.append(f"OK {python_msg}")
    else:
        issues.append(f"ERROR {python_msg}")

    # Check package versions
    for package, constraint in COMPATIBILITY_CONSTRAINTS.items():
        version = get_installed_version_pip(package)
        if version:
            # Check if version is in acceptable range
            if check_version_constraint(version, constraint["min"], constraint["max"]):
                successes.append(f"OK {package}: {version}")
            else:
                issues.append(f"ERROR {package} {version} - {constraint['issue']}")
                issues.append(f"    Required: {constraint['range']}")
        else:
            issues.append(f"ERROR {package} - Not installed")

    return {
        "mode": "check",
        "python_ok": python_ok,
        "issues": issues,
        "warnings": warnings,
        "successes": successes,
    }


def enforce_mode() -> Dict[str, any]:
    """Enforce mode: Strict version checking against requirements."""
    print("Internal Assistant Version Enforcement Check")
    print("=" * 60)

    issues = []
    successes = []

    # Check Python version (strict)
    python_ok, python_msg = check_python_version()
    if python_ok:
        successes.append(f"OK {python_msg}")
    else:
        issues.append(f"ERROR {python_msg}")

    # Check dependency versions (strict)
    deps_ok = True
    for package, constraint in COMPATIBILITY_CONSTRAINTS.items():
        version = get_installed_version_pkg_resources(package)

        if version is None:
            issues.append(f"ERROR {package}: Not installed")
            deps_ok = False
        elif check_version_constraint(version, constraint["min"], constraint["max"]):
            successes.append(f"OK {package}: {version}")
        else:
            issues.append(
                f"ERROR {package}: {version} (required: {constraint['range']})"
            )
            deps_ok = False

    # Check pyproject.toml configuration
    config_ok, config_msg = check_pyproject_toml()
    if config_ok:
        successes.append(f"OK {config_msg}")
    else:
        issues.append(f"ERROR {config_msg}")

    return {
        "mode": "enforce",
        "python_ok": python_ok,
        "deps_ok": deps_ok,
        "config_ok": config_ok,
        "all_ok": python_ok and deps_ok and config_ok,
        "issues": issues,
        "successes": successes,
    }


def check_pyproject_toml() -> Tuple[bool, str]:
    """Check if pyproject.toml has correct version constraints."""
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        return False, "pyproject.toml not found"

    try:
        content = pyproject_path.read_text()

        # Check if version constraints are present
        missing_constraints = []

        for package, constraint in COMPATIBILITY_CONSTRAINTS.items():
            expected_range = constraint["range"]

            # Look for the package with version constraint
            if f"{expected_range}" not in content:
                missing_constraints.append(f"{package} {expected_range}")

        if missing_constraints:
            return (
                False,
                f"pyproject.toml missing constraints: {', '.join(missing_constraints)}",
            )

        return True, "pyproject.toml has correct version constraints"

    except Exception as e:
        return False, f"Error reading pyproject.toml: {e}"


def fix_mode() -> Dict[str, any]:
    """Fix mode: Attempt to auto-fix compatibility issues."""
    print("Auto-fixing Internal Assistant compatibility issues...")
    print("=" * 60)

    issues = []
    fixes_applied = []
    manual_actions = []

    # Check current state
    current_state = enforce_mode()

    if current_state["all_ok"]:
        return {
            "mode": "fix",
            "nothing_to_fix": True,
            "issues": [],
            "fixes_applied": [],
            "manual_actions": [],
        }

    # Python version cannot be auto-fixed
    if not current_state["python_ok"]:
        manual_actions.append(f"Install Python {REQUIRED_PYTHON}")

    # Check if dependencies can be fixed with poetry
    poetry_install_needed = False
    poetry_lock_needed = False

    for package, constraint in COMPATIBILITY_CONSTRAINTS.items():
        version = get_installed_version_pkg_resources(package)

        if version is None:
            poetry_install_needed = True
            fixes_applied.append(f"Will install {package}")
        elif not check_version_constraint(
            version, constraint["min"], constraint["max"]
        ):
            poetry_lock_needed = True
            poetry_install_needed = True
            fixes_applied.append(
                f"Will update {package} from {version} to {constraint['range']}"
            )

    # Check pyproject.toml
    config_ok, config_msg = check_pyproject_toml()
    if not config_ok:
        manual_actions.append("Update pyproject.toml with correct version constraints")
        manual_actions.append(config_msg)

    # Apply fixes where possible
    if poetry_lock_needed:
        print("\nRunning poetry lock...")
        try:
            result = subprocess.run(
                ["poetry", "lock"], capture_output=True, text=True, check=True
            )
            fixes_applied.append("poetry lock completed")
        except subprocess.CalledProcessError as e:
            issues.append(f"ERROR poetry lock failed: {e}")
        except FileNotFoundError:
            manual_actions.append("Install Poetry package manager")

    if poetry_install_needed:
        print("Running poetry install...")
        try:
            result = subprocess.run(
                ["poetry", "install"], capture_output=True, text=True, check=True
            )
            fixes_applied.append("poetry install completed")
        except subprocess.CalledProcessError as e:
            issues.append(f"ERROR poetry install failed: {e}")
        except FileNotFoundError:
            manual_actions.append("Install Poetry package manager")

    return {
        "mode": "fix",
        "nothing_to_fix": False,
        "issues": issues,
        "fixes_applied": fixes_applied,
        "manual_actions": manual_actions,
    }


def display_results(results: Dict[str, any]) -> int:
    """Display results and return appropriate exit code."""

    if results["mode"] == "check":
        # Display successes
        if results["successes"]:
            print("\nCOMPATIBLE VERSIONS:")
            for success in results["successes"]:
                print(f"  {success}")

        # Display issues
        if results["issues"]:
            print("\nCOMPATIBILITY ISSUES FOUND:")
            for issue in results["issues"]:
                print(f"  {issue}")

            print("\nRECOMMENDATIONS:")
            print("  1. Run: python dev/scripts/manage_compatibility.py --fix")
            print("  2. Or manually update versions in pyproject.toml")
            print("  3. Run: poetry lock && poetry install")
            print("  4. Test application after updates")
            return 1
        else:
            print("\nOK All dependencies are compatible!")
            print("   The application should work without issues.")
            return 0

    elif results["mode"] == "enforce":
        # Display successes
        if results["successes"]:
            print("\nOK VERSION REQUIREMENTS MET:")
            for success in results["successes"]:
                print(f"  {success}")

        # Display issues
        if results["issues"]:
            print("\nERROR VERSION REQUIREMENTS NOT MET:")
            for issue in results["issues"]:
                print(f"  {issue}")

        print("\n" + "=" * 60)

        if results["all_ok"]:
            print("OK All version requirements are met!")
            print("   The application should work without compatibility issues.")
            return 0
        else:
            print("ERROR Version requirements not met!")
            print("\n To fix:")
            print(
                "   1. Run: poetry run python dev/scripts/manage_compatibility.py --fix"
            )
            print("   2. Or manually: poetry lock && poetry install")
            print("   3. Ensure Python 3.11.9 is installed")
            print("   4. Run this script again to verify")
            return 1

    elif results["mode"] == "fix":
        if results["nothing_to_fix"]:
            print("\nOK No compatibility issues found!")
            print("   All dependencies are already correctly configured.")
            return 0

        # Display fixes applied
        if results["fixes_applied"]:
            print("\nOK FIXES APPLIED:")
            for fix in results["fixes_applied"]:
                print(f"  {fix}")

        # Display manual actions needed
        if results["manual_actions"]:
            print("\nWARNING  MANUAL ACTIONS REQUIRED:")
            for action in results["manual_actions"]:
                print(f"  • {action}")

        # Display remaining issues
        if results["issues"]:
            print("\nERROR ISSUES ENCOUNTERED:")
            for issue in results["issues"]:
                print(f"  {issue}")

        # Verify fix was successful
        print("\nVerifying fixes...")
        verification = enforce_mode()

        if verification["all_ok"]:
            print("\nOK All compatibility issues have been resolved!")
            return 0
        else:
            print("\nWARNING  Some issues remain. Manual intervention may be required.")
            return 1


def main():
    parser = argparse.ArgumentParser(
        description="Manage Internal Assistant dependency compatibility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check current compatibility (default)
  python manage_compatibility.py --check
  
  # Strict version enforcement check
  python manage_compatibility.py --enforce
  
  # Auto-fix compatibility issues
  python manage_compatibility.py --fix
        """,
    )

    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--check",
        action="store_true",
        default=True,
        help="Check current versions for compatibility issues (default)",
    )
    mode_group.add_argument(
        "--enforce",
        action="store_true",
        help="Strict version enforcement against requirements",
    )
    mode_group.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix compatibility issues where possible",
    )

    args = parser.parse_args()

    # Override default if other modes specified
    if args.enforce or args.fix:
        args.check = False

    # Execute based on mode
    if args.fix:
        results = fix_mode()
    elif args.enforce:
        results = enforce_mode()
    else:  # check mode (default)
        results = check_compatibility_mode()

    return display_results(results)


if __name__ == "__main__":
    sys.exit(main())
