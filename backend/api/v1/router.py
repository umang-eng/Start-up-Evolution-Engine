from fastapi import APIRouter
from backend.app.health import router as health_router

api_router = APIRouter()

# Include health checks sub-router
api_router.include_router(health_router)

# Future endpoints will be mapped here:
# api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
# api_router.include_router(projects_router, prefix="/projects", tags=["Projects"])
# api_router.include_router(blueprints_router, prefix="/blueprints", tags=["Blueprints"])
