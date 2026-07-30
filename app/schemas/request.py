from typing import Any

from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(description="用户消息",min_length=1)
    session_id: str = Field(description="会话ID",min_length=1)

class RAGQueryRequest(BaseModel):
    """RAG 查询请求"""
    query: str = Field(description="用户查询",min_length=1)
    collection_name: str = Field(description="索引集合名称",min_length=1)
    top_k: int = Field(description="返回文档数量",default=4)

class RAGIngestRequest(BaseModel):
    """RAG 索引请求"""
    texts: list[str] = Field(description="文档列表",min_items=1)
    collection_name: str = Field(description="索引集合名称",min_length=1)
    metadatas: dict[str, Any] = Field(description="文档元数据",default={})

class AgentChatRequest(BaseModel):
    """智能体聊天请求"""
    session_id: str = Field(description="会话ID",min_length=1)
    message: str = Field(description="用户消息",min_length=1)
    collection_name: str | None = Field(
        default=None,
        description="预留的知识库集合名称；当前 Agent MVP 尚未接入 RAG",
    )
