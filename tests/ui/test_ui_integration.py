"""Basic UI integration tests for RSS feed functionality."""

from unittest.mock import Mock

from internal_assistant.server.feeds.feeds_service import RSSFeedService
from internal_assistant.ui.ui import InternalAssistantUI


class TestUIIntegration:
    """Test UI integration without breaking existing functionality."""

    def test_ui_class_initialization(self):
        """Test that UI class can be initialized with feeds service."""
        # Mock all dependencies
        mock_ingest = Mock()
        mock_chat = Mock()
        mock_chunks = Mock()
        mock_summarize = Mock()
        mock_feeds = Mock(spec=RSSFeedService)

        # Initialize UI class
        ui = InternalAssistantUI(
            ingest_service=mock_ingest,
            chat_service=mock_chat,
            chunks_service=mock_chunks,
            summarizeService=mock_summarize,
            feeds_service=mock_feeds,
        )

        # Verify feeds service is stored
        assert hasattr(ui, "_feeds_service")
        assert ui._feeds_service == mock_feeds

        print("[PASS] UI class initialization with feeds service")

    def test_format_feeds_display_empty(self):
        """Test feeds display formatting with empty data."""
        # Mock dependencies
        mock_ingest = Mock()
        mock_chat = Mock()
        mock_chunks = Mock()
        mock_summarize = Mock()
        mock_feeds = Mock(spec=RSSFeedService)

        # Mock feeds service to return empty list
        mock_feeds.get_feeds.return_value = []

        ui = InternalAssistantUI(
            ingest_service=mock_ingest,
            chat_service=mock_chat,
            chunks_service=mock_chunks,
            summarizeService=mock_summarize,
            feeds_service=mock_feeds,
        )

        # Test empty feeds display
        result = ui._format_feeds_display()

        assert "No external information available" in result
        assert "REFRESH button" in result
        assert "feed-content" in result

        print("[PASS] Empty feeds display formatting")

    def test_format_feeds_display_with_data(self):
        """Test feeds display formatting with sample data."""
        # Mock dependencies
        mock_ingest = Mock()
        mock_chat = Mock()
        mock_chunks = Mock()
        mock_summarize = Mock()
        mock_feeds = Mock(spec=RSSFeedService)

        # Mock sample feed data
        sample_feeds = [
            {
                "title": "Test FINRA Article",
                "link": "https://finra.org/test",
                "summary": "This is a test summary for FINRA article",
                "published": "2024-01-01 12:00 UTC",
                "source": "FINRA",
                "guid": "test-1",
            },
            {
                "title": "Federal Reserve Update",
                "link": "https://fed.gov/test",
                "summary": "Federal Reserve policy update for testing",
                "published": "2024-01-02 14:00 UTC",
                "source": "Federal Reserve",
                "guid": "test-2",
            },
        ]

        mock_feeds.get_feeds.return_value = sample_feeds

        ui = InternalAssistantUI(
            ingest_service=mock_ingest,
            chat_service=mock_chat,
            chunks_service=mock_chunks,
            summarizeService=mock_summarize,
            feeds_service=mock_feeds,
        )

        # Test feeds display with data
        result = ui._format_feeds_display()

        assert "Test FINRA Article" in result
        assert "Federal Reserve Update" in result
        assert "📋 FINRA" in result
        assert "🏦 Federal Reserve" in result
        assert "confirmOpenExternal" in result  # JavaScript function
        assert "feed-item" in result

        print("[PASS] Feeds display with data formatting")

    def test_format_feeds_display_filtering(self):
        """Test feeds display with filtering."""
        # Mock dependencies
        mock_ingest = Mock()
        mock_chat = Mock()
        mock_chunks = Mock()
        mock_summarize = Mock()
        mock_feeds = Mock(spec=RSSFeedService)

        # Mock filtered feed data
        filtered_feeds = [
            {
                "title": "FINRA Only Article",
                "link": "https://finra.org/filtered",
                "summary": "Filtered FINRA content",
                "published": "2024-01-01 12:00 UTC",
                "source": "FINRA",
                "guid": "filtered-1",
            }
        ]

        mock_feeds.get_feeds.return_value = filtered_feeds

        ui = InternalAssistantUI(
            ingest_service=mock_ingest,
            chat_service=mock_chat,
            chunks_service=mock_chunks,
            summarizeService=mock_summarize,
            feeds_service=mock_feeds,
        )

        # Test filtered display
        result = ui._format_feeds_display("FINRA", 7)

        assert "FINRA Only Article" in result
        assert "Filtered FINRA content" in result

        # Verify mock was called with correct parameters
        mock_feeds.get_feeds.assert_called_with("FINRA", 7)

        print("[PASS] Feeds display filtering")

    def test_format_feeds_display_error_handling(self):
        """Test error handling in feeds display."""
        # Mock dependencies
        mock_ingest = Mock()
        mock_chat = Mock()
        mock_chunks = Mock()
        mock_summarize = Mock()
        mock_feeds = Mock(spec=RSSFeedService)

        # Mock feeds service to raise exception
        mock_feeds.get_feeds.side_effect = Exception("Network error")

        ui = InternalAssistantUI(
            ingest_service=mock_ingest,
            chat_service=mock_chat,
            chunks_service=mock_chunks,
            summarizeService=mock_summarize,
            feeds_service=mock_feeds,
        )

        # Test error handling
        result = ui._format_feeds_display()

        assert "Error loading external information" in result
        assert "Network error" in result
        assert "feed-content error" in result

        print("[PASS] Feeds display error handling")


if __name__ == "__main__":
    test = TestUIIntegration()

    print("Running UI integration tests...")

    test.test_ui_class_initialization()
    test.test_format_feeds_display_empty()
    test.test_format_feeds_display_with_data()
    test.test_format_feeds_display_filtering()
    test.test_format_feeds_display_error_handling()

    print("\nAll Phase 3 UI integration tests passed! [SUCCESS]")
    print("✅ UI class accepts feeds service dependency")
    print("✅ Feeds display handles empty state correctly")
    print("✅ Feeds display renders sample data properly")
    print("✅ Filtering functionality works as expected")
    print("✅ Error states are handled gracefully")
