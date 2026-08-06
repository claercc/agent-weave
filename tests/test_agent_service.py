from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.services.agent_service import AgentService


def test_used_tools_only_contains_tools_from_current_turn() -> None:
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
    workflow.invoke.side_effect = [
        {"messages": first_turn_messages},
        {"messages": complete_history_after_second_turn},
    ]

    agent_service = AgentService(workflow)

    first_response = agent_service.chat(
        session_id="session-001",
        message="What is the weather?",
    )
    second_response = agent_service.chat(
        session_id="session-001",
        message="Thank you.",
    )

    assert first_response.used_tools == ["get_weather"]
    assert second_response.used_tools == []


def test_agent_service_passes_collection_name_to_workflow() -> None:
    workflow = Mock()
    workflow.invoke.return_value = {
        "messages": [
            HumanMessage(content="How is the project deployed?"),
            AIMessage(content="Deployment answer."),
        ]
    }

    agent_service = AgentService(workflow)

    agent_service.chat(
        session_id="session-001",
        message="How is the project deployed?",
        collection_name="engineering",
    )

    initial_state = workflow.invoke.call_args.args[0]

    assert initial_state["session_id"] == "session-001"
    assert initial_state["collection_name"] == "engineering"
    assert initial_state["messages"][0].content == ("How is the project deployed?")


def test_agent_service_returns_rag_citations() -> None:
    workflow = Mock()
    workflow.invoke.return_value = {
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

    response = agent_service.chat(
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
    assert response.route_reason == "当前工作流未启用路由器，直接执行 Agent。"
