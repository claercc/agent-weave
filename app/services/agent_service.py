from collections.abc import Iterator
from typing import Any

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    ToolMessage,
)

from app.domain.routing import RoutingMode
from app.schemas.response import AgentChatResponse
from app.utils.stream import encode_sse


class AgentService:
    """运行 LangGraph Agent 并将工作流状态映射为 API 响应。"""

    def __init__(self, workflow: Any) -> None:
        self._workflow = workflow

    def chat(
        self,
        session_id: str,
        message: str,
        collection_name: str | None = None,
        mode: RoutingMode = "auto",
    ) -> AgentChatResponse:
        result = self._workflow.invoke(
            self._build_input(
                session_id=session_id,
                message=message,
                collection_name=collection_name,
                mode=mode,
            ),
            config=self._build_config(session_id),
        )

        messages = result["messages"]
        current_turn_messages = self._get_current_turn_messages(messages)

        answer = self._find_final_answer(current_turn_messages)
        used_tools = self._find_used_tools(current_turn_messages)
        citations = result.get("citations", []) if result.get("route") == "rag" else []

        return AgentChatResponse(
            session_id=session_id,
            answer=answer,
            route=result.get("route", "agent"),
            route_reason=result.get(
                "route_reason",
                "当前工作流未启用路由器，直接执行 Agent。",
            ),
            used_tools=used_tools,
            citations=citations,
        )

    def stream_chat(
        self,
        session_id: str,
        message: str,
        collection_name: str | None = None,
        mode: RoutingMode = "auto",
    ) -> Iterator[str]:
        """以 SSE 形式输出 Agent 执行过程和回答内容。"""

        route = "agent"
        route_reason = "当前工作流未启用路由器，直接执行 Agent。"
        used_tools: list[str] = []
        citations: list[dict[str, Any]] = []
        final_answer = ""

        # 发送开始事件，包含会话 ID和请求模式。
        yield encode_sse(
            "start",
            {
                "session_id": session_id,
                "requested_mode": mode,
            },
        )

        try:
            stream = self._workflow.stream(
                self._build_input(
                    session_id=session_id,
                    message=message,
                    collection_name=collection_name,
                    mode=mode,
                ),
                config=self._build_config(session_id),
                # 两种模式负责不同的信息流，一种是节点更新，一种是消息流
                stream_mode=["updates", "messages"],
            )

            for stream_mode, chunk in stream:
                # messages 模式用于获取模型实时生成的 token
                if stream_mode == "messages":
                    message_chunk, metadata = chunk
                    node_name = metadata.get("langgraph_node")

                    # 只输出真正生成回答的节点，过滤路由模型的内部输出。
                    if node_name not in {"chat", "agent", "generate"}:
                        continue

                    if not isinstance(message_chunk, AIMessageChunk):
                        continue

                    content = message_chunk.content
                    if isinstance(content, str) and content:
                        yield encode_sse(
                            "token",
                            {
                                "content": content,
                                "node": node_name,
                            },
                        )

                # updates 模式用于获取工作流节点执行完成后的状态变化
                if stream_mode != "updates" or not isinstance(chunk, dict):
                    continue

                for node_name, update in chunk.items():
                    if not isinstance(update, dict):
                        continue

                    # router 节点决定路由；
                    # agent 节点决定调用工具；
                    # tools 节点返回工具结果；
                    # generate 节点生成引用；
                    # fallback 节点返回兜底答案。
                    # 这负责展示 Agent 的执行过程，包括路由、调用工具、生成引用等。
                    if node_name == "router":
                        route = update.get("route", route)
                        route_reason = update.get(
                            "route_reason",
                            route_reason,
                        )

                        # 发送路由事件，包含路由和路由原因。如：正在使用知识库搜索……。
                        yield encode_sse(
                            "route",
                            {
                                "route": route,
                                "reason": route_reason,
                            },
                        )

                    update_messages = update.get("messages", [])

                    for graph_message in update_messages:
                        if isinstance(graph_message, AIMessage):
                            if graph_message.tool_calls:
                                for tool_call in graph_message.tool_calls:
                                    tool_name = tool_call["name"]

                                    if tool_name not in used_tools:
                                        used_tools.append(tool_name)

                                    yield encode_sse(
                                        "tool_call",
                                        {
                                            "name": tool_name,
                                            "arguments": tool_call.get("args", {}),
                                        },
                                    )
                            else:
                                answer = self._message_content_to_text(
                                    graph_message.content
                                )
                                if answer:
                                    final_answer = answer

                        if isinstance(graph_message, ToolMessage):
                            yield encode_sse(
                                "tool_result",
                                {
                                    "name": graph_message.name or "unknown",
                                    "content": self._message_content_to_text(
                                        graph_message.content
                                    ),
                                },
                            )

                    if "citations" in update:
                        citations = update["citations"]

                        yield encode_sse(
                            "citations",
                            {
                                "items": citations,
                            },
                        )

            # 发送完成事件，包含会话 ID、最终答案、路由、路由原因、调用的工具列表和引用列表。
            yield encode_sse(
                "done",
                {
                    "session_id": session_id,
                    "answer": final_answer,
                    "route": route,
                    "route_reason": route_reason,
                    "used_tools": used_tools,
                    "citations": citations,
                },
            )

        except Exception as exc:
            # 流式响应一旦开始发送，HTTP 状态通常已经是 200，此时 Agent 后面即使失败，也很难再把响应改成 500
            yield encode_sse(
                "error",
                {
                    "message": str(exc),
                },
            )

    @staticmethod
    def _build_input(
        session_id: str,
        message: str,
        collection_name: str | None,
        mode: RoutingMode,
    ) -> dict[str, Any]:
        """构造 LangGraph 初始状态。"""

        return {
            "session_id": session_id,
            "mode": mode,
            "collection_name": collection_name,
            "messages": [HumanMessage(content=message)],
        }

    @staticmethod
    def _build_config(session_id: str) -> dict[str, Any]:
        """构造 LangGraph 运行配置。"""

        return {
            "configurable": {
                "thread_id": session_id,
            },
            "recursion_limit": 10,
        }

    @staticmethod
    def _find_final_answer(messages: list[Any]) -> str:
        for message in reversed(messages):
            if isinstance(message, AIMessage) and not message.tool_calls:
                return AgentService._message_content_to_text(message.content)

        return ""

    @staticmethod
    def _find_used_tools(messages: list[Any]) -> list[str]:
        used_tools: list[str] = []

        for graph_message in messages:
            if not isinstance(graph_message, AIMessage):
                continue

            for tool_call in graph_message.tool_calls:
                tool_name = tool_call["name"]

                if tool_name not in used_tools:
                    used_tools.append(tool_name)

        return used_tools

    @staticmethod
    def _message_content_to_text(content: Any) -> str:
        """将模型消息内容转换为可展示文本。"""

        if isinstance(content, str):
            return content

        return str(content)

    @staticmethod
    def _get_current_turn_messages(messages: list[Any]) -> list[Any]:
        for index in range(len(messages) - 1, -1, -1):
            if isinstance(messages[index], HumanMessage):
                return messages[index:]

        return messages