"""State Selectors

This module contains selectors for computing derived values from the application state.
Selectors provide an efficient way to compute values that depend on multiple state properties
while memoizing results until dependencies change.

Part of Phase 2.2: State Schema Design and Implementation
Author: UI Refactoring Team
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from internal_assistant.ui.state.state_manager import MemoizedSelector

logger = logging.getLogger(__name__)


# ============================================================================
# Chat State Selectors
# ============================================================================


def create_chat_status_selector() -> MemoizedSelector[dict[str, Any]]:
    """Create a selector for chat status information."""

    def selector(state: dict[str, Any]) -> dict[str, Any]:
        chat_state = state.get("chat", {})
        settings_state = state.get("settings", {})

        history_length = len(chat_state.get("history", []))
        is_processing = chat_state.get("is_processing", False)
        mode = chat_state.get("mode", "RAG Mode")
        system_prompt = settings_state.get("system_prompt", "")

        return {
            "mode": mode,
            "is_processing": is_processing,
            "history_length": history_length,
            "has_system_prompt": len(system_prompt.strip()) > 0,
            "is_document_mode": mode == "RAG Mode",
            "can_chat": not is_processing,
            "status_text": "Processing..." if is_processing else "Ready",
            "last_message_time": None,  # Could be computed from history
        }

    dependencies = {
        "chat.mode",
        "chat.is_processing",
        "chat.history",
        "settings.system_prompt",
    }
    return MemoizedSelector(selector, dependencies)


def create_chat_settings_selector() -> MemoizedSelector[dict[str, Any]]:
    """Create a selector for effective chat settings."""

    def selector(state: dict[str, Any]) -> dict[str, Any]:
        settings_state = state.get("settings", {})
        chat_settings = settings_state.get("chat", {})
        rag_settings = settings_state.get("rag", {})

        return {
            "temperature": chat_settings.get("temperature", 0.1),
            "max_tokens": chat_settings.get("max_tokens", 2048),
            "citation_style": chat_settings.get("citation_style", "Bullets"),
            "show_sources": chat_settings.get("show_sources", True),
            "similarity_threshold": rag_settings.get("similarity_threshold", 0.5),
            "max_sources": rag_settings.get("max_sources", 5),
            "enable_reranking": rag_settings.get("enable_reranking", True),
        }

    dependencies = {
        "settings.chat.temperature",
        "settings.chat.max_tokens",
        "settings.chat.citation_style",
        "settings.chat.show_sources",
        "settings.rag.similarity_threshold",
        "settings.rag.max_sources",
        "settings.rag.enable_reranking",
    }
    return MemoizedSelector(selector, dependencies)


# ============================================================================
# Document State Selectors
# ============================================================================


def create_document_counts_selector() -> MemoizedSelector[dict[str, Any]]:
    """Create a selector for document counts and statistics."""

    def selector(state: dict[str, Any]) -> dict[str, Any]:
        doc_state = state.get("documents", {})
        counts = doc_state.get("counts", {})
        filter_config = doc_state.get("filter", {})

        total = counts.get("total", 0)
        selected_count = len(doc_state.get("selected_documents", []))
        processing_count = len(doc_state.get("processing_queue", []))

        # Calculate filtered counts based on current filter
        current_filter = filter_config.get("type", "all")
        filtered_count = total

        if current_filter != "all":
            # Map filter types to count fields
            filter_map = {"pdf": "pdf_count", "docx": "docx_count", "txt": "txt_count"}
            if current_filter in filter_map:
                filtered_count = counts.get(filter_map[current_filter], 0)

        return {
            "total": total,
            "filtered": filtered_count,
            "selected": selected_count,
            "processing": processing_count,
            "categories": {
                "security_compliance": counts.get("security_compliance", 0),
                "policy_governance": counts.get("policy_governance", 0),
                "threat_intelligence": counts.get("threat_intelligence", 0),
                "incident_response": counts.get("incident_response", 0),
                "technical_infrastructure": counts.get("technical_infrastructure", 0),
                "research_analysis": counts.get("research_analysis", 0),
            },
            "file_types": {
                "pdf": counts.get("pdf_count", 0),
                "docx": counts.get("docx_count", 0),
                "txt": counts.get("txt_count", 0),
                "other": counts.get("other_count", 0),
            },
            "has_documents": total > 0,
            "has_selected": selected_count > 0,
            "is_processing": processing_count > 0,
        }

    dependencies = {
        "documents.counts",
        "documents.selected_documents",
        "documents.processing_queue",
        "documents.filter.type",
    }
    return MemoizedSelector(selector, dependencies)


def create_document_filter_summary_selector() -> MemoizedSelector[dict[str, Any]]:
    """Create a selector for document filter summary."""

    def selector(state: dict[str, Any]) -> dict[str, Any]:
        doc_state = state.get("documents", {})
        filter_config = doc_state.get("filter", {})

        filter_type = filter_config.get("type", "all")
        search_query = filter_config.get("search_query", "").strip()
        selected_tags = filter_config.get("selected_tags", set())
        date_range = filter_config.get("date_range")

        active_filters = []
        if filter_type != "all":
            active_filters.append(f"Type: {filter_type.upper()}")
        if search_query:
            active_filters.append(f"Search: '{search_query}'")
        if selected_tags:
            active_filters.append(f"Tags: {len(selected_tags)} selected")
        if date_range:
            active_filters.append("Date range")

        return {
            "active_count": len(active_filters),
            "active_filters": active_filters,
            "has_filters": len(active_filters) > 0,
            "filter_summary": (
                ", ".join(active_filters) if active_filters else "No filters active"
            ),
            "search_active": len(search_query) > 0,
            "type_filter_active": filter_type != "all",
        }

    dependencies = {
        "documents.filter.type",
        "documents.filter.search_query",
        "documents.filter.selected_tags",
        "documents.filter.date_range",
    }
    return MemoizedSelector(selector, dependencies)


# ============================================================================
# External Information Selectors
# ============================================================================


def create_feeds_summary_selector() -> MemoizedSelector[dict[str, Any]]:
    """Create a selector for feeds summary information."""

    def selector(state: dict[str, Any]) -> dict[str, Any]:
        external_state = state.get("external", {})

        feeds = external_state.get("feeds", [])
        cve_data = external_state.get("cve_data", [])
        mitre_data = external_state.get("mitre_data", [])
        feed_count = external_state.get("feed_count", 0)
        last_refresh = external_state.get("last_feed_refresh")
        refresh_status = external_state.get("feed_refresh_status", "idle")
        selected_time_range = external_state.get("selected_time_range", "24h")

        # Calculate time range for filtering
        now = datetime.now()
        time_ranges = {
            "1h": now - timedelta(hours=1),
            "6h": now - timedelta(hours=6),
            "24h": now - timedelta(hours=24),
            "7d": now - timedelta(days=7),
            "30d": now - timedelta(days=30),
        }

        cutoff_time = time_ranges.get(selected_time_range, time_ranges["24h"])

        # Filter feeds by time range (this would need actual datetime objects)
        recent_feeds = len([f for f in feeds if True])  # Placeholder logic

        return {
            "total_feeds": len(feeds),
            "recent_feeds": recent_feeds,
            "cve_count": len(cve_data),
            "mitre_count": len(mitre_data),
            "configured_sources": feed_count,
            "last_refresh": last_refresh,
            "refresh_status": refresh_status,
            "is_refreshing": refresh_status == "processing",
            "time_range": selected_time_range,
            "has_content": len(feeds) > 0 or len(cve_data) > 0 or len(mitre_data) > 0,
            "refresh_needed": (
                last_refresh is None
                or (
                    isinstance(last_refresh, str)
                    and datetime.fromisoformat(last_refresh) < now - timedelta(hours=1)
                )
                if last_refresh
                else True
            ),
        }

    dependencies = {
        "external.feeds",
        "external.cve_data",
        "external.mitre_data",
        "external.feed_count",
        "external.last_feed_refresh",
        "external.feed_refresh_status",
        "external.selected_time_range",
    }
    return MemoizedSelector(selector, dependencies)


def create_threat_intelligence_selector() -> MemoizedSelector[dict[str, Any]]:
    """Create a selector for threat intelligence summary."""

    def selector(state: dict[str, Any]) -> dict[str, Any]:
        external_state = state.get("external", {})

        cve_data = external_state.get("cve_data", [])
        mitre_data = external_state.get("mitre_data", [])

        # Categorize CVEs by severity
        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "unknown": 0,
        }
        for cve in cve_data:
            severity = cve.get("severity", "unknown").lower()
            if severity in severity_counts:
                severity_counts[severity] += 1
            else:
                severity_counts["unknown"] += 1

        # Categorize MITRE techniques by tactic
        tactic_counts = {}
        for technique in mitre_data:
            tactic = technique.get("tactic", "unknown")
            tactic_counts[tactic] = tactic_counts.get(tactic, 0) + 1

        return {
            "cve_total": len(cve_data),
            "mitre_total": len(mitre_data),
            "cve_severity": severity_counts,
            "mitre_tactics": tactic_counts,
            "critical_cves": severity_counts["critical"],
            "high_cves": severity_counts["high"],
            "has_critical_threats": severity_counts["critical"] > 0,
            "threat_score": (
                severity_counts["critical"] * 4
                + severity_counts["high"] * 3
                + severity_counts["medium"] * 2
                + severity_counts["low"] * 1
            ),
            "most_common_tactic": (
                max(tactic_counts.items(), key=lambda x: x[1])[0]
                if tactic_counts
                else None
            ),
        }

    dependencies = {"external.cve_data", "external.mitre_data"}
    return MemoizedSelector(selector, dependencies)


# ============================================================================
# System Status Selectors
# ============================================================================


def create_system_status_selector() -> MemoizedSelector[dict[str, Any]]:
    """Create a selector for overall system status."""

    def selector(state: dict[str, Any]) -> dict[str, Any]:
        chat_state = state.get("chat", {})
        doc_state = state.get("documents", {})
        external_state = state.get("external", {})
        settings_state = state.get("settings", {})
        ui_state = state.get("ui", {})

        # Calculate overall system health
        issues = []
        warnings = []

        # Check model configuration
        model_info = settings_state.get("model_info", {})
        llm_model = model_info.get("llm_model", "Unknown")
        embedding_model = model_info.get("embedding_model", "Unknown")

        if llm_model == "Unknown":
            issues.append("LLM model not configured")
        if embedding_model == "Unknown":
            warnings.append("Embedding model not configured")

        # Check document status
        doc_count = doc_state.get("counts", {}).get("total", 0)
        processing_count = len(doc_state.get("processing_queue", []))

        if chat_state.get("mode") == "RAG Mode" and doc_count == 0:
            warnings.append("RAG mode active but no documents loaded")

        # Check external feeds
        last_refresh = external_state.get("last_feed_refresh")
        if not last_refresh:
            warnings.append("Feeds have not been refreshed")

        # Calculate status level
        if issues:
            status_level = "error"
            status_text = f"{len(issues)} issues need attention"
        elif warnings:
            status_level = "warning"
            status_text = f"{len(warnings)} warnings"
        else:
            status_level = "healthy"
            status_text = "All systems operational"

        return {
            "status_level": status_level,
            "status_text": status_text,
            "issues": issues,
            "warnings": warnings,
            "is_healthy": status_level == "healthy",
            "needs_attention": len(issues) > 0,
            "model_status": {
                "llm_configured": llm_model != "Unknown",
                "embedding_configured": embedding_model != "Unknown",
                "llm_model": llm_model,
                "embedding_model": embedding_model,
            },
            "document_status": {
                "total_documents": doc_count,
                "processing_queue": processing_count,
                "has_documents": doc_count > 0,
            },
            "feed_status": {
                "last_refresh": last_refresh,
                "needs_refresh": not last_refresh,
            },
            "ui_status": {
                "current_tab": ui_state.get("current_tab", "chat"),
                "theme": ui_state.get("theme", "dark"),
            },
        }

    dependencies = {
        "chat.mode",
        "documents.counts.total",
        "documents.processing_queue",
        "external.last_feed_refresh",
        "settings.model_info",
        "ui.current_tab",
        "ui.theme",
    }
    return MemoizedSelector(selector, dependencies)


# ============================================================================
# UI State Selectors
# ============================================================================


def create_ui_layout_selector() -> MemoizedSelector[dict[str, Any]]:
    """Create a selector for UI layout information."""

    def selector(state: dict[str, Any]) -> dict[str, Any]:
        ui_state = state.get("ui", {})
        chat_state = state.get("chat", {})

        components = ui_state.get("components", {})
        current_tab = ui_state.get("current_tab", "chat")
        sidebar_collapsed = ui_state.get("sidebar_collapsed", False)
        theme = ui_state.get("theme", "dark")

        # Calculate visible components
        visible_components = [
            name for name, comp in components.items() if comp.get("is_visible", True)
        ]

        # Determine layout state
        is_chat_focused = current_tab == "chat" and chat_state.get(
            "is_processing", False
        )

        return {
            "current_tab": current_tab,
            "theme": theme,
            "sidebar_collapsed": sidebar_collapsed,
            "visible_components": visible_components,
            "component_count": len(visible_components),
            "is_chat_focused": is_chat_focused,
            "layout_mode": "compact" if sidebar_collapsed else "normal",
            "has_status_messages": len(ui_state.get("status_messages", [])) > 0,
            "has_notifications": len(ui_state.get("notifications", [])) > 0,
            "modal_active": ui_state.get("modal_state") is not None,
            "loading_states": ui_state.get("loading_states", {}),
            "error_states": ui_state.get("error_states", {}),
        }

    dependencies = {
        "ui.current_tab",
        "ui.theme",
        "ui.sidebar_collapsed",
        "ui.components",
        "ui.status_messages",
        "ui.notifications",
        "ui.modal_state",
        "ui.loading_states",
        "ui.error_states",
        "chat.is_processing",
    }
    return MemoizedSelector(selector, dependencies)


# ============================================================================
# Composite Selectors
# ============================================================================


def create_dashboard_summary_selector() -> MemoizedSelector[dict[str, Any]]:
    """Create a comprehensive selector for dashboard summary information."""

    def selector(state: dict[str, Any]) -> dict[str, Any]:
        # This would combine data from multiple other selectors
        # For now, provide a basic implementation

        app_state = state.get("", state)  # Handle root state
        session_id = app_state.get("session_id", "unknown")
        uptime = "unknown"  # Would calculate from startup_time

        # Get key metrics from different domains
        chat_mode = state.get("chat", {}).get("mode", "RAG Mode")
        doc_count = state.get("documents", {}).get("counts", {}).get("total", 0)
        feed_count = state.get("external", {}).get("feed_count", 0)

        return {
            "session_id": session_id,
            "uptime": uptime,
            "current_mode": chat_mode,
            "key_metrics": {
                "documents": doc_count,
                "feeds": feed_count,
                "chat_history": len(state.get("chat", {}).get("history", [])),
            },
            "quick_stats": f"{doc_count} docs, {feed_count} feeds, {chat_mode} mode",
        }

    dependencies = {
        "session_id",
        "chat.mode",
        "chat.history",
        "documents.counts.total",
        "external.feed_count",
    }
    return MemoizedSelector(selector, dependencies)


# ============================================================================
# Selector Registry
# ============================================================================

# Registry of all available selectors
SELECTOR_REGISTRY = {
    # Chat selectors
    "chat_status": create_chat_status_selector,
    "chat_settings": create_chat_settings_selector,
    # Document selectors
    "document_counts": create_document_counts_selector,
    "document_filter_summary": create_document_filter_summary_selector,
    # External information selectors
    "feeds_summary": create_feeds_summary_selector,
    "threat_intelligence": create_threat_intelligence_selector,
    # System selectors
    "system_status": create_system_status_selector,
    "ui_layout": create_ui_layout_selector,
    # Composite selectors
    "dashboard_summary": create_dashboard_summary_selector,
}


def register_all_selectors(state_store) -> None:
    """Register all selectors with a state store.

    Args:
        state_store: StateStore instance to register selectors with
    """
    for name, selector_factory in SELECTOR_REGISTRY.items():
        try:
            selector = selector_factory()
            state_store.register_selector(name, selector)
            logger.debug(f"Registered selector: {name}")
        except Exception as e:
            logger.error(f"Failed to register selector {name}: {e}")

    logger.info(f"Registered {len(SELECTOR_REGISTRY)} selectors")


def get_selector_dependencies() -> dict[str, set[str]]:
    """Get the dependencies for all selectors.

    Returns:
        Dictionary mapping selector names to their dependencies
    """
    dependencies = {}
    for name, selector_factory in SELECTOR_REGISTRY.items():
        try:
            selector = selector_factory()
            dependencies[name] = selector.get_dependencies()
        except Exception as e:
            logger.error(f"Failed to get dependencies for selector {name}: {e}")
            dependencies[name] = set()

    return dependencies
