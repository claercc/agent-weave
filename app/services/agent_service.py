from langchain.messages import AIMessage, HumanMessage

from app.schemas.response import AgentChatResponse
from app.domain.routing import RoutingMode


class AgentService:
    """Run the LangGraph agent and map its state to an API response."""

    def __init__(self, workflow) -> None:
        self._workflow = workflow

    def chat(
        self,
        session_id: str,
        message: str,
        collection_name: str | None = None,
        mode: RoutingMode = "auto",
    ) -> AgentChatResponse:
        result = self._workflow.invoke(
            {
                "session_id": session_id,
                "mode": mode,
                "collection_name": collection_name,
                "messages": [HumanMessage(content=message)],
            },
            config={
                "configurable": {"thread_id": session_id},
                "recursion_limit": 10,
            },
        )
        messages = result["messages"]
        current_turn_messages = self._get_current_turn_messages(messages)

        answer = self._find_final_answer(current_turn_messages)
        used_tools = [
            tool_call["name"]
            for graph_message in current_turn_messages
            if isinstance(graph_message, AIMessage)
            for tool_call in graph_message.tool_calls
        ]
        citations = result.get("citations", []) if result.get("route") == "rag" else []
        return AgentChatResponse(
            session_id=session_id,
            answer=answer,
            used_tools=used_tools,
            citations=citations,
        )

    @staticmethod
    def _find_final_answer(messages: list) -> str:
        for message in reversed(messages):
            if isinstance(message, AIMessage) and not message.tool_calls:
                return (
                    message.content
                    if isinstance(message.content, str)
                    else str(message.content)
                )
        return ""

    @staticmethod
    def _get_current_turn_messages(messages: list) -> list:
        for index in range(len(messages) - 1, -1, -1):
            if isinstance(messages[index], HumanMessage):
                return messages[index:]

        return messages
