"""Tests for background RSS feed refresh service."""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from internal_assistant.server.feeds.background_refresh import BackgroundRefreshService
from internal_assistant.server.feeds.feeds_service import RSSFeedService


class TestBackgroundRefreshIsolated:
    """Isolated tests for background refresh service."""

    def test_service_initialization(self):
        """Test background service initialization."""
        feed_service = RSSFeedService()
        bg_service = BackgroundRefreshService(feed_service, refresh_interval_minutes=30)

        assert bg_service.refresh_interval == 30 * 60  # 30 minutes in seconds
        assert not bg_service.is_running()
        assert bg_service._refresh_task is None

    def test_get_status(self):
        """Test status information retrieval."""
        feed_service = RSSFeedService()
        bg_service = BackgroundRefreshService(feed_service, refresh_interval_minutes=60)

        status = bg_service.get_status()

        assert "is_running" in status
        assert "refresh_interval_minutes" in status
        assert "last_refresh" in status
        assert "total_items" in status
        assert "sources" in status

        assert status["is_running"] is False
        assert status["refresh_interval_minutes"] == 60
        assert status["total_items"] == 0

    async def test_start_and_stop_service(self):
        """Test starting and stopping background service."""
        feed_service = RSSFeedService()

        # Mock the refresh method to avoid network calls
        with patch.object(
            feed_service, "refresh_feeds", new_callable=AsyncMock, return_value=True
        ):
            with patch.object(feed_service, "__aenter__", return_value=feed_service):
                with patch.object(feed_service, "__aexit__", return_value=None):
                    bg_service = BackgroundRefreshService(
                        feed_service, refresh_interval_minutes=1
                    )  # 1 minute for testing

                    # Test starting
                    await bg_service.start()
                    assert bg_service.is_running()
                    assert bg_service._refresh_task is not None

                    # Let it run briefly
                    await asyncio.sleep(0.1)

                    # Test stopping
                    await bg_service.stop()
                    assert not bg_service.is_running()

    async def test_refresh_failure_handling(self):
        """Test handling of refresh failures."""
        feed_service = RSSFeedService()

        # Mock refresh to fail
        with patch.object(
            feed_service, "refresh_feeds", new_callable=AsyncMock, return_value=False
        ):
            with patch.object(feed_service, "__aenter__", return_value=feed_service):
                with patch.object(feed_service, "__aexit__", return_value=None):
                    bg_service = BackgroundRefreshService(
                        feed_service, refresh_interval_minutes=1
                    )

                    # Start and let it run briefly
                    await bg_service.start()
                    await asyncio.sleep(0.1)

                    # Should still be running despite failed refresh
                    assert bg_service.is_running()

                    await bg_service.stop()

    async def test_exception_handling_in_loop(self):
        """Test exception handling in refresh loop."""
        feed_service = RSSFeedService()

        # Mock refresh to succeed initially, then raise exception in loop
        mock_refresh = AsyncMock(side_effect=[True, Exception("Network error")])

        with patch.object(feed_service, "refresh_feeds", mock_refresh):
            with patch.object(feed_service, "__aenter__", return_value=feed_service):
                with patch.object(feed_service, "__aexit__", return_value=None):
                    bg_service = BackgroundRefreshService(
                        feed_service, refresh_interval_minutes=1
                    )

                    # Start (initial refresh should succeed)
                    await bg_service.start()

                    # Let it run briefly to hit the exception in the loop
                    await asyncio.sleep(0.1)

                    # Should still be running despite exception in loop
                    assert bg_service.is_running()

                    await bg_service.stop()


async def run_async_tests():
    """Run async tests."""
    test = TestBackgroundRefreshIsolated()

    print("Testing start/stop functionality...")
    await test.test_start_and_stop_service()
    print("[PASS] Start/stop test passed")

    print("Testing refresh failure handling...")
    await test.test_refresh_failure_handling()
    print("[PASS] Refresh failure handling test passed")

    print("Testing exception handling...")
    await test.test_exception_handling_in_loop()
    print("[PASS] Exception handling test passed")


if __name__ == "__main__":
    # Run synchronous tests
    test = TestBackgroundRefreshIsolated()

    print("Running background service initialization test...")
    test.test_service_initialization()
    print("[PASS] Initialization test passed")

    print("Running status retrieval test...")
    test.test_get_status()
    print("[PASS] Status test passed")

    # Run async tests
    print("Running async tests...")
    asyncio.run(run_async_tests())

    print("\nAll Phase 2 background refresh tests passed! [SUCCESS]")
