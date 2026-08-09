from typing import Any, Self
from app.domain.routing import RoutingMode

from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    """聊天请求"""

    message: str = Field(description="用户消息", min_length=1)
    session_id: str = Field(description="会话ID", min_length=1)


class RAGQueryRequest(BaseModel):
    """RAG 查询请求"""

    query: str = Field(description="用户查询", min_length=1)
    collection_name: str = Field(description="索引集合名称", min_length=1)
    top_k: int = Field(description="返回文档数量", default=4)


class RAGIngestRequest(BaseModel):
    """RAG 索引请求"""

    texts: list[str] = Field(description="文档列表", min_length=1)
    collection_name: str = Field(description="索引集合名称", min_length=1)
    metadatas: dict[str, Any] = Field(description="文档元数据", default_factory=dict)


class AgentChatRequest(BaseModel):
    """智能体聊天请求"""

    session_id: str = Field(description="会话ID", min_length=1)
    message: str = Field(description="用户消息", min_length=1)
    collection_name: str | None = Field(
        default=None,
        description="预留的知识库集合名称；当前 Agent MVP 尚未接入 RAG",
    )
    mode: RoutingMode = Field(description="路由模式", default="auto")

    @model_validator(mode="after")
    def validate_rag_collection(self) -> Self:
        if self.mode == "rag" and self.collection_name is None:
            raise ValueError("RAG 模式下必须指定索引集合名称")
        return self


class AgentResumeRequest(BaseModel):
    """智能体恢复请求"""

    session_id: str = Field(description="会话ID", min_length=1)
    interrupt_id: str = Field(description="中断ID", min_length=1)
    approved: bool = Field(description="是否批准工具执行", default=False)
    feedback: str | None = Field(
        default=None, description="批准说明或拒绝原因", max_length=500
    )
