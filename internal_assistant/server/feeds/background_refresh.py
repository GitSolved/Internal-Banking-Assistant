"""Background RSS feed refresh service."""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from internal_assistant.server.feeds.feeds_service import RSSFeedService

logger = logging.getLogger(__name__)


class BackgroundRefreshService:
    """Service for managing background RSS feed refresh."""
    
    def __init__(self, feed_service: RSSFeedService, refresh_interval_minutes: int = 60):
        self.feed_service = feed_service
        self.refresh_interval = refresh_interval_minutes * 60  # Convert to seconds
        self._refresh_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._stop_event = asyncio.Event()
    
    async def start(self) -> None:
        """Start the background refresh service."""
        if self._is_running:
            logger.warning("Background refresh service is already running")
            return
        
        logger.info(f"Starting background RSS feed refresh (every {self.refresh_interval // 60} minutes)")
        self._is_running = True
        self._stop_event.clear()
        
        # Perform initial refresh
        async with self.feed_service:
            await self.feed_service.refresh_feeds()
        
        # Start background task
        self._refresh_task = asyncio.create_task(self._refresh_loop())
    
    async def stop(self) -> None:
        """Stop the background refresh service."""
        if not self._is_running:
            return
        
        logger.info("Stopping background RSS feed refresh")
        self._is_running = False
        self._stop_event.set()
        
        if self._refresh_task and not self._refresh_task.done():
            try:
                await asyncio.wait_for(self._refresh_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Background refresh task did not stop gracefully, cancelling")
                self._refresh_task.cancel()
                try:
                    await self._refresh_task
                except asyncio.CancelledError:
                    pass
    
    async def _refresh_loop(self) -> None:
        """Main refresh loop."""
        while self._is_running:
            try:
                # Wait for refresh interval or stop signal
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self.refresh_interval)
                    # If we get here, stop was requested
                    break
                except asyncio.TimeoutError:
                    # Normal refresh time
                    pass
                
                if not self._is_running:
                    break
                
                logger.info("Starting scheduled RSS feed refresh")
                
                # Perform refresh with session management
                async with self.feed_service:
                    success = await self.feed_service.refresh_feeds()
                
                if success:
                    cache_info = self.feed_service.get_cache_info()
                    logger.info(
                        f"Background refresh completed successfully. "
                        f"Total items: {cache_info['total_items']}"
                    )
                else:
                    logger.warning("Background refresh failed")
                    
            except Exception as e:
                logger.error(f"Error in background refresh loop: {e}")
                # Continue running even if one refresh fails
                await asyncio.sleep(60)  # Wait a minute before trying again
    
    def is_running(self) -> bool:
        """Check if the background service is running."""
        return self._is_running
    
    def get_status(self) -> dict:
        """Get status information about the background service."""
        cache_info = self.feed_service.get_cache_info()
        return {
            "is_running": self._is_running,
            "refresh_interval_minutes": self.refresh_interval // 60,
            "last_refresh": cache_info.get("last_refresh"),
            "total_items": cache_info.get("total_items", 0),
            "sources": cache_info.get("sources", {})
        }