"""Tests for expanded RSS feed sources."""

import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock, patch

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from internal_assistant.server.feeds.feeds_service import RSSFeedService


class TestExpandedFeeds:
    """Test expanded RSS feed functionality."""
    
    def test_expanded_feed_sources(self):
        """Test that all new feed sources are configured."""
        service = RSSFeedService()
        
        expected_sources = {
            "Federal Reserve", "FDIC", "FINRA", "FinCEN", "SEC", "OCC",
            "U.S. Treasury", "Bureau of Labor Statistics", "CFPB", "DOJ Financial Crimes"
        }
        
        actual_sources = set(service.FEED_SOURCES.keys())
        
        assert actual_sources == expected_sources, f"Missing sources: {expected_sources - actual_sources}"
        assert len(service.FEED_SOURCES) == 10, f"Expected 10 sources, got {len(service.FEED_SOURCES)}"
        
        print(f"[PASS] All {len(service.FEED_SOURCES)} RSS sources configured")
    
    def test_source_categories(self):
        """Test source categorization."""
        service = RSSFeedService()
        
        # Test all sources are categorized
        categorized_sources = set()
        for sources in service.SOURCE_CATEGORIES.values():
            categorized_sources.update(sources)
        
        all_sources = set(service.FEED_SOURCES.keys())
        uncategorized = all_sources - categorized_sources
        
        assert len(uncategorized) == 0, f"Uncategorized sources: {uncategorized}"
        
        # Test category structure
        expected_categories = {
            "Banking Regulation", "Securities & Markets", 
            "Enforcement & Legal", "Treasury & Economic"
        }
        actual_categories = set(service.SOURCE_CATEGORIES.keys())
        
        assert actual_categories == expected_categories
        
        print(f"[PASS] All sources properly categorized into {len(expected_categories)} categories")
    
    def test_priority_ordering(self):
        """Test source priority assignments."""
        service = RSSFeedService()
        
        # Test all sources have priorities
        prioritized_sources = set(service.SOURCE_PRIORITY.keys())
        all_sources = set(service.FEED_SOURCES.keys())
        
        missing_priorities = all_sources - prioritized_sources
        assert len(missing_priorities) == 0, f"Sources missing priorities: {missing_priorities}"
        
        # Test priority values are reasonable (1-10 range)
        priorities = list(service.SOURCE_PRIORITY.values())
        assert min(priorities) >= 1, "Priority values should start from 1"
        assert max(priorities) <= 10, "Priority values should not exceed 10"
        
        # Test Federal Reserve has highest priority
        assert service.SOURCE_PRIORITY["Federal Reserve"] == 1
        
        print(f"[PASS] All sources have valid priorities (range: {min(priorities)}-{max(priorities)})")
    
    def test_categorized_filtering(self):
        """Test category-based filtering."""
        service = RSSFeedService()
        
        # Mock some feed items
        from internal_assistant.server.feeds.feeds_service import FeedItem
        from datetime import datetime, timezone
        
        mock_items = [
            FeedItem("Fed News", "link1", "summary1", datetime.now(timezone.utc), "Federal Reserve", "1"),
            FeedItem("FDIC Update", "link2", "summary2", datetime.now(timezone.utc), "FDIC", "2"),
            FeedItem("SEC Alert", "link3", "summary3", datetime.now(timezone.utc), "SEC", "3"),
            FeedItem("FINRA Notice", "link4", "summary4", datetime.now(timezone.utc), "FINRA", "4"),
        ]
        
        service.feeds_cache = mock_items
        
        # Test category filtering
        banking_feeds = service.get_feeds(source_filter="Banking Regulation")
        securities_feeds = service.get_feeds(source_filter="Securities & Markets")
        
        # Banking Regulation should include Fed + FDIC
        banking_sources = {feed['source'] for feed in banking_feeds}
        assert "Federal Reserve" in banking_sources
        assert "FDIC" in banking_sources
        assert "SEC" not in banking_sources
        
        # Securities & Markets should include SEC + FINRA  
        securities_sources = {feed['source'] for feed in securities_feeds}
        assert "SEC" in securities_sources
        assert "FINRA" in securities_sources
        assert "Federal Reserve" not in securities_sources
        
        print("[PASS] Category-based filtering working correctly")
    
    def test_priority_sorting(self):
        """Test priority-based sorting."""
        service = RSSFeedService()
        
        # Mock items with different priorities
        from internal_assistant.server.feeds.feeds_service import FeedItem
        from datetime import datetime, timezone
        
        mock_items = [
            FeedItem("Low Priority", "link1", "summary1", datetime.now(timezone.utc), "DOJ Financial Crimes", "1"),  # Priority 10
            FeedItem("High Priority", "link2", "summary2", datetime.now(timezone.utc), "Federal Reserve", "2"),      # Priority 1
            FeedItem("Medium Priority", "link3", "summary3", datetime.now(timezone.utc), "SEC", "3"),                # Priority 3
        ]
        
        service.feeds_cache = mock_items
        
        # Get all feeds (should be sorted by priority)
        feeds = service.get_feeds()
        
        # Check sorting order
        assert feeds[0]['source'] == "Federal Reserve"  # Priority 1
        assert feeds[1]['source'] == "SEC"              # Priority 3  
        assert feeds[2]['source'] == "DOJ Financial Crimes"  # Priority 10
        
        print("[PASS] Priority-based sorting working correctly")
    
    def test_increased_cache_size(self):
        """Test increased cache capacity."""
        service = RSSFeedService()
        
        # Default should be 500 now (increased from 300)
        assert service.max_items == 500, f"Expected max_items=500, got {service.max_items}"
        
        # Test with custom size
        custom_service = RSSFeedService(max_items=1000)
        assert custom_service.max_items == 1000
        
        print(f"[PASS] Cache capacity increased to {service.max_items} items")
    
    def test_available_sources_with_categories(self):
        """Test enhanced available sources method."""
        service = RSSFeedService()
        
        # Mock some cached items
        from internal_assistant.server.feeds.feeds_service import FeedItem
        from datetime import datetime, timezone
        
        mock_items = [
            FeedItem("Test1", "link1", "summary1", datetime.now(timezone.utc), "Federal Reserve", "1"),
            FeedItem("Test2", "link2", "summary2", datetime.now(timezone.utc), "SEC", "2"),
            FeedItem("Test3", "link3", "summary3", datetime.now(timezone.utc), "FDIC", "3"),
        ]
        
        service.feeds_cache = mock_items
        
        sources = service.get_available_sources()
        
        # Should include categories and individual sources
        assert "All" in sources
        assert "Banking Regulation" in sources  # Fed + FDIC are cached
        assert "Securities & Markets" in sources  # SEC is cached
        assert "--- Individual Sources ---" in sources
        assert "Federal Reserve" in sources
        assert "SEC" in sources
        assert "FDIC" in sources
        
        print(f"[PASS] Enhanced sources list includes {len(sources)} options")


async def test_feed_urls():
    """Test that feed URLs are accessible and return valid content."""
    service = RSSFeedService()
    
    print("Testing RSS feed URL accessibility...")
    
    # Test a subset of feeds to avoid network issues
    test_sources = {
        "Federal Reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
        "SEC": "https://www.sec.gov/news/pressreleases.rss",
    }
    
    successful_feeds = 0
    
    for source, url in test_sources.items():
        try:
            async with service:
                items = await service.fetch_feed(url, source)
                
            if items and len(items) > 0:
                print(f"[PASS] {source}: {len(items)} articles fetched successfully")
                successful_feeds += 1
            else:
                print(f"[WARN] {source}: No articles found (may be empty feed)")
                
        except Exception as e:
            print(f"[FAIL] {source}: Error fetching feed - {e}")
    
    print(f"Feed URL test completed: {successful_feeds}/{len(test_sources)} successful")


if __name__ == "__main__":
    print("Testing expanded RSS feed functionality...\n")
    
    test = TestExpandedFeeds()
    
    # Run synchronous tests
    sync_tests = [
        ("Feed Sources Configuration", test.test_expanded_feed_sources),
        ("Source Categorization", test.test_source_categories), 
        ("Priority Ordering", test.test_priority_ordering),
        ("Categorized Filtering", test.test_categorized_filtering),
        ("Priority Sorting", test.test_priority_sorting),
        ("Increased Cache Size", test.test_increased_cache_size),
        ("Available Sources Enhancement", test.test_available_sources_with_categories)
    ]
    
    passed = 0
    for test_name, test_func in sync_tests:
        print(f"Testing {test_name}...")
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test_name}: {e}")
        print()
    
    print(f"Synchronous tests: {passed}/{len(sync_tests)} passed")
    
    # Run async feed URL test
    print("\nRunning feed URL accessibility test...")
    try:
        asyncio.run(test_feed_urls())
        print("\nAll expanded RSS feed tests completed!")
    except Exception as e:
        print(f"[FAIL] Feed URL test crashed: {e}")
    
    if passed == len(sync_tests):
        print("\n[SUCCESS] All expanded RSS feed functionality tests passed!")
        print("✓ 10 RSS sources configured and categorized")
        print("✓ Priority-based sorting implemented")  
        print("✓ Category-based filtering working")
        print("✓ Enhanced UI dropdown support")
        print("✓ Increased cache capacity to 500 items")
    else:
        print(f"\n[PARTIAL SUCCESS] {passed}/{len(sync_tests)} tests passed")
        print("Some functionality may need debugging before deployment.")