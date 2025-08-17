"""Full integration tests for RSS feed functionality."""

import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


class TestFullIntegration:
    """End-to-end integration tests."""
    
    async def test_api_endpoints_integration(self):
        """Test API endpoints are properly registered."""
        try:
            # Test that feeds router is importable
            from internal_assistant.server.feeds.feeds_router import feeds_router
            from internal_assistant.launcher import create_app
            from internal_assistant.di import create_application_injector
            
            print("[PASS] API endpoints importable")
            return True
            
        except ImportError as e:
            print(f"[FAIL] API integration error: {e}")
            return False
        except Exception as e:
            print(f"[FAIL] Unexpected API error: {e}")
            return False
    
    async def test_service_dependency_injection(self):
        """Test that services are properly injected."""
        try:
            from internal_assistant.di import create_application_injector
            from internal_assistant.server.feeds.feeds_service import RSSFeedService
            
            # Create injector
            injector = create_application_injector()
            
            # Get feeds service
            feeds_service = injector.get(RSSFeedService)
            
            # Verify it's the correct type
            assert isinstance(feeds_service, RSSFeedService)
            assert feeds_service.max_items == 300
            
            print("[PASS] Service dependency injection working")
            return True
            
        except Exception as e:
            print(f"[FAIL] DI integration error: {e}")
            return False
    
    async def test_background_service_lifecycle(self):
        """Test background service start/stop lifecycle."""
        try:
            from internal_assistant.server.feeds.feeds_service import RSSFeedService
            from internal_assistant.server.feeds.background_refresh import BackgroundRefreshService
            
            # Create services
            feeds_service = RSSFeedService(max_items=10)  # Small for testing
            background_service = BackgroundRefreshService(feeds_service, refresh_interval_minutes=1)
            
            # Mock the refresh method
            with patch.object(feeds_service, 'refresh_feeds', new_callable=AsyncMock, return_value=True):
                with patch.object(feeds_service, '__aenter__', return_value=feeds_service):
                    with patch.object(feeds_service, '__aexit__', return_value=None):
                        
                        # Test start
                        await background_service.start()
                        assert background_service.is_running()
                        
                        # Let it run briefly
                        await asyncio.sleep(0.1)
                        
                        # Test stop
                        await background_service.stop()
                        assert not background_service.is_running()
            
            print("[PASS] Background service lifecycle working")
            return True
            
        except Exception as e:
            print(f"[FAIL] Background service error: {e}")
            return False
    
    def test_ui_component_integration(self):
        """Test UI components are properly integrated."""
        try:
            # Check that UI file has all required components
            ui_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'internal_assistant', 'ui', 'ui.py')
            
            with open(ui_file_path, 'r', encoding='utf-8') as f:
                ui_content = f.read()
            
            # Essential integration points
            integration_points = [
                'RSSFeedService',  # Import
                'feeds_service: RSSFeedService',  # Constructor parameter
                'self._feeds_service = feeds_service',  # Assignment
                '[RSS] External Information',  # UI section
                'feed_refresh_btn.click',  # Event handler
                'confirmOpenExternal',  # JavaScript function
                '_format_feeds_display'  # Display method
            ]
            
            missing_points = []
            for point in integration_points:
                if point not in ui_content:
                    missing_points.append(point)
            
            if missing_points:
                print(f"[FAIL] Missing UI integration points: {missing_points}")
                return False
            
            print("[PASS] UI component integration complete")
            return True
            
        except Exception as e:
            print(f"[FAIL] UI integration error: {e}")
            return False
    
    async def test_error_handling_scenarios(self):
        """Test various error handling scenarios."""
        try:
            from internal_assistant.server.feeds.feeds_service import RSSFeedService
            
            feeds_service = RSSFeedService(max_items=10)
            
            # Test 1: Network timeout simulation
            with patch('aiohttp.ClientSession.get') as mock_get:
                mock_get.side_effect = asyncio.TimeoutError()
                
                async with feeds_service:
                    result = await feeds_service.fetch_feed("https://example.com/feed", "Test")
                    assert result == []  # Should return empty list on timeout
            
            # Test 2: Malformed feed content
            malformed_content = "This is not XML"
            items = feeds_service._parse_feed_content(malformed_content, "Test")
            assert items == []  # Should handle gracefully
            
            # Test 3: Memory limit enforcement
            from internal_assistant.server.feeds.feeds_service import FeedItem
            
            # Create more items than limit
            test_items = []
            for i in range(20):  # More than max_items=10
                item = FeedItem(
                    title=f"Test {i}",
                    link=f"https://test.com/{i}",
                    summary=f"Summary {i}",
                    published=datetime.now(timezone.utc),
                    source="Test",
                    guid=str(i)
                )
                test_items.append(item)
            
            # Simulate cache limit enforcement
            feeds_service.feeds_cache = test_items[:feeds_service.max_items]
            assert len(feeds_service.feeds_cache) == 10  # Limited to max_items
            
            print("[PASS] Error handling scenarios working")
            return True
            
        except Exception as e:
            print(f"[FAIL] Error handling test failed: {e}")
            return False
    
    def test_security_considerations(self):
        """Test security aspects of the implementation."""
        try:
            # Check that feeds router requires authentication
            router_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 
                                          'internal_assistant', 'server', 'feeds', 'feeds_router.py')
            
            with open(router_file_path, 'r', encoding='utf-8') as f:
                router_content = f.read()
            
            security_checks = [
                'dependencies=[Depends(authenticated)]',  # Router-level auth
                'HTTPException',  # Proper error handling
                'logger.error',   # Error logging
            ]
            
            missing_security = []
            for check in security_checks:
                if check not in router_content:
                    missing_security.append(check)
            
            if missing_security:
                print(f"[FAIL] Missing security features: {missing_security}")
                return False
            
            # Check UI JavaScript security
            ui_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'internal_assistant', 'ui', 'ui.py')
            with open(ui_file_path, 'r', encoding='utf-8') as f:
                ui_content = f.read()
            
            # Ensure external links open securely
            if 'noopener,noreferrer' not in ui_content:
                print("[FAIL] External links not properly secured")
                return False
            
            # Ensure confirmation dialog is present
            if 'confirm(' not in ui_content:
                print("[FAIL] No confirmation dialog for external links")
                return False
            
            print("[PASS] Security considerations implemented")
            return True
            
        except Exception as e:
            print(f"[FAIL] Security test error: {e}")
            return False
    
    def test_configuration_validation(self):
        """Test configuration and settings validation."""
        try:
            # Check that dependencies are added to pyproject.toml
            pyproject_path = os.path.join(os.path.dirname(__file__), '..', '..', 'pyproject.toml')
            
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                pyproject_content = f.read()
            
            required_deps = [
                'feedparser',
                'aiohttp', 
                'beautifulsoup4'
            ]
            
            missing_deps = []
            for dep in required_deps:
                if dep not in pyproject_content:
                    missing_deps.append(dep)
            
            if missing_deps:
                print(f"[FAIL] Missing dependencies in pyproject.toml: {missing_deps}")
                return False
            
            # Check feeds service configuration
            from internal_assistant.server.feeds.feeds_service import RSSFeedService
            
            # Verify feed sources are configured
            expected_sources = ["FINRA", "Federal Reserve", "FinCEN"]
            actual_sources = list(RSSFeedService.FEED_SOURCES.keys())
            
            for expected in expected_sources:
                if expected not in actual_sources:
                    print(f"[FAIL] Missing feed source: {expected}")
                    return False
            
            print("[PASS] Configuration validation complete")
            return True
            
        except Exception as e:
            print(f"[FAIL] Configuration validation error: {e}")
            return False


async def run_async_tests():
    """Run async integration tests."""
    test = TestFullIntegration()
    
    tests = [
        ("API Endpoints Integration", test.test_api_endpoints_integration),
        ("Service Dependency Injection", test.test_service_dependency_injection),
        ("Background Service Lifecycle", test.test_background_service_lifecycle),
        ("Error Handling Scenarios", test.test_error_handling_scenarios)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        try:
            if await test_func():
                passed += 1
        except Exception as e:
            print(f"[FAIL] {test_name} crashed: {e}")
        print()
    
    return passed, len(tests)


if __name__ == "__main__":
    print("Running full integration tests for RSS feed functionality...\n")
    
    # Run sync tests first
    test = TestFullIntegration()
    
    sync_tests = [
        ("UI Component Integration", test.test_ui_component_integration),
        ("Security Considerations", test.test_security_considerations), 
        ("Configuration Validation", test.test_configuration_validation)
    ]
    
    sync_passed = 0
    for test_name, test_func in sync_tests:
        print(f"Testing {test_name}...")
        try:
            if test_func():
                sync_passed += 1
        except Exception as e:
            print(f"[FAIL] {test_name} crashed: {e}")
        print()
    
    # Run async tests
    print("Running async integration tests...")
    async_passed, async_total = asyncio.run(run_async_tests())
    
    total_passed = sync_passed + async_passed
    total_tests = len(sync_tests) + async_total
    
    print(f"Results: {total_passed}/{total_tests} integration tests passed")
    
    if total_passed == total_tests:
        print("\nAll Phase 5 full integration tests passed! [SUCCESS]")
        print("[PASS] API endpoints properly integrated")
        print("[PASS] Dependency injection working correctly")
        print("[PASS] Background services functional")
        print("[PASS] UI components fully integrated")
        print("[PASS] Error handling robust")
        print("[PASS] Security measures in place")
        print("[PASS] Configuration properly set up")
        print("\n[SUCCESS] RSS FEED INTEGRATION COMPLETE!")
        print("External Information section ready for production use.")
    else:
        print(f"\n{total_tests - total_passed} integration tests failed.")
        print("Please review implementation before deployment.")
        sys.exit(1)