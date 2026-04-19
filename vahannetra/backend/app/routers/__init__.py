from .analyze import router as analyze_router
from .health import router as health_router
from .results import router as results_router
from .system import router as system_router

__all__ = ["analyze_router", "health_router", "results_router", "system_router"]
