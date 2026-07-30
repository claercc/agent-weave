from typing import Any

from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool
from langchain_openai import ChatOpenAI

from app.domain.message import Message, MessageRole
from app.graph.state import State
from app.prompts.system import SYSTEM_PROMPT
from app.services.tool_service import ToolService


def _convert_to_langchain_messages(messages: list[Message]) -> list[Any]:
    """Convert legacy domain messages to LangChain messages."""
    langchain_messages: list[Any] = [SystemMessage(content=SYSTEM_PROMPT)]
    for message in messages:
        if message.role == MessageRole.USER:
            langchain_messages.append(HumanMessage(content=message.content))
        elif message.role == MessageRole.ASSISTANT:
            langchain_messages.append(AIMessage(content=message.content))
        elif message.role == MessageRole.TOOL:
            langchain_messages.append(
                ToolMessage(content=message.content, tool_call_id="legacy")
            )
    return langchain_messages


def _get_langchain_tools(tool_service: ToolService) -> list[BaseTool]:
    """Adapt registered application tools to LangChain tools."""
    return [
        _create_langchain_tool(tool_dict, tool_service)
        for tool_dict in tool_service.list_tools()
    ]


def _create_langchain_tool(
    tool_dict: dict[str, Any],
    tool_service: ToolService,
) -> BaseTool:
    """Create a LangChain tool backed by ToolService."""
    function_spec = tool_dict["function"]

    def tool_wrapper(**kwargs: Any) -> str:
        result = tool_service.call_tool(function_spec["name"], **kwargs)
        if isinstance(result, str):
            return result
        if result.success:
            return str(result.data)
        return f"Tool execution failed: {result.error}"

    return StructuredTool.from_function(
        func=tool_wrapper,
        args_schema=function_spec["parameters"],
        name=function_spec["name"],
        description=function_spec["description"],
    )


def agent_node(
    state: State,
    *,
    llm: ChatOpenAI,
    tools: list[BaseTool],
) -> dict[str, list[AIMessage]]:
    """Ask the model for the next response or tool call."""
    messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
    model = llm.bind_tools(tools) if tools else llm
    response = model.invoke(messages)
    return {"messages": [response]}
