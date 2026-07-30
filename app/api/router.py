from fastapi import APIRouter

from app.api.agent import router as agent_router
from app.api.chat import router as chat_router
from app.api.rag import router as rag_router

router = APIRouter(prefix="/api",tags=["api"])
router.include_router(agent_router)
router.include_router(chat_router)
router.include_router(rag_router)
