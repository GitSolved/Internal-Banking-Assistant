"""UI Data Processing Utilities

Data processing functions for document analysis, categorization, and metadata handling.
Extracted from the monolithic ui.py file for better maintainability.
"""

import logging

logger = logging.getLogger(__name__)


def get_category_counts(files: list[list[str]]) -> dict[str, int]:
    """Get document counts by category for display."""
    try:
        category_counts = {
            "🔒 Security Reports": 0,
            "📋 Policy Documents": 0,
            "🔍 Threat Intelligence": 0,
            "🛡️ Incident Response": 0,
        }

        for file_row in files:
            if file_row and len(file_row) > 0:
                file_name = file_row[0]
                file_name_lower = file_name.lower()

                # Security Reports (general security assessments, audits, compliance)
                if any(
                    term in file_name_lower
                    for term in [
                        "security assessment",
                        "security_assessment",
                        "security audit",
                        "security_audit",
                        "compliance audit",
                        "compliance_audit",
                        "vulnerability assessment",
                        "vulnerability_assessment",
                        "penetration test",
                        "penetration_test",
                        "security scan",
                        "security_scan",
                        "risk assessment",
                        "risk_assessment",
                        "security review",
                        "security_review",
                        "security evaluation",
                        "security_evaluation",
                        "vulnerability scan",
                        "vulnerability_scan",
                        "security report",
                        "security_report",
                    ]
                ):
                    category_counts["🔒 Security Reports"] += 1

                # Policy Documents
                elif any(
                    term in file_name_lower
                    for term in [
                        "policy",
                        "procedure",
                        "guideline",
                        "manual",
                        "handbook",
                        "protocol",
                        "standard",
                        "regulation",
                        "code of conduct",
                        "code_of_conduct",
                    ]
                ):
                    category_counts["📋 Policy Documents"] += 1

                # Threat Intelligence (specific threat intel terms)
                elif any(
                    term in file_name_lower
                    for term in [
                        "threat intelligence",
                        "threat_intelligence",
                        "ioc",
                        "malware",
                        "apt",
                        "campaign",
                        "cve",
                        "exploit",
                        "zero-day",
                        "zero_day",
                        "adversary",
                        "tactic",
                        "technique",
                        "mitre",
                        "att&ck",
                        "ttp",
                        "indicator",
                        "signature",
                        "yara",
                    ]
                ):
                    category_counts["🔍 Threat Intelligence"] += 1

                # Incident Response (specific incident response terms)
                elif any(
                    term in file_name_lower
                    for term in [
                        "incident response",
                        "incident_response",
                        "forensics",
                        "investigation",
                        "breach",
                        "attack",
                        "alert",
                        "detection",
                        "mitigation",
                        "recovery",
                        "containment",
                        "eradication",
                        "lessons learned",
                        "lessons_learned",
                        "post-mortem",
                        "post_mortem",
                    ]
                ):
                    category_counts["🛡️ Incident Response"] += 1

                # Skip files that don't match any category
                else:
                    pass

        return category_counts
    except Exception as e:
        logger.error(f"Error getting category counts: {e}")
        return {}


def analyze_document_types(files: list[list[str]]) -> dict:
    """Analyze document types and return counts for cybersecurity-focused categories."""
    try:
        # Initialize counters with cybersecurity-focused categories
        type_counts = {
            "Security & Compliance": 0,
            "Policy & Governance": 0,
            "Threat Intelligence": 0,
            "Incident Response": 0,
            "Technical & Infrastructure": 0,
            "Research & Analysis": 0,
        }

        # Initialize content type flags
        has_security = False
        has_technical = False
        has_legal = False
        has_research = False

        total_files = len(files) if files else 0

        if total_files == 0:
            return {
                "total_files": 0,
                "type_counts": type_counts,
                "has_security": False,
                "has_technical": False,
                "has_legal": False,
                "has_research": False,
            }

        # Analyze each file
        for file_row in files:
            if file_row and len(file_row) > 0:
                file_name = file_row[0]
                file_name_lower = file_name.lower()

                # Security & Compliance Documents (security assessments, audits, compliance)
                if any(
                    term in file_name_lower
                    for term in [
                        "security assessment",
                        "security_assessment",
                        "security audit",
                        "security_audit",
                        "compliance audit",
                        "compliance_audit",
                        "vulnerability assessment",
                        "vulnerability_assessment",
                        "penetration test",
                        "penetration_test",
                        "security scan",
                        "security_scan",
                        "risk assessment",
                        "risk_assessment",
                        "security review",
                        "security_review",
                        "security evaluation",
                        "security_evaluation",
                        "vulnerability scan",
                        "vulnerability_scan",
                        "security report",
                        "security_report",
                        "firewall",
                        "ids",
                        "ips",
                        "siem",
                        "edr",
                        "xdr",
                        "mdr",
                        "compliance",
                        "regulatory",
                        "certification",
                        "iso",
                        "soc",
                        "pci",
                        "dss",
                        "gdpr",
                        "sox",
                    ]
                ):
                    type_counts["Security & Compliance"] += 1
                    has_security = True

                # Policy & Governance Documents
                elif any(
                    term in file_name_lower
                    for term in [
                        "policy",
                        "procedure",
                        "guideline",
                        "manual",
                        "handbook",
                        "protocol",
                        "standard",
                        "regulation",
                        "code of conduct",
                        "code_of_conduct",
                        "rules",
                        "terms",
                        "conditions",
                        "agreement",
                        "contract",
                        "governance",
                        "framework",
                        "baseline",
                        "control",
                        "requirement",
                        "specification",
                    ]
                ):
                    type_counts["Policy & Governance"] += 1
                    has_legal = True

                # Threat Intelligence Documents (specific threat intel terms)
                elif any(
                    term in file_name_lower
                    for term in [
                        "threat intelligence",
                        "threat_intelligence",
                        "ioc",
                        "malware",
                        "apt",
                        "campaign",
                        "cve",
                        "exploit",
                        "zero-day",
                        "zero_day",
                        "adversary",
                        "tactic",
                        "technique",
                        "mitre",
                        "att&ck",
                        "ttp",
                        "indicator",
                        "signature",
                        "yara",
                        "stix",
                        "taxii",
                        "threat",
                        "attack",
                        "vulnerability",
                        "exploit",
                        "malware",
                        "ransomware",
                        "phishing",
                    ]
                ):
                    type_counts["Threat Intelligence"] += 1
                    has_research = True

                # Incident Response Documents (specific incident response terms)
                elif any(
                    term in file_name_lower
                    for term in [
                        "incident response",
                        "incident_response",
                        "forensics",
                        "investigation",
                        "breach",
                        "attack",
                        "alert",
                        "detection",
                        "mitigation",
                        "recovery",
                        "containment",
                        "eradication",
                        "lessons learned",
                        "lessons_learned",
                        "post-mortem",
                        "post_mortem",
                        "incident",
                        "breach",
                        "compromise",
                        "intrusion",
                        "data breach",
                        "data_breach",
                    ]
                ):
                    type_counts["Incident Response"] += 1
                    has_technical = True

                # Technical & Infrastructure Documents
                elif any(
                    term in file_name_lower
                    for term in [
                        "technical",
                        "spec",
                        "architecture",
                        "design",
                        "api",
                        "database",
                        "system",
                        "infrastructure",
                        "code",
                        "development",
                        "software",
                        "hardware",
                        "network",
                        "config",
                        "deployment",
                        "configuration",
                        "blueprint",
                        "diagram",
                        "topology",
                        "schema",
                        "protocol",
                        "interface",
                    ]
                ):
                    type_counts["Technical & Infrastructure"] += 1
                    has_technical = True

                # Research & Analysis Documents
                elif any(
                    term in file_name_lower
                    for term in [
                        "research",
                        "analysis",
                        "study",
                        "report",
                        "whitepaper",
                        "survey",
                        "trend",
                        "forecast",
                        "insight",
                        "data",
                        "statistics",
                        "metrics",
                        "benchmark",
                        "comparison",
                        "evaluation",
                        "assessment",
                        "findings",
                        "conclusion",
                        "recommendation",
                        "summary",
                    ]
                ):
                    type_counts["Research & Analysis"] += 1
                    has_research = True

                # Everything else goes to Research & Analysis as default
                else:
                    type_counts["Research & Analysis"] += 1

        return {
            "total_files": total_files,
            "type_counts": type_counts,
            "has_security": has_security,
            "has_technical": has_technical,
            "has_legal": has_legal,
            "has_research": has_research,
        }

    except Exception as e:
        logger.error(f"Error analyzing document types: {e}")
        return {
            "total_files": 0,
            "type_counts": {
                "Security": 0,
                "Policy": 0,
                "Threat Intelligence": 0,
                "Incident Response": 0,
                "Other": 0,
            },
            "has_security": False,
            "has_technical": False,
            "has_legal": False,
            "has_research": False,
        }


def get_document_counts(files: list[list[str]]) -> dict[str, int]:
    """Get document counts by file type."""
    try:
        from .formatters import get_file_type

        type_counts = {}

        for file_row in files:
            if file_row and len(file_row) > 0:
                file_name = file_row[0]
                file_type = get_file_type(file_name)

                if file_type not in type_counts:
                    type_counts[file_type] = 0
                type_counts[file_type] += 1

        return type_counts
    except Exception as e:
        logger.error(f"Error getting document counts: {e}")
        return {}


def filter_documents_by_query(
    files: list[list[str]], search_query: str = "", filter_type: str = "all"
) -> tuple[list[list[str]], dict]:
    """Filter documents based on search query and filter type."""
    try:
        if not search_query.strip():
            return files, {}

        query_lower = search_query.lower()
        filtered_files = []

        for file_row in files:
            if file_row and len(file_row) > 0:
                file_name = file_row[0]
                file_name_lower = file_name.lower()

                # Check if file matches search query
                if query_lower in file_name_lower:
                    filtered_files.append(file_row)

        # Get metadata for filtered files
        doc_metadata = {
            "total_files": len(files),
            "filtered_count": len(filtered_files),
            "search_query": search_query,
            "filter_type": filter_type,
        }

        return filtered_files, doc_metadata
    except Exception as e:
        logger.error(f"Error filtering documents: {e}")
        return [], {}


def get_chat_mentioned_documents(history: list[list[str]]) -> set:
    """Extract document names mentioned in chat history."""
    try:
        mentioned_docs = set()

        for message_pair in history:
            if len(message_pair) >= 2:
                # Check user message
                user_msg = message_pair[0].lower()
                # Check assistant message
                assistant_msg = message_pair[1].lower()

                # Look for document references in both messages
                for msg in [user_msg, assistant_msg]:
                    # Simple pattern matching for document references
                    # This could be enhanced with more sophisticated parsing
                    if (
                        "document" in msg
                        or "file" in msg
                        or ".pdf" in msg
                        or ".doc" in msg
                    ):
                        # Extract potential document names
                        words = msg.split()
                        for word in words:
                            if any(
                                ext in word.lower()
                                for ext in [".pdf", ".doc", ".txt", ".xlsx"]
                            ):
                                mentioned_docs.add(word)

        return mentioned_docs
    except Exception as e:
        logger.error(f"Error extracting mentioned documents: {e}")
        return set()
