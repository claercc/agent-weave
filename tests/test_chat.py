import pytest
from unittest.mock import Mock, MagicMock
from openai import OpenAI
from app.services.chat_service import ChatService
from app.services.tool_service import ToolService
from app.core.config import Settings
from app.services.conversation_service import ConversationService
from app.repositories.memory_repository import MemoryConversationRepository
from app.tools.registry import InMemoryToolRegistry


class TestChatService:
    """ChatService 测试类"""

    @pytest.fixture
    def mock_openai_client(self):
        """创建模拟的 OpenAI 客户端"""
        client = Mock(spec=OpenAI)
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "这是助手的回复"
        client.chat.completions.create.return_value = mock_response
        return client

    @pytest.fixture
    def settings(self):
        """创建测试配置"""
        return Settings(openai_api_key="test-key", model_name="test-model")

    @pytest.fixture
    def conversation_service(self):
        """创建对话服务"""
        repo = MemoryConversationRepository()
        return ConversationService(repo)

    @pytest.fixture
    def tool_service(self):
        """创建工具服务"""
        registry = InMemoryToolRegistry()
        return ToolService(registry)

    @pytest.fixture
    def chat_service(
        self, mock_openai_client, settings, conversation_service, tool_service
    ):
        """创建聊天服务实例"""
        return ChatService(
            client=mock_openai_client,
            settings=settings,
            conversation_service=conversation_service,
            tool_service=tool_service,
        )

    def test_chat_service_initialization(self, chat_service):
        """测试聊天服务初始化"""
        assert chat_service is not None
        assert hasattr(chat_service, "_client")
        assert hasattr(chat_service, "_settings")
        assert hasattr(chat_service, "_conversation_service")
        assert hasattr(chat_service, "_tool_service")

    def test_chat_method(self, chat_service, mock_openai_client, settings):
        """测试普通聊天方法"""
        session_id = "test-session-123"
        message = "你好"

        response = chat_service.chat(session_id, message)

        assert response == "这是助手的回复"
        mock_openai_client.chat.completions.create.assert_called_once()

        call_args = mock_openai_client.chat.completions.create.call_args[1]
        assert call_args["model"] == settings.model_name
        assert "messages" in call_args
        assert len(call_args["messages"]) == 2
        assert call_args["messages"][0]["role"] == "system"
        assert call_args["messages"][1]["role"] == "user"
        assert call_args["messages"][1]["content"] == "你好"

    def test_chat_with_history(self, chat_service, mock_openai_client):
        """测试带历史消息的聊天"""
        session_id = "test-session-history"

        chat_service.chat(session_id, "第一条消息")

        mock_openai_client.chat.completions.create.reset_mock()

        chat_service.chat(session_id, "第二条消息")

        call_args = mock_openai_client.chat.completions.create.call_args[1]
        assert len(call_args["messages"]) == 4
        assert call_args["messages"][0]["role"] == "system"
        assert call_args["messages"][1]["content"] == "第一条消息"
        assert call_args["messages"][2]["content"] == "这是助手的回复"
        assert call_args["messages"][3]["content"] == "第二条消息"
