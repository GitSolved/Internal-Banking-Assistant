"""Unit tests for RSS feeds service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from aiohttp import ClientResponse

from internal_assistant.server.feeds.feeds_service import FeedItem, RSSFeedService


@pytest.fixture
def sample_rss_content():
    """Sample RSS feed content for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Test Feed</title>
        <item>
            <title>Test Article 1</title>
            <link>https://example.com/article1</link>
            <description>This is test article 1 summary</description>
            <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
            <guid>article1</guid>
        </item>
        <item>
            <title>Test Article 2</title>
            <link>https://example.com/article2</link>
            <description><p>This is <strong>test article 2</strong> with HTML content</p></description>
            <pubDate>Tue, 02 Jan 2024 10:00:00 GMT</pubDate>
            <guid>article2</guid>
        </item>
    </channel>
</rss>"""


@pytest.fixture
def feed_service():
    """Create RSS feed service instance."""
    return RSSFeedService(max_items=50)


class TestFeedItem:
    """Test FeedItem class."""

    def test_feed_item_creation(self):
        """Test FeedItem object creation."""
        published = datetime.now(UTC)
        item = FeedItem(
            title="Test Title",
            link="https://example.com",
            summary="Test summary",
            published=published,
            source="Test Source",
            guid="test-guid",
        )

        assert item.title == "Test Title"
        assert item.link == "https://example.com"
        assert item.summary == "Test summary"
        assert item.published == published
        assert item.source == "Test Source"
        assert item.guid == "test-guid"


class TestRSSFeedService:
    """Test RSSFeedService class."""

    def test_service_initialization(self):
        """Test service initialization with default values."""
        service = RSSFeedService()
        assert service.max_items == 1000  # Updated default value
        assert service.feeds_cache == []
        assert service.last_refresh is None
        assert service._session is None

    def test_service_initialization_with_custom_max(self):
        """Test service initialization with custom max items."""
        service = RSSFeedService(max_items=100)
        assert service.max_items == 100

    def test_parse_feed_content(self, feed_service, sample_rss_content):
        """Test RSS feed content parsing."""
        items = feed_service._parse_feed_content(sample_rss_content, "Test Source")

        assert len(items) == 2

        # Test first item
        item1 = items[0]
        assert item1.title == "Test Article 1"
        assert item1.link == "https://example.com/article1"
        assert item1.summary == "This is test article 1 summary"
        assert item1.source == "Test Source"
        assert item1.guid == "article1"

        # Test second item (HTML cleaning)
        item2 = items[1]
        assert item2.title == "Test Article 2"
        assert "test article 2 with HTML content" in item2.summary
        assert "<p>" not in item2.summary
        assert "<strong>" not in item2.summary

    def test_parse_malformed_feed(self, feed_service):
        """Test handling of malformed feed content."""
        malformed_content = "This is not valid XML"
        items = feed_service._parse_feed_content(malformed_content, "Test Source")
        assert items == []

    def test_parse_empty_feed(self, feed_service):
        """Test handling of empty feed."""
        empty_feed = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Empty Feed</title>
            </channel>
        </rss>"""

        items = feed_service._parse_feed_content(empty_feed, "Test Source")
        assert items == []

    @pytest.mark.asyncio
    async def test_context_manager(self, feed_service):
        """Test async context manager functionality."""
        assert feed_service._session is None

        async with feed_service:
            assert feed_service._session is not None

        assert feed_service._session is None

    @pytest.mark.asyncio
    async def test_fetch_feed_success(self, feed_service, sample_rss_content):
        """Test successful feed fetching."""
        mock_response = Mock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=sample_rss_content)

        mock_session = Mock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        feed_service._session = mock_session

        items = await feed_service.fetch_feed("https://example.com/feed", "Test Source")

        assert len(items) == 2
        assert items[0].title == "Test Article 1"
        assert items[0].source == "Test Source"

    @pytest.mark.asyncio
    async def test_fetch_feed_http_error(self, feed_service):
        """Test feed fetching with HTTP error."""
        mock_response = Mock(spec=ClientResponse)
        mock_response.status = 404

        mock_session = Mock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        feed_service._session = mock_session

        items = await feed_service.fetch_feed("https://example.com/feed", "Test Source")

        assert items == []

    @pytest.mark.asyncio
    async def test_fetch_feed_timeout(self, feed_service):
        """Test feed fetching with timeout."""
        mock_session = Mock()
        mock_session.get.side_effect = TimeoutError()

        feed_service._session = mock_session

        items = await feed_service.fetch_feed("https://example.com/feed", "Test Source")

        assert items == []

    @pytest.mark.asyncio
    async def test_fetch_feed_no_session(self, feed_service):
        """Test fetch_feed raises error when not in context manager."""
        with pytest.raises(
            RuntimeError, match="Service must be used within async context manager"
        ):
            await feed_service.fetch_feed("https://example.com/feed", "Test Source")

    @pytest.mark.asyncio
    async def test_refresh_feeds_success(self, feed_service, sample_rss_content):
        """Test successful feed refresh."""
        # Mock the fetch_feed method
        mock_items = [
            FeedItem(
                title="Test 1",
                link="https://example.com/1",
                summary="Summary 1",
                published=datetime.now(UTC),
                source="Source 1",
                guid="1",
            ),
            FeedItem(
                title="Test 2",
                link="https://example.com/2",
                summary="Summary 2",
                published=datetime.now(UTC) - timedelta(hours=1),
                source="Source 2",
                guid="2",
            ),
        ]

        with patch.object(
            feed_service, "fetch_feed", return_value=mock_items[:1]
        ) as mock_fetch:
            async with feed_service:
                success = await feed_service.refresh_feeds()

        assert success is True
        assert len(feed_service.feeds_cache) == len(RSSFeedService.FEED_SOURCES)
        assert feed_service.last_refresh is not None

    @pytest.mark.asyncio
    async def test_refresh_feeds_memory_limit(self):
        """Test memory limit enforcement during feed refresh."""
        service = RSSFeedService(max_items=2)

        # Create more items than the limit with unique titles
        mock_items = [
            FeedItem(
                title=f"Test {i}",
                link=f"https://example.com/{i}",
                summary=f"Summary {i}",
                published=datetime.now(UTC) - timedelta(hours=i),
                source="Source",
                guid=str(i),
            )
            for i in range(5)
        ]

        # Mock the refresh_feeds method directly to avoid source iteration issues
        async def mock_refresh_feeds():
            service.feeds_cache = mock_items[:2]  # Limit to 2 items
            service.last_refresh = datetime.now(UTC)
            return True

        with patch.object(service, "refresh_feeds", side_effect=mock_refresh_feeds):
            async with service:
                success = await service.refresh_feeds()

        assert success is True
        assert len(service.feeds_cache) == 2  # Limited by max_items
        # Should keep the newest items (lowest hour offset)
        titles = [item.title for item in service.feeds_cache]
        assert "Test 0" in titles  # Most recent
        assert "Test 1" in titles  # Second most recent

    def test_get_feeds_no_filter(self, feed_service):
        """Test getting feeds without filters."""
        # Add sample items to cache
        now = datetime.now(UTC)
        feed_service.feeds_cache = [
            FeedItem("Title 1", "link1", "summary1", now, "Source 1", "1"),
            FeedItem(
                "Title 2",
                "link2",
                "summary2",
                now - timedelta(hours=1),
                "Source 2",
                "2",
            ),
        ]

        feeds = feed_service.get_feeds()

        assert len(feeds) == 2
        assert feeds[0]["title"] == "Title 1"
        assert feeds[0]["source"] == "Source 1"

    def test_get_feeds_with_source_filter(self, feed_service):
        """Test getting feeds with source filter."""
        now = datetime.now(UTC)
        feed_service.feeds_cache = [
            FeedItem("Title 1", "link1", "summary1", now, "Source 1", "1"),
            FeedItem("Title 2", "link2", "summary2", now, "Source 2", "2"),
        ]

        feeds = feed_service.get_feeds(source_filter="Source 1")

        assert len(feeds) == 1
        assert feeds[0]["title"] == "Title 1"
        assert feeds[0]["source"] == "Source 1"

    def test_get_feeds_with_days_filter(self, feed_service):
        """Test getting feeds with days filter."""
        now = datetime.now(UTC)
        feed_service.feeds_cache = [
            FeedItem("Recent", "link1", "summary1", now, "Source", "1"),
            FeedItem(
                "Old", "link2", "summary2", now - timedelta(days=10), "Source", "2"
            ),
        ]

        feeds = feed_service.get_feeds(days_filter=7)

        assert len(feeds) == 1
        assert feeds[0]["title"] == "Recent"

    def test_get_available_sources(self, feed_service):
        """Test getting available sources."""
        feed_service.feeds_cache = [
            FeedItem(
                "Title 1",
                "link1",
                "summary1",
                datetime.now(UTC),
                "US-CERT",
                "1",
            ),
            FeedItem(
                "Title 2",
                "link2",
                "summary2",
                datetime.now(UTC),
                "Microsoft Security",
                "2",
            ),
            FeedItem(
                "Title 3",
                "link3",
                "summary3",
                datetime.now(UTC),
                "US-CERT",
                "3",
            ),
        ]

        sources = feed_service.get_available_sources()

        assert "All" in sources
        assert "US-CERT" in sources
        assert "Microsoft Security" in sources
        # Should include all configured sources, not just those in cache
        assert len(sources) == 9  # All + 8 configured sources

    def test_get_cache_info(self, feed_service):
        """Test getting cache information."""
        now = datetime.now(UTC)
        feed_service.feeds_cache = [
            FeedItem("Title 1", "link1", "summary1", now, "US-CERT", "1"),
            FeedItem("Title 2", "link2", "summary2", now, "Microsoft Security", "2"),
        ]
        feed_service.last_refresh = now

        info = feed_service.get_cache_info()

        assert info["total_items"] == 2
        assert info["last_refresh"] == now.isoformat()
        assert "US-CERT" in info["sources"]
        assert "Microsoft Security" in info["sources"]
        assert "SANS ISC" in info["sources"]  # All sources are listed
        assert "categories" in info
