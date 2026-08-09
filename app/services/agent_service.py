from collections.abc import Iterator
from typing import Any

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    ToolMessage,
)
from langgraph.types import Command

from app.domain.routing import RoutingMode
from app.schemas.response import AgentChatResponse
from app.utils.stream import encode_sse


class AgentService:
    """运行 LangGraph Agent 并映射普通响应或 SSE 事件。"""

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
        used_tools = self._find_requested_tools(current_turn_messages)
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
        """启动新的 Agent SSE 工作流。"""

        yield encode_sse(
            "start",
            {
                "session_id": session_id,
                "requested_mode": mode,
            },
        )

        yield from self._stream_workflow(
            input_value=self._build_input(
                session_id=session_id,
                message=message,
                collection_name=collection_name,
                mode=mode,
            ),
            session_id=session_id,
            route="agent",
            route_reason=("当前工作流未启用路由器，直接执行 Agent。"),
            used_tools=[],
            citations=[],
        )

    def resume_chat(
        self,
        session_id: str,
        interrupt_id: str,
        approved: bool,
        feedback: str | None = None,
    ) -> Iterator[str]:
        """根据人工审批结果恢复被暂停的 Agent 工作流。"""

        config = self._build_config(session_id)
        snapshot = self._workflow.get_state(config)
        values = snapshot.values or {}

        route = values.get("route", "agent")
        route_reason = values.get(
            "route_reason",
            "当前工作流未启用路由器，直接执行 Agent。",
        )

        messages = values.get("messages", [])
        current_turn_messages = self._get_current_turn_messages(messages)

        # 这里只统计已经产生 ToolMessage 的工具，
        # 避免把“提出调用但被拒绝”的工具算成已执行。
        used_tools = self._find_executed_tools(current_turn_messages)

        citations = values.get("citations", []) if route == "rag" else []

        normalized_feedback = (
            feedback.strip() if isinstance(feedback, str) and feedback.strip() else None
        )

        yield encode_sse(
            "approval_resolved",
            {
                "session_id": session_id,
                "interrupt_id": interrupt_id,
                "approved": approved,
                "feedback": normalized_feedback,
            },
        )

        resume_value = {
            "approved": approved,
            "feedback": normalized_feedback,
        }

        command: Command[str] = Command(
            resume={
                interrupt_id: resume_value,
            }
        )

        yield from self._stream_workflow(
            input_value=command,
            session_id=session_id,
            route=route,
            route_reason=route_reason,
            used_tools=used_tools,
            citations=citations,
        )

    def _stream_workflow(
        self,
        input_value: Any,
        session_id: str,
        route: str,
        route_reason: str,
        used_tools: list[str],
        citations: list[dict[str, Any]],
    ) -> Iterator[str]:
        """将 LangGraph stream 转换成前端使用的 SSE 事件。"""

        final_answer = ""
        was_interrupted = False

        retrieval_query: str | None = None
        retrieved_candidate_count = 0

        try:
            stream = self._workflow.stream(
                input_value,
                config=self._build_config(session_id),
                stream_mode=["updates", "messages"],
            )

            for stream_mode, chunk in stream:
                if stream_mode == "messages":
                    message_chunk, metadata = chunk
                    node_name = metadata.get("langgraph_node")

                    # 路由器和审批节点的内部输出不属于最终回答。
                    if node_name not in {
                        "chat",
                        "agent",
                        "generate",
                        "clarify",
                    }:
                        continue

                    if not isinstance(
                        message_chunk,
                        AIMessageChunk,
                    ):
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

                if stream_mode != "updates" or not isinstance(chunk, dict):
                    continue

                for node_name, update in chunk.items():
                    if node_name == "__interrupt__":
                        was_interrupted = True

                        if not isinstance(update, (list, tuple)):
                            continue

                        for interrupt_info in update:
                            value = interrupt_info.value

                            if not isinstance(value, dict):
                                value = {
                                    "type": "tool_approval",
                                    "message": str(value),
                                }

                            yield encode_sse(
                                "approval_required",
                                {
                                    **value,
                                    "session_id": session_id,
                                    "interrupt_id": (interrupt_info.id),
                                },
                            )

                        continue

                    if not isinstance(update, dict):
                        continue

                    if node_name == "router":
                        route = update.get("route", route)
                        route_reason = update.get(
                            "route_reason",
                            route_reason,
                        )

                        # 先发送完整请求分析，
                        # 再发送最终选择的工作流路由。
                        yield encode_sse(
                            "analysis",
                            {
                                "intent": update.get(
                                    "intent",
                                    "conversation",
                                ),
                                "route": route,
                                "needs_knowledge": update.get(
                                    "needs_knowledge",
                                    False,
                                ),
                                "needs_tools": update.get(
                                    "needs_tools",
                                    False,
                                ),
                                "requires_clarification": (
                                    update.get(
                                        "requires_clarification",
                                        False,
                                    )
                                ),
                                "rewritten_query": update.get("rewritten_query"),
                                "clarification_question": (
                                    update.get("clarification_question")
                                ),
                                "reason": route_reason,
                            },
                        )

                        yield encode_sse(
                            "route",
                            {
                                "route": route,
                                "reason": route_reason,
                            },
                        )

                    if node_name == "prepare_retrieval_query":
                        query_value = update.get("retrieval_query")

                        if isinstance(query_value, str):
                            retrieval_query = query_value

                    if node_name == "retrieve":
                        retrieved_documents = update.get(
                            "retrieved_documents",
                            [],
                        )

                        if not isinstance(
                            retrieved_documents,
                            list,
                        ):
                            retrieved_documents = []

                        retrieved_candidate_count = len(retrieved_documents)

                        candidates: list[dict[str, Any]] = []

                        for document in retrieved_documents:
                            if not isinstance(document, dict):
                                continue

                            metadata = document.get(
                                "metadata",
                                {},
                            )

                            if not isinstance(metadata, dict):
                                metadata = {}

                            candidates.append(
                                {
                                    "source": str(
                                        metadata.get(
                                            "source",
                                            "unknown",
                                        )
                                    ),
                                    "page": metadata.get("page"),
                                    "score": document.get("score"),
                                }
                            )

                        yield encode_sse(
                            "retrieval",
                            {
                                "query": retrieval_query or "",
                                "count": retrieved_candidate_count,
                                "candidates": candidates,
                            },
                        )

                    if node_name == "grade":
                        filtered_documents = update.get(
                            "retrieved_documents",
                            [],
                        )

                        if not isinstance(
                            filtered_documents,
                            list,
                        ):
                            filtered_documents = []

                        kept_count = len(filtered_documents)

                        yield encode_sse(
                            "retrieval_graded",
                            {
                                "input_count": (retrieved_candidate_count),
                                "kept_count": kept_count,
                                "discarded_count": max(
                                    0,
                                    retrieved_candidate_count - kept_count,
                                ),
                                "has_relevant_documents": (
                                    update.get(
                                        "has_relevant_documents",
                                        False,
                                    )
                                ),
                            },
                        )

                    update_messages = update.get(
                        "messages",
                        [],
                    )

                    for graph_message in update_messages:
                        if isinstance(
                            graph_message,
                            AIMessage,
                        ):
                            if graph_message.tool_calls:
                                for tool_call in graph_message.tool_calls:
                                    yield encode_sse(
                                        "tool_call",
                                        {
                                            "name": tool_call["name"],
                                            "arguments": (
                                                tool_call.get(
                                                    "args",
                                                    {},
                                                )
                                            ),
                                        },
                                    )
                            else:
                                answer = self._message_content_to_text(
                                    graph_message.content
                                )

                                if answer:
                                    final_answer = answer

                        if isinstance(
                            graph_message,
                            ToolMessage,
                        ):
                            tool_name = graph_message.name or "unknown"

                            # 只有 ToolNode 的 ToolMessage 才代表
                            # 工具确实执行过。审批拒绝产生的
                            # ToolMessage 不计入 used_tools。
                            if node_name == "tools" and tool_name not in used_tools:
                                used_tools.append(tool_name)

                            yield encode_sse(
                                "tool_result",
                                {
                                    "name": tool_name,
                                    "content": (
                                        self._message_content_to_text(
                                            graph_message.content
                                        )
                                    ),
                                    "executed": (node_name == "tools"),
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

            # interrupt 表示工作流只是暂停，并没有真正结束。
            # 此时不能发送 done，否则前端会误以为任务完成。
            if was_interrupted:
                return

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
            "messages": [
                HumanMessage(content=message),
            ],
        }

    @staticmethod
    def _build_config(
        session_id: str,
    ) -> dict[str, Any]:
        """使用 session_id 作为 LangGraph thread_id。"""

        return {
            "configurable": {
                "thread_id": session_id,
            },
            "recursion_limit": 10,
        }

    @staticmethod
    def _find_final_answer(
        messages: list[Any],
    ) -> str:
        for message in reversed(messages):
            if isinstance(message, AIMessage) and not message.tool_calls:
                return AgentService._message_content_to_text(message.content)

        return ""

    @staticmethod
    def _find_requested_tools(
        messages: list[Any],
    ) -> list[str]:
        """返回 Agent 在本轮中提出调用的工具。"""

        tool_names: list[str] = []

        for message in messages:
            if not isinstance(message, AIMessage):
                continue

            for tool_call in message.tool_calls:
                tool_name = tool_call["name"]

                if tool_name not in tool_names:
                    tool_names.append(tool_name)

        return tool_names

    @staticmethod
    def _find_executed_tools(
        messages: list[Any],
    ) -> list[str]:
        """根据 ToolMessage 返回已经执行的工具。"""

        tool_names: list[str] = []

        for message in messages:
            if not isinstance(message, ToolMessage):
                continue

            if message.name and message.name not in tool_names:
                tool_names.append(message.name)

        return tool_names

    @staticmethod
    def _message_content_to_text(
        content: Any,
    ) -> str:
        """将模型消息内容转换成可展示文本。"""

        if isinstance(content, str):
            return content

        return str(content)

    @staticmethod
    def _get_current_turn_messages(
        messages: list[Any],
    ) -> list[Any]:
        for index in range(
            len(messages) - 1,
            -1,
            -1,
        ):
            if isinstance(messages[index], HumanMessage):
                return messages[index:]

        return messages
