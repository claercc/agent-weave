from functools import partial
from typing import Any

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.graph.nodes import (
    _get_langchain_tools,
    agent_node,
    fallback_no_relevant_documents,
    generate_rag_answer,
    grade_documents,
    prepare_retrieval_query,
    retrieve_documents,
    route_after_agent,
    route_after_grading,
    route_request,
    select_request_route,
)
from app.graph.state import State
from app.rag.retriever import Retriever
from app.services.tool_service import ToolService
from langgraph.checkpoint.base import BaseCheckpointSaver


def create_agent_workflow(
    llm: ChatOpenAI,
    tool_service: ToolService,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
    retriever: Retriever | None = None,
    router_llm: ChatOpenAI | None = None,
) -> Any:
    """Build and compile the minimal ReAct agent workflow."""
    tools = _get_langchain_tools(tool_service)
    builder = StateGraph(State)
    effective_router_llm = router_llm or llm
    builder.add_node("agent", partial(agent_node, llm=llm, tools=tools))
    if retriever is None:
        builder.add_edge(START, "agent")
    else:
        builder.add_node(
            "router",
            partial(
                route_request,
                router_llm=effective_router_llm,
            ),
        )
        builder.add_node("prepare_retrieval_query", prepare_retrieval_query)
        builder.add_node("retrieve", partial(retrieve_documents, retriever=retriever))
        builder.add_node("grade", partial(grade_documents, min_score=0.4))
        builder.add_node("generate", partial(generate_rag_answer, llm=llm))
        builder.add_node("fallback", fallback_no_relevant_documents)
        builder.add_node("chat", partial(agent_node, llm=llm, tools=[]))

        builder.add_edge(START, "router")
        builder.add_conditional_edges(
            "router",
            select_request_route,
            {"chat": "chat", "rag": "prepare_retrieval_query", "agent": "agent"},
        )
        builder.add_edge("prepare_retrieval_query", "retrieve")
        builder.add_edge("retrieve", "grade")
        builder.add_conditional_edges(
            "grade",
            route_after_grading,
            {"generate": "generate", "fallback": "fallback"},
        )
        builder.add_edge("fallback", END)
        builder.add_edge("generate", END)
        builder.add_edge("chat", END)

    if tools:
        builder.add_node("tools", ToolNode(tools, handle_tool_errors=True))
        builder.add_conditional_edges(
            "agent", route_after_agent, {"tools": "tools", "end": END}
        )
        builder.add_edge("tools", "agent")
    else:
        builder.add_edge("agent", END)

    return builder.compile(checkpointer=checkpointer)
