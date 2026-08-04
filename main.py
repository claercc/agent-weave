from fastapi import FastAPI

from app.api.router import router as api_router
from app.core.config import get_settings
from app.core.lifespan import lifespan


def create_app() -> FastAPI:
    """创建 FastAPI 应用。"""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "AI Agent backend with automatic routing, "
            "tool calling, and retrieval-augmented generation."
        ),
        lifespan=lifespan,
    )
    application.include_router(api_router)

    @application.get("/", tags=["system"])
    def root() -> dict[str, str]:
        return {
            "message": settings.app_name,
            "version": settings.app_version,
        }

    return application


app = create_app()
