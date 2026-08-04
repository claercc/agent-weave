from __future__ import annotations
from collections.abc import Iterator
from openai import OpenAI
from app.core.config import Settings
from app.domain.message import Message, MessageRole
from app.adapters.openai_message_adapter import OpenAIMessageAdapter
from app.services.conversation_service import ConversationService
from app.services.tool_service import ToolService
from typing import cast
from openai.types.chat import (
    ChatCompletionToolParam, ChatCompletionMessageFunctionToolCall
)


class ChatService:
    """聊天服务"""

    def __init__(
        self,
        client: OpenAI,
        settings: Settings,
        conversation_service: ConversationService,
        tool_service: ToolService,
    ) -> None:
        self._client = client
        self._settings = settings
        self._conversation_service = conversation_service
        self._tool_service = tool_service

    # def stream_chat(self, request: ChatRequest) -> Iterator[str]:
    #     """流式聊天"""
    #     raise NotImplementedError
    def chat(self, session_id: str, message: str) -> str:
        """普通聊天"""
        conversation = self._conversation_service.get_or_create(session_id)
        conversation.add_message(Message(role=MessageRole.USER, content=message))
        response = self._client.chat.completions.create(
            model=self._settings.model_name,
            messages=OpenAIMessageAdapter.convert(conversation.get_messages()),
        )
        assistant_message = response.choices[0].message.content or ""
        conversation.add_message(
            Message(role=MessageRole.ASSISTANT, content=assistant_message)
        )
        self._conversation_service.save(conversation)
        return assistant_message

    def stream_chat(self, session_id: str, message: str) -> Iterator[str]:
        """流式聊天"""
        conversation = self._conversation_service.get_or_create(session_id)
        conversation.add_message(Message(role=MessageRole.USER, content=message))
        response = self._client.chat.completions.create(
            model=self._settings.model_name,
            messages=OpenAIMessageAdapter.convert(conversation.get_messages()),
            stream=True,
        )
        full_message = ""
        for chunk in response:
            context = chunk.choices[0].delta.content
            if context:
                full_message += context
                yield context
        conversation.add_message(
            Message(role=MessageRole.ASSISTANT, content=full_message)
        )
        self._conversation_service.save(conversation)

        # def summarize(self, ar: str) -> SummaryResponse:

    def chat_with_tool_calling(self, session_id: str, message: str) -> str:
        """聊天并使用工具调用"""
        conversation = self._conversation_service.get_or_create(session_id)
        conversation.add_message(Message(role=MessageRole.USER, content=message))
        tools = cast(list[ChatCompletionToolParam], self._tool_service.list_tools())
        print(tools)
        response = self._client.chat.completions.create(
            model=self._settings.model_name,
            messages=OpenAIMessageAdapter.convert(conversation.get_messages()),
            tools=tools,
            tool_choice="auto",
        )
        tool_call = (
            response.choices[0].message.tool_calls[0]
            if response.choices[0].message.tool_calls
            else None
        )
        if isinstance(tool_call, ChatCompletionMessageFunctionToolCall):
            tool_result = self._tool_service.execute_tool(
                tool_call.function.name, arguments=tool_call.function.arguments
            )

            conversation.add_message(
                Message(role=MessageRole.TOOL, content=str(tool_result))
            )

            response = self._client.chat.completions.create(
                model=self._settings.model_name,
                messages=OpenAIMessageAdapter.convert(conversation.get_messages()),
                tools=tools,
                tool_choice="auto",
            )

        assistant_message = response.choices[0].message.content or ""
        conversation.add_message(
            Message(role=MessageRole.ASSISTANT, content=assistant_message)
        )
        self._conversation_service.save(conversation)
        return assistant_message
