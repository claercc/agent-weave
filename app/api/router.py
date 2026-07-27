from fastapi import APIRouter,Depends
from app.api.chat import router as chat_router
from app.api.rag import router as rag_router

router = APIRouter(prefix="/api",tags=["api"])
router.include_router(chat_router,prefix="/chat")
router.include_router(rag_router,prefix="/rag")