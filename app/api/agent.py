from fastapi import (
    APIRouter,
    Depends,
    Request,
)
from fastapi.responses import StreamingResponse

from app.schemas.request import (
    AgentChatRequest,
    AgentResumeRequest,
)
from app.schemas.response import AgentChatResponse
from app.services.agent_service import AgentService

router = APIRouter(
    prefix="/agent",
    tags=["agent"],
)

async def get_agent_service(
    request: Request,
) -> AgentService:
    """从 FastAPI 应用状态中取得 AgentService。

    AgentService 已经在 lifespan 启动阶段创建，
    当前依赖不会重新创建模型、Retriever 或 Workflow。
    """

    agent_service = getattr(
        request.app.state,
        "agent_service",
        None,
    )

    if not isinstance(
        agent_service,
        AgentService,
    ):
        raise RuntimeError(
            "AgentService 尚未初始化，"
            "请确认 FastAPI lifespan 已正常执行"
        )

    return agent_service


@router.post(
    "/chat",
    response_model=AgentChatResponse,
)
async def chat_with_agent(
    request: AgentChatRequest,
    agent_service: AgentService = Depends(
        get_agent_service
    ),
) -> AgentChatResponse:
    """执行一次非流式 Agent 请求。"""

    return await agent_service.chat(
        session_id=request.session_id,
        message=request.message,
        collection_name=(
            request.collection_name
        ),
        mode=request.mode,
    )


@router.post(
    "/chat/stream",
    response_class=StreamingResponse,
)
async def chat_with_agent_stream(
    request: AgentChatRequest,
    agent_service: AgentService = Depends(
        get_agent_service
    ),
) -> StreamingResponse:
    """启动新的 Agent SSE 工作流。"""

    return StreamingResponse(
        agent_service.stream_chat(
            session_id=request.session_id,
            message=request.message,
            collection_name=(
                request.collection_name
            ),
            mode=request.mode,
        ),
        media_type="text/event-stream",
        headers={
            # 禁止浏览器和中间代理缓存 SSE。
            "Cache-Control": "no-cache",

            # 禁止 Nginx 等代理积攒响应块，
            # 保证 token 和执行事件实时到达前端。
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/chat/resume/stream",
    response_class=StreamingResponse,
)
async def resume_agent_stream(
    request: AgentResumeRequest,
    agent_service: AgentService = Depends(
        get_agent_service
    ),
) -> StreamingResponse:
    """根据人工审批结果恢复 Agent 工作流。"""

    return StreamingResponse(
        agent_service.resume_chat(
            session_id=request.session_id,
            interrupt_id=(
                request.interrupt_id
            ),
            approved=request.approved,
            feedback=request.feedback,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )