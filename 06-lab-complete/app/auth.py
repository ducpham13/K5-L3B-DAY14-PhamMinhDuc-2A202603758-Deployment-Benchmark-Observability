"""
API Key authentication (tiêu chí 6).
"""
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from app.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(key: str = Depends(_api_key_header)) -> str:
    """Dependency cho FastAPI — dùng trong /ask: Depends(verify_api_key)."""
    if not key or key != settings.agent_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return key
