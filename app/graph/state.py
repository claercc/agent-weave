from langgraph.graph import MessagesState


class State(MessagesState):
    """LangGraph workflow state."""

    session_id: str
