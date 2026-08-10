from typing import Any, NotRequired, TypedDict

from langgraph.graph import MessagesState

from app.domain.routing import (
    RequestIntent,
    Route,
    RoutingMode,
)


class Citation(TypedDict):
    """RAG 回答中的结构化引用。"""

    index: int
    source: str
    excerpt: str
    score: float | None


class RetrievedDocument(TypedDict):
    """检索层返回的文档。"""

    content: str
    metadata: dict[str, Any]
    score: float | None


class ProposedDecision(TypedDict):
    """Router 模型产生的原始请求分析建议。

    这份结果还没有经过确定性策略校验，
    不能直接用于选择业务工作流。
    """

    intent: RequestIntent
    route: Route
    needs_knowledge: bool
    needs_tools: bool
    requires_clarification: bool
    clarification_question: str | None
    rewritten_query: str | None
    reason: str


class ToolApprovalDecision(TypedDict):
    """用户对工具执行请求的审批结果。"""

    approved: bool
    feedback: str | None


class State(MessagesState):
    """Agent 工作流共享状态。"""

    session_id: str
    mode: NotRequired[RoutingMode]
    collection_name: NotRequired[str | None]

    # validate_decision 校验后的最终决策
    intent: NotRequired[RequestIntent]
    route: NotRequired[Route]
    route_reason: NotRequired[str]
    needs_knowledge: NotRequired[bool]
    needs_tools: NotRequired[bool]
    requires_clarification: NotRequired[bool]
    clarification_question: NotRequired[str | None]
    # Router 模型产生的原始建议
    proposed_decision: NotRequired[ProposedDecision]

    # RAG 检索状态
    rewritten_query: NotRequired[str | None]
    retrieval_query: NotRequired[str]
    retrieved_documents: NotRequired[list[RetrievedDocument]]
    has_relevant_documents: NotRequired[bool]
    citations: NotRequired[list[Citation]]

    # Human-in-the-loop 审批状态
    approval_decision: NotRequired[ToolApprovalDecision]
