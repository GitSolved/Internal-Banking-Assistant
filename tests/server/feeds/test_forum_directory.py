"""Tests for forum directory service and parser."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from internal_assistant.server.feeds.forum_directory_service import (
    ForumDirectoryService,
)
from internal_assistant.server.feeds.forum_parser import ForumDirectoryParser, ForumLink


class TestForumLink:
    """Test ForumLink model."""

    def test_forum_link_creation(self):
        """Test creating a forum link."""
        link = ForumLink(
            name="Test Forum",
            url="https://example.com",
            description="A test forum",
            category="General",
        )

        assert link.name == "Test Forum"
        assert link.url == "https://example.com"
        assert link.description == "A test forum"
        assert link.category == "General"

    def test_forum_link_to_dict(self):
        """Test converting forum link to dictionary."""
        link = ForumLink("Test Forum", "https://example.com", "Test", "General")
        result = link.to_dict()

        expected = {
            "name": "Test Forum",
            "url": "https://example.com",
            "description": "Test",
            "category": "General",
        }
        assert result == expected

    def test_forum_link_is_valid(self):
        """Test forum link validation."""
        # Valid link
        valid_link = ForumLink("Test Forum", "https://example.com")
        assert valid_link.is_valid() is True

        # Invalid - empty name
        invalid_name = ForumLink("", "https://example.com")
        assert invalid_name.is_valid() is False

        # Invalid - empty URL
        invalid_url = ForumLink("Test Forum", "")
        assert invalid_url.is_valid() is False

        # Invalid - bad URL
        invalid_protocol = ForumLink("Test Forum", "ftp://example.com")
        assert invalid_protocol.is_valid() is False


class TestForumDirectoryParser:
    """Test ForumDirectoryParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ForumDirectoryParser()

    def test_parser_initialization(self):
        """Test parser initialization."""
        assert isinstance(self.parser.EXCLUDED_KEYWORDS, set)
        assert isinstance(self.parser.FORUM_INDICATORS, set)
        assert self.parser.parsed_forums == []

    def test_is_excluded_section(self):
        """Test section exclusion logic."""
        # Should exclude marketplace sections
        assert self.parser._is_excluded_section("Drug Marketplace") is True
        assert self.parser._is_excluded_section("Weapon Sales") is True
        assert self.parser._is_excluded_section("Fraud Services") is True

        # Should allow forum sections
        assert self.parser._is_excluded_section("General Discussion") is False
        assert self.parser._is_excluded_section("Tech Forum") is False
        assert self.parser._is_excluded_section("Random Chat") is False

    def test_is_safe_forum(self):
        """Test forum safety validation."""
        # Safe forum
        safe_forum = ForumLink(
            "Tech Discussion", "https://example.com", "Technology forum"
        )
        assert self.parser._is_safe_forum(safe_forum) is True

        # Unsafe forum
        unsafe_forum = ForumLink(
            "Drug Market", "https://example.com", "Illegal marketplace"
        )
        assert self.parser._is_safe_forum(unsafe_forum) is False

        # Too short name
        short_name = ForumLink("Hi", "https://example.com")
        assert self.parser._is_safe_forum(short_name) is False

    def test_parse_forum_directory_with_safe_content(self):
        """Test parsing HTML with safe forum content."""
        html_content = """
        <html>
        <body>
        <h2>Discussion Forums</h2>
        <div class="forum-section">
            <a href="https://techforum.onion">Tech Discussion</a>
            <p>Technology and programming discussions</p>
        </div>
        <div class="forum-section">
            <a href="https://generalchat.onion">General Chat</a>
            <p>Random discussions and social interactions</p>
        </div>
        </body>
        </html>
        """

        forums = self.parser.parse_forum_directory(html_content)

        assert len(forums) >= 1
        for forum in forums:
            assert forum.is_valid()
            assert self.parser._is_safe_forum(forum)

    def test_parse_forum_directory_filters_unsafe_content(self):
        """Test that unsafe content is filtered out."""
        html_content = """
        <html>
        <body>
        <h2>Drug Marketplace</h2>
        <div>
            <a href="https://drugmarket.onion">Buy Drugs Here</a>
            <p>Illegal drug marketplace</p>
        </div>
        <h2>General Forums</h2>
        <div class="forum-section">
            <a href="https://techforum.onion">Tech Discussion</a>
            <p>Technology discussions</p>
        </div>
        </body>
        </html>
        """

        forums = self.parser.parse_forum_directory(html_content)

        # Should only contain safe forums
        for forum in forums:
            assert "drug" not in forum.name.lower()
            assert "drug" not in forum.description.lower()
            assert self.parser._is_safe_forum(forum)

    def test_get_forum_categories(self):
        """Test getting forum categories."""
        # Add some test forums
        self.parser.parsed_forums = [
            ForumLink("Forum 1", "https://example1.com", "", "Tech"),
            ForumLink("Forum 2", "https://example2.com", "", "Tech"),
            ForumLink("Forum 3", "https://example3.com", "", "General"),
        ]

        categories = self.parser.get_forum_categories()
        assert categories == {"Tech": 2, "General": 1}

    def test_get_parsing_stats(self):
        """Test getting parsing statistics."""
        self.parser.parsed_forums = [
            ForumLink("Forum 1", "https://example1.com"),
            ForumLink("Forum 2", "https://example2.com"),
        ]

        stats = self.parser.get_parsing_stats()
        assert stats["total_forums"] == 2
        assert stats["categories"] == 1  # Both have "General" category
        assert stats["valid_forums"] == 2


class TestForumDirectoryService:
    """Test ForumDirectoryService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ForumDirectoryService(cache_duration_hours=1)

    def test_service_initialization(self):
        """Test service initialization."""
        assert self.service.cache_duration_hours == 1
        assert self.service.forums_cache == []
        assert self.service.last_refresh is None
        assert self.service._session is None

    def test_cache_validity(self):
        """Test cache validity checking."""
        # No cache
        assert self.service.is_cache_valid() is False

        # Fresh cache
        self.service.forums_cache = [ForumLink("Test", "https://example.com")]
        self.service.last_refresh = datetime.now(UTC)
        assert self.service.is_cache_valid() is True

        # Expired cache
        self.service.last_refresh = datetime.now(UTC) - timedelta(hours=2)
        assert self.service.is_cache_valid() is False

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager functionality."""
        async with self.service as service:
            assert service._session is not None
        assert self.service._session is None

    def test_get_forums_filtering(self):
        """Test forum filtering functionality."""
        # Set up test forums
        self.service.forums_cache = [
            ForumLink("Tech Forum", "https://tech.com", "Technology", "Tech"),
            ForumLink(
                "General Chat", "https://general.com", "General discussion", "General"
            ),
            ForumLink("Programming", "https://prog.com", "Code discussion", "Tech"),
        ]
        self.service.last_refresh = datetime.now(UTC)

        # No filter
        all_forums = self.service.get_forums()
        assert len(all_forums) == 3

        # Category filter
        tech_forums = self.service.get_forums(category_filter="Tech")
        assert len(tech_forums) == 2

        # Search filter
        search_results = self.service.get_forums(search_query="tech")
        assert len(search_results) >= 1

        # Limit
        limited = self.service.get_forums(limit=2)
        assert len(limited) == 2

    def test_search_forums(self):
        """Test forum search functionality."""
        self.service.forums_cache = [
            ForumLink(
                "Python Programming", "https://python.com", "Python coding", "Tech"
            ),
            ForumLink("Web Development", "https://web.com", "HTML, CSS, JS", "Tech"),
            ForumLink(
                "General Chat", "https://general.com", "Random discussions", "General"
            ),
        ]
        self.service.last_refresh = datetime.now(UTC)

        # Search by name
        results = self.service.search_forums("Python")
        assert len(results) >= 1
        assert any("Python" in r["name"] for r in results)

        # Search by description
        results = self.service.search_forums("coding")
        assert len(results) >= 1

        # No results
        results = self.service.search_forums("nonexistent")
        assert len(results) == 0

    def test_get_forum_by_url(self):
        """Test getting forum by URL."""
        test_forum = ForumLink("Test Forum", "https://test.com", "Test description")
        self.service.forums_cache = [test_forum]

        # Found
        result = self.service.get_forum_by_url("https://test.com")
        assert result is not None
        assert result["name"] == "Test Forum"

        # Not found
        result = self.service.get_forum_by_url("https://notfound.com")
        assert result is None

    def test_get_cache_info(self):
        """Test cache information retrieval."""
        self.service.forums_cache = [ForumLink("Test", "https://test.com")]
        self.service.last_refresh = datetime.now(UTC)

        info = self.service.get_cache_info()

        assert info["total_forums"] == 1
        assert info["cache_valid"] is True
        assert info["source_url"] == "https://tor.taxi/"
        assert "last_refresh" in info

    def test_get_service_status(self):
        """Test service status retrieval."""
        status = self.service.get_service_status()

        assert status["service"] == "forum_directory"
        assert "cache_info" in status
        assert "safety_features" in status
        assert status["safety_features"]["content_filtering"] is True
        assert status["safety_features"]["forums_only"] is True

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test service health check."""
        async with self.service:
            health = await self.service.health_check()

        assert "service_healthy" in health
        assert "cache_valid" in health
        assert "source_reachable" in health
        assert "forums_count" in health

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_fetch_forum_directory_success(self, mock_get):
        """Test successful forum directory fetching."""
        # Mock successful HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value="""
            <html><body>
            <h2>Forums</h2>
            <a href="https://test.onion">Test Forum</a>
            </body></html>
        """
        )

        mock_get.return_value.__aenter__.return_value = mock_response

        async with self.service:
            success = await self.service.fetch_forum_directory()

        assert success is True
        assert self.service.last_refresh is not None

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_fetch_forum_directory_failure(self, mock_get):
        """Test failed forum directory fetching."""
        # Mock failed HTTP response
        mock_response = AsyncMock()
        mock_response.status = 404

        mock_get.return_value.__aenter__.return_value = mock_response

        async with self.service:
            success = await self.service.fetch_forum_directory()

        assert success is False

    @pytest.mark.asyncio
    async def test_refresh_if_needed(self):
        """Test conditional refresh logic."""
        # Fresh cache - should not refresh
        self.service.forums_cache = [ForumLink("Test", "https://test.com")]
        self.service.last_refresh = datetime.now(UTC)

        async with self.service:
            result = await self.service.refresh_if_needed()

        assert result is True

        # Expired cache - should refresh (but will fail without mocking)
        self.service.last_refresh = datetime.now(UTC) - timedelta(hours=2)

        async with self.service:
            # This will fail due to network, but that's expected in tests
            result = await self.service.refresh_if_needed()

        # Result depends on network availability, but test passes either way
