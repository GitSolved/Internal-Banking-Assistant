"""
UI Formatting Utilities

Pure utility functions for formatting and display purposes.
Extracted from the monolithic ui.py file for better maintainability.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


def get_file_type(filename: str) -> str:
    """Get file type from filename."""
    extension = filename.lower().split(".")[-1] if "." in filename else ""
    type_mapping = {
        "pdf": "pdf",
        "doc": "word",
        "docx": "word",
        "xls": "excel",
        "xlsx": "excel",
        "csv": "excel",
    }
    return type_mapping.get(extension, "other")


def get_file_type_icon(file_type: str) -> str:
    """Get emoji icon for file type."""
    icon_mapping = {"pdf": "📄", "word": "📝", "excel": "📊", "other": "📄"}
    return icon_mapping.get(file_type, "📄")


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    size = float(size_bytes)

    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1

    return f"{size:.1f} {size_names[i]}"


def extract_cve_id(text: str) -> str:
    """Extract CVE ID from text."""
    import re

    cve_pattern = r"CVE-\d{4}-\d{4,7}"
    match = re.search(cve_pattern, text, re.IGNORECASE)
    return match.group() if match else "Unknown"


def determine_cve_severity(text: str) -> str:
    """Determine CVE severity from text description."""
    text_lower = text.lower()

    # Critical indicators
    if any(
        term in text_lower
        for term in ["critical", "remote code execution", "rce", "zero-day", "0-day"]
    ):
        return "Critical"

    # High indicators
    elif any(
        term in text_lower
        for term in [
            "high",
            "privilege escalation",
            "authentication bypass",
            "sql injection",
        ]
    ):
        return "High"

    # Medium indicators
    elif any(
        term in text_lower
        for term in ["medium", "information disclosure", "denial of service", "dos"]
    ):
        return "Medium"

    # Low indicators
    elif any(term in text_lower for term in ["low", "minor", "cosmetic"]):
        return "Low"

    # Default to Medium if unclear
    return "Medium"
