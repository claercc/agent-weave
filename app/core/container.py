import logging
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from openai import OpenAI

from app.core.config import Settings
from app.graph.workflow import (
    create_agent_workflow,
)
from app.rag.embedding import EmbeddingService
from app.rag.retriever import Retriever
from app.rag.vectordb import VectorDBService
from app.services.agent_service import AgentService
from app.services.rag_service import RAGService
from app.services.tool_service import (
    get_tool_service,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ApplicationServices:
    """应用生命周期内共享的服务。"""

    agent_service: AgentService
    rag_service: RAGService


def build_agent_service(
    settings: Settings,
    *,
    embedding_service: EmbeddingService | None = None,
    vector_db_service: VectorDBService | None = None,
) -> AgentService:
    """创建应用级 AgentService。

    该函数是 Agent 相关依赖的统一组装入口，
    只应该在 FastAPI 启动阶段调用一次。

    创建顺序：
        1. 创建聊天模型；
        2. 创建 Embedding 和向量数据库服务；
        3. 创建 Retriever；
        4. 创建会话 Checkpointer；
        5. 编译 LangGraph Workflow；
        6. 创建 AgentService。

    返回：
        在整个应用生命周期内复用的 AgentService。
    """

    # ChatOpenAI 只负责配置模型客户端，
    # 创建对象时不会立即发送网络请求。
    llm = ChatOpenAI(
        model=settings.model_name,
        api_key=(settings.require_openai_api_key()),
        base_url=settings.openai_api_base,
        timeout=settings.model_request_timeout_seconds,
        max_retries=settings.model_max_retries,
    )

    # EmbeddingService 内部使用缓存加载 BGE 模型。
    # 此处创建服务不会立即执行模型推理。
    effective_embedding_service = embedding_service or EmbeddingService(settings)

    # VectorDBService 创建 Chroma 本地客户端。
    effective_vector_db_service = vector_db_service or VectorDBService()

    # Retriever 统一负责：
    # 查询向量化 → Chroma 检索。
    retriever = Retriever(
        effective_vector_db_service,
        effective_embedding_service,
    )

    # 当前使用内存 Checkpointer。
    # 它在应用存活期间保存会话和审批中断状态。
    checkpointer = InMemorySaver()

    tool_service = get_tool_service()

    # 主图和两个子图只在这里构建并编译一次。
    workflow = create_agent_workflow(
        llm=llm,
        tool_service=tool_service,
        checkpointer=checkpointer,
        retriever=retriever,
    )

    logger.info(
        "Agent Workflow 初始化完成，模型：%s，" "Embedding：%s",
        settings.model_name,
        effective_embedding_service.model_name,
    )

    return AgentService(workflow)


def build_application_services(
    settings: Settings,
) -> ApplicationServices:
    """构建共享 Embedding 和 Chroma 客户端的应用服务。"""

    embedding_service = EmbeddingService(settings)
    vector_db_service = VectorDBService()

    agent_service = build_agent_service(
        settings,
        embedding_service=embedding_service,
        vector_db_service=vector_db_service,
    )

    model_client = OpenAI(
        api_key=settings.require_openai_api_key().get_secret_value(),
        base_url=settings.openai_api_base,
        timeout=settings.model_request_timeout_seconds,
        max_retries=settings.model_max_retries,
    )

    rag_service = RAGService(
        client=model_client,
        settings=settings,
        embedding_service=embedding_service,
        vector_db_service=vector_db_service,
    )

    return ApplicationServices(
        agent_service=agent_service,
        rag_service=rag_service,
    )
