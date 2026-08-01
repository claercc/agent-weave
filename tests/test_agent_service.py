from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.services.agent_service import AgentService


def test_used_tools_only_contains_tools_from_current_turn():
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

def test_agent_service_passes_collection_name_to_workflow():
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
    assert initial_state["messages"][0].content == (
        "How is the project deployed?"
    )