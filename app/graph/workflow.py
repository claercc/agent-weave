from functools import partial
from typing import Any

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    agent_node,
    clarify_request,
    route_request,
    select_request_route,
    validate_decision,
)
from app.graph.state import State
from app.graph.subgraphs.rag import (
    create_rag_subgraph,
)
from app.graph.subgraphs.tool_agent import (
    create_tool_agent_subgraph,
)
from app.rag.retriever import Retriever
from app.services.tool_service import ToolService


def create_agent_workflow(
    llm: ChatOpenAI,
    tool_service: ToolService,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
    retriever: Retriever | None = None,
    router_llm: ChatOpenAI | None = None,
) -> Any:
    """构建并编译顶层 Agent 工作流。

    顶层工作流只负责：
        1. 分析用户请求；
        2. 选择业务分支；
        3. 调用 Chat、RAG 或 Tool Agent；
        4. 管理会话 checkpoint。

    RAG 和工具 Agent 的内部执行过程分别由子图负责。
    """

    builder = StateGraph(State)

    # 默认复用主聊天模型进行请求分析。
    # 未来可以注入更便宜、更快速的独立 Router 模型。
    effective_router_llm = router_llm or llm

    # 工具 Agent 无论是否启用 RAG 都可以独立工作。
    tool_agent_subgraph = create_tool_agent_subgraph(
        llm=llm,
        tool_service=tool_service,
    )

    builder.add_node(
        "tool_agent",
        tool_agent_subgraph,
    )

    if retriever is None:
        # 精简模式主要用于独立工具 Agent 测试。
        # 没有 Retriever 时不构建 Router 和 RAG 分支。
        builder.add_edge(
            START,
            "tool_agent",
        )
    else:
        rag_subgraph = create_rag_subgraph(
            llm=llm,
            retriever=retriever,
            min_score=0.4,
        )

        # Router 负责产生结构化请求分析。
        builder.add_node(
            "router",
            partial(
                route_request,
                router_llm=effective_router_llm,
            ),
        )

        builder.add_node(
            "validate_decision",
            validate_decision,
        )

        # 信息不足时返回确定性的澄清问题。
        builder.add_node(
            "clarify",
            clarify_request,
        )

        # 普通聊天复用 agent_node，但不绑定工具。
        builder.add_node(
            "chat",
            partial(
                agent_node,
                llm=llm,
                tools=[],
            ),
        )

        # 顶层工作流只把 RAG 视为一个完整业务能力。
        builder.add_node(
            "rag",
            rag_subgraph,
        )

        builder.add_edge(START, "router")
        builder.add_edge("router", "validate_decision")

        # Router 的结构化结果决定进入哪个业务分支。
        builder.add_conditional_edges(
            "validate_decision",
            select_request_route,
            {
                "clarify": "clarify",
                "chat": "chat",
                "rag": "rag",
                "agent": "tool_agent",
            },
        )

        builder.add_edge("clarify", END)
        builder.add_edge("chat", END)
        builder.add_edge("rag", END)

    # Tool Agent 子图完成后，本轮主工作流结束。
    builder.add_edge("tool_agent", END)

    # 主图 checkpointer 同时覆盖两个子图，
    # 用于会话记忆和人工审批恢复。
    return builder.compile(checkpointer=checkpointer)
