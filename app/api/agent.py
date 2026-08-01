from fastapi import APIRouter, Depends
from langchain_openai import ChatOpenAI

from app.core.config import Settings, get_settings
from app.graph.workflow import create_agent_workflow
from app.schemas.request import AgentChatRequest
from app.schemas.response import AgentChatResponse
from app.services.agent_service import AgentService
from app.services.tool_service import ToolService, get_tool_service
from functools import lru_cache

from langgraph.checkpoint.memory import InMemorySaver
from app.rag.retriever import Retriever
from app.rag.vectordb import VectorDBService


router = APIRouter(prefix="/agent", tags=["agent"])
@lru_cache()
def get_agent_retriever() -> Retriever:
    vector_db_service = VectorDBService()
    return Retriever(vector_db_service)
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
        api_key=settings.openai_api_key,
        base_url=settings.openai_api_base,
    )
    workflow = create_agent_workflow(
        llm=llm,
        tool_service=tool_service,
        checkpointer=checkpointer,
        retriepointer=checkpointer,
        retriever=retriever
        )
    return AgentService(workflow)


@router.post("/chat", response_model=AgentChatResponse)
def chat_with_agent(
    request: AgentChatRequest,
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentChatResponse:
    return agent_service.chat(request.session_id, request.message,request.collection_name)

