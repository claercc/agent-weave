# d:\ai_std_3\ai-agent-backend\tests\test_conversation.py
"""测试 Conversation 领域模型"""

from app.domain.conversation import Conversation
from app.domain.message import Message, MessageRole


class TestConversation:
    """Conversation 类测试"""

    def test_initialization(self):
        """测试初始化"""
        messages = [
            Message(role=MessageRole.USER, content="你好"),
            Message(role=MessageRole.ASSISTANT, content="你好！我能帮你做什么？"),
        ]
        conversation = Conversation(session_id="test-session-001", messages=messages)

        assert conversation.session_id == "test-session-001"
        assert len(conversation.messages) == 2
        assert conversation.messages[0].role == MessageRole.USER
        assert conversation.messages[1].role == MessageRole.ASSISTANT

    def test_add_message(self):
        """测试添加消息"""
        conversation = Conversation(session_id="test-session-002", messages=[])

        # 添加第一条消息
        msg1 = Message(role=MessageRole.USER, content="问题1")
        conversation.add_message(msg1)
        assert len(conversation.messages) == 1

        # 添加第二条消息
        msg2 = Message(role=MessageRole.ASSISTANT, content="回答1")
        conversation.add_message(msg2)
        assert len(conversation.messages) == 2
        assert conversation.messages[1].content == "回答1"

    def test_get_messages_returns_copy(self):
        """测试 get_messages 返回副本（防止外部修改）"""
        messages = [Message(role=MessageRole.USER, content="原始消息")]
        conversation = Conversation(session_id="test-session-003", messages=messages)

        # 获取消息
        retrieved_messages = conversation.get_messages()

        # 修改返回的列表
        retrieved_messages.append(
            Message(role=MessageRole.ASSISTANT, content="额外消息")
        )

        # 原对象不应受影响
        assert len(conversation.messages) == 1
        assert len(retrieved_messages) == 2

    def test_clear_messages(self):
        """测试清空消息"""
        messages = [
            Message(role=MessageRole.USER, content="消息1"),
            Message(role=MessageRole.ASSISTANT, content="消息2"),
        ]
        conversation = Conversation(session_id="test-session-004", messages=messages)

        assert len(conversation.messages) == 2

        conversation.clear()

        assert len(conversation.messages) == 0

    def test_empty_conversation(self):
        """测试空对话"""
        conversation = Conversation(session_id="test-session-005", messages=[])

        assert conversation.session_id == "test-session-005"
        assert conversation.messages == []
        assert conversation.get_messages() == []
