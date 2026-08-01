from typing import Any, Literal, NotRequired, TypedDict

from langgraph.graph import MessagesState


Route = Literal["chat", "rag", "agent"]


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