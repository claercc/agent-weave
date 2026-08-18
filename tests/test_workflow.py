from unittest.mock import AsyncMock, Mock

import pytest

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

from app.graph.workflow import create_agent_workflow
from app.models.output_model import ToolCallResult
from app.models.routing import RequestAnalysis
from app.services.tool_service import ToolService
from langgraph.checkpoint.memory import InMemorySaver

from app.services.agent_service import AgentService
from app.rag.retriever import Retriever


@pytest.mark.anyio
async def test_agent_workflow_executes_tool_and_returns_final_answer():
    # Arrange：模拟项目中已经注册的天气工具
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
    tool_service.requires_approval.return_value = False

    # 模拟 bind_tools 后的模型
    llm = Mock(spec=ChatOpenAI)
    bound_model = Mock()
    bound_model.ainvoke = AsyncMock()
    llm.bind_tools.return_value = bound_model

    # 第一次调用要求执行工具，第二次调用给出最终回答
    bound_model.ainvoke.side_effect = [
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
        AIMessage(content="The weather in Singapore is sunny."),
    ]

    workflow = create_agent_workflow(llm, tool_service)

    # Act
    result = await workflow.ainvoke(
        {
            "session_id": "session-001",
            "messages": [
                HumanMessage(content="What is the weather in Singapore?"),
            ],
        }
    )

    # Assert
    messages = result["messages"]

    assert len(messages) == 4
    assert isinstance(messages[0], HumanMessage)
    assert isinstance(messages[1], AIMessage)
    assert isinstance(messages[2], ToolMessage)
    assert isinstance(messages[3], AIMessage)

    assert messages[2].content == "sunny"
    assert messages[2].tool_call_id == "call-001"
    assert messages[3].content == "The weather in Singapore is sunny."

    assert bound_model.ainvoke.await_count == 2
    tool_service.call_tool_async.assert_awaited_once_with(
        "get_weather",
        city="Singapore",
    )


@pytest.mark.anyio
async def test_agent_workflow_converts_dsml_content_to_tool_call() -> None:
    tool_service = Mock(spec=ToolService)
    tool_service.list_tools.return_value = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        }
    ]
    tool_service.call_tool_async.return_value = ToolCallResult.success_result(
        tool_name="web_search",
        data={"items": []},
    )
    tool_service.serialize_result.return_value = '{"items": []}'
    tool_service.requires_approval.return_value = False

    llm = Mock(spec=ChatOpenAI)
    bound_model = Mock()
    bound_model.ainvoke = AsyncMock()
    llm.bind_tools.return_value = bound_model
    bound_model.ainvoke.side_effect = [
        AIMessage(
            content=(
                "<｜｜DSML｜｜tool_calls>\n"
                '<｜｜DSML｜｜invoke name="web_search">\n'
                '<｜｜DSML｜｜parameter name="query" string="true">'
                "白人性魅力 含义 王水牛 洋滤镜"
                "</｜｜DSML｜｜parameter>\n"
                "</｜｜DSML｜｜invoke>\n"
                "</｜｜DSML｜｜tool_calls>"
            )
        ),
        AIMessage(content="这里是搜索后的回答。"),
    ]

    workflow = create_agent_workflow(llm, tool_service)
    result = await workflow.ainvoke(
        {
            "session_id": "session-dsml",
            "messages": [HumanMessage(content="白人性魅力")],
        }
    )

    tool_call_message = result["messages"][1]
    assert tool_call_message.content == ""
    assert tool_call_message.tool_calls[0]["name"] == "web_search"
    assert tool_call_message.tool_calls[0]["args"] == {
        "query": "白人性魅力 含义 王水牛 洋滤镜"
    }
    assert result["messages"][-1].content == "这里是搜索后的回答。"
    tool_service.call_tool_async.assert_awaited_once_with(
        "web_search",
        query="白人性魅力 含义 王水牛 洋滤镜",
    )


@pytest.mark.anyio
async def test_agent_workflow_does_not_execute_or_expose_unknown_dsml_tool() -> None:
    tool_service = Mock(spec=ToolService)
    tool_service.list_tools.return_value = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]

    llm = Mock(spec=ChatOpenAI)
    bound_model = Mock()
    bound_model.ainvoke = AsyncMock(
        return_value=AIMessage(
            content=(
                "<｜｜DSML｜｜tool_calls>"
                '<｜｜DSML｜｜invoke name="delete_everything">'
                "</｜｜DSML｜｜invoke>"
                "</｜｜DSML｜｜tool_calls>"
            )
        )
    )
    llm.bind_tools.return_value = bound_model

    workflow = create_agent_workflow(llm, tool_service)
    result = await workflow.ainvoke(
        {
            "session_id": "session-unknown-dsml",
            "messages": [HumanMessage(content="test")],
        }
    )

    answer = result["messages"][-1]
    assert "DSML" not in answer.content
    assert "未执行任何工具" in answer.content
    tool_service.call_tool_async.assert_not_called()


@pytest.mark.anyio
async def test_agent_remembers_messages_in_same_session():
    tool_service = Mock(spec=ToolService)
    tool_service.list_tools.return_value = []

    llm = Mock(spec=ChatOpenAI)
    llm.ainvoke.side_effect = [
        AIMessage(content="I will remember that your name is Alice."),
        AIMessage(content="Your name is Alice."),
    ]

    workflow = create_agent_workflow(
        llm,
        tool_service,
        checkpointer=InMemorySaver(),
    )
    agent_service = AgentService(workflow)

    first_response = await agent_service.chat(
        session_id="session-001",
        message="My name is Alice.",
    )
    second_response = await agent_service.chat(
        session_id="session-001",
        message="What is my name?",
    )

    assert first_response.answer == ("I will remember that your name is Alice.")
    assert second_response.answer == "Your name is Alice."

    second_call_messages = llm.ainvoke.call_args_list[1].args[0]
    assert len(second_call_messages) == 4
    assert second_call_messages[1].content == "My name is Alice."
    assert second_call_messages[2].content == (
        "I will remember that your name is Alice."
    )
    assert second_call_messages[3].content == "What is my name?"


@pytest.mark.anyio
async def test_agent_keeps_different_sessions_isolated():
    tool_service = Mock(spec=ToolService)
    tool_service.list_tools.return_value = []

    llm = Mock(spec=ChatOpenAI)
    llm.ainvoke.side_effect = [
        AIMessage(content="I will remember your name."),
        AIMessage(content="I do not know your name."),
    ]

    workflow = create_agent_workflow(
        llm,
        tool_service,
        checkpointer=InMemorySaver(),
    )
    agent_service = AgentService(workflow)

    await agent_service.chat(
        session_id="session-001",
        message="My name is Alice.",
    )
    second_response = await agent_service.chat(
        session_id="session-002",
        message="What is my name?",
    )

    second_call_messages = llm.ainvoke.call_args_list[1].args[0]

    assert second_response.answer == "I do not know your name."
    assert len(second_call_messages) == 2
    assert second_call_messages[1].content == "What is my name?"


@pytest.mark.anyio
async def test_rag_branch_retrieves_and_generates_answer():
    tool_service = Mock(spec=ToolService)
    tool_service.list_tools.return_value = []

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

    llm = Mock(spec=ChatOpenAI)
    llm.ainvoke.return_value = AIMessage(content="The service uses FastAPI [1].")

    workflow = create_agent_workflow(
        llm=llm,
        tool_service=tool_service,
        retriever=retriever,
    )

    result = await workflow.ainvoke(
        {
            "session_id": "session-001",
            "mode": "rag",
            "collection_name": "engineering",
            "messages": [HumanMessage(content="Which framework does the service use?")],
        }
    )

    assert result["route"] == "rag"
    assert result["retrieval_query"] == ("Which framework does the service use?")
    assert len(result["retrieved_documents"]) == 1
    assert result["messages"][-1].content == ("The service uses FastAPI [1].")

    retriever.retrieve.assert_called_once_with(
        query="Which framework does the service use?",
        collection_name="engineering",
        top_k=4,
    )

    llm.ainvoke.assert_awaited_once()
    generation_messages = llm.ainvoke.call_args.args[0]

    assert "README.md" in generation_messages[1].content
    assert "The service uses FastAPI." in (generation_messages[1].content)
    assert result["citations"] == [
        {
            "index": 1,
            "source": "README.md",
            "excerpt": "The service uses FastAPI.",
            "score": 0.75,
        }
    ]


@pytest.mark.anyio
async def test_rag_branch_falls_back_without_relevant_documents():
    tool_service = Mock(spec=ToolService)
    tool_service.list_tools.return_value = []

    retriever = Mock(spec=Retriever)
    retriever.retrieve.return_value = []

    llm = Mock(spec=ChatOpenAI)

    workflow = create_agent_workflow(
        llm=llm,
        tool_service=tool_service,
        retriever=retriever,
    )

    result = await workflow.ainvoke(
        {
            "mode": "rag",
            "session_id": "session-002",
            "collection_name": "engineering",
            "messages": [
                HumanMessage(content="What is the internal deployment password?")
            ],
        }
    )

    assert result["route"] == "rag"
    assert result["has_relevant_documents"] is False
    assert result["retrieved_documents"] == []
    assert result["messages"][-1].content == (
        "根据当前知识库中检索到的信息，" "我无法回答这个问题。"
    )

    llm.ainvoke.assert_not_awaited()


@pytest.mark.anyio
async def test_explicit_chat_mode_skips_retrieval():
    tool_service = Mock(spec=ToolService)
    tool_service.list_tools.return_value = []

    retriever = Mock(spec=Retriever)

    llm = Mock(spec=ChatOpenAI)
    llm.ainvoke.return_value = AIMessage(content="Hello! How can I help you?")

    workflow = create_agent_workflow(
        llm=llm,
        tool_service=tool_service,
        retriever=retriever,
    )

    result = await workflow.ainvoke(
        {
            "session_id": "session-001",
            "mode": "chat",
            "collection_name": "engineering",
            "messages": [
                HumanMessage(content="hello"),
            ],
        }
    )

    assert result["route"] == "chat"
    assert result["messages"][-1].content == ("Hello! How can I help you?")

    retriever.retrieve.assert_not_called()
    llm.bind_tools.assert_not_called()
    llm.ainvoke.assert_awaited_once()


@pytest.mark.anyio
async def test_auto_mode_uses_router_model_and_selects_chat():
    tool_service = Mock(spec=ToolService)
    tool_service.list_tools.return_value = []

    retriever = Mock(spec=Retriever)

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

    llm = Mock(spec=ChatOpenAI)
    llm.ainvoke.return_value = AIMessage(content="Hello! How can I help?")

    workflow = create_agent_workflow(
        llm=llm,
        router_llm=router_llm,
        tool_service=tool_service,
        retriever=retriever,
    )

    result = await workflow.ainvoke(
        {
            "session_id": "session-001",
            "mode": "auto",
            "collection_name": "engineering",
            "messages": [
                HumanMessage(content="hello"),
            ],
        }
    )

    assert result["route"] == "chat"
    assert result["route_reason"] == ("The user is greeting the assistant.")
    assert result["messages"][-1].content == ("Hello! How can I help?")

    router_llm.with_structured_output.assert_called_once_with(
        RequestAnalysis,
        method="json_mode",
    )
    retriever.retrieve.assert_not_called()
    llm.ainvoke.assert_awaited_once()
