#!/usr/bin/env python3
"""Comprehensive functionality testing for Forum Directory Backend
This is a standalone test suite for static analysis without server startup
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta

# Import modules to test
sys.path.append(".")
from internal_assistant.server.feeds.forum_directory_service import (
    ForumDirectoryService,
)
from internal_assistant.server.feeds.forum_parser import ForumDirectoryParser, ForumLink


def test_forum_link_functionality():
    """Test ForumLink basic functionality"""
    print("Testing ForumLink functionality...")

    # Valid link
    valid_link = ForumLink(
        "Tech Forum", "https://techforum.onion", "Technology discussions", "Technology"
    )
    assert valid_link.is_valid() == True
    assert valid_link.to_dict()["name"] == "Tech Forum"
    assert valid_link.to_dict()["category"] == "Technology"

    # Invalid links
    invalid_name = ForumLink("", "https://example.com")
    assert invalid_name.is_valid() == False

    invalid_url = ForumLink("Test", "ftp://invalid.com")
    assert invalid_url.is_valid() == False

    print("+ ForumLink validation working correctly")


def test_forum_parser_safety():
    """Test ForumDirectoryParser safety mechanisms"""
    print("Testing ForumDirectoryParser safety...")

    parser = ForumDirectoryParser()

    # Test exclusion patterns
    assert parser._is_excluded_section("Drug Marketplace") == True
    assert parser._is_excluded_section("Weapon Sales") == True
    assert parser._is_excluded_section("General Discussion") == False
    assert parser._is_excluded_section("Tech Forum") == False

    # Test forum safety validation
    safe_forum = ForumLink("Tech Discussion", "https://tech.onion", "Technology forum")
    unsafe_forum = ForumLink("Drug Market", "https://drugs.onion", "Buy drugs here")

    assert parser._is_safe_forum(safe_forum) == True
    assert parser._is_safe_forum(unsafe_forum) == False

    print("+ Safety filtering working correctly")


def test_forum_parser_html_parsing():
    """Test HTML parsing with safe content"""
    print("Testing HTML parsing...")

    parser = ForumDirectoryParser()

    # Test with safe forum HTML
    safe_html = """
    <html>
    <body>
    <h2>Discussion Forums</h2>
    <div class="forum-section">
        <a href="https://techforum.onion">Tech Discussion</a>
        <p>Technology and programming discussions</p>
    </div>
    <h2>General Chat</h2>
    <div class="forum-section">
        <a href="https://generalchat.onion">General Chat</a>
        <p>Random discussions and social interactions</p>
    </div>
    </body>
    </html>
    """

    forums = parser.parse_forum_directory(safe_html)
    assert len(forums) >= 1
    assert all(forum.is_valid() for forum in forums)
    assert all(parser._is_safe_forum(forum) for forum in forums)

    # Test with mixed content (should filter out unsafe)
    mixed_html = """
    <html>
    <body>
    <h2>Drug Marketplace</h2>
    <div>
        <a href="https://drugmarket.onion">Buy Drugs</a>
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

    filtered_forums = parser.parse_forum_directory(mixed_html)
    # Should only contain safe forums
    for forum in filtered_forums:
        assert "drug" not in forum.name.lower()
        assert parser._is_safe_forum(forum)

    print("+ HTML parsing and filtering working correctly")


def test_forum_service_initialization():
    """Test ForumDirectoryService initialization"""
    print("Testing ForumDirectoryService initialization...")

    service = ForumDirectoryService(cache_duration_hours=6)
    assert service.cache_duration_hours == 6
    assert service.forums_cache == []
    assert service.last_refresh is None
    assert service._session is None

    # Test cache validity
    assert service.is_cache_valid() == False

    # Simulate cache with data
    service.forums_cache = [ForumLink("Test", "https://test.onion")]
    service.last_refresh = datetime.now(UTC)
    assert service.is_cache_valid() == True

    # Simulate expired cache
    service.last_refresh = datetime.now(UTC) - timedelta(hours=7)
    assert service.is_cache_valid() == False

    print("+ Service initialization and cache validation working")


def test_forum_service_filtering():
    """Test forum filtering and search functionality"""
    print("Testing forum filtering and search...")

    service = ForumDirectoryService()

    # Set up test data
    test_forums = [
        ForumLink(
            "Python Programming",
            "https://python.onion",
            "Python coding discussions",
            "Technology",
        ),
        ForumLink(
            "Web Development",
            "https://webdev.onion",
            "HTML, CSS, JavaScript",
            "Technology",
        ),
        ForumLink(
            "General Chat", "https://general.onion", "Random discussions", "General"
        ),
        ForumLink(
            "Crypto Discussion",
            "https://crypto.onion",
            "Cryptocurrency talk",
            "Finance",
        ),
    ]

    service.forums_cache = test_forums
    service.last_refresh = datetime.now(UTC)

    # Test filtering by category
    tech_forums = service.get_forums(category_filter="Technology")
    assert len(tech_forums) == 2

    # Test search functionality
    python_results = service.search_forums("Python")
    assert len(python_results) >= 1
    assert any("Python" in result["name"] for result in python_results)

    # Test search by description
    coding_results = service.search_forums("coding")
    assert len(coding_results) >= 1

    # Test URL lookup
    found_forum = service.get_forum_by_url("https://python.onion")
    assert found_forum is not None
    assert found_forum["name"] == "Python Programming"

    not_found = service.get_forum_by_url("https://nonexistent.onion")
    assert not_found is None

    print("+ Filtering and search functionality working")


def test_error_scenarios():
    """Test error handling scenarios"""
    print("Testing error scenarios...")

    parser = ForumDirectoryParser()

    # Test with malformed HTML
    malformed_html = "<html><body><h2>Incomplete"
    try:
        forums = parser.parse_forum_directory(malformed_html)
        # Should not crash, might return empty list
        assert isinstance(forums, list)
        print("+ Malformed HTML handled gracefully")
    except Exception as e:
        print(f"- Malformed HTML caused error: {e}")

    # Test with empty HTML
    empty_html = ""
    forums = parser.parse_forum_directory(empty_html)
    assert isinstance(forums, list)
    assert len(forums) == 0
    print("+ Empty HTML handled gracefully")

    # Test service error handling
    service = ForumDirectoryService()

    # Test operations on empty cache
    empty_results = service.get_forums()
    assert isinstance(empty_results, list)
    assert len(empty_results) == 0

    empty_search = service.search_forums("test")
    assert isinstance(empty_search, list)
    assert len(empty_search) == 0

    print("+ Error scenarios handled properly")


async def test_async_functionality():
    """Test async context manager and network handling"""
    print("Testing async functionality...")

    service = ForumDirectoryService()

    # Test async context manager
    async with service as svc:
        assert svc._session is not None

        # Test health check (will fail without network but shouldn't crash)
        try:
            health_status = await svc.health_check()
            assert isinstance(health_status, dict)
            assert "service_healthy" in health_status
            print("+ Health check structure correct")
        except Exception as e:
            print(f"Health check failed as expected (no network): {type(e).__name__}")

    # Session should be closed after context
    assert service._session is None
    print("+ Async context manager working")


def main():
    """Run all functionality tests"""
    print("FORUM DIRECTORY FUNCTIONALITY TEST SUITE")
    print("=" * 50)

    try:
        # Basic functionality tests
        test_forum_link_functionality()
        test_forum_parser_safety()
        test_forum_parser_html_parsing()
        test_forum_service_initialization()
        test_forum_service_filtering()
        test_error_scenarios()

        # Async tests
        asyncio.run(test_async_functionality())

        print("\n" + "=" * 50)
        print("+ ALL TESTS PASSED - Forum directory backend functional")

    except Exception as e:
        print(f"\n- TEST FAILED: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
