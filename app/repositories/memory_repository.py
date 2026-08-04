from __future__ import annotations
from app.domain.conversation import Conversation
from app.repositories.conversation_repository import ConversationRepository


class MemoryConversationRepository(ConversationRepository):
    """内存中的对话存储库"""

    def __init__(self) -> None:
        self._store: dict[str, Conversation] = {}

    def get(self, session_id: str) -> Conversation | None:
        """根据session_id获取对话"""
        return self._store.get(session_id)

    def save(self, conversation: Conversation) -> Conversation:
        """保存对话"""
        self._store[conversation.session_id] = conversation
        return conversation

    def delete(self, session_id: str) -> None:
        """删除对话"""
        self._store.pop(session_id, None)
