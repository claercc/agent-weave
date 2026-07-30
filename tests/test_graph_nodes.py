from unittest.mock import Mock
from app.graph.nodes import _get_langchain_tools
from app.services.tool_service import ToolService

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.domain.message import Message, MessageRole
from app.graph.nodes import _convert_to_langchain_messages
from app.prompts.system import SYSTEM_PROMPT

def test_get_langchain_tools_preserves_schema_and_uses_injected_service():
    tool_service = Mock(spec=ToolService)
    tool_service.list_tools.return_value = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取天气",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"},
                    },
                    "required": ["city"],
                },
            },
        }
    ]
    tool_service.call_tool.return_value = "sunny"

    tools = _get_langchain_tools(tool_service)
    tool = tools[0]
    result = tool.invoke({"city": "Shanghai"})

    assert len(tools) == 1
    assert tool.name == "get_weather"
    assert "city" in tool.args
    assert result == "sunny"

    tool_service.call_tool.assert_called_once_with(
        "get_weather",
        city="Shanghai",
    )
def test_convert_domain_messages_to_langchain_messages():
    # Arrange
    messages = [
        Message(role=MessageRole.USER, content="hello"),
        Message(role=MessageRole.ASSISTANT, content="hi"),
    ]

    # Act
    result = _convert_to_langchain_messages(messages)

    # Assert
    assert len(result) == 3

    assert isinstance(result[0], SystemMessage)
    assert result[0].content == SYSTEM_PROMPT

    assert isinstance(result[1], HumanMessage)
    assert result[1].content == "hello"

    assert isinstance(result[2], AIMessage)
    assert result[2].content == "hi"