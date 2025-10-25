"""Version check utility for Internal Assistant.
Validates that all dependencies meet the required version constraints.
"""

import logging
import platform
import sys

import psutil

logger = logging.getLogger(__name__)

# Required version constraints for compatibility
# IMPORTANT: These constraints are used by the version check system
# and should be kept in sync with pyproject.toml
REQUIRED_VERSIONS: dict[str, tuple[str, str]] = {
    # Core Framework
    "fastapi": (">=0.108.0", "<0.115.0"),
    "pydantic": (">=2.8.0", "<2.9.0"),
    "gradio": (">=4.15.0", "<4.39.0"),
    # AI/ML Core
    "llama-index-core": (">=0.11.2", "<0.12.0"),
    "transformers": (">=4.44.2", "<5.0.0"),
    "torch": (">=2.4.1", "<3.0.0"),
    # Vector Store & Embeddings
    "llama-index-vector-stores-qdrant": ("*", "*"),
    "llama-index-embeddings-huggingface": ("*", "*"),
    "sentence-transformers": (">=3.1.1", "<4.0.0"),
    # LLM Components
    "llama-index-llms-ollama": ("*", "*"),
    "llama-index-llms-openai-like": ("*", "*"),
    # Security & Cryptography
    "cryptography": (">=3.1", "<4.0.0"),
    # File Processing
    "python-multipart": (">=0.0.10", "<1.0.0"),
    "docx2txt": (">=0.8", "<1.0.0"),
    # RSS/Feed Processing
    "feedparser": (">=6.0.10", "<7.0.0"),
    "aiohttp": (">=3.9.0", "<4.0.0"),
    "beautifulsoup4": (">=4.12.0", "<5.0.0"),
    # System & Performance
    "psutil": (">=7.0.0", "<8.0.0"),
    "watchdog": (">=4.0.1", "<5.0.0"),
    # Development Tools
    "pytest": (">=8.0.0", "<9.0.0"),
    "black": (">=24.0.0", "<25.0.0"),
    "ruff": (">=0.0.0", "<1.0.0"),
}

# Python version requirement (minimum version)
REQUIRED_PYTHON_MIN = "3.11.9"
REQUIRED_PYTHON_MAX = "3.12.0"

# Application version
APP_VERSION = "0.6.2"

# Critical packages that must be compatible for the application to function
CRITICAL_PACKAGES = ["fastapi", "pydantic", "llama-index-core", "transformers"]


def check_python_version() -> bool:
    """Check if the current Python version matches requirements."""
    current_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )

    try:
        from packaging import version as packaging_version

        current = packaging_version.parse(current_version)
        min_ver = packaging_version.parse(REQUIRED_PYTHON_MIN)
        max_ver = packaging_version.parse(REQUIRED_PYTHON_MAX)

        if not (min_ver <= current < max_ver):
            logger.error(
                "Python version out of range! Required: >=%s,<%s, Current: %s",
                REQUIRED_PYTHON_MIN,
                REQUIRED_PYTHON_MAX,
                current_version,
            )
            return False

        logger.info("👾✅ Python version check passed: %s", current_version)
        return True
    except ImportError:
        # Fallback to simple comparison if packaging not available
        if not (REQUIRED_PYTHON_MIN <= current_version < REQUIRED_PYTHON_MAX):
            logger.error(
                "Python version out of range! Required: >=%s,<%s, Current: %s",
                REQUIRED_PYTHON_MIN,
                REQUIRED_PYTHON_MAX,
                current_version,
            )
            return False
        logger.info("👾✅ Python version check passed: %s", current_version)
        return True


def get_package_version(package_name: str) -> str:
    """Get the installed version of a package."""
    try:
        from importlib.metadata import version
        return version(package_name)
    except Exception as e:
        # Package not found or other error with importlib.metadata
        # Try fallback to pkg_resources
        try:
            import pkg_resources
            return pkg_resources.get_distribution(package_name).version
        except Exception:
            # Package not found in pkg_resources either
            logger.warning("Could not get version for %s: %s", package_name, e)
            return "unknown"


def check_version_constraint(version: str, min_version: str, max_version: str) -> bool:
    """Check if a version meets the constraint requirements."""
    if version == "unknown":
        return True  # Skip unknown versions

    # Handle wildcard versions (any version is acceptable)
    if min_version == "*" or max_version == "*":
        return True

    try:
        from packaging import version as packaging_version

        current = packaging_version.parse(version)
        min_ver = packaging_version.parse(min_version.replace(">=", ""))
        max_ver = packaging_version.parse(max_version.replace("<", ""))

        return min_ver <= current < max_ver
    except ImportError:
        # Fallback to pkg_resources for older Python versions
        try:
            import pkg_resources

            current = pkg_resources.parse_version(version)
            min_ver = pkg_resources.parse_version(min_version.replace(">=", ""))
            max_ver = pkg_resources.parse_version(max_version.replace("<", ""))

            return min_ver <= current < max_ver
        except Exception as e:
            logger.warning("Could not parse version constraint for %s: %s", version, e)
            return True  # Skip parsing errors
    except Exception as e:
        logger.warning("Could not parse version constraint for %s: %s", version, e)
        return True  # Skip parsing errors


def check_system_requirements() -> bool:
    """Check system requirements and resources."""
    logger.info("Checking system requirements...")

    # Check Python version
    if not check_python_version():
        return False

    # Check system architecture
    arch = platform.architecture()[0]
    if arch != "64bit":
        logger.warning(
            "⚠️  System architecture: %s (64-bit recommended for AI models)", arch
        )

    # Check available memory
    try:
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        if memory_gb < 8:
            logger.warning(
                "⚠️  Low memory detected: %.1f GB (8+ GB recommended for AI models)",
                memory_gb,
            )
        else:
            logger.info("👾✅ System memory: %.1f GB", memory_gb)
    except Exception as e:
        logger.warning("Could not check system memory: %s", e)

    # Check available disk space
    try:
        disk = psutil.disk_usage(".")
        disk_gb = disk.free / (1024**3)
        if disk_gb < 10:
            logger.warning(
                "⚠️  Low disk space: %.1f GB free (10+ GB recommended)", disk_gb
            )
        else:
            logger.info("👾✅ Disk space: %.1f GB free", disk_gb)
    except Exception as e:
        logger.warning("Could not check disk space: %s", e)

    return True


def validate_dependency_versions() -> None:
    """Validate that all dependencies meet version requirements."""
    # Check system requirements first
    if not check_system_requirements():
        logger.error("❌ System requirements check failed!")
        return

    # Check dependency versions
    all_good = True
    critical_failures = []

    # Start with alien emoji, will change to red X if issues found
    status_emoji = "👾✅"
    logger.info("%s Validating dependency versions...", status_emoji)

    for package, (min_ver, max_ver) in REQUIRED_VERSIONS.items():
        version = get_package_version(package)

        if version == "unknown":
            logger.warning("⚠️  Could not verify version for %s", package)
            continue

        if check_version_constraint(version, min_ver, max_ver):
            logger.info("👾✅ %s: %s", package, version)
        else:
            logger.error(
                "❌ %s: %s (required: %s, %s)", package, version, min_ver, max_ver
            )
            all_good = False
            status_emoji = "❌"  # Change to red X
            # Mark critical packages
            if package in ["fastapi", "pydantic", "llama-index-core", "transformers"]:
                critical_failures.append(package)

    if not all_good:
        logger.error("❌ Dependency version validation failed!")
        if critical_failures:
            logger.error("❌ Critical failures: %s", ", ".join(critical_failures))
        logger.error("Please check COMPATIBILITY.md for version requirements")
        logger.error("Run: poetry lock && poetry install to fix")
    else:
        logger.info("👾✅ All dependency versions are compatible")


def log_version_info() -> None:
    """Log version information for debugging."""
    logger.info("Internal Assistant Version Information:")
    logger.info("Application Version: %s", get_application_version())
    logger.info(
        "Python: %s.%s.%s",
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro,
    )

    for package in REQUIRED_VERSIONS:
        version = get_package_version(package)
        logger.info("%s: %s", package, version)


def generate_compatibility_report() -> dict[str, any]:
    """Generate a comprehensive compatibility report for future processes."""
    report = {
        "application_version": get_application_version(),
        "python_version": {
            "required_min": REQUIRED_PYTHON_MIN,
            "required_max": REQUIRED_PYTHON_MAX,
            "required_range": f">={REQUIRED_PYTHON_MIN},<{REQUIRED_PYTHON_MAX}",
            "current": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "compatible": check_python_version(),
        },
        "critical_packages": {},
        "all_packages": {},
        "system_resources": {},
        "recommendations": [],
    }

    # Check all packages
    for package, (min_ver, max_ver) in REQUIRED_VERSIONS.items():
        version = get_package_version(package)
        compatible = check_version_constraint(version, min_ver, max_ver)

        package_info = {
            "current_version": version,
            "required_min": min_ver,
            "required_max": max_ver,
            "compatible": compatible,
        }

        report["all_packages"][package] = package_info

        if package in CRITICAL_PACKAGES:
            report["critical_packages"][package] = package_info

    # Check system resources
    try:
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        report["system_resources"]["memory"] = {
            "total_gb": round(memory_gb, 1),
            "sufficient": memory_gb >= 8,
        }
    except Exception:
        report["system_resources"]["memory"] = {"error": "Could not check memory"}

    try:
        disk = psutil.disk_usage(".")
        disk_gb = disk.free / (1024**3)
        report["system_resources"]["disk"] = {
            "free_gb": round(disk_gb, 1),
            "sufficient": disk_gb >= 10,
        }
    except Exception:
        report["system_resources"]["disk"] = {"error": "Could not check disk space"}

    # Generate recommendations
    if not report["python_version"]["compatible"]:
        report["recommendations"].append(
            f"Update Python to version >={REQUIRED_PYTHON_MIN},<{REQUIRED_PYTHON_MAX}"
        )

    for package, info in report["critical_packages"].items():
        if not info["compatible"]:
            report["recommendations"].append(
                f"Update {package} to version between {info['required_min']} and {info['required_max']}"
            )

    if not report["system_resources"].get("memory", {}).get("sufficient", True):
        report["recommendations"].append(
            "Consider upgrading to at least 8GB RAM for AI models"
        )

    if not report["system_resources"].get("disk", {}).get("sufficient", True):
        report["recommendations"].append("Ensure at least 10GB free disk space")

    return report


def get_application_version() -> str:
    """Get the current application version from pyproject.toml."""
    try:
        import tomllib

        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
            return data["tool"]["poetry"]["version"]
    except Exception:
        return APP_VERSION  # Fallback to hardcoded version


def export_version_constraints() -> str:
    """Export version constraints in a format suitable for pyproject.toml updates."""
    constraints = []
    constraints.append("# Version constraints for pyproject.toml")
    constraints.append("# Generated by internal_assistant.utils.version_check")
    constraints.append(
        "# Update these in pyproject.toml to match version check requirements"
    )
    constraints.append("")

    for package, (min_ver, max_ver) in REQUIRED_VERSIONS.items():
        if min_ver == "*" and max_ver == "*":
            constraints.append(f'{package} = "*"  # Any version acceptable')
        else:
            # Convert to Poetry format
            poetry_constraint = f'{package} = "{min_ver}, {max_ver}"'
            constraints.append(f"{poetry_constraint}  # Required for compatibility")

    return "\n".join(constraints)
