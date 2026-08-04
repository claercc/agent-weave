from __future__ import annotations
from app.domain.message import Message, MessageRole
from app.prompts.system import SYSTEM_PROMPT


class OpenAIMessageAdapter:
    """OpenAI 消息适配器"""

    @staticmethod
    def convert(messages: list[Message]) -> list[dict]:
        """将消息列表转换为 OpenAI 消息格式"""

        result = [
            {"role": MessageRole.SYSTEM.value, "content": SYSTEM_PROMPT},
        ]
        result.extend(
            [{"role": msg.role.value, "content": msg.content} for msg in messages]
        )
        return result
