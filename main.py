from fastapi import FastAPI
import uvicorn

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
            "具备自动路由功能的AI代理后端, " "支持工具调用, 以及基于检索增强的生成能力."
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


def main() -> None:
    """通过已安装的“start”命令运行应用程序"""
    uvicorn.run("main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
