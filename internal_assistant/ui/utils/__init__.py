"""
UI Utilities Package

Utility functions extracted from the monolithic ui.py file for better maintainability.
"""

from .formatters import (
    get_file_type,
    get_file_type_icon,
    format_file_size,
    extract_cve_id,
    determine_cve_severity,
)

from .data_processors import (
    get_category_counts,
    analyze_document_types,
    get_document_counts,
    filter_documents_by_query,
    get_chat_mentioned_documents,
)

__all__ = [
    # Formatters
    "get_file_type",
    "get_file_type_icon",
    "format_file_size",
    "extract_cve_id",
    "determine_cve_severity",
    # Data Processors
    "get_category_counts",
    "analyze_document_types",
    "get_document_counts",
    "filter_documents_by_query",
    "get_chat_mentioned_documents",
]
