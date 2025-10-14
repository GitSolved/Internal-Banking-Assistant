"""Router for RSS feeds API endpoints."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from injector import inject
from pydantic import BaseModel, Field, HttpUrl, ConfigDict

from internal_assistant.server.utils.auth import authenticated
from internal_assistant.server.feeds.feeds_service import RSSFeedService
from internal_assistant.server.feeds.background_refresh import BackgroundRefreshService
from internal_assistant.server.feeds.forum_directory_service import (
    ForumDirectoryService,
)
from internal_assistant.di import global_injector

logger = logging.getLogger(__name__)

feeds_router = APIRouter(prefix="/v1/feeds", dependencies=[Depends(authenticated)])


class FeedRequest(BaseModel):
    """Request model for feed filtering."""

    source: Optional[str] = Field(
        None, description="Filter by source (FINRA, Federal Reserve, FinCEN)"
    )
    days: Optional[int] = Field(None, description="Filter by days (7, 30, etc.)")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class FeedResponse(BaseModel):
    """Response model for feed data."""

    items: List[Dict[str, Any]]
    total_count: int
    sources: List[str]
    cache_info: Dict[str, Any]
    model_config = ConfigDict(arbitrary_types_allowed=True)


class AddFeedRequest(BaseModel):
    name: str
    url: HttpUrl
    category: str = "Custom"
    priority: int = 5
    color: str = "#6C757D"
    model_config = ConfigDict(arbitrary_types_allowed=True)


class FeedHealthResponse(BaseModel):
    total_sources: int
    categories: int
    last_refresh: Optional[str]
    cache_size: int
    sources: Dict[str, Any]
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ForumRequest(BaseModel):
    """Request model for forum filtering."""

    category: Optional[str] = Field(None, description="Filter by category")
    search: Optional[str] = Field(
        None, description="Search in forum names and descriptions"
    )
    limit: Optional[int] = Field(None, description="Maximum number of results")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ForumResponse(BaseModel):
    """Response model for forum directory."""

    forums: List[Dict[str, Any]]
    total_count: int
    categories: Dict[str, int]
    cache_info: Dict[str, Any]
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ForumHealthResponse(BaseModel):
    """Response model for forum service health."""

    service_healthy: bool
    cache_valid: bool
    source_reachable: bool
    forums_count: int
    last_refresh: Optional[str]
    error: Optional[str]
    model_config = ConfigDict(arbitrary_types_allowed=True)


@feeds_router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for feeds service."""
    return {"status": "healthy", "service": "feeds"}


@feeds_router.post("/refresh")
@inject
async def refresh_feeds(feed_service: RSSFeedService = Depends()) -> Dict[str, Any]:
    """Manually trigger feed refresh."""
    try:
        async with feed_service:
            success = await feed_service.refresh_feeds()

        if success:
            return {
                "status": "success",
                "message": "Feeds refreshed successfully",
                "cache_info": feed_service.get_cache_info(),
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to refresh feeds")

    except Exception as e:
        logger.error(f"Error refreshing feeds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@feeds_router.post("/list", response_model=FeedResponse)
@inject
async def get_feeds(
    feed_request: FeedRequest = FeedRequest(), feed_service: RSSFeedService = Depends()
) -> FeedResponse:
    """Get RSS feeds with optional filtering."""
    try:
        items = feed_service.get_feeds(
            source_filter=feed_request.source, days_filter=feed_request.days
        )

        return FeedResponse(
            items=items,
            total_count=len(items),
            sources=feed_service.get_available_sources(),
            cache_info=feed_service.get_cache_info(),
        )

    except Exception as e:
        logger.error(f"Error getting feeds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@feeds_router.get("/sources")
@inject
async def get_sources(feed_service: RSSFeedService = Depends()) -> Dict[str, List[str]]:
    """Get available feed sources."""
    try:
        return {"sources": feed_service.get_available_sources()}
    except Exception as e:
        logger.error(f"Error getting sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@feeds_router.post("/background/start")
@inject
async def start_background_refresh(
    feed_service: RSSFeedService = Depends(),
) -> Dict[str, Any]:
    """Start background RSS feed refresh service."""
    try:
        # Create background service (would be better as singleton in production)
        background_service = BackgroundRefreshService(
            feed_service, refresh_interval_minutes=60
        )

        if background_service.is_running():
            return {
                "status": "already_running",
                "message": "Background refresh service is already running",
            }

        await background_service.start()

        return {
            "status": "started",
            "message": "Background refresh service started",
            "refresh_interval_minutes": 60,
        }

    except Exception as e:
        logger.error(f"Error starting background refresh: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@feeds_router.get("/background/status")
@inject
async def get_background_status(
    feed_service: RSSFeedService = Depends(),
) -> Dict[str, Any]:
    """Get background refresh service status."""
    try:
        # In production, this would reference the same singleton instance
        background_service = BackgroundRefreshService(feed_service)
        return background_service.get_status()

    except Exception as e:
        logger.error(f"Error getting background status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@feeds_router.post("/feeds/add")
async def add_feed_source(
    request: AddFeedRequest,
    feeds_service: RSSFeedService = Depends(
        lambda: global_injector.get(RSSFeedService)
    ),
) -> Dict[str, Any]:
    """Add a new RSS feed source dynamically."""
    success = feeds_service.add_feed_source(
        name=request.name,
        url=str(request.url),
        category=request.category,
        priority=request.priority,
        color=request.color,
    )

    if success:
        return {"status": "success", "message": f"Added feed source: {request.name}"}
    else:
        raise HTTPException(
            status_code=400, detail=f"Failed to add feed source: {request.name}"
        )


@feeds_router.delete("/feeds/{feed_name}")
async def remove_feed_source(
    feed_name: str,
    feeds_service: RSSFeedService = Depends(
        lambda: global_injector.get(RSSFeedService)
    ),
) -> Dict[str, Any]:
    """Remove an RSS feed source."""
    success = feeds_service.remove_feed_source(feed_name)

    if success:
        return {"status": "success", "message": f"Removed feed source: {feed_name}"}
    else:
        raise HTTPException(
            status_code=404, detail=f"Feed source not found: {feed_name}"
        )


@feeds_router.get("/feeds/health", response_model=FeedHealthResponse)
async def get_feed_health(
    feeds_service: RSSFeedService = Depends(
        lambda: global_injector.get(RSSFeedService)
    ),
) -> FeedHealthResponse:
    """Get health status of all RSS feed sources."""
    return feeds_service.get_feed_health_status()


# ========================================
# FORUM DIRECTORY ENDPOINTS
# ========================================


@feeds_router.post("/forums/refresh")
async def refresh_forum_directory(
    forum_service: ForumDirectoryService = Depends(
        lambda: global_injector.get(ForumDirectoryService)
    ),
) -> Dict[str, Any]:
    """Manually refresh the forum directory from tor.taxi."""
    try:
        async with forum_service:
            success = await forum_service.fetch_forum_directory()

        if success:
            cache_info = forum_service.get_cache_info()
            return {
                "status": "success",
                "message": f"Forum directory refreshed successfully. Found {cache_info['total_forums']} forums.",
                "cache_info": cache_info,
            }
        else:
            raise HTTPException(
                status_code=500, detail="Failed to refresh forum directory"
            )

    except Exception as e:
        logger.error(f"Error refreshing forum directory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@feeds_router.post("/forums/directory", response_model=ForumResponse)
async def get_forum_directory(
    forum_request: ForumRequest = ForumRequest(),
    forum_service: ForumDirectoryService = Depends(
        lambda: global_injector.get(ForumDirectoryService)
    ),
) -> ForumResponse:
    """Get forum directory with optional filtering."""
    try:
        # Ensure we have fresh data
        async with forum_service:
            await forum_service.refresh_if_needed()

        # Get forums with filters
        forums = forum_service.get_forums(
            category_filter=forum_request.category,
            search_query=forum_request.search,
            limit=forum_request.limit,
        )

        return ForumResponse(
            forums=forums,
            total_count=len(forums),
            categories=forum_service.get_forum_categories(),
            cache_info=forum_service.get_cache_info(),
        )

    except Exception as e:
        logger.error(f"Error getting forum directory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@feeds_router.get("/forums/search")
async def search_forums(
    query: str,
    max_results: int = 20,
    forum_service: ForumDirectoryService = Depends(
        lambda: global_injector.get(ForumDirectoryService)
    ),
) -> Dict[str, Any]:
    """Search forums by name, description, or category."""
    try:
        # Ensure we have fresh data
        async with forum_service:
            await forum_service.refresh_if_needed()

        results = forum_service.search_forums(query, max_results)

        return {
            "query": query,
            "results": results,
            "total_results": len(results),
            "cache_info": forum_service.get_cache_info(),
        }

    except Exception as e:
        logger.error(f"Error searching forums: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@feeds_router.get("/forums/categories")
async def get_forum_categories(
    forum_service: ForumDirectoryService = Depends(
        lambda: global_injector.get(ForumDirectoryService)
    ),
) -> Dict[str, Any]:
    """Get available forum categories."""
    try:
        async with forum_service:
            await forum_service.refresh_if_needed()

        return {
            "categories": forum_service.get_forum_categories(),
            "cache_info": forum_service.get_cache_info(),
        }

    except Exception as e:
        logger.error(f"Error getting forum categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@feeds_router.get("/forums/health", response_model=ForumHealthResponse)
async def get_forum_health(
    forum_service: ForumDirectoryService = Depends(
        lambda: global_injector.get(ForumDirectoryService)
    ),
) -> ForumHealthResponse:
    """Get health status of forum directory service."""
    try:
        async with forum_service:
            health_status = await forum_service.health_check()
        return ForumHealthResponse(**health_status)

    except Exception as e:
        logger.error(f"Error checking forum health: {e}")
        return ForumHealthResponse(
            service_healthy=False,
            cache_valid=False,
            source_reachable=False,
            forums_count=0,
            last_refresh=None,
            error=str(e),
        )


@feeds_router.get("/forums/status")
async def get_forum_status(
    forum_service: ForumDirectoryService = Depends(
        lambda: global_injector.get(ForumDirectoryService)
    ),
) -> Dict[str, Any]:
    """Get comprehensive forum service status."""
    try:
        return forum_service.get_service_status()

    except Exception as e:
        logger.error(f"Error getting forum status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
