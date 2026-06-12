from fastapi import APIRouter
from backend.app.health import router as health_router
from backend.api.v1.auth import router as auth_router
from backend.api.v1.streams import router as streams_router
from backend.api.v1.projects import router as projects_router
from backend.api.v1.generator import router as generator_router
from backend.api.v1.blueprints import router as blueprints_router

api_router = APIRouter()

# Mount sub-routers
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(streams_router)
api_router.include_router(projects_router)
api_router.include_router(generator_router)
api_router.include_router(blueprints_router)
