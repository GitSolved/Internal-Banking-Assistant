"""
Version check utility for Internal Assistant.
Validates that all dependencies meet the required version constraints.
"""

import logging
import sys
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Required version constraints for compatibility
REQUIRED_VERSIONS: Dict[str, Tuple[str, str]] = {
    'fastapi': ('>=0.108.0', '<0.115.0'),
    'pydantic': ('>=2.8.0', '<2.9.0'),
    'gradio': ('>=4.15.0', '<4.39.0'),
}

# Python version requirement
REQUIRED_PYTHON = '3.11.9'


def check_python_version() -> bool:
    """Check if the current Python version matches requirements."""
    current_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    if current_version != REQUIRED_PYTHON:
        logger.error(
            "Python version mismatch! Required: %s, Current: %s",
            REQUIRED_PYTHON, current_version
        )
        return False
    
    logger.info("Python version check passed: %s", current_version)
    return True


def get_package_version(package_name: str) -> str:
    """Get the installed version of a package."""
    try:
        import pkg_resources
        return pkg_resources.get_distribution(package_name).version
    except ImportError:
        logger.warning("pkg_resources not available, skipping version check for %s", package_name)
        return "unknown"
    except Exception as e:
        logger.warning("Could not get version for %s: %s", package_name, e)
        return "unknown"


def check_version_constraint(version: str, min_version: str, max_version: str) -> bool:
    """Check if a version meets the constraint requirements."""
    if version == "unknown":
        return True  # Skip unknown versions
    
    try:
        import pkg_resources
        current = pkg_resources.parse_version(version)
        min_ver = pkg_resources.parse_version(min_version.replace('>=', ''))
        max_ver = pkg_resources.parse_version(max_version.replace('<', ''))
        
        return min_ver <= current < max_ver
    except Exception as e:
        logger.warning("Could not parse version constraint for %s: %s", version, e)
        return True  # Skip parsing errors


def validate_dependency_versions() -> None:
    """Validate that all dependencies meet version requirements."""
    logger.info("Validating dependency versions...")
    
    # Check Python version
    if not check_python_version():
        logger.error("Python version validation failed!")
        return
    
    # Check dependency versions
    all_good = True
    
    for package, (min_ver, max_ver) in REQUIRED_VERSIONS.items():
        version = get_package_version(package)
        
        if version == "unknown":
            logger.warning("Could not verify version for %s", package)
            continue
        
        if check_version_constraint(version, min_ver, max_ver):
            logger.info("✅ %s: %s", package, version)
        else:
            logger.error(
                "❌ %s: %s (required: %s, %s)",
                package, version, min_ver, max_ver
            )
            all_good = False
    
    if not all_good:
        logger.error("Dependency version validation failed!")
        logger.error("Please check COMPATIBILITY.md for version requirements")
        logger.error("Run: poetry lock && poetry install to fix")
    else:
        logger.info("✅ All dependency versions are compatible")


def log_version_info() -> None:
    """Log version information for debugging."""
    logger.info("Internal Assistant Version Information:")
    logger.info("Python: %s.%s.%s", sys.version_info.major, sys.version_info.minor, sys.version_info.micro)
    
    for package in REQUIRED_VERSIONS.keys():
        version = get_package_version(package)
        logger.info("%s: %s", package, version)
