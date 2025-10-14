from fastapi import APIRouter, Depends, Request
import os
import re
from datetime import datetime
from typing import Annotated
from internal_assistant.settings.settings import settings


def get_injector(request: Request):
    return request.state.injector


try:
    import psutil
except ImportError:
    psutil = None

# This router exposes only non-sensitive status information for privacy
status_router = APIRouter(prefix="/status", tags=["Status"])

LOG_PATH = os.path.join("local_data", "logs", "pgpt_ingestion1.log")
MAX_LOG_LINES = 100


@status_router.get("/ingestion")
def ingestion_status():
    """Return ingestion and processing status: logs, last ingestion time, errors/warnings."""
    logs = []
    errors = []
    warnings = []
    last_ingestion_time = None
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[-MAX_LOG_LINES:]
            for line in lines:
                logs.append(line.strip())
                if "[ERROR]" in line:
                    errors.append(line.strip())
                if "[WARNING]" in line:
                    warnings.append(line.strip())
                # Find last ingestion time from info lines
                match = re.search(
                    r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\].*Finished ingestion",
                    line,
                )
                if match:
                    last_ingestion_time = match.group(1)
    return {
        "recent_logs": logs,
        "last_ingestion_time": last_ingestion_time,
        "recent_errors": errors,
        "recent_warnings": warnings,
        "pending_files": [],  # Not tracked in current implementation
    }


@status_router.get("/system")
def system_status():
    """Return system and model information: LLM/embedding model, vector store, disk space, RAM/CPU."""
    s = settings()
    # LLM info
    llm_info = {
        "mode": s.llm.mode,
    }
    if s.llm.mode == "llamacpp":
        llm_info["model_file"] = getattr(s.llamacpp, "llm_hf_model_file", None)
    elif s.llm.mode == "openai":
        llm_info["model"] = getattr(s.openai, "model", None)
    elif s.llm.mode == "ollama":
        llm_info["model"] = getattr(s.ollama, "llm_model", None)
    elif s.llm.mode == "gemini":
        llm_info["model"] = getattr(s.gemini, "model", None)
    elif s.llm.mode == "azopenai":
        llm_info["model"] = getattr(s.azopenai, "llm_model", None)
    elif s.llm.mode == "sagemaker":
        llm_info["endpoint"] = getattr(s.sagemaker, "llm_endpoint_name", None)

    # Embedding info
    embedding_info = {
        "mode": s.embedding.mode,
    }
    if s.embedding.mode == "huggingface":
        embedding_info["model_name"] = getattr(
            s.huggingface, "embedding_hf_model_name", None
        )
    elif s.embedding.mode == "openai":
        embedding_info["model"] = getattr(s.openai, "embedding_model", None)
    elif s.llm.mode == "ollama":
        embedding_info["model"] = getattr(s.ollama, "embedding_model", None)
    elif s.llm.mode == "gemini":
        embedding_info["model"] = getattr(s.gemini, "embedding_model", None)
    elif s.llm.mode == "azopenai":
        embedding_info["model"] = getattr(s.azopenai, "embedding_model", None)
    elif s.llm.mode == "sagemaker":
        embedding_info["endpoint"] = getattr(
            s.sagemaker, "embedding_endpoint_name", None
        )

    # Vector store info
    vectorstore_info = {
        "type": s.vectorstore.database,
    }

    # Disk, RAM, CPU info
    system_stats = {}
    try:
        if psutil:
            disk = psutil.disk_usage(os.getcwd())
            system_stats["disk_total_gb"] = round(disk.total / (1024**3), 2)
            system_stats["disk_used_gb"] = round(disk.used / (1024**3), 2)
            system_stats["disk_free_gb"] = round(disk.free / (1024**3), 2)
            system_stats["ram_total_gb"] = round(
                psutil.virtual_memory().total / (1024**3), 2
            )
            system_stats["ram_available_gb"] = round(
                psutil.virtual_memory().available / (1024**3), 2
            )
            system_stats["cpu_percent"] = psutil.cpu_percent(interval=0.5)
        else:
            st = os.statvfs(os.getcwd())
            system_stats["disk_total_gb"] = round(
                (st.f_blocks * st.f_frsize) / (1024**3), 2
            )
            system_stats["disk_free_gb"] = round(
                (st.f_bavail * st.f_frsize) / (1024**3), 2
            )
            # RAM/CPU not available without psutil
    except Exception:
        pass

    return {
        "llm": llm_info,
        "embedding": embedding_info,
        "vectorstore": vectorstore_info,
        "system_stats": system_stats,
    }


@status_router.get("/query_stats")
def query_stats():
    """Return query success/failure rates. Not yet tracked in current implementation."""
    return {
        "message": "Query success/failure rates are not currently tracked. Instrumentation required.",
        "success_rate": None,
        "failure_rate": None,
        "total_queries": None,
    }
