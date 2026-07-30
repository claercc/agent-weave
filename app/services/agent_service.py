from langchain.messages import AIMessage, HumanMessage

from app.schemas.response import AgentChatResponse


class AgentService:
    """Run the LangGraph agent and map its state to an API response."""

    def __init__(self, workflow):
        self._workflow = workflow

    def chat(self, session_id: str, message: str) -> AgentChatResponse:
        result = self._workflow.invoke(
            {
                "session_id": session_id,
                "messages": [HumanMessage(content=message)],
            },
            config={"recursion_limit": 10},
        )
        messages = result["messages"]
        answer = self._find_final_answer(messages)
        used_tools = [
            tool_call["name"]
            for graph_message in messages
            if isinstance(graph_message, AIMessage)
            for tool_call in graph_message.tool_calls
        ]
        return AgentChatResponse(
            session_id=session_id,
            answer=answer,
            used_tools=used_tools,
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
