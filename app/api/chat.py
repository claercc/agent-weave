from fastapi import APIRouter, Depends
from openai import OpenAI
from app.core.config import Settings, get_settings
from app.core.openai_client import get_openai_client
from app.repositories.memory_repository import MemoryConversationRepository
from app.services.tool_service import ToolService, get_tool_service
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.schemas.request import ChatRequest

# stream chat
from collections.abc import Iterator

router = APIRouter(prefix="/chat", tags=["chat"])
repository = MemoryConversationRepository()


def get_chat_service(
    settings: Settings = Depends(get_settings),
    client: OpenAI = Depends(get_openai_client),
) -> ChatService:

    conversation_service = ConversationService(repository)
    tool_service: ToolService = get_tool_service()
    return ChatService(
        client=client,
        tool_service=tool_service,
        settings=settings,
        conversation_service=conversation_service,
    )


@router.post("")
def chat(
    request: ChatRequest, chat_service: ChatService = Depends(get_chat_service)
) -> dict[str, str]:
    answer = chat_service.chat(request.session_id, request.message)
    return {"answer": answer}


@router.post("/stream")
def stream_chat(
    request: ChatRequest, chat_service: ChatService = Depends(get_chat_service)
) -> Iterator[str]:
    return chat_service.stream_chat(request.session_id, request.message)


@router.post("/tools")
def tools(
    request: ChatRequest, chat_service: ChatService = Depends(get_chat_service)
) -> str:
    return chat_service.chat_with_tool_calling(request.session_id, request.message)
