from fastapi import APIRouter

from app.api.agent import router as agent_router
from app.api.chat import router as chat_router
from app.api.rag import router as rag_router
from app.api.health import router as health_router

router = APIRouter(prefix="/api")
router.include_router(agent_router)
router.include_router(chat_router)
router.include_router(rag_router)
router.include_router(health_router)
