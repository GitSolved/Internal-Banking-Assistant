"""Simple router for forum directory API endpoints."""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from internal_assistant.server.utils.auth import authenticated
from internal_assistant.server.feeds.simple_forum_service import SimpleForumDirectoryService
from internal_assistant.di import global_injector

logger = logging.getLogger(__name__)

simple_forum_router = APIRouter(prefix="/v1/feeds/forums", dependencies=[Depends(authenticated)])


class ForumDirectoryResponse(BaseModel):
    """Response model for forum directory."""
    forums: List[Dict[str, str]]
    total_count: int
    cache_info: Dict[str, Any]
    model_config = ConfigDict(arbitrary_types_allowed=True)


@simple_forum_router.get("/directory", response_model=ForumDirectoryResponse)
async def get_forum_directory(
    forum_service: SimpleForumDirectoryService = Depends(lambda: global_injector.get(SimpleForumDirectoryService))
) -> ForumDirectoryResponse:
    """Get forum directory with forum names and onion links."""
    try:
        # Ensure we have fresh data
        async with forum_service:
            await forum_service.refresh_if_needed()
        
        forums = forum_service.get_forums()
        
        return ForumDirectoryResponse(
            forums=forums,
            total_count=len(forums),
            cache_info=forum_service.get_cache_info()
        )
        
    except Exception as e:
        logger.error(f"Error getting forum directory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@simple_forum_router.post("/refresh")
async def refresh_forum_directory(
    forum_service: SimpleForumDirectoryService = Depends(lambda: global_injector.get(SimpleForumDirectoryService))
) -> Dict[str, Any]:
    """Manually refresh the forum directory."""
    try:
        async with forum_service:
            success = await forum_service.fetch_forum_directory()
        
        if success:
            cache_info = forum_service.get_cache_info()
            return {
                "status": "success",
                "message": f"Forum directory refreshed. Found {cache_info['total_forums']} forums.",
                "cache_info": cache_info
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to refresh forum directory")
            
    except Exception as e:
        logger.error(f"Error refreshing forum directory: {e}")
        raise HTTPException(status_code=500, detail=str(e))