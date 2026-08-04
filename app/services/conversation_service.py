from __future__ import annotations
from app.domain.conversation import Conversation
from app.repositories.conversation_repository import ConversationRepository


class ConversationService:
    """回话业务服务"""

    def __init__(self, repository: ConversationRepository):
        self._repository = repository

    def get_or_create(self, session_id: str) -> Conversation:
        """获取或创建会话"""
        conversation = self._repository.get(session_id)
        if conversation is None:
            conversation = Conversation(session_id=session_id)
            self._repository.save(conversation)
        return conversation

    def save(self, conversation: Conversation) -> None:
        """保存会话"""
        self._repository.save(conversation)

    def delete(self, session_id: str) -> None:
        """删除会话"""
        self._repository.delete(session_id)

    # def add_message(self, session_id: str, message: Message) -> None:
    #     """添加消息"""
    #     conversation = self.get_or_create(session_id)
    #     conversation.add_message(message)
    #     self._repository.save(conversation)

    # def get_messages(self, session_id: str) -> list[Message]:
    #     """获取所有消息"""
    #     conversation = self.get_or_create(session_id)
    #     return conversation.get_messages()

    # def clear(self, session_id: str) -> None:
    #     """清空历史消息"""
    #     self._repository.delete(session_id)
