from .analyze import router as analyze_router
from .health import router as health_router
from .system import router as system_router

__all__ = ["analyze_router", "health_router", "system_router"]
