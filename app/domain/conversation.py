# conversation 对话

# Message
#         ↓
# Conversation
#         ↓
# ConversationRepository（接口）
#         ↓
# InMemoryConversationRepository（实现）
#         ↓
# ConversationService
#         ↓
# ChatService

from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from app.domain.message import Message


class Conversation(BaseModel):
    """一个完整的对话"""

    model_config = ConfigDict(validate_assignment=True)
    # model_config = ConfigDict(from_attributes=True) #模型可以直接从具有相同字段名的任意对象中创建实例，而无需手动转换
    session_id: str = Field(description="会话ID")
    messages: list[Message] = Field(default_factory=list, description="消息列表")

    def add_message(self, message: Message) -> None:
        """添加消息"""
        self.messages.append(message)

    def extend_messages(self, messages: list[Message]) -> None:
        """批量添加消息"""
        self.messages.extend(messages)

    def get_messages(self) -> list[Message]:
        """返回消息副本"""
        return self.messages.copy()

    def message_count(self) -> int:
        """返回消息数量"""
        return len(self.messages)

    def is_empty(self) -> bool:
        """是否为空会话"""
        return len(self.messages) == 0

    def last_message(self) -> Message | None:
        """返回最后一条消息"""
        return self.messages[-1] if self.messages else None

    def clear(self) -> None:
        """清空历史消息"""
        self.messages.clear()
