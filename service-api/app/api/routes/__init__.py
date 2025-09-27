from .auth import router as auth_router
from .health import router as health_router
from .lpa import router as lpa_router
from .users import router as users_router

ROUTERS = [auth_router, health_router, users_router, lpa_router]

__all__ = ["auth_router", "health_router", "users_router", "lpa_router", "ROUTERS"]
