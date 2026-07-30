from functools import partial

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.graph.nodes import _get_langchain_tools, agent_node
from app.graph.state import State
from app.services.tool_service import ToolService


def create_agent_workflow(
    llm: ChatOpenAI,
    tool_service: ToolService,
):
    """Build and compile the minimal ReAct agent workflow."""
    tools = _get_langchain_tools(tool_service)
    builder = StateGraph(State)
    builder.add_node("agent", partial(agent_node, llm=llm, tools=tools))
    builder.add_edge(START, "agent")

    if tools:
        builder.add_node("tools", ToolNode(tools, handle_tool_errors=True))
        builder.add_conditional_edges("agent", tools_condition)
        builder.add_edge("tools", "agent")
    else:
        builder.add_edge("agent", END)

    return builder.compile()
