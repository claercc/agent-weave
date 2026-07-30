from fastapi import APIRouter, Depends
from langchain_openai import ChatOpenAI

from app.core.config import Settings, get_settings
from app.graph.workflow import create_agent_workflow
from app.schemas.request import AgentChatRequest
from app.schemas.response import AgentChatResponse
from app.services.agent_service import AgentService
from app.services.tool_service import ToolService, get_tool_service


router = APIRouter(prefix="/agent", tags=["agent"])


def get_agent_service(
    settings: Settings = Depends(get_settings),
    tool_service: ToolService = Depends(get_tool_service),
) -> AgentService:
    llm = ChatOpenAI(
        model=settings.model_name,
        api_key=settings.openai_api_key,
        base_url=settings.openai_api_base,
    )
    workflow = create_agent_workflow(llm, tool_service)
    return AgentService(workflow)


@router.post("/chat", response_model=AgentChatResponse)
def chat_with_agent(
    request: AgentChatRequest,
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentChatResponse:
    return agent_service.chat(request.session_id, request.message)
