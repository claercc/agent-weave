from unittest.mock import AsyncMock, Mock

import pytest

from langchain_openai import ChatOpenAI
from app.graph.nodes import _get_langchain_tools
from app.services.tool_service import ToolService

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.domain.message import Message, MessageRole
from app.graph.nodes import _convert_to_langchain_messages
from app.prompts.system import SYSTEM_PROMPT
from app.graph.nodes import route_after_agent
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import ToolNode

from app.models.output_model import ToolCallResult
from langgraph.graph import END, START, StateGraph
from app.graph.nodes import grade_documents, route_after_grading

from app.graph.state import State
from app.graph.nodes import route_request
from app.graph.nodes import (
    prepare_retrieval_query,
    retrieve_documents,
)
from app.rag.retriever import Retriever
from app.models.routing import RequestAnalysis


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


def test_route_after_agent_ends_when_model_returns_final_answer():
    tool_service = Mock(spec=ToolService)
    state = {
        "session_id": "session-001",
        "messages": [
            AIMessage(content="This is the final answer."),
        ],
    }

    result = route_after_agent(state, tool_service=tool_service)

    assert result == "end"


def test_route_after_agent_routes_to_tools_when_model_requests_tool():
    tool_service = Mock(spec=ToolService)
    tool_service.requires_approval.return_value = False
    state = {
        "session_id": "session-001",
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_weather",
                        "args": {"city": "Singapore"},
                        "id": "call-001",
                        "type": "tool_call",
                    }
                ],
            ),
        ],
    }

    result = route_after_agent(state, tool_service=tool_service)

    assert result == "tools"


@pytest.mark.anyio
async def test_tool_node_executes_tool_call_and_returns_tool_message():
    tool_service = Mock(spec=ToolService)
    tool_service.list_tools.return_value = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather for a city",
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
    tool_service.call_tool_async.return_value = ToolCallResult.success_result(
        tool_name="get_weather",
        data="sunny",
    )
    tool_service.serialize_result.return_value = "sunny"

    tools = _get_langchain_tools(tool_service)

    builder = StateGraph(State)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "tools")
    builder.add_edge("tools", END)
    workflow = builder.compile()

    result = await workflow.ainvoke(
        {
            "session_id": "session-001",
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "get_weather",
                            "args": {"city": "Singapore"},
                            "id": "call-001",
                            "type": "tool_call",
                        }
                    ],
                )
            ],
        }
    )

    tool_message = result["messages"][-1]

    assert isinstance(tool_message, ToolMessage)
    assert tool_message.content == "sunny"
    assert tool_message.name == "get_weather"
    assert tool_message.tool_call_id == "call-001"

    tool_service.call_tool_async.assert_awaited_once_with(
        "get_weather",
        city="Singapore",
    )


@pytest.mark.anyio
async def test_route_request_selects_rag_when_collection_is_provided():
    state = {
        "session_id": "session-001",
        "collection_name": "engineering",
        "messages": [HumanMessage(content="Which framework is used?")],
    }

    result = await route_request(state)

    decision = result["proposed_decision"]
    assert decision["route"] == "rag"
    assert "确定性兜底建议" in decision["reason"]


@pytest.mark.anyio
async def test_route_request_selects_agent_without_collection():
    state = {
        "session_id": "session-001",
        "collection_name": None,
        "messages": [HumanMessage(content="What time is it?")],
    }

    result = await route_request(state)

    decision = result["proposed_decision"]
    assert decision["route"] == "agent"
    assert "确定性兜底建议" in decision["reason"]


def test_prepare_retrieval_query_uses_latest_user_message():
    state = {
        "session_id": "session-001",
        "messages": [
            HumanMessage(content="First question"),
            AIMessage(content="First answer"),
            HumanMessage(content="Latest question"),
        ],
    }

    result = prepare_retrieval_query(state)

    assert result == {
        "retrieval_query": "Latest question",
    }


@pytest.mark.anyio
async def test_retrieve_documents_returns_normalized_documents():
    retriever = Mock(spec=Retriever)
    retriever.retrieve.return_value = [
        {
            "document": "The service uses FastAPI.",
            "metadatas": {
                "source": "README.md",
            },
            "distance": 0.25,
        }
    ]

    state = {
        "session_id": "session-001",
        "collection_name": "engineering",
        "retrieval_query": "Which framework is used?",
        "messages": [],
    }

    result = await retrieve_documents(
        state,
        retriever=retriever,
        top_k=3,
    )

    assert result == {
        "retrieved_documents": [
            {
                "content": "The service uses FastAPI.",
                "metadata": {
                    "source": "README.md",
                },
                "score": 0.75,
            }
        ]
    }

    retriever.retrieve.assert_called_once_with(
        query="Which framework is used?",
        collection_name="engineering",
        top_k=3,
    )


def test_grade_documents_filters_low_score_documents():
    relevant_document = {
        "content": "The service uses FastAPI.",
        "metadata": {"source": "README.md"},
        "score": 0.8,
    }
    irrelevant_document = {
        "content": "Unrelated information.",
        "metadata": {"source": "other.txt"},
        "score": 0.2,
    }

    state = {
        "session_id": "session-001",
        "messages": [],
        "retrieved_documents": [
            relevant_document,
            irrelevant_document,
        ],
    }

    result = grade_documents(
        state,
        min_score=0.5,
    )

    assert result == {
        "retrieved_documents": [relevant_document],
        "has_relevant_documents": True,
    }


def test_grade_documents_marks_empty_result_as_not_relevant():
    state = {
        "session_id": "session-001",
        "messages": [],
        "retrieved_documents": [
            {
                "content": "Unrelated information.",
                "metadata": {},
                "score": 0.2,
            }
        ],
    }

    result = grade_documents(
        state,
        min_score=0.5,
    )

    assert result == {
        "retrieved_documents": [],
        "has_relevant_documents": False,
    }


def test_route_after_grading_selects_generate_or_fallback():
    generate_route = route_after_grading(
        {
            "session_id": "session-001",
            "messages": [],
            "has_relevant_documents": True,
        }
    )
    fallback_route = route_after_grading(
        {
            "session_id": "session-002",
            "messages": [],
            "has_relevant_documents": False,
        }
    )

    assert generate_route == "generate"
    assert fallback_route == "fallback"


@pytest.mark.anyio
async def test_route_request_honors_explicit_chat_mode():
    state = {
        "session_id": "session-001",
        "mode": "chat",
        "collection_name": "engineering",
        "messages": [HumanMessage(content="hello")],
    }

    result = await route_request(state)

    assert result["proposed_decision"]["route"] == "chat"


@pytest.mark.anyio
async def test_auto_router_uses_structured_llm_decision():
    router_llm = Mock(spec=ChatOpenAI)
    structured_router = Mock()
    structured_router.ainvoke = AsyncMock()

    router_llm.with_structured_output.return_value = structured_router
    structured_router.ainvoke.return_value = RequestAnalysis(
        intent="conversation",
        route="chat",
        needs_knowledge=False,
        needs_tools=False,
        requires_clarification=False,
        rewritten_query=None,
        clarification_question=None,
        reason="The user is greeting the assistant.",
    )

    state = {
        "session_id": "session-001",
        "mode": "auto",
        "collection_name": "engineering",
        "messages": [
            HumanMessage(content="hello"),
        ],
    }

    result = await route_request(
        state,
        router_llm=router_llm,
    )

    assert result["proposed_decision"]["route"] == "chat"
    assert result["proposed_decision"]["reason"] == (
        "The user is greeting the assistant."
    )

    router_llm.with_structured_output.assert_called_once_with(
        RequestAnalysis,
        method="json_mode",
    )
    structured_router.ainvoke.assert_awaited_once()


@pytest.mark.anyio
async def test_auto_router_falls_back_when_llm_fails():
    router_llm = Mock(spec=ChatOpenAI)
    structured_router = Mock()
    structured_router.ainvoke = AsyncMock()

    router_llm.with_structured_output.return_value = structured_router
    structured_router.ainvoke.side_effect = RuntimeError("Router unavailable")

    state = {
        "session_id": "session-001",
        "mode": "auto",
        "collection_name": "engineering",
        "messages": [
            HumanMessage(content="hello"),
        ],
    }

    result = await route_request(
        state,
        router_llm=router_llm,
    )

    decision = result["proposed_decision"]
    assert decision["route"] == "rag"
    assert "确定性兜底建议" in decision["reason"]
