"""FastAPI implementation of ChewyAttachment"""

from .router import router, health_router

__all__ = ["router", "health_router"]
