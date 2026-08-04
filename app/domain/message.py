# from __future__ import annotations 是 Python 3.7+ 引入的一个 future 语句，主要用于实现 延迟注解求值
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class MessageRole(str, Enum):
    """对话角色"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Message(BaseModel):
    """对话消息"""

    model_config = ConfigDict(frozen=True)  # 冻结模型，防止属性被修改
    role: MessageRole = Field(description="消息角色")
    content: str = Field(default="", description="消息内容")
