"""Test to verify time filter buttons correctly update all components.

This test validates the fix for the regulatory information feed time filter issue
where clicking filter buttons (24h, 7d, 30d, 90d) should update:
1. time_range_display - Visual display of current time range
2. current_time_filter - Hidden state tracking the filter
3. feed_display - Filtered feed content
"""

from datetime import UTC, datetime, timedelta

import pytest

from internal_assistant.server.feeds.feeds_service import RSSFeedService
from internal_assistant.ui.components.feeds.feeds_events import FeedsEventHandler


@pytest.fixture
def feeds_service():
    """Create a feeds service instance for testing."""
    return RSSFeedService(max_items=100)


@pytest.fixture
def handler(feeds_service):
    """Create a feeds event handler instance."""
    return FeedsEventHandler(feeds_service)


def test_filter_feeds_returns_tuple(handler):
    """Verify filter_feeds returns a tuple of 3 values."""
    result = handler.filter_feeds("24h", "")

    assert isinstance(result, tuple), "filter_feeds should return a tuple"
    assert len(result) == 3, "filter_feeds should return exactly 3 values"

    time_range_html, filter_state, feeds_html = result
    assert isinstance(time_range_html, str), "First value should be HTML string"
    assert isinstance(filter_state, str), "Second value should be filter state string"
    assert isinstance(feeds_html, str), "Third value should be feeds HTML string"


def test_filter_feeds_time_range_display(handler):
    """Verify time range display HTML is correctly generated."""
    test_cases = [
        ("24h", "24 hours"),
        ("7d", "7 days"),
        ("30d", "30 days"),
        ("90d", "90 days"),
    ]

    for time_filter, expected_text in test_cases:
        time_range_html, filter_state, _ = handler.filter_feeds(time_filter, "")

        assert "⏰ TIME RANGE:" in time_range_html
        assert expected_text in time_range_html
        assert filter_state == expected_text


def test_filter_feeds_with_mock_data(handler, feeds_service):
    """Test filtering with mock feed data."""
    # Create mock feed data with various timestamps
    now = datetime.now(UTC)

    # Mock feeds with different ages
    mock_feeds = [
        {
            "title": "Recent Feed",
            "link": "http://example.com/1",
            "summary": "Recent news",
            "published": now.isoformat(),
            "source": "Test Source",
            "priority": 1,
            "color": "#FF0000",
        },
        {
            "title": "Old Feed",
            "link": "http://example.com/2",
            "summary": "Old news",
            "published": (now - timedelta(days=60)).isoformat(),
            "source": "Test Source",
            "priority": 1,
            "color": "#FF0000",
        },
        {
            "title": "Week Old Feed",
            "link": "http://example.com/3",
            "summary": "Week old news",
            "published": (now - timedelta(days=5)).isoformat(),
            "source": "Test Source",
            "priority": 1,
            "color": "#FF0000",
        },
    ]

    # Inject mock data into feeds service
    from internal_assistant.server.feeds.feeds_service import FeedItem

    feeds_service.feeds_cache = [
        FeedItem(
            title=f["title"],
            link=f["link"],
            summary=f["summary"],
            published=datetime.fromisoformat(f["published"]),
            source=f["source"],
            guid=f["link"],
        )
        for f in mock_feeds
    ]

    # Test 7-day filter
    time_range_html, filter_state, feeds_html = handler.filter_feeds("7d", "")

    # Should include recent and week-old feeds, but not 60-day old feed
    assert "Recent Feed" in feeds_html
    assert "Week Old Feed" in feeds_html
    assert "Old Feed" not in feeds_html

    assert filter_state == "7 days"
    assert "7 days" in time_range_html


def test_iso_date_parsing(handler):
    """Verify ISO date format parsing works correctly."""
    now = datetime.now(UTC)

    # Test feed with ISO format date
    test_feed = {
        "published": now.isoformat(),
        "title": "Test",
        "link": "http://test.com",
        "summary": "Test summary",
        "source": "Test",
        "priority": 1,
        "color": "#000000",
    }

    cutoff_date = now - timedelta(hours=1)

    # Should be within timeframe (published now, cutoff 1 hour ago)
    result = handler._is_feed_within_timeframe(test_feed, cutoff_date)
    assert result is True


def test_filter_with_no_feeds(handler, feeds_service):
    """Test filtering when no feeds are available."""
    feeds_service.feeds_cache = []

    time_range_html, filter_state, feeds_html = handler.filter_feeds("24h", "")

    assert "24 hours" in time_range_html
    assert filter_state == "24 hours"
    assert "No feeds available" in feeds_html


def test_all_time_filters(handler):
    """Verify all time filter values produce correct outputs."""
    filters = ["24h", "7d", "30d", "90d"]

    for time_filter in filters:
        time_range_html, filter_state, feeds_html = handler.filter_feeds(
            time_filter, ""
        )

        # All should produce valid HTML
        assert len(time_range_html) > 0
        assert len(filter_state) > 0
        assert len(feeds_html) > 0

        # Time range HTML should be valid
        assert time_range_html.startswith("<div")
        assert time_range_html.endswith("</div>")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
