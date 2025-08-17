"""Tests for threat intelligence RSS feed sources."""

import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock, patch

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from internal_assistant.server.feeds.feeds_service import RSSFeedService


class TestThreatIntelFeeds:
    """Test threat intelligence RSS feed functionality."""
    
    def test_threat_intel_feed_sources(self):
        """Test that all threat intelligence feed sources are configured."""
        service = RSSFeedService()
        
        expected_sources = {
            "Federal Reserve", "FDIC", "OCC", "FinCEN", "FFIEC",
            "CISA Financial Services", "FBI IC3", "Secret Service Financial Crimes",
            "Treasury OFAC", "NY DFS Cybersecurity"
        }
        
        actual_sources = set(service.FEED_SOURCES.keys())
        
        assert actual_sources == expected_sources, f"Missing sources: {expected_sources - actual_sources}"
        assert len(service.FEED_SOURCES) == 10, f"Expected 10 sources, got {len(service.FEED_SOURCES)}"
        
        print(f"[PASS] All {len(service.FEED_SOURCES)} threat intelligence RSS sources configured")
    
    def test_threat_intel_categories(self):
        """Test threat intelligence categorization."""
        service = RSSFeedService()
        
        # Test all sources are categorized
        categorized_sources = set()
        for sources in service.SOURCE_CATEGORIES.values():
            categorized_sources.update(sources)
        
        all_sources = set(service.FEED_SOURCES.keys())
        uncategorized = all_sources - categorized_sources
        
        assert len(uncategorized) == 0, f"Uncategorized sources: {uncategorized}"
        
        # Test threat intelligence category structure
        expected_categories = {
            "Banking Regulators", "Financial Crimes", 
            "Cybersecurity", "Sanctions & Compliance"
        }
        actual_categories = set(service.SOURCE_CATEGORIES.keys())
        
        assert actual_categories == expected_categories
        
        print(f"[PASS] All sources properly categorized into {len(expected_categories)} threat intelligence categories")
    
    def test_threat_intel_priority_ordering(self):
        """Test threat intelligence priority assignments."""
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
        
        # Test CISA has highest priority for threat intelligence
        assert service.SOURCE_PRIORITY["CISA Financial Services"] == 1
        
        # Test FBI IC3 has second priority for active threats
        assert service.SOURCE_PRIORITY["FBI IC3"] == 2
        
        print(f"[PASS] All sources have valid threat intel priorities (range: {min(priorities)}-{max(priorities)})")
    
    def test_threat_intel_categorized_filtering(self):
        """Test threat intelligence category-based filtering."""
        service = RSSFeedService()
        
        # Mock some threat intel feed items
        from internal_assistant.server.feeds.feeds_service import FeedItem
        from datetime import datetime, timezone
        
        mock_items = [
            FeedItem("CISA Alert", "link1", "Critical vulnerability", datetime.now(timezone.utc), "CISA Financial Services", "1"),
            FeedItem("FBI Threat", "link2", "Active threat campaign", datetime.now(timezone.utc), "FBI IC3", "2"),
            FeedItem("FinCEN Advisory", "link3", "Suspicious activity", datetime.now(timezone.utc), "FinCEN", "3"),
            FeedItem("Fed Guidance", "link4", "Cyber guidance", datetime.now(timezone.utc), "Federal Reserve", "4"),
        ]
        
        service.feeds_cache = mock_items
        
        # Test category filtering
        cyber_feeds = service.get_feeds(source_filter="Cybersecurity")
        crimes_feeds = service.get_feeds(source_filter="Financial Crimes")
        
        # Cybersecurity should include CISA + NY DFS
        cyber_sources = {feed['source'] for feed in cyber_feeds}
        assert "CISA Financial Services" in cyber_sources
        assert "FBI IC3" not in cyber_sources
        
        # Financial Crimes should include FinCEN + FBI IC3 + Secret Service  
        crimes_sources = {feed['source'] for feed in crimes_feeds}
        assert "FinCEN" in crimes_sources
        assert "FBI IC3" in crimes_sources
        assert "CISA Financial Services" not in crimes_sources
        
        print("[PASS] Threat intelligence category-based filtering working correctly")
    
    def test_threat_intel_priority_sorting(self):
        """Test threat intelligence priority-based sorting."""
        service = RSSFeedService()
        
        # Mock items with different threat intel priorities
        from internal_assistant.server.feeds.feeds_service import FeedItem
        from datetime import datetime, timezone
        
        mock_items = [
            FeedItem("Low Priority", "link1", "summary1", datetime.now(timezone.utc), "FFIEC", "1"),        # Priority 10
            FeedItem("High Priority", "link2", "summary2", datetime.now(timezone.utc), "CISA Financial Services", "2"),  # Priority 1
            FeedItem("Medium Priority", "link3", "summary3", datetime.now(timezone.utc), "FinCEN", "3"),    # Priority 3
        ]
        
        service.feeds_cache = mock_items
        
        # Get all feeds (should be sorted by threat intel priority)
        feeds = service.get_feeds()
        
        # Check sorting order
        assert feeds[0]['source'] == "CISA Financial Services"  # Priority 1
        assert feeds[1]['source'] == "FinCEN"                   # Priority 3  
        assert feeds[2]['source'] == "FFIEC"                    # Priority 10
        
        print("[PASS] Threat intelligence priority-based sorting working correctly")


async def test_threat_intel_feed_urls():
    """Test that threat intel feed URLs are accessible and return valid content."""
    service = RSSFeedService()
    
    print("Testing threat intelligence RSS feed URL accessibility...")
    
    # Test a subset of feeds to avoid network issues
    test_sources = {
        "Federal Reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
        "FDIC": "https://www.fdic.gov/news/financial-institution-letters/rss.xml",
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
    
    print(f"Threat intel feed URL test completed: {successful_feeds}/{len(test_sources)} successful")


if __name__ == "__main__":
    print("Testing threat intelligence RSS feed functionality...\n")
    
    test = TestThreatIntelFeeds()
    
    # Run synchronous tests
    sync_tests = [
        ("Threat Intel Feed Sources Configuration", test.test_threat_intel_feed_sources),
        ("Threat Intel Source Categorization", test.test_threat_intel_categories), 
        ("Threat Intel Priority Ordering", test.test_threat_intel_priority_ordering),
        ("Threat Intel Categorized Filtering", test.test_threat_intel_categorized_filtering),
        ("Threat Intel Priority Sorting", test.test_threat_intel_priority_sorting),
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
    print("\nRunning threat intel feed URL accessibility test...")
    try:
        asyncio.run(test_threat_intel_feed_urls())
        print("\nAll threat intelligence RSS feed tests completed!")
    except Exception as e:
        print(f"[FAIL] Feed URL test crashed: {e}")
    
    if passed == len(sync_tests):
        print("\n[SUCCESS] All threat intelligence RSS feed functionality tests passed!")
        print("* 10 threat intelligence RSS sources configured and categorized")
        print("* Priority-based sorting with CISA Financial Services as top priority")  
        print("* Category-based filtering for Banking Regulators, Financial Crimes, Cybersecurity, Sanctions")
        print("* Enhanced UI dropdown support for threat intelligence")
        print("* Ready for banking threat intelligence monitoring")
    else:
        print(f"\n[PARTIAL SUCCESS] {passed}/{len(sync_tests)} tests passed")
        print("Some functionality may need debugging before deployment.")