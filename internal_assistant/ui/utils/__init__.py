"""UI Utilities Package

Utility functions extracted from the monolithic ui.py file for better maintainability.
"""

from .data_processors import (
    analyze_document_types,
    filter_documents_by_query,
    get_category_counts,
    get_chat_mentioned_documents,
    get_document_counts,
)
from .formatters import (
    determine_cve_severity,
    extract_cve_id,
    format_file_size,
    get_file_type,
    get_file_type_icon,
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
