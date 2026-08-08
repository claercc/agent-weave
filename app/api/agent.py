from fastapi import APIRouter, Depends
from langchain_openai import ChatOpenAI

from app.core.config import Settings, get_settings
from app.graph.workflow import create_agent_workflow
from app.rag.embedding import EmbeddingService
from app.schemas.request import AgentChatRequest, AgentResumeRequest
from app.schemas.response import AgentChatResponse
from app.services.agent_service import AgentService
from app.services.tool_service import ToolService, get_tool_service
from functools import lru_cache

from langgraph.checkpoint.memory import InMemorySaver
from app.rag.retriever import Retriever
from app.rag.vectordb import VectorDBService
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/agent", tags=["agent"])


@lru_cache()
def get_agent_retriever() -> Retriever:
    settings = get_settings()
    vector_db_service = VectorDBService()
    embedding_service = EmbeddingService(settings)
    return Retriever(vector_db_service, embedding_service)


@lru_cache()
def get_agent_checkpointer() -> InMemorySaver:
    return InMemorySaver()


def get_agent_service(
    settings: Settings = Depends(get_settings),
    tool_service: ToolService = Depends(get_tool_service),
    checkpointer: InMemorySaver = Depends(get_agent_checkpointer),
    retriever: Retriever = Depends(get_agent_retriever),
) -> AgentService:
    llm = ChatOpenAI(
        model=settings.model_name,
        api_key=settings.require_openai_api_key(),
        base_url=settings.openai_api_base,
    )
    workflow = create_agent_workflow(
        llm=llm,
        tool_service=tool_service,
        checkpointer=checkpointer,
        retriever=retriever,
    )
    return AgentService(workflow)


@router.post("/chat", response_model=AgentChatResponse)
def chat_with_agent(
    request: AgentChatRequest,
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentChatResponse:
    return agent_service.chat(
        session_id=request.session_id,
        message=request.message,
        collection_name=request.collection_name,
        mode=request.mode,
    )

@router.post("/chat/stream", response_class=StreamingResponse)
def chat_with_agent_stream(
    request: AgentChatRequest,
    agent_service: AgentService = Depends(get_agent_service),
) -> StreamingResponse:
    return StreamingResponse(
        agent_service.stream_chat(
        session_id=request.session_id,
        message=request.message,
        collection_name=request.collection_name,
        mode=request.mode,
        ),
        media_type="text/event-stream",
        # 关闭缓存，确保实时性
        headers={"Cache-Control": "no-cache",
        # 告诉客户端和代理服务器不要缓存事件流
        # 告诉 Nginx 等反向代理不要攒够一批数据再发送，否则看起来会像非流式响应
                 "X-Accel-Buffering": "no"},
    )

@router.post(
    "/chat/resume/stream",
    response_class=StreamingResponse,
)
def resume_agent_stream(
    request: AgentResumeRequest,
    agent_service: AgentService = Depends(
        get_agent_service
    ),
) -> StreamingResponse:
    """根据用户审批结果恢复 Agent 工作流。"""

    return StreamingResponse(
        agent_service.resume_chat(
            session_id=request.session_id,
            interrupt_id=request.interrupt_id,
            approved=request.approved,
            feedback=request.feedback,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )