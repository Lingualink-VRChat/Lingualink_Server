from .audio_routes import router as audio_router
from .auth_routes import router as auth_router
from .health_routes import router as health_router
from .cache_routes import router as cache_router

__all__ = [
    "audio_router",
    "auth_router", 
    "health_router",
    "cache_router"
] 