from fastapi import FastAPI
from app.api.chat import router as chat_router
from app.core.config import Settings,get_settings
from app.services.tool_service import init_tools
from app.api.router import router as api_router



settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    """应用启动时执行的初始化"""
    init_tools()

@app.get("/")
def root():
    return {"message": "Hello World", "version": settings.app_version}