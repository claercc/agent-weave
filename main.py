from fastapi import FastAPI
from app.core.config import get_settings
from app.services.tool_service import init_tools
from app.api.router import router as api_router
from app.core.lifespan import lifespan

settings = get_settings()
def create_app() -> FastAPI:
    """创建FastAPI应用"""

    app = FastAPI(title=settings.app_name, version=settings.app_version,
                  description=(
                    "AI Agent backend with automatic routing, "
                    "tool calling, and retrieval-augmented generation."
                  ),
                  lifespan=lifespan)
    app.include_router(api_router)
    @app.get("/",tags=["system"])
    def root() -> dict[str, str]:
        return {"message": "Hello World", "version": settings.app_version}
    return app


app = create_app()

@app.on_event("startup")
async def startup_event() -> None:
    """应用启动时执行的初始化"""
    init_tools()


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Hello World", "version": settings.app_version}
