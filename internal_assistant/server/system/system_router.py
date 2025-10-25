from typing import Annotated

from fastapi import APIRouter, Depends, Request
from injector import Injector
from pydantic import BaseModel, ConfigDict

from internal_assistant.server.chat.chat_service import ChatService
from internal_assistant.server.utils.auth import authenticated


def get_injector(request: Request) -> Injector:
    return request.state.injector


system_router = APIRouter(prefix="/v1/system", dependencies=[Depends(authenticated)])


class SystemInventoryResponse(BaseModel):
    total_documents: int
    unique_files: int
    files_list: list[str]
    documents_per_file: dict[str, int]
    model_config = ConfigDict(arbitrary_types_allowed=True)


@system_router.get(
    "/inventory",
    response_model=SystemInventoryResponse,
    tags=["System"],
    summary="Get system document inventory",
    description="Returns comprehensive information about ingested documents",
)
def get_system_inventory(
    injector: Annotated[Injector, Depends(get_injector)]
) -> SystemInventoryResponse:
    """Get current system document inventory.

    Returns information about:
    - Total number of document chunks
    - Number of unique files
    - List of available files
    - Document count per file
    """
    chat_service = injector.get(ChatService)
    inventory = chat_service.get_system_inventory()

    return SystemInventoryResponse(
        total_documents=inventory["total_documents"],
        unique_files=inventory["unique_files"],
        files_list=inventory["files_list"],
        documents_per_file=inventory["documents_per_file"],
    )


@system_router.get("/status", tags=["System"], summary="Get system status summary")
def get_system_status(injector: Annotated[Injector, Depends(get_injector)]) -> dict:
    """Get a quick system status summary."""
    chat_service = injector.get(ChatService)
    inventory = chat_service.get_system_inventory()

    if inventory["total_documents"] == 0:
        status = "empty"
        message = "No documents ingested"
    elif inventory["unique_files"] < 5:
        status = "light"
        message = f"Small knowledge base: {inventory['unique_files']} files"
    elif inventory["unique_files"] < 20:
        status = "moderate"
        message = f"Moderate knowledge base: {inventory['unique_files']} files"
    else:
        status = "extensive"
        message = f"Large knowledge base: {inventory['unique_files']} files"

    return {
        "status": status,
        "message": message,
        "summary": f"{inventory['unique_files']} Files, 📄 {inventory['total_documents']} Segments",
    }
