"""Forum directory service for managing tor.taxi forum links."""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

from internal_assistant.server.feeds.forum_parser import ForumDirectoryParser, ForumLink

logger = logging.getLogger(__name__)


class ForumDirectoryService:
    """Service for managing forum directory from tor.taxi."""
    
    # Source configuration
    TOR_TAXI_URL = "https://tor.taxi/"
    CACHE_DURATION_HOURS = 12
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 2
    
    def __init__(self, cache_duration_hours: int = 12):
        self.cache_duration_hours = cache_duration_hours
        self.forums_cache: List[ForumLink] = []
        self.last_refresh: Optional[datetime] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self.parser = ForumDirectoryParser()
        self._refresh_lock = asyncio.Lock()
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT),
            headers={
                'User-Agent': 'Internal Assistant Forum Directory Service/1.0'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
    
    async def fetch_forum_directory(self) -> bool:
        """
        Fetch and parse forum directory from tor.taxi.
        
        Returns:
            True if successful, False otherwise
        """
        if not self._session:
            raise RuntimeError("Service must be used within async context manager")
        
        async with self._refresh_lock:
            try:
                logger.info(f"Fetching forum directory from {self.TOR_TAXI_URL}")
                
                # Attempt to fetch with retries
                for attempt in range(self.MAX_RETRIES + 1):
                    try:
                        async with self._session.get(self.TOR_TAXI_URL) as response:
                            if response.status == 200:
                                html_content = await response.text()
                                break
                            else:
                                logger.warning(f"HTTP {response.status} from tor.taxi (attempt {attempt + 1})")
                                
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout fetching tor.taxi (attempt {attempt + 1})")
                        
                    except Exception as e:
                        logger.warning(f"Error fetching tor.taxi (attempt {attempt + 1}): {e}")
                    
                    if attempt < self.MAX_RETRIES:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to fetch tor.taxi after {self.MAX_RETRIES + 1} attempts")
                    return False
                
                # Parse the HTML content
                forums = self.parser.parse_forum_directory(html_content)
                
                # Update cache
                self.forums_cache = forums
                self.last_refresh = datetime.now(timezone.utc)
                
                logger.info(f"Successfully parsed {len(forums)} forum links")
                return True
                
            except Exception as e:
                logger.error(f"Error in fetch_forum_directory: {e}")
                return False
    
    def get_forums(
        self,
        category_filter: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get forums with optional filtering.
        
        Args:
            category_filter: Filter by category
            search_query: Search in forum names and descriptions
            limit: Maximum number of results
            
        Returns:
            List of forum dictionaries
        """
        forums = self.forums_cache.copy()
        
        # Apply category filter
        if category_filter:
            forums = [f for f in forums if f.category.lower() == category_filter.lower()]
        
        # Apply search filter
        if search_query:
            query_lower = search_query.lower()
            forums = [
                f for f in forums
                if query_lower in f.name.lower() or query_lower in f.description.lower()
            ]
        
        # Apply limit
        if limit and limit > 0:
            forums = forums[:limit]
        
        # Convert to dictionaries and add metadata
        return [
            {
                **forum.to_dict(),
                "id": f"forum_{i}",
                "last_updated": self.last_refresh.isoformat() if self.last_refresh else None
            }
            for i, forum in enumerate(forums)
        ]
    
    def get_forum_categories(self) -> Dict[str, int]:
        """Get available forum categories with counts."""
        categories = {}
        for forum in self.forums_cache:
            categories[forum.category] = categories.get(forum.category, 0) + 1
        return categories
    
    def is_cache_valid(self) -> bool:
        """Check if the current cache is still valid."""
        if not self.last_refresh or not self.forums_cache:
            return False
        
        cache_age = datetime.now(timezone.utc) - self.last_refresh
        return cache_age < timedelta(hours=self.cache_duration_hours)
    
    async def refresh_if_needed(self) -> bool:
        """Refresh the forum directory if cache is invalid."""
        if not self.is_cache_valid():
            return await self.fetch_forum_directory()
        return True
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache status information."""
        cache_age_hours = None
        if self.last_refresh:
            cache_age = datetime.now(timezone.utc) - self.last_refresh
            cache_age_hours = cache_age.total_seconds() / 3600
        
        return {
            "total_forums": len(self.forums_cache),
            "categories": len(self.get_forum_categories()),
            "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None,
            "cache_age_hours": cache_age_hours,
            "cache_valid": self.is_cache_valid(),
            "source_url": self.TOR_TAXI_URL,
            "cache_duration_hours": self.cache_duration_hours
        }
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive service status."""
        parsing_stats = self.parser.get_parsing_stats() if self.forums_cache else {}
        
        return {
            "service": "forum_directory",
            "status": "active" if self.forums_cache else "empty",
            "cache_info": self.get_cache_info(),
            "categories": self.get_forum_categories(),
            "parsing_stats": parsing_stats,
            "safety_features": {
                "content_filtering": True,
                "forums_only": True,
                "excluded_keywords": list(self.parser.EXCLUDED_KEYWORDS),
                "required_indicators": list(self.parser.FORUM_INDICATORS)
            }
        }
    
    def search_forums(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search forums by name, description, or category.
        
        Args:
            query: Search term
            max_results: Maximum number of results to return
            
        Returns:
            List of matching forum dictionaries with relevance scores
        """
        if not query or not self.forums_cache:
            return []
        
        query_lower = query.lower()
        results = []
        
        for forum in self.forums_cache:
            relevance_score = 0
            
            # Exact name match gets highest score
            if query_lower == forum.name.lower():
                relevance_score = 100
            # Name contains query
            elif query_lower in forum.name.lower():
                relevance_score = 80
            # Description contains query
            elif query_lower in forum.description.lower():
                relevance_score = 60
            # Category contains query
            elif query_lower in forum.category.lower():
                relevance_score = 40
            
            if relevance_score > 0:
                forum_dict = forum.to_dict()
                forum_dict["relevance_score"] = relevance_score
                forum_dict["last_updated"] = self.last_refresh.isoformat() if self.last_refresh else None
                results.append(forum_dict)
        
        # Sort by relevance score (descending) and return top results
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:max_results]
    
    def get_forum_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get forum information by URL."""
        for forum in self.forums_cache:
            if forum.url == url:
                return forum.to_dict()
        return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the service."""
        try:
            # Check if we can reach tor.taxi
            can_reach_source = False
            if self._session:
                try:
                    async with self._session.get(self.TOR_TAXI_URL, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        can_reach_source = response.status == 200
                except:
                    pass
            
            return {
                "service_healthy": True,
                "cache_valid": self.is_cache_valid(),
                "source_reachable": can_reach_source,
                "forums_count": len(self.forums_cache),
                "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None,
                "error": None
            }
            
        except Exception as e:
            return {
                "service_healthy": False,
                "cache_valid": False,
                "source_reachable": False,
                "forums_count": 0,
                "last_refresh": None,
                "error": str(e)
            }