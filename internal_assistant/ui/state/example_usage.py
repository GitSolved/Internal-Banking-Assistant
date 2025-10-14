"""
State Management Usage Examples

This module demonstrates how to use the new centralized state management system
to replace scattered state variables in the Internal Assistant UI.

This serves as documentation and reference for integrating the state system.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

# Import the state management components
from internal_assistant.ui.state import (
    ApplicationState,
    StateIntegrationManager,
    create_default_application_state,
    create_application_state_from_legacy,
    ProcessingStatus,
    FilterType,
    CitationStyle,
)

logger = logging.getLogger(__name__)


def example_basic_usage():
    """Example of basic state management usage."""

    # 1. Create default application state
    app_state = create_default_application_state()
    print("Default state created:", app_state.session_id)

    # 2. Access state values
    current_mode = app_state.chat.mode
    doc_count = app_state.documents.counts.total
    print(f"Current mode: {current_mode}, Documents: {doc_count}")

    # 3. Modify state (creates new instance due to Pydantic validation)
    app_state.chat.mode = "General LLM"
    app_state.settings.chat.temperature = 0.7
    app_state.documents.filter.type = FilterType.PDF

    # 4. Get state summary
    summary = app_state.get_summary()
    print("State summary:", summary["chat"]["mode"])


def example_migration_from_legacy():
    """Example of migrating from legacy scattered state."""

    # Simulate legacy state variables
    legacy_mode = "RAG Mode"
    legacy_history = [["Hello", "Hi there!"], ["How are you?", "I'm doing well!"]]
    legacy_system_prompt = "You are a helpful AI assistant."
    legacy_temperature = 0.5
    legacy_similarity = 0.7

    # Create state from legacy values
    migrated_state = create_application_state_from_legacy(
        legacy_mode=legacy_mode,
        legacy_history=legacy_history,
        legacy_system_prompt=legacy_system_prompt,
        legacy_temperature=legacy_temperature,
        legacy_similarity=legacy_similarity,
    )

    print("Migrated state mode:", migrated_state.chat.mode)
    print("Migrated history length:", len(migrated_state.chat.history))
    print("Migrated temperature:", migrated_state.settings.chat.temperature)


def example_integration_manager():
    """Example of using the StateIntegrationManager."""

    # 1. Create integration manager
    manager = StateIntegrationManager()

    # 2. Register UI update callback
    def ui_update_callback(path: str, old_value: Any, new_value: Any):
        print(f"UI Update: {path} changed from {old_value} to {new_value}")

    ui_observer = manager.register_ui_observer(ui_update_callback)

    # 3. Update state and see UI callback triggered
    manager.set_state_value("chat.mode", "General LLM", source="user_action")
    manager.set_state_value("documents.filter.type", "pdf", source="filter_change")

    # 4. Use selectors to get computed values
    chat_status = manager.select("chat_status")
    print("Chat status:", chat_status)

    document_counts = manager.select("document_counts")
    print("Document counts:", document_counts)

    # 5. Get state summary
    summary = manager.get_state_summary()
    print("Session ID:", summary["session_id"])


def example_gradio_integration():
    """Example of integrating with Gradio components."""

    manager = StateIntegrationManager()

    # Simulate Gradio components (normally these would be actual Gradio objects)
    class MockGradioComponent:
        def __init__(self, initial_value):
            self.value = initial_value

        def update(self, value):
            self.value = value
            print(f"Gradio component updated to: {value}")

    # Register mock components
    mode_selector = MockGradioComponent("RAG Mode")
    temperature_slider = MockGradioComponent(0.1)

    manager.register_component("mode_selector", mode_selector, "chat.mode")
    manager.register_component(
        "temperature_slider", temperature_slider, "settings.chat.temperature"
    )

    # Bind components to state for automatic updates
    manager.bind_component_to_state("mode_selector", "chat.mode")
    manager.bind_component_to_state("temperature_slider", "settings.chat.temperature")

    # Now when state changes, components get updated automatically
    manager.set_state_value("chat.mode", "General LLM", source="user_selection")
    manager.set_state_value("settings.chat.temperature", 0.8, source="user_adjustment")

    # And when components change, state gets updated
    manager.update_state_from_component("mode_selector", "RAG Mode")

    print("Final mode:", manager.get_state_value("chat.mode"))


def example_document_state_management():
    """Example of managing document-related state."""

    manager = StateIntegrationManager()

    # Update document counts (simulating document ingestion)
    document_updates = {
        "documents.counts.total": 15,
        "documents.counts.pdf_count": 8,
        "documents.counts.docx_count": 4,
        "documents.counts.txt_count": 3,
        "documents.counts.security_compliance": 6,
        "documents.counts.policy_governance": 4,
        "documents.counts.threat_intelligence": 5,
    }

    manager.update_state_values(document_updates, source="document_ingestion")

    # Set document filter
    manager.set_state_value("documents.filter.type", "pdf", source="user_filter")
    manager.set_state_value(
        "documents.filter.search_query", "security policy", source="user_search"
    )

    # Get computed document information
    doc_counts = manager.select("document_counts")
    filter_summary = manager.select("document_filter_summary")

    print("Total documents:", doc_counts["total"])
    print("Filtered documents:", doc_counts["filtered"])
    print("Active filters:", filter_summary["active_filters"])
    print("Filter summary:", filter_summary["filter_summary"])


def example_external_feeds_state():
    """Example of managing external feeds and threat intelligence state."""

    manager = StateIntegrationManager()

    # Simulate feed data updates
    feed_updates = {
        "external.feed_count": 5,
        "external.selected_time_range": "24h",
        "external.feed_refresh_status": ProcessingStatus.PROCESSING.value,
        "external.last_feed_refresh": datetime.now().isoformat(),
    }

    manager.update_state_values(feed_updates, source="feed_service")

    # Simulate CVE data
    cve_data = [
        {
            "cve_id": "CVE-2024-1234",
            "severity": "critical",
            "description": "Critical vulnerability in web server",
            "published": datetime.now().isoformat(),
        },
        {
            "cve_id": "CVE-2024-5678",
            "severity": "high",
            "description": "High severity authentication bypass",
            "published": datetime.now().isoformat(),
        },
    ]

    manager.set_state_value("external.cve_data", cve_data, source="cve_feed")

    # Get threat intelligence summary
    threat_summary = manager.select("threat_intelligence")
    feeds_summary = manager.select("feeds_summary")

    print("Total CVEs:", threat_summary["cve_total"])
    print("Critical CVEs:", threat_summary["critical_cves"])
    print("Threat score:", threat_summary["threat_score"])
    print("Feed refresh needed:", feeds_summary["refresh_needed"])


def example_system_monitoring():
    """Example of system status monitoring."""

    manager = StateIntegrationManager()

    # Set up system information
    system_updates = {
        "settings.model_info.llm_model": "Foundation-Sec-8B",
        "settings.model_info.embedding_model": "Nomic-Embed",
        "chat.mode": "RAG Mode",
        "documents.counts.total": 25,
        "external.feed_count": 8,
    }

    manager.update_state_values(system_updates, source="system_init")

    # Get comprehensive system status
    system_status = manager.select("system_status")
    dashboard_summary = manager.select("dashboard_summary")

    print("System status level:", system_status["status_level"])
    print("System status text:", system_status["status_text"])
    print("System is healthy:", system_status["is_healthy"])
    print("Model status:", system_status["model_status"])
    print("Dashboard summary:", dashboard_summary["quick_stats"])

    # Check for issues
    if system_status["issues"]:
        print("Issues that need attention:")
        for issue in system_status["issues"]:
            print(f"  - {issue}")

    if system_status["warnings"]:
        print("Warnings:")
        for warning in system_status["warnings"]:
            print(f"  - {warning}")


def example_state_persistence():
    """Example of persisting and loading state."""

    manager = StateIntegrationManager()

    # Make some state changes
    manager.set_state_value("chat.mode", "General LLM", source="user")
    manager.set_state_value(
        "settings.system_prompt",
        "You are an expert cybersecurity analyst.",
        source="user",
    )
    manager.set_state_value("documents.counts.total", 42, source="ingestion")

    # Export state for persistence
    state_export = manager.export_state_for_persistence()
    print("Exported state at:", state_export["export_timestamp"])
    print("Component bindings:", list(state_export["component_bindings"].keys()))

    # In a real application, you would save this to disk and load it later
    # The StateStore also has built-in persistence capabilities

    # Simulate loading state (in real usage, this would be from saved data)
    print("State would be persisted and could be restored on next startup")


def run_all_examples():
    """Run all the examples to demonstrate the state system."""

    print("=== Basic Usage Example ===")
    example_basic_usage()

    print("\n=== Legacy Migration Example ===")
    example_migration_from_legacy()

    print("\n=== Integration Manager Example ===")
    example_integration_manager()

    print("\n=== Gradio Integration Example ===")
    example_gradio_integration()

    print("\n=== Document State Management Example ===")
    example_document_state_management()

    print("\n=== External Feeds State Example ===")
    example_external_feeds_state()

    print("\n=== System Monitoring Example ===")
    example_system_monitoring()

    print("\n=== State Persistence Example ===")
    example_state_persistence()

    print("\n=== All examples completed successfully! ===")


if __name__ == "__main__":
    # Run examples when script is executed directly
    run_all_examples()
