from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    ToolMessage,
)

from app.services.agent_service import AgentService


class FakeStreamingWorkflow:
    async def astream(
        self,
        *args: object,
        **kwargs: object,
    ) -> AsyncIterator[Any]:
        dsml = "<｜｜DSML｜｜tool_calls>internal protocol</｜｜DSML｜｜tool_calls>"
        yield (
            ("tool_agent",),
            "messages",
            (AIMessageChunk(content=dsml), {"langgraph_node": "agent"}),
        )
        yield (
            ("tool_agent",),
            "updates",
            {
                "agent": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "name": "web_search",
                                    "args": {"query": "test"},
                                    "id": "call-dsml",
                                    "type": "tool_call",
                                }
                            ],
                        )
                    ]
                }
            },
        )
        yield (
            ("tool_agent",),
            "messages",
            (
                AIMessageChunk(content="最终回答"),
                {"langgraph_node": "agent"},
            ),
        )
        yield (
            ("tool_agent",),
            "updates",
            {"agent": {"messages": [AIMessage(content="最终回答")]}},
        )


@pytest.mark.anyio
async def test_used_tools_only_contains_tools_from_current_turn() -> None:
    tool_call_message = AIMessage(
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
    tool_result_message = ToolMessage(
        content="sunny",
        name="get_weather",
        tool_call_id="call-001",
    )

    first_turn_messages = [
        HumanMessage(content="What is the weather?"),
        tool_call_message,
        tool_result_message,
        AIMessage(content="It is sunny."),
    ]
    complete_history_after_second_turn = [
        *first_turn_messages,
        HumanMessage(content="Thank you."),
        AIMessage(content="You are welcome."),
    ]

    workflow = Mock()
    workflow.ainvoke = AsyncMock()
    workflow.ainvoke.side_effect = [
        {"messages": first_turn_messages},
        {"messages": complete_history_after_second_turn},
    ]

    agent_service = AgentService(workflow)

    first_response = await agent_service.chat(
        session_id="session-001",
        message="What is the weather?",
    )
    second_response = await agent_service.chat(
        session_id="session-001",
        message="Thank you.",
    )

    assert first_response.used_tools == ["get_weather"]
    assert second_response.used_tools == []


@pytest.mark.anyio
async def test_agent_service_passes_collection_name_to_workflow() -> None:
    workflow = Mock()
    workflow.ainvoke = AsyncMock()
    workflow.ainvoke.return_value = {
        "messages": [
            HumanMessage(content="How is the project deployed?"),
            AIMessage(content="Deployment answer."),
        ]
    }

    agent_service = AgentService(workflow)

    await agent_service.chat(
        session_id="session-001",
        message="How is the project deployed?",
        collection_name="engineering",
    )

    initial_state = workflow.ainvoke.call_args.args[0]

    assert initial_state["session_id"] == "session-001"
    assert initial_state["collection_name"] == "engineering"
    assert initial_state["messages"][0].content == ("How is the project deployed?")


@pytest.mark.anyio
async def test_agent_service_returns_rag_citations() -> None:
    workflow = Mock()
    workflow.ainvoke = AsyncMock()
    workflow.ainvoke.return_value = {
        "route": "rag",
        "route_reason": "Explicit rag mode was requested.",
        "messages": [
            HumanMessage(content="Which framework is used?"),
            AIMessage(content="The service uses FastAPI [1]."),
        ],
        "citations": [
            {
                "index": 1,
                "source": "README.md",
                "excerpt": "The service uses FastAPI.",
                "score": 0.8,
            }
        ],
    }

    agent_service = AgentService(workflow)

    response = await agent_service.chat(
        session_id="session-001",
        message="Which framework is used?",
        collection_name="engineering",
    )

    assert response.answer == "The service uses FastAPI [1]."
    assert len(response.citations) == 1
    assert response.citations[0].index == 1
    assert response.citations[0].source == "README.md"
    assert response.citations[0].score == 0.8
    assert response.route == "rag"
    assert response.route_reason == "Explicit rag mode was requested."


@pytest.mark.anyio
async def test_stream_does_not_expose_agent_protocol_content() -> None:
    agent_service = AgentService(FakeStreamingWorkflow())

    events = [
        event
        async for event in agent_service._stream_workflow(
            input_value={},
            session_id="session-dsml",
            route="agent",
            route_reason="test",
            used_tools=[],
            citations=[],
        )
    ]

    output = "".join(events)
    assert "internal protocol" not in output
    assert "event: tool_call" in output
    assert '"name": "web_search"' in output
    assert "event: token" in output
    assert "最终回答" in output
