from typing import Any, NotRequired, TypedDict

from langgraph.graph import MessagesState
from app.domain.routing import Route, RoutingMode

class Citation(TypedDict):
    """一个结构化的引用返回了一个RAG答案"""
    index: int
    source: str
    excerpt: str #摘录
    score: float | None

class RetrievedDocument(TypedDict):
    """检索层返回的文档"""

    content: str
    metadata: dict[str, Any]
    score: float | None


class State(MessagesState):
    """代理工作流的共享状态"""

    session_id: str
    collection_name: NotRequired[str | None]
    route: NotRequired[Route]
    # 检索查询
    retrieval_query: NotRequired[str]
    # 检索文档
    retrieved_documents: NotRequired[list[RetrievedDocument]]
    # 已检索文档
    has_relevant_documents: NotRequired[bool]
    citations: NotRequired[list[Citation]]
    mode: NotRequired[RoutingMode]
    # "route_reason": "Explicit rag mode was requested."
    route_reason: NotRequired[str]
