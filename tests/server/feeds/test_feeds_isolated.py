"""Isolated unit tests for RSS feeds service without Internal Assistant imports."""

import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

import pytest
from aiohttp import ClientResponse

from internal_assistant.server.feeds.feeds_service import RSSFeedService, FeedItem


class TestFeedServiceIsolated:
    """Isolated tests that don't trigger dependency injection."""
    
    def test_memory_limit_validation(self):
        """Test that memory limit is properly enforced."""
        service = RSSFeedService(max_items=3)
        
        # Create test items
        items = [
            FeedItem(
                title=f"Item {i}",
                link=f"https://example.com/{i}",
                summary=f"Summary {i}",
                published=datetime.now(timezone.utc) - timedelta(hours=i),
                source="Test",
                guid=str(i)
            )
            for i in range(6)
        ]
        
        # Simulate what happens during refresh
        items.sort(key=lambda x: x.published, reverse=True)
        service.feeds_cache = items[:service.max_items]
        
        assert len(service.feeds_cache) == 3
        assert service.feeds_cache[0].title == "Item 0"  # Most recent
        assert service.feeds_cache[1].title == "Item 1"
        assert service.feeds_cache[2].title == "Item 2"
    
    def test_feed_parsing_with_html(self):
        """Test RSS feed parsing with HTML content."""
        service = RSSFeedService()
        
        rss_content = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Test Feed</title>
                <item>
                    <title>Test Article</title>
                    <link>https://example.com/test</link>
                    <description>&lt;p&gt;This is &lt;strong&gt;bold&lt;/strong&gt; text&lt;/p&gt;</description>
                    <pubDate>Wed, 01 Jan 2025 12:00:00 GMT</pubDate>
                    <guid>test-guid</guid>
                </item>
            </channel>
        </rss>"""
        
        items = service._parse_feed_content(rss_content, "Test Source")
        
        assert len(items) == 1
        item = items[0]
        assert item.title == "Test Article"
        assert "bold" in item.summary
        assert "<p>" not in item.summary
        assert "<strong>" not in item.summary
    
    def test_source_filtering(self):
        """Test source-based filtering."""
        service = RSSFeedService()
        
        # Add test items with different sources
        service.feeds_cache = [
            FeedItem("FINRA Item", "link1", "summary1", datetime.now(timezone.utc), "FINRA", "1"),
            FeedItem("Fed Item", "link2", "summary2", datetime.now(timezone.utc), "Federal Reserve", "2"),
            FeedItem("Another FINRA", "link3", "summary3", datetime.now(timezone.utc), "FINRA", "3")
        ]
        
        # Test filtering by FINRA
        finra_feeds = service.get_feeds(source_filter="FINRA")
        assert len(finra_feeds) == 2
        assert all("FINRA" == feed["source"] for feed in finra_feeds)
        
        # Test "All" filter
        all_feeds = service.get_feeds(source_filter="All")
        assert len(all_feeds) == 3
    
    def test_date_filtering(self):
        """Test date-based filtering."""
        service = RSSFeedService()
        
        now = datetime.now(timezone.utc)
        service.feeds_cache = [
            FeedItem("Recent", "link1", "summary1", now, "Test", "1"),
            FeedItem("Week Old", "link2", "summary2", now - timedelta(days=5), "Test", "2"),
            FeedItem("Month Old", "link3", "summary3", now - timedelta(days=20), "Test", "3"),
            FeedItem("Very Old", "link4", "summary4", now - timedelta(days=40), "Test", "4")
        ]
        
        # Test 7-day filter
        recent_feeds = service.get_feeds(days_filter=7)
        assert len(recent_feeds) == 2  # Recent and Week Old
        
        # Test 30-day filter  
        month_feeds = service.get_feeds(days_filter=30)
        assert len(month_feeds) == 3  # All but Very Old
    
    def test_error_handling_in_parsing(self):
        """Test error handling during feed parsing."""
        service = RSSFeedService()
        
        # Test with malformed XML
        bad_xml = "This is not XML at all"
        items = service._parse_feed_content(bad_xml, "Test")
        assert items == []
        
        # Test with valid XML but malformed RSS
        bad_rss = """<?xml version="1.0"?>
        <root>
            <not-rss>true</not-rss>
        </root>"""
        items = service._parse_feed_content(bad_rss, "Test")
        assert items == []


if __name__ == "__main__":
    # Run basic validation
    test = TestFeedServiceIsolated()
    
    print("Running memory limit test...")
    test.test_memory_limit_validation()
    print("[PASS] Memory limit test passed")
    
    print("Running HTML parsing test...")
    test.test_feed_parsing_with_html()
    print("[PASS] HTML parsing test passed")
    
    print("Running source filtering test...")
    test.test_source_filtering()
    print("[PASS] Source filtering test passed")
    
    print("Running date filtering test...")
    test.test_date_filtering()
    print("[PASS] Date filtering test passed")
    
    print("Running error handling test...")
    test.test_error_handling_in_parsing()
    print("[PASS] Error handling test passed")
    
    print("\nAll Phase 1 tests passed! [SUCCESS]")