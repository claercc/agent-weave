# 对话存储库（接口）
from __future__ import annotations
from app.domain.conversation import Conversation
from abc import ABC, abstractmethod


class ConversationRepository(ABC):
    """对话存储库接口"""

    @abstractmethod
    def get(self, session_id: str) -> Conversation | None:
        """根据session_id获取对话"""
        raise NotImplementedError()

    def save(self, conversation: Conversation) -> Conversation:
        """保存对话"""
        raise NotImplementedError()

    def delete(self, session_id: str) -> None:
        """删除对话"""
        raise NotImplementedError()
