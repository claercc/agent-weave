from typing import cast

from openai.types.chat import ChatCompletionMessageParam

from app.domain.message import Message, MessageRole
from app.prompts.system import SYSTEM_PROMPT


class OpenAIMessageAdapter:
    """OpenAI 消息适配器。"""

    @staticmethod
    def convert(
        messages: list[Message],
    ) -> list[ChatCompletionMessageParam]:
        """将领域消息转换为 OpenAI 消息格式。"""
        raw_messages = [
            {
                "role": MessageRole.SYSTEM.value,
                "content": SYSTEM_PROMPT,
            },
            *[
                {
                    "role": message.role.value,
                    "content": message.content,
                }
                for message in messages
            ],
        ]

        return cast(
            list[ChatCompletionMessageParam],
            raw_messages,
        )
